"""Automated tests for Day 4 Attendance, QR check-in, Overrides, Check-out, and Analytics."""
import random
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient


def _create_active_member(client: TestClient, headers: dict) -> tuple[dict, dict]:
    """Helper to create a member with an active monthly membership."""
    suffix = uuid.uuid4().hex[:6]
    rand_phone = f"+9198{random.randint(10000000, 99999999)}"
    m_resp = client.post(
        "/api/v1/members",
        json={"full_name": f"Attendee {suffix}", "phone": rand_phone},
        headers=headers,
    )
    assert m_resp.status_code == 201, f"Member creation failed: {m_resp.status_code} - {m_resp.text}"
    member = m_resp.json()

    p_resp = client.post(
        "/api/v1/membership-plans",
        json={"name": f"Monthly {suffix}", "duration": 1, "duration_unit": "MONTHS", "price": 2000.00},
        headers=headers,
    )
    assert p_resp.status_code == 201
    plan = p_resp.json()

    ms_resp = client.post(
        "/api/v1/memberships",
        json={
            "member_id": member["id"],
            "membership_plan_id": plan["id"],
            "start_date": (date.today() - timedelta(days=2)).isoformat(),
        },
        headers=headers,
    )
    assert ms_resp.status_code == 201
    membership = ms_resp.json()

    return member, membership


def test_manual_check_in_active_membership(client: TestClient, registered_gym):
    """Test standard receptionist manual check-in for an eligible member."""
    member, _ = _create_active_member(client, registered_gym["headers"])

    resp = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    )
    assert resp.status_code == 201, f"Failed: {resp.text}"
    data = resp.json()

    assert data["member_id"] == member["id"]
    assert data["tenant_id"] == str(registered_gym["tenant_id"])
    assert data["check_in_method"] == "MANUAL"
    assert data["check_out_time"] is None
    assert data["is_active"] is True
    assert data["is_override"] is False
    assert data["checked_in_by_id"] == str(registered_gym["owner_id"])


def test_prevent_duplicate_active_check_in(client: TestClient, registered_gym):
    """A member who is currently checked in cannot check in again without checking out."""
    member, _ = _create_active_member(client, registered_gym["headers"])

    # First check-in
    r1 = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    )
    assert r1.status_code == 201

    # Second check-in attempt must fail with 409 Conflict
    r2 = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    )
    assert r2.status_code == 409
    assert "already checked in" in r2.json()["detail"].lower()


def test_check_out_and_re_check_in(client: TestClient, registered_gym):
    """After checking out of an active visit, the member can check in again."""
    member, _ = _create_active_member(client, registered_gym["headers"])

    # Check in
    r_in = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    )
    assert r_in.status_code == 201
    visit = r_in.json()

    # Check out via member check-out endpoint
    r_out = client.post(
        f"/api/v1/attendance/members/{member['id']}/check-out",
        headers=registered_gym["headers"],
    )
    assert r_out.status_code == 200
    checked_out = r_out.json()
    assert checked_out["check_out_time"] is not None
    assert checked_out["is_active"] is False

    # Second visit check-in must now succeed
    r_re_in = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    )
    assert r_re_in.status_code == 201


def test_cannot_check_out_already_checked_out_visit(client: TestClient, registered_gym):
    """Attempting to check out an already completed visit returns 400 Bad Request."""
    member, _ = _create_active_member(client, registered_gym["headers"])

    r_in = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    ).json()

    # First check-out
    client.post(f"/api/v1/attendance/{r_in['id']}/check-out", headers=registered_gym["headers"])

    # Repeat check-out
    r_repeat = client.post(f"/api/v1/attendance/{r_in['id']}/check-out", headers=registered_gym["headers"])
    assert r_repeat.status_code == 400
    assert "already checked out" in r_repeat.json()["detail"].lower()


