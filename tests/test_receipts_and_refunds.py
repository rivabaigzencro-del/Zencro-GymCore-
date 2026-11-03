"""Automated tests for Receipts, Refunds, Reversals, Daily Summary, and Financial RBAC."""
from datetime import date
import uuid
import pytest
from fastapi.testclient import TestClient


def _create_test_member(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/v1/members",
        json={"full_name": f"Financial Member {uuid.uuid4().hex[:6]}"},
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


def test_manual_receipt_generation_and_duplicate_prevention(client: TestClient, registered_gym):
    """Manual receipt creation works and rejects duplicate generation with 409 Conflict."""
    member = _create_test_member(client, registered_gym["headers"])

    # Create payment with auto_generate_receipt=False
    p_resp = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "amount_paise": 200000,
            "payment_method": "CASH",
            "auto_generate_receipt": False,
        },
        headers=registered_gym["headers"],
    )
    assert p_resp.status_code == 201
    payment = p_resp.json()
    assert payment["receipt_number"] is None

    # Manually generate receipt
    r_resp = client.post(
        f"/api/v1/receipts/payment/{payment['id']}",
        json={"notes": "Manual counter receipt"},
        headers=registered_gym["headers"],
    )
    assert r_resp.status_code == 201
    receipt = r_resp.json()
    assert receipt["receipt_number"].startswith("REC-")
    assert receipt["payment_id"] == payment["id"]

    # Duplicate generation attempt must return 409 Conflict
    dup_resp = client.post(
        f"/api/v1/receipts/payment/{payment['id']}",
        headers=registered_gym["headers"],
    )
    assert dup_resp.status_code == 409

    # Retrieve receipt by ID and by payment ID
    get_by_id = client.get(f"/api/v1/receipts/{receipt['id']}", headers=registered_gym["headers"])
    assert get_by_id.status_code == 200
    assert get_by_id.json()["receipt_number"] == receipt["receipt_number"]

    get_by_pay = client.get(f"/api/v1/receipts/payment/{payment['id']}", headers=registered_gym["headers"])
    assert get_by_pay.status_code == 200
    assert get_by_pay.json()["id"] == receipt["id"]


def test_full_refund_payment_and_restore_invoice(client: TestClient, registered_gym):
    """
    Refunding a completed payment transitions payment status to REFUNDED,
    restores the linked invoice's balance, and updates invoice status back to ISSUED.
    """
    member = _create_test_member(client, registered_gym["headers"])
    invoice = _create_test_invoice(client, registered_gym["headers"], member["id"], 500000)

    # Full payment of ₹5,000
    p_resp = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": invoice["id"],
            "amount_paise": 500000,
            "payment_method": "UPI",
        },
        headers=registered_gym["headers"],
    )
    payment = p_resp.json()

    # Invoice is now PAID
    inv_paid = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"]).json()
    assert inv_paid["invoice_status"] == "PAID"
    assert inv_paid["balance_amount_paise"] == 0

    # Process full refund
    ref_resp = client.post(
        f"/api/v1/payments/{payment['id']}/refund",
        json={"amount_paise": 500000, "reason": "Customer cancellation within refund window"},
        headers=registered_gym["headers"],
    )
    assert ref_resp.status_code == 200
    ref_data = ref_resp.json()
    assert ref_data["amount_paise"] == 500000
    assert ref_data["refund_type"] == "REFUND"
    assert ref_data["status"] == "COMPLETED"

    # Payment status is now REFUNDED
    p_check = client.get(f"/api/v1/payments/{payment['id']}", headers=registered_gym["headers"]).json()
    assert p_check["payment_status"] == "REFUNDED"

    # Invoice balance restored to ₹5,000 and status is ISSUED
    inv_restored = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"]).json()
    assert inv_restored["paid_amount_paise"] == 0
    assert inv_restored["balance_amount_paise"] == 500000
    assert inv_restored["invoice_status"] in ("ISSUED", "OVERDUE")


