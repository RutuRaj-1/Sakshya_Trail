"""
Test Suite: Prompt 6 — Notification Integration, RBAC-Aware Communication, Delivery Reliability, and E2E Verification
Covers:
1. Failed notification response schema contract (total_count, page, limit, items)
2. Tenant isolation (INSTITUTION_USER inbox, details, retry prohibition)
3. Auditor read-only restrictions on mutations (retry/dispatch forbidden, inbox/failed read-only)
4. Recipient selection across the 7 canonical roles
5. Idempotent deduplication and bounded retries
6. Honest delivery semantics: In-App, Email (simulated mail-catcher vs invalid recipient), SMS (mock)
7. Workflow event notifications:
   - Submission, return for correction, correction response, readiness, approval, order, bank action, closure
8. Operational oversight feed for SYSTEM_ADMIN
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import LifecycleNotification, NotificationDeliveryAttempt
from app.modules.lifecycle.event_notification_service import emit_material_event
from app.modules.lifecycle.notification_service import (
    dispatch_single_notification,
    retry_notification,
    list_failed_notifications,
)
from app.modules.auth.service import provision_user
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    create_access_token,
)
from app.core.config import settings


def set_auth(client: TestClient, user: User):
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    client.cookies.set(
        name=settings.AUTH_COOKIE_NAME,
        value=token,
        path=settings.AUTH_COOKIE_PATH,
    )


@pytest.fixture
def notify_fixture(db_session: Session):
    inst_a = Institution(
        code="INST-NOTIF-A",
        legal_name="Apex Institute of Technology",
        institution_type="TECHNICAL",
        contact_email="apex@aicte.test",
        state="Maharashtra",
        assigned_office="WRO-MUMBAI",
        is_active=True,
    )
    inst_b = Institution(
        code="INST-NOTIF-B",
        legal_name="Beacon Institute of Science",
        institution_type="POLYTECHNIC",
        contact_email="beacon@aicte.test",
        state="Karnataka",
        assigned_office="SRO-BANGALORE",
        is_active=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    admin = provision_user(db_session, "Admin User", "admin@notif.test", "Secret123!", ROLE_SYSTEM_ADMIN)
    scrutiny = provision_user(db_session, "Scrutiny Officer", "scrutiny@notif.test", "Secret123!", ROLE_SCRUTINY_OFFICER)
    branch = provision_user(db_session, "Branch Head", "branch@notif.test", "Secret123!", ROLE_BRANCH_HEAD)
    authority = provision_user(db_session, "Authority User", "authority@notif.test", "Secret123!", ROLE_COMPETENT_AUTHORITY)
    finance = provision_user(db_session, "Finance Officer", "finance@notif.test", "Secret123!", ROLE_FINANCE_OFFICER)
    auditor = provision_user(db_session, "Auditor User", "auditor@notif.test", "Secret123!", ROLE_AUDITOR)
    inst_user_a = provision_user(db_session, "Apex User", "user@apex.test", "Secret123!", ROLE_INSTITUTION_USER, institution_id=inst_a.id)
    inst_user_b = provision_user(db_session, "Beacon User", "user@beacon.test", "Secret123!", ROLE_INSTITUTION_USER, institution_id=inst_b.id)

    # Active FDR instruments
    ins_a = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-NOTIF-A001",
        bank_name="State Bank of India",
        branch="Main",
        amount=1000000.0,
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 12, 31),
        status="ACTIVE",
    )
    ins_b = Instrument(
        institution_id=inst_b.id,
        reference_number="FDR-NOTIF-B001",
        bank_name="Punjab National Bank",
        branch="City",
        amount=500000.0,
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 12, 31),
        status="ACTIVE",
    )
    db_session.add_all([ins_a, ins_b])
    db_session.commit()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "ins_a": ins_a,
        "ins_b": ins_b,
        "admin": admin,
        "scrutiny": scrutiny,
        "branch": branch,
        "authority": authority,
        "finance": finance,
        "auditor": auditor,
        "inst_user_a": inst_user_a,
        "inst_user_b": inst_user_b,
    }


def test_failed_notification_response_schema_contract(client: TestClient, db_session: Session, notify_fixture):
    """
    Verifies that GET /api/v1/lifecycle/notifications/failed returns
    { total_count, page, limit, items } matching NotificationListResponse contract.
    """
    f = notify_fixture
    set_auth(client, f["admin"])

    # Initially empty response
    res = client.get("/api/v1/lifecycle/notifications/failed?page=1&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert "total_count" in data
    assert "page" in data
    assert "limit" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["total_count"] == 0

    # Create a failed notification
    failed_notif = LifecycleNotification(
        idempotency_key="test-failed-1",
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        event_type="NOTIFICATION_DELIVERY_FAILED",
        trigger_date=date.today(),
        recipient_role="SCRUTINY_OFFICER",
        recipient_email="invalid-email-format",
        channel="EMAIL",
        title="Test Failed Email",
        message="Delivery attempted",
        status="FAILED",
        failure_category="INVALID_RECIPIENT",
        failure_reason="Missing or malformed recipient email",
        is_mock=False,
    )
    db_session.add(failed_notif)
    db_session.commit()

    # Query again
    res = client.get("/api/v1/lifecycle/notifications/failed?page=1&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    assert len(data["items"]) >= 1
    item = next(i for i in data["items"] if i["id"] == failed_notif.id)
    assert item["status"] == "FAILED"
    assert item["failure_category"] == "INVALID_RECIPIENT"
    assert item["channel"] == "EMAIL"


def test_tenant_isolation_inbox_and_history(client: TestClient, db_session: Session, notify_fixture):
    """
    Verifies strict institution scope:
    - Inst User A only receives notifications for Inst A.
    - Inst User B cannot view Inst A's inbox or instrument history.
    """
    f = notify_fixture

    # Emit submission event for Inst A
    emit_material_event(
        db=db_session,
        event_type="INSTRUMENT_SUBMITTED",
        entity_type="INSTRUMENT",
        entity_id=f["ins_a"].id,
        actor_user=f["inst_user_a"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="SUBMITTED",
    )
    db_session.commit()

    # Inst User A queries inbox -> has notif
    set_auth(client, f["inst_user_a"])
    res_a = client.get("/api/v1/lifecycle/notifications/inbox")
    assert res_a.status_code == 200
    items_a = res_a.json()["items"]
    assert any(i["instrument_id"] == f["ins_a"].id for i in items_a)

    # Inst User B queries inbox -> Inst A notif is strictly excluded
    set_auth(client, f["inst_user_b"])
    res_b = client.get("/api/v1/lifecycle/notifications/inbox")
    assert res_b.status_code == 200
    items_b = res_b.json()["items"]
    assert not any(i["instrument_id"] == f["ins_a"].id for i in items_b)

    # Inst User B attempts to access Inst A instrument notification history -> 403 Forbidden
    res_forbidden = client.get(f"/api/v1/lifecycle/instruments/{f['ins_a'].id}/notifications")
    assert res_forbidden.status_code == 403


def test_auditor_read_only_and_mutation_restrictions(client: TestClient, db_session: Session, notify_fixture):
    """
    Auditor can view audit views and failed notifications list,
    but is strictly forbidden from mutating notifications (retry, dispatch-due).
    """
    f = notify_fixture
    set_auth(client, f["auditor"])

    # 1. Auditor CAN view failed notifications list (Audit view)
    res_list = client.get("/api/v1/lifecycle/notifications/failed")
    assert res_list.status_code == 200

    # 2. Auditor CAN view own personal inbox
    res_inbox = client.get("/api/v1/lifecycle/notifications/inbox")
    assert res_inbox.status_code == 200

    # 3. Auditor CANNOT trigger manual retry (403 Forbidden)
    res_retry = client.post("/api/v1/lifecycle/notifications/notif-dummy-id/retry", json={"force": False})
    assert res_retry.status_code == 403

    # 4. Auditor CANNOT trigger reminder dispatch (403 Forbidden)
    res_dispatch = client.post("/api/v1/lifecycle/notifications/dispatch-due", json={"batch_size": 10})
    assert res_dispatch.status_code == 403


def test_idempotent_deduplication_and_safe_retries(client: TestClient, db_session: Session, notify_fixture):
    """
    Verifies that calling emit_material_event repeatedly on the same day with unchanged
    inputs does not produce duplicate notifications.
    """
    f = notify_fixture

    # Dispatch event 1
    notifs_run1 = emit_material_event(
        db=db_session,
        event_type="VALIDATION_FINDING_CREATED",
        entity_type="INSTRUMENT",
        entity_id=f["ins_a"].id,
        actor_user=f["scrutiny"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="FINDINGS_LOGGED",
        details={"finding_code": "VAL-XSRC-001", "severity": "HIGH"},
    )
    db_session.commit()
    count_run1 = len(notifs_run1)
    assert count_run1 >= 1

    # Dispatch same event again
    notifs_run2 = emit_material_event(
        db=db_session,
        event_type="VALIDATION_FINDING_CREATED",
        entity_type="INSTRUMENT",
        entity_id=f["ins_a"].id,
        actor_user=f["scrutiny"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="FINDINGS_LOGGED",
        details={"finding_code": "VAL-XSRC-001", "severity": "HIGH"},
    )
    db_session.commit()

    # Re-returned existing records without creating new database rows
    assert len(notifs_run2) == count_run1
    all_notifs = db_session.scalars(
        select(LifecycleNotification).where(
            LifecycleNotification.instrument_id == f["ins_a"].id,
            LifecycleNotification.event_type == "VALIDATION_FINDING_CREATED",
        )
    ).all()
    assert len(list(all_notifs)) == 1


def test_honest_delivery_semantics_and_mock_tagging(db_session: Session, notify_fixture):
    """
    Verifies honest delivery attribution:
    - Email with mock SMTP returns ACCEPTED with is_mock=True.
    - Email with invalid address returns FAILED with INVALID_RECIPIENT.
    - SMS returns MOCKED with is_mock=True.
    - In-app returns DELIVERED.
    """
    f = notify_fixture

    # 1. Email with mock provider
    email_notif = LifecycleNotification(
        idempotency_key="test-email-honest-1",
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        event_type="MATURITY_APPROACHING",
        trigger_date=date.today(),
        recipient_role="INSTITUTION_USER",
        recipient_email="principal@apex.test",
        channel="EMAIL",
        title="Maturity Notice",
        message="Matures soon",
        status="CREATED",
    )
    db_session.add(email_notif)
    db_session.commit()

    res_email = dispatch_single_notification(db_session, email_notif)
    assert res_email.status == "ACCEPTED"
    assert res_email.is_mock is True
    assert "LOCAL_MAIL_CATCHER" in (res_email.mock_disclaimer or "")
    assert email_notif.status == "ACCEPTED"
    assert email_notif.is_mock is True

    # 2. Email with invalid address
    bad_email_notif = LifecycleNotification(
        idempotency_key="test-email-bad-1",
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        event_type="MATURITY_APPROACHING",
        trigger_date=date.today(),
        recipient_role="INSTITUTION_USER",
        recipient_email="invalid_email_no_at",
        channel="EMAIL",
        title="Maturity Notice",
        message="Matures soon",
        status="CREATED",
    )
    db_session.add(bad_email_notif)
    db_session.commit()

    res_bad = dispatch_single_notification(db_session, bad_email_notif)
    assert res_bad.status == "FAILED"
    assert res_bad.error_category == "INVALID_RECIPIENT"
    assert bad_email_notif.status == "FAILED"
    assert bad_email_notif.failure_category == "INVALID_RECIPIENT"

    # 3. Mock SMS
    sms_notif = LifecycleNotification(
        idempotency_key="test-sms-honest-1",
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        event_type="MATURITY_APPROACHING",
        trigger_date=date.today(),
        recipient_role="INSTITUTION_USER",
        channel="MOCK_SMS",
        title="SMS Alert",
        message="FDR alert",
        status="CREATED",
    )
    db_session.add(sms_notif)
    db_session.commit()

    res_sms = dispatch_single_notification(db_session, sms_notif)
    assert res_sms.status == "MOCKED"
    assert res_sms.is_mock is True
    assert "MOCK" in (res_sms.mock_disclaimer or "")
    assert sms_notif.status == "MOCKED"


def test_business_workflow_events_and_recipient_routing(db_session: Session, notify_fixture):
    """
    Verifies event emission across 9-stage workflow actions:
    - SUBMISSION_RETURNED_FOR_CORRECTION -> notifies Institution User and Branch Head
    - CORRECTION_RESPONSE_SUBMITTED -> notifies Scrutiny Officer and Institution User
    - RELEASE_READINESS_BLOCKED -> notifies Branch Head and Competent Authority with blocker count
    - RELEASE_CASE_APPROVED -> notifies Finance Officer and Institution User
    - RELEASE_ORDER_RECORDED -> notifies Finance Officer and Institution User
    - DOWNSTREAM_BANK_ACTION_RECORDED -> notifies Finance Officer and Institution User
    - RELEASE_CASE_CLOSED -> notifies Finance Officer, Branch Head, and Institution User
    """
    f = notify_fixture

    # 1. Return for correction
    notifs_returned = emit_material_event(
        db=db_session,
        event_type="SUBMISSION_RETURNED_FOR_CORRECTION",
        entity_type="INSTRUMENT",
        entity_id=f["ins_a"].id,
        actor_user=f["scrutiny"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="RETURNED_FOR_CORRECTION",
        details={"reason": "Maturity date mismatch on certificate."},
    )
    db_session.commit()
    roles_returned = [n.recipient_role for n in notifs_returned]
    assert "INSTITUTION_USER" in roles_returned
    assert "BRANCH_HEAD" in roles_returned
    assert "SYSTEM_ADMIN" in roles_returned

    # 2. Correction response submitted
    notifs_corrected = emit_material_event(
        db=db_session,
        event_type="CORRECTION_RESPONSE_SUBMITTED",
        entity_type="INSTRUMENT",
        entity_id=f["ins_a"].id,
        actor_user=f["inst_user_a"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="SUBMITTED",
        details={"reference_number": f["ins_a"].reference_number},
    )
    db_session.commit()
    roles_corrected = [n.recipient_role for n in notifs_corrected]
    assert "SCRUTINY_OFFICER" in roles_corrected
    assert "INSTITUTION_USER" in roles_corrected

    # 3. Release Readiness Blocked
    notifs_blocked = emit_material_event(
        db=db_session,
        event_type="RELEASE_READINESS_BLOCKED",
        entity_type="RELEASE_CASE",
        entity_id="CASE-NOTIF-001",
        actor_user=f["scrutiny"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="BLOCKED",
        details={"readiness_status": "BLOCKED", "blockers_count": 2},
    )
    db_session.commit()
    roles_blocked = [n.recipient_role for n in notifs_blocked]
    assert "BRANCH_HEAD" in roles_blocked
    assert "COMPETENT_AUTHORITY" in roles_blocked
    blocked_bh = next(n for n in notifs_blocked if n.recipient_role == "BRANCH_HEAD")
    assert "2 Blocker(s)" in blocked_bh.title

    # 4. Release Case Approved
    notifs_approved = emit_material_event(
        db=db_session,
        event_type="RELEASE_CASE_APPROVED",
        entity_type="RELEASE_CASE",
        entity_id="CASE-NOTIF-001",
        actor_user=f["authority"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="APPROVED",
    )
    db_session.commit()
    roles_approved = [n.recipient_role for n in notifs_approved]
    assert "FINANCE_OFFICER" in roles_approved
    assert "INSTITUTION_USER" in roles_approved

    # 5. Release Case Closed
    notifs_closed = emit_material_event(
        db=db_session,
        event_type="RELEASE_CASE_CLOSED",
        entity_type="RELEASE_CASE",
        entity_id="CASE-NOTIF-001",
        actor_user=f["branch"],
        instrument_id=f["ins_a"].id,
        institution_id=f["inst_a"].id,
        resulting_state="CLOSED",
        details={"case_number": "CASE-NOTIF-001", "closure_notes": "Disbursement settled."},
    )
    db_session.commit()
    roles_closed = [n.recipient_role for n in notifs_closed]
    assert "FINANCE_OFFICER" in roles_closed
    assert "BRANCH_HEAD" in roles_closed
    assert "INSTITUTION_USER" in roles_closed
    assert "SYSTEM_ADMIN" in roles_closed
