"""
Base workflow orchestration.

Provides:
- BaseWorkflow abstract class
- WorkflowRunner for executing workflows
- Step execution and error handling
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import structlog

from lead_gen.core.exceptions import WorkflowError
from lead_gen.models.workflow import (
    StepType,
    WorkflowConfig,
    WorkflowStatus,
    WorkflowStep,
)
from lead_gen.tools.base import ToolContext, ToolResult, ToolStatus

logger = structlog.get_logger(__name__)


class BaseWorkflow(ABC):
    """
    Base class for workflows.

    Provides the structure for defining and executing workflows.

    Example:
        >>> class MyWorkflow(BaseWorkflow):
        ...     async def execute_step(self, step, context):
        ...         # Implementation
        ...         pass
    """

    def __init__(self, config: WorkflowConfig) -> None:
        """Initialize workflow with configuration."""
        self.config = config
        self._logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    async def execute_step(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult[Any]:
        """
        Execute a single workflow step.

        Args:
            step: Step configuration
            context: Execution context

        Returns:
            ToolResult from step execution
        """
        ...

    async def run(self, context: ToolContext | None = None) -> WorkflowConfig:
        """
        Run the complete workflow.

        Args:
            context: Execution context (created if not provided)

        Returns:
            Updated WorkflowConfig with execution results
        """
        context = context or ToolContext()

        self.config.status = WorkflowStatus.RUNNING
        self.config.started_at = datetime.now(timezone.utc)
        self.config.current_step_index = 0

        self._logger.info(
            "workflow_started",
            workflow=self.config.name,
            steps=self.config.total_steps,
            dry_run=context.dry_run,
            correlation_id=context.correlation_id,
        )

        try:
            for i, step in enumerate(self.config.enabled_steps):
                self.config.current_step_index = i

                # Check if workflow should continue
                if self.config.status == WorkflowStatus.CANCELLED:
                    break

                # Execute step
                step.status = WorkflowStatus.RUNNING
                step.started_at = datetime.now(timezone.utc)

                try:
                    result = await self.execute_step(step, context)

                    step.completed_at = datetime.now(timezone.utc)
                    step.output_count = result.items_processed

                    if result.status == ToolStatus.SUCCESS:
                        step.status = WorkflowStatus.COMPLETED
                    elif result.status == ToolStatus.PARTIAL:
                        step.status = WorkflowStatus.COMPLETED
                        step.error_message = result.error_message
                    elif result.status == ToolStatus.SKIPPED:
                        step.status = WorkflowStatus.COMPLETED
                    else:
                        step.status = WorkflowStatus.FAILED
                        step.error_message = result.error_message

                        if self.config.stop_on_error and not step.skip_on_error:
                            raise WorkflowError(
                                f"Step '{step.name}' failed: {result.error_message}",
                                workflow_name=self.config.name,
                                step_name=step.name,
                                step_index=i,
                            )

                except Exception as e:
                    step.status = WorkflowStatus.FAILED
                    step.completed_at = datetime.now(timezone.utc)
                    step.error_message = str(e)

                    if self.config.stop_on_error and not step.skip_on_error:
                        raise

                self._logger.info(
                    "step_completed",
                    workflow=self.config.name,
                    step=step.name,
                    status=step.status.value,
                    items_processed=step.output_count,
                    duration_seconds=step.duration_seconds,
                )

            # Mark workflow complete
            self.config.status = WorkflowStatus.COMPLETED
            self.config.completed_at = datetime.now(timezone.utc)
            self.config.total_leads_processed = len(context.leads) + len(context.enriched_leads)

        except Exception as e:
            self.config.status = WorkflowStatus.FAILED
            self.config.completed_at = datetime.now(timezone.utc)
            self.config.error_message = str(e)

            self._logger.error(
                "workflow_failed",
                workflow=self.config.name,
                error=str(e),
                correlation_id=context.correlation_id,
            )

            raise

        self._logger.info(
            "workflow_completed",
            workflow=self.config.name,
            status=self.config.status.value,
            leads_processed=self.config.total_leads_processed,
            elapsed_seconds=context.elapsed_seconds,
            api_calls=context.api_calls,
            tokens_used=context.tokens_used,
            cost_usd=context.cost_usd,
            correlation_id=context.correlation_id,
        )

        return self.config


class WorkflowRunner:
    """
    Utility class for running workflows from configuration.

    Example:
        >>> runner = WorkflowRunner()
        >>> config = WorkflowConfig.from_yaml("workflow.yaml")
        >>> result = await runner.run(config)
    """

    def __init__(self) -> None:
        self._logger = structlog.get_logger(__name__)

    async def run(
        self,
        config: WorkflowConfig,
        context: ToolContext | None = None,
    ) -> WorkflowConfig:
        """
        Run a workflow from configuration.

        Automatically selects the appropriate workflow class.

        Args:
            config: Workflow configuration
            context: Execution context

        Returns:
            Updated configuration with results
        """
        # Validate configuration
        errors = config.validate_workflow()
        if errors:
            raise WorkflowError(
                f"Invalid workflow configuration: {', '.join(errors)}",
                workflow_name=config.name,
            )

        # Import here to avoid circular imports
        from lead_gen.workflows.lead_generation import LeadGenWorkflow

        # Create and run workflow
        workflow = LeadGenWorkflow(config)
        return await workflow.run(context)

    async def run_from_yaml(
        self,
        yaml_path: str,
        context: ToolContext | None = None,
    ) -> WorkflowConfig:
        """
        Run a workflow from YAML file.

        Args:
            yaml_path: Path to YAML configuration
            context: Execution context

        Returns:
            Updated configuration with results
        """
        config = WorkflowConfig.from_yaml(yaml_path)
        return await self.run(config, context)
