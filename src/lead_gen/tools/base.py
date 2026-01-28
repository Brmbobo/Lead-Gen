"""
Base tool abstraction for Lead-Gen.

Provides a consistent interface for all tools with:
- Input/output validation
- Error handling
- Logging and metrics
- GDPR compliance tracking
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import uuid4

import structlog

from lead_gen.core.gdpr import GDPRManager, ProcessingPurpose, get_gdpr_manager

logger = structlog.get_logger(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ToolStatus(str, Enum):
    """Tool execution status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ToolContext:
    """
    Context passed to tool execution.

    Contains shared state and configuration for the workflow.
    """

    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    dry_run: bool = False
    gdpr_manager: GDPRManager | None = None

    # Shared data between tools
    leads: list[Any] = field(default_factory=list)
    messages: list[Any] = field(default_factory=list)
    enriched_leads: list[Any] = field(default_factory=list)

    # Metrics
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    api_calls: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.gdpr_manager is None:
            self.gdpr_manager = get_gdpr_manager()

    def add_lead(self, lead: Any) -> None:
        """Add a lead to context."""
        self.leads.append(lead)

    def add_message(self, message: Any) -> None:
        """Add a message to context."""
        self.messages.append(message)

    def add_enriched_lead(self, lead: Any) -> None:
        """Add an enriched lead to context."""
        self.enriched_leads.append(lead)

    def track_api_call(self, tokens: int = 0, cost: float = 0.0) -> None:
        """Track an API call."""
        self.api_calls += 1
        self.tokens_used += tokens
        self.cost_usd += cost

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since start."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


@dataclass
class ToolResult(Generic[OutputT]):
    """
    Result from tool execution.

    Contains output data, status, and metrics.
    """

    status: ToolStatus
    output: OutputT | None = None
    error_message: str = ""
    items_processed: int = 0
    items_failed: int = 0
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if tool completed successfully."""
        return self.status in (ToolStatus.SUCCESS, ToolStatus.PARTIAL)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.items_processed + self.items_failed
        if total == 0:
            return 0.0
        return self.items_processed / total * 100


class BaseTool(ABC, Generic[InputT, OutputT]):
    """
    Base class for all tools.

    Provides:
    - Consistent execution interface
    - Input/output validation
    - Error handling and logging
    - GDPR compliance tracking

    Example:
        >>> class MyTool(BaseTool[MyInput, MyOutput]):
        ...     name = "my_tool"
        ...     description = "Does something useful"
        ...
        ...     async def _execute(self, input_data, context):
        ...         # Implementation
        ...         return ToolResult(status=ToolStatus.SUCCESS, output=result)
    """

    # Tool metadata (override in subclasses)
    name: str = "base_tool"
    description: str = "Base tool"
    version: str = "1.0.0"

    # GDPR
    processing_purpose: ProcessingPurpose = ProcessingPurpose.LEAD_GENERATION

    def __init__(self) -> None:
        """Initialize the tool."""
        self._logger = structlog.get_logger(self.name)

    async def run(
        self,
        input_data: InputT,
        context: ToolContext | None = None,
    ) -> ToolResult[OutputT]:
        """
        Execute the tool.

        Args:
            input_data: Tool-specific input data
            context: Execution context (created if not provided)

        Returns:
            ToolResult with output and status
        """
        context = context or ToolContext()
        start_time = datetime.now(timezone.utc)

        self._logger.info(
            "tool_started",
            tool=self.name,
            correlation_id=context.correlation_id,
            dry_run=context.dry_run,
        )

        try:
            # Validate input
            validation_error = self._validate_input(input_data)
            if validation_error:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error_message=f"Input validation failed: {validation_error}",
                )

            # Execute
            if context.dry_run:
                result = await self._dry_run(input_data, context)
            else:
                result = await self._execute(input_data, context)

            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time

            self._logger.info(
                "tool_completed",
                tool=self.name,
                status=result.status.value,
                items_processed=result.items_processed,
                items_failed=result.items_failed,
                execution_time_ms=execution_time,
                correlation_id=context.correlation_id,
            )

            return result

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            self._logger.error(
                "tool_failed",
                tool=self.name,
                error=str(e),
                error_type=type(e).__name__,
                execution_time_ms=execution_time,
                correlation_id=context.correlation_id,
            )

            return ToolResult(
                status=ToolStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time,
            )

    @abstractmethod
    async def _execute(
        self,
        input_data: InputT,
        context: ToolContext,
    ) -> ToolResult[OutputT]:
        """
        Execute the tool (implement in subclass).

        Args:
            input_data: Validated input data
            context: Execution context

        Returns:
            ToolResult with output
        """
        ...

    async def _dry_run(
        self,
        input_data: InputT,
        context: ToolContext,
    ) -> ToolResult[OutputT]:
        """
        Dry run mode (no actual execution).

        Override in subclass for custom dry run behavior.
        """
        self._logger.info(
            "tool_dry_run",
            tool=self.name,
            input_type=type(input_data).__name__,
        )

        return ToolResult(
            status=ToolStatus.SKIPPED,
            error_message="Dry run mode - no execution",
            metadata={"dry_run": True, "input": str(input_data)[:100]},
        )

    def _validate_input(self, input_data: InputT) -> str | None:
        """
        Validate input data.

        Override in subclass for custom validation.

        Returns:
            Error message if validation fails, None if valid
        """
        if input_data is None:
            return "Input data is required"
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r})"
