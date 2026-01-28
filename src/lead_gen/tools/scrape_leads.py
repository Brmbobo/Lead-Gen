"""
Tool for scraping leads from Google Places API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from lead_gen.core.gdpr import DataCategory, ProcessingPurpose
from lead_gen.models.lead import Lead
from lead_gen.models.workflow import ScrapeConfig
from lead_gen.services.places_service import PlacesService
from lead_gen.tools.base import BaseTool, ToolContext, ToolResult, ToolStatus


@dataclass
class ScrapeInput:
    """Input for scrape leads tool."""

    config: ScrapeConfig
    places_service: PlacesService | None = None


class ScrapeLeadsTool(BaseTool[ScrapeInput, list[Lead]]):
    """
    Tool for scraping business leads from Google Places.

    Example:
        >>> tool = ScrapeLeadsTool()
        >>> config = ScrapeConfig(query="zubár", location="Bratislava")
        >>> result = await tool.run(ScrapeInput(config=config), context)
        >>> for lead in result.output:
        ...     print(lead.name)
    """

    name = "scrape_leads"
    description = "Scrape business leads from Google Places API"
    version = "1.0.0"
    processing_purpose = ProcessingPurpose.LEAD_GENERATION

    async def _execute(
        self,
        input_data: ScrapeInput,
        context: ToolContext,
    ) -> ToolResult[list[Lead]]:
        """Execute the scraping."""
        config = input_data.config

        # Get or create service
        service = input_data.places_service
        if service is None:
            service = PlacesService()

        try:
            # Search for places
            result = await service.search_text(
                query=config.query,
                location=config.location,
                radius_km=config.radius_km,
                max_results=config.max_results,
                language=config.language,
                region=config.region,
                min_rating=config.min_rating,
                open_now=config.open_now,
                included_types=config.business_types or None,
                correlation_id=context.correlation_id,
            )

            leads = result.places

            # Apply additional filters
            if config.min_reviews:
                leads = [l for l in leads if l.metrics.review_count >= config.min_reviews]

            # Record GDPR processing
            if context.gdpr_manager:
                for lead in leads:
                    context.gdpr_manager.record_processing(
                        purpose=ProcessingPurpose.LEAD_GENERATION,
                        data_categories=[
                            DataCategory.BUSINESS_NAME,
                            DataCategory.BUSINESS_ADDRESS,
                            DataCategory.BUSINESS_PHONE,
                            DataCategory.BUSINESS_WEBSITE,
                        ],
                        operation=f"Scraped lead: {lead.name}",
                        source="Google Places API",
                        data_subject_id=context.gdpr_manager.pseudonymize(lead.place_id),
                        correlation_id=context.correlation_id,
                    )

            # Add to context
            for lead in leads:
                context.add_lead(lead)

            # Track metrics
            context.track_api_call()

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=leads,
                items_processed=len(leads),
                metadata={
                    "query": config.query,
                    "location": config.location,
                    "api_response_time_ms": result.api_response_time_ms,
                },
            )

        finally:
            # Clean up service if we created it
            if input_data.places_service is None:
                await service.close()

    def _validate_input(self, input_data: ScrapeInput) -> str | None:
        """Validate scrape input."""
        if input_data is None:
            return "Input is required"
        if input_data.config is None:
            return "ScrapeConfig is required"
        if not input_data.config.query:
            return "Search query is required"
        return None

    async def _dry_run(
        self,
        input_data: ScrapeInput,
        context: ToolContext,
    ) -> ToolResult[list[Lead]]:
        """Dry run - show what would be scraped."""
        config = input_data.config

        return ToolResult(
            status=ToolStatus.SKIPPED,
            output=[],
            metadata={
                "dry_run": True,
                "would_search": {
                    "query": config.query,
                    "location": config.location,
                    "max_results": config.max_results,
                    "min_rating": config.min_rating,
                },
            },
        )
