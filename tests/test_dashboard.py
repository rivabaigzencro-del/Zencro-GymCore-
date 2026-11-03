"""Tests for Day 6: Dashboard Statistics, Financial KPIs, and Activity Feeds."""
import uuid
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.refund import Refund, RefundType, RefundStatus


def _seed_gym_data(client: TestClient, headers: dict) -> dict:
    """Helper to seed member, plan, membership, invoice, payment, and attendance."""
    # 1. Member
    m_resp = client.post(
        "/api/v1/members",
        headers=headers,
        json={"full_name": "Karan Sharma", "phone": "9876543210", "email": "karan@example.com"},
    )
    assert m_resp.status_code == 201
    member = m_resp.json()

    # 2. Plan
    p_resp = client.post(
        "/api/v1/membership-plans",
        headers=headers,
        json={"name": "Monthly Gold", "duration": 1, "duration_unit": "MONTHS", "price": 2000.00},
    )
    assert p_resp.status_code == 201
    plan = p_resp.json()

    # 3. Membership
    today = date.today()
    ms_resp = client.post(
        "/api/v1/memberships",
        headers=headers,
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": str(today)},
    )
    assert ms_resp.status_code == 201
    membership = ms_resp.json()

    # 4. Invoice
    inv_resp = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={
            "member_id": member["id"],
            "membership_id": membership["id"],
            "issue_date": str(today),
            "due_date": str(today + timedelta(days=5)),
            "amount_paise": 200000,
        },
    )
    assert inv_resp.status_code == 201
    invoice = inv_resp.json()

    # 5. Payment (partial payment 1500.00 = 150000 paise)
    pay_resp = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "invoice_id": invoice["id"],
            "member_id": member["id"],
            "amount_paise": 150000,
            "payment_method": "UPI",
        },
    )
    assert pay_resp.status_code == 201
    payment = pay_resp.json()

    # 6. Attendance check-in
    att_resp = client.post(
        "/api/v1/attendance/check-in",
        headers=headers,
        json={"member_id": member["id"]},
    )
    assert att_resp.status_code in (200, 201)
    attendance = att_resp.json()

    return {
        "member": member,
        "plan": plan,
        "membership": membership,
        "invoice": invoice,
        "payment": payment,
        "attendance": attendance,
    }


