"""Comprehensive tests for Member Management module."""
import random
import uuid
from fastapi.testclient import TestClient


def _random_phone() -> str:
    """Generate a valid numeric phone number for tests."""
    return f"+9198{random.randint(10000000, 99999999)}"


def test_member_registration_all_fields(client: TestClient, registered_gym):
    """Test registering a new member with full profile details."""
    payload = {
        "full_name": "Rohan Sharma",
        "email": f"rohan_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "+919876543210",
        "gender": "MALE",
        "date_of_birth": "1995-05-15",
        "address": "42 Richmond Road, Bangalore",
        "emergency_contact_name": "Priya Sharma",
        "emergency_contact_phone": "+919876543211",
        "status": "ACTIVE",
    }
    resp = client.post("/api/v1/members", json=payload, headers=registered_gym["headers"])
    assert resp.status_code == 201, f"Failed: {resp.text}"
    data = resp.json()

    assert data["full_name"] == "Rohan Sharma"
    assert data["email"] == payload["email"]
    assert data["phone"] == "+919876543210"
    assert data["gender"] == "MALE"
    assert data["date_of_birth"] == "1995-05-15"
    assert data["address"] == "42 Richmond Road, Bangalore"
    assert data["emergency_contact_name"] == "Priya Sharma"
    assert data["emergency_contact_phone"] == "+919876543211"
    assert data["status"] == "ACTIVE"
    assert data["tenant_id"] == str(registered_gym["tenant_id"])
    assert "id" in data


