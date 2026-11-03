"""Comprehensive tests for Membership lifecycle operations."""
from datetime import date, timedelta
import uuid
from fastapi.testclient import TestClient


def _setup_member_and_plan(client: TestClient, headers: dict):
    """Helper to create a member and a plan for membership tests."""
    member_resp = client.post(
        "/api/v1/members",
        json={"full_name": f"Member {uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert member_resp.status_code == 201
    member = member_resp.json()

    plan_resp = client.post(
        "/api/v1/membership-plans",
        json={"name": "Monthly Standard", "duration": 1, "duration_unit": "MONTHS", "price": 2000.00},
        headers=headers,
    )
    assert plan_resp.status_code == 201
    plan = plan_resp.json()

    return member, plan


def test_assign_membership_and_expiry_calculation(client: TestClient, registered_gym):
    """Test assigning a membership plan to a member with auto-calculated expiry date."""
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])

    start_date = "2026-11-01"
    payload = {
        "member_id": member["id"],
        "membership_plan_id": plan["id"],
        "start_date": start_date,
        "notes": "New joiner discount applied",
    }
    resp = client.post("/api/v1/memberships", json=payload, headers=registered_gym["headers"])
    assert resp.status_code == 201, f"Failed: {resp.text}"
    data = resp.json()

    assert data["member_id"] == member["id"]
    assert data["membership_plan_id"] == plan["id"]
    assert data["start_date"] == start_date
    # 1 month starting 2026-11-01 ends 2026-11-30
    assert data["end_date"] == "2026-11-30"
    assert data["status"] == "ACTIVE"
    assert data["total_frozen_days"] == 0
    assert data["tenant_id"] == str(registered_gym["tenant_id"])

    # Verify member status is ACTIVE
    m_check = client.get(f"/api/v1/members/{member['id']}", headers=registered_gym["headers"]).json()
    assert m_check["status"] == "ACTIVE"


def test_prevent_overlapping_active_memberships(client: TestClient, registered_gym):
    """Attempting to assign a second active membership to an already active member must fail with 409."""
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])

    # First assignment
    r1 = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": "2026-11-01"},
        headers=registered_gym["headers"],
    )
    assert r1.status_code == 201

    # Second assignment attempt
    r2 = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": "2026-11-15"},
        headers=registered_gym["headers"],
    )
    assert r2.status_code == 409
    assert "already has an active or frozen membership" in r2.json()["detail"]


def test_cannot_assign_inactive_plan(client: TestClient, registered_gym):
    """Attempting to assign an inactive plan must be rejected with 400 Bad Request."""
    member, _ = _setup_member_and_plan(client, registered_gym["headers"])

    inactive_plan = client.post(
        "/api/v1/membership-plans",
        json={"name": "Discontinued", "duration": 1, "duration_unit": "MONTHS", "price": 500.00, "is_active": False},
        headers=registered_gym["headers"],
    ).json()

    resp = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": inactive_plan["id"], "start_date": "2026-11-01"},
        headers=registered_gym["headers"],
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


def test_freeze_and_unfreeze_membership_with_extension(client: TestClient, registered_gym):
    """
    Test freezing an active membership and unfreezing it.
    Validates that:
    1. Status becomes FROZEN during freeze.
    2. Status becomes ACTIVE after unfreeze.
    3. end_date is extended by the number of frozen days.
    4. total_frozen_days tracks the frozen period.
    """
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])

    # Start today for 1 month
    today = date.today()
    start_str = today.isoformat()

    ms = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": start_str},
        headers=registered_gym["headers"],
    ).json()

    initial_end = date.fromisoformat(ms["end_date"])

    # Freeze for 10 days starting today
    freeze_start = today
    freeze_end = today + timedelta(days=10)

    freeze_resp = client.post(
        f"/api/v1/memberships/{ms['id']}/freeze",
        json={"freeze_start_date": freeze_start.isoformat(), "freeze_end_date": freeze_end.isoformat()},
        headers=registered_gym["headers"],
    )
    assert freeze_resp.status_code == 200
    f_data = freeze_resp.json()
    assert f_data["status"] == "FROZEN"
    assert f_data["freeze_start_date"] == freeze_start.isoformat()
    assert f_data["freeze_end_date"] == freeze_end.isoformat()

    # Unfreeze specifying the unfreeze_date = freeze_end (10 days frozen)
    unfreeze_resp = client.post(
        f"/api/v1/memberships/{ms['id']}/unfreeze",
        json={"unfreeze_date": freeze_end.isoformat()},
        headers=registered_gym["headers"],
    )
    assert unfreeze_resp.status_code == 200
    u_data = unfreeze_resp.json()
    assert u_data["status"] == "ACTIVE"
    assert u_data["freeze_start_date"] is None
    assert u_data["freeze_end_date"] is None
    assert u_data["total_frozen_days"] == 10

    # Expiry must be extended by exactly 10 days
    expected_new_end = initial_end + timedelta(days=10)
    assert u_data["end_date"] == expected_new_end.isoformat()


