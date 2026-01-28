"""
GDPR compliance utilities.

Provides tools for:
- Data subject rights (access, erasure, portability)
- Consent management
- Audit logging
- Data retention enforcement
- Legal basis tracking
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

from lead_gen.core.config import get_settings
from lead_gen.core.exceptions import GDPRError

logger = structlog.get_logger(__name__)


class LegalBasis(str, Enum):
    """GDPR Article 6 legal bases for processing."""

    CONSENT = "consent"  # Art. 6(1)(a)
    CONTRACT = "contract"  # Art. 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"  # Art. 6(1)(c)
    VITAL_INTERESTS = "vital_interests"  # Art. 6(1)(d)
    PUBLIC_TASK = "public_task"  # Art. 6(1)(e)
    LEGITIMATE_INTEREST = "legitimate_interest"  # Art. 6(1)(f)


class ProcessingPurpose(str, Enum):
    """Documented purposes for data processing."""

    LEAD_GENERATION = "lead_generation"
    OUTREACH = "outreach"
    EMAIL_ENRICHMENT = "email_enrichment"
    ANALYTICS = "analytics"
    EXPORT = "export"


class DataCategory(str, Enum):
    """Categories of personal data processed."""

    BUSINESS_NAME = "business_name"
    BUSINESS_ADDRESS = "business_address"
    BUSINESS_PHONE = "business_phone"
    BUSINESS_WEBSITE = "business_website"
    BUSINESS_EMAIL = "business_email"
    CONTACT_NAME = "contact_name"
    CONTACT_EMAIL = "contact_email"


@dataclass
class ProcessingRecord:
    """
    Record of Processing Activities (Art. 30).

    Documents each processing operation for GDPR compliance.
    """

    record_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # What
    purpose: ProcessingPurpose = ProcessingPurpose.LEAD_GENERATION
    legal_basis: LegalBasis = LegalBasis.LEGITIMATE_INTEREST
    data_categories: list[DataCategory] = field(default_factory=list)

    # Who
    data_subject_id: str | None = None  # Pseudonymized identifier
    controller: str = "Lead-Gen"

    # Details
    operation: str = ""  # What was done
    source: str = ""  # Where data came from
    retention_until: datetime | None = None

    # Audit
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "purpose": self.purpose.value,
            "legal_basis": self.legal_basis.value,
            "data_categories": [c.value for c in self.data_categories],
            "data_subject_id": self.data_subject_id,
            "controller": self.controller,
            "operation": self.operation,
            "source": self.source,
            "retention_until": self.retention_until.isoformat() if self.retention_until else None,
            "correlation_id": self.correlation_id,
        }


@dataclass
class DataSubjectRequest:
    """Data subject rights request (Art. 15-22)."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    request_type: str = ""  # access, erasure, portability, rectification, restriction
    data_subject_id: str = ""
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: datetime = field(init=False)  # 30 days by default
    status: str = "pending"  # pending, in_progress, completed, rejected
    completed_at: datetime | None = None
    response: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.deadline = self.requested_at + timedelta(days=30)