def test_partial_refunds_and_excessive_refund_rejection(client: TestClient, registered_gym):
    """
    Partial refunds transition payment status to PARTIALLY_REFUNDED.
    Excessive refunds exceeding remaining refundable amount are rejected with 400.
    """
    member = _create_test_member(client, registered_gym["headers"])

    # Payment of ₹5,000
    p_resp = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 500000, "payment_method": "CARD"},
        headers=registered_gym["headers"],
    )
    payment = p_resp.json()

    # Partial refund 1: ₹2,000
    r1 = client.post(
        f"/api/v1/payments/{payment['id']}/refund",
        json={"amount_paise": 200000, "reason": "Partial dissatisfaction"},
        headers=registered_gym["headers"],
    )
    assert r1.status_code == 200
    p_check1 = client.get(f"/api/v1/payments/{payment['id']}", headers=registered_gym["headers"]).json()
    assert p_check1["payment_status"] == "PARTIALLY_REFUNDED"

    # Excessive refund: try to refund ₹4,000 when only ₹3,000 remains -> 400
    r_excess = client.post(
        f"/api/v1/payments/{payment['id']}/refund",
        json={"amount_paise": 400000, "reason": "Excessive request"},
        headers=registered_gym["headers"],
    )
    assert r_excess.status_code == 400
    assert "exceeds" in r_excess.json()["detail"].lower()

    # Partial refund 2: ₹3,000 completing the full refund
    r2 = client.post(
        f"/api/v1/payments/{payment['id']}/refund",
        json={"amount_paise": 300000, "reason": "Final remaining settlement"},
        headers=registered_gym["headers"],
    )
    assert r2.status_code == 200
    p_check2 = client.get(f"/api/v1/payments/{payment['id']}", headers=registered_gym["headers"]).json()
    assert p_check2["payment_status"] == "REFUNDED"


def test_payment_reversal_bounced_cheque(client: TestClient, registered_gym):
    """
    Reversing a payment (e.g. cheque bounce) updates status to REVERSED,
    creates a REVERSAL audit record, and restores invoice balance.
    """
    member = _create_test_member(client, registered_gym["headers"])
    invoice = _create_test_invoice(client, registered_gym["headers"], member["id"], 400000)

    # Cheque payment of ₹4,000
    p_resp = client.post(
        "/api/v1/payments",
        json={
            "member_id": member["id"],
            "invoice_id": invoice["id"],
            "amount_paise": 400000,
            "payment_method": "CHEQUE",
            "transaction_reference": "CHQ_998877",
        },
        headers=registered_gym["headers"],
    )
    payment = p_resp.json()

    # Reverse payment due to bounced cheque
    rev_resp = client.post(
        f"/api/v1/payments/{payment['id']}/reverse",
        json={"reason": "Cheque returned unpaid: insufficient funds (NSF)"},
        headers=registered_gym["headers"],
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["refund_type"] == "REVERSAL"
    assert rev_data["amount_paise"] == 400000
    assert rev_data["status"] == "COMPLETED"

    # Payment status is REVERSED
    p_check = client.get(f"/api/v1/payments/{payment['id']}", headers=registered_gym["headers"]).json()
    assert p_check["payment_status"] == "REVERSED"

    # Invoice balance restored
    inv_check = client.get(f"/api/v1/invoices/{invoice['id']}", headers=registered_gym["headers"]).json()
    assert inv_check["paid_amount_paise"] == 0
    assert inv_check["balance_amount_paise"] == 400000


def test_receipt_preserved_after_refund_and_reversal(client: TestClient, registered_gym):
    """Receipts must never be erased when payments are refunded or reversed."""
    member = _create_test_member(client, registered_gym["headers"])

    # Payment with auto receipt
    p_resp = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 150000, "payment_method": "CASH"},
        headers=registered_gym["headers"],
    )
    payment = p_resp.json()
    receipt_id = payment["receipt_id"]
    assert receipt_id is not None

    # Refund the payment
    client.post(
        f"/api/v1/payments/{payment['id']}/refund",
        json={"amount_paise": 150000, "reason": "Full refund audit test"},
        headers=registered_gym["headers"],
    )

    # Receipt is still retrievable
    r_check = client.get(f"/api/v1/receipts/{receipt_id}", headers=registered_gym["headers"])
    assert r_check.status_code == 200
    assert r_check.json()["payment_id"] == payment["id"]


