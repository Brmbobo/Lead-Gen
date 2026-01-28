"""
Tool for generating AI-powered outreach messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lead_gen.core.gdpr import DataCategory, ProcessingPurpose
from lead_gen.models.lead import Lead
from lead_gen.models.outreach import MessageLanguage, MessageTone, MessageType, OutreachMessage
from lead_gen.models.workflow import GenerateConfig
from lead_gen.services.openai_service import OpenAIService
from lead_gen.tools.base import BaseTool, ToolContext, ToolResult, ToolStatus


@dataclass
class GenerateInput:
    """Input for generate outreach tool."""

    leads: list[Lead]
    config: GenerateConfig
    openai_service: OpenAIService | None = None


class GenerateOutreachTool(BaseTool[GenerateInput, list[OutreachMessage]]):
    """
    Tool for generating personalized outreach messages.

    Uses OpenAI to generate contextual messages for each lead.

    Example:
        >>> tool = GenerateOutreachTool()
        >>> config = GenerateConfig(
        ...     language="sk",
        ...     tone="professional",
        ...     value_proposition="Pomáhame získať viac pacientov",
        ... )
        >>> result = await tool.run(GenerateInput(leads=leads, config=config), context)
    """

    name = "generate_outreach"
    description = "Generate AI-powered outreach messages"
    version = "1.0.0"
    processing_purpose = ProcessingPurpose.OUTREACH

    async def _execute(
        self,
        input_data: GenerateInput,
        context: ToolContext,
    ) -> ToolResult[list[OutreachMessage]]:
        """Execute message generation."""
        leads = input_data.leads
        config = input_data.config

        # Use leads from context if not provided
        if not leads and context.leads:
            leads = context.leads

        if not leads:
            return ToolResult(
                status=ToolStatus.SKIPPED,
                output=[],
                error_message="No leads to generate messages for",
            )

        # Get or create service
        service = input_data.openai_service
        if service is None:
            service = OpenAIService(
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
            )

        messages: list[OutreachMessage] = []
        failed = 0
        total_tokens = 0
        total_cost = 0.0

        try:
            for lead in leads:
                try:
                    result = await service.generate_message(
                        lead=lead,
                        language=MessageLanguage(config.language),
                        tone=MessageTone(config.tone),
                        message_type=MessageType.COLD_EMAIL,
                        value_proposition=config.value_proposition,
                        sender_name=config.sender_name,
                        sender_company=config.sender_company,
                        correlation_id=context.correlation_id,
                    )

                    messages.append(result.message)
                    total_tokens += result.total_tokens
                    total_cost += result.cost_usd

                    # Add to context
                    context.add_message(result.message)

                    # Record GDPR processing
                    if context.gdpr_manager:
                        context.gdpr_manager.record_processing(
                            purpose=ProcessingPurpose.OUTREACH,
                            data_categories=[
                                DataCategory.BUSINESS_NAME,
                                DataCategory.BUSINESS_ADDRESS,
                            ],
                            operation=f"Generated outreach for: {lead.name}",
                            source="OpenAI API",
                            data_subject_id=context.gdpr_manager.pseudonymize(lead.id),
                            correlation_id=context.correlation_id,
                        )

                except Exception as e:
                    self._logger.warning(
                        "message_generation_failed",
                        lead_id=lead.id,
                        error=str(e),
                    )
                    failed += 1

            # Track metrics
            context.track_api_call(tokens=total_tokens, cost=total_cost)

            status = ToolStatus.SUCCESS if failed == 0 else ToolStatus.PARTIAL

            return ToolResult(
                status=status,
                output=messages,
                items_processed=len(messages),
                items_failed=failed,
                metadata={
                    "model": config.model,
                    "total_tokens": total_tokens,
                    "total_cost_usd": total_cost,
                    "language": config.language,
                    "tone": config.tone,
                },
            )

        finally:
            pass  # Service cleanup handled by caller if needed

    def _validate_input(self, input_data: GenerateInput) -> str | None:
        """Validate generate input."""
        if input_data is None:
            return "Input is required"
        if input_data.config is None:
            return "GenerateConfig is required"
        return None

    async def _dry_run(
        self,
        input_data: GenerateInput,
        context: ToolContext,
    ) -> ToolResult[list[OutreachMessage]]:
        """Dry run - show what would be generated."""
        leads = input_data.leads or context.leads
        config = input_data.config

        return ToolResult(
            status=ToolStatus.SKIPPED,
            output=[],
            metadata={
                "dry_run": True,
                "would_generate": {
                    "lead_count": len(leads),
                    "model": config.model,
                    "language": config.language,
                    "tone": config.tone,
                },
            },
        )
