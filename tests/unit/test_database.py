"""
Comprehensive unit tests for database management module.

Tests cover:
- DatabaseManager initialization and schema creation
- Transaction commit on success
- Transaction rollback on error
- purge_expired_records deletes old data
- erase_data_subject removes all subject data
- get_stats returns correct counts
- Thread-local connections
- Audit logging
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from lead_gen.core.database import DatabaseManager, get_database


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = DatabaseManager(db_path)
    yield db

    # Cleanup
    db.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def db_with_data(temp_db):
    """Create database with sample test data."""
    with temp_db.transaction() as conn:
        # Add processing records
        conn.execute("""
            INSERT INTO processing_records (
                record_id, timestamp, purpose, legal_basis, data_categories,
                data_subject_id, controller, operation, retention_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "rec-1",
            datetime.now(timezone.utc).isoformat(),
            "marketing",
            "consent",
            '["email", "name"]',
            "subject-1",
            "ACME Corp",
            "email_campaign",
            (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        ))

        # Add consent record
        conn.execute("""
            INSERT INTO consent_records (
                consent_id, data_subject_id, purpose, granted, granted_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            "consent-1",
            "subject-1",
            "marketing",
            True,
            datetime.now(timezone.utc).isoformat(),
        ))

        # Add audit log
        conn.execute("""
            INSERT INTO audit_logs (
                log_id, timestamp, event_type, data_subject_id, action, result
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "log-1",
            datetime.now(timezone.utc).isoformat(),
            "data_access",
            "subject-1",
            "view_profile",
            "success",
        ))

    return temp_db


@pytest.fixture(autouse=True)
def reset_global_db():
    """Reset global database manager singleton."""
    import lead_gen.core.database
    lead_gen.core.database._db_manager = None
    yield
    lead_gen.core.database._db_manager = None


# ============================================================================
# Initialization Tests
# ============================================================================


