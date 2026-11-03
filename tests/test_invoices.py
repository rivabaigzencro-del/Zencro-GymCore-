"""Automated tests for Invoices, billing, and outstanding dues management."""
from datetime import date, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient


def _create_test_member(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/v1/members",
        json={"full_name": f"Invoice Member {uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_invoice_success(client: TestClient, registered_gym):
    """Test creating an invoice with valid positive amount in paise."""
    member = _create_test_member(client, registered_gym["headers"])
    today = date.today().isoformat()
    due = (date.today() + timedelta(days=7)).isoformat()

    payload = {
        "member_id": member["id"],
        "amount_paise": 500000,  # ₹5,000.00
        "issue_date": today,
        "due_date": due,
        "description": "Annual Gym Membership Fee",
    }
    resp = client.post("/api/v1/invoices", json=payload, headers=registered_gym["headers"])
    assert resp.status_code == 201, f"Failed: {resp.text}"
    data = resp.json()

    assert data["member_id"] == member["id"]
    assert data["amount_paise"] == 500000
    assert data["paid_amount_paise"] == 0
    assert data["balance_amount_paise"] == 500000
    assert data["invoice_status"] == "ISSUED"
    assert data["issue_date"] == today
    assert data["due_date"] == due
    assert data["invoice_number"].startswith("INV-")
    assert data["tenant_id"] == str(registered_gym["tenant_id"])


def test_create_invoice_with_membership(client: TestClient, registered_gym):
    """Test creating an invoice linked to an active membership."""
    member = _create_test_member(client, registered_gym["headers"])

    # Create plan and membership
    p_resp = client.post(
        "/api/v1/membership-plans",
        json={"name": "Monthly", "duration": 1, "duration_unit": "MONTHS", "price": 1500.00},
        headers=registered_gym["headers"],
    )
    plan = p_resp.json()

    m_resp = client.post(
        "/api/v1/memberships",
        json={
            "member_id": member["id"],
            "membership_plan_id": plan["id"],
            "start_date": date.today().isoformat(),
        },
        headers=registered_gym["headers"],
    )
    membership = m_resp.json()

    inv_resp = client.post(
        "/api/v1/invoices",
        json={
            "member_id": member["id"],
            "membership_id": membership["id"],
            "amount_paise": 150000,
            "description": "Monthly Plan invoice",
        },
        headers=registered_gym["headers"],
    )
    assert inv_resp.status_code == 201
    inv_data = inv_resp.json()
    assert inv_data["membership_id"] == membership["id"]


def test_create_invoice_invalid_amounts_and_dates(client: TestClient, registered_gym):
    """Zero amount, negative amount, and due_date < issue_date must be rejected."""
    member = _create_test_member(client, registered_gym["headers"])

    # Zero amount
    r_zero = client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 0},
        headers=registered_gym["headers"],
    )
    assert r_zero.status_code == 422

    # Negative amount
    r_neg = client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": -5000},
        headers=registered_gym["headers"],
    )
    assert r_neg.status_code == 422

    # due_date < issue_date
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    r_dates = client.post(
        "/api/v1/invoices",
        json={
            "member_id": member["id"],
            "amount_paise": 100000,
            "issue_date": today.isoformat(),
            "due_date": yesterday,
        },
        headers=registered_gym["headers"],
    )
    assert r_dates.status_code == 422


def test_get_invoice_and_auto_overdue(client: TestClient, registered_gym):
    """An invoice with a past due_date automatically transitions to OVERDUE upon retrieval."""
    member = _create_test_member(client, registered_gym["headers"])
    past_issue = (date.today() - timedelta(days=10)).isoformat()
    past_due = (date.today() - timedelta(days=3)).isoformat()

    inv_resp = client.post(
        "/api/v1/invoices",
        json={
            "member_id": member["id"],
            "amount_paise": 200000,
            "issue_date": past_issue,
            "due_date": past_due,
        },
        headers=registered_gym["headers"],
    )
    assert inv_resp.status_code == 201
    invoice = inv_resp.json()
    assert invoice["invoice_status"] == "OVERDUE"

    # Get single invoice
    get_resp = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["invoice_status"] == "OVERDUE"


def test_list_invoices_and_filters(client: TestClient, registered_gym):
    """Test listing invoices with pagination and member filter."""
    member = _create_test_member(client, registered_gym["headers"])

    # Create 3 invoices
    for i in range(3):
        client.post(
            "/api/v1/invoices",
            json={"member_id": member["id"], "amount_paise": (i + 1) * 100000},
            headers=registered_gym["headers"],
        )

    # List all
    list_resp = client.get(
        f"/api/v1/invoices?member_id={member['id']}&page=1&page_size=2",
        headers=registered_gym["headers"],
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


def test_update_invoice_permitted_fields(client: TestClient, registered_gym):
    """Updating due_date and description on an existing invoice."""
    member = _create_test_member(client, registered_gym["headers"])
    inv = client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 300000, "description": "Original"},
        headers=registered_gym["headers"],
    ).json()

    new_due = (date.today() + timedelta(days=15)).isoformat()
    patch_resp = client.patch(
        f"/api/v1/invoices/{inv['id']}",
        json={"due_date": new_due, "description": "Updated Description"},
        headers=registered_gym["headers"],
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["due_date"] == new_due
    assert updated["description"] == "Updated Description"


def test_cancel_invoice_unpaid(client: TestClient, registered_gym):
    """Cancelling an unpaid invoice changes status to CANCELLED and clears balance."""
    member = _create_test_member(client, registered_gym["headers"])
    inv = client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 400000},
        headers=registered_gym["headers"],
    ).json()

    cancel_resp = client.post(
        f"/api/v1/invoices/{inv['id']}/cancel",
        json={"reason": "Member withdrew request"},
        headers=registered_gym["headers"],
    )
    assert cancel_resp.status_code == 200
    cancelled = cancel_resp.json()
    assert cancelled["invoice_status"] == "CANCELLED"
    assert cancelled["balance_amount_paise"] == 400000

    # Repeating cancel must fail
    repeat_resp = client.post(
        f"/api/v1/invoices/{inv['id']}/cancel",
        headers=registered_gym["headers"],
    )
    assert repeat_resp.status_code == 400