def test_member_registration_minimal_fields(client: TestClient, registered_gym):
    """Test registering a member with only the mandatory full_name field."""
    payload = {"full_name": "Anita Desai"}
    resp = client.post("/api/v1/members", json=payload, headers=registered_gym["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Anita Desai"
    assert data["status"] == "ACTIVE"
    assert data["email"] is None
    assert data["phone"] is None


def test_prevent_duplicate_member_phone_same_gym(client: TestClient, registered_gym):
    """Duplicate phone within the same gym facility must be rejected with HTTP 409."""
    phone = _random_phone()
    payload1 = {"full_name": "First Member", "phone": phone}
    resp1 = client.post("/api/v1/members", json=payload1, headers=registered_gym["headers"])
    assert resp1.status_code == 201, f"Expected 201, got {resp1.status_code}: {resp1.text}"

    payload2 = {"full_name": "Second Member", "phone": phone}
    resp2 = client.post("/api/v1/members", json=payload2, headers=registered_gym["headers"])
    assert resp2.status_code == 409
    assert "already exists in this gym" in resp2.json()["detail"]


def test_prevent_duplicate_member_email_same_gym(client: TestClient, registered_gym):
    """Duplicate email within the same gym facility must be rejected with HTTP 409."""
    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
    payload1 = {"full_name": "Member A", "email": email}
    resp1 = client.post("/api/v1/members", json=payload1, headers=registered_gym["headers"])
    assert resp1.status_code == 201

    payload2 = {"full_name": "Member B", "email": email}
    resp2 = client.post("/api/v1/members", json=payload2, headers=registered_gym["headers"])
    assert resp2.status_code == 409
    assert "already exists in this gym" in resp2.json()["detail"]


def test_allow_same_member_phone_across_different_tenants(
    client: TestClient, registered_gym, second_registered_gym
):
    """Same phone number used across different gyms must be allowed (tenant isolation)."""
    shared_phone = _random_phone()

    # Gym 1 registers member
    resp1 = client.post(
        "/api/v1/members",
        json={"full_name": "Gym 1 Member", "phone": shared_phone},
        headers=registered_gym["headers"],
    )
    assert resp1.status_code == 201

    # Gym 2 registers member with identical phone
    resp2 = client.post(
        "/api/v1/members",
        json={"full_name": "Gym 2 Member", "phone": shared_phone},
        headers=second_registered_gym["headers"],
    )
    assert resp2.status_code == 201
    assert resp1.json()["id"] != resp2.json()["id"]


def test_list_members_and_pagination(client: TestClient, registered_gym):
    """Test paginated member retrieval."""
    # Seed 3 members
    for i in range(3):
        create_resp = client.post(
            "/api/v1/members",
            json={"full_name": f"Paging Test Member {i}", "phone": _random_phone()},
            headers=registered_gym["headers"],
        )
        assert create_resp.status_code == 201, f"Seed member failed: {create_resp.text}"

    resp = client.get("/api/v1/members?page=1&page_size=2", headers=registered_gym["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] >= 3
    assert data["pages"] >= 2


def test_search_members(client: TestClient, registered_gym):
    """Test member search by name, email, and phone."""
    uniq = uuid.uuid4().hex[:6]
    search_name = f"Kavita Unique_{uniq}"
    search_email = f"kavita_{uniq}@unique.org"
    search_phone = _random_phone()

    create_resp = client.post(
        "/api/v1/members",
        json={"full_name": search_name, "email": search_email, "phone": search_phone},
        headers=registered_gym["headers"],
    )
    assert create_resp.status_code == 201, f"Seed failed: {create_resp.text}"

    # Search by name
    r_name = client.get("/api/v1/members/search", params={"q": uniq}, headers=registered_gym["headers"])
    assert r_name.status_code == 200
    assert any(m["full_name"] == search_name for m in r_name.json()["items"])

    # Search by phone
    r_phone = client.get("/api/v1/members/search", params={"q": search_phone}, headers=registered_gym["headers"])
    assert r_phone.status_code == 200
    assert any(m["phone"] == search_phone for m in r_phone.json()["items"])


def test_get_member_profile(client: TestClient, registered_gym):
    """Test retrieving a member's full profile by member ID."""
    create_resp = client.post(
        "/api/v1/members",
        json={"full_name": "Deepak Verma", "address": "Indiranagar"},
        headers=registered_gym["headers"],
    )
    assert create_resp.status_code == 201
    member_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/members/{member_id}", headers=registered_gym["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == member_id
    assert data["full_name"] == "Deepak Verma"
    assert data["address"] == "Indiranagar"


def test_update_member(client: TestClient, registered_gym):
    """Test updating member profile fields."""
    create_resp = client.post(
        "/api/v1/members",
        json={"full_name": "Original Name", "phone": _random_phone()},
        headers=registered_gym["headers"],
    )
    assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
    member_id = create_resp.json()["id"]

    update_payload = {
        "full_name": "Updated Name",
        "address": "New Gym Colony",
        "emergency_contact_name": "Dr. Smith",
    }
    update_resp = client.put(
        f"/api/v1/members/{member_id}",
        json=update_payload,
        headers=registered_gym["headers"],
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["full_name"] == "Updated Name"
    assert data["address"] == "New Gym Colony"
    assert data["emergency_contact_name"] == "Dr. Smith"


def test_update_member_duplicate_phone_rejected(client: TestClient, registered_gym):
    """Updating a member's phone to one already used by another member must fail with 409."""
    phone1 = _random_phone()
    phone2 = _random_phone()

    r1 = client.post("/api/v1/members", json={"full_name": "M1", "phone": phone1}, headers=registered_gym["headers"])
    assert r1.status_code == 201
    m1 = r1.json()

    r2 = client.post("/api/v1/members", json={"full_name": "M2", "phone": phone2}, headers=registered_gym["headers"])
    assert r2.status_code == 201
    m2 = r2.json()

    # Attempt to change M2's phone to M1's phone
    resp = client.put(f"/api/v1/members/{m2['id']}", json={"phone": phone1}, headers=registered_gym["headers"])
    assert resp.status_code == 409


def test_delete_member_soft_deactivation(client: TestClient, registered_gym):
    """Soft deletion sets member status to INACTIVE and preserves history."""
    m = client.post(
        "/api/v1/members",
        json={"full_name": "To Deactivate"},
        headers=registered_gym["headers"],
    ).json()

    del_resp = client.delete(f"/api/v1/members/{m['id']}", headers=registered_gym["headers"])
    assert del_resp.status_code == 200
    assert "deactivated successfully" in del_resp.json()["message"]

    # Verify status changed to INACTIVE
    get_resp = client.get(f"/api/v1/members/{m['id']}", headers=registered_gym["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "INACTIVE"


def test_tenant_isolation_members(client: TestClient, registered_gym, second_registered_gym):
    """Ensure Tenant A cannot view, edit, or delete Tenant B's member."""
    # Member created by Gym 1
    m1 = client.post(
        "/api/v1/members",
        json={"full_name": "Gym 1 Secret Member"},
        headers=registered_gym["headers"],
    ).json()

    # Gym 2 tries to GET Gym 1's member -> 404
    resp_get = client.get(f"/api/v1/members/{m1['id']}", headers=second_registered_gym["headers"])
    assert resp_get.status_code == 404

    # Gym 2 tries to PUT Gym 1's member -> 404
    resp_put = client.put(
        f"/api/v1/members/{m1['id']}",
        json={"full_name": "Hijacked"},
        headers=second_registered_gym["headers"],
    )
    assert resp_put.status_code == 404

    # Gym 2 tries to DELETE Gym 1's member -> 404
    resp_del = client.delete(f"/api/v1/members/{m1['id']}", headers=second_registered_gym["headers"])
    assert resp_del.status_code == 404


def test_rbac_member_management(client: TestClient, gym_with_roles):
    """
    Test RBAC authorization matrix:
    - FRONT_DESK can register and update members.
    - FRONT_DESK cannot delete/deactivate members (403 Forbidden).
    - MANAGER and OWNER can delete members.
    """
    headers_desk = gym_with_roles["front_desk_headers"]
    headers_mgr = gym_with_roles["manager_headers"]

    # FRONT_DESK creates member -> 201
    resp_create = client.post(
        "/api/v1/members",
        json={"full_name": "Front Desk Registration"},
        headers=headers_desk,
    )
    assert resp_create.status_code == 201
    member_id = resp_create.json()["id"]

    # FRONT_DESK updates member -> 200
    resp_update = client.put(
        f"/api/v1/members/{member_id}",
        json={"address": "Updated by Desk"},
        headers=headers_desk,
    )
    assert resp_update.status_code == 200

    # FRONT_DESK tries to delete member -> 403 Forbidden
    resp_del_desk = client.delete(f"/api/v1/members/{member_id}", headers=headers_desk)
    assert resp_del_desk.status_code == 403

    # MANAGER deletes member -> 200
    resp_del_mgr = client.delete(f"/api/v1/members/{member_id}", headers=headers_mgr)
    assert resp_del_mgr.status_code == 200


def test_member_future_dob_rejected(client: TestClient, registered_gym):
    """Registering a member with a future date of birth must fail with 422."""
    resp = client.post(
        "/api/v1/members",
        json={"full_name": "Time Traveler", "date_of_birth": "2099-01-01"},
        headers=registered_gym["headers"],
    )
    assert resp.status_code == 422
    assert "date of birth cannot be in the future" in resp.text.lower()


def test_member_invalid_phone_rejected(client: TestClient, registered_gym):
    """Invalid phone number formats must fail validation with 422."""
    bad_phones = ["123", "abc1234567", "++9188888888888888888888888888888888888888888"]
    for bad_phone in bad_phones:
        resp = client.post(
            "/api/v1/members",
            json={"full_name": "Bad Phone", "phone": bad_phone},
            headers=registered_gym["headers"],
        )
        assert resp.status_code == 422, f"Expected 422 for phone '{bad_phone}', got {resp.status_code}"


def test_member_lifecycle_status_cannot_be_set_by_client(client: TestClient, registered_gym):
    """Clients cannot arbitrarily dictate lifecycle status upon registration or update."""
    # Attempt to create with EXPIRED status -> 422
    resp_create = client.post(
        "/api/v1/members",
        json={"full_name": "Client Hack", "status": "EXPIRED"},
        headers=registered_gym["headers"],
    )
    assert resp_create.status_code == 422

    # Create legitimate member
    valid_resp = client.post(
        "/api/v1/members",
        json={"full_name": "Valid Member"},
        headers=registered_gym["headers"],
    )
    assert valid_resp.status_code == 201
    member_id = valid_resp.json()["id"]

    # Attempt to PUT status to SUSPENDED -> 422
    resp_update = client.put(
        f"/api/v1/members/{member_id}",
        json={"status": "SUSPENDED"},
        headers=registered_gym["headers"],
    )
    assert resp_update.status_code == 422


def test_member_explicit_null_updates(client: TestClient, registered_gym):
    """Supplying null for non-nullable fields must fail; null for optional fields is allowed."""
    create_resp = client.post(
        "/api/v1/members",
        json={
            "full_name": "Original Person",
            "emergency_contact_name": "Initial Contact",
        },
        headers=registered_gym["headers"],
    )
    assert create_resp.status_code == 201
    member_id = create_resp.json()["id"]

    # Attempt to set full_name to None -> 422
    null_name_resp = client.put(
        f"/api/v1/members/{member_id}",
        json={"full_name": None},
        headers=registered_gym["headers"],
    )
    assert null_name_resp.status_code == 422

    # Successfully clear optional emergency_contact_name
    clear_resp = client.put(
        f"/api/v1/members/{member_id}",
        json={"emergency_contact_name": None},
        headers=registered_gym["headers"],
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["emergency_contact_name"] is None
