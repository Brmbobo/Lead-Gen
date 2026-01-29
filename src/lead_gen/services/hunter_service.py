"""
Hunter.io API service client for email enrichment.

Provides async access to Hunter.io API for:
- Email finder (find emails for a domain)
- Email verifier (verify email validity)
- Domain search (find all emails for a domain)

Rate limited with cost tracking.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import structlog

from lead_gen.core.config import get_settings
from lead_gen.core.exceptions import APIError, ConfigurationError, RateLimitError
from lead_gen.core.rate_limiter import RateLimitConfig, get_rate_limiter
from lead_gen.core.retry import CircuitBreaker, RetryConfig, retry_with_backoff
from lead_gen.models.lead import EmailEnrichment, EnrichedLead, Lead

logger = structlog.get_logger(__name__)

HUNTER_API_BASE = "https://api.hunter.io/v2"


@dataclass
class EmailFinderResult:
    """Result from email finder."""

    email: str | None
    confidence: int = 0
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    department: str = ""
    linkedin_url: str = ""
    twitter: str = ""
    phone_number: str = ""
    verified: bool = False
    sources: list[dict[str, Any]] = field(default_factory=list)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    api_response_time_ms: float = 0.0


@dataclass
class EmailVerifyResult:
    """Result from email verification."""

    email: str
    result: str  # deliverable, undeliverable, risky, unknown
    score: int = 0  # 0-100
    regexp: bool = False
    gibberish: bool = False
    disposable: bool = False
    webmail: bool = False
    mx_records: bool = False
    smtp_server: bool = False
    smtp_check: bool = False
    accept_all: bool = False
    block: bool = False
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class DomainSearchResult:
    """Result from domain search."""

    domain: str
    emails: list[EmailEnrichment]
    organization: str = ""
    pattern: str = ""  # Email pattern (e.g., {first}.{last})
    total_emails: int = 0
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


class HunterService:
    """
    Hunter.io API service client.

    Provides methods for finding and verifying business emails.
    Includes rate limiting and cost tracking.

    Example:
        >>> service = HunterService()
        >>> result = await service.find_email(
        ...     domain="example.com",
        ...     first_name="John",
        ...     last_name="Doe",
        ... )
        >>> print(result.email, result.confidence)
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Hunter service.

        Args:
            api_key: Hunter.io API key (defaults to settings)
            timeout: Request timeout in seconds
        """
        settings = get_settings()

        self.api_key = api_key or settings.get_hunter_key()
        if not self.api_key:
            raise ConfigurationError(
                "Hunter.io API key not configured",
                config_key="HUNTER_API_KEY",
            )

        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(service="hunter")

        # Configure rate limiter
        limiter = get_rate_limiter()
        limiter.add_service(
            "hunter",
            RateLimitConfig(requests_per_minute=settings.rate_limits.hunter),
        )

        logger.info(
            "hunter_service_initialized",
            timeout=timeout,
            rate_limit=settings.rate_limits.hunter,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                params={"api_key": self.api_key},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "HunterService":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    @retry_with_backoff(
        config=RetryConfig(max_retries=2, base_delay=1.0),
    )
    async def find_email(
        self,
        domain: str,
        first_name: str = "",
        last_name: str = "",
        full_name: str = "",
        correlation_id: str | None = None,
    ) -> EmailFinderResult:
        """
        Find email address for a person at a domain.

        Args:
            domain: Company domain (e.g., "example.com")
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last)
            correlation_id: Request correlation ID

        Returns:
            EmailFinderResult with found email
        """
        correlation_id = correlation_id or str(uuid4())
        start_time = datetime.now(timezone.utc)

        params: dict[str, str] = {"domain": domain}

        if first_name and last_name:
            params["first_name"] = first_name
            params["last_name"] = last_name
        elif full_name:
            params["full_name"] = full_name
        else:
            raise ValueError("Either first_name/last_name or full_name is required")

        # Rate limit
        limiter = get_rate_limiter()
        await limiter.acquire("hunter")

        async with self._circuit_breaker:
            client = await self._get_client()

            try:
                response = await client.get(
                    f"{HUNTER_API_BASE}/email-finder",
                    params=params,
                )

                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                if response.status_code == 429:
                    raise RateLimitError(
                        "Hunter.io rate limit exceeded",
                        service="hunter",
                        retry_after_seconds=60,
                    )

                if response.status_code == 402:
                    raise APIError(
                        "Hunter.io quota exceeded",
                        status_code=402,
                        service="hunter",
                        operation="find_email",
                    )

                if response.status_code != 200:
                    raise APIError(
                        f"Hunter.io API error: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                        service="hunter",
                        operation="find_email",
                    )

                data = response.json()

            except httpx.RequestError as e:
                raise APIError(
                    f"Network error calling Hunter.io API: {e}",
                    service="hunter",
                    operation="find_email",
                    cause=e,
                )

        result_data = data.get("data", {})

        result = EmailFinderResult(
            email=result_data.get("email"),
            confidence=result_data.get("score", 0),
            first_name=result_data.get("first_name", first_name),
            last_name=result_data.get("last_name", last_name),
            position=result_data.get("position", ""),
            department=result_data.get("department", ""),
            linkedin_url=result_data.get("linkedin", ""),
            twitter=result_data.get("twitter", ""),
            phone_number=result_data.get("phone_number", ""),
            verified=result_data.get("verification", {}).get("status") == "valid",
            sources=result_data.get("sources", []),
            correlation_id=correlation_id,
            api_response_time_ms=response_time,
        )

        logger.info(
            "hunter_email_found",
            domain=domain,
            email_found=bool(result.email),
            confidence=result.confidence,
            response_time_ms=response_time,
            correlation_id=correlation_id,
        )

        return result

    @retry_with_backoff(
        config=RetryConfig(max_retries=2, base_delay=1.0),
    )
    async def verify_email(
        self,
        email: str,
        correlation_id: str | None = None,
    ) -> EmailVerifyResult:
        """
        Verify an email address.

        Args:
            email: Email address to verify
            correlation_id: Request correlation ID

        Returns:
            EmailVerifyResult with verification details
        """
        correlation_id = correlation_id or str(uuid4())

        limiter = get_rate_limiter()
        await limiter.acquire("hunter")

        async with self._circuit_breaker:
            client = await self._get_client()

            try:
                response = await client.get(
                    f"{HUNTER_API_BASE}/email-verifier",
                    params={"email": email},
                )

                if response.status_code == 429:
                    raise RateLimitError(
                        "Hunter.io rate limit exceeded",
                        service="hunter",
                        retry_after_seconds=60,
                    )

                if response.status_code != 200:
                    raise APIError(
                        f"Hunter.io API error: {response.status_code}",
                        status_code=response.status_code,
                        service="hunter",
                        operation="verify_email",
                    )

                data = response.json()

            except httpx.RequestError as e:
                raise APIError(
                    f"Network error calling Hunter.io API: {e}",
                    service="hunter",
                    operation="verify_email",
                    cause=e,
                )

        result_data = data.get("data", {})

        result = EmailVerifyResult(
            email=email,
            result=result_data.get("result", "unknown"),
            score=result_data.get("score", 0),
            regexp=result_data.get("regexp", False),
            gibberish=result_data.get("gibberish", False),
            disposable=result_data.get("disposable", False),
            webmail=result_data.get("webmail", False),
            mx_records=result_data.get("mx_records", False),
            smtp_server=result_data.get("smtp_server", False),
            smtp_check=result_data.get("smtp_check", False),
            accept_all=result_data.get("accept_all", False),
            block=result_data.get("block", False),
            correlation_id=correlation_id,
        )

        logger.info(
            "hunter_email_verified",
            email=email[:3] + "***",  # Partial mask for logging
            result=result.result,
            score=result.score,
            correlation_id=correlation_id,
        )

        return result

    @retry_with_backoff(
        config=RetryConfig(max_retries=2, base_delay=1.0),
    )
    async def search_domain(
        self,
        domain: str,
        limit: int = 10,
        correlation_id: str | None = None,
    ) -> DomainSearchResult:
        """
        Search for all emails at a domain.

        Args:
            domain: Company domain
            limit: Maximum emails to return
            correlation_id: Request correlation ID

        Returns:
            DomainSearchResult with list of emails
        """
        correlation_id = correlation_id or str(uuid4())

        limiter = get_rate_limiter()
        await limiter.acquire("hunter")

        async with self._circuit_breaker:
            client = await self._get_client()

            try:
                response = await client.get(
                    f"{HUNTER_API_BASE}/domain-search",
                    params={"domain": domain, "limit": limit},
                )

                if response.status_code == 429:
                    raise RateLimitError(
                        "Hunter.io rate limit exceeded",
                        service="hunter",
                        retry_after_seconds=60,
                    )

                if response.status_code != 200:
                    raise APIError(
                        f"Hunter.io API error: {response.status_code}",
                        status_code=response.status_code,
                        service="hunter",
                        operation="search_domain",
                    )

                data = response.json()

            except httpx.RequestError as e:
                raise APIError(
                    f"Network error calling Hunter.io API: {e}",
                    service="hunter",
                    operation="search_domain",
                    cause=e,
                )

        result_data = data.get("data", {})

        # Parse emails
        emails: list[EmailEnrichment] = []
        for email_data in result_data.get("emails", []):
            emails.append(EmailEnrichment(
                email=email_data.get("value", ""),
                confidence=email_data.get("confidence", 0),
                type=email_data.get("type", "generic"),
                first_name=email_data.get("first_name", ""),
                last_name=email_data.get("last_name", ""),
                position=email_data.get("position", ""),
                department=email_data.get("department", ""),
                linkedin_url=email_data.get("linkedin"),
                twitter_handle=email_data.get("twitter", ""),
                phone_number=email_data.get("phone_number", ""),
                verified=email_data.get("verification", {}).get("status") == "valid",
                sources=[s.get("uri", "") for s in email_data.get("sources", [])],
            ))

        result = DomainSearchResult(
            domain=domain,
            emails=emails,
            organization=result_data.get("organization", ""),
            pattern=result_data.get("pattern", ""),
            total_emails=result_data.get("total", len(emails)),
            correlation_id=correlation_id,
        )

        logger.info(
            "hunter_domain_searched",
            domain=domain,
            emails_found=len(emails),
            total_available=result.total_emails,
            correlation_id=correlation_id,
        )

        return result

    async def enrich_lead(
        self,
        lead: Lead,
        verify: bool = True,
        correlation_id: str | None = None,
    ) -> EnrichedLead:
        """
        Enrich a lead with email data.

        Extracts domain from website and searches for emails.

        Args:
            lead: Lead to enrich
            verify: Whether to verify found emails
            correlation_id: Request correlation ID

        Returns:
            EnrichedLead with email data
        """
        correlation_id = correlation_id or str(uuid4())

        # Extract domain from website
        domain = None
        if lead.website:
            parsed = urlparse(str(lead.website))
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

        if not domain:
            # Return lead as EnrichedLead without enrichment
            return EnrichedLead(**lead.model_dump())

        # Search for emails
        try:
            domain_result = await self.search_domain(
                domain=domain,
                limit=3,
                correlation_id=correlation_id,
            )
        except APIError as e:
            logger.warning(
                "hunter_enrichment_failed",
                lead_id=lead.id,
                domain=domain,
                error=str(e),
            )
            return EnrichedLead(**lead.model_dump())

        # Verify emails if requested
        enrichments: list[EmailEnrichment] = []
        for email_data in domain_result.emails:
            if verify:
                try:
                    verify_result = await self.verify_email(
                        email=email_data.email,
                        correlation_id=correlation_id,
                    )
                    # Update verification status
                    email_data = EmailEnrichment(
                        **email_data.model_dump(),
                        verified=verify_result.result == "deliverable",
                        verified_at=datetime.now(timezone.utc),
                    )
                except APIError as e:
                    logger.debug(
                        "email_verification_failed",
                        email=email_data.email[:3] + "***" if email_data.email else None,
                        error=str(e),
                        correlation_id=correlation_id,
                    )
                    # Continue with unverified email

            enrichments.append(email_data)

        # Create enriched lead
        enriched = EnrichedLead(
            **lead.model_dump(),
            enrichments=enrichments,
            enriched_at=datetime.now(timezone.utc),
            enrichment_source="hunter",
            additional_emails=[e.email for e in enrichments if e.email],
        )

        # Set best email as primary if none exists
        if not enriched.email and enrichments:
            best = max(enrichments, key=lambda e: e.confidence)
            enriched.email = best.email

        logger.info(
            "lead_enriched",
            lead_id=lead.id,
            domain=domain,
            emails_found=len(enrichments),
            best_email=enriched.best_email[:3] + "***" if enriched.best_email else None,
            correlation_id=correlation_id,
        )

        return enriched

    async def enrich_leads_batch(
        self,
        leads: list[Lead],
        verify: bool = True,
        correlation_id: str | None = None,
    ) -> list[EnrichedLead]:
        """
        Enrich multiple leads with email data.

        Args:
            leads: List of leads to enrich
            verify: Whether to verify emails
            correlation_id: Request correlation ID

        Returns:
            List of EnrichedLeads
        """
        correlation_id = correlation_id or str(uuid4())
        results: list[EnrichedLead] = []

        for lead in leads:
            try:
                enriched = await self.enrich_lead(
                    lead=lead,
                    verify=verify,
                    correlation_id=correlation_id,
                )
                results.append(enriched)
            except Exception as e:
                logger.error(
                    "lead_enrichment_failed",
                    lead_id=lead.id,
                    error=str(e),
                    correlation_id=correlation_id,
                )
                # Add unenriched lead
                results.append(EnrichedLead(**lead.model_dump()))

        return results

    async def enrich_leads_concurrent(
        self,
        leads: list[Lead],
        concurrency_limit: int = 5,
        verify: bool = True,
        correlation_id: str | None = None,
    ) -> list[EnrichedLead]:
        """
        Enrich multiple leads with email data concurrently.

        This method provides significant performance improvements over sequential
        batch processing by processing multiple leads in parallel while respecting
        rate limits.

        Args:
            leads: List of leads to enrich
            concurrency_limit: Maximum number of concurrent requests (default: 5)
            verify: Whether to verify emails
            correlation_id: Request correlation ID

        Returns:
            List of EnrichedLeads (same order as input leads)
        """
        correlation_id = correlation_id or str(uuid4())
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def _enrich_with_semaphore(lead: Lead, index: int) -> tuple[int, EnrichedLead]:
            """Enrich a single lead with semaphore control."""
            async with semaphore:
                try:
                    enriched = await self.enrich_lead(
                        lead=lead,
                        verify=verify,
                        correlation_id=correlation_id,
                    )
                    return (index, enriched)
                except Exception as e:
                    logger.error(
                        "concurrent_lead_enrichment_failed",
                        lead_id=lead.id,
                        error=str(e),
                        correlation_id=correlation_id,
                    )
                    # Return unenriched lead on error
                    return (index, EnrichedLead(**lead.model_dump()))

        # Create tasks for all leads with their original indices
        tasks = [_enrich_with_semaphore(lead, idx) for idx, lead in enumerate(leads)]

        # Execute all tasks concurrently
        task_results = await asyncio.gather(*tasks, return_exceptions=False)

        # Sort results by original index to maintain order
        sorted_results = sorted(task_results, key=lambda x: x[0])
        results = [enriched for _, enriched in sorted_results]

        # Count successful enrichments
        enriched_count = sum(1 for lead in results if lead.enrichments)

        logger.info(
            "concurrent_lead_enrichment_completed",
            total_leads=len(leads),
            enriched=enriched_count,
            failed=len(leads) - enriched_count,
            concurrency_limit=concurrency_limit,
            correlation_id=correlation_id,
        )

        return results


# Factory function
async def create_hunter_service(api_key: str | None = None) -> HunterService:
    """Create and initialize a HunterService instance."""
    return HunterService(api_key=api_key)