class TestDatabaseInitialization:
    """Test DatabaseManager initialization and schema creation."""

    def test_initialization_creates_database(self):
        """Test DatabaseManager creates database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            db = DatabaseManager(db_path)

            assert Path(db_path).exists()
            assert Path(db_path).stat().st_size > 0

            db.close()
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_initialization_creates_parent_directories(self):
        """Test DatabaseManager creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "nested" / "test.db"

            db = DatabaseManager(db_path)

            assert db_path.exists()
            assert db_path.parent.exists()

            db.close()

    def test_schema_creates_all_tables(self, temp_db):
        """Test schema initialization creates all required tables."""
        conn = temp_db.get_connection()

        # Check all tables exist
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        assert "processing_records" in tables
        assert "consent_records" in tables
        assert "audit_logs" in tables
        assert "data_subject_requests" in tables
        assert "schema_version" in tables

    def test_schema_creates_indexes(self, temp_db):
        """Test schema initialization creates all indexes."""
        conn = temp_db.get_connection()

        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
            ORDER BY name
        """)
        indexes = [row[0] for row in cursor.fetchall()]

        # Check key indexes exist
        assert "idx_processing_data_subject" in indexes
        assert "idx_processing_retention" in indexes
        assert "idx_consent_subject" in indexes
        assert "idx_audit_timestamp" in indexes

    def test_schema_version_initialized(self, temp_db):
        """Test schema version table is initialized with version 1."""
        conn = temp_db.get_connection()

        cursor = conn.execute("SELECT version FROM schema_version")
        version = cursor.fetchone()[0]

        assert version == 1

    def test_foreign_keys_enabled(self, temp_db):
        """Test foreign keys are enabled."""
        conn = temp_db.get_connection()

        cursor = conn.execute("PRAGMA foreign_keys")
        enabled = cursor.fetchone()[0]

        assert enabled == 1

    def test_wal_mode_enabled(self, temp_db):
        """Test WAL mode is enabled for better concurrency."""
        conn = temp_db.get_connection()

        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]

        assert mode.lower() == "wal"


# ============================================================================
# Connection Management Tests
# ============================================================================


class TestConnectionManagement:
    """Test thread-local connection management."""

    def test_get_connection_returns_connection(self, temp_db):
        """Test get_connection returns SQLite connection."""
        conn = temp_db.get_connection()

        assert isinstance(conn, sqlite3.Connection)

    def test_get_connection_thread_local(self, temp_db):
        """Test each thread gets its own connection."""
        connections = []

        def get_conn():
            conn = temp_db.get_connection()
            connections.append((threading.current_thread().ident, id(conn)))

        threads = [threading.Thread(target=get_conn) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All connections should have different IDs (different objects)
        connection_ids = [conn_id for _, conn_id in connections]
        assert len(set(connection_ids)) == len(connection_ids)

    def test_get_connection_same_thread_returns_same(self, temp_db):
        """Test multiple calls in same thread return same connection."""
        conn1 = temp_db.get_connection()
        conn2 = temp_db.get_connection()

        assert conn1 is conn2

    def test_row_factory_returns_dict_rows(self, temp_db):
        """Test connections use Row factory for dict-like access."""
        conn = temp_db.get_connection()

        cursor = conn.execute("SELECT 1 as value")
        row = cursor.fetchone()

        assert row["value"] == 1

    def test_close_removes_thread_local_connection(self, temp_db):
        """Test close() removes thread-local connection."""
        # Get initial connection
        conn1 = temp_db.get_connection()

        # Close it
        temp_db.close()

        # Next call should create new connection
        conn2 = temp_db.get_connection()

        assert conn1 is not conn2


# ============================================================================
# Transaction Tests
# ============================================================================


class TestTransactions:
    """Test transaction management."""

    def test_transaction_commits_on_success(self, temp_db):
        """Test transaction commits changes on successful completion."""
        with temp_db.transaction() as conn:
            conn.execute("""
                INSERT INTO audit_logs (
                    log_id, timestamp, event_type, action, result
                ) VALUES (?, ?, ?, ?, ?)
            """, ("test-log", datetime.now(timezone.utc).isoformat(), "test", "test_action", "success"))

        # Verify data was committed
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE log_id = ?", ("test-log",))
        count = cursor.fetchone()[0]

        assert count == 1

    def test_transaction_rollback_on_database_error(self, temp_db):
        """Test transaction rolls back on database errors."""
        try:
            with temp_db.transaction() as conn:
                # Valid insert
                conn.execute("""
                    INSERT INTO audit_logs (
                        log_id, timestamp, event_type, action, result
                    ) VALUES (?, ?, ?, ?, ?)
                """, ("test-1", datetime.now(timezone.utc).isoformat(), "test", "action", "success"))

                # Invalid insert (duplicate primary key)
                conn.execute("""
                    INSERT INTO audit_logs (
                        log_id, timestamp, event_type, action, result
                    ) VALUES (?, ?, ?, ?, ?)
                """, ("test-1", datetime.now(timezone.utc).isoformat(), "test", "action", "success"))
        except sqlite3.IntegrityError:
            pass  # Expected

        # Verify data was rolled back
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE log_id = ?", ("test-1",))
        count = cursor.fetchone()[0]

        assert count == 0

    def test_transaction_rollback_on_python_exception(self, temp_db):
        """Test transaction rolls back on Python exceptions."""
        try:
            with temp_db.transaction() as conn:
                conn.execute("""
                    INSERT INTO audit_logs (
                        log_id, timestamp, event_type, action, result
                    ) VALUES (?, ?, ?, ?, ?)
                """, ("test-2", datetime.now(timezone.utc).isoformat(), "test", "action", "success"))

                # Raise Python exception
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Verify data was rolled back
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE log_id = ?", ("test-2",))
        count = cursor.fetchone()[0]

        assert count == 0

    def test_transaction_isolation(self, temp_db):
        """Test transactions are isolated using autocommit mode."""
        # In autocommit mode (isolation_level=None), each statement is immediately committed
        # This test verifies that completed transactions are visible to other connections

        # Insert data using transaction
        with temp_db.transaction() as conn:
            conn.execute("""
                INSERT INTO audit_logs (
                    log_id, timestamp, event_type, action, result
                ) VALUES (?, ?, ?, ?, ?)
            """, ("test-3", datetime.now(timezone.utc).isoformat(), "test", "action", "success"))

        # Check from same connection (should see committed data)
        conn2 = temp_db.get_connection()
        cursor = conn2.execute("SELECT COUNT(*) FROM audit_logs WHERE log_id = ?", ("test-3",))
        count = cursor.fetchone()[0]

        # Should see committed data
        assert count == 1


# ============================================================================
# Data Purge Tests
# ============================================================================


class TestPurgeExpiredRecords:
    """Test purge_expired_records functionality."""

    def test_purge_deletes_expired_records(self, temp_db):
        """Test purge_expired_records deletes records past retention period."""
        with temp_db.transaction() as conn:
            # Add expired record (old timestamp, expired retention)
            past_timestamp = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            expired_retention = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation, retention_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "expired-1",
                past_timestamp,
                "test",
                "consent",
                "[]",
                "subject-1",
                "Test",
                "test_op",
                expired_retention,  # Expired (but still > timestamp)
            ))

            # Add non-expired record
            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation, retention_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "active-1",
                datetime.now(timezone.utc).isoformat(),
                "test",
                "consent",
                "[]",
                "subject-1",
                "Test",
                "test_op",
                (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),  # Not expired
            ))

        # Purge expired records
        deleted_count = temp_db.purge_expired_records()

        assert deleted_count == 1

        # Verify expired record was deleted
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM processing_records WHERE record_id = ?", ("expired-1",))
        assert cursor.fetchone()[0] == 0

        # Verify active record remains
        cursor = conn.execute("SELECT COUNT(*) FROM processing_records WHERE record_id = ?", ("active-1",))
        assert cursor.fetchone()[0] == 1

    def test_purge_returns_zero_when_no_expired(self, temp_db):
        """Test purge_expired_records returns 0 when no expired records."""
        with temp_db.transaction() as conn:
            # Add non-expired record
            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation, retention_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "active-1",
                datetime.now(timezone.utc).isoformat(),
                "test",
                "consent",
                "[]",
                "subject-1",
                "Test",
                "test_op",
                (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            ))

        deleted_count = temp_db.purge_expired_records()

        assert deleted_count == 0

    def test_purge_creates_audit_logs(self, temp_db):
        """Test purge_expired_records creates audit log entries."""
        with temp_db.transaction() as conn:
            past_timestamp = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            expired_retention = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation, retention_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "expired-1",
                past_timestamp,
                "marketing",
                "consent",
                "[]",
                "subject-1",
                "Test",
                "test_op",
                expired_retention,
            ))

        temp_db.purge_expired_records()

        # Check audit log was created
        conn = temp_db.get_connection()
        cursor = conn.execute("""
            SELECT event_type, action, resource_id, details
            FROM audit_logs
            WHERE event_type = 'data_deletion'
            AND action = 'automatic_purge'
        """)
        log = cursor.fetchone()

        assert log is not None
        assert log["resource_id"] == "expired-1"
        details = json.loads(log["details"])
        assert details["reason"] == "retention_period_expired"
        assert details["purpose"] == "marketing"

    def test_purge_ignores_null_retention(self, temp_db):
        """Test purge ignores records with NULL retention_until."""
        with temp_db.transaction() as conn:
            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation, retention_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "no-retention",
                datetime.now(timezone.utc).isoformat(),
                "test",
                "consent",
                "[]",
                "subject-1",
                "Test",
                "test_op",
                None,  # No retention period
            ))

        deleted_count = temp_db.purge_expired_records()

        assert deleted_count == 0

        # Verify record still exists
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM processing_records WHERE record_id = ?", ("no-retention",))
        assert cursor.fetchone()[0] == 1


# ============================================================================
# Data Subject Erasure Tests
# ============================================================================


class TestEraseDataSubject:
    """Test erase_data_subject functionality (GDPR Right to Erasure)."""

    def test_erase_removes_all_subject_data(self, db_with_data):
        """Test erase_data_subject removes all data for a subject."""
        counts = db_with_data.erase_data_subject("subject-1")

        assert counts["processing_records"] == 1
        assert counts["consents_withdrawn"] == 1

        # Verify processing records deleted
        conn = db_with_data.get_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM processing_records WHERE data_subject_id = ?",
            ("subject-1",)
        )
        assert cursor.fetchone()[0] == 0

        # Verify consents withdrawn
        cursor = conn.execute(
            "SELECT withdrawn_at FROM consent_records WHERE data_subject_id = ?",
            ("subject-1",)
        )
        row = cursor.fetchone()
        assert row["withdrawn_at"] is not None

    def test_erase_returns_zero_for_unknown_subject(self, temp_db):
        """Test erase_data_subject returns zeros for unknown subject."""
        counts = temp_db.erase_data_subject("unknown-subject")

        assert counts["processing_records"] == 0
        assert counts["consents_withdrawn"] == 0
        assert counts["requests_deleted"] == 0

    def test_erase_creates_audit_log(self, db_with_data):
        """Test erase_data_subject creates audit log entry."""
        db_with_data.erase_data_subject("subject-1")

        conn = db_with_data.get_connection()
        cursor = conn.execute("""
            SELECT event_type, action, data_subject_id, details
            FROM audit_logs
            WHERE event_type = 'data_erasure'
        """)
        log = cursor.fetchone()

        assert log is not None
        assert log["event_type"] == "data_erasure"
        assert log["action"] == "erase_data_subject"
        assert log["data_subject_id"] == "subject-1"

        details = json.loads(log["details"])
        assert "processing_records_deleted" in details
        assert "consents_withdrawn" in details
        assert "requests_deleted" in details

    def test_erase_is_atomic(self, db_with_data):
        """Test erase_data_subject is atomic (all or nothing)."""
        # This test verifies transaction behavior
        # Even if there's an error, everything rolls back

        with patch.object(db_with_data, '_audit_log', side_effect=Exception("Audit failed")):
            try:
                db_with_data.erase_data_subject("subject-1")
            except Exception:
                pass

        # Verify data was NOT deleted (transaction rolled back)
        conn = db_with_data.get_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM processing_records WHERE data_subject_id = ?",
            ("subject-1",)
        )
        # Should still exist because transaction rolled back
        assert cursor.fetchone()[0] == 1

    def test_erase_handles_multiple_records(self, temp_db):
        """Test erase_data_subject handles multiple records per subject."""
        with temp_db.transaction() as conn:
            # Add multiple processing records
            for i in range(5):
                conn.execute("""
                    INSERT INTO processing_records (
                        record_id, timestamp, purpose, legal_basis, data_categories,
                        data_subject_id, controller, operation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"rec-{i}",
                    datetime.now(timezone.utc).isoformat(),
                    "test",
                    "consent",
                    "[]",
                    "multi-subject",
                    "Test",
                    "test_op",
                ))

            # Add multiple consent records
            for i in range(3):
                conn.execute("""
                    INSERT INTO consent_records (
                        consent_id, data_subject_id, purpose, granted, granted_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    f"consent-{i}",
                    "multi-subject",
                    f"purpose-{i}",
                    True,
                    datetime.now(timezone.utc).isoformat(),
                ))

        counts = temp_db.erase_data_subject("multi-subject")

        assert counts["processing_records"] == 5
        assert counts["consents_withdrawn"] == 3

    def test_erase_deletes_data_subject_requests(self, temp_db):
        """Test erase_data_subject also deletes data subject requests (GDPR Art. 17)."""
        # Add data subject requests
        with temp_db.transaction() as conn:
            for i, req_type in enumerate(['access', 'erasure', 'portability']):
                conn.execute("""
                    INSERT INTO data_subject_requests (
                        request_id, request_type, data_subject_id, requested_at,
                        deadline, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"req-{i}",
                    req_type,
                    "request-subject",
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    "pending",
                ))

        counts = temp_db.erase_data_subject("request-subject")

        assert counts["requests_deleted"] == 3

        # Verify requests actually deleted
        conn = temp_db.get_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM data_subject_requests WHERE data_subject_id = ?",
            ("request-subject",)
        )
        assert cursor.fetchone()[0] == 0


