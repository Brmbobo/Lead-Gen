"""
GDPR compliance utilities with SQLite persistence.

Provides tools for:
- Data subject rights (access, erasure, portability)
- Consent management
- Audit logging
- Data retention enforcement
- Legal basis tracking

All data is persisted to SQLite for GDPR Article 30 compliance.
Automatic purging of expired data ensures data minimization.
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
from lead_gen.core.database import get_database
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

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> ProcessingRecord:
        """Create ProcessingRecord from database row."""
        data_categories = json.loads(row["data_categories"])
        return cls(
            record_id=row["record_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            purpose=ProcessingPurpose(row["purpose"]),
            legal_basis=LegalBasis(row["legal_basis"]),
            data_categories=[DataCategory(c) for c in data_categories],
            data_subject_id=row["data_subject_id"],
            controller=row["controller"],
            operation=row["operation"],
            source=row["source"],
            retention_until=datetime.fromisoformat(row["retention_until"]) if row["retention_until"] else None,
            correlation_id=row["correlation_id"],
        )


@dataclass
class ConsentRecord:
    """Record of consent for processing (Art. 7)."""

    consent_id: str = field(default_factory=lambda: str(uuid4()))
    data_subject_id: str = ""
    purpose: ProcessingPurpose = ProcessingPurpose.LEAD_GENERATION
    granted: bool = False
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    withdrawn_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    consent_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "consent_id": self.consent_id,
            "data_subject_id": self.data_subject_id,
            "purpose": self.purpose.value,
            "granted": self.granted,
            "granted_at": self.granted_at.isoformat(),
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "consent_text": self.consent_text,
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "request_id": self.request_id,
            "request_type": self.request_type,
            "data_subject_id": self.data_subject_id,
            "requested_at": self.requested_at.isoformat(),
            "deadline": self.deadline.isoformat(),
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "response": self.response,
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> DataSubjectRequest:
        """Create DataSubjectRequest from database row."""
        request = cls.__new__(cls)
        request.request_id = row["request_id"]
        request.request_type = row["request_type"]
        request.data_subject_id = row["data_subject_id"]
        request.requested_at = datetime.fromisoformat(row["requested_at"])
        request.deadline = datetime.fromisoformat(row["deadline"])
        request.status = row["status"]
        request.completed_at = datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
        request.response = json.loads(row["response"]) if row["response"] else {}
        return request


class GDPRManager:
    """
    GDPR compliance manager with SQLite persistence.

    Provides utilities for:
    - Recording processing activities (Art. 30)
    - Handling data subject requests (Art. 15-22)
    - Enforcing retention policies
    - Pseudonymization
    - Automatic data deletion

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

        # Get database instance
        self.db = get_database()

        # Run automatic purge on initialization
        self._auto_purge()

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

        # Persist to database
        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation, source, retention_until,
                    correlation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.record_id,
                record.timestamp.isoformat(),
                record.purpose.value,
                record.legal_basis.value,
                json.dumps([c.value for c in record.data_categories]),
                record.data_subject_id,
                record.controller,
                record.operation,
                record.source,
                record.retention_until.isoformat() if record.retention_until else None,
                record.correlation_id,
            ))

            # Audit log
            if self.audit_enabled:
                self.db._audit_log(
                    conn=conn,
                    event_type="processing_recorded",
                    action="record_processing",
                    data_subject_id=data_subject_id,
                    resource_type="processing_record",
                    resource_id=record.record_id,
                    result="success",
                    details=record.to_dict(),
                )

        if self.audit_enabled:
            logger.info(
                "gdpr_processing_recorded",
                **record.to_dict(),
            )

        return record

    def record_consent(
        self,
        data_subject_id: str,
        purpose: ProcessingPurpose,
        granted: bool,
        consent_text: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ConsentRecord:
        """
        Record consent for data processing (Art. 7).

        Args:
            data_subject_id: Pseudonymized identifier
            purpose: Purpose of processing
            granted: Whether consent was granted
            consent_text: Text of consent agreement
            ip_address: IP address of user
            user_agent: User agent string

        Returns:
            The created ConsentRecord
        """
        consent = ConsentRecord(
            data_subject_id=data_subject_id,
            purpose=purpose,
            granted=granted,
            ip_address=ip_address,
            user_agent=user_agent,
            consent_text=consent_text,
        )

        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO consent_records (
                    consent_id, data_subject_id, purpose, granted, granted_at,
                    ip_address, user_agent, consent_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                consent.consent_id,
                consent.data_subject_id,
                consent.purpose.value,
                consent.granted,
                consent.granted_at.isoformat(),
                consent.ip_address,
                consent.user_agent,
                consent.consent_text,
            ))

            if self.audit_enabled:
                self.db._audit_log(
                    conn=conn,
                    event_type="consent_recorded",
                    action="record_consent",
                    data_subject_id=data_subject_id,
                    resource_type="consent_record",
                    resource_id=consent.consent_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    result="success",
                    details={"purpose": purpose.value, "granted": granted},
                )

        logger.info(
            "gdpr_consent_recorded",
            **consent.to_dict(),
        )

        return consent

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

        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO data_subject_requests (
                    request_id, request_type, data_subject_id, requested_at,
                    deadline, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.request_type,
                request.data_subject_id,
                request.requested_at.isoformat(),
                request.deadline.isoformat(),
                request.status,
            ))

            if self.audit_enabled:
                self.db._audit_log(
                    conn=conn,
                    event_type="access_request",
                    action="create_access_request",
                    data_subject_id=data_subject_id,
                    resource_type="data_subject_request",
                    resource_id=request.request_id,
                    result="success",
                )

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

        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO data_subject_requests (
                    request_id, request_type, data_subject_id, requested_at,
                    deadline, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.request_type,
                request.data_subject_id,
                request.requested_at.isoformat(),
                request.deadline.isoformat(),
                request.status,
            ))

            if self.audit_enabled:
                self.db._audit_log(
                    conn=conn,
                    event_type="erasure_request",
                    action="create_erasure_request",
                    data_subject_id=data_subject_id,
                    resource_type="data_subject_request",
                    resource_id=request.request_id,
                    result="success",
                )

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

        with self.db.transaction() as conn:
            conn.execute("""
                INSERT INTO data_subject_requests (
                    request_id, request_type, data_subject_id, requested_at,
                    deadline, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.request_type,
                request.data_subject_id,
                request.requested_at.isoformat(),
                request.deadline.isoformat(),
                request.status,
            ))

            if self.audit_enabled:
                self.db._audit_log(
                    conn=conn,
                    event_type="portability_request",
                    action="create_portability_request",
                    data_subject_id=data_subject_id,
                    resource_type="data_subject_request",
                    resource_id=request.request_id,
                    result="success",
                )

        logger.info(
            "gdpr_portability_request_created",
            request_id=request.request_id,
            data_subject_id=data_subject_id,
            deadline=request.deadline.isoformat(),
        )

        return request

    def execute_erasure_request(self, request_id: str) -> dict[str, int]:
        """
        Execute an erasure request (Art. 17 - Right to be Forgotten).

        Args:
            request_id: ID of the erasure request

        Returns:
            Dictionary with counts of deleted records

        Raises:
            GDPRError: If request is not found or not an erasure request
        """
        conn = self.db.get_connection()

        # Get request
        cursor = conn.execute("""
            SELECT * FROM data_subject_requests
            WHERE request_id = ?
        """, (request_id,))
        row = cursor.fetchone()

        if not row:
            raise GDPRError(
                f"Request not found: {request_id}",
                article="Art. 17",
                required_action="verify_request_id",
            )

        if row["request_type"] != "erasure":
            raise GDPRError(
                f"Request {request_id} is not an erasure request",
                article="Art. 17",
                required_action="use_correct_request_type",
            )

        data_subject_id = row["data_subject_id"]

        # Erase all data for subject
        counts = self.db.erase_data_subject(data_subject_id)

        # Mark request as completed
        with self.db.transaction() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                UPDATE data_subject_requests
                SET status = 'completed',
                    completed_at = ?,
                    updated_at = ?,
                    response = ?
                WHERE request_id = ?
            """, (
                now,
                now,
                json.dumps(counts),
                request_id,
            ))

        logger.info(
            "gdpr_erasure_request_executed",
            request_id=request_id,
            data_subject_id=data_subject_id,
            **counts,
        )

        return counts

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
        conn = self.db.get_connection()
        query = "SELECT * FROM processing_records WHERE 1=1"
        params: list[Any] = []

        if data_subject_id:
            query += " AND data_subject_id = ?"
            params.append(data_subject_id)

        if purpose:
            query += " AND purpose = ?"
            params.append(purpose.value)

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        return [ProcessingRecord.from_db_row(dict(row)) for row in rows]

    def export_data_subject_data(self, data_subject_id: str) -> dict[str, Any]:
        """
        Export all data for a data subject (Art. 15/20).

        Args:
            data_subject_id: The data subject's identifier

        Returns:
            Dictionary of all data for the subject
        """
        conn = self.db.get_connection()

        # Get processing records
        records = self.get_processing_records(data_subject_id=data_subject_id)

        # Get consent records
        cursor = conn.execute("""
            SELECT * FROM consent_records
            WHERE data_subject_id = ?
            ORDER BY granted_at DESC
        """, (data_subject_id,))
        consents = [dict(row) for row in cursor.fetchall()]

        # Get all requests
        cursor = conn.execute("""
            SELECT * FROM data_subject_requests
            WHERE data_subject_id = ?
            ORDER BY requested_at DESC
        """, (data_subject_id,))
        requests = [dict(row) for row in cursor.fetchall()]

        # Audit the export
        with self.db.transaction() as conn:
            if self.audit_enabled:
                self.db._audit_log(
                    conn=conn,
                    event_type="data_export",
                    action="export_data_subject_data",
                    data_subject_id=data_subject_id,
                    result="success",
                    details={
                        "processing_records_count": len(records),
                        "consent_records_count": len(consents),
                        "requests_count": len(requests),
                    },
                )

        return {
            "data_subject_id": data_subject_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "processing_records": [r.to_dict() for r in records],
            "consent_records": consents,
            "data_subject_requests": requests,
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
        conn = self.db.get_connection()
        now = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute("""
            SELECT * FROM processing_records
            WHERE retention_until IS NOT NULL
            AND retention_until < ?
        """, (now,))

        rows = cursor.fetchall()
        expired = [ProcessingRecord.from_db_row(dict(row)) for row in rows]

        if expired:
            logger.warning(
                "gdpr_retention_expired",
                count=len(expired),
            )

        return expired

    def _auto_purge(self) -> int:
        """
        Automatically purge expired records.

        Called on initialization to ensure compliance.

        Returns:
            Number of records deleted
        """
        count = self.db.purge_expired_records()

        if count > 0:
            logger.info(
                "gdpr_auto_purge_completed",
                records_deleted=count,
            )

        return count

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
        conn = self.db.get_connection()
        cursor = conn.execute("""
            SELECT * FROM data_subject_requests
            WHERE status = 'pending'
            ORDER BY requested_at ASC
        """)

        return [DataSubjectRequest.from_db_row(dict(row)) for row in cursor.fetchall()]

    def get_overdue_requests(self) -> list[DataSubjectRequest]:
        """Get requests that are past their deadline."""
        conn = self.db.get_connection()
        now = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute("""
            SELECT * FROM data_subject_requests
            WHERE status IN ('pending', 'in_progress')
            AND deadline < ?
            ORDER BY deadline ASC
        """, (now,))

        return [DataSubjectRequest.from_db_row(dict(row)) for row in cursor.fetchall()]

    def get_audit_logs(
        self,
        data_subject_id: str | None = None,
        event_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get audit logs with optional filters.

        Args:
            data_subject_id: Filter by data subject
            event_type: Filter by event type
            since: Filter by timestamp
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        conn = self.db.get_connection()
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params: list[Any] = []

        if data_subject_id:
            query += " AND data_subject_id = ?"
            params.append(data_subject_id)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict[str, Any]:
        """
        Get GDPR compliance statistics.

        Returns:
            Dictionary with compliance metrics
        """
        db_stats = self.db.get_stats()

        # Add additional GDPR-specific stats
        conn = self.db.get_connection()

        # Count records by purpose
        cursor = conn.execute("""
            SELECT purpose, COUNT(*) as count
            FROM processing_records
            GROUP BY purpose
        """)
        records_by_purpose = {row["purpose"]: row["count"] for row in cursor.fetchall()}

        # Count expired records that need purging
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM processing_records
            WHERE retention_until IS NOT NULL
            AND retention_until < ?
        """, (now,))
        expired_count = cursor.fetchone()["count"]

        # Count overdue requests
        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM data_subject_requests
            WHERE status IN ('pending', 'in_progress')
            AND deadline < ?
        """, (now,))
        overdue_requests = cursor.fetchone()["count"]

        return {
            **db_stats,
            "records_by_purpose": records_by_purpose,
            "expired_records_needing_purge": expired_count,
            "overdue_requests": overdue_requests,
            "retention_days": self.retention_days,
            "default_legal_basis": self.default_legal_basis.value,
            "dpo_email": self.dpo_email,
            "audit_enabled": self.audit_enabled,
        }


# Global GDPR manager instance
_gdpr_manager: GDPRManager | None = None


def get_gdpr_manager() -> GDPRManager:
    """Get or create the global GDPR manager."""
    global _gdpr_manager
    if _gdpr_manager is None:
        _gdpr_manager = GDPRManager()
    return _gdpr_manager
