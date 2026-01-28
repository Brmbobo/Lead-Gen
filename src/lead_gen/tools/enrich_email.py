"""
Tool for enriching leads with email data.
"""

from __future__ import annotations

from dataclasses import dataclass

from lead_gen.core.gdpr import DataCategory, ProcessingPurpose
from lead_gen.models.lead import EnrichedLead, Lead
from lead_gen.models.workflow import EnrichConfig
from lead_gen.services.hunter_service import HunterService
from lead_gen.tools.base import BaseTool, ToolContext, ToolResult, ToolStatus


@dataclass
class EnrichInput:
    """Input for enrich email tool."""

    leads: list[Lead] | None = None
    config: EnrichConfig | None = None
    hunter_service: HunterService | None = None


class EnrichEmailTool(BaseTool[EnrichInput, list[EnrichedLead]]):
    """
    Tool for enriching leads with email addresses.

    Uses Hunter.io to find and verify business emails.

    Example:
        >>> tool = EnrichEmailTool()
        >>> config = EnrichConfig(find_emails=True, verify_emails=True)
        >>> result = await tool.run(EnrichInput(leads=leads, config=config), context)
    """

    name = "enrich_email"
    description = "Enrich leads with email addresses via Hunter.io"
    version = "1.0.0"
    processing_purpose = ProcessingPurpose.EMAIL_ENRICHMENT

    async def _execute(
        self,
        input_data: EnrichInput,
        context: ToolContext,
    ) -> ToolResult[list[EnrichedLead]]:
        """Execute email enrichment."""
        # Use leads from context if not provided
        leads = input_data.leads or context.leads

        if not leads:
            return ToolResult(
                status=ToolStatus.SKIPPED,
                output=[],
                error_message="No leads to enrich",
            )

        config = input_data.config or EnrichConfig()

        # Get or create service
        service = input_data.hunter_service
        if service is None:
            service = HunterService()

        enriched_leads: list[EnrichedLead] = []
        failed = 0
        emails_found = 0

        try:
            for lead in leads:
                try:
                    enriched = await service.enrich_lead(
                        lead=lead,
                        verify=config.verify_emails,
                        correlation_id=context.correlation_id,
                    )
                    enriched_leads.append(enriched)

                    # Track if email was found
                    if enriched.best_email:
                        emails_found += 1

                    # Add to context
                    context.add_enriched_lead(enriched)

                    # Record GDPR processing
                    if context.gdpr_manager and enriched.best_email:
                        context.gdpr_manager.record_processing(
                            purpose=ProcessingPurpose.EMAIL_ENRICHMENT,
                            data_categories=[
                                DataCategory.BUSINESS_EMAIL,
                                DataCategory.CONTACT_EMAIL,
                            ],
                            operation=f"Enriched email for: {lead.name}",
                            source="Hunter.io API",
                            data_subject_id=context.gdpr_manager.pseudonymize(lead.id),
                            correlation_id=context.correlation_id,
                        )

                except Exception as e:
                    self._logger.warning(
                        "lead_enrichment_failed",
                        lead_id=lead.id,
                        error=str(e),
                    )
                    # Add unenriched lead
                    enriched_leads.append(EnrichedLead(**lead.model_dump()))
                    failed += 1

            context.track_api_call()

            status = ToolStatus.SUCCESS if failed == 0 else ToolStatus.PARTIAL

            return ToolResult(
                status=status,
                output=enriched_leads,
                items_processed=len(enriched_leads),
                items_failed=failed,
                metadata={
                    "emails_found": emails_found,
                    "enrichment_rate": f"{(emails_found / len(leads) * 100):.1f}%" if leads else "0%",
                    "provider": config.provider,
                },
            )

        finally:
            if input_data.hunter_service is None and service:
                await service.close()

    def _validate_input(self, input_data: EnrichInput) -> str | None:
        """Validate enrich input."""
        # Leads can come from context, so no strict validation needed
        return None

    async def _dry_run(
        self,
        input_data: EnrichInput,
        context: ToolContext,
    ) -> ToolResult[list[EnrichedLead]]:
        """Dry run - show what would be enriched."""
        leads = input_data.leads or context.leads
        config = input_data.config or EnrichConfig()

        return ToolResult(
            status=ToolStatus.SKIPPED,
            output=[],
            metadata={
                "dry_run": True,
                "would_enrich": {
                    "lead_count": len(leads) if leads else 0,
                    "provider": config.provider,
                    "verify_emails": config.verify_emails,
                },
            },
        )