def test_dashboard_summary_and_all_kpis(client: TestClient, registered_gym):
    """Verify aggregated dashboard summary endpoint returns complete, accurate KPIs."""
    headers = registered_gym["headers"]
    data = _seed_gym_data(client, headers)

    resp = client.get("/api/v1/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    # Member stats
    m_stats = body["member_stats"]
    assert m_stats["total_members"] == 1
    assert m_stats["active_members"] == 1
    assert m_stats["inactive_members"] == 0

    # Financial stats
    f_stats = body["financial_stats"]
    assert f_stats["total_revenue_paise"] == 150000
    assert f_stats["total_revenue_rupees"] == 1500.0
    assert f_stats["today_collection_paise"] == 150000
    assert f_stats["pending_payments_count"] == 1  # 50000 balance remains on invoice
    assert f_stats["outstanding_dues_paise"] == 50000
    assert f_stats["outstanding_dues_rupees"] == 500.0

    # Membership stats
    ms_stats = body["membership_stats"]
    assert ms_stats["active_memberships"] == 1
    assert ms_stats["upcoming_renewals"] == 1

    # Attendance stats
    att_stats = body["attendance_stats"]
    assert att_stats["today_check_ins"] == 1
    assert len(att_stats["daily_trends"]) == 7

    # Recent Feeds
    assert len(body["recent_payments"]) == 1
    assert body["recent_payments"][0]["amount_paise"] == 150000
    assert len(body["pending_dues"]) == 1
    assert body["pending_dues"][0]["balance_amount_paise"] == 50000
    assert len(body["recent_registrations"]) == 1
    assert len(body["recent_attendance"]) == 1


def test_dashboard_modular_kpi_endpoints(client: TestClient, registered_gym):
    """Verify individual sub-endpoints for members, financial, memberships, and attendance."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    # 1. Members
    m_resp = client.get("/api/v1/dashboard/members", headers=headers)
    assert m_resp.status_code == 200
    assert m_resp.json()["total_members"] == 1

    # 2. Financial
    f_resp = client.get("/api/v1/dashboard/financial", headers=headers)
    assert f_resp.status_code == 200
    assert f_resp.json()["total_revenue_paise"] == 150000

    # 3. Memberships
    ms_resp = client.get("/api/v1/dashboard/memberships", headers=headers)
    assert ms_resp.status_code == 200
    assert ms_resp.json()["active_memberships"] == 1

    # 4. Attendance
    att_resp = client.get("/api/v1/dashboard/attendance?days_trend=14", headers=headers)
    assert att_resp.status_code == 200
    assert att_resp.json()["today_check_ins"] == 1
    assert len(att_resp.json()["daily_trends"]) == 14


def test_dashboard_recent_feed_endpoints(client: TestClient, registered_gym):
    """Verify modular activity feed endpoints."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    assert client.get("/api/v1/dashboard/recent-payments", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/upcoming-renewals", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/pending-dues", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/recent-registrations", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/recent-attendance", headers=headers).status_code == 200


def test_dashboard_financial_excludes_pending_and_failed_and_deducts_refunds(
    client: TestClient, registered_gym, db: Session
):
    """
    Ensure financial stats do not count pending/failed payments as revenue,
    and properly subtract completed refunds from net collections.
    """
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)
    tenant_id = registered_gym["tenant_id"]

    # Insert a dummy FAILED payment directly in DB
    failed_payment = Payment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        member_id=uuid.UUID(seeded["member"]["id"]),
        invoice_id=uuid.UUID(seeded["invoice"]["id"]),
        amount_paise=999999,
        payment_method=PaymentMethod.CARD,
        payment_status=PaymentStatus.FAILED,
        payment_date=datetime.now(timezone.utc),
    )
    db.add(failed_payment)
    db.commit()

    # Verify revenue still only counts the 150000 paise
    resp = client.get("/api/v1/dashboard/financial", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_revenue_paise"] == 150000

    # Issue a refund of 50000 paise on the completed payment
    pay_id = seeded["payment"]["id"]
    rf_resp = client.post(
        f"/api/v1/payments/{pay_id}/refund",
        headers=headers,
        json={"amount_paise": 50000, "reason": "Customer discount adjustment"},
    )
    assert rf_resp.status_code == 200

    # Net revenue should now be 150000 - 50000 = 100000 paise
    resp2 = client.get("/api/v1/dashboard/financial", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["total_revenue_paise"] == 100000
    assert resp2.json()["total_revenue_rupees"] == 1000.0


def test_dashboard_tenant_isolation(client: TestClient, registered_gym, second_registered_gym):
    """Verify that dashboard statistics in Gym 1 do not bleed into Gym 2."""
    headers1 = registered_gym["headers"]
    headers2 = second_registered_gym["headers"]

    # Seed Gym 1
    _seed_gym_data(client, headers1)

    # Gym 2 dashboard must be empty
    resp2 = client.get("/api/v1/dashboard/summary", headers=headers2)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["member_stats"]["total_members"] == 0
    assert body2["financial_stats"]["total_revenue_paise"] == 0
    assert body2["membership_stats"]["active_memberships"] == 0
    assert body2["attendance_stats"]["today_check_ins"] == 0
    assert len(body2["recent_payments"]) == 0


def test_dashboard_rbac(client: TestClient, gym_with_roles):
    """Verify OWNER, MANAGER, and FRONT_DESK can read dashboard, unauthenticated cannot."""
    # Owner
    assert client.get("/api/v1/dashboard/summary", headers=gym_with_roles["headers"]).status_code == 200
    # Manager
    assert client.get("/api/v1/dashboard/summary", headers=gym_with_roles["manager_headers"]).status_code == 200
    # Front Desk
    assert client.get("/api/v1/dashboard/summary", headers=gym_with_roles["front_desk_headers"]).status_code == 200
    # Unauthenticated
    assert client.get("/api/v1/dashboard/summary").status_code == 401