def test_membership_eligibility_scenarios(client: TestClient, registered_gym):
    """Centralized eligibility engine accurately identifies expired, frozen, future, and missing memberships."""
    headers = registered_gym["headers"]

    # 1. Member with NO membership
    m_none = client.post("/api/v1/members", json={"full_name": "No Sub Member"}, headers=headers).json()
    e_none = client.get(f"/api/v1/attendance/eligibility/{m_none['id']}", headers=headers).json()
    assert e_none["eligible"] is False
    assert e_none["membership_status"] == "NONE"

    # Attempting to check in without override must fail with 400
    r_none_in = client.post("/api/v1/attendance/check-in", json={"member_id": m_none["id"]}, headers=headers)
    assert r_none_in.status_code == 400

    # 2. Member with FROZEN membership
    m_frz, ms_frz = _create_active_member(client, headers)
    # Freeze it
    client.post(
        f"/api/v1/memberships/{ms_frz['id']}/freeze",
        json={
            "freeze_start_date": date.today().isoformat(),
            "freeze_end_date": (date.today() + timedelta(days=10)).isoformat(),
        },
        headers=headers,
    )
    e_frz = client.get(f"/api/v1/attendance/eligibility/{m_frz['id']}", headers=headers).json()
    assert e_frz["eligible"] is False
    assert e_frz["membership_status"] == "FROZEN"

    # 3. Member with FUTURE membership
    m_fut = client.post("/api/v1/members", json={"full_name": "Future Member"}, headers=headers).json()
    p_resp = client.post(
        "/api/v1/membership-plans",
        json={"name": "Fut Plan", "duration": 1, "duration_unit": "MONTHS", "price": 1000.0},
        headers=headers,
    ).json()
    client.post(
        "/api/v1/memberships",
        json={
            "member_id": m_fut["id"],
            "membership_plan_id": p_resp["id"],
            "start_date": (date.today() + timedelta(days=5)).isoformat(),
        },
        headers=headers,
    )
    e_fut = client.get(f"/api/v1/attendance/eligibility/{m_fut['id']}", headers=headers).json()
    assert e_fut["eligible"] is False
    assert e_fut["membership_status"] == "FUTURE"


def test_authorized_check_in_override(client: TestClient, registered_gym):
    """An ineligible member can be checked in by OWNER/MANAGER with override=True and mandatory reason."""
    headers = registered_gym["headers"]
    member = client.post("/api/v1/members", json={"full_name": "Override Member"}, headers=headers).json()

    # Attempt override WITHOUT reason -> 400 Bad Request
    r_no_reason = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"], "override": True, "override_reason": ""},
        headers=headers,
    )
    assert r_no_reason.status_code == 400
    assert "mandatory override reason" in r_no_reason.json()["detail"].lower()

    # Valid override by OWNER
    r_override = client.post(
        "/api/v1/attendance/check-in",
        json={
            "member_id": member["id"],
            "override": True,
            "override_reason": "Owner VIP trial day pass",
        },
        headers=headers,
    )
    assert r_override.status_code == 201
    data = r_override.json()
    assert data["is_override"] is True
    assert data["override_reason"] == "Owner VIP trial day pass"
    assert data["override_by_id"] == str(registered_gym["owner_id"])


def test_rbac_check_in_override_restricted_to_owner_manager(client: TestClient, gym_with_roles):
    """FRONT_DESK cannot grant check-in overrides (403 Forbidden). MANAGER and OWNER can."""
    headers = gym_with_roles["headers"]
    member = client.post("/api/v1/members", json={"full_name": "RBAC Member"}, headers=headers).json()

    # FRONT_DESK attempt -> 403 Forbidden
    r_fd = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"], "override": True, "override_reason": "Desk approval"},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert r_fd.status_code == 403

    # MANAGER attempt -> 201 Created
    r_mgr = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"], "override": True, "override_reason": "Manager approved trial"},
        headers=gym_with_roles["manager_headers"],
    )
    assert r_mgr.status_code == 201
    assert r_mgr.json()["is_override"] is True


def test_qr_check_in_workflow(client: TestClient, registered_gym, second_registered_gym):
    """Test retrieving member QR code, validating QR check-in, token invalidation, and cross-tenant protection."""
    member, _ = _create_active_member(client, registered_gym["headers"])

    # 1. Retrieve QR token
    qr_resp = client.get(
        f"/api/v1/attendance/members/{member['id']}/qr",
        headers=registered_gym["headers"],
    )
    assert qr_resp.status_code == 200
    qr_data = qr_resp.json()
    qr_token = qr_data["qr_code"]
    assert qr_token.startswith("GYM_")

    # 2. Check in using valid QR code
    checkin_resp = client.post(
        "/api/v1/attendance/qr-check-in",
        json={"qr_code": qr_token},
        headers=registered_gym["headers"],
    )
    assert checkin_resp.status_code == 201
    att = checkin_resp.json()
    assert att["check_in_method"] == "QR"
    assert att["member_id"] == member["id"]

    # Check out
    client.post(f"/api/v1/attendance/{att['id']}/check-out", headers=registered_gym["headers"])

    # 3. Cross-tenant check: Second gym tries to use Gym 1's QR code -> 404 Not Found
    cross_resp = client.post(
        "/api/v1/attendance/qr-check-in",
        json={"qr_code": qr_token},
        headers=second_registered_gym["headers"],
    )
    assert cross_resp.status_code == 404

    # 4. Regenerate QR code
    regen_resp = client.post(
        f"/api/v1/attendance/members/{member['id']}/qr/regenerate",
        headers=registered_gym["headers"],
    )
    assert regen_resp.status_code == 200
    new_qr = regen_resp.json()["qr_code"]
    assert new_qr != qr_token

    # Old QR code now fails
    r_old = client.post(
        "/api/v1/attendance/qr-check-in",
        json={"qr_code": qr_token},
        headers=registered_gym["headers"],
    )
    assert r_old.status_code == 404

    # New QR code succeeds
    r_new = client.post(
        "/api/v1/attendance/qr-check-in",
        json={"qr_code": new_qr},
        headers=registered_gym["headers"],
    )
    assert r_new.status_code == 201


