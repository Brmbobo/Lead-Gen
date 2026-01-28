"""
Lead domain models with GDPR compliance.

Provides comprehensive lead models with:
- Full Google Places data structure
- Email enrichment fields
- GDPR consent tracking
- Data retention metadata
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)


class LeadSource(str, Enum):
    """Source of lead data."""

    GOOGLE_PLACES = "google_places"
    YELP = "yelp"
    MANUAL = "manual"
    IMPORT = "import"
    REFERRAL = "referral"


class LeadStatus(str, Enum):
    """Lead processing status."""

    NEW = "new"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class GDPRConsent(BaseModel):
    """
    GDPR consent record.

    Tracks consent for data processing per Article 7.
    """

    model_config = ConfigDict(frozen=True)

    given: bool = False
    timestamp: datetime | None = None
    source: str | None = None  # Where consent was collected
    version: str | None = None  # Privacy policy version
    ip_address: str | None = None  # For audit (pseudonymized)
    withdrawable: bool = True

    @model_validator(mode="after")
    def validate_consent(self) -> "GDPRConsent":
        """Ensure timestamp is set when consent is given."""
        if self.given and self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc))
        return self


class Location(BaseModel):
    """Geographic location data."""

    model_config = ConfigDict(frozen=True)

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    formatted_address: str = ""
    street: str = ""
    city: str = ""
    region: str = ""  # State/Province
    postal_code: str = ""
    country: str = ""
    country_code: str = Field(default="", max_length=2)

    @computed_field
    @property
    def coordinates(self) -> tuple[float, float]:
        """Get coordinates as tuple."""
        return (self.latitude, self.longitude)


class OpeningHours(BaseModel):
    """Business opening hours."""

    model_config = ConfigDict(frozen=True)

    monday: str = ""
    tuesday: str = ""
    wednesday: str = ""
    thursday: str = ""
    friday: str = ""
    saturday: str = ""
    sunday: str = ""
    timezone: str = "Europe/Bratislava"

    def is_open_now(self) -> bool:
        """Check if business is currently open (simplified)."""
        # Simplified implementation - would need proper timezone handling
        return True


class BusinessMetrics(BaseModel):
    """Business metrics and ratings."""

    model_config = ConfigDict(frozen=True)

    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    price_level: int | None = Field(default=None, ge=0, le=4)
    user_ratings_total: int = Field(default=0, ge=0)

    @computed_field
    @property
    def rating_quality(self) -> str:
        """Categorize rating quality."""
        if self.rating is None:
            return "unknown"
        if self.rating >= 4.5:
            return "excellent"
        if self.rating >= 4.0:
            return "good"
        if self.rating >= 3.0:
            return "average"
        return "poor"


class Lead(BaseModel):
    """
    Business lead model.

    Represents a scraped business lead with full metadata.
    Includes GDPR compliance fields.

    Example:
        >>> lead = Lead(
        ...     name="Zubná Ambulancia Dr. Novák",
        ...     phone="+421901234567",
        ...     location=Location(latitude=48.1486, longitude=17.1077),
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))
    place_id: str = Field(default="", description="Google Places ID")

    # Core business info
    name: str = Field(..., min_length=1, max_length=300)
    phone: str = Field(default="")
    website: HttpUrl | None = None
    email: str | None = Field(default=None, description="Primary email (from enrichment)")

    # Location
    location: Location | None = None

    # Business details
    business_type: str = Field(default="", description="e.g., dentist, restaurant")
    categories: list[str] = Field(default_factory=list)
    metrics: BusinessMetrics = Field(default_factory=BusinessMetrics)
    opening_hours: OpeningHours | None = None

    # Source metadata
    source: LeadSource = LeadSource.GOOGLE_PLACES
    source_url: HttpUrl | None = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Processing status
    status: LeadStatus = LeadStatus.NEW
    status_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # GDPR Compliance
    gdpr_consent: GDPRConsent = Field(default_factory=GDPRConsent)
    gdpr_legal_basis: str = Field(default="legitimate_interest")
    gdpr_retention_until: datetime | None = None
    gdpr_pseudonymized_id: str = Field(default="", description="Hashed identifier for GDPR")

    # Processing metadata
    correlation_id: str | None = Field(default=None, description="Request correlation ID")
    tags: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalize phone number."""
        if not v:
            return v
        # Remove common formatting
        import re
        cleaned = re.sub(r"[\s\-\(\)\.]", "", v)
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validate and normalize email."""
        if not v:
            return None
        return v.lower().strip()

    @field_validator("categories", mode="before")
    @classmethod
    def normalize_categories(cls, v: Any) -> list[str]:
        """Normalize categories to list."""
        if isinstance(v, str):
            return [c.strip() for c in v.split(",") if c.strip()]
        return v or []

    @computed_field
    @property
    def display_name(self) -> str:
        """Get display-friendly name."""
        return self.name.strip()

    @computed_field
    @property
    def has_contact_info(self) -> bool:
        """Check if lead has usable contact information."""
        return bool(self.phone or self.email or self.website)

    @computed_field
    @property
    def quality_score(self) -> int:
        """Calculate lead quality score (0-100)."""
        score = 0

        # Basic info
        if self.name:
            score += 10
        if self.phone:
            score += 20
        if self.email:
            score += 25
        if self.website:
            score += 15

        # Location
        if self.location:
            score += 10
            if self.location.formatted_address:
                score += 5

        # Metrics
        if self.metrics.rating:
            score += 5
            if self.metrics.rating >= 4.0:
                score += 5
        if self.metrics.review_count > 10:
            score += 5

        return min(100, score)

    def update_status(self, new_status: LeadStatus) -> None:
        """Update lead status with timestamp."""
        self.status = new_status
        self.status_updated_at = datetime.now(timezone.utc)

    def to_export_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for export (e.g., Google Sheets).

        Excludes internal fields and flattens nested structures.
        """
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email or "",
            "website": str(self.website) if self.website else "",
            "address": self.location.formatted_address if self.location else "",
            "city": self.location.city if self.location else "",
            "country": self.location.country if self.location else "",
            "rating": self.metrics.rating,
            "review_count": self.metrics.review_count,
            "business_type": self.business_type,
            "categories": ", ".join(self.categories),
            "status": self.status.value,
            "quality_score": self.quality_score,
            "scraped_at": self.scraped_at.isoformat(),
            "source": self.source.value,
        }

    def to_gdpr_export(self) -> dict[str, Any]:
        """
        Export for GDPR data subject access request.

        Includes all personal data with processing metadata.
        """
        return {
            "personal_data": {
                "business_name": self.name,
                "phone": self.phone,
                "email": self.email,
                "website": str(self.website) if self.website else None,
                "address": self.location.formatted_address if self.location else None,
            },
            "processing_metadata": {
                "source": self.source.value,
                "legal_basis": self.gdpr_legal_basis,
                "collected_at": self.scraped_at.isoformat(),
                "retention_until": (
                    self.gdpr_retention_until.isoformat()
                    if self.gdpr_retention_until
                    else None
                ),
                "consent": self.gdpr_consent.model_dump() if self.gdpr_consent.given else None,
            },
        }


class EmailEnrichment(BaseModel):
    """Email enrichment data from Hunter.io or similar."""

    model_config = ConfigDict(frozen=True)

    email: str
    confidence: int = Field(default=0, ge=0, le=100)
    type: str = Field(default="generic")  # generic, personal, role-based
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    department: str = ""
    linkedin_url: HttpUrl | None = None
    twitter_handle: str = ""
    phone_number: str = ""
    verified: bool = False
    verified_at: datetime | None = None
    sources: list[str] = Field(default_factory=list)


class EnrichedLead(Lead):
    """
    Lead with email enrichment data.

    Extends Lead with additional contact information
    from Hunter.io or similar services.
    """

    # Enrichment data
    enrichments: list[EmailEnrichment] = Field(default_factory=list)
    enriched_at: datetime | None = None
    enrichment_source: str = ""  # hunter, clearbit, etc.

    # Additional contacts found
    additional_emails: list[str] = Field(default_factory=list)
    additional_phones: list[str] = Field(default_factory=list)

    # Company data (from enrichment)
    company_size: str = ""
    company_industry: str = ""
    company_founded: int | None = None
    company_linkedin: HttpUrl | None = None

    @computed_field
    @property
    def best_email(self) -> str | None:
        """Get the highest confidence email."""
        if self.email:
            return self.email

        if self.enrichments:
            sorted_enrichments = sorted(
                self.enrichments,
                key=lambda e: e.confidence,
                reverse=True,
            )
            return sorted_enrichments[0].email

        if self.additional_emails:
            return self.additional_emails[0]

        return None

    @computed_field
    @property
    def contact_person(self) -> str | None:
        """Get contact person name if available."""
        for enrichment in self.enrichments:
            if enrichment.first_name or enrichment.last_name:
                return f"{enrichment.first_name} {enrichment.last_name}".strip()
        return None

    @computed_field
    @property
    def enrichment_quality(self) -> str:
        """Assess enrichment quality."""
        if not self.enrichments:
            return "none"

        max_confidence = max(e.confidence for e in self.enrichments)
        if max_confidence >= 90:
            return "high"
        if max_confidence >= 70:
            return "medium"
        return "low"

    def to_export_dict(self) -> dict[str, Any]:
        """Export with enrichment data."""
        base = super().to_export_dict()
        base.update({
            "best_email": self.best_email,
            "contact_person": self.contact_person,
            "email_confidence": (
                max(e.confidence for e in self.enrichments)
                if self.enrichments
                else 0
            ),
            "enrichment_quality": self.enrichment_quality,
            "enriched_at": self.enriched_at.isoformat() if self.enriched_at else "",
        })
        return base
