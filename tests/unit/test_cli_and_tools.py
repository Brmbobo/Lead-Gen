"""
Unit tests for CLI commands and tools module.

Tests cover:
- CLI commands (main, run, validate_env, init, version)
- ToolContext class
- ToolResult class
- BaseTool abstract class
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from lead_gen.cli import main, run, validate_env, init, version
from lead_gen.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
    ToolStatus,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CliRunner for testing Click commands."""
    return CliRunner()


@pytest.fixture
def sample_tool_context() -> ToolContext:
    """Create a sample ToolContext for testing."""
    with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
        mock_gdpr.return_value = MagicMock()
        return ToolContext(
            correlation_id="test-correlation-123",
            dry_run=False,
        )


@pytest.fixture
def dry_run_context() -> ToolContext:
    """Create a dry-run ToolContext for testing."""
    with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
        mock_gdpr.return_value = MagicMock()
        return ToolContext(
            correlation_id="test-dry-run-456",
            dry_run=True,
        )


@pytest.fixture
def mock_workflow_config() -> MagicMock:
    """Create a mock WorkflowConfig for testing."""
    mock_config = MagicMock()
    mock_config.name = "test_workflow"
    mock_config.description = "Test workflow description"
    mock_config.total_steps = 3
    mock_config.steps = [
        MagicMock(name="step1", type=MagicMock(value="scrape"), enabled=True),
        MagicMock(name="step2", type=MagicMock(value="enrich"), enabled=True),
        MagicMock(name="step3", type=MagicMock(value="export"), enabled=False),
    ]
    mock_config.validate_workflow.return_value = []
    return mock_config


@pytest.fixture
def mock_workflow_result() -> MagicMock:
    """Create a mock workflow execution result."""
    result = MagicMock()
    result.status = MagicMock(value="completed")
    result.total_leads_processed = 25
    result.completed_steps = 3
    result.total_steps = 3
    result.error_message = None
    return result


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.environment = MagicMock(value="development")
    settings.log_level = MagicMock(value="INFO")
    settings.secret_backend = MagicMock(value="env")
    settings.gdpr = MagicMock(retention_days=90)
    settings.rate_limits = MagicMock(google_places=60, openai=60)
    settings.openai = MagicMock(model="gpt-4o-mini")
    settings.google_service_account_path = "/path/to/sa.json"
    settings.hunter_api_key = MagicMock()
    settings.hunter_api_key.get_secret_value.return_value = "test-hunter-key"
    settings.validate_required_keys.return_value = []
    return settings


# ==============================================================================
# Concrete BaseTool Implementation for Testing
# ==============================================================================


class MockTool(BaseTool[dict, dict]):
    """Concrete implementation of BaseTool for testing purposes."""

    name = "mock_tool"
    description = "A mock tool for testing"
    version = "1.0.0"

    def __init__(self, fail: bool = False, fail_validation: bool = False):
        super().__init__()
        self._fail = fail
        self._fail_validation = fail_validation

    async def _execute(
        self,
        input_data: dict,
        context: ToolContext,
    ) -> ToolResult[dict]:
        """Execute the mock tool."""
        if self._fail:
            raise ValueError("Mock execution failure")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            output={"processed": input_data},
            items_processed=1,
            items_failed=0,
        )

    def _validate_input(self, input_data: dict) -> str | None:
        """Validate input data."""
        if self._fail_validation:
            return "Mock validation error"
        if input_data is None:
            return "Input data is required"
        if not isinstance(input_data, dict):
            return "Input must be a dictionary"
        return None


class PartialSuccessTool(BaseTool[dict, dict]):
    """Tool that returns partial success."""

    name = "partial_tool"
    description = "A tool that returns partial success"
    version = "1.0.0"

    async def _execute(
        self,
        input_data: dict,
        context: ToolContext,
    ) -> ToolResult[dict]:
        """Execute with partial success."""
        return ToolResult(
            status=ToolStatus.PARTIAL,
            output={"partial": True},
            items_processed=5,
            items_failed=2,
        )


# ==============================================================================
# CLI Tests
# ==============================================================================