def test_membership_renewal(client: TestClient, registered_gym):
    """
    Test membership renewal:
    - Old membership is marked CANCELLED.
    - New membership is created chained via renewed_from_id.
    - New membership starts day after old end_date by default.
    """
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])

    m1 = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": "2026-11-01"},
        headers=registered_gym["headers"],
    ).json()

    # Renew
    renew_resp = client.post(
        f"/api/v1/memberships/{m1['id']}/renew",
        json={"notes": "Renewed for next cycle"},
        headers=registered_gym["headers"],
    )
    assert renew_resp.status_code == 201
    m2 = renew_resp.json()

    assert m2["renewed_from_id"] == m1["id"]
    assert m2["start_date"] == "2026-12-01"  # Day after 2026-11-30
    assert m2["status"] == "ACTIVE"

    # Verify old membership is cancelled
    old_check = client.get(f"/api/v1/memberships/{m1['id']}", headers=registered_gym["headers"]).json()
    assert old_check["status"] == "CANCELLED"


def test_membership_upgrade(client: TestClient, registered_gym):
    """
    Test upgrading membership to a different plan:
    - Old membership marked CANCELLED.
    - New membership created with new plan and new end date.
    """
    member, plan1 = _setup_member_and_plan(client, registered_gym["headers"])

    # Create yearly premium plan
    plan2 = client.post(
        "/api/v1/membership-plans",
        json={"name": "Yearly Premium", "duration": 12, "duration_unit": "MONTHS", "price": 18000.00},
        headers=registered_gym["headers"],
    ).json()

    m1 = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan1["id"], "start_date": "2026-11-01"},
        headers=registered_gym["headers"],
    ).json()

    # Upgrade to Yearly
    upgrade_resp = client.post(
        f"/api/v1/memberships/{m1['id']}/upgrade",
        json={"new_membership_plan_id": plan2["id"], "effective_date": "2026-11-15", "notes": "Upgraded to yearly"},
        headers=registered_gym["headers"],
    )
    assert upgrade_resp.status_code == 201
    m2 = upgrade_resp.json()

    assert m2["membership_plan_id"] == plan2["id"]
    assert m2["start_date"] == "2026-11-15"
    assert m2["status"] == "ACTIVE"
    assert m2["renewed_from_id"] == m1["id"]

    # Upgrading to same plan must fail with 400
    same_plan_resp = client.post(
        f"/api/v1/memberships/{m2['id']}/upgrade",
        json={"new_membership_plan_id": plan2["id"]},
        headers=registered_gym["headers"],
    )
    assert same_plan_resp.status_code == 400


def test_cannot_deactivate_plan_with_active_memberships(client: TestClient, registered_gym):
    """A plan that currently has active memberships cannot be deactivated (409 Conflict)."""
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])

    # Assign active membership
    client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": "2026-11-01"},
        headers=registered_gym["headers"],
    )

    # Attempt to deactivate plan
    del_resp = client.delete(f"/api/v1/membership-plans/{plan['id']}", headers=registered_gym["headers"])
    assert del_resp.status_code == 409
    assert "active membership(s) use this plan" in del_resp.json()["detail"]


def test_tenant_isolation_memberships(client: TestClient, registered_gym, second_registered_gym):
    """Gym 2 cannot view, freeze, unfreeze, renew, or upgrade Gym 1's memberships."""
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])

    m1 = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": "2026-11-01"},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to access Gym 1's membership -> 404
    assert client.get(f"/api/v1/memberships/{m1['id']}", headers=second_registered_gym["headers"]).status_code == 404

    # Gym 2 tries to freeze Gym 1's membership -> 404
    assert client.post(
        f"/api/v1/memberships/{m1['id']}/freeze",
        json={"freeze_start_date": date.today().isoformat(), "freeze_end_date": (date.today() + timedelta(days=5)).isoformat()},
        headers=second_registered_gym["headers"],
    ).status_code == 404


def test_cross_tenant_member_or_plan_mismatch_rejected(client: TestClient, registered_gym, second_registered_gym):
    """Assigning a plan from gym 2 to a member from gym 1 must fail with 404."""
    member_gym1, _ = _setup_member_and_plan(client, registered_gym["headers"])
    _, plan_gym2 = _setup_member_and_plan(client, second_registered_gym["headers"])

    resp = client.post(
        "/api/v1/memberships",
        json={
            "member_id": member_gym1["id"],
            "membership_plan_id": plan_gym2["id"],
            "start_date": date.today().isoformat(),
        },
        headers=registered_gym["headers"],
    )
    assert resp.status_code == 404
    assert "plan not found" in resp.json()["detail"].lower()


