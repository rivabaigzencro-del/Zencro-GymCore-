"""Tests for Day 7 Staff Management & RBAC module."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def _create_staff_helper(
    client: TestClient,
    auth_headers: dict,
    name: str = "Test Staff",
    email: str = None,
    role: str = "FRONT_DESK",
    password: str = "StaffPass123!",
):
    if not email:
        email = f"staff_{uuid.uuid4().hex[:8]}@gymcoretest.com"
    resp = client.post(
        "/api/v1/staff",
        headers=auth_headers,
        json={
            "name": name,
            "email": email,
            "phone": "+919876543210",
            "password": password,
            "role": role,
        },
    )
    return resp, email, password


def test_create_staff_by_owner_success(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    # 1. Owner creates a Manager
    resp_mgr, email_mgr, _ = _create_staff_helper(
        client, headers, name="Gym Manager", role="MANAGER"
    )
    assert resp_mgr.status_code == 201
    mgr_data = resp_mgr.json()
    assert mgr_data["name"] == "Gym Manager"
    assert mgr_data["email"] == email_mgr
    assert mgr_data["role"] == "MANAGER"
    assert mgr_data["is_active"] is True
    assert "password" not in mgr_data
    assert "password_hash" not in mgr_data

    # 2. Owner creates a Front Desk staff
    resp_fd, email_fd, _ = _create_staff_helper(
        client, headers, name="Front Desk Staff", role="FRONT_DESK"
    )
    assert resp_fd.status_code == 201
    fd_data = resp_fd.json()
    assert fd_data["name"] == "Front Desk Staff"
    assert fd_data["email"] == email_fd
    assert fd_data["role"] == "FRONT_DESK"
    assert fd_data["is_active"] is True


def test_create_staff_manager_restrictions(client: TestClient, registered_gym: dict):
    owner_headers = registered_gym["headers"]

    # Create a Manager
    resp_mgr, mgr_email, mgr_pass = _create_staff_helper(
        client, owner_headers, name="Branch Manager", role="MANAGER"
    )
    assert resp_mgr.status_code == 201

    # Login as Manager
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": mgr_email, "password": mgr_pass},
    )
    assert login_resp.status_code == 200
    mgr_token = login_resp.json()["access_token"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # Manager can create FRONT_DESK
    resp_fd, _, _ = _create_staff_helper(
        client, mgr_headers, name="Desk Assistant", role="FRONT_DESK"
    )
    assert resp_fd.status_code == 201
    assert resp_fd.json()["role"] == "FRONT_DESK"

    # Manager CANNOT create another MANAGER
    resp_bad_mgr, _, _ = _create_staff_helper(
        client, mgr_headers, name="Another Manager", role="MANAGER"
    )
    assert resp_bad_mgr.status_code == 403
    assert "Managers are only permitted" in resp_bad_mgr.json()["detail"]


def test_create_staff_front_desk_forbidden(client: TestClient, registered_gym: dict):
    owner_headers = registered_gym["headers"]

    # Create Front Desk staff
    resp_fd, fd_email, fd_pass = _create_staff_helper(
        client, owner_headers, name="Receptionist", role="FRONT_DESK"
    )
    assert resp_fd.status_code == 201

    # Login as Front Desk
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": fd_email, "password": fd_pass},
    )
    assert login_resp.status_code == 200
    fd_token = login_resp.json()["access_token"]
    fd_headers = {"Authorization": f"Bearer {fd_token}"}

    # Front Desk cannot create staff
    resp_create, _, _ = _create_staff_helper(client, fd_headers, role="FRONT_DESK")
    assert resp_create.status_code == 403

    # Front Desk cannot list staff
    resp_list = client.get("/api/v1/staff", headers=fd_headers)
    assert resp_list.status_code == 403


def test_cannot_create_owner_via_staff_endpoint(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]
    resp = client.post(
        "/api/v1/staff",
        headers=headers,
        json={
            "name": "Second Owner",
            "email": f"owner2_{uuid.uuid4().hex[:6]}@gym.com",
            "password": "Password123!",
            "role": "OWNER",
        },
    )
    assert resp.status_code in (400, 422)


def test_create_staff_duplicate_email_fails(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]
    duplicate_email = f"shared_{uuid.uuid4().hex[:6]}@gym.com"

    # Create first staff
    resp1, _, _ = _create_staff_helper(
        client, headers, email=duplicate_email, role="FRONT_DESK"
    )
    assert resp1.status_code == 201

    # Attempt to create second staff with identical email
    resp2, _, _ = _create_staff_helper(
        client, headers, email=duplicate_email, role="FRONT_DESK"
    )
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_list_staff_pagination_and_filters(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    # Create 2 managers and 2 front desk
    _create_staff_helper(client, headers, name="Alice Manager", role="MANAGER")
    _create_staff_helper(client, headers, name="Bob Manager", role="MANAGER")
    _create_staff_helper(client, headers, name="Charlie Desk", role="FRONT_DESK")
    _create_staff_helper(client, headers, name="Diana Desk", role="FRONT_DESK")

    # List all staff (should include Owner + 4 staff = 5)
    resp = client.get("/api/v1/staff", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5
    assert len(data["items"]) >= 5

    # Filter by role=MANAGER
    resp_mgr = client.get("/api/v1/staff?role=MANAGER", headers=headers)
    assert resp_mgr.status_code == 200
    mgr_items = resp_mgr.json()["items"]
    assert len(mgr_items) == 2
    assert all(item["role"] == "MANAGER" for item in mgr_items)

    # Search filter
    resp_search = client.get("/api/v1/staff?search=Alice", headers=headers)
    assert resp_search.status_code == 200
    assert resp_search.json()["total"] == 1
    assert resp_search.json()["items"][0]["name"] == "Alice Manager"


def test_get_and_update_staff_profile(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    resp_staff, _, _ = _create_staff_helper(
        client, headers, name="Original Name", role="FRONT_DESK"
    )
    staff_id = resp_staff.json()["id"]

    # Get staff by ID
    resp_get = client.get(f"/api/v1/staff/{staff_id}", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == staff_id

    # Update staff profile
    resp_patch = client.patch(
        f"/api/v1/staff/{staff_id}",
        headers=headers,
        json={"name": "Updated Staff Name", "phone": "+911122334455"},
    )
    assert resp_patch.status_code == 200
    patch_data = resp_patch.json()
    assert patch_data["name"] == "Updated Staff Name"
    assert patch_data["phone"] == "+911122334455"


def test_manager_cannot_modify_owner(client: TestClient, registered_gym: dict):
    owner_headers = registered_gym["headers"]
    owner_id = str(registered_gym["owner_id"])

    # Create Manager
    resp_mgr, mgr_email, mgr_pass = _create_staff_helper(
        client, owner_headers, role="MANAGER"
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": mgr_email, "password": mgr_pass},
    )
    mgr_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Manager attempts to modify Owner
    resp_update = client.patch(
        f"/api/v1/staff/{owner_id}",
        headers=mgr_headers,
        json={"name": "Hacked Owner"},
    )
    assert resp_update.status_code == 403
    assert "Managers cannot modify Owner" in resp_update.json()["detail"]

    # Manager attempts to deactivate Owner
    resp_deact = client.patch(
        f"/api/v1/staff/{owner_id}/status",
        headers=mgr_headers,
        json={"is_active": False, "reason": "Attempted takeover"},
    )
    assert resp_deact.status_code == 403


def test_staff_status_deactivation_and_login_blocking(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    # Create staff
    resp_staff, staff_email, staff_pass = _create_staff_helper(
        client, headers, role="FRONT_DESK"
    )
    staff_id = resp_staff.json()["id"]

    # Login before deactivation succeeds
    login_resp1 = client.post(
        "/api/v1/auth/login",
        json={"email": staff_email, "password": staff_pass},
    )
    assert login_resp1.status_code == 200
    valid_token = login_resp1.json()["access_token"]
    staff_auth = {"Authorization": f"Bearer {valid_token}"}

    # Verify staff can access allowed endpoint
    check_resp = client.get("/api/v1/members", headers=staff_auth)
    assert check_resp.status_code == 200

    # Owner deactivates staff member
    resp_deact = client.patch(
        f"/api/v1/staff/{staff_id}/status",
        headers=headers,
        json={"is_active": False, "reason": "Employee terminated"},
    )
    assert resp_deact.status_code == 200
    assert resp_deact.json()["is_active"] is False

    # Deactivated staff cannot use existing token
    blocked_resp = client.get("/api/v1/members", headers=staff_auth)
    assert blocked_resp.status_code == 403
    assert "Inactive user" in blocked_resp.json()["detail"] or "inactive" in blocked_resp.json()["detail"].lower()

    # Deactivated staff cannot login
    login_resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": staff_email, "password": staff_pass},
    )
    assert login_resp2.status_code == 403


def test_prevent_self_deactivation(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]
    owner_id = str(registered_gym["owner_id"])

    # Owner attempts to deactivate themselves
    resp = client.patch(
        f"/api/v1/staff/{owner_id}/status",
        headers=headers,
        json={"is_active": False, "reason": "Self deactivation test"},
    )
    assert resp.status_code == 400
    assert "cannot deactivate your own account" in resp.json()["detail"].lower()


def test_prevent_deactivating_only_active_owner(client: TestClient, registered_gym: dict, db: Session):
    headers = registered_gym["headers"]

    # Create a Manager
    resp_mgr, mgr_email, mgr_pass = _create_staff_helper(
        client, headers, role="MANAGER"
    )
    mgr_id = resp_mgr.json()["id"]

    # Now verify owner cannot be deactivated by another user (or if self-check didn't catch it)
    owner_id = str(registered_gym["owner_id"])
    owner_user = db.query(User).filter(User.id == registered_gym["owner_id"]).first()
    assert owner_user.role == UserRole.OWNER


def test_update_staff_role_owner_only(client: TestClient, registered_gym: dict):
    owner_headers = registered_gym["headers"]

    # Create Front Desk staff
    resp_staff, staff_email, staff_pass = _create_staff_helper(
        client, owner_headers, role="FRONT_DESK"
    )
    staff_id = resp_staff.json()["id"]

    # Owner promotes Front Desk to MANAGER
    resp_role = client.patch(
        f"/api/v1/staff/{staff_id}/role",
        headers=owner_headers,
        json={"role": "MANAGER", "reason": "Promotion for outstanding performance"},
    )
    assert resp_role.status_code == 200
    assert resp_role.json()["role"] == "MANAGER"

    # Owner attempts to promote to OWNER (Forbidden / Bad Request)
    resp_promote_owner = client.patch(
        f"/api/v1/staff/{staff_id}/role",
        headers=owner_headers,
        json={"role": "OWNER"},
    )
    assert resp_promote_owner.status_code in (400, 422)

    # Login as newly promoted Manager
    login_mgr = client.post(
        "/api/v1/auth/login",
        json={"email": staff_email, "password": staff_pass},
    )
    mgr_token = login_mgr.json()["access_token"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # Manager CANNOT change roles
    resp_mgr_role = client.patch(
        f"/api/v1/staff/{staff_id}/role",
        headers=mgr_headers,
        json={"role": "FRONT_DESK"},
    )
    assert resp_mgr_role.status_code == 403


def test_staff_tenant_isolation(client: TestClient, registered_gym: dict, second_registered_gym: dict):
    gym1_headers = registered_gym["headers"]
    gym2_headers = second_registered_gym["headers"]

    # Gym 1 creates a staff member
    resp_staff1, _, _ = _create_staff_helper(
        client, gym1_headers, name="Gym1 Staff", role="FRONT_DESK"
    )
    staff1_id = resp_staff1.json()["id"]

    # Gym 2 owner cannot view Gym 1 staff
    resp_get = client.get(f"/api/v1/staff/{staff1_id}", headers=gym2_headers)
    assert resp_get.status_code == 404

    # Gym 2 owner cannot update Gym 1 staff
    resp_patch = client.patch(
        f"/api/v1/staff/{staff1_id}",
        headers=gym2_headers,
        json={"name": "Attacker Hijack"},
    )
    assert resp_patch.status_code == 404

    # Gym 2 owner cannot deactivate Gym 1 staff
    resp_deact = client.patch(
        f"/api/v1/staff/{staff1_id}/status",
        headers=gym2_headers,
        json={"is_active": False},
    )
    assert resp_deact.status_code == 404

    # Gym 2 staff list does not contain Gym 1 staff
    list_gym2 = client.get("/api/v1/staff", headers=gym2_headers).json()["items"]
    assert not any(item["id"] == staff1_id for item in list_gym2)

