"""
Tool for exporting data to Google Sheets.
"""

from __future__ import annotations

from dataclasses import dataclass

from lead_gen.core.gdpr import DataCategory, ProcessingPurpose
from lead_gen.models.lead import EnrichedLead, Lead
from lead_gen.models.outreach import OutreachMessage
from lead_gen.models.workflow import ExportConfig
from lead_gen.services.sheets_service import ExportResult, SheetsService
from lead_gen.tools.base import BaseTool, ToolContext, ToolResult, ToolStatus


@dataclass
class ExportInput:
    """Input for export to sheets tool."""

    config: ExportConfig
    leads: list[Lead | EnrichedLead] | None = None
    messages: list[OutreachMessage] | None = None
    sheets_service: SheetsService | None = None


@dataclass
class ExportOutput:
    """Output from export tool."""

    leads_result: ExportResult | None = None
    messages_result: ExportResult | None = None
    spreadsheet_url: str = ""


class ExportToSheetsTool(BaseTool[ExportInput, ExportOutput]):
    """
    Tool for exporting leads and messages to Google Sheets.

    Example:
        >>> tool = ExportToSheetsTool()
        >>> config = ExportConfig(
        ...     spreadsheet_id="your-id",
        ...     worksheet_name="Leads",
        ... )
        >>> result = await tool.run(ExportInput(config=config, leads=leads), context)
    """

    name = "export_to_sheets"
    description = "Export leads and messages to Google Sheets"
    version = "1.0.0"
    processing_purpose = ProcessingPurpose.EXPORT

    async def _execute(
        self,
        input_data: ExportInput,
        context: ToolContext,
    ) -> ToolResult[ExportOutput]:
        """Execute export to sheets."""
        config = input_data.config

        # Use data from context if not provided
        leads = input_data.leads or context.leads or context.enriched_leads
        messages = input_data.messages or context.messages

        if not leads and not messages:
            return ToolResult(
                status=ToolStatus.SKIPPED,
                output=ExportOutput(),
                error_message="No data to export",
            )

        # Get or create service
        service = input_data.sheets_service
        if service is None:
            service = SheetsService()

        output = ExportOutput()
        total_exported = 0

        # Export leads
        if leads:
            leads_result = await service.export_leads(
                leads=leads,
                spreadsheet_id=config.spreadsheet_id,
                worksheet_name=config.worksheet_name,
                append=config.append_mode,
                correlation_id=context.correlation_id,
            )
            output.leads_result = leads_result
            output.spreadsheet_url = leads_result.spreadsheet_url
            total_exported += leads_result.rows_exported

            # Record GDPR processing
            if context.gdpr_manager:
                context.gdpr_manager.record_processing(
                    purpose=ProcessingPurpose.EXPORT,
                    data_categories=[
                        DataCategory.BUSINESS_NAME,
                        DataCategory.BUSINESS_ADDRESS,
                        DataCategory.BUSINESS_PHONE,
                        DataCategory.BUSINESS_EMAIL,
                    ],
                    operation=f"Exported {leads_result.rows_exported} leads to Google Sheets",
                    source="Lead-Gen",
                    correlation_id=context.correlation_id,
                )

        # Export messages
        if messages and config.include_messages:
            messages_worksheet = f"{config.worksheet_name} - Messages"
            messages_result = await service.export_messages(
                messages=messages,
                spreadsheet_id=config.spreadsheet_id,
                worksheet_name=messages_worksheet,
                append=config.append_mode,
                correlation_id=context.correlation_id,
            )
            output.messages_result = messages_result
            if not output.spreadsheet_url:
                output.spreadsheet_url = messages_result.spreadsheet_url
            total_exported += messages_result.rows_exported

        context.track_api_call()

        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output,
            items_processed=total_exported,
            metadata={
                "spreadsheet_id": config.spreadsheet_id,
                "leads_exported": output.leads_result.rows_exported if output.leads_result else 0,
                "messages_exported": output.messages_result.rows_exported if output.messages_result else 0,
                "spreadsheet_url": output.spreadsheet_url,
            },
        )

    def _validate_input(self, input_data: ExportInput) -> str | None:
        """Validate export input."""
        if input_data is None:
            return "Input is required"
        if input_data.config is None:
            return "ExportConfig is required"
        if input_data.config.destination == "sheets" and not input_data.config.spreadsheet_id:
            return "spreadsheet_id is required for sheets export"
        return None

    async def _dry_run(
        self,
        input_data: ExportInput,
        context: ToolContext,
    ) -> ToolResult[ExportOutput]:
        """Dry run - show what would be exported."""
        leads = input_data.leads or context.leads or context.enriched_leads
        messages = input_data.messages or context.messages
        config = input_data.config

        return ToolResult(
            status=ToolStatus.SKIPPED,
            output=ExportOutput(),
            metadata={
                "dry_run": True,
                "would_export": {
                    "leads_count": len(leads) if leads else 0,
                    "messages_count": len(messages) if messages else 0,
                    "spreadsheet_id": config.spreadsheet_id,
                    "worksheet": config.worksheet_name,
                },
            },
        )