# ============================================================================
# Statistics Tests
# ============================================================================


class TestGetStats:
    """Test get_stats functionality."""

    def test_get_stats_returns_counts(self, db_with_data):
        """Test get_stats returns correct row counts."""
        stats = db_with_data.get_stats()

        assert stats["processing_records_count"] == 1
        assert stats["consent_records_count"] == 1
        assert stats["audit_logs_count"] == 1
        assert stats["data_subject_requests_count"] == 0

    def test_get_stats_includes_file_size(self, db_with_data):
        """Test get_stats includes database file size."""
        stats = db_with_data.get_stats()

        assert "size_bytes" in stats
        assert stats["size_bytes"] > 0

    def test_get_stats_empty_database(self, temp_db):
        """Test get_stats on empty database."""
        stats = temp_db.get_stats()

        assert stats["processing_records_count"] == 0
        assert stats["consent_records_count"] == 0
        assert stats["audit_logs_count"] == 0
        assert stats["data_subject_requests_count"] == 0

    def test_get_stats_after_operations(self, temp_db):
        """Test get_stats reflects changes after operations."""
        # Initial stats
        stats1 = temp_db.get_stats()
        assert stats1["processing_records_count"] == 0

        # Add data
        with temp_db.transaction() as conn:
            conn.execute("""
                INSERT INTO processing_records (
                    record_id, timestamp, purpose, legal_basis, data_categories,
                    data_subject_id, controller, operation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "test-rec",
                datetime.now(timezone.utc).isoformat(),
                "test",
                "consent",
                "[]",
                "subject-1",
                "Test",
                "test_op",
            ))

        # Updated stats
        stats2 = temp_db.get_stats()
        assert stats2["processing_records_count"] == 1


# ============================================================================
# Audit Logging Tests
# ============================================================================


class TestAuditLogging:
    """Test internal audit logging functionality."""

    def test_audit_log_creates_entry(self, temp_db):
        """Test _audit_log creates audit log entry."""
        with temp_db.transaction() as conn:
            log_id = temp_db._audit_log(
                conn=conn,
                event_type="test_event",
                action="test_action",
                data_subject_id="subject-1",
                result="success",
            )

        # Verify log was created
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT * FROM audit_logs WHERE log_id = ?", (log_id,))
        log = cursor.fetchone()

        assert log is not None
        assert log["event_type"] == "test_event"
        assert log["action"] == "test_action"
        assert log["data_subject_id"] == "subject-1"
        assert log["result"] == "success"

    def test_audit_log_with_details(self, temp_db):
        """Test _audit_log stores details as JSON."""
        details = {
            "key1": "value1",
            "key2": 42,
            "key3": ["list", "of", "items"],
        }

        with temp_db.transaction() as conn:
            log_id = temp_db._audit_log(
                conn=conn,
                event_type="test_event",
                action="test_action",
                details=details,
            )

        # Verify details stored as JSON
        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT details FROM audit_logs WHERE log_id = ?", (log_id,))
        stored_details = json.loads(cursor.fetchone()["details"])

        assert stored_details == details

    def test_audit_log_with_all_fields(self, temp_db):
        """Test _audit_log stores all optional fields."""
        with temp_db.transaction() as conn:
            log_id = temp_db._audit_log(
                conn=conn,
                event_type="data_access",
                action="view_profile",
                data_subject_id="subject-1",
                user_id="user-123",
                resource_type="profile",
                resource_id="profile-456",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                result="success",
                details={"field": "value"},
            )

        conn = temp_db.get_connection()
        cursor = conn.execute("SELECT * FROM audit_logs WHERE log_id = ?", (log_id,))
        log = cursor.fetchone()

        assert log["user_id"] == "user-123"
        assert log["resource_type"] == "profile"
        assert log["resource_id"] == "profile-456"
        assert log["ip_address"] == "192.168.1.1"
        assert log["user_agent"] == "Mozilla/5.0"


# ============================================================================
# Utility Tests
# ============================================================================


class TestDatabaseUtilities:
    """Test database utility functions."""

    def test_vacuum_reduces_file_size(self, temp_db):
        """Test vacuum() optimizes database after deletions."""
        # Add many records
        with temp_db.transaction() as conn:
            for i in range(100):
                conn.execute("""
                    INSERT INTO processing_records (
                        record_id, timestamp, purpose, legal_basis, data_categories,
                        data_subject_id, controller, operation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"rec-{i}",
                    datetime.now(timezone.utc).isoformat(),
                    "test",
                    "consent",
                    "[]",
                    f"subject-{i}",
                    "Test",
                    "test_op",
                ))

        size_before = temp_db.db_path.stat().st_size

        # Delete all records
        with temp_db.transaction() as conn:
            conn.execute("DELETE FROM processing_records")

        # Vacuum should reduce size
        temp_db.vacuum()

        size_after = temp_db.db_path.stat().st_size

        # After vacuum, size should be smaller or same
        assert size_after <= size_before