def test_outstanding_dues_policy(client: TestClient, registered_gym):
    """Test attendance dues policy warning and blocking behavior."""
    headers = registered_gym["headers"]
    member, _ = _create_active_member(client, headers)

    # Create unpaid invoice of ₹1,500
    client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 150000},
        headers=headers,
    )

    # 1. Under default policy (block_dues = False): check-in is allowed with dues warning
    e1 = client.get(f"/api/v1/attendance/eligibility/{member['id']}", headers=headers).json()
    assert e1["eligible"] is True
    assert e1["has_outstanding_dues"] is True
    assert e1["outstanding_dues_paise"] == 150000

    r_in = client.post("/api/v1/attendance/check-in", json={"member_id": member["id"]}, headers=headers)
    assert r_in.status_code == 201
    client.post(f"/api/v1/attendance/members/{member['id']}/check-out", headers=headers)

    # 2. Update policy to block_on_dues = True
    p_update = client.patch(
        "/api/v1/attendance/settings",
        json={"attendance_block_on_dues": True},
        headers=headers,
    )
    assert p_update.status_code == 200

    # Check eligibility now blocked
    e2 = client.get(f"/api/v1/attendance/eligibility/{member['id']}", headers=headers).json()
    assert e2["eligible"] is False
    assert "overdue" in e2["warning"].lower()

    # Check-in without override now rejected
    r_blocked = client.post("/api/v1/attendance/check-in", json={"member_id": member["id"]}, headers=headers)
    assert r_blocked.status_code == 400


def test_receptionist_member_search(client: TestClient, registered_gym):
    """Fast receptionist search by name and phone returns member check-in states."""
    headers = registered_gym["headers"]
    member, _ = _create_active_member(client, headers)

    # Search by partial name
    q_name = member["full_name"][:5]
    res_name = client.get(f"/api/v1/attendance/search-members?q={q_name}", headers=headers)
    assert res_name.status_code == 200
    items = res_name.json()
    assert len(items) >= 1
    found = next((i for i in items if i["member_id"] == member["id"]), None)
    assert found is not None
    assert found["is_currently_checked_in"] is False

    # Check member in
    client.post("/api/v1/attendance/check-in", json={"member_id": member["id"]}, headers=headers)

    # Search again: now shows checked in
    res_checked = client.get(f"/api/v1/attendance/search-members?q={q_name}", headers=headers).json()
    found_after = next((i for i in res_checked if i["member_id"] == member["id"]), None)
    assert found_after["is_currently_checked_in"] is True
    assert found_after["active_attendance_id"] is not None


def test_today_attendance_and_history(client: TestClient, registered_gym):
    """Today's attendance list and individual member history endpoints."""
    headers = registered_gym["headers"]
    member, _ = _create_active_member(client, headers)

    # Check in
    att = client.post("/api/v1/attendance/check-in", json={"member_id": member["id"]}, headers=headers).json()

    # GET /attendance/today
    today_resp = client.get("/api/v1/attendance/today", headers=headers)
    assert today_resp.status_code == 200
    t_data = today_resp.json()
    assert t_data["total"] >= 1
    assert any(item["id"] == att["id"] for item in t_data["items"])

    # GET /attendance/members/{member_id}
    hist_resp = client.get(f"/api/v1/attendance/members/{member['id']}", headers=headers)
    assert hist_resp.status_code == 200
    h_data = hist_resp.json()
    assert h_data["total"] == 1
    assert h_data["items"][0]["member_id"] == member["id"]


