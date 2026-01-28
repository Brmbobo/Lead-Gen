"""
Workflow configuration models.

Provides YAML-compatible workflow definitions for:
- Multi-step lead generation pipelines
- Configurable scraping, enrichment, and export
- Error handling and retry configuration
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StepType(str, Enum):
    """Types of workflow steps."""

    SCRAPE = "scrape"
    ENRICH = "enrich"
    GENERATE = "generate"
    EXPORT = "export"
    FILTER = "filter"
    TRANSFORM = "transform"
    NOTIFY = "notify"
    WAIT = "wait"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetryPolicy(BaseModel):
    """Retry configuration for workflow steps."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=3, ge=0, le=10)
    base_delay_seconds: float = Field(default=1.0, ge=0.1, le=60)
    max_delay_seconds: float = Field(default=60.0, ge=1, le=600)
    exponential_base: float = Field(default=2.0, ge=1.5, le=4.0)


class RateLimitPolicy(BaseModel):
    """Rate limiting configuration."""

    model_config = ConfigDict(frozen=True)

    requests_per_minute: int = Field(default=60, ge=1, le=1000)
    burst_size: int | None = None


class ScrapeConfig(BaseModel):
    """Configuration for scraping step."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(..., min_length=1, description="Search query")
    location: str = Field(default="", description="Location filter")
    radius_km: int = Field(default=50, ge=1, le=500)
    max_results: int = Field(default=20, ge=1, le=60)
    language: str = Field(default="sk", max_length=2)
    region: str = Field(default="sk", max_length=2)
    business_types: list[str] = Field(default_factory=list)

    # Filters
    min_rating: float | None = Field(default=None, ge=0, le=5)
    min_reviews: int | None = Field(default=None, ge=0)
    open_now: bool = False

    @field_validator("business_types", mode="before")
    @classmethod
    def normalize_types(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []


class EnrichConfig(BaseModel):
    """Configuration for enrichment step."""

    model_config = ConfigDict(frozen=True)

    provider: Literal["hunter", "clearbit", "manual"] = "hunter"
    find_emails: bool = True
    verify_emails: bool = True
    find_social: bool = False
    max_enrichments_per_lead: int = Field(default=3, ge=1, le=10)


class GenerateConfig(BaseModel):
    """Configuration for message generation step."""

    model_config = ConfigDict(frozen=True)

    template_id: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, ge=50, le=2000)
    language: str = "sk"
    tone: str = "professional"

    # Personalization
    use_business_name: bool = True
    use_location: bool = True
    use_rating: bool = False

    # Generation settings
    generate_subject: bool = True
    generate_body: bool = True
    include_signature: bool = True

    # Sender info (for signature)
    sender_name: str = ""
    sender_company: str = ""
    sender_position: str = ""
    sender_email: str = ""
    sender_phone: str = ""

    # Content
    value_proposition: str = ""
    call_to_action: str = ""


class ExportConfig(BaseModel):
    """Configuration for export step."""

    model_config = ConfigDict(frozen=True)

    destination: Literal["sheets", "csv", "json", "database"] = "sheets"

    # Google Sheets
    spreadsheet_id: str = ""
    worksheet_name: str = "Leads"
    append_mode: bool = True  # Append vs overwrite

    # CSV/JSON
    output_path: str = ""
    include_messages: bool = True

    # Fields to export
    fields: list[str] = Field(default_factory=lambda: [
        "name", "phone", "email", "website", "address",
        "rating", "review_count", "status", "message_subject"
    ])


class FilterConfig(BaseModel):
    """Configuration for filter step."""

    model_config = ConfigDict(frozen=True)

    # Inclusion filters
    min_quality_score: int | None = Field(default=None, ge=0, le=100)
    required_fields: list[str] = Field(default_factory=list)
    include_statuses: list[str] = Field(default_factory=list)
    include_categories: list[str] = Field(default_factory=list)

    # Exclusion filters
    exclude_statuses: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)  # Email domains to exclude

    # Deduplication
    deduplicate_by: str = ""  # Field to deduplicate on


class WorkflowStep(BaseModel):
    """
    Single step in a workflow.

    Each step has a type and type-specific configuration.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = Field(..., min_length=1, max_length=100)
    type: StepType

    # Configuration (one of these based on type)
    scrape_config: ScrapeConfig | None = None
    enrich_config: EnrichConfig | None = None
    generate_config: GenerateConfig | None = None
    export_config: ExportConfig | None = None
    filter_config: FilterConfig | None = None

    # Execution
    enabled: bool = True
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)

    # Conditions
    run_if: str = ""  # Expression for conditional execution
    skip_on_error: bool = False  # Continue workflow if this step fails

    # Execution state (runtime)
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str = ""
    output_count: int = 0

    @model_validator(mode="after")
    def validate_config(self) -> "WorkflowStep":
        """Ensure appropriate config is set for step type."""
        config_map = {
            StepType.SCRAPE: self.scrape_config,
            StepType.ENRICH: self.enrich_config,
            StepType.GENERATE: self.generate_config,
            StepType.EXPORT: self.export_config,
            StepType.FILTER: self.filter_config,
        }

        expected_config = config_map.get(self.type)
        if self.type in config_map and expected_config is None:
            raise ValueError(f"Step type '{self.type.value}' requires {self.type.value}_config")

        return self

    @property
    def duration_seconds(self) -> float | None:
        """Calculate step duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class WorkflowConfig(BaseModel):
    """
    Complete workflow configuration.

    Can be loaded from YAML files.

    Example YAML:
        name: slovakia_dentists
        description: Scrape Slovak dentists and generate outreach
        steps:
          - name: scrape
            type: scrape
            scrape_config:
              query: "zubár"
              location: "Bratislava"
              max_results: 20
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    version: str = "1.0"

    # Steps
    steps: list[WorkflowStep] = Field(..., min_length=1)

    # Global settings
    rate_limits: dict[str, RateLimitPolicy] = Field(default_factory=dict)
    default_retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    # Execution settings
    parallel_steps: bool = False  # Allow parallel step execution
    stop_on_error: bool = True  # Stop workflow on first error
    max_leads: int | None = Field(default=None, ge=1)  # Global lead limit
    dry_run: bool = False  # Don't actually execute, just validate

    # Scheduling
    schedule_cron: str = ""  # Cron expression for scheduled runs
    enabled: bool = True

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    tags: list[str] = Field(default_factory=list)

    # Runtime state
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str = ""
    total_leads_processed: int = 0

    @classmethod
    def from_yaml(cls, path: str | Path) -> "WorkflowConfig":
        """
        Load workflow from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed WorkflowConfig
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def from_yaml_string(cls, yaml_string: str) -> "WorkflowConfig":
        """Load workflow from YAML string."""
        data = yaml.safe_load(yaml_string)
        return cls(**data)

    def to_yaml(self, path: str | Path | None = None) -> str:
        """
        Export workflow to YAML.

        Args:
            path: Optional path to save YAML file

        Returns:
            YAML string
        """
        # Convert to dict, excluding runtime state
        data = self.model_dump(
            exclude={
                "status",
                "current_step_index",
                "started_at",
                "completed_at",
                "error_message",
                "total_leads_processed",
            },
            exclude_none=True,
        )

        # Also exclude step runtime state
        for step in data.get("steps", []):
            for key in ["status", "started_at", "completed_at", "error_message", "output_count"]:
                step.pop(key, None)

        yaml_string = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

        if path:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(yaml_string)

        return yaml_string

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Get step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_step_by_name(self, name: str) -> WorkflowStep | None:
        """Get step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None

    @property
    def enabled_steps(self) -> list[WorkflowStep]:
        """Get only enabled steps."""
        return [s for s in self.steps if s.enabled]

    @property
    def total_steps(self) -> int:
        """Get total number of enabled steps."""
        return len(self.enabled_steps)

    @property
    def completed_steps(self) -> int:
        """Get number of completed steps."""
        return sum(1 for s in self.steps if s.status == WorkflowStatus.COMPLETED)

    @property
    def progress_percent(self) -> float:
        """Calculate workflow progress."""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100

    def validate_workflow(self) -> list[str]:
        """
        Validate workflow configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        # Check for at least one scrape step
        scrape_steps = [s for s in self.steps if s.type == StepType.SCRAPE]
        if not scrape_steps:
            errors.append("Workflow must have at least one scrape step")

        # Check step names are unique
        names = [s.name for s in self.steps]
        if len(names) != len(set(names)):
            errors.append("Step names must be unique")

        # Check export config has destination
        for step in self.steps:
            if step.type == StepType.EXPORT and step.export_config:
                if step.export_config.destination == "sheets":
                    if not step.export_config.spreadsheet_id:
                        errors.append(f"Step '{step.name}': sheets export requires spreadsheet_id")

        return errors


# Example workflow configuration
EXAMPLE_WORKFLOW_YAML = """
name: slovakia_dentists
description: Scrape Slovak dentists, enrich with emails, generate outreach, export to Sheets
version: "1.0"
tags:
  - dentists
  - slovakia
  - outreach