class TestCLIMain:
    """Tests for the main CLI group."""

    def test_main_group_invocation(self, cli_runner: CliRunner) -> None:
        """Test that main group can be invoked."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Lead-Gen" in result.output
        assert "lead generation platform" in result.output.lower()

    def test_main_shows_commands(self, cli_runner: CliRunner) -> None:
        """Test that main shows available commands."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "validate-env" in result.output
        assert "init" in result.output
        assert "version" in result.output


class TestCLIRun:
    """Tests for the run command."""

    def test_run_workflow_not_found(self, cli_runner: CliRunner) -> None:
        """Test run command with non-existent file."""
        result = cli_runner.invoke(main, ["run", "nonexistent.yaml"])
        assert result.exit_code != 0

    def test_run_dry_run_mode(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run command with --dry-run flag."""
        # Create a more complete mock that Rich can render
        mock_config = MagicMock()
        mock_config.name = "test_workflow"
        mock_config.description = "Test workflow"
        mock_config.total_steps = 2

        # Create mock step type that returns proper string value
        mock_step_type = MagicMock()
        mock_step_type.value = "scrape"

        mock_step = MagicMock()
        mock_step.name = "step1"
        mock_step.type = mock_step_type
        mock_step.enabled = True

        mock_config.steps = [mock_step]
        mock_config.validate_workflow.return_value = []

        with patch("lead_gen.models.workflow.WorkflowConfig.from_yaml") as mock_from_yaml:
            mock_from_yaml.return_value = mock_config

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("name: test\nsteps: []")
                f.flush()

                result = cli_runner.invoke(main, ["run", f.name, "--dry-run"])

                # Should show dry run mode indication and not execute
                assert "Dry run mode" in result.output or "Dry Run" in result.output

    def test_run_with_validation_errors(
        self,
        cli_runner: CliRunner,
        mock_workflow_config: MagicMock,
    ) -> None:
        """Test run command when configuration has validation errors."""
        mock_workflow_config.validate_workflow.return_value = [
            "Missing required step",
            "Invalid configuration",
        ]
        with patch("lead_gen.models.workflow.WorkflowConfig.from_yaml") as mock_from_yaml:
            mock_from_yaml.return_value = mock_workflow_config

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("name: test\nsteps: []")
                f.flush()

                result = cli_runner.invoke(main, ["run", f.name])

                assert result.exit_code == 1
                assert "Configuration errors" in result.output
                assert "Missing required step" in result.output

    def test_run_successful_workflow(
        self,
        cli_runner: CliRunner,
        mock_workflow_config: MagicMock,
        mock_workflow_result: MagicMock,
    ) -> None:
        """Test successful workflow execution."""
        with patch("lead_gen.models.workflow.WorkflowConfig.from_yaml") as mock_from_yaml, \
             patch("lead_gen.workflows.base.WorkflowRunner") as mock_runner_cls, \
             patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:

            mock_from_yaml.return_value = mock_workflow_config
            mock_gdpr.return_value = MagicMock()

            # Setup runner mock
            mock_runner = MagicMock()

            async def mock_run_async(*args, **kwargs):
                return mock_workflow_result

            mock_runner.run = mock_run_async
            mock_runner_cls.return_value = mock_runner

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("name: test\nsteps: []")
                f.flush()

                result = cli_runner.invoke(main, ["run", f.name])

                # Check output contains expected information
                assert "Workflow Configuration" in result.output or "Workflow" in result.output

    def test_run_with_exception(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run command when an exception occurs."""
        with patch("lead_gen.models.workflow.WorkflowConfig.from_yaml") as mock_from_yaml:
            mock_from_yaml.side_effect = Exception("YAML parse error")

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("invalid yaml content")
                f.flush()

                result = cli_runner.invoke(main, ["run", f.name])
                assert result.exit_code == 1
                assert "Error" in result.output

    def test_run_verbose_flag(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test run command with --verbose flag shows stack trace on error."""
        with patch("lead_gen.models.workflow.WorkflowConfig.from_yaml") as mock_from_yaml:
            mock_from_yaml.side_effect = Exception("Test error")

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("name: test")
                f.flush()

                result = cli_runner.invoke(main, ["run", f.name, "--verbose"])
                assert result.exit_code == 1


class TestCLIValidateEnv:
    """Tests for the validate_env command."""

    def test_validate_env_all_keys_present(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
    ) -> None:
        """Test validate_env when all keys are present."""
        with patch("lead_gen.core.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            result = cli_runner.invoke(main, ["validate-env"])

            assert result.exit_code == 0
            assert "All required configuration is present" in result.output

    def test_validate_env_missing_keys(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
    ) -> None:
        """Test validate_env when keys are missing."""
        mock_settings.validate_required_keys.return_value = [
            "GOOGLE_PLACES_API_KEY",
            "OPENAI_API_KEY",
        ]
        with patch("lead_gen.core.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            result = cli_runner.invoke(main, ["validate-env"])

            assert result.exit_code == 1
            assert "Missing required keys" in result.output
            assert "GOOGLE_PLACES_API_KEY" in result.output

    def test_validate_env_displays_configuration(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
    ) -> None:
        """Test that validate_env displays configuration settings."""
        with patch("lead_gen.core.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            result = cli_runner.invoke(main, ["validate-env"])

            assert "Environment" in result.output
            assert "Settings" in result.output

    def test_validate_env_exception_handling(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test validate_env handles exceptions gracefully."""
        with patch("lead_gen.core.config.get_settings") as mock_get_settings:
            mock_get_settings.side_effect = Exception("Config load error")

            result = cli_runner.invoke(main, ["validate-env"])

            assert result.exit_code == 1
            assert "Error loading configuration" in result.output

    def test_validate_env_hunter_optional(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
    ) -> None:
        """Test that Hunter.io key is shown as optional."""
        mock_settings.hunter_api_key.get_secret_value.return_value = ""
        with patch("lead_gen.core.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            result = cli_runner.invoke(main, ["validate-env"])

            assert "optional" in result.output.lower() or "Hunter" in result.output


class TestCLIInit:
    """Tests for the init command."""

    def test_init_creates_workflow_file(self, cli_runner: CliRunner) -> None:
        """Test that init creates a new workflow file."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["init", "test_workflow.yaml"])

            assert result.exit_code == 0
            assert "Created workflow configuration" in result.output
            assert Path("test_workflow.yaml").exists()

    def test_init_default_filename(self, cli_runner: CliRunner) -> None:
        """Test init with default filename."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["init"])

            assert result.exit_code == 0
            assert Path("workflow.yaml").exists()

    def test_init_overwrite_confirm_yes(self, cli_runner: CliRunner) -> None:
        """Test init overwrites existing file when confirmed."""
        with cli_runner.isolated_filesystem():
            # Create existing file
            Path("workflow.yaml").write_text("existing content")

            result = cli_runner.invoke(main, ["init"], input="y\n")

            assert result.exit_code == 0
            assert "Created workflow configuration" in result.output
            # Content should be overwritten
            content = Path("workflow.yaml").read_text()
            assert "existing content" not in content

    def test_init_overwrite_confirm_no(self, cli_runner: CliRunner) -> None:
        """Test init cancels when user declines overwrite."""
        with cli_runner.isolated_filesystem():
            # Create existing file
            original_content = "existing content"
            Path("workflow.yaml").write_text(original_content)

            result = cli_runner.invoke(main, ["init"], input="n\n")

            assert "Cancelled" in result.output
            # Content should remain unchanged
            assert Path("workflow.yaml").read_text() == original_content

    def test_init_shows_next_steps(self, cli_runner: CliRunner) -> None:
        """Test init shows next steps to user."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["init"])

            assert "Next steps" in result.output
            assert "lead-gen run" in result.output

    def test_init_workflow_content_valid(self, cli_runner: CliRunner) -> None:
        """Test that init creates valid workflow content."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["init"])

            content = Path("workflow.yaml").read_text()
            # Check key workflow components are present
            assert "name:" in content
            assert "steps:" in content
            assert "scrape" in content.lower() or "type:" in content


class TestCLIVersion:
    """Tests for the version command."""

    def test_version_displays_version(self, cli_runner: CliRunner) -> None:
        """Test that version command displays the version."""
        result = cli_runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "Lead-Gen version" in result.output


# ==============================================================================
# ToolContext Tests
# ==============================================================================


class TestToolContext:
    """Tests for ToolContext class."""

    def test_initialization_with_defaults(self) -> None:
        """Test ToolContext initializes with default values."""
        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_gdpr.return_value = MagicMock()
            context = ToolContext()

            assert context.correlation_id is not None
            assert context.dry_run is False
            assert context.gdpr_manager is not None
            assert context.leads == []
            assert context.messages == []
            assert context.enriched_leads == []
            assert context.api_calls == 0
            assert context.tokens_used == 0
            assert context.cost_usd == 0.0
            assert context.start_time is not None

    def test_initialization_with_custom_values(self) -> None:
        """Test ToolContext initializes with custom values."""
        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_gdpr.return_value = MagicMock()
            context = ToolContext(
                correlation_id="custom-id-123",
                dry_run=True,
            )

            assert context.correlation_id == "custom-id-123"
            assert context.dry_run is True

    def test_add_lead(self, sample_tool_context: ToolContext) -> None:
        """Test add_lead adds lead to context."""
        lead = {"id": "lead-1", "name": "Test Lead"}
        sample_tool_context.add_lead(lead)

        assert len(sample_tool_context.leads) == 1
        assert sample_tool_context.leads[0] == lead

    def test_add_multiple_leads(self, sample_tool_context: ToolContext) -> None:
        """Test adding multiple leads."""
        for i in range(5):
            sample_tool_context.add_lead({"id": f"lead-{i}"})

        assert len(sample_tool_context.leads) == 5

    def test_add_message(self, sample_tool_context: ToolContext) -> None:
        """Test add_message adds message to context."""
        message = {"id": "msg-1", "content": "Test message"}
        sample_tool_context.add_message(message)

        assert len(sample_tool_context.messages) == 1
        assert sample_tool_context.messages[0] == message

    def test_add_enriched_lead(self, sample_tool_context: ToolContext) -> None:
        """Test add_enriched_lead adds enriched lead to context."""
        enriched = {"id": "lead-1", "email": "test@example.com"}
        sample_tool_context.add_enriched_lead(enriched)

        assert len(sample_tool_context.enriched_leads) == 1
        assert sample_tool_context.enriched_leads[0] == enriched

    def test_track_api_call_basic(self, sample_tool_context: ToolContext) -> None:
        """Test track_api_call increments counters."""
        sample_tool_context.track_api_call()

        assert sample_tool_context.api_calls == 1
        assert sample_tool_context.tokens_used == 0
        assert sample_tool_context.cost_usd == 0.0

    def test_track_api_call_with_tokens_and_cost(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test track_api_call with tokens and cost."""
        sample_tool_context.track_api_call(tokens=150, cost=0.0015)

        assert sample_tool_context.api_calls == 1
        assert sample_tool_context.tokens_used == 150
        assert sample_tool_context.cost_usd == 0.0015

    def test_track_multiple_api_calls(self, sample_tool_context: ToolContext) -> None:
        """Test multiple API calls accumulate correctly."""
        sample_tool_context.track_api_call(tokens=100, cost=0.001)
        sample_tool_context.track_api_call(tokens=200, cost=0.002)
        sample_tool_context.track_api_call(tokens=50, cost=0.0005)

        assert sample_tool_context.api_calls == 3
        assert sample_tool_context.tokens_used == 350
        assert sample_tool_context.cost_usd == pytest.approx(0.0035)

    def test_elapsed_seconds(self, sample_tool_context: ToolContext) -> None:
        """Test elapsed_seconds property."""
        elapsed = sample_tool_context.elapsed_seconds

        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_elapsed_seconds_increases(self, sample_tool_context: ToolContext) -> None:
        """Test elapsed_seconds increases over time."""
        initial = sample_tool_context.elapsed_seconds
        import time

        time.sleep(0.01)  # Small delay
        later = sample_tool_context.elapsed_seconds

        assert later >= initial

    def test_gdpr_manager_initialized(self) -> None:
        """Test GDPR manager is initialized if not provided."""
        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_manager = MagicMock()
            mock_gdpr.return_value = mock_manager

            context = ToolContext()

            mock_gdpr.assert_called_once()
            assert context.gdpr_manager == mock_manager

    def test_gdpr_manager_custom(self) -> None:
        """Test custom GDPR manager is preserved."""
        custom_manager = MagicMock()

        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            context = ToolContext(gdpr_manager=custom_manager)

            assert context.gdpr_manager == custom_manager
            # get_gdpr_manager should not be called when custom manager is provided

    def test_correlation_id_is_uuid(self) -> None:
        """Test that correlation_id is auto-generated as UUID."""
        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_gdpr.return_value = MagicMock()
            context = ToolContext()

            # Should be a valid UUID string (36 chars with hyphens)
            assert len(context.correlation_id) == 36
            assert context.correlation_id.count("-") == 4


# ==============================================================================
# ToolResult Tests
# ==============================================================================


class TestToolResult:
    """Tests for ToolResult class."""

    def test_is_success_for_success_status(self) -> None:
        """Test is_success returns True for SUCCESS status."""
        result = ToolResult(status=ToolStatus.SUCCESS)
        assert result.is_success is True

    def test_is_success_for_partial_status(self) -> None:
        """Test is_success returns True for PARTIAL status."""
        result = ToolResult(status=ToolStatus.PARTIAL)
        assert result.is_success is True

    def test_is_success_for_failed_status(self) -> None:
        """Test is_success returns False for FAILED status."""
        result = ToolResult(status=ToolStatus.FAILED)
        assert result.is_success is False

    def test_is_success_for_skipped_status(self) -> None:
        """Test is_success returns False for SKIPPED status."""
        result = ToolResult(status=ToolStatus.SKIPPED)
        assert result.is_success is False

    def test_success_rate_all_processed(self) -> None:
        """Test success_rate when all items processed."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            items_processed=10,
            items_failed=0,
        )
        assert result.success_rate == 100.0

    def test_success_rate_all_failed(self) -> None:
        """Test success_rate when all items failed."""
        result = ToolResult(
            status=ToolStatus.FAILED,
            items_processed=0,
            items_failed=10,
        )
        assert result.success_rate == 0.0

    def test_success_rate_partial(self) -> None:
        """Test success_rate with partial success."""
        result = ToolResult(
            status=ToolStatus.PARTIAL,
            items_processed=7,
            items_failed=3,
        )
        assert result.success_rate == 70.0

    def test_success_rate_zero_items(self) -> None:
        """Test success_rate with zero items."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            items_processed=0,
            items_failed=0,
        )
        assert result.success_rate == 0.0

    def test_result_with_output(self) -> None:
        """Test ToolResult with output data."""
        output_data = {"leads": [1, 2, 3], "count": 3}
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            output=output_data,
        )
        assert result.output == output_data

    def test_result_with_error_message(self) -> None:
        """Test ToolResult with error message."""
        result = ToolResult(
            status=ToolStatus.FAILED,
            error_message="Connection timeout",
        )
        assert result.error_message == "Connection timeout"

    def test_result_with_metadata(self) -> None:
        """Test ToolResult with metadata."""
        metadata = {"request_id": "abc123", "retry_count": 2}
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            metadata=metadata,
        )
        assert result.metadata == metadata

    def test_execution_time_tracking(self) -> None:
        """Test execution time is tracked."""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            execution_time_ms=150.5,
        )
        assert result.execution_time_ms == 150.5

    def test_result_default_values(self) -> None:
        """Test ToolResult default values."""
        result = ToolResult(status=ToolStatus.SUCCESS)

        assert result.output is None
        assert result.error_message == ""
        assert result.items_processed == 0
        assert result.items_failed == 0
        assert result.execution_time_ms == 0.0
        assert result.metadata == {}


# ==============================================================================
# BaseTool Tests
# ==============================================================================


class TestBaseTool:
    """Tests for BaseTool abstract class."""

    @pytest.mark.asyncio
    async def test_run_successful_execution(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test successful tool execution."""
        tool = MockTool()
        input_data = {"key": "value"}

        result = await tool.run(input_data, sample_tool_context)

        assert result.status == ToolStatus.SUCCESS
        assert result.output == {"processed": input_data}
        assert result.items_processed == 1
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_run_with_dry_run_mode(
        self, dry_run_context: ToolContext
    ) -> None:
        """Test tool execution in dry run mode."""
        tool = MockTool()
        input_data = {"key": "value"}

        result = await tool.run(input_data, dry_run_context)

        assert result.status == ToolStatus.SKIPPED
        assert "Dry run mode" in result.error_message
        assert result.metadata.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_run_input_validation_failure(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test tool execution with validation failure."""
        tool = MockTool(fail_validation=True)
        input_data = {"key": "value"}

        result = await tool.run(input_data, sample_tool_context)

        assert result.status == ToolStatus.FAILED
        assert "Input validation failed" in result.error_message
        assert "Mock validation error" in result.error_message

    @pytest.mark.asyncio
    async def test_run_null_input_validation(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test tool execution with null input."""
        tool = MockTool()

        result = await tool.run(None, sample_tool_context)

        assert result.status == ToolStatus.FAILED
        assert "Input validation failed" in result.error_message

    @pytest.mark.asyncio
    async def test_run_exception_handling(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test tool handles execution exceptions."""
        tool = MockTool(fail=True)
        input_data = {"key": "value"}

        result = await tool.run(input_data, sample_tool_context)

        assert result.status == ToolStatus.FAILED
        assert "Mock execution failure" in result.error_message
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_run_creates_context_if_none(self) -> None:
        """Test tool creates context if none provided."""
        tool = MockTool()
        input_data = {"key": "value"}

        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_gdpr.return_value = MagicMock()
            result = await tool.run(input_data, None)

        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_run_logs_start_and_complete(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test tool logs start and completion."""
        tool = MockTool()
        input_data = {"key": "value"}

        with patch.object(tool, "_logger") as mock_logger:
            await tool.run(input_data, sample_tool_context)

            # Check logging calls
            mock_logger.info.assert_called()
            call_args_list = [call[0][0] for call in mock_logger.info.call_args_list]
            assert "tool_started" in call_args_list
            assert "tool_completed" in call_args_list

    @pytest.mark.asyncio
    async def test_run_logs_failure(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test tool logs failures."""
        tool = MockTool(fail=True)
        input_data = {"key": "value"}

        with patch.object(tool, "_logger") as mock_logger:
            await tool.run(input_data, sample_tool_context)

            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert error_call[0][0] == "tool_failed"

    @pytest.mark.asyncio
    async def test_partial_success_tool(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test tool that returns partial success."""
        tool = PartialSuccessTool()
        input_data = {"key": "value"}

        result = await tool.run(input_data, sample_tool_context)

        assert result.status == ToolStatus.PARTIAL
        assert result.is_success is True
        assert result.items_processed == 5
        assert result.items_failed == 2
        assert result.success_rate == pytest.approx(71.43, rel=0.01)

    def test_tool_repr(self) -> None:
        """Test tool string representation."""
        tool = MockTool()
        repr_str = repr(tool)

        assert "MockTool" in repr_str
        assert "mock_tool" in repr_str
        assert "1.0.0" in repr_str

    def test_tool_attributes(self) -> None:
        """Test tool has correct attributes."""
        tool = MockTool()

        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert tool.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_execution_time_tracking(
        self, sample_tool_context: ToolContext
    ) -> None:
        """Test execution time is properly tracked."""
        tool = MockTool()
        input_data = {"key": "value"}

        result = await tool.run(input_data, sample_tool_context)

        assert result.execution_time_ms >= 0
        assert isinstance(result.execution_time_ms, float)

    @pytest.mark.asyncio
    async def test_dry_run_includes_input_preview(
        self, dry_run_context: ToolContext
    ) -> None:
        """Test dry run includes truncated input preview in metadata."""
        tool = MockTool()
        input_data = {"key": "value", "long_data": "x" * 200}

        result = await tool.run(input_data, dry_run_context)

        assert "input" in result.metadata
        # Input should be truncated to 100 chars
        assert len(result.metadata["input"]) <= 100


# ==============================================================================
# ToolStatus Tests
# ==============================================================================


class TestToolStatus:
    """Tests for ToolStatus enum."""

    def test_status_values(self) -> None:
        """Test ToolStatus has correct values."""
        assert ToolStatus.SUCCESS.value == "success"
        assert ToolStatus.PARTIAL.value == "partial"
        assert ToolStatus.FAILED.value == "failed"
        assert ToolStatus.SKIPPED.value == "skipped"

    def test_status_is_string_enum(self) -> None:
        """Test ToolStatus inherits from str."""
        # ToolStatus inherits from str, so it can be compared to strings
        assert ToolStatus.SUCCESS == "success"
        assert ToolStatus.PARTIAL == "partial"
        assert ToolStatus.FAILED == "failed"
        assert ToolStatus.SKIPPED == "skipped"

    def test_status_enum_members(self) -> None:
        """Test all ToolStatus enum members are present."""
        assert hasattr(ToolStatus, "SUCCESS")
        assert hasattr(ToolStatus, "PARTIAL")
        assert hasattr(ToolStatus, "FAILED")
        assert hasattr(ToolStatus, "SKIPPED")


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_full_init_and_validate_flow(self, cli_runner: CliRunner) -> None:
        """Test complete flow: init then validate configuration."""
        with cli_runner.isolated_filesystem():
            # Initialize workflow
            init_result = cli_runner.invoke(main, ["init"])
            assert init_result.exit_code == 0
            assert Path("workflow.yaml").exists()

            # Verify workflow file has content
            content = Path("workflow.yaml").read_text()
            assert "name:" in content
            assert "steps:" in content


class TestToolIntegration:
    """Integration tests for tool components."""

    @pytest.mark.asyncio
    async def test_tool_context_full_workflow(self) -> None:
        """Test ToolContext through a simulated workflow."""
        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_gdpr.return_value = MagicMock()
            context = ToolContext()

            # Simulate workflow execution
            for i in range(5):
                context.add_lead({"id": f"lead-{i}", "name": f"Lead {i}"})
                context.track_api_call(tokens=100, cost=0.001)

            for i in range(3):
                context.add_enriched_lead({"id": f"lead-{i}", "email": f"lead{i}@test.com"})
                context.track_api_call(tokens=50, cost=0.0005)

            for i in range(5):
                context.add_message({"id": f"msg-{i}", "lead_id": f"lead-{i}"})
                context.track_api_call(tokens=200, cost=0.002)

            # Verify final state
            assert len(context.leads) == 5
            assert len(context.enriched_leads) == 3
            assert len(context.messages) == 5
            assert context.api_calls == 13
            assert context.tokens_used == 5 * 100 + 3 * 50 + 5 * 200
            assert context.cost_usd == pytest.approx(5 * 0.001 + 3 * 0.0005 + 5 * 0.002)

    @pytest.mark.asyncio
    async def test_tool_chaining(self) -> None:
        """Test multiple tools can be run in sequence with shared context."""
        with patch("lead_gen.tools.base.get_gdpr_manager") as mock_gdpr:
            mock_gdpr.return_value = MagicMock()
            context = ToolContext()

            tool1 = MockTool()
            tool2 = MockTool()
            tool3 = PartialSuccessTool()

            # Run tools in sequence
            result1 = await tool1.run({"step": 1}, context)
            result2 = await tool2.run({"step": 2}, context)
            result3 = await tool3.run({"step": 3}, context)

            # All should complete
            assert result1.status == ToolStatus.SUCCESS
            assert result2.status == ToolStatus.SUCCESS
            assert result3.status == ToolStatus.PARTIAL

            # Context is shared
            assert context.correlation_id is not None