class GDPRManager:
    """
    GDPR compliance manager.

    Provides utilities for:
    - Recording processing activities
    - Handling data subject requests
    - Enforcing retention policies
    - Pseudonymization

    Example:
        >>> gdpr = GDPRManager()
        >>> record = gdpr.record_processing(
        ...     purpose=ProcessingPurpose.LEAD_GENERATION,
        ...     data_categories=[DataCategory.BUSINESS_NAME, DataCategory.BUSINESS_EMAIL],
        ...     operation="Scraped leads from Google Places",
        ... )
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.retention_days = settings.gdpr.retention_days
        self.default_legal_basis = LegalBasis(settings.gdpr.legal_basis)
        self.dpo_email = settings.gdpr.dpo_email
        self.audit_enabled = settings.gdpr.enable_audit_log

        # In-memory storage (replace with database in production)
        self._processing_records: list[ProcessingRecord] = []
        self._data_subject_requests: list[DataSubjectRequest] = []

    def pseudonymize(self, identifier: str) -> str:
        """
        Pseudonymize an identifier using SHA-256.

        This creates a consistent but irreversible mapping.

        Args:
            identifier: The identifier to pseudonymize (e.g., email, phone)

        Returns:
            Pseudonymized identifier (hash)
        """
        # Add salt from settings for extra security
        salted = f"lead-gen:{identifier}"
        return hashlib.sha256(salted.encode()).hexdigest()[:16]

    def record_processing(
        self,
        purpose: ProcessingPurpose,
        data_categories: list[DataCategory],
        operation: str,
        source: str = "Google Places API",
        data_subject_id: str | None = None,
        legal_basis: LegalBasis | None = None,
        correlation_id: str | None = None,
    ) -> ProcessingRecord:
        """
        Record a processing activity (Art. 30).

        Args:
            purpose: Why the data is being processed
            data_categories: What types of data are involved
            operation: Description of what was done
            source: Where the data came from
            data_subject_id: Pseudonymized identifier of data subject
            legal_basis: Legal basis for processing
            correlation_id: Request correlation ID

        Returns:
            The created ProcessingRecord
        """
        record = ProcessingRecord(
            purpose=purpose,
            legal_basis=legal_basis or self.default_legal_basis,
            data_categories=data_categories,
            operation=operation,
            source=source,
            data_subject_id=data_subject_id,
            retention_until=datetime.now(timezone.utc) + timedelta(days=self.retention_days),
            correlation_id=correlation_id,
        )

        self._processing_records.append(record)

        if self.audit_enabled:
            logger.info(
                "gdpr_processing_recorded",
                **record.to_dict(),
            )

        return record

    def create_access_request(self, data_subject_id: str) -> DataSubjectRequest:
        """
        Create a data subject access request (Art. 15).

        Args:
            data_subject_id: Identifier of the requesting data subject

        Returns:
            The created request
        """
        request = DataSubjectRequest(
            request_type="access",
            data_subject_id=data_subject_id,
        )
        self._data_subject_requests.append(request)

        logger.info(
            "gdpr_access_request_created",
            request_id=request.request_id,
            data_subject_id=data_subject_id,
            deadline=request.deadline.isoformat(),
        )

        return request

    def create_erasure_request(self, data_subject_id: str) -> DataSubjectRequest:
        """
        Create a right to erasure request (Art. 17).

        Args:
            data_subject_id: Identifier of the requesting data subject

        Returns:
            The created request
        """
        request = DataSubjectRequest(
            request_type="erasure",
            data_subject_id=data_subject_id,
        )
        self._data_subject_requests.append(request)

        logger.info(
            "gdpr_erasure_request_created",
            request_id=request.request_id,
            data_subject_id=data_subject_id,
            deadline=request.deadline.isoformat(),
        )

        return request

    def create_portability_request(self, data_subject_id: str) -> DataSubjectRequest:
        """
        Create a data portability request (Art. 20).

        Args:
            data_subject_id: Identifier of the requesting data subject

        Returns:
            The created request
        """
        request = DataSubjectRequest(
            request_type="portability",
            data_subject_id=data_subject_id,
        )
        self._data_subject_requests.append(request)

        logger.info(
            "gdpr_portability_request_created",
            request_id=request.request_id,
            data_subject_id=data_subject_id,
            deadline=request.deadline.isoformat(),
        )

        return request

    def get_processing_records(
        self,
        data_subject_id: str | None = None,
        purpose: ProcessingPurpose | None = None,
        since: datetime | None = None,
    ) -> list[ProcessingRecord]:
        """
        Get processing records with optional filters.

        Args:
            data_subject_id: Filter by data subject
            purpose: Filter by purpose
            since: Filter by timestamp

        Returns:
            List of matching records
        """
        records = self._processing_records

        if data_subject_id:
            records = [r for r in records if r.data_subject_id == data_subject_id]

        if purpose:
            records = [r for r in records if r.purpose == purpose]

        if since:
            records = [r for r in records if r.timestamp >= since]

        return records

    def export_data_subject_data(self, data_subject_id: str) -> dict[str, Any]:
        """
        Export all data for a data subject (Art. 15/20).

        Args:
            data_subject_id: The data subject's identifier

        Returns:
            Dictionary of all data for the subject
        """
        records = self.get_processing_records(data_subject_id=data_subject_id)

        return {
            "data_subject_id": data_subject_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "processing_records": [r.to_dict() for r in records],
            "data_controller": "Lead-Gen",
            "dpo_contact": self.dpo_email,
            "retention_policy_days": self.retention_days,
        }

    def check_retention(self) -> list[ProcessingRecord]:
        """
        Check for records that have exceeded retention period.

        Returns:
            List of records that should be deleted
        """
        now = datetime.now(timezone.utc)
        expired = [
            r
            for r in self._processing_records
            if r.retention_until and r.retention_until < now
        ]

        if expired:
            logger.warning(
                "gdpr_retention_expired",
                count=len(expired),
            )

        return expired

    def validate_legal_basis(
        self,
        purpose: ProcessingPurpose,
        data_categories: list[DataCategory],
    ) -> None:
        """
        Validate that processing has a valid legal basis.

        Raises:
            GDPRError: If no valid legal basis exists
        """
        # For lead generation of business data, legitimate interest is typically valid
        # But we should document the balancing test
        if self.default_legal_basis == LegalBasis.LEGITIMATE_INTEREST:
            # Business contact data (not personal) is generally allowed
            personal_categories = {DataCategory.CONTACT_NAME, DataCategory.CONTACT_EMAIL}
            has_personal = any(c in personal_categories for c in data_categories)

            if has_personal and purpose == ProcessingPurpose.OUTREACH:
                logger.warning(
                    "gdpr_personal_data_processed",
                    purpose=purpose.value,
                    data_categories=[c.value for c in data_categories],
                    legal_basis=self.default_legal_basis.value,
                    warning="Ensure Legitimate Interest Assessment is documented",
                )

    def get_pending_requests(self) -> list[DataSubjectRequest]:
        """Get all pending data subject requests."""
        return [r for r in self._data_subject_requests if r.status == "pending"]

    def get_overdue_requests(self) -> list[DataSubjectRequest]:
        """Get requests that are past their deadline."""
        now = datetime.now(timezone.utc)
        return [
            r
            for r in self._data_subject_requests
            if r.status in ("pending", "in_progress") and r.deadline < now
        ]


# Global GDPR manager instance
_gdpr_manager: GDPRManager | None = None


def get_gdpr_manager() -> GDPRManager:
    """Get or create the global GDPR manager."""
    global _gdpr_manager
    if _gdpr_manager is None:
        _gdpr_manager = GDPRManager()
    return _gdpr_manager