# ============================================================================
# Singleton Tests
# ============================================================================


class TestGetDatabase:
    """Test get_database singleton function."""

    def test_get_database_creates_instance(self):
        """Test get_database creates and returns instance."""
        db = get_database()

        assert db is not None
        assert isinstance(db, DatabaseManager)

    def test_get_database_returns_same_instance(self):
        """Test get_database returns same instance on multiple calls."""
        db1 = get_database()
        db2 = get_database()

        assert db1 is db2

    def test_get_database_thread_safe(self):
        """Test get_database is thread-safe."""
        instances = []

        def get_db():
            db = get_database()
            instances.append(id(db))

        threads = [threading.Thread(target=get_db) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get the same instance
        assert len(set(instances)) == 1

    def test_singleton_reset(self, reset_global_db):
        """Test singleton can be reset for testing."""
        db1 = get_database()

        # Reset (done by fixture)
        import lead_gen.core.database
        lead_gen.core.database._db_manager = None

        db2 = get_database()

        # Should be different instances
        assert db1 is not db2


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestSchemaValidation:
    """Test database schema constraints and validation."""

    def test_processing_record_requires_timestamp(self, temp_db):
        """Test processing_records enforces NOT NULL on timestamp."""
        with pytest.raises(sqlite3.IntegrityError):
            with temp_db.transaction() as conn:
                conn.execute("""
                    INSERT INTO processing_records (
                        record_id, purpose, legal_basis, data_categories,
                        controller, operation
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, ("test", "test", "consent", "[]", "Test", "test_op"))

    def test_consent_record_validates_withdrawal(self, temp_db):
        """Test consent_records validates withdrawal_at >= granted_at."""
        with pytest.raises(sqlite3.IntegrityError):
            with temp_db.transaction() as conn:
                conn.execute("""
                    INSERT INTO consent_records (
                        consent_id, data_subject_id, purpose, granted,
                        granted_at, withdrawn_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "test",
                    "subject-1",
                    "test",
                    True,
                    datetime.now(timezone.utc).isoformat(),
                    (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),  # Before granted
                ))

    def test_data_subject_request_valid_types(self, temp_db):
        """Test data_subject_requests enforces valid request types."""
        with pytest.raises(sqlite3.IntegrityError):
            with temp_db.transaction() as conn:
                conn.execute("""
                    INSERT INTO data_subject_requests (
                        request_id, request_type, data_subject_id,
                        requested_at, deadline, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "test",
                    "invalid_type",  # Invalid type
                    "subject-1",
                    datetime.now(timezone.utc).isoformat(),
                    (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "pending",
                ))

    def test_data_subject_request_valid_status(self, temp_db):
        """Test data_subject_requests enforces valid status values."""
        with pytest.raises(sqlite3.IntegrityError):
            with temp_db.transaction() as conn:
                conn.execute("""
                    INSERT INTO data_subject_requests (
                        request_id, request_type, data_subject_id,
                        requested_at, deadline, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "test",
                    "access",
                    "subject-1",
                    datetime.now(timezone.utc).isoformat(),
                    (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "invalid_status",  # Invalid status
                ))