def test_outstanding_dues_calculation(client: TestClient, registered_gym):
    """Outstanding dues correctly aggregates invoices, paid amounts, and overdue balances."""
    member = _create_test_member(client, registered_gym["headers"])

    # Invoice 1: current (500000 paise)
    client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 500000},
        headers=registered_gym["headers"],
    )

    # Invoice 2: overdue (300000 paise)
    past_due = (date.today() - timedelta(days=5)).isoformat()
    client.post(
        "/api/v1/invoices",
        json={
            "member_id": member["id"],
            "amount_paise": 300000,
            "issue_date": past_due,
            "due_date": past_due,
        },
        headers=registered_gym["headers"],
    )

    dues_resp = client.get(
        f"/api/v1/invoices/outstanding?member_id={member['id']}",
        headers=registered_gym["headers"],
    )
    assert dues_resp.status_code == 200
    dues = dues_resp.json()
    assert dues["total_invoiced_paise"] == 800000
    assert dues["total_paid_paise"] == 0
    assert dues["total_outstanding_paise"] == 800000
    assert dues["overdue_invoices_count"] == 1
    assert dues["overdue_amount_paise"] == 300000


def test_tenant_isolation_invoices(client: TestClient, registered_gym, second_registered_gym):
    """Tenants cannot view, update, cancel, or associate another tenant's invoices."""
    gym1_member = _create_test_member(client, registered_gym["headers"])
    gym1_inv = client.post(
        "/api/v1/invoices",
        json={"member_id": gym1_member["id"], "amount_paise": 250000},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to GET Gym 1's invoice -> 404
    r_get = client.get(f"/api/v1/invoices/{gym1_inv['id']}", headers=second_registered_gym["headers"])
    assert r_get.status_code == 404

    # Gym 2 tries to cancel Gym 1's invoice -> 404
    r_cancel = client.post(
        f"/api/v1/invoices/{gym1_inv['id']}/cancel",
        headers=second_registered_gym["headers"],
    )
    assert r_cancel.status_code == 404

    # Gym 2 tries to create an invoice for Gym 1's member -> 404
    r_cross_create = client.post(
        "/api/v1/invoices",
        json={"member_id": gym1_member["id"], "amount_paise": 100000},
        headers=second_registered_gym["headers"],
    )
    assert r_cross_create.status_code == 404


def test_rbac_invoices(client: TestClient, gym_with_roles):
    """FRONT_DESK cannot create or cancel invoices; OWNER and MANAGER can."""
    member = _create_test_member(client, gym_with_roles["headers"])

    # FRONT_DESK create invoice -> 403 Forbidden
    fd_create = client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 100000},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_create.status_code == 403

    # MANAGER creates invoice -> 201 Created
    mgr_create = client.post(
        "/api/v1/invoices",
        json={"member_id": member["id"], "amount_paise": 100000},
        headers=gym_with_roles["manager_headers"],
    )
    assert mgr_create.status_code == 201
    inv = mgr_create.json()

    # FRONT_DESK views invoice -> 200 OK
    fd_get = client.get(f"/api/v1/invoices/{inv['id']}", headers=gym_with_roles["front_desk_headers"])
    assert fd_get.status_code == 200

    # FRONT_DESK cancels invoice -> 403 Forbidden
    fd_cancel = client.post(
        f"/api/v1/invoices/{inv['id']}/cancel",
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_cancel.status_code == 403


def test_concurrent_invoice_number_uniqueness(client: TestClient, registered_gym):
    """Multiple concurrent invoice creations must produce strictly unique sequential invoice numbers."""
    from concurrent.futures import ThreadPoolExecutor

    member = _create_test_member(client, registered_gym["headers"])

    def create_single_invoice(idx: int):
        return client.post(
            "/api/v1/invoices",
            json={"member_id": member["id"], "amount_paise": 100000 + idx},
            headers=registered_gym["headers"],
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(create_single_invoice, range(6)))

    for r in results:
        assert r.status_code == 201, f"Concurrent creation failed: {r.text}"

    numbers = [r.json()["invoice_number"] for r in results]
    assert len(numbers) == 6
    assert len(set(numbers)) == 6, f"Duplicate invoice numbers detected: {numbers}"

