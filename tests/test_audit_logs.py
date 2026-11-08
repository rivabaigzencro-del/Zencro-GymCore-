"""Tests for Day 7 Audit Logging & Append-Only Trail."""
import uuid
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.membership_plan import DurationUnit
from app.services.audit_service import sanitize_payload


def test_sanitize_payload_masks_sensitive_data():
    raw_data = {
        "user_id": str(uuid.uuid4()),
        "password": "SuperSecretPassword123!",
        "password_hash": "$2b$12$somehashedpasswordstring",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "secret_key": "my-secret-value",
        "nested": {
            "new_password": "NewSecretPassword!",
            "public_field": "visible_info",
        },
        "list_items": [
            {"token": "secret_token"},
            {"item_name": "clean_item"},
        ],
    }

    sanitized = sanitize_payload(raw_data)

    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["password_hash"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["secret_key"] == "[REDACTED]"
    assert sanitized["nested"]["new_password"] == "[REDACTED]"
    assert sanitized["nested"]["public_field"] == "visible_info"
    assert sanitized["list_items"][0]["token"] == "[REDACTED]"
    assert sanitized["list_items"][1]["item_name"] == "clean_item"


def test_staff_operations_generate_audit_logs(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]
    owner_id = str(registered_gym["owner_id"])

    # 1. Create a staff member
    resp_staff = client.post(
        "/api/v1/staff",
        headers=headers,
        json={
            "name": "Audit Test Staff",
            "email": f"audit_staff_{uuid.uuid4().hex[:6]}@gym.com",
            "phone": "+919876543211",
            "password": "Password123!",
            "role": "FRONT_DESK",
        },
    )
    assert resp_staff.status_code == 201
    staff_id = resp_staff.json()["id"]

    # Verify STAFF_CREATE audit log
    resp_logs = client.get(
        f"/api/v1/audit-logs?action=STAFF_CREATE&resource_id={staff_id}",
        headers=headers,
    )
    assert resp_logs.status_code == 200
    logs = resp_logs.json()["items"]
    assert len(logs) == 1
    create_log = logs[0]
    assert create_log["action"] == "STAFF_CREATE"
    assert create_log["resource_type"] == "USER"
    assert create_log["user_id"] == owner_id
    assert create_log["after_values"]["name"] == "Audit Test Staff"
    assert "password" not in create_log["after_values"]
    assert "password_hash" not in create_log["after_values"]

    # 2. Update staff profile
    resp_update = client.patch(
        f"/api/v1/staff/{staff_id}",
        headers=headers,
        json={"name": "Updated Audit Staff"},
    )
    assert resp_update.status_code == 200

    # Verify STAFF_UPDATE audit log
    resp_up_logs = client.get(
        f"/api/v1/audit-logs?action=STAFF_UPDATE&resource_id={staff_id}",
        headers=headers,
    )
    assert resp_up_logs.status_code == 200
    assert len(resp_up_logs.json()["items"]) == 1
    update_log = resp_up_logs.json()["items"][0]
    assert update_log["before_values"]["name"] == "Audit Test Staff"
    assert update_log["after_values"]["name"] == "Updated Audit Staff"

    # 3. Status change
    resp_status = client.patch(
        f"/api/v1/staff/{staff_id}/status",
        headers=headers,
        json={"is_active": False, "reason": "Staff leave of absence"},
    )
    assert resp_status.status_code == 200

    resp_st_logs = client.get(
        f"/api/v1/audit-logs?action=STAFF_STATUS_CHANGE&resource_id={staff_id}",
        headers=headers,
    )
    assert resp_st_logs.status_code == 200
    st_log = resp_st_logs.json()["items"][0]
    assert st_log["before_values"]["is_active"] is True
    assert st_log["after_values"]["is_active"] is False
    assert st_log["reason"] == "Staff leave of absence"

    # 4. Role change
    resp_role = client.patch(
        f"/api/v1/staff/{staff_id}/role",
        headers=headers,
        json={"role": "MANAGER", "reason": "Promoted to supervisor"},
    )
    assert resp_role.status_code == 200

    resp_role_logs = client.get(
        f"/api/v1/audit-logs?action=STAFF_ROLE_CHANGE&resource_id={staff_id}",
        headers=headers,
    )
    assert resp_role_logs.status_code == 200
    r_log = resp_role_logs.json()["items"][0]
    assert r_log["before_values"]["role"] == "FRONT_DESK"
    assert r_log["after_values"]["role"] == "MANAGER"
    assert r_log["reason"] == "Promoted to supervisor"


def test_member_and_financial_audit_logs(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    # Create Member
    resp_member = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "full_name": "Audit Member",
            "phone": "+919876543999",
            "gender": "MALE",
        },
    )
    assert resp_member.status_code == 201
    member_id = resp_member.json()["id"]

    # Update Member -> logs MEMBER_UPDATE
    client.put(
        f"/api/v1/members/{member_id}",
        headers=headers,
        json={"full_name": "Audit Member Updated", "phone": "+919876543999", "gender": "MALE"},
    )
    resp_m_logs = client.get(
        f"/api/v1/audit-logs?action=MEMBER_UPDATE&resource_id={member_id}",
        headers=headers,
    )
    assert resp_m_logs.status_code == 200
    assert len(resp_m_logs.json()["items"]) == 1

    # Create Invoice -> logs INVOICE_CREATE
    resp_inv = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={
            "member_id": member_id,
            "amount_paise": 500000,
            "description": "Monthly gym invoice",
        },
    )
    assert resp_inv.status_code == 201
    inv_id = resp_inv.json()["id"]

    resp_inv_logs = client.get(
        f"/api/v1/audit-logs?action=INVOICE_CREATE&resource_id={inv_id}",
        headers=headers,
    )
    assert resp_inv_logs.status_code == 200
    assert len(resp_inv_logs.json()["items"]) == 1

    # Record Payment -> logs PAYMENT_CREATE
    resp_pay = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "member_id": member_id,
            "invoice_id": inv_id,
            "amount_paise": 500000,
            "payment_method": "UPI",
            "auto_generate_receipt": True,
        },
    )
    assert resp_pay.status_code == 201
    pay_id = resp_pay.json()["id"]

    resp_pay_logs = client.get(
        f"/api/v1/audit-logs?action=PAYMENT_CREATE&resource_id={pay_id}",
        headers=headers,
    )
    assert resp_pay_logs.status_code == 200
    assert len(resp_pay_logs.json()["items"]) == 1