def test_attendance_analytics(client: TestClient, registered_gym):
    """Daily summary, peak-hours distribution, and member frequency analytics."""
    headers = registered_gym["headers"]
    m1, _ = _create_active_member(client, headers)
    m2, _ = _create_active_member(client, headers)

    # m1 visit
    a1 = client.post("/api/v1/attendance/check-in", json={"member_id": m1["id"]}, headers=headers).json()
    client.post(f"/api/v1/attendance/{a1['id']}/check-out", headers=headers)

    # m2 visit (active)
    client.post("/api/v1/attendance/check-in", json={"member_id": m2["id"]}, headers=headers)

    # 1. Summary
    sum_resp = client.get("/api/v1/attendance/analytics/summary", headers=headers)
    assert sum_resp.status_code == 200
    s_data = sum_resp.json()
    assert s_data["total_check_ins"] == 2
    assert s_data["unique_members"] == 2
    assert s_data["active_check_ins"] == 1
    assert s_data["completed_visits"] == 1

    # 2. Peak Hours
    peak_resp = client.get("/api/v1/attendance/analytics/peak-hours", headers=headers)
    assert peak_resp.status_code == 200
    p_data = peak_resp.json()
    assert len(p_data["hourly_breakdown"]) == 24
    assert p_data["peak_hour_count"] >= 2

    # 3. Frequency
    freq_resp = client.get("/api/v1/attendance/analytics/frequency", headers=headers)
    assert freq_resp.status_code == 200
    f_data = freq_resp.json()
    assert f_data["total_visits"] == 2
    assert f_data["unique_members"] == 2
    assert len(f_data["top_members"]) >= 2


def test_tenant_isolation_attendance(client: TestClient, registered_gym, second_registered_gym):
    """Gym 2 cannot view Gym 1's attendance, check out Gym 1's member, or view analytics."""
    member, _ = _create_active_member(client, registered_gym["headers"])
    att = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to check out Gym 1's visit -> 404
    r_out = client.post(
        f"/api/v1/attendance/{att['id']}/check-out",
        headers=second_registered_gym["headers"],
    )
    assert r_out.status_code == 404

    # Gym 2 tries to view Gym 1's member history -> 404
    r_hist = client.get(
        f"/api/v1/attendance/members/{member['id']}",
        headers=second_registered_gym["headers"],
    )
    assert r_hist.status_code == 404

    # Gym 2's today list does NOT include Gym 1's visit
    g2_today = client.get("/api/v1/attendance/today", headers=second_registered_gym["headers"]).json()
    assert not any(i["id"] == att["id"] for i in g2_today["items"])


def test_rbac_attendance_endpoints(client: TestClient, gym_with_roles):
    """FRONT_DESK can check in/out and view today's list, but cannot view analytics or change settings."""
    member, _ = _create_active_member(client, gym_with_roles["headers"])

    # FRONT_DESK check in -> 201
    fd_in = client.post(
        "/api/v1/attendance/check-in",
        json={"member_id": member["id"]},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_in.status_code == 201

    # FRONT_DESK view today -> 200
    fd_today = client.get("/api/v1/attendance/today", headers=gym_with_roles["front_desk_headers"])
    assert fd_today.status_code == 200

    # FRONT_DESK view analytics -> 403 Forbidden
    fd_analytics = client.get("/api/v1/attendance/analytics/summary", headers=gym_with_roles["front_desk_headers"])
    assert fd_analytics.status_code == 403

    # FRONT_DESK update settings -> 403 Forbidden
    fd_settings = client.patch(
        "/api/v1/attendance/settings",
        json={"attendance_block_expired": False},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_settings.status_code == 403

    # MANAGER view analytics -> 200 OK
    mgr_analytics = client.get("/api/v1/attendance/analytics/summary", headers=gym_with_roles["manager_headers"])
    assert mgr_analytics.status_code == 200


def test_concurrent_check_in_protection(client: TestClient, registered_gym):
    """
    Concurrent simultaneous check-in attempts for the same member:
    Exactly 1 must succeed with 201 Created; all others must be rejected with 409 Conflict.
    """
    member, _ = _create_active_member(client, registered_gym["headers"])

    def attempt_checkin(_):
        return client.post(
            "/api/v1/attendance/check-in",
            json={"member_id": member["id"]},
            headers=registered_gym["headers"],
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(attempt_checkin, range(4)))

    successes = [r for r in results if r.status_code == 201]
    conflicts = [r for r in results if r.status_code == 409]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(conflicts) == 3, f"Expected 3 conflicts, got {len(conflicts)}"