steps:
  - name: scrape_dentists
    type: scrape
    scrape_config:
      query: "zubár"
      location: "Bratislava, Slovakia"
      radius_km: 30
      max_results: 20
      language: sk
      region: sk
      min_rating: 4.0
      min_reviews: 5

  - name: filter_quality
    type: filter
    filter_config:
      min_quality_score: 50
      required_fields:
        - phone
      deduplicate_by: phone

  - name: enrich_emails
    type: enrich
    enrich_config:
      provider: hunter
      find_emails: true
      verify_emails: true
      max_enrichments_per_lead: 2

  - name: generate_messages
    type: generate
    generate_config:
      model: gpt-4o-mini
      language: sk
      tone: professional
      temperature: 0.7
      sender_name: "Ján Novák"
      sender_company: "Lead-Gen s.r.o."
      sender_email: "jan@lead-gen.sk"
      value_proposition: "Pomáhame zubným ambulanciám získať viac pacientov cez online marketing"

  - name: export_to_sheets
    type: export
    export_config:
      destination: sheets
      spreadsheet_id: "your-spreadsheet-id"
      worksheet_name: "Dentists - Bratislava"
      append_mode: true
      include_messages: true

rate_limits:
  google_places:
    requests_per_minute: 60
  openai:
    requests_per_minute: 60
  hunter:
    requests_per_minute: 30

default_retry_policy:
  max_retries: 3
  base_delay_seconds: 1.0
  max_delay_seconds: 30.0

stop_on_error: false
max_leads: 100
"""
