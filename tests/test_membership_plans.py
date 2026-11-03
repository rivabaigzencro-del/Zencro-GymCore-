"""Comprehensive tests for Membership Plans module."""
from decimal import Decimal
from fastapi.testclient import TestClient


def test_create_monthly_plan(client: TestClient, registered_gym):
    """Test creating a standard monthly membership plan."""
    payload = {
        "name": "Standard Monthly",
        "description": "Full access to gym equipment and lockers",
        "duration": 1,
        "duration_unit": "MONTHS",
        "price": 1999.00,
        "is_active": True,
    }
    resp = client.post("/api/v1/membership-plans", json=payload, headers=registered_gym["headers"])
    assert resp.status_code == 201, f"Failed: {resp.text}"
    data = resp.json()
    assert data["name"] == "Standard Monthly"
    assert data["duration"] == 1
    assert data["duration_unit"] == "MONTHS"
    assert float(data["price"]) == 1999.00
    assert data["is_active"] is True
    assert data["tenant_id"] == str(registered_gym["tenant_id"])
    assert "id" in data


def test_create_quarterly_half_yearly_and_yearly_plans(client: TestClient, registered_gym):
    """Test creating quarterly, half-yearly and yearly plans with correct pricing."""
    plans = [
        {"name": "Quarterly Pro", "duration": 3, "duration_unit": "MONTHS", "price": 4999.00},
        {"name": "Half-Yearly Elite", "duration": 6, "duration_unit": "MONTHS", "price": 8999.00},
        {"name": "Annual Unlimited", "duration": 12, "duration_unit": "MONTHS", "price": 14999.00},
        {"name": "Two-Week Pass", "duration": 14, "duration_unit": "DAYS", "price": 999.00},
    ]
    for p in plans:
        resp = client.post("/api/v1/membership-plans", json=p, headers=registered_gym["headers"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == p["name"]
        assert data["duration"] == p["duration"]
        assert data["duration_unit"] == p["duration_unit"]
        assert float(data["price"]) == p["price"]


def test_plan_validation_negative_price_and_duration_rejected(client: TestClient, registered_gym):
    """Price <= 0 or duration <= 0 must fail validation with 422 Unprocessable Entity."""
    # Invalid negative price
    resp1 = client.post(
        "/api/v1/membership-plans",
        json={"name": "Bad Price", "duration": 1, "duration_unit": "MONTHS", "price": -50.00},
        headers=registered_gym["headers"],
    )
    assert resp1.status_code == 422

    # Invalid zero duration
    resp2 = client.post(
        "/api/v1/membership-plans",
        json={"name": "Bad Duration", "duration": 0, "duration_unit": "MONTHS", "price": 1000.00},
        headers=registered_gym["headers"],
    )
    assert resp2.status_code == 422


def test_list_plans_active_filter(client: TestClient, registered_gym):
    """Test plan listing with include_inactive filter flag."""
    # Active plan
    client.post(
        "/api/v1/membership-plans",
        json={"name": "Active Plan", "duration": 1, "duration_unit": "MONTHS", "price": 1000.00, "is_active": True},
        headers=registered_gym["headers"],
    )
    # Inactive plan
    client.post(
        "/api/v1/membership-plans",
        json={"name": "Inactive Plan", "duration": 1, "duration_unit": "MONTHS", "price": 1000.00, "is_active": False},
        headers=registered_gym["headers"],
    )

    # By default, only active plans returned
    r_active = client.get("/api/v1/membership-plans", headers=registered_gym["headers"])
    assert r_active.status_code == 200
    names = [p["name"] for p in r_active.json()["items"]]
    assert "Active Plan" in names
    assert "Inactive Plan" not in names

    # With include_inactive=true
    r_all = client.get("/api/v1/membership-plans?include_inactive=true", headers=registered_gym["headers"])
    assert r_all.status_code == 200
    all_names = [p["name"] for p in r_all.json()["items"]]
    assert "Active Plan" in all_names
    assert "Inactive Plan" in all_names


def test_get_and_update_membership_plan(client: TestClient, registered_gym):
    """Test retrieving and updating an existing membership plan."""
    created = client.post(
        "/api/v1/membership-plans",
        json={"name": "Before Update", "duration": 1, "duration_unit": "MONTHS", "price": 1200.00},
        headers=registered_gym["headers"],
    ).json()

    # Get by ID
    get_resp = client.get(f"/api/v1/membership-plans/{created['id']}", headers=registered_gym["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Before Update"

    # Update
    update_resp = client.put(
        f"/api/v1/membership-plans/{created['id']}",
        json={"name": "After Update", "price": 1400.00},
        headers=registered_gym["headers"],
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "After Update"
    assert float(update_resp.json()["price"]) == 1400.00


def test_deactivate_membership_plan(client: TestClient, registered_gym):
    """Test soft-deactivation of a membership plan."""
    created = client.post(
        "/api/v1/membership-plans",
        json={"name": "To Deactivate", "duration": 1, "duration_unit": "MONTHS", "price": 800.00},
        headers=registered_gym["headers"],
    ).json()

    del_resp = client.delete(f"/api/v1/membership-plans/{created['id']}", headers=registered_gym["headers"])
    assert del_resp.status_code == 200
    assert "deactivated" in del_resp.json()["message"]

    # Verify is_active changed to False
    get_resp = client.get(f"/api/v1/membership-plans/{created['id']}", headers=registered_gym["headers"])
    assert get_resp.json()["is_active"] is False


def test_tenant_isolation_plans(client: TestClient, registered_gym, second_registered_gym):
    """Gym 2 cannot view, update or deactivate Gym 1's plans."""
    plan1 = client.post(
        "/api/v1/membership-plans",
        json={"name": "Gym 1 Confidential Plan", "duration": 1, "duration_unit": "MONTHS", "price": 3000.00},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to GET -> 404
    assert client.get(f"/api/v1/membership-plans/{plan1['id']}", headers=second_registered_gym["headers"]).status_code == 404

    # Gym 2 tries to PUT -> 404
    assert client.put(
        f"/api/v1/membership-plans/{plan1['id']}",
        json={"name": "Tampered"},
        headers=second_registered_gym["headers"],
    ).status_code == 404

    # Gym 2 tries to DELETE -> 404
    assert client.delete(f"/api/v1/membership-plans/{plan1['id']}", headers=second_registered_gym["headers"]).status_code == 404


def test_rbac_membership_plans(client: TestClient, gym_with_roles):
    """
    Test RBAC authorization for Membership Plans:
    - FRONT_DESK can VIEW plans (GET).
    - FRONT_DESK CANNOT create, update or deactivate plans (403 Forbidden).
    - MANAGER and OWNER CAN create, update and deactivate plans.
    """
    headers_desk = gym_with_roles["front_desk_headers"]
    headers_mgr = gym_with_roles["manager_headers"]

    # MANAGER creates plan -> 201
    mgr_plan = client.post(
        "/api/v1/membership-plans",
        json={"name": "Manager Created Plan", "duration": 1, "duration_unit": "MONTHS", "price": 1500.00},
        headers=headers_mgr,
    )
    assert mgr_plan.status_code == 201
    plan_id = mgr_plan.json()["id"]

    # FRONT_DESK can VIEW plans -> 200
    assert client.get("/api/v1/membership-plans", headers=headers_desk).status_code == 200
    assert client.get(f"/api/v1/membership-plans/{plan_id}", headers=headers_desk).status_code == 200

    # FRONT_DESK attempts to CREATE plan -> 403 Forbidden
    resp_desk_create = client.post(
        "/api/v1/membership-plans",
        json={"name": "Desk Rogue Plan", "duration": 1, "duration_unit": "MONTHS", "price": 500.00},
        headers=headers_desk,
    )
    assert resp_desk_create.status_code == 403

    # FRONT_DESK attempts to UPDATE plan -> 403 Forbidden
    resp_desk_put = client.put(
        f"/api/v1/membership-plans/{plan_id}",
        json={"price": 100.00},
        headers=headers_desk,
    )
    assert resp_desk_put.status_code == 403

    # FRONT_DESK attempts to DEACTIVATE plan -> 403 Forbidden
    resp_desk_del = client.delete(f"/api/v1/membership-plans/{plan_id}", headers=headers_desk)
    assert resp_desk_del.status_code == 403


def test_plan_duration_and_price_overflow_protection(client: TestClient, registered_gym):
    """Excessive durations and numeric price overflow must be rejected with 422."""
    headers = registered_gym["headers"]

    # Duration > 3650
    resp_dur = client.post(
        "/api/v1/membership-plans",
        json={"name": "Century Plan", "duration": 5000, "duration_unit": "DAYS", "price": 1000.00},
        headers=headers,
    )
    assert resp_dur.status_code == 422

    # Price exceeding 99,999,999.99
    resp_overflow = client.post(
        "/api/v1/membership-plans",
        json={"name": "Billionaire Plan", "duration": 1, "duration_unit": "MONTHS", "price": 1000000000.00},
        headers=headers,
    )
    assert resp_overflow.status_code == 422


def test_plan_explicit_null_updates_rejected(client: TestClient, registered_gym):
    """Supplying null for non-nullable plan fields during update must fail with 422."""
    headers = registered_gym["headers"]
    plan = client.post(
        "/api/v1/membership-plans",
        json={"name": "Standard Plan", "duration": 1, "duration_unit": "MONTHS", "price": 1000.00},
        headers=headers,
    ).json()

    for field in ["name", "duration", "price", "duration_unit", "is_active"]:
        resp = client.put(
            f"/api/v1/membership-plans/{plan['id']}",
            json={field: None},
            headers=headers,
        )
        assert resp.status_code == 422, f"Expected 422 when setting {field} to null, got {resp.status_code}"

