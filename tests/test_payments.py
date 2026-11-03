"""Automated tests for Payment operations, partial payments, and balance tracking."""
from datetime import date
import uuid
import pytest
from fastapi.testclient import TestClient


def _create_test_member(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/v1/members",
        json={"full_name": f"Payment Member {uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_test_invoice(client: TestClient, headers: dict, member_id: str, amount_paise: int) -> dict:
    resp = client.post(
        "/api/v1/invoices",
        json={"member_id": member_id, "amount_paise": amount_paise},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_record_payment_all_payment_methods(client: TestClient, registered_gym):
    """Test recording payments using CASH, UPI, CARD, BANK_TRANSFER, and CHEQUE."""
    member = _create_test_member(client, registered_gym["headers"])
    methods = [
        ("CASH", None),
        ("UPI", "upi_ref_1234567890"),
        ("CARD", "card_auth_987654321"),
        ("BANK_TRANSFER", "IMPS_20261103001"),
        ("CHEQUE", "CHQ_445566"),
    ]

    for method, ref in methods:
        payload = {
            "member_id": member["id"],
            "amount_paise": 100000,
            "payment_method": method,
            "transaction_reference": ref,
            "notes": f"Payment test via {method}",
            "auto_generate_receipt": True,
        }
        resp = client.post("/api/v1/payments", json=payload, headers=registered_gym["headers"])
        assert resp.status_code == 201, f"Failed for {method}: {resp.text}"
        data = resp.json()
        assert data["payment_method"] == method
        assert data["payment_status"] == "COMPLETED"
        assert data["amount_paise"] == 100000
        assert data["transaction_reference"] == ref
        assert data["receipt_number"] is not None
        assert data["receipt_number"].startswith("REC-")


def test_invalid_payment_amounts(client: TestClient, registered_gym):
    """Zero and negative payment amounts must be rejected with 422 Unprocessable Entity."""
    member = _create_test_member(client, registered_gym["headers"])

    # Zero amount
    r_zero = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 0, "payment_method": "CASH"},
        headers=registered_gym["headers"],
    )
    assert r_zero.status_code == 422

    # Negative amount
    r_neg = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": -50000, "payment_method": "UPI"},
        headers=registered_gym["headers"],
    )
    assert r_neg.status_code == 422


def test_partial_payments_and_invoice_balance(client: TestClient, registered_gym):
    """
    Test multiple partial payments against a single invoice:
    Invoice = ₹5,000 (500,000 paise)
    Payment 1 = ₹2,000 -> balance ₹3,000 (PARTIALLY_PAID)
    Payment 2 = ₹3,000 -> balance ₹0 (PAID)
    """
    member = _create_test_member(client, registered_gym["headers"])
    invoice = _create_test_invoice(client, registered_gym["headers"], member["id"], 500000)

    # First partial payment: ₹2,000
    p1 = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": invoice["id"],
            "amount_paise": 200000,
            "payment_method": "UPI",
            "transaction_reference": "upi_part_1",
        },
        headers=registered_gym["headers"],
    )
    assert p1.status_code == 201

    # Check invoice status and balance
    inv_check = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"]).json()
    assert inv_check["paid_amount_paise"] == 200000
    assert inv_check["balance_amount_paise"] == 300000
    assert inv_check["invoice_status"] == "PARTIALLY_PAID"

    # Second payment completing invoice: ₹3,000
    p2 = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": invoice["id"],
            "amount_paise": 300000,
            "payment_method": "CASH",
        },
        headers=registered_gym["headers"],
    )
    assert p2.status_code == 201

    # Check invoice status is now PAID
    inv_final = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"]).json()
    assert inv_final["paid_amount_paise"] == 500000
    assert inv_final["balance_amount_paise"] == 0
    assert inv_final["invoice_status"] == "PAID"


def test_overpayment_prevention(client: TestClient, registered_gym):
    """A payment exceeding the outstanding invoice balance must be rejected with 400 Bad Request."""
    member = _create_test_member(client, registered_gym["headers"])
    invoice = _create_test_invoice(client, registered_gym["headers"], member["id"], 300000)

    # Try paying ₹4,000 against ₹3,000 invoice
    resp = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": invoice["id"],
            "amount_paise": 400000,
            "payment_method": "CARD",
        },
        headers=registered_gym["headers"],
    )
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_cannot_pay_cancelled_or_paid_invoice(client: TestClient, registered_gym):
    """Payments against CANCELLED or already PAID invoices must be rejected with 400 Bad Request."""
    member = _create_test_member(client, registered_gym["headers"])

    # 1. Cancelled invoice
    inv_cancel = _create_test_invoice(client, registered_gym["headers"], member["id"], 200000)
    client.post(f"/api/v1/invoices/{inv_cancel['id']}/cancel", headers=registered_gym["headers"])

    r_cancel = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": inv_cancel["id"],
            "amount_paise": 200000,
            "payment_method": "CASH",
        },
        headers=registered_gym["headers"],
    )
    assert r_cancel.status_code == 400
    assert "cancelled" in r_cancel.json()["detail"].lower()

    # 2. Fully paid invoice
    inv_paid = _create_test_invoice(client, registered_gym["headers"], member["id"], 100000)
    client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": inv_paid["id"],
            "amount_paise": 100000,
            "payment_method": "CASH",
        },
        headers=registered_gym["headers"],
    )

    r_paid = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": inv_paid["id"],
            "amount_paise": 50000,
            "payment_method": "CASH",
        },
        headers=registered_gym["headers"],
    )
    assert r_paid.status_code == 400
    assert "fully paid" in r_paid.json()["detail"].lower()


