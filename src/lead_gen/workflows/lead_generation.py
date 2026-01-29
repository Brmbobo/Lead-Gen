"""
Lead generation workflow implementation.

Main workflow that orchestrates:
1. Scraping leads from Google Places
2. Filtering leads by quality
3. Enriching leads with emails
4. Generating outreach messages
5. Exporting to Google Sheets
"""

from __future__ import annotations

from typing import Any

import structlog

from lead_gen.models.workflow import (
    StepType,
    WorkflowConfig,
    WorkflowStep,
)
from lead_gen.services.hunter_service import HunterService
from lead_gen.services.openai_service import OpenAIService
from lead_gen.services.places_service import PlacesService
from lead_gen.services.sheets_service import SheetsService
from lead_gen.tools.base import ToolContext, ToolResult, ToolStatus
from lead_gen.tools.enrich_email import EnrichEmailTool, EnrichInput
from lead_gen.tools.export_to_sheets import ExportInput, ExportToSheetsTool
from lead_gen.tools.generate_outreach import GenerateInput, GenerateOutreachTool
from lead_gen.tools.scrape_leads import ScrapeInput, ScrapeLeadsTool
from lead_gen.workflows.base import BaseWorkflow

logger = structlog.get_logger(__name__)


class LeadGenWorkflow(BaseWorkflow):
    """
    Main lead generation workflow.

    Orchestrates the complete lead generation pipeline from
    scraping to export.

    Example:
        >>> config = WorkflowConfig.from_yaml("workflows/slovakia_dentists.yaml")
        >>> workflow = LeadGenWorkflow(config)
        >>> result = await workflow.run()
    """

    def __init__(self, config: WorkflowConfig) -> None:
        """Initialize the workflow."""
        super().__init__(config)

        # Services (lazy initialized)
        self._places_service: PlacesService | None = None
        self._openai_service: OpenAIService | None = None
        self._sheets_service: SheetsService | None = None
        self._hunter_service: HunterService | None = None

        # Tools
        self._scrape_tool = ScrapeLeadsTool()
        self._generate_tool = GenerateOutreachTool()
        self._export_tool = ExportToSheetsTool()
        self._enrich_tool = EnrichEmailTool()

    async def execute_step(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """Execute a workflow step based on its type."""
        self._logger.debug(
            "executing_step",
            step_name=step.name,
            step_type=step.type.value,
        )

        if step.type == StepType.SCRAPE:
            return await self._execute_scrape(step, context)
        elif step.type == StepType.FILTER:
            return await self._execute_filter(step, context)
        elif step.type == StepType.ENRICH:
            return await self._execute_enrich(step, context)
        elif step.type == StepType.GENERATE:
            return await self._execute_generate(step, context)
        elif step.type == StepType.EXPORT:
            return await self._execute_export(step, context)
        else:
            return ToolResult(
                status=ToolStatus.SKIPPED,
                error_message=f"Unknown step type: {step.type}",
            )

    async def _execute_scrape(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """Execute a scrape step."""
        if not step.scrape_config:
            return ToolResult(
                status=ToolStatus.FAILED,
                error_message="Scrape config missing",
            )

        # Initialize service if needed
        if self._places_service is None:
            self._places_service = PlacesService()

        input_data = ScrapeInput(
            config=step.scrape_config,
            places_service=self._places_service,
        )

        return await self._scrape_tool.run(input_data, context)

    async def _execute_filter(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """Execute a filter step."""
        if not step.filter_config:
            return ToolResult(
                status=ToolStatus.FAILED,
                error_message="Filter config missing",
            )

        config = step.filter_config
        original_count = len(context.leads)
        filtered_leads = []

        for lead in context.leads:
            # Quality score filter
            if config.min_quality_score and lead.quality_score < config.min_quality_score:
                continue

            # Required fields filter
            if config.required_fields:
                has_all = True
                for field in config.required_fields:
                    if not getattr(lead, field, None):
                        has_all = False
                        break
                if not has_all:
                    continue

            # Status filter
            if config.include_statuses and lead.status.value not in config.include_statuses:
                continue
            if config.exclude_statuses and lead.status.value in config.exclude_statuses:
                continue

            filtered_leads.append(lead)

        # Deduplication
        if config.deduplicate_by:
            seen = set()
            deduped = []
            for lead in filtered_leads:
                key = getattr(lead, config.deduplicate_by, None)
                if key and key not in seen:
                    seen.add(key)
                    deduped.append(lead)
            filtered_leads = deduped

        # Update context - clear and re-add filtered leads
        context._leads.clear()
        for lead in filtered_leads:
            context.add_lead(lead)
        filtered_count = original_count - len(filtered_leads)

        self._logger.info(
            "leads_filtered",
            original=original_count,
            remaining=len(filtered_leads),
            filtered_out=filtered_count,
        )

        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=filtered_leads,
            items_processed=len(filtered_leads),
            items_failed=filtered_count,
            metadata={
                "original_count": original_count,
                "filtered_count": filtered_count,
                "remaining_count": len(filtered_leads),
            },
        )

    async def _execute_enrich(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """Execute an enrich step."""
        if not step.enrich_config:
            return ToolResult(
                status=ToolStatus.FAILED,
                error_message="Enrich config missing",
            )

        # Initialize service if needed
        if step.enrich_config.provider == "hunter":
            if self._hunter_service is None:
                try:
                    self._hunter_service = HunterService()
                except Exception as e:
                    self._logger.warning(
                        "hunter_service_init_failed",
                        error=str(e),
                    )
                    # Return leads as-is without enrichment
                    return ToolResult(
                        status=ToolStatus.PARTIAL,
                        output=context.leads,
                        items_processed=len(context.leads),
                        error_message=f"Hunter service unavailable: {e}",
                    )

        input_data = EnrichInput(
            leads=context.leads,
            config=step.enrich_config,
            hunter_service=self._hunter_service,
        )

        return await self._enrich_tool.run(input_data, context)

    async def _execute_generate(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """Execute a generate step."""
        if not step.generate_config:
            return ToolResult(
                status=ToolStatus.FAILED,
                error_message="Generate config missing",
            )

        # Initialize service if needed
        if self._openai_service is None:
            self._openai_service = OpenAIService(
                model=step.generate_config.model,
                max_tokens=step.generate_config.max_tokens,
                temperature=step.generate_config.temperature,
            )

        # Use enriched leads if available, otherwise regular leads
        leads = context.enriched_leads if context.enriched_leads else context.leads

        input_data = GenerateInput(
            leads=leads,
            config=step.generate_config,
            openai_service=self._openai_service,
        )

        return await self._generate_tool.run(input_data, context)

    async def _execute_export(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """Execute an export step."""
        if not step.export_config:
            return ToolResult(
                status=ToolStatus.FAILED,
                error_message="Export config missing",
            )

        # Initialize service if needed
        if self._sheets_service is None:
            try:
                self._sheets_service = SheetsService()
            except Exception as e:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error_message=f"Sheets service unavailable: {e}",
                )

        # Use enriched leads if available
        leads = context.enriched_leads if context.enriched_leads else context.leads

        input_data = ExportInput(
            config=step.export_config,
            leads=leads,
            messages=context.messages,
            sheets_service=self._sheets_service,
        )

        return await self._export_tool.run(input_data, context)

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._places_service:
            await self._places_service.close()
        if self._hunter_service:
            await self._hunter_service.close()