def test_invalid_freeze_and_unfreeze_dates(client: TestClient, registered_gym):
    """Boundary conditions for freeze and unfreeze dates must be strictly enforced."""
    member, plan = _setup_member_and_plan(client, registered_gym["headers"])
    today = date.today()

    ms = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": today.isoformat()},
        headers=registered_gym["headers"],
    ).json()

    # 1. Freeze in the past -> 400
    past_freeze = client.post(
        f"/api/v1/memberships/{ms['id']}/freeze",
        json={
            "freeze_start_date": (today - timedelta(days=2)).isoformat(),
            "freeze_end_date": (today + timedelta(days=5)).isoformat(),
        },
        headers=registered_gym["headers"],
    )
    assert past_freeze.status_code == 400
    assert "past" in past_freeze.json()["detail"].lower()

    # 2. Freeze in the future -> 400
    future_freeze = client.post(
        f"/api/v1/memberships/{ms['id']}/freeze",
        json={
            "freeze_start_date": (today + timedelta(days=3)).isoformat(),
            "freeze_end_date": (today + timedelta(days=10)).isoformat(),
        },
        headers=registered_gym["headers"],
    )
    assert future_freeze.status_code == 400
    assert "future" in future_freeze.json()["detail"].lower()

    # 3. Legitimate immediate freeze
    freeze_resp = client.post(
        f"/api/v1/memberships/{ms['id']}/freeze",
        json={
            "freeze_start_date": today.isoformat(),
            "freeze_end_date": (today + timedelta(days=7)).isoformat(),
        },
        headers=registered_gym["headers"],
    )
    assert freeze_resp.status_code == 200

    # 4. Unfreeze with date after membership end_date -> 400
    future_unfreeze = client.post(
        f"/api/v1/memberships/{ms['id']}/unfreeze",
        json={"unfreeze_date": (today + timedelta(days=60)).isoformat()},
        headers=registered_gym["headers"],
    )
    assert future_unfreeze.status_code == 400
    assert "exceed" in future_unfreeze.json()["detail"].lower()

    # 5. Unfreeze with date before freeze_start -> 400
    past_unfreeze = client.post(
        f"/api/v1/memberships/{ms['id']}/unfreeze",
        json={"unfreeze_date": (today - timedelta(days=1)).isoformat()},
        headers=registered_gym["headers"],
    )
    assert past_unfreeze.status_code == 400
    assert "precede" in past_unfreeze.json()["detail"].lower()


def test_cannot_upgrade_frozen_membership_until_unfrozen(client: TestClient, registered_gym):
    """A frozen membership cannot be upgraded until unfrozen (policy protection)."""
    member, plan1 = _setup_member_and_plan(client, registered_gym["headers"])
    today = date.today()

    plan2 = client.post(
        "/api/v1/membership-plans",
        json={"name": "Yearly Plan", "duration": 12, "duration_unit": "MONTHS", "price": 18000.00},
        headers=registered_gym["headers"],
    ).json()

    ms = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan1["id"], "start_date": today.isoformat()},
        headers=registered_gym["headers"],
    ).json()

    # Freeze the membership
    client.post(
        f"/api/v1/memberships/{ms['id']}/freeze",
        json={"freeze_start_date": today.isoformat(), "freeze_end_date": (today + timedelta(days=5)).isoformat()},
        headers=registered_gym["headers"],
    )

    # Attempt upgrade while frozen -> 400
    upgrade_resp = client.post(
        f"/api/v1/memberships/{ms['id']}/upgrade",
        json={"new_membership_plan_id": plan2["id"]},
        headers=registered_gym["headers"],
    )
    assert upgrade_resp.status_code == 400
    assert "unfreeze the membership before upgrading" in upgrade_resp.json()["detail"].lower()


def test_rbac_memberships_operations(client: TestClient, gym_with_roles):
    """
    Test that FRONT_DESK can perform standard membership operations
    (create, view, freeze, unfreeze, renew, upgrade).
    """
    headers = gym_with_roles["front_desk_headers"]
    today = date.today()

    member, plan = _setup_member_and_plan(client, gym_with_roles["headers"])

    # Create membership as FRONT_DESK
    ms_resp = client.post(
        "/api/v1/memberships",
        json={"member_id": member["id"], "membership_plan_id": plan["id"], "start_date": today.isoformat()},
        headers=headers,
    )
    assert ms_resp.status_code == 201
    ms_id = ms_resp.json()["id"]

    # View list and detail as FRONT_DESK
    assert client.get("/api/v1/memberships", headers=headers).status_code == 200
    assert client.get(f"/api/v1/memberships/{ms_id}", headers=headers).status_code == 200

    # Freeze as FRONT_DESK
    freeze_resp = client.post(
        f"/api/v1/memberships/{ms_id}/freeze",
        json={"freeze_start_date": today.isoformat(), "freeze_end_date": (today + timedelta(days=5)).isoformat()},
        headers=headers,
    )
    assert freeze_resp.status_code == 200

    # Unfreeze as FRONT_DESK
    unfreeze_resp = client.post(
        f"/api/v1/memberships/{ms_id}/unfreeze",
        json={"unfreeze_date": today.isoformat()},
        headers=headers,
    )
    assert unfreeze_resp.status_code == 200