def test_list_audit_logs_filters_and_pagination(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    # Query all logs
    resp_all = client.get("/api/v1/audit-logs?page=1&page_size=5", headers=headers)
    assert resp_all.status_code == 200
    data = resp_all.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5

    # Filter by date
    today_str = date.today().isoformat()
    resp_date = client.get(f"/api/v1/audit-logs?start_date={today_str}&end_date={today_str}", headers=headers)
    assert resp_date.status_code == 200


def test_get_audit_log_detail(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]

    # Create staff to trigger an audit log
    client.post(
        "/api/v1/staff",
        headers=headers,
        json={
            "name": "Audit Detail Staff",
            "email": f"detail_{uuid.uuid4().hex[:6]}@gym.com",
            "password": "Password123!",
            "role": "FRONT_DESK",
        },
    )

    list_resp = client.get("/api/v1/audit-logs?page=1&page_size=1", headers=headers)
    assert list_resp.status_code == 200
    first_log = list_resp.json()["items"][0]
    log_id = first_log["id"]

    # Fetch log by ID
    get_resp = client.get(f"/api/v1/audit-logs/{log_id}", headers=headers)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == log_id
    assert detail["action"] == first_log["action"]
    assert "actor_name" in detail

    # Fetch non-existent log
    fake_id = str(uuid.uuid4())
    fake_resp = client.get(f"/api/v1/audit-logs/{fake_id}", headers=headers)
    assert fake_resp.status_code == 404


def test_audit_log_tenant_isolation(client: TestClient, registered_gym: dict, second_registered_gym: dict):
    gym1_headers = registered_gym["headers"]
    gym2_headers = second_registered_gym["headers"]

    # Gym 1 generates an audit log
    client.post(
        "/api/v1/staff",
        headers=gym1_headers,
        json={
            "name": "Gym1 Only Staff",
            "email": f"gym1_{uuid.uuid4().hex[:6]}@gym.com",
            "password": "Password123!",
            "role": "FRONT_DESK",
        },
    )

    gym1_logs = client.get("/api/v1/audit-logs", headers=gym1_headers).json()["items"]
    gym1_log_ids = [l["id"] for l in gym1_logs]

    # Gym 2 cannot view Gym 1's audit logs in list
    gym2_logs = client.get("/api/v1/audit-logs", headers=gym2_headers).json()["items"]
    gym2_log_ids = [l["id"] for l in gym2_logs]
    assert not any(lid in gym2_log_ids for lid in gym1_log_ids)

    # Gym 2 cannot get Gym 1 audit log by ID
    for lid in gym1_log_ids[:2]:
        resp_isolated = client.get(f"/api/v1/audit-logs/{lid}", headers=gym2_headers)
        assert resp_isolated.status_code == 404


def test_audit_logs_append_only_read_only(client: TestClient, registered_gym: dict):
    headers = registered_gym["headers"]
    fake_id = str(uuid.uuid4())

    # POST to /audit-logs should not exist
    resp_post = client.post("/api/v1/audit-logs", headers=headers, json={"action": "TAMPER"})
    assert resp_post.status_code == 405

    # PUT to /audit-logs/{id} should not exist
    resp_put = client.put(f"/api/v1/audit-logs/{fake_id}", headers=headers, json={"action": "TAMPER"})
    assert resp_put.status_code == 405

    # DELETE to /audit-logs/{id} should not exist
    resp_del = client.delete(f"/api/v1/audit-logs/{fake_id}", headers=headers)
    assert resp_del.status_code == 405


def test_audit_logs_rbac(client: TestClient, registered_gym: dict):
    owner_headers = registered_gym["headers"]

    # Create Manager and Front Desk
    resp_mgr = client.post(
        "/api/v1/staff",
        headers=owner_headers,
        json={
            "name": "Manager Reviewer",
            "email": f"mgr_{uuid.uuid4().hex[:6]}@gym.com",
            "password": "Password123!",
            "role": "MANAGER",
        },
    )
    resp_fd = client.post(
        "/api/v1/staff",
        headers=owner_headers,
        json={
            "name": "Front Desk User",
            "email": f"fd_{uuid.uuid4().hex[:6]}@gym.com",
            "password": "Password123!",
            "role": "FRONT_DESK",
        },
    )

    # Login Manager
    login_mgr = client.post(
        "/api/v1/auth/login",
        json={"email": resp_mgr.json()["email"], "password": "Password123!"},
    )
    mgr_headers = {"Authorization": f"Bearer {login_mgr.json()['access_token']}"}

    # Login Front Desk
    login_fd = client.post(
        "/api/v1/auth/login",
        json={"email": resp_fd.json()["email"], "password": "Password123!"},
    )
    fd_headers = {"Authorization": f"Bearer {login_fd.json()['access_token']}"}

    # Manager can access audit logs
    assert client.get("/api/v1/audit-logs", headers=mgr_headers).status_code == 200

    # Front Desk CANNOT access audit logs
    assert client.get("/api/v1/audit-logs", headers=fd_headers).status_code == 403

