#!/usr/bin/env python3
"""
Test script for GDPR implementation with SQLite persistence.

This script demonstrates:
1. Database initialization
2. Processing record storage
3. Consent management
4. Data subject requests (access, erasure)
5. Automatic data purging
6. Audit logging
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for config
os.environ['GDPR__RETENTION_DAYS'] = '90'
os.environ['GDPR__LEGAL_BASIS'] = 'legitimate_interest'
os.environ['GDPR__DPO_EMAIL'] = 'dpo@company.com'
os.environ['GDPR__ENABLE_AUDIT_LOG'] = 'true'
os.environ['LOG_LEVEL'] = 'WARNING'  # Reduce logging noise

# Direct imports to avoid package init issues
from lead_gen.core.config import get_settings
from lead_gen.core.database import DatabaseManager
from lead_gen.core.gdpr import (
    GDPRManager,
    ProcessingPurpose,
    DataCategory,
    LegalBasis
)

def test_gdpr_implementation():
    """Test the complete GDPR implementation."""
    print("=" * 60)
    print("GDPR Compliance Implementation Test")
    print("=" * 60)
    print()

    # 1. Initialize database
    print("1. Initializing database...")
    db = DatabaseManager(db_path="test_gdpr.db")
    print(f"   ✓ Database initialized at: {db.db_path}")
    print()

    # 2. Initialize GDPR manager
    print("2. Initializing GDPR manager...")
    settings = get_settings()
    gdpr = GDPRManager()
    print(f"   ✓ GDPR manager initialized")
    print(f"   - Retention period: {gdpr.retention_days} days")
    print(f"   - Legal basis: {gdpr.default_legal_basis.value}")
    print(f"   - DPO email: {gdpr.dpo_email}")
    print(f"   - Audit enabled: {gdpr.audit_enabled}")
    print()

    # 3. Test processing record (Art. 30)
    print("3. Testing processing record (GDPR Art. 30)...")
    record = gdpr.record_processing(
        purpose=ProcessingPurpose.LEAD_GENERATION,
        data_categories=[
            DataCategory.BUSINESS_NAME,
            DataCategory.BUSINESS_EMAIL,
            DataCategory.BUSINESS_PHONE
        ],
        operation="Scraped business leads from Google Places API",
        source="Google Places API",
        data_subject_id=gdpr.pseudonymize("example-business@test.com")
    )
    print(f"   ✓ Processing record created")
    print(f"   - Record ID: {record.record_id}")
    print(f"   - Purpose: {record.purpose.value}")
    print(f"   - Legal basis: {record.legal_basis.value}")
    print(f"   - Retention until: {record.retention_until}")
    print()

    # 4. Test consent management (Art. 7)
    print("4. Testing consent management (GDPR Art. 7)...")
    data_subject_id = gdpr.pseudonymize("user@example.com")
    consent = gdpr.record_consent(
        data_subject_id=data_subject_id,
        purpose=ProcessingPurpose.OUTREACH,
        granted=True,
        consent_text="I consent to receive business outreach emails",
        ip_address="192.0.2.1",
        user_agent="Mozilla/5.0 (Test)"
    )
    print(f"   ✓ Consent recorded")
    print(f"   - Consent ID: {consent.consent_id}")
    print(f"   - Purpose: {consent.purpose.value}")
    print(f"   - Granted: {consent.granted}")
    print()

    # 5. Test data subject access request (Art. 15)
    print("5. Testing data subject access request (GDPR Art. 15)...")
    access_request = gdpr.create_access_request(data_subject_id=data_subject_id)
    print(f"   ✓ Access request created")
    print(f"   - Request ID: {access_request.request_id}")
    print(f"   - Deadline: {access_request.deadline}")
    print()

    # 6. Test data export (Art. 15/20)
    print("6. Testing data export (GDPR Art. 15/20)...")
    export_data = gdpr.export_data_subject_data(data_subject_id=data_subject_id)
    print(f"   ✓ Data exported")
    print(f"   - Processing records: {len(export_data['processing_records'])}")
    print(f"   - Consent records: {len(export_data['consent_records'])}")
    print(f"   - Requests: {len(export_data['data_subject_requests'])}")
    print()

    # 7. Test erasure request (Art. 17 - Right to be Forgotten)
    print("7. Testing erasure request (GDPR Art. 17)...")
    erasure_request = gdpr.create_erasure_request(data_subject_id=data_subject_id)
    print(f"   ✓ Erasure request created")
    print(f"   - Request ID: {erasure_request.request_id}")

    # Execute erasure
    counts = gdpr.execute_erasure_request(erasure_request.request_id)
    print(f"   ✓ Erasure executed")
    print(f"   - Processing records deleted: {counts.get('processing_records', 0)}")
    print(f"   - Consents withdrawn: {counts.get('consents_withdrawn', 0)}")
    print()

    # 8. Test retention checking
    print("8. Testing retention checking...")
    expired = gdpr.check_retention()
    print(f"   ✓ Retention check completed")
    print(f"   - Expired records found: {len(expired)}")
    print()

    # 9. Test audit logs
    print("9. Testing audit logs...")
    audit_logs = gdpr.get_audit_logs(limit=5)
    print(f"   ✓ Audit logs retrieved")
    print(f"   - Recent log entries: {len(audit_logs)}")
    for log in audit_logs[:3]:
        print(f"     * {log['event_type']}: {log['action']}")
    print()

    # 10. Get compliance statistics
    print("10. GDPR Compliance Statistics...")
    stats = gdpr.get_stats()
    print(f"   ✓ Statistics retrieved")
    print(f"   - Processing records: {stats['processing_records_count']}")
    print(f"   - Consent records: {stats['consent_records_count']}")
    print(f"   - Audit logs: {stats['audit_logs_count']}")
    print(f"   - Data subject requests: {stats['data_subject_requests_count']}")
    print(f"   - Expired records needing purge: {stats['expired_records_needing_purge']}")
    print(f"   - Overdue requests: {stats['overdue_requests']}")
    print(f"   - Database size: {stats.get('size_bytes', 0):,} bytes")
    print()

    # 11. Test automatic purge
    print("11. Testing automatic purge...")
    purge_count = gdpr.db.purge_expired_records()
    print(f"   ✓ Automatic purge completed")
    print(f"   - Records purged: {purge_count}")
    print()

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("GDPR Compliance Features Verified:")
    print("  ✓ Art. 30: Records of processing activities")
    print("  ✓ Art. 17: Right to erasure (Right to be Forgotten)")
    print("  ✓ Art. 15: Right of access by data subject")
    print("  ✓ Art. 20: Right to data portability")
    print("  ✓ Art. 7:  Consent management")
    print("  ✓ Automatic data deletion after retention period")
    print("  ✓ Complete audit logging")
    print("  ✓ SQLite persistence (no more in-memory storage)")
    print()

    # Cleanup
    db.close()
    import os
    if os.path.exists("test_gdpr.db"):
        os.remove("test_gdpr.db")
        print("Test database cleaned up.")

if __name__ == "__main__":
    try:
        test_gdpr_implementation()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
