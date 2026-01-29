"""
SQLite database management for GDPR compliance.

Provides:
- Connection pooling with thread safety
- Schema migration support
- GDPR data persistence (processing records, consent, audit logs)
- Automatic cleanup of expired data
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import structlog

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """
    Thread-safe SQLite database manager for GDPR compliance.

    Features:
    - Automatic schema creation and migration
    - Connection pooling per thread
    - Transaction management
    - Automatic cleanup of expired records

    Example:
        >>> db = DatabaseManager()
        >>> with db.transaction() as conn:
        ...     conn.execute("INSERT INTO audit_logs (...) VALUES (...)")
    """

    def __init__(self, db_path: str | Path = "gdpr_compliance.db") -> None:
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._lock = threading.Lock()

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._init_schema()

        logger.info(
            "database_initialized",
            db_path=str(self.db_path),
            size_bytes=self.db_path.stat().st_size if self.db_path.exists() else 0,
        )

    def get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local database connection.

        Returns:
            SQLite connection for current thread
        """
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")

        return self._local.connection

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database transactions.

        Yields:
            Database connection with active transaction

        Example:
            >>> with db.transaction() as conn:
            ...     conn.execute("INSERT ...")
            ...     conn.execute("UPDATE ...")
        """
        conn = self.get_connection()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except (sqlite3.DatabaseError, sqlite3.OperationalError, sqlite3.IntegrityError):
            conn.execute("ROLLBACK")
            raise
        except Exception:
            # Non-database exceptions also need rollback
            conn.execute("ROLLBACK")
            raise

    def _init_schema(self) -> None:
        """Initialize database schema with all required tables."""
        with self.transaction() as conn:
            # Processing records table (GDPR Art. 30)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_records (
                    record_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    legal_basis TEXT NOT NULL,
                    data_categories TEXT NOT NULL,  -- JSON array
                    data_subject_id TEXT,
                    controller TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    source TEXT,
                    retention_until TEXT,
                    correlation_id TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    CONSTRAINT valid_timestamp CHECK (timestamp IS NOT NULL),
                    CONSTRAINT valid_retention CHECK (
                        retention_until IS NULL OR
                        datetime(retention_until) > datetime(timestamp)
                    )
                )
            """)

            # Consent records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consent_records (
                    consent_id TEXT PRIMARY KEY,
                    data_subject_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    granted BOOLEAN NOT NULL,
                    granted_at TEXT NOT NULL,
                    withdrawn_at TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    consent_text TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    CONSTRAINT valid_withdrawal CHECK (
                        withdrawn_at IS NULL OR
                        datetime(withdrawn_at) >= datetime(granted_at)
                    )
                )
            """)

            # Audit logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data_subject_id TEXT,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    result TEXT,  -- success, failure, denied
                    details TEXT,  -- JSON
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # Data subject requests table (Art. 15-22)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_subject_requests (
                    request_id TEXT PRIMARY KEY,
                    request_type TEXT NOT NULL,
                    data_subject_id TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    status TEXT NOT NULL,
                    completed_at TEXT,
                    response TEXT,  -- JSON
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    CONSTRAINT valid_type CHECK (
                        request_type IN ('access', 'erasure', 'portability',
                                       'rectification', 'restriction', 'objection')
                    ),
                    CONSTRAINT valid_status CHECK (
                        status IN ('pending', 'in_progress', 'completed', 'rejected')
                    ),
                    CONSTRAINT valid_completion CHECK (
                        completed_at IS NULL OR
                        datetime(completed_at) >= datetime(requested_at)
                    )
                )
            """)

            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_data_subject
                ON processing_records(data_subject_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_retention
                ON processing_records(retention_until)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processing_purpose
                ON processing_records(purpose)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_consent_subject
                ON consent_records(data_subject_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_consent_purpose
                ON consent_records(purpose)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_logs(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_subject
                ON audit_logs(data_subject_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_requests_subject
                ON data_subject_requests(data_subject_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_requests_status
                ON data_subject_requests(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_requests_deadline
                ON data_subject_requests(deadline)
            """)

            # Schema version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # Set initial version if not exists
            conn.execute("""
                INSERT OR IGNORE INTO schema_version (version) VALUES (1)
            """)

    def purge_expired_records(self) -> int:
        """
        Delete processing records that have exceeded retention period.

        This implements GDPR data minimization principle.

        Returns:
            Number of records deleted
        """
        with self.transaction() as conn:
            now = datetime.now(timezone.utc).isoformat()

            # Find expired records
            cursor = conn.execute("""
                SELECT record_id, data_subject_id, purpose
                FROM processing_records
                WHERE retention_until IS NOT NULL
                AND retention_until < ?
            """, (now,))

            expired = cursor.fetchall()
            count = len(expired)

            if count > 0:
                # Log deletions in audit log
                for record in expired:
                    self._audit_log(
                        conn=conn,
                        event_type="data_deletion",
                        action="automatic_purge",
                        data_subject_id=record["data_subject_id"],
                        resource_type="processing_record",
                        resource_id=record["record_id"],
                        result="success",
                        details={
                            "reason": "retention_period_expired",
                            "purpose": record["purpose"],
                        },
                    )

                # Delete expired records
                conn.execute("""
                    DELETE FROM processing_records
                    WHERE retention_until IS NOT NULL
                    AND retention_until < ?
                """, (now,))

                logger.info(
                    "gdpr_automatic_purge",
                    records_deleted=count,
                    timestamp=now,
                )

            return count

    def erase_data_subject(self, data_subject_id: str) -> dict[str, int]:
        """
        Erase all data for a data subject (GDPR Art. 17).

        This implements the "Right to Erasure" (Right to be Forgotten).

        Args:
            data_subject_id: Pseudonymized identifier

        Returns:
            Dictionary with counts of deleted records by type
        """
        with self.transaction() as conn:
            counts = {}

            # Delete processing records
            cursor = conn.execute("""
                DELETE FROM processing_records
                WHERE data_subject_id = ?
                RETURNING record_id
            """, (data_subject_id,))
            counts["processing_records"] = len(cursor.fetchall())

            # Withdraw all consents
            cursor = conn.execute("""
                UPDATE consent_records
                SET withdrawn_at = datetime('now')
                WHERE data_subject_id = ?
                AND withdrawn_at IS NULL
                RETURNING consent_id
            """, (data_subject_id,))
            counts["consents_withdrawn"] = len(cursor.fetchall())

            # Delete data subject requests (GDPR Art. 17 compliance)
            cursor = conn.execute("""
                DELETE FROM data_subject_requests
                WHERE data_subject_id = ?
                RETURNING request_id
            """, (data_subject_id,))
            counts["requests_deleted"] = len(cursor.fetchall())

            # Audit the erasure
            self._audit_log(
                conn=conn,
                event_type="data_erasure",
                action="erase_data_subject",
                data_subject_id=data_subject_id,
                result="success",
                details={
                    "processing_records_deleted": counts["processing_records"],
                    "consents_withdrawn": counts["consents_withdrawn"],
                    "requests_deleted": counts["requests_deleted"],
                },
            )

            logger.info(
                "gdpr_data_subject_erased",
                data_subject_id=data_subject_id,
                **counts,
            )

            return counts

    def _audit_log(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        action: str,
        data_subject_id: str | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        result: str = "success",
        details: dict[str, Any] | None = None,
    ) -> str:
        """
        Internal method to create audit log entry.

        Args:
            conn: Database connection
            event_type: Type of event (data_access, data_deletion, etc.)
            action: Specific action taken
            data_subject_id: Subject identifier
            user_id: User who performed action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            ip_address: IP address of requester
            user_agent: User agent string
            result: Result of action (success, failure, denied)
            details: Additional details as dictionary

        Returns:
            Generated log_id
        """
        import json
        from uuid import uuid4

        log_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        conn.execute("""
            INSERT INTO audit_logs (
                log_id, timestamp, event_type, data_subject_id, user_id,
                action, resource_type, resource_id, ip_address, user_agent,
                result, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            timestamp,
            event_type,
            data_subject_id,
            user_id,
            action,
            resource_type,
            resource_id,
            ip_address,
            user_agent,
            result,
            json.dumps(details) if details else None,
        ))

        return log_id

    def vacuum(self) -> None:
        """
        Optimize database by reclaiming space from deleted records.

        Should be run periodically after purges.
        """
        conn = self.get_connection()
        conn.execute("VACUUM")
        logger.info("database_vacuumed", db_path=str(self.db_path))

    def get_stats(self) -> dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with table row counts and database size
        """
        conn = self.get_connection()
        stats = {}

        # Count rows in each table
        # Note: Table names are hardcoded here, not user input - safe from SQL injection
        allowed_tables = {"processing_records", "consent_records", "audit_logs", "data_subject_requests"}
        for table in allowed_tables:
            assert table in allowed_tables, f"Invalid table name: {table}"  # Defense in depth
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")  # nosec B608
            stats[f"{table}_count"] = cursor.fetchone()["count"]

        # Database file size
        if self.db_path.exists():
            stats["size_bytes"] = self.db_path.stat().st_size

        return stats

    def close(self) -> None:
        """Close database connection for current thread."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            delattr(self._local, "connection")


# Global database manager instance
_db_manager: DatabaseManager | None = None
_db_lock = threading.Lock()


def get_database() -> DatabaseManager:
    """
    Get or create the global database manager.

    Thread-safe singleton pattern.

    Returns:
        Global DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        with _db_lock:
            if _db_manager is None:
                _db_manager = DatabaseManager()
    return _db_manager
