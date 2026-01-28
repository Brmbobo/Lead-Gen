"""
OpenAI API service client for message generation.

Provides async access to OpenAI API for:
- Generating personalized outreach messages
- Message translation
- Content optimization

Rate limited with token tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import structlog
from openai import AsyncOpenAI, APIError as OpenAIAPIError, RateLimitError as OpenAIRateLimitError

from lead_gen.core.config import get_settings
from lead_gen.core.exceptions import APIError, ConfigurationError, RateLimitError, SecurityError
from lead_gen.core.rate_limiter import RateLimitConfig, get_rate_limiter
from lead_gen.core.retry import CircuitBreaker, RetryConfig, retry_with_backoff
from lead_gen.core.sanitization import sanitize_for_llm
from lead_gen.models.lead import Lead
from lead_gen.models.outreach import (
    MessageLanguage,
    MessageTone,
    MessageType,
    OutreachMessage,
    PersonalizationContext,
)

logger = structlog.get_logger(__name__)


# Pricing per 1M tokens (as of 2024)
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


@dataclass
class GenerationResult:
    """Result from message generation."""

    message: OutreachMessage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    generation_time_ms: float = 0.0
    model: str = "gpt-4o-mini"
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


class OpenAIService:
    """
    OpenAI API service client.

    Provides async methods for generating personalized outreach messages.
    Includes rate limiting, retry logic, and input sanitization.

    Example:
        >>> service = OpenAIService()
        >>> result = await service.generate_message(
        ...     lead=lead,
        ...     language=MessageLanguage.SLOVAK,
        ...     tone=MessageTone.PROFESSIONAL,
        ... )
        >>> print(result.message.subject)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        """
        Initialize OpenAI service.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Model to use (defaults to settings)
            max_tokens: Max tokens for generation (defaults to settings)
            temperature: Generation temperature (defaults to settings)
        """
        settings = get_settings()

        api_key = api_key or settings.get_openai_key()
        if not api_key:
            raise ConfigurationError(
                "OpenAI API key not configured",
                config_key="OPENAI_API_KEY",
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or settings.openai.model
        self.max_tokens = max_tokens or settings.openai.max_tokens
        self.temperature = temperature or settings.openai.temperature
        self._circuit_breaker = CircuitBreaker(service="openai")

        # Configure rate limiter
        limiter = get_rate_limiter()
        limiter.add_service(
            "openai",
            RateLimitConfig(requests_per_minute=settings.rate_limits.openai),
        )

        logger.info(
            "openai_service_initialized",
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

    @retry_with_backoff(
        config=RetryConfig(max_retries=3, base_delay=1.0),
    )
    async def generate_message(
        self,
        lead: Lead,
        language: MessageLanguage = MessageLanguage.SLOVAK,
        tone: MessageTone = MessageTone.PROFESSIONAL,
        message_type: MessageType = MessageType.COLD_EMAIL,
        value_proposition: str = "",
        sender_name: str = "",
        sender_company: str = "",
        custom_instructions: str = "",
        correlation_id: str | None = None,
    ) -> GenerationResult:
        """
        Generate a personalized outreach message for a lead.

        Args:
            lead: Lead to generate message for
            language: Target language
            tone: Message tone
            message_type: Type of message
            value_proposition: What value you're offering
            sender_name: Name of the sender
            sender_company: Company of the sender
            custom_instructions: Additional instructions for AI
            correlation_id: Request correlation ID

        Returns:
            GenerationResult with generated message
        """
        correlation_id = correlation_id or str(uuid4())
        start_time = datetime.now(timezone.utc)

        # Build personalization context
        context = PersonalizationContext(
            business_name=lead.name,
            business_type=lead.business_type,
            city=lead.location.city if lead.location else "",
            region=lead.location.region if lead.location else "",
            country=lead.location.country if lead.location else "",
            rating=lead.metrics.rating,
            review_count=lead.metrics.review_count,
            sender_name=sender_name,
            sender_company=sender_company,
            value_proposition=value_proposition,
        )

        # Build system prompt
        system_prompt = self._build_system_prompt(language, tone, message_type)

        # Build user prompt
        user_prompt = self._build_user_prompt(lead, context, custom_instructions)

        # Sanitize input for LLM safety
        sanitized = sanitize_for_llm(user_prompt, strict=True)
        if not sanitized.is_safe:
            raise SecurityError(
                "Potential prompt injection detected in lead data",
                threat_type="prompt_injection",
                operation="generate_message",
            )

        # Rate limit
        limiter = get_rate_limiter()
        await limiter.acquire("openai")

        # Make API call
        async with self._circuit_breaker:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": sanitized.sanitized},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

            except OpenAIRateLimitError as e:
                raise RateLimitError(
                    f"OpenAI rate limit exceeded: {e}",
                    service="openai",
                    retry_after_seconds=60,
                )
            except OpenAIAPIError as e:
                raise APIError(
                    f"OpenAI API error: {e}",
                    service="openai",
                    operation="generate_message",
                    status_code=getattr(e, "status_code", None),
                )

        # Parse response
        content = response.choices[0].message.content or ""
        subject, body = self._parse_response(content)

        # Calculate metrics
        generation_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost
        pricing = PRICING.get(self.model, PRICING["gpt-4o-mini"])
        cost = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000

        # Create message
        message = OutreachMessage(
            subject=subject,
            body=body,
            language=language,
            tone=tone,
            message_type=message_type,
            lead_id=lead.id,
            generation_model=self.model,
            generation_tokens=total_tokens,
            generation_cost_usd=cost,
            personalization_context=context,
            correlation_id=correlation_id,
        )

        logger.info(
            "message_generated",
            lead_id=lead.id,
            language=language.value,
            tone=tone.value,
            tokens=total_tokens,
            cost_usd=cost,
            generation_time_ms=generation_time,
            correlation_id=correlation_id,
        )

        return GenerationResult(
            message=message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            generation_time_ms=generation_time,
            model=self.model,
            correlation_id=correlation_id,
        )

    async def generate_messages_batch(
        self,
        leads: list[Lead],
        **kwargs: Any,
    ) -> list[GenerationResult]:
        """
        Generate messages for multiple leads.

        Args:
            leads: List of leads
            **kwargs: Arguments passed to generate_message

        Returns:
            List of GenerationResults
        """
        results = []
        for lead in leads:
            try:
                result = await self.generate_message(lead, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(
                    "message_generation_failed",
                    lead_id=lead.id,
                    error=str(e),
                )
                # Continue with other leads
                continue

        return results

    def _build_system_prompt(
        self,
        language: MessageLanguage,
        tone: MessageTone,
        message_type: MessageType,
    ) -> str:
        """Build the system prompt for message generation."""
        language_instructions = {
            MessageLanguage.SLOVAK: "Píš v slovenčine. Používaj správnu slovenčinu vrátane diakritiky.",
            MessageLanguage.CZECH: "Piš v češtině. Používej správnou češtinu včetně diakritiky.",
            MessageLanguage.GERMAN: "Schreibe auf Deutsch. Verwende korrektes Deutsch.",
            MessageLanguage.ENGLISH: "Write in English. Use proper English grammar.",
        }

        tone_instructions = {
            MessageTone.PROFESSIONAL: "Používaj profesionálny, vecný tón.",
            MessageTone.FRIENDLY: "Používaj priateľský, ale stále profesionálny tón.",
            MessageTone.CASUAL: "Používaj neformálny, uvoľnený tón.",
            MessageTone.FORMAL: "Používaj veľmi formálny, oficiálny tón.",
            MessageTone.ENTHUSIASTIC: "Používaj nadšený, energický tón.",
        }

        type_instructions = {
            MessageType.COLD_EMAIL: "Toto je prvý kontakt. Buď stručný a zaujímavý.",
            MessageType.FOLLOW_UP: "Toto je follow-up email. Odvolávaj sa na predchádzajúci kontakt.",
            MessageType.INTRODUCTION: "Toto je úvodný email. Predstav sa a svoju spoločnosť.",
            MessageType.PARTNERSHIP: "Toto je návrh na spoluprácu. Zdôrazni obojstranné výhody.",
            MessageType.FEEDBACK_REQUEST: "Toto je žiadosť o spätnú väzbu. Buď zdvorilý a konkrétny.",
        }

        return f"""Si profesionálny copywriter špecializujúci sa na B2B outreach emaily.

{language_instructions.get(language, language_instructions[MessageLanguage.SLOVAK])}
{tone_instructions.get(tone, tone_instructions[MessageTone.PROFESSIONAL])}
{type_instructions.get(message_type, type_instructions[MessageType.COLD_EMAIL])}

Pravidlá:
1. Vygeneruj SUBJECT: a BODY: presne v tomto formáte
2. Subject má byť krátky (max 60 znakov)
3. Body má byť stručné (max 150 slov)
4. Personalizuj pomocou názvu firmy a ďalších dostupných údajov
5. Zakonči jasnou výzvou k akcii (CTA)
6. NIKDY nepoužívaj placeholder text ako [Your Name] alebo {{variable}}
7. Nepoužívaj emotikony ani špeciálne znaky
8. Buď autentický, nie predajný"""

    def _build_user_prompt(
        self,
        lead: Lead,
        context: PersonalizationContext,
        custom_instructions: str = "",
    ) -> str:
        """Build the user prompt for message generation."""
        parts = [
            f"Vygeneruj personalizovaný outreach email pre túto firmu:",
            f"",
            f"FIRMA: {lead.name}",
        ]

        if lead.business_type:
            parts.append(f"TYP: {lead.business_type}")

        if lead.location:
            if lead.location.city:
                parts.append(f"MESTO: {lead.location.city}")
            if lead.location.formatted_address:
                parts.append(f"ADRESA: {lead.location.formatted_address}")

        if lead.metrics.rating:
            parts.append(f"HODNOTENIE: {lead.metrics.rating}/5 ({lead.metrics.review_count} recenzií)")

        if lead.website:
            parts.append(f"WEB: {lead.website}")

        parts.append("")

        if context.value_proposition:
            parts.append(f"HODNOTA KTORÚ PONÚKAM: {context.value_proposition}")

        if context.sender_name:
            parts.append(f"ODOSIELATEĽ: {context.sender_name}")
            if context.sender_company:
                parts.append(f"SPOLOČNOSŤ: {context.sender_company}")

        if custom_instructions:
            parts.append("")
            parts.append(f"DODATOČNÉ INŠTRUKCIE: {custom_instructions}")

        parts.append("")
        parts.append("Vygeneruj email vo formáte:")
        parts.append("SUBJECT: <predmet>")
        parts.append("BODY: <telo emailu>")

        return "\n".join(parts)

    def _parse_response(self, content: str) -> tuple[str, str]:
        """Parse AI response into subject and body."""
        subject = ""
        body = ""

        lines = content.strip().split("\n")

        in_body = False
        body_lines = []

        for line in lines:
            if line.upper().startswith("SUBJECT:"):
                subject = line[8:].strip()
            elif line.upper().startswith("BODY:"):
                in_body = True
                body_lines.append(line[5:].strip())
            elif in_body:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        # Fallback if format not followed
        if not subject or not body:
            # Try to extract from unformatted response
            if not subject:
                subject = lines[0][:60] if lines else "Spolupráca"
            if not body:
                body = content

        return subject, body

    async def translate_message(
        self,
        message: OutreachMessage,
        target_language: MessageLanguage,
        correlation_id: str | None = None,
    ) -> OutreachMessage:
        """
        Translate an existing message to another language.

        Args:
            message: Message to translate
            target_language: Target language
            correlation_id: Request correlation ID

        Returns:
            New OutreachMessage with translated content
        """
        correlation_id = correlation_id or str(uuid4())

        language_names = {
            MessageLanguage.SLOVAK: "slovenčina",
            MessageLanguage.CZECH: "čeština",
            MessageLanguage.GERMAN: "nemčina",
            MessageLanguage.ENGLISH: "angličtina",
        }

        prompt = f"""Prelož tento email do jazyka: {language_names.get(target_language, 'slovenčina')}

SUBJECT: {message.subject}
BODY: {message.body}

Zachovaj profesionálny tón a štruktúru. Výstup vo formáte:
SUBJECT: <preložený predmet>
BODY: <preložené telo>"""

        limiter = get_rate_limiter()
        await limiter.acquire("openai")

        async with self._circuit_breaker:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for translation
            )

        content = response.choices[0].message.content or ""
        subject, body = self._parse_response(content)

        return OutreachMessage(
            subject=subject,
            body=body,
            language=target_language,
            tone=message.tone,
            message_type=message.message_type,
            lead_id=message.lead_id,
            template_id=message.template_id,
            generation_model=self.model,
            personalization_context=message.personalization_context,
            correlation_id=correlation_id,
        )


# Factory function
async def create_openai_service(api_key: str | None = None) -> OpenAIService:
    """Create and initialize an OpenAIService instance."""
    return OpenAIService(api_key=api_key)