def test_daily_collection_summary(client: TestClient, registered_gym):
    """
    Daily close summary accurately groups gross collections by payment method,
    tallies refunds and reversals, and computes correct net collections.
    """
    member = _create_test_member(client, registered_gym["headers"])

    # Cash: ₹1,000 (100000)
    client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 100000, "payment_method": "CASH"},
        headers=registered_gym["headers"],
    )

    # UPI: ₹2,000 (200000)
    p_upi = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 200000, "payment_method": "UPI"},
        headers=registered_gym["headers"],
    ).json()

    # Card: ₹3,000 (300000)
    p_card = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 300000, "payment_method": "CARD"},
        headers=registered_gym["headers"],
    ).json()

    # Refund ₹500 (50000) on UPI
    client.post(
        f"/api/v1/payments/{p_upi['id']}/refund",
        json={"amount_paise": 50000, "reason": "Partial UPI refund"},
        headers=registered_gym["headers"],
    )

    # Reverse Card payment of ₹3,000 (300000)
    client.post(
        f"/api/v1/payments/{p_card['id']}/reverse",
        json={"reason": "Customer disputed card charge"},
        headers=registered_gym["headers"],
    )

    # Fetch daily summary
    summary_resp = client.get("/api/v1/payments/daily-summary", headers=registered_gym["headers"])
    assert summary_resp.status_code == 200
    s = summary_resp.json()

    # Gross = 100,000 (CASH) + 200,000 (UPI) + 300,000 (CARD tendered) = 600,000 paise
    # Total refunds = 50,000, reversals = 300,000
    # Net collections = 600,000 - 50,000 - 300,000 = 250,000 paise (Cash 100,000 + Net UPI 150,000 + Net Card 0)
    assert s["total_gross_paise"] == 600000
    assert s["cash_paise"] == 100000
    assert s["upi_paise"] == 200000
    assert s["card_paise"] == 300000
    assert s["total_refunds_paise"] == 50000
    assert s["total_reversals_paise"] == 300000
    assert s["net_collections_paise"] == 250000
    assert s["transaction_count"] == 3
    assert s["refund_count"] == 2


def test_rbac_refunds_reversals_and_daily_summary(client: TestClient, gym_with_roles):
    """
    FRONT_DESK cannot issue refunds, reverse payments, or view daily summary (403 Forbidden).
    OWNER and MANAGER can.
    """
    member = _create_test_member(client, gym_with_roles["headers"])
    p_resp = client.post(
        "/api/v1/payments",
        json={"member_id": member["id"], "amount_paise": 100000, "payment_method": "CASH"},
        headers=gym_with_roles["headers"],
    )
    payment = p_resp.json()

    # 1. FRONT_DESK refund -> 403
    fd_refund = client.post(
        f"/api/v1/payments/{payment['id']}/refund",
        json={"amount_paise": 50000, "reason": "Unauthorized desk refund"},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_refund.status_code == 403

    # 2. FRONT_DESK reverse -> 403
    fd_reverse = client.post(
        f"/api/v1/payments/{payment['id']}/reverse",
        json={"reason": "Unauthorized desk reversal"},
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_reverse.status_code == 403

    # 3. FRONT_DESK daily-summary -> 403
    fd_summary = client.get(
        "/api/v1/payments/daily-summary",
        headers=gym_with_roles["front_desk_headers"],
    )
    assert fd_summary.status_code == 403

    # 4. MANAGER can view daily-summary -> 200
    mgr_summary = client.get(
        "/api/v1/payments/daily-summary",
        headers=gym_with_roles["manager_headers"],
    )
    assert mgr_summary.status_code == 200


def test_tenant_isolation_receipts_and_refunds(client: TestClient, registered_gym, second_registered_gym):
    """Gym 2 cannot retrieve Gym 1's receipts or refund Gym 1's payments."""
    gym1_member = _create_test_member(client, registered_gym["headers"])
    p1 = client.post(
        "/api/v1/payments",
        json={"member_id": gym1_member["id"], "amount_paise": 200000, "payment_method": "CASH"},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to GET Gym 1's receipt -> 404
    r_get = client.get(f"/api/v1/receipts/{p1['receipt_id']}", headers=second_registered_gym["headers"])
    assert r_get.status_code == 404

    # Gym 2 tries to refund Gym 1's payment -> 404
    r_refund = client.post(
        f"/api/v1/payments/{p1['id']}/refund",
        json={"amount_paise": 100000, "reason": "Cross-tenant refund attempt"},
        headers=second_registered_gym["headers"],
    )
    assert r_refund.status_code == 404

