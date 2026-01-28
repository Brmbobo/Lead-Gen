"""
Unit tests for workflow orchestration.

Tests for:
- BaseWorkflow abstract class
- WorkflowRunner for workflow execution
- LeadGenWorkflow implementation
- Filter step logic
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from lead_gen.core.exceptions import WorkflowError
from lead_gen.models.lead import (
    Lead,
    LeadSource,
    LeadStatus,
    Location,
    BusinessMetrics,
    EnrichedLead,
    EmailEnrichment,
)
from lead_gen.models.workflow import (
    WorkflowConfig,
    WorkflowStep,
    WorkflowStatus,
    StepType,
    ScrapeConfig,
    FilterConfig,
    EnrichConfig,
    GenerateConfig,
    ExportConfig,
    RetryPolicy,
)
from lead_gen.tools.base import ToolContext, ToolResult, ToolStatus
from lead_gen.workflows.base import BaseWorkflow, WorkflowRunner
from lead_gen.workflows.lead_generation import LeadGenWorkflow


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_scrape_config() -> ScrapeConfig:
    """Create minimal scrape configuration."""
    return ScrapeConfig(
        query="dentist",
        location="Bratislava",
        max_results=10,
    )


@pytest.fixture
def minimal_filter_config() -> FilterConfig:
    """Create minimal filter configuration."""
    return FilterConfig(
        min_quality_score=50,
    )


@pytest.fixture
def minimal_enrich_config() -> EnrichConfig:
    """Create minimal enrich configuration."""
    return EnrichConfig(
        provider="hunter",
        find_emails=True,
        verify_emails=False,
    )


@pytest.fixture
def minimal_generate_config() -> GenerateConfig:
    """Create minimal generate configuration."""
    return GenerateConfig(
        model="gpt-4o-mini",
        language="sk",
        sender_name="Test Sender",
    )


@pytest.fixture
def minimal_export_config() -> ExportConfig:
    """Create minimal export configuration."""
    return ExportConfig(
        destination="sheets",
        spreadsheet_id="test-spreadsheet-id",
        worksheet_name="Leads",
    )


@pytest.fixture
def scrape_step(minimal_scrape_config: ScrapeConfig) -> WorkflowStep:
    """Create a scrape workflow step."""
    return WorkflowStep(
        name="scrape_leads",
        type=StepType.SCRAPE,
        scrape_config=minimal_scrape_config,
    )


@pytest.fixture
def filter_step(minimal_filter_config: FilterConfig) -> WorkflowStep:
    """Create a filter workflow step."""
    return WorkflowStep(
        name="filter_leads",
        type=StepType.FILTER,
        filter_config=minimal_filter_config,
    )


@pytest.fixture
def enrich_step(minimal_enrich_config: EnrichConfig) -> WorkflowStep:
    """Create an enrich workflow step."""
    return WorkflowStep(
        name="enrich_leads",
        type=StepType.ENRICH,
        enrich_config=minimal_enrich_config,
    )


@pytest.fixture
def generate_step(minimal_generate_config: GenerateConfig) -> WorkflowStep:
    """Create a generate workflow step."""
    return WorkflowStep(
        name="generate_messages",
        type=StepType.GENERATE,
        generate_config=minimal_generate_config,
    )


@pytest.fixture
def export_step(minimal_export_config: ExportConfig) -> WorkflowStep:
    """Create an export workflow step."""
    return WorkflowStep(
        name="export_leads",
        type=StepType.EXPORT,
        export_config=minimal_export_config,
    )


@pytest.fixture
def simple_workflow_config(scrape_step: WorkflowStep) -> WorkflowConfig:
    """Create a simple workflow with just a scrape step."""
    return WorkflowConfig(
        name="test_workflow",
        description="Test workflow for unit tests",
        steps=[scrape_step],
    )


@pytest.fixture
def full_workflow_config(
    scrape_step: WorkflowStep,
    filter_step: WorkflowStep,
    enrich_step: WorkflowStep,
    generate_step: WorkflowStep,
    export_step: WorkflowStep,
) -> WorkflowConfig:
    """Create a full workflow with all step types."""
    return WorkflowConfig(
        name="full_test_workflow",
        description="Full test workflow",
        steps=[scrape_step, filter_step, enrich_step, generate_step, export_step],
    )


@pytest.fixture
def sample_leads() -> list[Lead]:
    """Create sample leads for testing."""
    leads = []
    for i in range(5):
        lead = Lead(
            id=f"test-lead-{i}",
            place_id=f"ChIJtest{i}",
            name=f"Test Business {i}",
            phone=f"+4219012345{i:02d}" if i % 2 == 0 else "",  # Some without phone
            website=f"https://test{i}.sk" if i < 3 else None,  # Some without website
            location=Location(
                latitude=48.1486 + i * 0.01,
                longitude=17.1077 + i * 0.01,
                formatted_address=f"Test Street {i}, Bratislava",
                city="Bratislava",
                country="Slovakia",
            ),
            business_type="dentist",
            metrics=BusinessMetrics(
                rating=3.5 + i * 0.3,  # Ratings: 3.5, 3.8, 4.1, 4.4, 4.7
                review_count=10 + i * 20,
            ),
            source=LeadSource.GOOGLE_PLACES,
            status=LeadStatus.NEW if i < 4 else LeadStatus.ENRICHED,
        )
        leads.append(lead)
    return leads


@pytest.fixture
def sample_enriched_leads(sample_leads: list[Lead]) -> list[EnrichedLead]:
    """Create sample enriched leads."""
    enriched = []
    for lead in sample_leads[:3]:
        # Get dict but exclude computed fields which are not allowed as inputs
        lead_data = lead.model_dump(exclude={"display_name", "has_contact_info", "quality_score"})
        enriched_lead = EnrichedLead(
            **lead_data,
            enrichments=[
                EmailEnrichment(
                    email=f"contact@{lead.name.lower().replace(' ', '')}.sk",
                    confidence=85,
                    type="generic",
                    verified=True,
                )
            ],
            enriched_at=datetime.now(timezone.utc),
            enrichment_source="hunter",
        )
        enriched.append(enriched_lead)
    return enriched


@pytest.fixture
def tool_context(sample_leads: list[Lead]) -> ToolContext:
    """Create a tool context with sample data."""
    ctx = ToolContext(
        correlation_id="test-correlation-id",
        dry_run=False,
    )
    ctx.leads = sample_leads.copy()
    return ctx


@pytest.fixture
def success_tool_result() -> ToolResult:
    """Create a successful tool result."""
    return ToolResult(
        status=ToolStatus.SUCCESS,
        output=["result1", "result2"],
        items_processed=2,
        items_failed=0,
    )


@pytest.fixture
def failed_tool_result() -> ToolResult:
    """Create a failed tool result."""
    return ToolResult(
        status=ToolStatus.FAILED,
        error_message="Test failure",
        items_processed=0,
        items_failed=1,
    )


@pytest.fixture
def partial_tool_result() -> ToolResult:
    """Create a partial success tool result."""
    return ToolResult(
        status=ToolStatus.PARTIAL,
        output=["result1"],
        items_processed=1,
        items_failed=1,
        error_message="Partial completion",
    )


# =============================================================================
# Test BaseWorkflow
# =============================================================================


class ConcreteWorkflow(BaseWorkflow):
    """Concrete implementation for testing BaseWorkflow."""

    def __init__(self, config: WorkflowConfig, execute_results: list[ToolResult] | None = None):
        super().__init__(config)
        self.execute_results = execute_results or []
        self.execute_call_count = 0
        self.executed_steps: list[WorkflowStep] = []

    async def execute_step(
        self,
        step: WorkflowStep,
        context: ToolContext,
    ) -> ToolResult:
        self.executed_steps.append(step)
        if self.execute_call_count < len(self.execute_results):
            result = self.execute_results[self.execute_call_count]
            self.execute_call_count += 1
            return result
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=[],
            items_processed=5,
        )


class TestBaseWorkflow:
    """Tests for BaseWorkflow abstract class."""

    def test_workflow_initialization(self, simple_workflow_config: WorkflowConfig) -> None:
        """Test workflow initializes with correct configuration."""
        workflow = ConcreteWorkflow(simple_workflow_config)

        assert workflow.config == simple_workflow_config
        assert workflow.config.name == "test_workflow"
        assert workflow._logger is not None

    @pytest.mark.asyncio
    async def test_run_successful_workflow(
        self,
        simple_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test running a workflow that completes successfully."""
        workflow = ConcreteWorkflow(simple_workflow_config, [success_tool_result])

        result = await workflow.run()

        assert result.status == WorkflowStatus.COMPLETED
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.error_message == ""
        assert workflow.execute_call_count == 1

    @pytest.mark.asyncio
    async def test_run_workflow_with_context(
        self,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
        success_tool_result: ToolResult,
    ) -> None:
        """Test running a workflow with provided context."""
        workflow = ConcreteWorkflow(simple_workflow_config, [success_tool_result])

        result = await workflow.run(context=tool_context)

        assert result.status == WorkflowStatus.COMPLETED
        # Context should maintain correlation_id
        assert tool_context.correlation_id == "test-correlation-id"

    @pytest.mark.asyncio
    async def test_run_creates_context_if_none(
        self,
        simple_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test that run creates a context if none is provided."""
        workflow = ConcreteWorkflow(simple_workflow_config, [success_tool_result])

        result = await workflow.run(context=None)

        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_step_status_transitions_to_completed(
        self,
        simple_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test that step status transitions to COMPLETED on success."""
        workflow = ConcreteWorkflow(simple_workflow_config, [success_tool_result])

        await workflow.run()

        step = simple_workflow_config.steps[0]
        assert step.status == WorkflowStatus.COMPLETED
        assert step.started_at is not None
        assert step.completed_at is not None
        assert step.output_count == success_tool_result.items_processed

    @pytest.mark.asyncio
    async def test_step_status_transitions_to_failed(
        self,
        simple_workflow_config: WorkflowConfig,
        failed_tool_result: ToolResult,
    ) -> None:
        """Test that step status transitions to FAILED on failure."""
        simple_workflow_config.stop_on_error = False
        workflow = ConcreteWorkflow(simple_workflow_config, [failed_tool_result])

        await workflow.run()

        step = simple_workflow_config.steps[0]
        assert step.status == WorkflowStatus.FAILED
        assert step.error_message == "Test failure"

    @pytest.mark.asyncio
    async def test_stop_on_error_raises_workflow_error(
        self,
        simple_workflow_config: WorkflowConfig,
        failed_tool_result: ToolResult,
    ) -> None:
        """Test that stop_on_error raises WorkflowError."""
        simple_workflow_config.stop_on_error = True
        workflow = ConcreteWorkflow(simple_workflow_config, [failed_tool_result])

        with pytest.raises(WorkflowError) as exc_info:
            await workflow.run()

        assert "scrape_leads" in str(exc_info.value)
        assert simple_workflow_config.status == WorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_skip_on_error_continues_workflow(
        self,
        full_workflow_config: WorkflowConfig,
        failed_tool_result: ToolResult,
        success_tool_result: ToolResult,
    ) -> None:
        """Test that skip_on_error allows workflow to continue."""
        full_workflow_config.stop_on_error = True
        # Mark first step as skip_on_error
        full_workflow_config.steps[0].skip_on_error = True

        results = [failed_tool_result] + [success_tool_result] * 4
        workflow = ConcreteWorkflow(full_workflow_config, results)

        result = await workflow.run()

        assert result.status == WorkflowStatus.COMPLETED
        assert full_workflow_config.steps[0].status == WorkflowStatus.FAILED
        assert full_workflow_config.steps[1].status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_cancellation_during_execution(
        self,
        full_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test that cancelled workflow stops execution after cancellation.

        The workflow checks cancellation at the START of each loop iteration,
        so if we cancel during step 1, the check happens before step 2 runs,
        meaning step 2 will execute before the cancellation is detected.
        Cancelling during step 2 will prevent step 3 from running.
        """

        class CancellingWorkflow(ConcreteWorkflow):
            """Workflow that cancels itself during second step."""

            async def execute_step(
                self,
                step: WorkflowStep,
                context: ToolContext,
            ) -> ToolResult:
                result = await super().execute_step(step, context)
                # Cancel during second step - will prevent step 3+
                if self.execute_call_count == 2:
                    self.config.status = WorkflowStatus.CANCELLED
                return result

        workflow = CancellingWorkflow(full_workflow_config, [success_tool_result] * 5)
        result = await workflow.run()

        # Should have executed step 1 and 2, then cancelled before step 3
        # (cancellation is checked at start of loop iteration)
        assert workflow.execute_call_count == 2

    @pytest.mark.asyncio
    async def test_partial_result_completes_step(
        self,
        simple_workflow_config: WorkflowConfig,
        partial_tool_result: ToolResult,
    ) -> None:
        """Test that partial result still marks step as completed."""
        workflow = ConcreteWorkflow(simple_workflow_config, [partial_tool_result])

        result = await workflow.run()

        assert result.status == WorkflowStatus.COMPLETED
        step = simple_workflow_config.steps[0]
        assert step.status == WorkflowStatus.COMPLETED
        assert step.error_message == "Partial completion"

    @pytest.mark.asyncio
    async def test_metrics_collection(
        self,
        simple_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test that workflow collects metrics."""
        workflow = ConcreteWorkflow(simple_workflow_config, [success_tool_result])
        context = ToolContext()
        context.leads = [MagicMock()]
        context.enriched_leads = [MagicMock(), MagicMock()]

        result = await workflow.run(context)

        assert result.total_leads_processed == 3  # 1 lead + 2 enriched

    @pytest.mark.asyncio
    async def test_exception_during_step_marks_failed(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test that exceptions during step execution mark step as failed."""

        class FailingWorkflow(ConcreteWorkflow):
            async def execute_step(self, step: WorkflowStep, context: ToolContext) -> ToolResult:
                raise ValueError("Unexpected error")

        simple_workflow_config.stop_on_error = False
        workflow = FailingWorkflow(simple_workflow_config)

        result = await workflow.run()

        step = simple_workflow_config.steps[0]
        assert step.status == WorkflowStatus.FAILED
        assert "Unexpected error" in step.error_message

    @pytest.mark.asyncio
    async def test_disabled_steps_are_skipped(
        self,
        full_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test that disabled steps are not executed."""
        # Disable middle step
        full_workflow_config.steps[2].enabled = False

        workflow = ConcreteWorkflow(full_workflow_config, [success_tool_result] * 5)
        await workflow.run()

        # Only 4 enabled steps should be executed
        assert workflow.execute_call_count == 4


# =============================================================================
# Test WorkflowRunner
# =============================================================================


class TestWorkflowRunner:
    """Tests for WorkflowRunner."""

    def test_runner_initialization(self) -> None:
        """Test runner initializes correctly."""
        runner = WorkflowRunner()
        assert runner._logger is not None

    @pytest.mark.asyncio
    async def test_run_with_valid_config(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test running with valid configuration."""
        runner = WorkflowRunner()

        # Mock the LeadGenWorkflow - import happens inside run() method
        with patch(
            "lead_gen.workflows.lead_generation.LeadGenWorkflow"
        ) as mock_workflow_class:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = simple_workflow_config
            mock_workflow_class.return_value = mock_instance

            result = await runner.run(simple_workflow_config)

            mock_workflow_class.assert_called_once_with(simple_workflow_config)
            mock_instance.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_validates_config(self) -> None:
        """Test that run validates configuration before executing."""
        runner = WorkflowRunner()

        # Create invalid config (no scrape step)
        invalid_config = WorkflowConfig(
            name="invalid_workflow",
            steps=[
                WorkflowStep(
                    name="filter",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                )
            ],
        )

        with pytest.raises(WorkflowError) as exc_info:
            await runner.run(invalid_config)

        assert "at least one scrape step" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_with_duplicate_step_names(
        self,
        minimal_scrape_config: ScrapeConfig,
    ) -> None:
        """Test validation fails with duplicate step names."""
        runner = WorkflowRunner()

        config = WorkflowConfig(
            name="duplicate_names",
            steps=[
                WorkflowStep(
                    name="same_name",
                    type=StepType.SCRAPE,
                    scrape_config=minimal_scrape_config,
                ),
                WorkflowStep(
                    name="same_name",
                    type=StepType.SCRAPE,
                    scrape_config=minimal_scrape_config,
                ),
            ],
        )

        with pytest.raises(WorkflowError) as exc_info:
            await runner.run(config)

        assert "unique" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_run_with_context(
        self,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test running with provided context."""
        runner = WorkflowRunner()

        with patch(
            "lead_gen.workflows.lead_generation.LeadGenWorkflow"
        ) as mock_workflow_class:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = simple_workflow_config
            mock_workflow_class.return_value = mock_instance

            await runner.run(simple_workflow_config, tool_context)

            mock_instance.run.assert_called_once_with(tool_context)

    @pytest.mark.asyncio
    async def test_run_from_yaml(self, tmp_path) -> None:
        """Test running workflow from YAML file."""
        runner = WorkflowRunner()

        yaml_content = """
name: yaml_workflow
description: Test YAML workflow
steps:
  - name: scrape
    type: scrape
    scrape_config:
      query: "test query"
      location: "Test City"
      max_results: 5
"""
        yaml_file = tmp_path / "workflow.yaml"
        yaml_file.write_text(yaml_content)

        with patch(
            "lead_gen.workflows.lead_generation.LeadGenWorkflow"
        ) as mock_workflow_class:
            mock_instance = AsyncMock()
            mock_config = MagicMock()
            mock_config.status = WorkflowStatus.COMPLETED
            mock_instance.run.return_value = mock_config
            mock_workflow_class.return_value = mock_instance

            result = await runner.run_from_yaml(str(yaml_file))

            mock_workflow_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_from_yaml_file_not_found(self) -> None:
        """Test error when YAML file not found."""
        runner = WorkflowRunner()

        with pytest.raises(FileNotFoundError):
            await runner.run_from_yaml("/nonexistent/path/workflow.yaml")


# =============================================================================
# Test LeadGenWorkflow
# =============================================================================


class TestLeadGenWorkflow:
    """Tests for LeadGenWorkflow."""

    def test_initialization(self, simple_workflow_config: WorkflowConfig) -> None:
        """Test workflow initialization."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        assert workflow.config == simple_workflow_config
        assert workflow._places_service is None
        assert workflow._openai_service is None
        assert workflow._sheets_service is None
        assert workflow._hunter_service is None
        assert workflow._scrape_tool is not None
        assert workflow._generate_tool is not None
        assert workflow._export_tool is not None
        assert workflow._enrich_tool is not None

    @pytest.mark.asyncio
    async def test_execute_scrape_step(
        self,
        scrape_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test scrape step execution."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        with patch.object(
            workflow._scrape_tool, "run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                status=ToolStatus.SUCCESS,
                items_processed=5,
            )

            # Mock PlacesService to avoid API key requirement
            with patch(
                "lead_gen.workflows.lead_generation.PlacesService"
            ) as mock_places:
                mock_places.return_value = MagicMock()
                result = await workflow.execute_step(scrape_step, context)

            assert result.status == ToolStatus.SUCCESS
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scrape_without_config(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test scrape step fails without config."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        # Use MagicMock to bypass Pydantic validation
        step = MagicMock(spec=WorkflowStep)
        step.name = "bad_scrape"
        step.type = StepType.SCRAPE
        step.scrape_config = None

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.FAILED
        assert "Scrape config missing" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_filter_step(
        self,
        filter_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test filter step execution."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        result = await workflow.execute_step(filter_step, tool_context)

        assert result.status == ToolStatus.SUCCESS
        assert "original_count" in result.metadata
        assert "filtered_count" in result.metadata
        assert "remaining_count" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_filter_without_config(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test filter step fails without config."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        # Use MagicMock to bypass Pydantic validation
        step = MagicMock(spec=WorkflowStep)
        step.name = "bad_filter"
        step.type = StepType.FILTER
        step.filter_config = None

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.FAILED
        assert "Filter config missing" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_enrich_step(
        self,
        enrich_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test enrich step execution."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        with patch.object(
            workflow._enrich_tool, "run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                status=ToolStatus.SUCCESS,
                items_processed=3,
            )

            # Mock HunterService initialization
            with patch(
                "lead_gen.workflows.lead_generation.HunterService"
            ) as mock_hunter:
                mock_hunter.return_value = MagicMock()
                result = await workflow.execute_step(enrich_step, tool_context)

            assert result.status == ToolStatus.SUCCESS
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_enrich_without_config(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test enrich step fails without config."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        # Use MagicMock to bypass Pydantic validation
        step = MagicMock(spec=WorkflowStep)
        step.name = "bad_enrich"
        step.type = StepType.ENRICH
        step.enrich_config = None

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.FAILED
        assert "Enrich config missing" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_enrich_service_unavailable(
        self,
        enrich_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test enrich returns partial when service unavailable."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        with patch(
            "lead_gen.workflows.lead_generation.HunterService"
        ) as mock_hunter:
            mock_hunter.side_effect = Exception("API key missing")
            result = await workflow.execute_step(enrich_step, tool_context)

        assert result.status == ToolStatus.PARTIAL
        assert "unavailable" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_generate_step(
        self,
        generate_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test generate step execution."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        with patch.object(
            workflow._generate_tool, "run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                status=ToolStatus.SUCCESS,
                items_processed=3,
            )

            with patch(
                "lead_gen.workflows.lead_generation.OpenAIService"
            ) as mock_openai:
                mock_openai.return_value = MagicMock()
                result = await workflow.execute_step(generate_step, tool_context)

            assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_generate_without_config(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test generate step fails without config."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        # Use MagicMock to bypass Pydantic validation
        step = MagicMock(spec=WorkflowStep)
        step.name = "bad_generate"
        step.type = StepType.GENERATE
        step.generate_config = None

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.FAILED
        assert "Generate config missing" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_generate_uses_enriched_leads(
        self,
        generate_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        sample_enriched_leads: list[EnrichedLead],
    ) -> None:
        """Test generate uses enriched leads when available."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()
        context.leads = []
        context.enriched_leads = sample_enriched_leads

        with patch.object(
            workflow._generate_tool, "run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(status=ToolStatus.SUCCESS)

            with patch(
                "lead_gen.workflows.lead_generation.OpenAIService"
            ) as mock_openai:
                mock_openai.return_value = MagicMock()
                await workflow.execute_step(generate_step, context)

            # Check that enriched leads were used
            call_args = mock_run.call_args
            input_data = call_args[0][0]
            assert input_data.leads == sample_enriched_leads

    @pytest.mark.asyncio
    async def test_execute_export_step(
        self,
        export_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test export step execution."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        with patch.object(
            workflow._export_tool, "run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                status=ToolStatus.SUCCESS,
                items_processed=5,
            )

            with patch(
                "lead_gen.workflows.lead_generation.SheetsService"
            ) as mock_sheets:
                mock_sheets.return_value = MagicMock()
                result = await workflow.execute_step(export_step, tool_context)

            assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_export_without_config(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test export step fails without config."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        # Use MagicMock to bypass Pydantic validation
        step = MagicMock(spec=WorkflowStep)
        step.name = "bad_export"
        step.type = StepType.EXPORT
        step.export_config = None

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.FAILED
        assert "Export config missing" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_export_service_unavailable(
        self,
        export_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
        tool_context: ToolContext,
    ) -> None:
        """Test export fails when sheets service unavailable."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        with patch(
            "lead_gen.workflows.lead_generation.SheetsService"
        ) as mock_sheets:
            mock_sheets.side_effect = Exception("Credentials missing")
            result = await workflow.execute_step(export_step, tool_context)

        assert result.status == ToolStatus.FAILED
        assert "unavailable" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_step_type(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test unknown step type returns skipped."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        # Create a step with an unknown type
        step = MagicMock(spec=WorkflowStep)
        step.name = "unknown"
        step.type = MagicMock()
        step.type.value = "unknown_type"

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.SKIPPED
        assert "Unknown step type" in result.error_message

    @pytest.mark.asyncio
    async def test_service_lazy_initialization(
        self,
        scrape_step: WorkflowStep,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test services are lazily initialized."""
        workflow = LeadGenWorkflow(simple_workflow_config)
        context = ToolContext()

        assert workflow._places_service is None

        with patch.object(
            workflow._scrape_tool, "run", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(status=ToolStatus.SUCCESS)

            with patch(
                "lead_gen.workflows.lead_generation.PlacesService"
            ) as mock_places:
                mock_places.return_value = MagicMock()
                await workflow.execute_step(scrape_step, context)

            # Service should now be initialized
            assert workflow._places_service is not None

    @pytest.mark.asyncio
    async def test_cleanup(self, simple_workflow_config: WorkflowConfig) -> None:
        """Test cleanup closes services."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        # Mock services
        mock_places = AsyncMock()
        mock_hunter = AsyncMock()
        workflow._places_service = mock_places
        workflow._hunter_service = mock_hunter

        await workflow.cleanup()

        mock_places.close.assert_called_once()
        mock_hunter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_no_services(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test cleanup handles no initialized services."""
        workflow = LeadGenWorkflow(simple_workflow_config)

        # Should not raise
        await workflow.cleanup()


# =============================================================================
# Test Filter Step Logic
# =============================================================================


class TestWorkflowFilter:
    """Focused tests for filter step logic."""

    @pytest.fixture
    def workflow_with_filter(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> LeadGenWorkflow:
        """Create workflow for filter testing."""
        return LeadGenWorkflow(simple_workflow_config)

    @pytest.mark.asyncio
    async def test_filter_by_min_quality_score(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filtering by minimum quality score."""
        context = ToolContext()
        context.leads = sample_leads.copy()

        filter_config = FilterConfig(min_quality_score=60)
        step = WorkflowStep(
            name="quality_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        # Only leads with quality_score >= 60 should remain
        for lead in context.leads:
            assert lead.quality_score >= 60

    @pytest.mark.asyncio
    async def test_filter_by_required_fields_phone(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filtering by required phone field."""
        context = ToolContext()
        context.leads = sample_leads.copy()
        original_count = len(context.leads)

        filter_config = FilterConfig(required_fields=["phone"])
        step = WorkflowStep(
            name="phone_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        # Only leads with phone should remain
        for lead in context.leads:
            assert lead.phone
        assert len(context.leads) < original_count

    @pytest.mark.asyncio
    async def test_filter_by_required_fields_website(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filtering by required website field."""
        context = ToolContext()
        context.leads = sample_leads.copy()
        original_count = len(context.leads)

        filter_config = FilterConfig(required_fields=["website"])
        step = WorkflowStep(
            name="website_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        for lead in context.leads:
            assert lead.website is not None
        assert len(context.leads) < original_count

    @pytest.mark.asyncio
    async def test_filter_by_multiple_required_fields(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filtering by multiple required fields."""
        context = ToolContext()
        context.leads = sample_leads.copy()

        filter_config = FilterConfig(required_fields=["phone", "website"])
        step = WorkflowStep(
            name="multi_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        for lead in context.leads:
            assert lead.phone
            assert lead.website is not None

    @pytest.mark.asyncio
    async def test_filter_by_include_statuses(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filtering by included statuses."""
        context = ToolContext()
        context.leads = sample_leads.copy()

        filter_config = FilterConfig(include_statuses=["new"])
        step = WorkflowStep(
            name="status_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        for lead in context.leads:
            assert lead.status == LeadStatus.NEW

    @pytest.mark.asyncio
    async def test_filter_by_exclude_statuses(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filtering by excluded statuses."""
        context = ToolContext()
        context.leads = sample_leads.copy()

        filter_config = FilterConfig(exclude_statuses=["enriched"])
        step = WorkflowStep(
            name="exclude_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        for lead in context.leads:
            assert lead.status != LeadStatus.ENRICHED

    @pytest.mark.asyncio
    async def test_filter_deduplicate_by_phone(
        self,
        workflow_with_filter: LeadGenWorkflow,
    ) -> None:
        """Test deduplication by phone number."""
        # Create leads with duplicate phones
        leads = [
            Lead(
                name="Business 1",
                phone="+421111111111",
                location=Location(latitude=48.0, longitude=17.0),
            ),
            Lead(
                name="Business 2",
                phone="+421111111111",  # Duplicate
                location=Location(latitude=48.0, longitude=17.0),
            ),
            Lead(
                name="Business 3",
                phone="+421222222222",
                location=Location(latitude=48.0, longitude=17.0),
            ),
        ]
        context = ToolContext()
        context.leads = leads.copy()

        filter_config = FilterConfig(deduplicate_by="phone")
        step = WorkflowStep(
            name="dedup_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        assert len(context.leads) == 2  # One duplicate removed
        phones = [lead.phone for lead in context.leads]
        assert len(phones) == len(set(phones))  # All unique

    @pytest.mark.asyncio
    async def test_filter_deduplicate_by_name(
        self,
        workflow_with_filter: LeadGenWorkflow,
    ) -> None:
        """Test deduplication by business name."""
        leads = [
            Lead(
                name="Same Business",
                phone="+421111111111",
                location=Location(latitude=48.0, longitude=17.0),
            ),
            Lead(
                name="Same Business",  # Duplicate
                phone="+421222222222",
                location=Location(latitude=48.0, longitude=17.0),
            ),
            Lead(
                name="Different Business",
                phone="+421333333333",
                location=Location(latitude=48.0, longitude=17.0),
            ),
        ]
        context = ToolContext()
        context.leads = leads.copy()

        filter_config = FilterConfig(deduplicate_by="name")
        step = WorkflowStep(
            name="dedup_name_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert len(context.leads) == 2

    @pytest.mark.asyncio
    async def test_filter_combined_filters(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test combining multiple filter conditions."""
        context = ToolContext()
        context.leads = sample_leads.copy()

        filter_config = FilterConfig(
            min_quality_score=40,
            required_fields=["phone"],
            include_statuses=["new"],
        )
        step = WorkflowStep(
            name="combined_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        for lead in context.leads:
            assert lead.quality_score >= 40
            assert lead.phone
            assert lead.status == LeadStatus.NEW

    @pytest.mark.asyncio
    async def test_filter_empty_input(
        self,
        workflow_with_filter: LeadGenWorkflow,
    ) -> None:
        """Test filter with empty lead list."""
        context = ToolContext()
        context.leads = []

        filter_config = FilterConfig(min_quality_score=50)
        step = WorkflowStep(
            name="empty_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        assert result.items_processed == 0
        assert len(context.leads) == 0

    @pytest.mark.asyncio
    async def test_filter_all_removed(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filter that removes all leads."""
        context = ToolContext()
        context.leads = sample_leads.copy()
        original_count = len(context.leads)

        # Use impossibly high quality score
        filter_config = FilterConfig(min_quality_score=100)
        step = WorkflowStep(
            name="strict_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.status == ToolStatus.SUCCESS
        assert len(context.leads) == 0
        assert result.items_failed == original_count

    @pytest.mark.asyncio
    async def test_filter_metadata(
        self,
        workflow_with_filter: LeadGenWorkflow,
        sample_leads: list[Lead],
    ) -> None:
        """Test filter result contains correct metadata."""
        context = ToolContext()
        context.leads = sample_leads.copy()
        original_count = len(context.leads)

        filter_config = FilterConfig(min_quality_score=50)
        step = WorkflowStep(
            name="metadata_filter",
            type=StepType.FILTER,
            filter_config=filter_config,
        )

        result = await workflow_with_filter.execute_step(step, context)

        assert result.metadata["original_count"] == original_count
        assert result.metadata["remaining_count"] == len(context.leads)
        assert result.metadata["filtered_count"] == original_count - len(context.leads)


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestWorkflowEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_workflow_with_no_enabled_steps(
        self,
        scrape_step: WorkflowStep,
    ) -> None:
        """Test workflow with all steps disabled."""
        scrape_step.enabled = False
        config = WorkflowConfig(
            name="disabled_workflow",
            steps=[scrape_step],
        )

        workflow = ConcreteWorkflow(config)
        result = await workflow.run()

        assert result.status == WorkflowStatus.COMPLETED
        assert workflow.execute_call_count == 0

    @pytest.mark.asyncio
    async def test_workflow_step_duration_calculation(
        self,
        simple_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test step duration is calculated correctly."""
        workflow = ConcreteWorkflow(simple_workflow_config, [success_tool_result])

        await workflow.run()

        step = simple_workflow_config.steps[0]
        assert step.duration_seconds is not None
        assert step.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_workflow_current_step_index_tracking(
        self,
        full_workflow_config: WorkflowConfig,
        success_tool_result: ToolResult,
    ) -> None:
        """Test current step index is tracked during execution."""
        workflow = ConcreteWorkflow(
            full_workflow_config,
            [success_tool_result] * 5,
        )

        await workflow.run()

        # After completion, index should be at last step
        assert full_workflow_config.current_step_index == 4

    @pytest.mark.asyncio
    async def test_skipped_step_result(
        self,
        simple_workflow_config: WorkflowConfig,
    ) -> None:
        """Test handling of skipped step result."""
        skipped_result = ToolResult(
            status=ToolStatus.SKIPPED,
            error_message="Skipped due to condition",
        )
        workflow = ConcreteWorkflow(simple_workflow_config, [skipped_result])

        result = await workflow.run()

        step = simple_workflow_config.steps[0]
        assert step.status == WorkflowStatus.COMPLETED  # Skipped is treated as completed
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_context_leads_persist_across_steps(
        self,
        full_workflow_config: WorkflowConfig,
    ) -> None:
        """Test that context leads persist across steps."""

        class LeadModifyingWorkflow(ConcreteWorkflow):
            async def execute_step(
                self,
                step: WorkflowStep,
                context: ToolContext,
            ) -> ToolResult:
                if step.type == StepType.SCRAPE:
                    # Add leads during scrape
                    context.leads = [MagicMock() for _ in range(5)]
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    items_processed=len(context.leads),
                )

        workflow = LeadModifyingWorkflow(full_workflow_config)
        context = ToolContext()

        await workflow.run(context)

        # Leads should persist
        assert len(context.leads) == 5

    @pytest.mark.asyncio
    async def test_export_validation_spreadsheet_id(
        self,
        minimal_scrape_config: ScrapeConfig,
    ) -> None:
        """Test validation error for sheets export without spreadsheet_id."""
        config = WorkflowConfig(
            name="invalid_export",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=minimal_scrape_config,
                ),
                WorkflowStep(
                    name="export",
                    type=StepType.EXPORT,
                    export_config=ExportConfig(
                        destination="sheets",
                        spreadsheet_id="",  # Empty - should fail validation
                    ),
                ),
            ],
        )

        errors = config.validate_workflow()
        assert any("spreadsheet_id" in e for e in errors)