def test_list_payments_and_filters(client: TestClient, registered_gym):
    """Test listing payments with pagination, member filter, and invoice filter."""
    member = _create_test_member(client, registered_gym["headers"])
    inv = _create_test_invoice(client, registered_gym["headers"], member["id"], 1000000)

    # 3 payments against invoice
    for _ in range(3):
        client.post(
            "/api/v1/payments",
            json={
                "member_id": member["id"],
                "invoice_id": inv["id"],
                "amount_paise": 200000,
                "payment_method": "UPI",
            },
            headers=registered_gym["headers"],
        )

    list_resp = client.get(
        f"/api/v1/payments?invoice_id={inv['id']}&page=1&page_size=2",
        headers=registered_gym["headers"],
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


def test_tenant_isolation_payments(client: TestClient, registered_gym, second_registered_gym):
    """Tenants cannot view or create payments for another gym's members or invoices."""
    gym1_member = _create_test_member(client, registered_gym["headers"])
    p1 = client.post(
        "/api/v1/payments",
        json={"member_id": gym1_member["id"], "amount_paise": 150000, "payment_method": "CASH"},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to GET Gym 1's payment -> 404
    r_get = client.get(f"/api/v1/payments/{p1['id']}", headers=second_registered_gym["headers"])
    assert r_get.status_code == 404

    # Gym 2 tries to pay Gym 1's member -> 404
    r_pay = client.post(
        "/api/v1/payments",
        json={"member_id": gym1_member["id"], "amount_paise": 50000, "payment_method": "CASH"},
        headers=second_registered_gym["headers"],
    )
    assert r_pay.status_code == 404


def test_rbac_payments(client: TestClient, gym_with_roles):
    """FRONT_DESK role can record and view payments."""
    member = _create_test_member(client, gym_with_roles["headers"])

    # FRONT_DESK records payment -> 201 Created
    fd_resp = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 100000, "payment_method": "CASH"},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_resp.status_code == 201
    payment = fd_resp.json()

    # FRONT_DESK retrieves payment -> 200 OK
    fd_get = client.get(f"/api/v1/payments/{payment['id']}", headers=gym_with_roles["front_desk_headers"])
    assert fd_get.status_code == 200


def test_concurrent_receipt_number_uniqueness(client: TestClient, registered_gym):
    """Concurrent payment recordings with auto-receipt generation produce strictly unique receipt numbers."""
    from concurrent.futures import ThreadPoolExecutor

    member = _create_test_member(client, registered_gym["headers"])

    def create_single_payment(idx: int):
        return client.post(
            "/api/v1/payments",
            json={
                "member_id": member["id"],
                "amount_paise": 50000 + idx,
                "payment_method": "CASH",
                "auto_generate_receipt": True,
            },
            headers=registered_gym["headers"],
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(create_single_payment, range(8)))

    for r in results:
        assert r.status_code == 201, f"Concurrent payment failed: {r.text}"

    receipt_numbers = [r.json()["receipt_number"] for r in results]
    assert len(receipt_numbers) == 8
    assert len(set(receipt_numbers)) == 8, f"Duplicate receipt numbers detected: {receipt_numbers}"


def test_concurrent_payment_overpayment_prevention(client: TestClient, registered_gym):
    """
    When multiple payments are submitted concurrently against an invoice of ₹5,000,
    the cumulative paid amount must never exceed ₹5,000.
    """
    from concurrent.futures import ThreadPoolExecutor

    member = _create_test_member(client, registered_gym["headers"])
    invoice = _create_test_invoice(client, registered_gym["headers"], member["id"], 500000)

    # 4 concurrent requests each attempting to pay ₹2,000 (total ₹8,000 > ₹5,000)
    def attempt_payment(_):
        return client.post(
            "/api/v1/payments",
            json={
                "member_id": member["id"],
                "invoice_id": invoice["id"],
                "amount_paise": 200000,
                "payment_method": "UPI",
            },
            headers=registered_gym["headers"],
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(attempt_payment, range(4)))

    successes = [r for r in results if r.status_code == 201]
    rejections = [r for r in results if r.status_code == 400]

    # At most 2 payments of ₹2,000 can succeed (₹4,000 <= ₹5,000). The 3rd would be ₹6,000 and must be rejected.
    assert len(successes) <= 2
    assert len(rejections) >= 2

    # Verify invoice final balance is consistent
    inv_check = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"]).json()
    assert inv_check["paid_amount_paise"] <= 500000
    assert inv_check["balance_amount_paise"] == inv_check["amount_paise"] - inv_check["paid_amount_paise"]

