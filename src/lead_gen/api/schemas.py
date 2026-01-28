"""
Pydantic v2 schemas for API request/response models.

These schemas are separate from domain models to allow
API-specific validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# Generic type for paginated responses
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: T | None = None
    error: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response with metadata."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    correlation_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: str
    error_code: str | None = None
    details: dict[str, Any] | None = None
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Lead Schemas

class LeadStatusEnum(str, Enum):
    """Lead status for API."""

    NEW = "new"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class LeadSourceEnum(str, Enum):
    """Lead source for API."""

    GOOGLE_PLACES = "google_places"
    YELP = "yelp"
    MANUAL = "manual"
    IMPORT = "import"
    REFERRAL = "referral"


class LocationSchema(BaseModel):
    """Location data schema."""

    model_config = ConfigDict(from_attributes=True)

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    formatted_address: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    country_code: str = ""


class BusinessMetricsSchema(BaseModel):
    """Business metrics schema."""

    model_config = ConfigDict(from_attributes=True)

    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    price_level: int | None = Field(default=None, ge=0, le=4)


class LeadResponse(BaseModel):
    """Lead response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    place_id: str = ""
    name: str
    phone: str = ""
    website: str | None = None
    email: str | None = None
    location: LocationSchema | None = None
    business_type: str = ""
    categories: list[str] = Field(default_factory=list)
    metrics: BusinessMetricsSchema = Field(default_factory=BusinessMetricsSchema)
    source: LeadSourceEnum = LeadSourceEnum.GOOGLE_PLACES
    status: LeadStatusEnum = LeadStatusEnum.NEW
    quality_score: int = 0
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    scraped_at: datetime
    status_updated_at: datetime


class LeadCreateRequest(BaseModel):
    """Request schema for creating a lead."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=300)
    phone: str = ""
    website: HttpUrl | None = None
    email: str | None = None
    business_type: str = ""
    categories: list[str] = Field(default_factory=list)
    location: LocationSchema | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    source: LeadSourceEnum = LeadSourceEnum.MANUAL


class LeadUpdateRequest(BaseModel):
    """Request schema for updating a lead."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: LeadStatusEnum | None = None
    tags: list[str] | None = None
    notes: str | None = None
    email: str | None = None
    phone: str | None = None


class LeadFilterParams(BaseModel):
    """Lead filtering parameters."""

    status: LeadStatusEnum | None = None
    source: LeadSourceEnum | None = None
    business_type: str | None = None
    min_quality_score: int | None = Field(default=None, ge=0, le=100)
    has_email: bool | None = None
    has_phone: bool | None = None
    city: str | None = None
    tags: list[str] | None = None
    search: str | None = Field(default=None, description="Search in name, phone, email")


class LeadExportRequest(BaseModel):
    """Request schema for exporting leads."""

    format: str = Field(default="csv", pattern="^(csv|json|sheets)$")
    spreadsheet_id: str | None = None
    worksheet_name: str = "Leads Export"
    filters: LeadFilterParams | None = None
    fields: list[str] | None = None


class LeadExportResponse(BaseModel):
    """Response schema for lead export."""

    format: str
    exported_count: int
    file_path: str | None = None
    spreadsheet_url: str | None = None
    correlation_id: str | None = None


# Workflow Schemas

class WorkflowStatusEnum(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepTypeEnum(str, Enum):
    """Workflow step types."""

    SCRAPE = "scrape"
    ENRICH = "enrich"
    GENERATE = "generate"
    EXPORT = "export"
    FILTER = "filter"
    TRANSFORM = "transform"
    NOTIFY = "notify"
    WAIT = "wait"


class WorkflowStepSchema(BaseModel):
    """Workflow step schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: StepTypeEnum
    enabled: bool = True
    status: WorkflowStatusEnum = WorkflowStatusEnum.PENDING
    timeout_seconds: int = 300
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str = ""
    output_count: int = 0


class WorkflowResponse(BaseModel):
    """Workflow response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    steps: list[WorkflowStepSchema]
    status: WorkflowStatusEnum = WorkflowStatusEnum.PENDING
    enabled: bool = True
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_leads_processed: int = 0
    progress_percent: float = 0.0
    error_message: str = ""
    tags: list[str] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    """Request schema for running a workflow."""

    dry_run: bool = False
    max_leads: int | None = Field(default=None, ge=1, le=1000)
    overrides: dict[str, Any] | None = None


class WorkflowRunResponse(BaseModel):
    """Response schema for workflow run."""

    workflow_id: str
    execution_id: str
    status: WorkflowStatusEnum
    message: str
    started_at: datetime
    correlation_id: str | None = None


class WorkflowStatusResponse(BaseModel):
    """Response schema for workflow status."""

    workflow_id: str
    execution_id: str | None
    status: WorkflowStatusEnum
    current_step: str | None = None
    progress_percent: float = 0.0
    leads_processed: int = 0
    started_at: datetime | None = None
    elapsed_seconds: float | None = None
    estimated_remaining_seconds: float | None = None
    error_message: str | None = None
    correlation_id: str | None = None


# Settings Schemas

class RateLimitSettingsSchema(BaseModel):
    """Rate limit settings schema."""

    model_config = ConfigDict(from_attributes=True)

    google_places: int = Field(default=60, ge=1, le=1000)
    openai: int = Field(default=60, ge=1, le=1000)
    hunter: int = Field(default=30, ge=1, le=1000)
    sheets: int = Field(default=60, ge=1, le=1000)


class GDPRSettingsSchema(BaseModel):
    """GDPR settings schema."""

    model_config = ConfigDict(from_attributes=True)

    retention_days: int = Field(default=90, ge=1, le=365)
    legal_basis: str = "legitimate_interest"
    dpo_email: str = ""
    enable_audit_log: bool = True


class OpenAISettingsSchema(BaseModel):
    """OpenAI settings schema."""

    model_config = ConfigDict(from_attributes=True)

    model: str = "gpt-4o-mini"
    max_tokens: int = Field(default=500, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class SettingsResponse(BaseModel):
    """Settings response schema (secrets masked)."""

    model_config = ConfigDict(from_attributes=True)

    environment: str
    log_level: str
    rate_limits: RateLimitSettingsSchema
    gdpr: GDPRSettingsSchema
    openai: OpenAISettingsSchema
    # API keys are shown as masked
    google_places_api_key_configured: bool = False
    openai_api_key_configured: bool = False
    hunter_api_key_configured: bool = False
    google_service_account_configured: bool = False


class SettingsUpdateRequest(BaseModel):
    """Request schema for updating settings."""

    rate_limits: RateLimitSettingsSchema | None = None
    gdpr: GDPRSettingsSchema | None = None
    openai: OpenAISettingsSchema | None = None


class APIKeyValidationResult(BaseModel):
    """Result of API key validation."""

    service: str
    valid: bool
    message: str


class SettingsValidateResponse(BaseModel):
    """Response schema for settings validation."""

    all_valid: bool
    results: list[APIKeyValidationResult]
    correlation_id: str | None = None


# Health Schemas

class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Individual service health status."""

    name: str
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus
    version: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    status: HealthStatus
    services: list[ServiceHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
