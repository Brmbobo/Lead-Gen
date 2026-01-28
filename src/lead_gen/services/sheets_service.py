"""
Google Sheets service client for data export.

Provides async access to Google Sheets API for:
- Creating and updating spreadsheets
- Batch data export
- Formatting and styling

Uses service account authentication.
"""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from lead_gen.core.config import get_settings
from lead_gen.core.exceptions import APIError, ConfigurationError
from lead_gen.core.rate_limiter import RateLimitConfig, get_rate_limiter
from lead_gen.core.retry import CircuitBreaker, RetryConfig, retry_with_backoff
from lead_gen.models.lead import Lead, EnrichedLead
from lead_gen.models.outreach import OutreachMessage

logger = structlog.get_logger(__name__)


@dataclass
class ExportResult:
    """Result from a Sheets export operation."""

    spreadsheet_id: str
    worksheet_name: str
    rows_exported: int
    spreadsheet_url: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    export_time_ms: float = 0.0


class SheetsService:
    """
    Google Sheets service client.

    Provides methods for exporting leads and messages to Google Sheets.
    Uses service account authentication.

    Example:
        >>> service = SheetsService()
        >>> result = await service.export_leads(
        ...     leads=leads,
        ...     spreadsheet_id="your-spreadsheet-id",
        ... )
        >>> print(f"Exported {result.rows_exported} rows")
    """

    def __init__(
        self,
        service_account_path: str | Path | None = None,
        service_account_json: str | None = None,
    ) -> None:
        """
        Initialize Sheets service.

        Args:
            service_account_path: Path to service account JSON file
            service_account_json: Base64 encoded service account JSON
        """
        settings = get_settings()

        # Get credentials
        self._credentials = self._load_credentials(
            service_account_path or settings.google_service_account_path,
            service_account_json or settings.google_service_account_base64.get_secret_value(),
        )

        self._client: Any = None
        self._circuit_breaker = CircuitBreaker(service="sheets")

        # Configure rate limiter
        limiter = get_rate_limiter()
        limiter.add_service(
            "sheets",
            RateLimitConfig(requests_per_minute=settings.rate_limits.sheets),
        )

        logger.info("sheets_service_initialized")

    def _load_credentials(
        self,
        path: str | Path | None,
        base64_json: str | None,
    ) -> dict[str, Any]:
        """Load service account credentials."""
        # Try path first
        if path:
            path = Path(path)
            if path.exists():
                with open(path) as f:
                    return json.load(f)

        # Try base64
        if base64_json:
            try:
                decoded = base64.b64decode(base64_json)
                return json.loads(decoded)
            except Exception:
                # Maybe it's raw JSON
                try:
                    return json.loads(base64_json)
                except Exception:
                    pass

        raise ConfigurationError(
            "Google service account credentials not configured",
            config_key="GOOGLE_SERVICE_ACCOUNT_PATH or GOOGLE_SERVICE_ACCOUNT_BASE64",
        )

    def _get_client(self) -> Any:
        """Get or create gspread client."""
        if self._client is None:
            try:
                import gspread
                from google.oauth2.service_account import Credentials

                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]

                creds = Credentials.from_service_account_info(
                    self._credentials,
                    scopes=scopes,
                )

                self._client = gspread.authorize(creds)

            except ImportError:
                raise ConfigurationError(
                    "gspread package required. Install with: pip install gspread",
                    config_key="dependencies",
                )

        return self._client

    @retry_with_backoff(
        config=RetryConfig(max_retries=3, base_delay=2.0),
    )
    async def export_leads(
        self,
        leads: list[Lead | EnrichedLead],
        spreadsheet_id: str,
        worksheet_name: str = "Leads",
        append: bool = True,
        include_headers: bool = True,
        correlation_id: str | None = None,
    ) -> ExportResult:
        """
        Export leads to Google Sheets.

        Args:
            leads: List of leads to export
            spreadsheet_id: Target spreadsheet ID
            worksheet_name: Worksheet name (created if not exists)
            append: Append to existing data vs overwrite
            include_headers: Include header row
            correlation_id: Request correlation ID

        Returns:
            ExportResult with export details
        """
        correlation_id = correlation_id or str(uuid4())
        start_time = datetime.now(timezone.utc)

        if not leads:
            return ExportResult(
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                rows_exported=0,
                correlation_id=correlation_id,
            )

        # Rate limit
        limiter = get_rate_limiter()
        await limiter.acquire("sheets")

        # Run in thread pool to not block async loop
        def _export() -> tuple[int, str]:
            client = self._get_client()

            try:
                spreadsheet = client.open_by_key(spreadsheet_id)
            except Exception as e:
                raise APIError(
                    f"Failed to open spreadsheet: {e}",
                    service="sheets",
                    operation="open_spreadsheet",
                )

            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except Exception:
                # Create new worksheet
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=1000,
                    cols=20,
                )

            # Prepare data
            rows: list[list[Any]] = []

            # Headers
            headers = [
                "ID", "Name", "Phone", "Email", "Website", "Address",
                "City", "Country", "Rating", "Reviews", "Type",
                "Categories", "Status", "Quality Score", "Source",
                "Scraped At"
            ]

            # Check if we have enriched leads
            if leads and isinstance(leads[0], EnrichedLead):
                headers.extend(["Best Email", "Contact Person", "Email Confidence"])

            if include_headers and not append:
                rows.append(headers)

            # Data rows
            for lead in leads:
                row = [
                    lead.id,
                    lead.name,
                    lead.phone,
                    lead.email or "",
                    str(lead.website) if lead.website else "",
                    lead.location.formatted_address if lead.location else "",
                    lead.location.city if lead.location else "",
                    lead.location.country if lead.location else "",
                    lead.metrics.rating,
                    lead.metrics.review_count,
                    lead.business_type,
                    ", ".join(lead.categories),
                    lead.status.value,
                    lead.quality_score,
                    lead.source.value,
                    lead.scraped_at.isoformat(),
                ]

                if isinstance(lead, EnrichedLead):
                    row.extend([
                        lead.best_email or "",
                        lead.contact_person or "",
                        max((e.confidence for e in lead.enrichments), default=0),
                    ])

                rows.append(row)

            # Write to sheet
            if append:
                # Find first empty row
                values = worksheet.get_all_values()
                start_row = len(values) + 1

                # Add headers if sheet is empty
                if not values and include_headers:
                    worksheet.append_row(headers)
                    start_row = 2

                # Append data
                if rows:
                    worksheet.append_rows(rows)
            else:
                # Clear and write
                worksheet.clear()
                worksheet.update("A1", rows)

            # Format header row
            if include_headers:
                worksheet.format("1:1", {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                })

            return len(rows), spreadsheet.url

        async with self._circuit_breaker:
            try:
                rows_exported, spreadsheet_url = await asyncio.get_event_loop().run_in_executor(
                    None, _export
                )
            except Exception as e:
                raise APIError(
                    f"Failed to export to Sheets: {e}",
                    service="sheets",
                    operation="export_leads",
                    cause=e,
                )

        export_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        logger.info(
            "sheets_export_completed",
            spreadsheet_id=spreadsheet_id,
            worksheet=worksheet_name,
            rows=rows_exported,
            export_time_ms=export_time,
            correlation_id=correlation_id,
        )

        return ExportResult(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=worksheet_name,
            rows_exported=rows_exported,
            spreadsheet_url=spreadsheet_url,
            correlation_id=correlation_id,
            export_time_ms=export_time,
        )

    @retry_with_backoff(
        config=RetryConfig(max_retries=3, base_delay=2.0),
    )
    async def export_messages(
        self,
        messages: list[OutreachMessage],
        spreadsheet_id: str,
        worksheet_name: str = "Messages",
        append: bool = True,
        correlation_id: str | None = None,
    ) -> ExportResult:
        """
        Export generated messages to Google Sheets.

        Args:
            messages: List of messages to export
            spreadsheet_id: Target spreadsheet ID
            worksheet_name: Worksheet name
            append: Append vs overwrite
            correlation_id: Request correlation ID

        Returns:
            ExportResult with export details
        """
        correlation_id = correlation_id or str(uuid4())
        start_time = datetime.now(timezone.utc)

        if not messages:
            return ExportResult(
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                rows_exported=0,
                correlation_id=correlation_id,
            )

        limiter = get_rate_limiter()
        await limiter.acquire("sheets")

        def _export() -> tuple[int, str]:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)

            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except Exception:
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=1000,
                    cols=15,
                )

            headers = [
                "ID", "Lead ID", "Subject", "Body Preview", "Language",
                "Tone", "Type", "Word Count", "Generated At", "Model",
                "Tokens", "Cost USD"
            ]

            rows: list[list[Any]] = []

            if not append:
                rows.append(headers)

            for msg in messages:
                body_preview = msg.body[:200] + "..." if len(msg.body) > 200 else msg.body
                rows.append([
                    msg.id,
                    msg.lead_id,
                    msg.subject,
                    body_preview,
                    msg.language.value,
                    msg.tone.value,
                    msg.message_type.value,
                    msg.word_count,
                    msg.generated_at.isoformat(),
                    msg.generation_model,
                    msg.generation_tokens,
                    f"${msg.generation_cost_usd:.4f}",
                ])

            if append:
                values = worksheet.get_all_values()
                if not values:
                    worksheet.append_row(headers)
                worksheet.append_rows(rows)
            else:
                worksheet.clear()
                worksheet.update("A1", rows)

            return len(rows), spreadsheet.url

        async with self._circuit_breaker:
            try:
                rows_exported, spreadsheet_url = await asyncio.get_event_loop().run_in_executor(
                    None, _export
                )
            except Exception as e:
                raise APIError(
                    f"Failed to export messages to Sheets: {e}",
                    service="sheets",
                    operation="export_messages",
                    cause=e,
                )

        export_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        logger.info(
            "sheets_messages_export_completed",
            spreadsheet_id=spreadsheet_id,
            worksheet=worksheet_name,
            rows=rows_exported,
            export_time_ms=export_time,
            correlation_id=correlation_id,
        )

        return ExportResult(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=worksheet_name,
            rows_exported=rows_exported,
            spreadsheet_url=spreadsheet_url,
            correlation_id=correlation_id,
            export_time_ms=export_time,
        )

    async def create_spreadsheet(
        self,
        title: str,
        correlation_id: str | None = None,
    ) -> str:
        """
        Create a new spreadsheet.

        Args:
            title: Spreadsheet title
            correlation_id: Request correlation ID

        Returns:
            Spreadsheet ID
        """
        correlation_id = correlation_id or str(uuid4())

        limiter = get_rate_limiter()
        await limiter.acquire("sheets")

        def _create() -> str:
            client = self._get_client()
            spreadsheet = client.create(title)
            return spreadsheet.id

        async with self._circuit_breaker:
            try:
                spreadsheet_id = await asyncio.get_event_loop().run_in_executor(
                    None, _create
                )
            except Exception as e:
                raise APIError(
                    f"Failed to create spreadsheet: {e}",
                    service="sheets",
                    operation="create_spreadsheet",
                    cause=e,
                )

        logger.info(
            "spreadsheet_created",
            spreadsheet_id=spreadsheet_id,
            title=title,
            correlation_id=correlation_id,
        )

        return spreadsheet_id

    async def share_spreadsheet(
        self,
        spreadsheet_id: str,
        email: str,
        role: str = "reader",
        correlation_id: str | None = None,
    ) -> None:
        """
        Share spreadsheet with a user.

        Args:
            spreadsheet_id: Spreadsheet ID
            email: Email to share with
            role: Permission role (reader, writer, owner)
            correlation_id: Request correlation ID
        """
        correlation_id = correlation_id or str(uuid4())

        limiter = get_rate_limiter()
        await limiter.acquire("sheets")

        def _share() -> None:
            client = self._get_client()
            spreadsheet = client.open_by_key(spreadsheet_id)
            spreadsheet.share(email, perm_type="user", role=role)

        async with self._circuit_breaker:
            try:
                await asyncio.get_event_loop().run_in_executor(None, _share)
            except Exception as e:
                raise APIError(
                    f"Failed to share spreadsheet: {e}",
                    service="sheets",
                    operation="share_spreadsheet",
                    cause=e,
                )

        logger.info(
            "spreadsheet_shared",
            spreadsheet_id=spreadsheet_id,
            email=email,
            role=role,
            correlation_id=correlation_id,
        )


# Factory function
async def create_sheets_service(
    service_account_path: str | Path | None = None,
) -> SheetsService:
    """Create and initialize a SheetsService instance."""
    return SheetsService(service_account_path=service_account_path)
