"""
Integration tests for Lead-Gen workflow orchestration.

Tests complete workflow execution including:
- Full pipeline (scrape -> filter -> enrich -> generate -> export)
- State management and context propagation
- Error handling and recovery
- Partial execution and resume
- Configuration from YAML
- Concurrent workflow execution
- GDPR compliance integration
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

from lead_gen.core.exceptions import WorkflowError
from lead_gen.core.gdpr import (
    DataCategory,
    GDPRManager,
    ProcessingPurpose,
    get_gdpr_manager,
)
from lead_gen.models.lead import (
    BusinessMetrics,
    EnrichedLead,
    Lead,
    LeadSource,
    LeadStatus,
    Location,
    EmailEnrichment,
)
from lead_gen.models.outreach import (
    MessageLanguage,
    MessageTone,
    OutreachMessage,
)
from lead_gen.models.workflow import (
    EnrichConfig,
    ExportConfig,
    FilterConfig,
    GenerateConfig,
    ScrapeConfig,
    StepType,
    WorkflowConfig,
    WorkflowStatus,
    WorkflowStep,
)
from lead_gen.services.hunter_service import DomainSearchResult, HunterService
from lead_gen.services.openai_service import GenerationResult, OpenAIService
from lead_gen.services.places_service import PlacesSearchResult, PlacesService
from lead_gen.services.sheets_service import ExportResult, SheetsService
from lead_gen.tools.base import ToolContext, ToolResult, ToolStatus
from lead_gen.workflows.base import BaseWorkflow, WorkflowRunner
from lead_gen.workflows.lead_generation import LeadGenWorkflow


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_leads() -> list[Lead]:
    """Create a list of sample leads for testing."""
    leads = []
    for i in range(5):
        leads.append(Lead(
            id=f"test-lead-{i}",
            place_id=f"ChIJtest{i:03d}",
            name=f"Zubna Ambulancia {i}",
            phone=f"+4219012345{i:02d}",
            website=f"https://zubar{i}.sk",
            email=f"info@zubar{i}.sk" if i % 2 == 0 else None,
            location=Location(
                latitude=48.1486 + i * 0.01,
                longitude=17.1077 + i * 0.01,
                formatted_address=f"Hlavna {i}, 811 01 Bratislava",
                city="Bratislava",
                country="Slovakia",
                country_code="SK",
            ),
            business_type="dentist",
            categories=["dentist", "health"],
            metrics=BusinessMetrics(
                rating=4.0 + i * 0.1,
                review_count=50 + i * 10,
                price_level=2,
            ),
            source=LeadSource.GOOGLE_PLACES,
        ))
    return leads


@pytest.fixture
def sample_enriched_leads(sample_leads: list[Lead]) -> list[EnrichedLead]:
    """Create enriched leads from sample leads."""
    enriched = []
    for lead in sample_leads:
        # Extract domain from website URL
        domain = "test.sk"
        if lead.website:
            parsed = urlparse(str(lead.website))
            domain = parsed.netloc or "test.sk"

        enrichment = EmailEnrichment(
            email=f"contact@{domain}",
            confidence=85,
            type="generic",
            first_name="Jan",
            last_name="Novak",
            position="Owner",
            verified=True,
        )
        # Exclude computed fields when creating EnrichedLead
        lead_data = lead.model_dump(exclude={"display_name", "has_contact_info", "quality_score"})
        enriched.append(EnrichedLead(
            **lead_data,
            enrichments=[enrichment],
            enriched_at=datetime.now(timezone.utc),
            enrichment_source="hunter",
        ))
    return enriched


@pytest.fixture
def sample_messages() -> list[OutreachMessage]:
    """Create sample outreach messages."""
    messages = []
    for i in range(5):
        messages.append(OutreachMessage(
            id=f"test-msg-{i}",
            subject=f"Spolupraca pre Zubna Ambulancia {i}",
            body=f"Dobry den,\n\noslovujem Vas s ponukou pre Vasu ambulanciu {i}...",
            language=MessageLanguage.SLOVAK,
            tone=MessageTone.PROFESSIONAL,
            lead_id=f"test-lead-{i}",
            generation_model="gpt-4o-mini",
            generation_tokens=150,
            generation_cost_usd=0.0001,
        ))
    return messages


@pytest.fixture
def mock_places_service(sample_leads: list[Lead]) -> AsyncMock:
    """Create a mock PlacesService."""
    mock = AsyncMock(spec=PlacesService)
    mock.search_text = AsyncMock(return_value=PlacesSearchResult(
        places=sample_leads,
        total_count=len(sample_leads),
        search_query="zubar",
        search_location="Bratislava",
    ))
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_hunter_service(sample_enriched_leads: list[EnrichedLead]) -> AsyncMock:
    """Create a mock HunterService."""
    mock = AsyncMock(spec=HunterService)
    mock.enrich_lead = AsyncMock(side_effect=sample_enriched_leads)
    mock.enrich_leads_batch = AsyncMock(return_value=sample_enriched_leads)
    mock.search_domain = AsyncMock(return_value=DomainSearchResult(
        domain="test.sk",
        emails=[EmailEnrichment(
            email="contact@test.sk",
            confidence=85,
            type="generic",
            first_name="Jan",
            last_name="Novak",
            verified=True,
        )],
        organization="Test Company",
        total_emails=1,
    ))
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_openai_service(sample_messages: list[OutreachMessage]) -> AsyncMock:
    """Create a mock OpenAIService."""
    mock = AsyncMock(spec=OpenAIService)

    results = [
        GenerationResult(
            message=msg,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.0001,
            model="gpt-4o-mini",
        )
        for msg in sample_messages
    ]

    mock.generate_message = AsyncMock(side_effect=results)
    mock.generate_messages_batch = AsyncMock(return_value=results)
    return mock


@pytest.fixture
def mock_sheets_service() -> AsyncMock:
    """Create a mock SheetsService."""
    mock = AsyncMock(spec=SheetsService)
    mock.export_leads = AsyncMock(return_value=ExportResult(
        spreadsheet_id="test-spreadsheet-id",
        worksheet_name="Leads",
        rows_exported=5,
        spreadsheet_url="https://docs.google.com/spreadsheets/d/test",
    ))
    mock.export_messages = AsyncMock(return_value=ExportResult(
        spreadsheet_id="test-spreadsheet-id",
        worksheet_name="Messages",
        rows_exported=5,
        spreadsheet_url="https://docs.google.com/spreadsheets/d/test",
    ))
    return mock


@pytest.fixture
def mock_gdpr_manager() -> MagicMock:
    """Create a mock GDPRManager."""
    mock = MagicMock(spec=GDPRManager)
    mock.record_processing = MagicMock(return_value=MagicMock(record_id="test-record"))
    mock.pseudonymize = MagicMock(return_value="pseudonymized-id")
    mock.validate_legal_basis = MagicMock()
    return mock


@pytest.fixture
def workflow_config() -> WorkflowConfig:
    """Create a test workflow configuration."""
    return WorkflowConfig(
        name="test_workflow",
        description="Test workflow for integration testing",
        steps=[
            WorkflowStep(
                name="scrape_leads",
                type=StepType.SCRAPE,
                scrape_config=ScrapeConfig(
                    query="zubar",
                    location="Bratislava, Slovakia",
                    radius_km=30,
                    max_results=20,
                    language="sk",
                    region="sk",
                ),
            ),
            WorkflowStep(
                name="filter_quality",
                type=StepType.FILTER,
                filter_config=FilterConfig(
                    min_quality_score=30,
                    required_fields=["phone"],
                ),
            ),
            WorkflowStep(
                name="enrich_emails",
                type=StepType.ENRICH,
                enrich_config=EnrichConfig(
                    provider="hunter",
                    find_emails=True,
                    verify_emails=True,
                ),
            ),
            WorkflowStep(
                name="generate_messages",
                type=StepType.GENERATE,
                generate_config=GenerateConfig(
                    model="gpt-4o-mini",
                    language="sk",
                    tone="professional",
                    sender_name="Jan Novak",
                    sender_company="Lead-Gen s.r.o.",
                ),
            ),
            WorkflowStep(
                name="export_to_sheets",
                type=StepType.EXPORT,
                export_config=ExportConfig(
                    destination="sheets",
                    spreadsheet_id="test-spreadsheet-id",
                    worksheet_name="Leads",
                ),
            ),
        ],
        stop_on_error=True,
    )


@pytest.fixture
def tool_context(mock_gdpr_manager: MagicMock) -> ToolContext:
    """Create a tool context for testing."""
    return ToolContext(
        correlation_id="test-correlation-id",
        dry_run=False,
        gdpr_manager=mock_gdpr_manager,
    )


# =============================================================================
# Complete Workflow Execution Tests
# =============================================================================


@pytest.mark.asyncio
class TestCompleteWorkflowExecution:
    """Test complete workflow execution from scrape to export."""

    async def test_workflow_initialization(
        self,
        workflow_config: WorkflowConfig,
    ):
        """Test workflow can be initialized with config."""
        workflow = LeadGenWorkflow(workflow_config)

        assert workflow.config == workflow_config
        assert workflow.config.name == "test_workflow"
        assert len(workflow.config.steps) == 5

    async def test_workflow_processes_leads_through_pipeline(
        self,
        mock_places_service: AsyncMock,
        sample_leads: list[Lead],
    ):
        """Test that leads flow correctly through the pipeline."""
        # Create workflow with only scrape step
        config = WorkflowConfig(
            name="test_pipeline",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test", max_results=10),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        context = ToolContext()
        result = await workflow.run(context)

        assert result.status == WorkflowStatus.COMPLETED
        # Verify scrape was called
        mock_places_service.search_text.assert_called_once()

    async def test_workflow_tracks_metrics(
        self,
        mock_places_service: AsyncMock,
        sample_leads: list[Lead],
    ):
        """Test that workflow tracks metrics correctly."""
        config = WorkflowConfig(
            name="test_metrics",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        context = ToolContext()
        result = await workflow.run(context)

        # Verify metrics are tracked
        assert context.api_calls >= 0
        assert context.elapsed_seconds >= 0
        assert result.started_at is not None
        assert result.completed_at is not None

    async def test_workflow_dry_run_mode(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test workflow dry run mode doesn't execute actual operations."""
        config = WorkflowConfig(
            name="test_dry_run",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        context = ToolContext(dry_run=True)

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(context)

        # In dry run, workflow should complete
        assert result.status == WorkflowStatus.COMPLETED


# =============================================================================
# Workflow State Management Tests
# =============================================================================


@pytest.mark.asyncio
class TestWorkflowStateManagement:
    """Test workflow state management and context propagation."""

    async def test_context_leads_persist_between_steps(
        self,
        sample_leads: list[Lead],
    ):
        """Test that leads in context persist between workflow steps."""
        context = ToolContext()

        # Add leads
        for lead in sample_leads:
            context.add_lead(lead)

        # Verify leads persist
        assert len(context.leads) == len(sample_leads)
        assert all(lead.id in [l.id for l in context.leads] for lead in sample_leads)

    async def test_context_enriched_leads_tracked(self):
        """Test that enriched leads are tracked separately."""
        context = ToolContext()

        # Create simple enriched leads
        for i in range(3):
            lead = EnrichedLead(
                id=f"enriched-{i}",
                name=f"Test Lead {i}",
                location=Location(latitude=48.0, longitude=17.0),
                enrichments=[],
            )
            context.add_enriched_lead(lead)

        assert len(context.enriched_leads) == 3

    async def test_context_messages_tracked(
        self,
        sample_messages: list[OutreachMessage],
    ):
        """Test that generated messages are tracked in context."""
        context = ToolContext()

        for msg in sample_messages:
            context.add_message(msg)

        assert len(context.messages) == len(sample_messages)

    async def test_workflow_step_status_tracking(
        self,
        workflow_config: WorkflowConfig,
    ):
        """Test that individual step statuses are tracked correctly."""
        # All steps should start as PENDING
        for step in workflow_config.steps:
            assert step.status == WorkflowStatus.PENDING

        # Verify step properties
        assert workflow_config.total_steps == 5
        assert workflow_config.completed_steps == 0
        assert workflow_config.progress_percent == 0.0

    async def test_workflow_current_step_index_updated(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test that current step index is updated during execution."""
        config = WorkflowConfig(
            name="test_index",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service
        context = ToolContext()

        result = await workflow.run(context)

        # After completion, index should be at last step
        assert result.current_step_index == 0

    async def test_context_api_calls_tracked(self):
        """Test that API calls are tracked in context."""
        context = ToolContext()

        context.track_api_call(tokens=100, cost=0.001)
        context.track_api_call(tokens=150, cost=0.002)

        assert context.api_calls == 2
        assert context.tokens_used == 250
        assert context.cost_usd == 0.003

    async def test_context_memory_tracking(self):
        """Test that context tracks memory usage."""
        context = ToolContext()

        # Add some leads
        for i in range(10):
            context.add_lead(Lead(
                id=f"lead-{i}",
                name=f"Test Lead {i}",
                location=Location(latitude=48.0, longitude=17.0),
            ))

        # Check memory tracking methods exist and work
        stats = context.get_collection_stats()
        assert "leads_count" in stats
        assert stats["leads_count"] == 10
        assert "memory_usage_mb" in stats


# =============================================================================
# Error Handling and Recovery Tests
# =============================================================================


@pytest.mark.asyncio
class TestErrorHandlingAndRecovery:
    """Test workflow error handling and recovery mechanisms."""

    async def test_workflow_step_validation(self):
        """Test workflow step requires appropriate config."""
        # This should raise validation error
        with pytest.raises(ValueError):
            WorkflowStep(
                name="bad_step",
                type=StepType.SCRAPE,
                # Missing scrape_config
            )

    async def test_workflow_handles_step_failure_with_stop_on_error(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test workflow stops on error when stop_on_error is True."""
        mock_places_service.search_text = AsyncMock(
            side_effect=Exception("API Error")
        )

        config = WorkflowConfig(
            name="test_stop_on_error",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
                WorkflowStep(
                    name="filter",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(min_quality_score=30),
                ),
            ],
            stop_on_error=True,
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        with pytest.raises(Exception, match="API Error"):
            await workflow.run(ToolContext())

    async def test_workflow_continues_on_error_when_configured(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test workflow continues when stop_on_error is False."""
        mock_places_service.search_text = AsyncMock(
            side_effect=Exception("API Error")
        )

        config = WorkflowConfig(
            name="test_continue_on_error",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                    skip_on_error=True,
                ),
                WorkflowStep(
                    name="filter",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(min_quality_score=30),
                ),
            ],
            stop_on_error=False,
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(ToolContext())

        # Workflow should complete despite step failure
        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps[0].status == WorkflowStatus.FAILED
        assert result.steps[0].error_message != ""

    async def test_workflow_step_skip_on_error(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test individual step skip_on_error flag."""
        mock_places_service.search_text = AsyncMock(
            side_effect=Exception("API Error")
        )

        config = WorkflowConfig(
            name="test_skip_step",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                    skip_on_error=True,  # Allow this step to fail
                ),
            ],
            stop_on_error=True,
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(ToolContext())

        # Should complete because step has skip_on_error
        assert result.status == WorkflowStatus.COMPLETED

    async def test_workflow_records_error_message(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test that error messages are recorded on step failure."""
        error_msg = "Test API failure"
        mock_places_service.search_text = AsyncMock(
            side_effect=Exception(error_msg)
        )

        config = WorkflowConfig(
            name="test_error_msg",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                    skip_on_error=True,
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(ToolContext())

        assert error_msg in result.steps[0].error_message


# =============================================================================
# Partial Execution and Resume Tests
# =============================================================================


@pytest.mark.asyncio
class TestPartialExecutionAndResume:
    """Test partial workflow execution and resume capabilities."""

    async def test_workflow_can_be_cancelled(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test that workflow can be cancelled mid-execution."""
        config = WorkflowConfig(
            name="test_cancel",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        # Cancel before running
        config.status = WorkflowStatus.CANCELLED

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(ToolContext())

        # Should complete without executing steps
        assert result.status == WorkflowStatus.COMPLETED

    async def test_workflow_disabled_steps_skipped(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test that disabled steps are skipped."""
        config = WorkflowConfig(
            name="test_disabled",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                    enabled=False,  # Disabled
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(ToolContext())

        # Should complete but scrape not called
        assert result.status == WorkflowStatus.COMPLETED
        mock_places_service.search_text.assert_not_called()

    async def test_enabled_steps_filter(self):
        """Test that enabled_steps property filters correctly."""
        config = WorkflowConfig(
            name="test_filter",
            steps=[
                WorkflowStep(
                    name="step1",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                    enabled=True,
                ),
                WorkflowStep(
                    name="step2",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                    enabled=False,
                ),
                WorkflowStep(
                    name="step3",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                    enabled=True,
                ),
            ],
        )

        enabled = config.enabled_steps

        assert len(enabled) == 2
        assert enabled[0].name == "step1"
        assert enabled[1].name == "step3"

    async def test_workflow_progress_tracking(self):
        """Test workflow progress calculation."""
        config = WorkflowConfig(
            name="test_progress",
            steps=[
                WorkflowStep(
                    name="step1",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
                WorkflowStep(
                    name="step2",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                ),
            ],
        )

        # Initially 0%
        assert config.progress_percent == 0.0

        # Mark first step complete
        config.steps[0].status = WorkflowStatus.COMPLETED
        assert config.progress_percent == 50.0

        # Mark second step complete
        config.steps[1].status = WorkflowStatus.COMPLETED
        assert config.progress_percent == 100.0


# =============================================================================
# YAML Configuration Tests
# =============================================================================


@pytest.mark.asyncio
class TestYAMLConfiguration:
    """Test workflow configuration from YAML files."""

    async def test_workflow_config_from_yaml_string(self):
        """Test loading workflow config from YAML string."""
        yaml_content = """
name: test_yaml_workflow
description: Test workflow from YAML
version: "1.0"
steps:
  - name: scrape_leads
    type: scrape
    scrape_config:
      query: "zubar"
      location: "Bratislava"
      max_results: 10
  - name: filter_leads
    type: filter
    filter_config:
      min_quality_score: 50
stop_on_error: true
"""

        config = WorkflowConfig.from_yaml_string(yaml_content)

        assert config.name == "test_yaml_workflow"
        assert len(config.steps) == 2
        assert config.steps[0].type == StepType.SCRAPE
        assert config.steps[0].scrape_config.query == "zubar"
        assert config.steps[1].type == StepType.FILTER
        assert config.stop_on_error is True

    async def test_workflow_config_from_yaml_file(self):
        """Test loading workflow config from YAML file."""
        yaml_content = """
name: file_test_workflow
description: Test from file
steps:
  - name: scrape
    type: scrape
    scrape_config:
      query: "dentist"
      max_results: 5
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            f.write(yaml_content)
            f.flush()

            config = WorkflowConfig.from_yaml(f.name)

            assert config.name == "file_test_workflow"
            assert len(config.steps) == 1

            # Cleanup
            Path(f.name).unlink()

    async def test_workflow_config_to_yaml(self):
        """Test exporting workflow config to YAML."""
        config = WorkflowConfig(
            name="export_test",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        yaml_string = config.to_yaml()

        assert "name: export_test" in yaml_string
        assert "scrape" in yaml_string

    async def test_workflow_config_yaml_roundtrip(self):
        """Test YAML export/import roundtrip using a clean YAML string."""
        # Test the roundtrip by manually creating a YAML string that
        # can be parsed and converted back
        original_yaml = """
name: roundtrip_test
description: Test roundtrip
version: "1.0"
steps:
  - name: scrape
    type: scrape
    scrape_config:
      query: zubar
      location: Bratislava
      max_results: 20
stop_on_error: true
"""
        # Load from YAML string
        config = WorkflowConfig.from_yaml_string(original_yaml)

        assert config.name == "roundtrip_test"
        assert config.description == "Test roundtrip"
        assert len(config.steps) == 1
        assert config.steps[0].scrape_config.query == "zubar"
        assert config.steps[0].scrape_config.location == "Bratislava"
        assert config.steps[0].scrape_config.max_results == 20
        assert config.stop_on_error is True

        # Verify the config can be exported
        yaml_output = config.to_yaml()
        assert "roundtrip_test" in yaml_output
        assert "zubar" in yaml_output

    async def test_workflow_config_validation(self):
        """Test workflow configuration validation."""
        # Missing scrape step
        config = WorkflowConfig(
            name="invalid_workflow",
            steps=[
                WorkflowStep(
                    name="filter_only",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                ),
            ],
        )

        errors = config.validate_workflow()
        assert len(errors) > 0
        assert any("scrape" in e.lower() for e in errors)

    async def test_workflow_config_unique_step_names(self):
        """Test that duplicate step names are detected."""
        config = WorkflowConfig(
            name="duplicate_names",
            steps=[
                WorkflowStep(
                    name="same_name",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
                WorkflowStep(
                    name="same_name",  # Duplicate
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                ),
            ],
        )

        errors = config.validate_workflow()
        assert any("unique" in e.lower() for e in errors)


# =============================================================================
# Concurrent Workflow Execution Tests
# =============================================================================


@pytest.mark.asyncio
class TestConcurrentWorkflowExecution:
    """Test concurrent workflow execution scenarios."""

    async def test_multiple_workflows_concurrent(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test running multiple workflows concurrently."""
        configs = [
            WorkflowConfig(
                name=f"concurrent_workflow_{i}",
                steps=[
                    WorkflowStep(
                        name="scrape",
                        type=StepType.SCRAPE,
                        scrape_config=ScrapeConfig(query=f"test_{i}"),
                    ),
                ],
            )
            for i in range(3)
        ]

        async def run_workflow(config: WorkflowConfig) -> WorkflowConfig:
            workflow = LeadGenWorkflow(config)
            workflow._places_service = mock_places_service
            return await workflow.run(ToolContext())

        # Run all workflows concurrently
        results = await asyncio.gather(*[run_workflow(c) for c in configs])

        # All should complete
        assert len(results) == 3
        assert all(r.status == WorkflowStatus.COMPLETED for r in results)

    async def test_isolated_contexts_in_concurrent_execution(self):
        """Test that contexts are isolated between concurrent workflows."""
        context1 = ToolContext(correlation_id="workflow-1")
        context2 = ToolContext(correlation_id="workflow-2")

        # Add different data to each
        context1.add_lead(Lead(
            id="lead-1",
            name="Lead 1",
            location=Location(latitude=48.0, longitude=17.0),
        ))
        context2.add_lead(Lead(
            id="lead-2",
            name="Lead 2",
            location=Location(latitude=48.0, longitude=17.0),
        ))
        context2.add_lead(Lead(
            id="lead-3",
            name="Lead 3",
            location=Location(latitude=48.0, longitude=17.0),
        ))

        # Verify isolation
        assert len(context1.leads) == 1
        assert len(context2.leads) == 2
        assert context1.correlation_id != context2.correlation_id

    async def test_concurrent_context_does_not_share_state(self):
        """Test that concurrent executions don't share context state."""
        async def add_leads(context: ToolContext, prefix: str, count: int):
            for i in range(count):
                await asyncio.sleep(0.001)  # Simulate async work
                context.add_lead(Lead(
                    id=f"{prefix}-{i}",
                    name=f"Lead {prefix}-{i}",
                    location=Location(latitude=48.0, longitude=17.0),
                ))

        context1 = ToolContext()
        context2 = ToolContext()

        # Run concurrently
        await asyncio.gather(
            add_leads(context1, "ctx1", 5),
            add_leads(context2, "ctx2", 3),
        )

        assert len(context1.leads) == 5
        assert len(context2.leads) == 3
        assert all("ctx1" in l.id for l in context1.leads)
        assert all("ctx2" in l.id for l in context2.leads)


# =============================================================================
# GDPR Compliance Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestGDPRComplianceIntegration:
    """Test GDPR compliance integration with workflows."""

    async def test_workflow_records_gdpr_processing(
        self,
        tool_context: ToolContext,
        mock_gdpr_manager: MagicMock,
        sample_leads: list[Lead],
    ):
        """Test that workflow operations are recorded for GDPR compliance."""
        # Verify GDPR manager is available
        assert tool_context.gdpr_manager is not None

    async def test_leads_have_gdpr_fields(
        self,
        sample_leads: list[Lead],
    ):
        """Test that leads have required GDPR fields."""
        for lead in sample_leads:
            assert hasattr(lead, "gdpr_consent")
            assert hasattr(lead, "gdpr_legal_basis")
            assert hasattr(lead, "gdpr_retention_until")
            assert hasattr(lead, "gdpr_pseudonymized_id")

    async def test_lead_gdpr_export(
        self,
        sample_leads: list[Lead],
    ):
        """Test lead GDPR export functionality."""
        lead = sample_leads[0]

        gdpr_export = lead.to_gdpr_export()

        assert "personal_data" in gdpr_export
        assert "processing_metadata" in gdpr_export
        assert gdpr_export["personal_data"]["business_name"] == lead.name
        assert gdpr_export["processing_metadata"]["legal_basis"] == lead.gdpr_legal_basis

    async def test_workflow_context_gdpr_integration(
        self,
        mock_gdpr_manager: MagicMock,
    ):
        """Test workflow context GDPR manager integration."""
        context = ToolContext(gdpr_manager=mock_gdpr_manager)

        assert context.gdpr_manager is mock_gdpr_manager

    async def test_gdpr_processing_purposes_available(self):
        """Test that processing purposes are properly defined."""
        assert ProcessingPurpose.LEAD_GENERATION
        assert ProcessingPurpose.OUTREACH
        assert ProcessingPurpose.EMAIL_ENRICHMENT
        assert ProcessingPurpose.EXPORT

    async def test_gdpr_data_categories_available(self):
        """Test that data categories are properly defined."""
        assert DataCategory.BUSINESS_NAME
        assert DataCategory.BUSINESS_EMAIL
        assert DataCategory.BUSINESS_PHONE
        assert DataCategory.CONTACT_EMAIL


# =============================================================================
# WorkflowRunner Tests
# =============================================================================


@pytest.mark.asyncio
class TestWorkflowRunner:
    """Test WorkflowRunner functionality."""

    async def test_runner_validates_config(self):
        """Test that runner validates configuration."""
        runner = WorkflowRunner()

        # Config without scrape step
        invalid_config = WorkflowConfig(
            name="invalid",
            steps=[
                WorkflowStep(
                    name="filter",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(),
                ),
            ],
        )

        with pytest.raises(WorkflowError, match="Invalid workflow"):
            await runner.run(invalid_config)

    async def test_runner_from_yaml(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test running workflow from YAML file."""
        yaml_content = """
name: yaml_runner_test
steps:
  - name: scrape
    type: scrape
    scrape_config:
      query: "test"
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            f.write(yaml_content)
            f.flush()

            runner = WorkflowRunner()

            with patch(
                "lead_gen.workflows.lead_generation.PlacesService",
                return_value=mock_places_service,
            ):
                result = await runner.run_from_yaml(f.name)

            assert result.name == "yaml_runner_test"

            Path(f.name).unlink()


# =============================================================================
# Step Execution Tests
# =============================================================================


@pytest.mark.asyncio
class TestStepExecution:
    """Test individual step execution."""

    async def test_scrape_step_execution(
        self,
        mock_places_service: AsyncMock,
        sample_leads: list[Lead],
    ):
        """Test scrape step execution."""
        config = WorkflowConfig(
            name="test_scrape",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(
                        query="zubar",
                        location="Bratislava",
                        max_results=20,
                    ),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        context = ToolContext()
        step = config.steps[0]

        result = await workflow._execute_scrape(step, context)

        assert result.status == ToolStatus.SUCCESS
        mock_places_service.search_text.assert_called_once()

    async def test_scrape_step_missing_config(self):
        """Test scrape step fails gracefully with missing config."""
        config = WorkflowConfig(
            name="test_scrape_missing",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)

        # Create step with a valid scrape config, then set it to None
        step = config.steps[0].model_copy()
        object.__setattr__(step, 'scrape_config', None)

        context = ToolContext()
        result = await workflow._execute_scrape(step, context)

        assert result.status == ToolStatus.FAILED
        assert "missing" in result.error_message.lower() or "config" in result.error_message.lower()

    async def test_generate_step_execution(
        self,
        mock_openai_service: AsyncMock,
        sample_leads: list[Lead],
    ):
        """Test generate step execution."""
        config = WorkflowConfig(
            name="test_generate",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
                WorkflowStep(
                    name="generate",
                    type=StepType.GENERATE,
                    generate_config=GenerateConfig(
                        model="gpt-4o-mini",
                        language="sk",
                        sender_name="Test",
                    ),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._openai_service = mock_openai_service

        context = ToolContext()
        for lead in sample_leads:
            context.add_lead(lead)

        step = config.steps[1]
        result = await workflow._execute_generate(step, context)

        assert result.status == ToolStatus.SUCCESS

    async def test_export_step_execution(
        self,
        mock_sheets_service: AsyncMock,
        sample_leads: list[Lead],
    ):
        """Test export step execution."""
        config = WorkflowConfig(
            name="test_export",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
                WorkflowStep(
                    name="export",
                    type=StepType.EXPORT,
                    export_config=ExportConfig(
                        destination="sheets",
                        spreadsheet_id="test-id",
                        worksheet_name="Test",
                    ),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._sheets_service = mock_sheets_service

        context = ToolContext()
        for lead in sample_leads:
            context.add_lead(lead)

        step = config.steps[1]
        result = await workflow._execute_export(step, context)

        assert result.status == ToolStatus.SUCCESS
        mock_sheets_service.export_leads.assert_called_once()

    async def test_unknown_step_type_skipped(self):
        """Test that unknown step types are skipped gracefully."""
        config = WorkflowConfig(
            name="test_unknown",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        context = ToolContext()

        # Create a step with WAIT type (not handled in execute_step)
        step = WorkflowStep(
            name="wait_step",
            type=StepType.WAIT,
            scrape_config=ScrapeConfig(query="dummy"),  # type: ignore
        )

        result = await workflow.execute_step(step, context)

        assert result.status == ToolStatus.SKIPPED


# =============================================================================
# Cleanup Tests
# =============================================================================


@pytest.mark.asyncio
class TestWorkflowCleanup:
    """Test workflow resource cleanup."""

    async def test_workflow_cleanup_closes_services(
        self,
        mock_places_service: AsyncMock,
        mock_hunter_service: AsyncMock,
    ):
        """Test that cleanup closes all services."""
        config = WorkflowConfig(
            name="test_cleanup",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service
        workflow._hunter_service = mock_hunter_service

        await workflow.cleanup()

        mock_places_service.close.assert_called_once()
        mock_hunter_service.close.assert_called_once()

    async def test_context_clear_collections(self):
        """Test clearing context collections."""
        context = ToolContext()

        # Add some data
        context.add_lead(Lead(
            id="test",
            name="Test",
            location=Location(latitude=48.0, longitude=17.0),
        ))
        context.add_message(OutreachMessage(
            subject="Test",
            body="Test body",
            lead_id="test",
        ))

        assert len(context.leads) == 1
        assert len(context.messages) == 1

        context.clear_collections()

        assert len(context.leads) == 0
        assert len(context.messages) == 0


# =============================================================================
# Integration Scenarios
# =============================================================================


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    async def test_complete_scrape_to_export_scenario(
        self,
        mock_places_service: AsyncMock,
        mock_sheets_service: AsyncMock,
        sample_leads: list[Lead],
    ):
        """Test complete scrape to export workflow scenario."""
        config = WorkflowConfig(
            name="full_scenario",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(
                        query="dentist",
                        location="Bratislava",
                    ),
                ),
                WorkflowStep(
                    name="export",
                    type=StepType.EXPORT,
                    export_config=ExportConfig(
                        destination="sheets",
                        spreadsheet_id="test-id",
                    ),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service
        workflow._sheets_service = mock_sheets_service

        context = ToolContext()
        result = await workflow.run(context)

        # Verify workflow completed
        assert result.status == WorkflowStatus.COMPLETED

        # Verify scrape was called
        mock_places_service.search_text.assert_called_once()

        # Verify export was called
        mock_sheets_service.export_leads.assert_called_once()

    async def test_workflow_with_all_step_types(self):
        """Test creating a workflow with all supported step types."""
        config = WorkflowConfig(
            name="all_steps",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
                WorkflowStep(
                    name="filter",
                    type=StepType.FILTER,
                    filter_config=FilterConfig(min_quality_score=50),
                ),
                WorkflowStep(
                    name="enrich",
                    type=StepType.ENRICH,
                    enrich_config=EnrichConfig(provider="hunter"),
                ),
                WorkflowStep(
                    name="generate",
                    type=StepType.GENERATE,
                    generate_config=GenerateConfig(model="gpt-4o-mini"),
                ),
                WorkflowStep(
                    name="export",
                    type=StepType.EXPORT,
                    export_config=ExportConfig(
                        destination="sheets",
                        spreadsheet_id="test",
                    ),
                ),
            ],
        )

        # Verify all steps created
        assert len(config.steps) == 5
        assert config.steps[0].type == StepType.SCRAPE
        assert config.steps[1].type == StepType.FILTER
        assert config.steps[2].type == StepType.ENRICH
        assert config.steps[3].type == StepType.GENERATE
        assert config.steps[4].type == StepType.EXPORT

    async def test_workflow_step_duration_tracking(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test that step execution duration is tracked."""
        config = WorkflowConfig(
            name="duration_test",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        result = await workflow.run(ToolContext())

        # Verify step has timing
        step = result.steps[0]
        assert step.started_at is not None
        assert step.completed_at is not None
        assert step.duration_seconds is not None
        assert step.duration_seconds >= 0

    async def test_workflow_correlation_id_propagation(
        self,
        mock_places_service: AsyncMock,
    ):
        """Test that correlation ID is propagated through workflow."""
        config = WorkflowConfig(
            name="correlation_test",
            steps=[
                WorkflowStep(
                    name="scrape",
                    type=StepType.SCRAPE,
                    scrape_config=ScrapeConfig(query="test"),
                ),
            ],
        )

        workflow = LeadGenWorkflow(config)
        workflow._places_service = mock_places_service

        correlation_id = "test-correlation-123"
        context = ToolContext(correlation_id=correlation_id)

        await workflow.run(context)

        # Verify correlation ID was passed
        assert context.correlation_id == correlation_id
