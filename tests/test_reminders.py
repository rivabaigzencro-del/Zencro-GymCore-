"""Automated tests for Day 5 Expiry Tracking, Reminder Worklists, WhatsApp Links, and Follow-ups."""
import random
import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.services.membership_service import get_gym_today


def _random_phone() -> str:
    """Generate a valid numeric phone number for tests."""
    return f"+9198{random.randint(10000000, 99999999)}"


def _create_member(client: TestClient, headers: dict, full_name: str = "Test Member", dob: date = None) -> dict:
    """Helper to create a member with optional valid DOB."""
    payload = {
        "full_name": full_name,
        "phone": _random_phone(),
    }
    if dob:
        payload["date_of_birth"] = dob.isoformat()
    resp = client.post("/api/v1/members", json=payload, headers=headers)
    assert resp.status_code == 201, f"Member creation failed: {resp.text}"
    return resp.json()


def _create_plan(client: TestClient, headers: dict, name: str = "Standard Plan", price: float = 1500.0) -> dict:
    """Helper to create a membership plan."""
    suffix = uuid.uuid4().hex[:6]
    resp = client.post(
        "/api/v1/membership-plans",
        json={"name": f"{name} {suffix}", "duration": 1, "duration_unit": "MONTHS", "price": price},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _assign_membership(client: TestClient, headers: dict, member_id: str, plan_id: str, start_date: date) -> dict:
    """Helper to assign a membership subscription."""
    resp = client.post(
        "/api/v1/memberships",
        json={
            "member_id": member_id,
            "membership_plan_id": plan_id,
            "start_date": start_date.isoformat(),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ──────────────────────────────────────────────────────────────────────────────
# 1. Expiry Tracking Worklist Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_expiry_worklist_expiring_soon_and_today(client: TestClient, registered_gym):
    """Identify memberships expiring today and expiring within warning days (default 7 days)."""
    headers = registered_gym["headers"]
    today = date.today()

    plan = _create_plan(client, headers)

    # 1. Member expiring in 3 days (EXPIRING_SOON)
    m_soon = _create_member(client, headers, "Expiring Soon Member")
    # A 1-month plan ending in 3 days means start_date was ~27 days ago
    start_soon = today + timedelta(days=4) - timedelta(days=31)
    _assign_membership(client, headers, m_soon["id"], plan["id"], start_soon)

    # Query expiries
    resp = client.get("/api/v1/reminders/expiries", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    found = next((i for i in data["items"] if i["member_id"] == m_soon["id"]), None)
    assert found is not None
    assert found["expiry_category"] in ("EXPIRING_SOON", "EXPIRING_TODAY")
    assert found["days_until_expiry"] >= 0


def test_expiry_worklist_expired_and_lapsed(client: TestClient, registered_gym):
    """Categorize expired (within 30 days) vs lapsed (> 30 days) subscriptions."""
    headers = registered_gym["headers"]
    today = date.today()
    plan = _create_plan(client, headers)

    # 1. Expired 10 days ago (EXPIRED)
    m_exp = _create_member(client, headers, "Expired Member")
    start_exp = today - timedelta(days=10) - timedelta(days=31)
    _assign_membership(client, headers, m_exp["id"], plan["id"], start_exp)

    # 2. Expired 60 days ago (LAPSED)
    m_lap = _create_member(client, headers, "Lapsed Member")
    start_lap = today - timedelta(days=60) - timedelta(days=31)
    _assign_membership(client, headers, m_lap["id"], plan["id"], start_lap)

    resp = client.get("/api/v1/reminders/expiries", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    exp_item = next((i for i in data["items"] if i["member_id"] == m_exp["id"]), None)
    lap_item = next((i for i in data["items"] if i["member_id"] == m_lap["id"]), None)

    assert exp_item is not None
    assert exp_item["expiry_category"] == "EXPIRED"
    assert exp_item["days_until_expiry"] < 0

    assert lap_item is not None
    assert lap_item["expiry_category"] == "LAPSED"
    assert lap_item["days_until_expiry"] < -30

    # Test filtering strictly by category
    resp_lapsed = client.get("/api/v1/reminders/expiries?category=LAPSED", headers=headers)
    assert resp_lapsed.status_code == 200
    l_data = resp_lapsed.json()
    assert all(i["expiry_category"] == "LAPSED" for i in l_data["items"])


# ──────────────────────────────────────────────────────────────────────────────
# 2. Renewal Follow-Up Worklist Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_renewal_followup_worklist(client: TestClient, registered_gym):
    """Members requiring renewal follow-up are listed with balance and contact status."""
    headers = registered_gym["headers"]
    today = date.today()
    plan = _create_plan(client, headers)

    m = _create_member(client, headers, "Renewal Target")
    start_exp = today - timedelta(days=5) - timedelta(days=31)
    _assign_membership(client, headers, m["id"], plan["id"], start_exp)

    resp = client.get("/api/v1/reminders/renewals", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    found = next((i for i in data["items"] if i["member_id"] == m["id"]), None)
    assert found is not None
    assert found["follow_up_status"] == "NONE"

    # Log a contact with next follow-up date in the future
    c_resp = client.post(
        "/api/v1/reminders/contacts",
        json={
            "member_id": m["id"],
            "category": "RENEWAL_FOLLOWUP",
            "channel": "PHONE",
            "outcome": "CALL_BACK_REQUESTED",
            "notes": "Member asked to call back next week",
            "follow_up_date": (today + timedelta(days=7)).isoformat(),
        },
        headers=headers,
    )
    assert c_resp.status_code == 201

    # Check renewal list again: follow-up status must now be PENDING
    resp2 = client.get("/api/v1/reminders/renewals", headers=headers)
    found2 = next(i for i in resp2.json()["items"] if i["member_id"] == m["id"])
    assert found2["follow_up_status"] == "PENDING"
    assert found2["last_contact_outcome"] == "CALL_BACK_REQUESTED"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Outstanding Dues Worklist Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_outstanding_dues_worklist_and_ageing(client: TestClient, registered_gym):
    """Invoices with outstanding balances are listed with ageing categories (0-7, 8-30, 30+ days)."""
    headers = registered_gym["headers"]
    today = date.today()

    m = _create_member(client, headers, "Dues Member")

    # 1. Invoice due 3 days ago (0-7 days overdue)
    r1 = client.post(
        "/api/v1/invoices",
        json={
            "member_id": m["id"],
            "amount_paise": 100000,
            "issue_date": (today - timedelta(days=10)).isoformat(),
            "due_date": (today - timedelta(days=3)).isoformat(),
        },
        headers=headers,
    )
    assert r1.status_code == 201

    # 2. Invoice due 20 days ago (8-30 days overdue)
    r2 = client.post(
        "/api/v1/invoices",
        json={
            "member_id": m["id"],
            "amount_paise": 200000,
            "issue_date": (today - timedelta(days=30)).isoformat(),
            "due_date": (today - timedelta(days=20)).isoformat(),
        },
        headers=headers,
    )
    assert r2.status_code == 201

    # 3. Invoice due 45 days ago (30+ days overdue)
    r3 = client.post(
        "/api/v1/invoices",
        json={
            "member_id": m["id"],
            "amount_paise": 300000,
            "issue_date": (today - timedelta(days=60)).isoformat(),
            "due_date": (today - timedelta(days=45)).isoformat(),
        },
        headers=headers,
    )
    assert r3.status_code == 201

    # 4. Fully paid invoice (must be excluded)
    r_paid = client.post(
        "/api/v1/invoices",
        json={
            "member_id": m["id"],
            "amount_paise": 50000,
            "issue_date": (today - timedelta(days=20)).isoformat(),
            "due_date": (today - timedelta(days=10)).isoformat(),
        },
        headers=headers,
    ).json()
    p_res = client.post(
        "/api/v1/payments",
        json={
            "member_id": m["id"],
            "invoice_id": r_paid["id"],
            "amount_paise": 50000,
            "payment_method": "CASH",
        },
        headers=headers,
    )
    assert p_res.status_code == 201

    # Fetch dues worklist
    resp = client.get("/api/v1/reminders/dues", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] >= 3
    # Fully paid invoice must NOT appear
    assert not any(i["invoice_id"] == r_paid["id"] for i in data["items"])

    # Verify ageing categories
    item_0_7 = next(i for i in data["items"] if i["invoice_id"] == r1.json()["id"])
    assert item_0_7["ageing_category"] == "0-7 days"

    item_8_30 = next(i for i in data["items"] if i["invoice_id"] == r2.json()["id"])
    assert item_8_30["ageing_category"] == "8-30 days"

    item_30_plus = next(i for i in data["items"] if i["invoice_id"] == r3.json()["id"])
    assert item_30_plus["ageing_category"] == "30+ days"

    # Verify aggregates
    assert data["total_dues_paise"] >= 600000
    assert data["days_0_7_paise"] >= 100000
    assert data["days_8_30_paise"] >= 200000
    assert data["days_over_30_paise"] >= 300000


# ──────────────────────────────────────────────────────────────────────────────
# 4. Birthday Reminders Worklist Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_birthday_reminders_worklist(client: TestClient, registered_gym):
    """Retrieve members with birthdays today or upcoming within 7 days, ignoring null DOB."""
    headers = registered_gym["headers"]
    today = date.today()

    # 1. Birthday today
    bday_today = date(1996, today.month, today.day)
    m_today = _create_member(client, headers, "Birthday Today Member", dob=bday_today)

    # 2. Birthday in 4 days
    upcoming_date = today + timedelta(days=4)
    bday_up = date(1994, upcoming_date.month, upcoming_date.day)
    m_up = _create_member(client, headers, "Upcoming Birthday Member", dob=bday_up)

    # 3. Birthday 40 days ago (should not appear in 7-day upcoming list)
    past_date = today - timedelta(days=40)
    bday_past = date(1992, past_date.month, past_date.day)
    m_past = _create_member(client, headers, "Past Birthday Member", dob=bday_past)

    # 4. Member with NO DOB (must be safely ignored)
    m_no_dob = _create_member(client, headers, "No DOB Member", dob=None)

    resp = client.get("/api/v1/reminders/birthdays?upcoming_days=7", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert any(i["member_id"] == m_today["id"] and i["is_today"] is True for i in data["items"])
    assert any(i["member_id"] == m_up["id"] and i["days_until_birthday"] == 4 for i in data["items"])
    assert not any(i["member_id"] == m_past["id"] for i in data["items"])
    assert not any(i["member_id"] == m_no_dob["id"] for i in data["items"])

    # Test is_today_only filter
    resp_today_only = client.get("/api/v1/reminders/birthdays?is_today_only=true", headers=headers)
    assert resp_today_only.status_code == 200
    t_items = resp_today_only.json()["items"]
    assert all(i["is_today"] is True for i in t_items)


# ──────────────────────────────────────────────────────────────────────────────
# 5. WhatsApp Pre-filled Generation Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_whatsapp_message_generation(client: TestClient, registered_gym):
    """Generate pre-filled message text and URL-encoded click-to-chat links."""
    headers = registered_gym["headers"]
    m = _create_member(client, headers, "WhatsApp Member")

    # Generate expiry reminder
    resp = client.post(
        "/api/v1/reminders/whatsapp/generate",
        json={"category": "MEMBERSHIP_EXPIRING", "member_id": m["id"]},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_send"] is True
    assert data["whatsapp_url"] is not None
    assert "https://wa.me/" in data["whatsapp_url"]
    assert "text=" in data["whatsapp_url"]
    assert data["clean_phone"] is not None

    # Test custom message override
    resp_custom = client.post(
        "/api/v1/reminders/whatsapp/generate",
        json={
            "category": "RENEWAL_FOLLOWUP",
            "member_id": m["id"],
            "custom_message": "Special 20% discount on annual renewal this week only!",
        },
        headers=headers,
    )
    assert resp_custom.status_code == 200
    data_c = resp_custom.json()
    assert "Special 20% discount" in data_c["message_text"]
    assert "Special%2020%25" in data_c["whatsapp_url"]

    # Test member without phone
    m_no_phone_resp = client.post("/api/v1/members", json={"full_name": "No Phone Member"}, headers=headers)
    assert m_no_phone_resp.status_code == 201
    m_no_phone = m_no_phone_resp.json()

    resp_no_phone = client.post(
        "/api/v1/reminders/whatsapp/generate",
        json={"category": "BIRTHDAY", "member_id": m_no_phone["id"]},
        headers=headers,
    )
    assert resp_no_phone.status_code == 200
    data_np = resp_no_phone.json()
    assert data_np["can_send"] is False
    assert data_np["whatsapp_url"] is None
    assert "invalid or missing" in data_np["warning"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# 6. Reminder Contact Logging & Follow-up Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_log_reminder_contact_interaction(client: TestClient, registered_gym):
    """Log actual contact interactions with channel, outcome, and audit details."""
    headers = registered_gym["headers"]
    m = _create_member(client, headers, "Audited Member")

    payload = {
        "member_id": m["id"],
        "category": "PAYMENT_DUE",
        "channel": "WHATSAPP",
        "outcome": "PROMISED_TO_PAY",
        "message_snippet": "Hi Audited Member, you have an outstanding payment...",
        "notes": "Member promised to pay by Friday evening via UPI",
        "follow_up_date": (date.today() + timedelta(days=3)).isoformat(),
    }
    resp = client.post("/api/v1/reminders/contacts", json=payload, headers=headers)
    assert resp.status_code == 201
    contact = resp.json()
    assert contact["member_id"] == m["id"]
    assert contact["category"] == "PAYMENT_DUE"
    assert contact["channel"] == "WHATSAPP"
    assert contact["outcome"] == "PROMISED_TO_PAY"
    assert contact["staff_user_id"] == str(registered_gym["owner_id"])

    # Query contact history
    c_hist = client.get(f"/api/v1/reminders/contacts/member/{m['id']}", headers=headers)
    assert c_hist.status_code == 200
    assert c_hist.json()["total"] == 1
    assert c_hist.json()["items"][0]["id"] == contact["id"]


def test_follow_up_scheduling_and_retrieval(client: TestClient, registered_gym):
    """Retrieve scheduled follow-ups and identify overdue vs upcoming."""
    headers = registered_gym["headers"]
    today = date.today()

    m1 = _create_member(client, headers, "Overdue Followup Member")
    m2 = _create_member(client, headers, "Upcoming Followup Member")

    # Overdue task (follow_up_date was 2 days ago)
    client.post(
        "/api/v1/reminders/contacts",
        json={
            "member_id": m1["id"],
            "category": "MEMBERSHIP_EXPIRED",
            "channel": "PHONE",
            "outcome": "NO_ANSWER",
            "follow_up_date": (today - timedelta(days=2)).isoformat(),
        },
        headers=headers,
    )

    # Upcoming task (follow_up_date is 5 days in future)
    client.post(
        "/api/v1/reminders/contacts",
        json={
            "member_id": m2["id"],
            "category": "RENEWAL_FOLLOWUP",
            "channel": "IN_PERSON",
            "outcome": "REACHED",
            "follow_up_date": (today + timedelta(days=5)).isoformat(),
        },
        headers=headers,
    )

    resp = client.get("/api/v1/reminders/follow-ups", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overdue_count"] >= 1
    assert data["upcoming_count"] >= 1

    item1 = next(i for i in data["items"] if i["member_id"] == m1["id"])
    assert item1["is_overdue"] is True
    assert item1["days_overdue"] == 2

    item2 = next(i for i in data["items"] if i["member_id"] == m2["id"])
    assert item2["is_overdue"] is False
    assert item2["days_overdue"] < 0


# ──────────────────────────────────────────────────────────────────────────────
# 7. Tenant Isolation & RBAC Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_tenant_isolation_reminders(client: TestClient, registered_gym, second_registered_gym):
    """Gym 2 cannot view or log reminders/follow-ups for Gym 1's members."""
    headers_g1 = registered_gym["headers"]
    headers_g2 = second_registered_gym["headers"]

    m1 = _create_member(client, headers_g1, "Gym 1 Member")

    # Gym 2 tries to log contact for Gym 1's member -> 404 Not Found
    r_log = client.post(
        "/api/v1/reminders/contacts",
        json={
            "member_id": m1["id"],
            "category": "BIRTHDAY",
            "channel": "PHONE",
            "outcome": "REACHED",
        },
        headers=headers_g2,
    )
    assert r_log.status_code == 404

    # Gym 2 tries to generate WhatsApp link for Gym 1's member -> 404 Not Found
    r_wa = client.post(
        "/api/v1/reminders/whatsapp/generate",
        json={"category": "BIRTHDAY", "member_id": m1["id"]},
        headers=headers_g2,
    )
    assert r_wa.status_code == 404

    # Gym 2's member contact history query for Gym 1 member is empty
    r_hist = client.get(f"/api/v1/reminders/contacts/member/{m1['id']}", headers=headers_g2)
    assert r_hist.status_code == 200
    assert r_hist.json()["total"] == 0


def test_rbac_reminder_endpoints(client: TestClient, gym_with_roles):
    """FRONT_DESK can access worklists, generate WhatsApp messages, and log contacts."""
    fd_headers = gym_with_roles["front_desk_headers"]

    # FRONT_DESK access expiries -> 200 OK
    r_exp = client.get("/api/v1/reminders/expiries", headers=fd_headers)
    assert r_exp.status_code == 200

    # FRONT_DESK access dues -> 200 OK
    r_dues = client.get("/api/v1/reminders/dues", headers=fd_headers)
    assert r_dues.status_code == 200

    # FRONT_DESK access birthdays -> 200 OK
    r_bday = client.get("/api/v1/reminders/birthdays", headers=fd_headers)
    assert r_bday.status_code == 200

    # Unauthorized request (no token) -> 401 Unauthorized
    r_unauth = client.get("/api/v1/reminders/expiries")
    assert r_unauth.status_code == 401


def test_configurable_lapse_grace_period_per_tenant(client: TestClient, registered_gym, second_registered_gym):
    """
    Test that the lapse grace threshold is independently configurable per gym:
    1. Gym 1 updates threshold to 15 days.
    2. Gym 2 keeps default threshold of 30 days.
    3. A member expired 20 days ago is LAPSED in Gym 1 (20 > 15), but EXPIRED in Gym 2 (20 <= 30).
    """
    h1 = registered_gym["headers"]
    h2 = second_registered_gym["headers"]
    today = date.today()

    # 1. Verify default settings
    s1 = client.get("/api/v1/reminders/settings", headers=h1)
    assert s1.status_code == 200
    assert s1.json()["membership_lapsed_grace_days"] == 30
    assert s1.json()["membership_expiry_warning_days"] == 7

    # 2. Update Gym 1 lapse threshold to 15 days
    p_up = client.patch(
        "/api/v1/reminders/settings",
        json={"membership_lapsed_grace_days": 15},
        headers=h1,
    )
    assert p_up.status_code == 200
    assert p_up.json()["membership_lapsed_grace_days"] == 15

    # 3. Create member expired 20 days ago in Gym 1
    p1 = _create_plan(client, h1)
    m1 = _create_member(client, h1, "Gym 1 20-Day Expired Member")
    start_20_days_ago = today - timedelta(days=20) - timedelta(days=31)
    _assign_membership(client, h1, m1["id"], p1["id"], start_20_days_ago)

    # In Gym 1 (threshold 15): 20 days expired > 15 -> LAPSED
    exp1 = client.get("/api/v1/reminders/expiries", headers=h1).json()
    item1 = next(i for i in exp1["items"] if i["member_id"] == m1["id"])
    assert item1["expiry_category"] == "LAPSED"

    # 4. Create identical member expired 20 days ago in Gym 2 (threshold default 30)
    p2 = _create_plan(client, h2)
    m2 = _create_member(client, h2, "Gym 2 20-Day Expired Member")
    _assign_membership(client, h2, m2["id"], p2["id"], start_20_days_ago)

    # In Gym 2 (threshold 30): 20 days expired <= 30 -> EXPIRED
    exp2 = client.get("/api/v1/reminders/expiries", headers=h2).json()
    item2 = next(i for i in exp2["items"] if i["member_id"] == m2["id"])
    assert item2["expiry_category"] == "EXPIRED"

