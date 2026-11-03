"""Tests for Day 6: Reports Backend APIs (Revenue, Memberships, Attendance, Dues, Expiries)."""
import uuid
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient

from tests.test_dashboard import _seed_gym_data


def test_revenue_report_date_filtering_and_methods(client: TestClient, registered_gym):
    """Test revenue report with date range and payment method filters."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)
    today = date.today()

    resp = client.get(
        f"/api/v1/reports/revenue?start_date={today}&end_date={today}&payment_method=UPI",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_gross_paise"] == 150000
    assert body["summary"]["total_net_paise"] == 150000
    assert body["summary"]["by_payment_method"]["UPI"] == 150000
    assert len(body["transactions"]) == 1

    # Filter with non-matching method returns 0 transactions
    resp_cash = client.get(
        f"/api/v1/reports/revenue?start_date={today}&end_date={today}&payment_method=CASH",
        headers=headers,
    )
    assert resp_cash.status_code == 200
    assert resp_cash.json()["summary"]["total_gross_paise"] == 0
    assert len(resp_cash.json()["transactions"]) == 0


def test_membership_report_plans_and_status(client: TestClient, registered_gym):
    """Test membership report with status filter and plan distributions."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)

    resp = client.get("/api/v1/reports/memberships?status=ACTIVE", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_memberships"] == 1
    assert body["summary"]["active_count"] == 1
    assert "Monthly Gold" in body["summary"]["by_plan"]
    assert len(body["memberships"]) == 1


def test_attendance_report_slots_and_methods(client: TestClient, registered_gym):
    """Test attendance report with time slot breakdowns and check-in methods."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)
    today = date.today()

    resp = client.get(
        f"/api/v1/reports/attendance?start_date={today}&end_date={today}",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_visits"] == 1
    assert body["summary"]["unique_members"] == 1
    assert body["summary"]["by_method"]["MANUAL"] == 1
    assert len(body["visits"]) == 1


def test_pending_dues_report_ageing_buckets(client: TestClient, registered_gym):
    """Test pending dues report with balance amounts and ageing categorization."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)

    resp = client.get("/api/v1/reports/pending-dues", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_outstanding_paise"] == 50000
    assert body["summary"]["total_pending_invoices"] == 1
    assert len(body["invoices"]) == 1
    assert body["invoices"][0]["balance_amount_paise"] == 50000


def test_expiry_report_categories(client: TestClient, registered_gym):
    """Test membership expiry report categorized into status buckets."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)

    resp = client.get("/api/v1/reports/expiries?status=ALL", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_count"] == 1
    assert body["summary"]["expiring_soon_count"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "EXPIRING_SOON"


def test_reports_empty_dataset_handling(client: TestClient, registered_gym):
    """Verify that reports querying empty date ranges handle gracefully with 200 and zeroed summaries."""
    headers = registered_gym["headers"]
    past_date = date.today() - timedelta(days=365)

    resp = client.get(
        f"/api/v1/reports/revenue?start_date={past_date}&end_date={past_date}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]["total_gross_paise"] == 0
    assert len(resp.json()["transactions"]) == 0


def test_reports_tenant_isolation(client: TestClient, registered_gym, second_registered_gym):
    """Verify Gym 2 cannot view reports containing Gym 1 data."""
    headers1 = registered_gym["headers"]
    headers2 = second_registered_gym["headers"]
    _seed_gym_data(client, headers1)

    today = date.today()
    resp2 = client.get(f"/api/v1/reports/revenue?start_date={today}&end_date={today}", headers=headers2)
    assert resp2.status_code == 200
    assert resp2.json()["summary"]["total_gross_paise"] == 0
    assert len(resp2.json()["transactions"]) == 0


def test_reports_rbac(client: TestClient, gym_with_roles):
    """
    Verify RBAC:
    - Financial reports (revenue, pending-dues) require OWNER or MANAGER (FRONT_DESK receives 403).
    - Operational reports (memberships, attendance, expiries) are accessible by FRONT_DESK.
    """
    mgr_headers = gym_with_roles["manager_headers"]
    desk_headers = gym_with_roles["front_desk_headers"]

    today = date.today()

    # Manager has access to revenue and dues
    assert client.get(f"/api/v1/reports/revenue?start_date={today}&end_date={today}", headers=mgr_headers).status_code == 200
    assert client.get("/api/v1/reports/pending-dues", headers=mgr_headers).status_code == 200

    # Front desk is forbidden from revenue and dues
    assert client.get(f"/api/v1/reports/revenue?start_date={today}&end_date={today}", headers=desk_headers).status_code == 403
    assert client.get("/api/v1/reports/pending-dues", headers=desk_headers).status_code == 403

    # Front desk can access operational reports
    assert client.get("/api/v1/reports/memberships", headers=desk_headers).status_code == 200
    assert client.get(f"/api/v1/reports/attendance?start_date={today}&end_date={today}", headers=desk_headers).status_code == 200
    assert client.get("/api/v1/reports/expiries", headers=desk_headers).status_code == 200

