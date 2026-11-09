import uuid
from datetime import timedelta
from unittest.mock import patch
from fastapi import HTTPException
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import enforce_tenant_isolation, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole


def test_1_successful_registration(client: TestClient, unique_email: str):
    """Test 1: Register a new gym tenant and initial owner account."""
    payload = {
        "gym_name": "Iron Pulse Fitness",
        "name": "Alex Mercer",
        "email": unique_email,
        "password": "StrongPassword123!",
        "phone": "+919876543210",
        "address": "123 MG Road, Bangalore",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["tenant"]["name"] == "Iron Pulse Fitness"
    assert data["tenant"]["timezone"] == "Asia/Kolkata"
    assert data["tenant"]["currency"] == "INR"
    assert data["user"]["email"] == unique_email.lower()
    assert data["user"]["role"] == "OWNER"
    assert data["user"]["is_active"] is True
    # Ensure password_hash is never exposed
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


def test_2_duplicate_email_registration_rejected(client: TestClient, unique_email: str):
    """Test 2: Prevent duplicate registration with already registered email."""
    payload = {
        "gym_name": "First Gym",
        "name": "First Owner",
        "email": unique_email,
        "password": "ValidPassword123!",
    }
    # Initial registration
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    # Duplicate attempt
    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"].lower()


def test_3_successful_login(client: TestClient, unique_email: str):
    """Test 3: Authenticate valid user and retrieve JWT token."""
    password = "CorrectPassword123!"
    # Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Titan Gym",
            "name": "Titan Owner",
            "email": unique_email,
            "password": password,
        },
    )
    assert reg_resp.status_code == 201

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == unique_email.lower()
    assert data["user"]["role"] == "OWNER"
    assert "password_hash" not in data["user"]


def test_4_incorrect_password_rejected(client: TestClient, unique_email: str):
    """Test 4: Reject login attempt with wrong password."""
    client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Delta Fitness",
            "name": "Delta Owner",
            "email": unique_email,
            "password": "CorrectPassword123!",
        },
    )

    # Attempt with incorrect password
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "WrongPassword999!"},
    )
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()


def test_5_missing_and_invalid_jwt_rejected(client: TestClient):
    """Test 5: Reject requests with missing, malformed, or expired JWTs."""
    # Missing Authorization header
    resp_no_token = client.get("/api/v1/auth/me")
    assert resp_no_token.status_code in (401, 403)

    # Invalid token string
    resp_bad_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not_a_valid_token_xyz"},
    )
    assert resp_bad_token.status_code == 401

    # Expired token
    expired_token = create_access_token(
        {"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()), "role": "OWNER"},
        expires_delta=timedelta(seconds=-10),
    )
    resp_expired = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp_expired.status_code == 401
    assert "expired" in resp_expired.json()["detail"].lower()


def test_6_auth_me_with_valid_token(client: TestClient, unique_email: str):
    """Test 6: Retrieve /auth/me profile with verified JWT token."""
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Zenith Gym",
            "name": "Zenith Owner",
            "email": unique_email,
            "password": "Password1234!",
        },
    )
    token = reg_resp.json()["access_token"]

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    me_data = resp.json()
    assert me_data["email"] == unique_email.lower()
    assert me_data["name"] == "Zenith Owner"
    assert me_data["role"] == "OWNER"
    assert "password_hash" not in me_data


def test_7_role_authorization_behavior(client: TestClient, db: Session, unique_email: str):
    """Test 7: Verify RBAC role guards (OWNER allowed, FRONT_DESK denied)."""
    # 1. Register OWNER
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "RBAC Test Gym",
            "name": "Owner User",
            "email": unique_email,
            "password": "Password123!",
        },
    )
    owner_token = reg_resp.json()["access_token"]
    tenant_id = uuid.UUID(reg_resp.json()["tenant"]["id"])

    # Owner accesses owner-only endpoint -> 200 OK
    resp_owner = client.get(
        "/api/v1/auth/test-owner-only",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_owner.status_code == 200
    assert resp_owner.json()["role"] == "OWNER"

    # 2. Create FRONT_DESK user within same tenant
    front_desk_email = f"frontdesk_{uuid.uuid4().hex[:8]}@gymcoretest.com"
    fd_user = User(
        tenant_id=tenant_id,
        name="Front Desk Staff",
        email=front_desk_email,
        password_hash=hash_password("StaffPass123!"),
        role=UserRole.FRONT_DESK,
        is_active=True,
    )
    db.add(fd_user)
    db.commit()
    db.refresh(fd_user)

    fd_token = create_access_token({
        "sub": str(fd_user.id),
        "tenant_id": str(tenant_id),
        "role": fd_user.role.value,
    })

    # FRONT_DESK accesses owner-only endpoint -> 403 Forbidden
    resp_fd_blocked = client.get(
        "/api/v1/auth/test-owner-only",
        headers={"Authorization": f"Bearer {fd_token}"},
    )
    assert resp_fd_blocked.status_code == 403
    assert "required role" in resp_fd_blocked.json()["detail"].lower()

    # FRONT_DESK accesses manager-only endpoint -> 403 Forbidden
    resp_fd_mgr = client.get(
        "/api/v1/auth/test-manager-only",
        headers={"Authorization": f"Bearer {fd_token}"},
    )
    assert resp_fd_mgr.status_code == 403


def test_8_tenant_isolation_behavior(client: TestClient, db: Session, unique_email: str):
    """Test 8: Verify tenant isolation guards and spoofing prevention."""
    # Register Tenant A
    reg_a = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Tenant A Gym",
            "name": "Owner A",
            "email": unique_email,
            "password": "Password123!",
        },
    )
    user_a_id = uuid.UUID(reg_a.json()["user"]["id"])
    tenant_a_id = uuid.UUID(reg_a.json()["tenant"]["id"])
    token_a = reg_a.json()["access_token"]

    user_a = db.query(User).filter(User.id == user_a_id).first()
    assert user_a is not None

    # 1. Dependency helper enforce_tenant_isolation
    # Allowed: User A accesses Tenant A resource
    enforce_tenant_isolation(tenant_a_id, user_a)

    # Forbidden: User A attempts to access Tenant B resource
    alien_tenant_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_isolation(alien_tenant_id, user_a)
    assert exc_info.value.status_code == 403
    assert "another tenant" in exc_info.value.detail

    # 2. Spoofing test: Craft token with user_a_id but alien tenant_id
    spoofed_token = create_access_token({
        "sub": str(user_a_id),
        "tenant_id": str(alien_tenant_id),  # Spoofed!
        "role": "OWNER",
    })
    resp_spoof = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {spoofed_token}"},
    )
    assert resp_spoof.status_code == 401
    assert "tenant context mismatch" in resp_spoof.json()["detail"].lower()


def test_auth_invalid_email_formats_rejected(client: TestClient):
    """Test invalid email formats are rejected with 422 on register and login."""
    bad_emails = ["notanemail", "missing@domain", "@nodomain.com", "spaces in@email.com"]
    for bad_email in bad_emails:
        reg_resp = client.post(
            "/api/v1/auth/register",
            json={
                "gym_name": "Test Gym",
                "name": "Owner",
                "email": bad_email,
                "password": "Password123!",
            },
        )
        assert reg_resp.status_code == 422, f"Expected 422 for bad email '{bad_email}', got {reg_resp.status_code}"

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": bad_email, "password": "Password123!"},
        )
        assert login_resp.status_code == 422, f"Expected 422 for login bad email '{bad_email}', got {login_resp.status_code}"


def test_auth_email_normalization(client: TestClient):
    """Verify email normalization works across case variations on register and login."""
    suffix = uuid.uuid4().hex[:6]
    mixed_email = f"MiXeD_{suffix}@ExAmPlE.CoM"
    password = "SecurePassword123!"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Case Gym",
            "name": "Owner",
            "email": mixed_email,
            "password": password,
        },
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert data["user"]["email"] == mixed_email.lower()

    # Login with all uppercase
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": mixed_email.upper(), "password": password},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == mixed_email.lower()


def test_auth_password_exceeding_bcrypt_72_bytes_rejected(client: TestClient):
    """Passwords exceeding the 72-byte bcrypt limit must be rejected with 422."""
    long_password = "A" * 73
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Long Password Gym",
            "name": "Owner",
            "email": f"longpass_{uuid.uuid4().hex[:6]}@example.com",
            "password": long_password,
        },
    )
    assert resp.status_code == 422
    assert "72 bytes" in resp.text


def test_auth_inactive_account_rejected(client: TestClient, db: Session, unique_email: str):
    """Inactive accounts must be rejected with 403 on login and on token authentication."""
    password = "ActivePassword123!"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": "Inactive Account Gym",
            "name": "Owner",
            "email": unique_email,
            "password": password,
        },
    )
    assert reg_resp.status_code == 201
    user_id = uuid.UUID(reg_resp.json()["user"]["id"])
    token = reg_resp.json()["access_token"]

    # Deactivate the account in the database
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    user.is_active = False
    db.commit()

    # Attempt to login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 403
    assert "deactivated" in login_resp.json()["detail"].lower()

    # Attempt to use existing token
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 403
    assert "inactive" in me_resp.json()["detail"].lower()


def test_auth_invalid_and_expired_tokens(client: TestClient, registered_gym):
    """Expired or malformed tokens must return 401 Unauthorized."""
    # 1. Expired token
    expired_token = create_access_token(
        {"sub": str(registered_gym["owner_id"]), "tenant_id": str(registered_gym["tenant_id"]), "role": "OWNER"},
        expires_delta=timedelta(minutes=-10),
    )
    resp_exp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_exp.status_code == 401
    assert "expired" in resp_exp.json()["detail"].lower()

    # 2. Tampered / invalid signature token
    tampered_token = expired_token[:-5] + "XXXXX"
    resp_tampered = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp_tampered.status_code == 401

    # 3. Malformed token string
    resp_malformed = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp_malformed.status_code == 401


# =====================================================================
# 15 MANDATORY REGISTRATION & MULTI-TENANT ISOLATION ACCEPTANCE TESTS
# =====================================================================

def test_reg_01_successful_gym_registration(client: TestClient, unique_email: str):
    """Requirement 1: Successful gym registration with valid payload returns 201 and JWT."""
    payload = {
        "gym_name": "Titanium Fitness Club",
        "name": "Vikram Malhotra",
        "email": unique_email,
        "password": "SecurePassword123!",
        "phone": "+919876543210",
        "address": "45 Indiranagar, Bangalore",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["tenant"]["name"] == "Titanium Fitness Club"
    assert data["tenant"]["timezone"] == "Asia/Kolkata"
    assert data["tenant"]["currency"] == "INR"
    assert data["user"]["email"] == unique_email.lower()


def test_reg_02_successful_owner_creation(client: TestClient, db: Session, unique_email: str):
    """Requirement 2: Successful owner user creation in database linked to tenant."""
    payload = {
        "gym_name": "Apex Gym",
        "name": "Apex Owner",
        "email": unique_email,
        "password": "ApexPassword123!",
        "phone": "+919811122233",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    user_id = uuid.UUID(response.json()["user"]["id"])
    tenant_id = uuid.UUID(response.json()["tenant"]["id"])

    # Query DB directly to verify persistence
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    assert user.tenant_id == tenant_id
    assert user.name == "Apex Owner"
    assert user.email == unique_email.lower()
    assert user.is_active is True


def test_reg_03_owner_role_assigned_automatically(client: TestClient, db: Session, unique_email: str):
    """Requirement 3: Newly registered user is automatically assigned OWNER role."""
    payload = {
        "gym_name": "Autonomy Gym",
        "name": "Auto Owner",
        "email": unique_email,
        "password": "AutoPassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "OWNER"

    user_id = uuid.UUID(response.json()["user"]["id"])
    user = db.query(User).filter(User.id == user_id).first()
    assert user.role == UserRole.OWNER


def test_reg_04_password_stored_as_bcrypt_hash(client: TestClient, db: Session, unique_email: str):
    """Requirement 4: Password is never stored in plaintext and is hashed with bcrypt."""
    plaintext = "PlainTextPass123!"
    payload = {
        "gym_name": "Crypto Gym",
        "name": "Crypto Owner",
        "email": unique_email,
        "password": plaintext,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    user_id = uuid.UUID(response.json()["user"]["id"])
    user = db.query(User).filter(User.id == user_id).first()
    assert user.password_hash != plaintext
    assert user.password_hash.startswith(("$2b$", "$2a$", "$2y$"))
    assert verify_password(plaintext, user.password_hash) is True


def test_reg_05_duplicate_email_rejection(client: TestClient, unique_email: str):
    """Requirement 5: Duplicate email registration rejected with 400 Bad Request."""
    payload = {
        "gym_name": "Original Gym",
        "name": "Original Owner",
        "email": unique_email,
        "password": "OriginalPassword123!",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400
    assert "already registered" in r2.json()["detail"].lower()


def test_reg_06_invalid_email_rejection(client: TestClient):
    """Requirement 6: Invalid email format rejected with 422 Unprocessable Entity."""
    invalid_emails = ["notanemail", "plainword", "@missingusername.com", "missingdot@com"]
    for bad_email in invalid_emails:
        payload = {
            "gym_name": "Invalid Email Gym",
            "name": "Bad Owner",
            "email": bad_email,
            "password": "ValidPassword123!",
        }
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 422


def test_reg_07_missing_required_fields_rejection(client: TestClient):
    """Requirement 7: Missing required fields rejected with 422 Unprocessable Entity."""
    # Missing gym_name
    r1 = client.post("/api/v1/auth/register", json={
        "name": "Owner", "email": "valid@example.com", "password": "Password123!"
    })
    assert r1.status_code == 422

    # Missing name
    r2 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym", "email": "valid@example.com", "password": "Password123!"
    })
    assert r2.status_code == 422

    # Missing email
    r3 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym", "name": "Owner", "password": "Password123!"
    })
    assert r3.status_code == 422

    # Missing password
    r4 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym", "name": "Owner", "email": "valid@example.com"
    })
    assert r4.status_code == 422


def test_reg_08_password_validation_lengths(client: TestClient):
    """Requirement 8: Password validation enforcing minimum 8 chars and maximum 72 bytes."""
    # Under 8 chars
    r_short = client.post("/api/v1/auth/register", json={
        "gym_name": "Short Gym",
        "name": "Short Owner",
        "email": f"short_{uuid.uuid4().hex[:6]}@example.com",
        "password": "short",
    })
    assert r_short.status_code == 422

    # Over 72 bytes
    r_long = client.post("/api/v1/auth/register", json={
        "gym_name": "Long Gym",
        "name": "Long Owner",
        "email": f"long_{uuid.uuid4().hex[:6]}@example.com",
        "password": "X" * 73,
    })
    assert r_long.status_code == 422


def test_reg_09_tenant_creation_rollback_on_user_creation_failure(client: TestClient, db: Session):
    """Requirement 9: Tenant creation is rolled back if owner creation fails (atomic transaction)."""
    gym_name = f"Rollback Gym {uuid.uuid4().hex[:6]}"
    with patch("app.api.v1.endpoints.auth.hash_password", side_effect=RuntimeError("Simulated hash failure")):
        with pytest.raises(RuntimeError):
            client.post("/api/v1/auth/register", json={
                "gym_name": gym_name,
                "name": "Rollback Owner",
                "email": f"rollback_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Password123!",
            })
    # Verify tenant was rolled back and is not persisted in DB
    tenant = db.query(Tenant).filter(Tenant.name == gym_name).first()
    assert tenant is None, "Tenant must be rolled back if owner creation fails"


def test_reg_10_successful_login_after_registration(client: TestClient, unique_email: str):
    """Requirement 10: Successful login after registration using registered credentials."""
    password = "CorrectLoginPass123!"
    reg_res = client.post("/api/v1/auth/register", json={
        "gym_name": "Login Test Gym",
        "name": "Login Owner",
        "email": unique_email,
        "password": password,
    })
    assert reg_res.status_code == 201

    login_res = client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": password,
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == unique_email.lower()
    assert data["user"]["role"] == "OWNER"


def test_reg_11_jwt_authentication_after_login(client: TestClient, unique_email: str):
    """Requirement 11: JWT authentication against /auth/me after login returns valid profile."""
    password = "AuthMePassword123!"
    reg_res = client.post("/api/v1/auth/register", json={
        "gym_name": "Auth Me Gym",
        "name": "Auth Me Owner",
        "email": unique_email,
        "password": password,
    })
    assert reg_res.status_code == 201

    login_res = client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": password,
    })
    token = login_res.json()["access_token"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["email"] == unique_email.lower()
    assert profile["role"] == "OWNER"
    assert profile["name"] == "Auth Me Owner"
    assert "password_hash" not in profile


def test_reg_12_new_tenant_zero_business_records(client: TestClient, unique_email: str):
    """Requirement 12: Newly registered tenant starts with exactly zero members, payments, and attendance."""
    reg_res = client.post("/api/v1/auth/register", json={
        "gym_name": "Fresh Slate Gym",
        "name": "Clean Owner",
        "email": unique_email,
        "password": "CleanPassword123!",
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query Member API
    m_res = client.get("/api/v1/members", headers=headers)
    assert m_res.status_code == 200
    m_data = m_res.json()
    items = m_data.get("items", m_data if isinstance(m_data, list) else [])
    assert len(items) == 0

    # Query Payment API
    p_res = client.get("/api/v1/payments", headers=headers)
    assert p_res.status_code == 200
    p_data = p_res.json()
    p_items = p_data.get("items", p_data if isinstance(p_data, list) else [])
    assert len(p_items) == 0

    # Query Attendance API
    a_res = client.get("/api/v1/attendance", headers=headers)
    assert a_res.status_code == 200
    a_data = a_res.json()
    a_items = a_data.get("items", a_data if isinstance(a_data, list) else [])
    assert len(a_items) == 0


def test_reg_13_two_gyms_have_different_tenant_ids(client: TestClient):
    """Requirement 13: Multiple gyms registered receive strictly distinct tenant IDs."""
    r1 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym Alpha",
        "name": "Owner Alpha",
        "email": f"alpha_{uuid.uuid4().hex[:6]}@example.com",
        "password": "PasswordAlpha123!",
    })
    r2 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym Beta",
        "name": "Owner Beta",
        "email": f"beta_{uuid.uuid4().hex[:6]}@example.com",
        "password": "PasswordBeta123!",
    })
    assert r1.status_code == 201
    assert r2.status_code == 201

    tenant_a = r1.json()["tenant"]["id"]
    tenant_b = r2.json()["tenant"]["id"]
    user_a = r1.json()["user"]["id"]
    user_b = r2.json()["user"]["id"]

    assert tenant_a != tenant_b
    assert user_a != user_b


def test_reg_14_cross_tenant_access_rejected(client: TestClient):
    """Requirement 14: Cross-tenant access is rejected when tenant ID is spoofed."""
    r1 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym South",
        "name": "Owner South",
        "email": f"south_{uuid.uuid4().hex[:6]}@example.com",
        "password": "SouthPassword123!",
    })
    r2 = client.post("/api/v1/auth/register", json={
        "gym_name": "Gym North",
        "name": "Owner North",
        "email": f"north_{uuid.uuid4().hex[:6]}@example.com",
        "password": "NorthPassword123!",
    })
    user_south_id = r1.json()["user"]["id"]
    tenant_north_id = r2.json()["tenant"]["id"]

    # Spoofed token: User South attempting to operate under Tenant North's ID
    spoofed_token = create_access_token({
        "sub": user_south_id,
        "tenant_id": tenant_north_id,
        "role": "OWNER",
    })
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {spoofed_token}"})
    assert resp.status_code == 401
    assert "tenant context mismatch" in resp.json()["detail"].lower()


def test_reg_15_public_registration_cannot_create_manager_or_front_desk(client: TestClient, db: Session):
    """Requirement 15: Public registration cannot create MANAGER or FRONT_DESK accounts."""
    email = f"sneaky_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "gym_name": "Sneaky Gym",
        "name": "Sneaky User",
        "email": email,
        "password": "SneakyPassword123!",
        "role": "MANAGER",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    if res.status_code == 201:
        # Pydantic may ignore extra fields; verify the created user role is strictly OWNER
        assert res.json()["user"]["role"] == "OWNER"
        user = db.query(User).filter(User.email == email.lower()).first()
        assert user.role == UserRole.OWNER
    else:
        # Or schema rejects extra field
        assert res.status_code == 422


# =====================================================================
# CORS PRODUCTION & LOCALHOST VERIFICATION TESTS
# =====================================================================

def test_cors_vercel_production_origin_allowed(client: TestClient):
    """Verify that production Vercel frontend origin receives valid CORS headers."""
    vercel_origin = "https://zencro-gym-core.vercel.app"
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": vercel_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == vercel_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_localhost_allowed(client: TestClient):
    """Verify that local development origins remain permitted for development."""
    local_origin = "http://localhost:3000"
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": local_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == local_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_unauthorized_origin_rejected(client: TestClient):
    """Verify that unauthorized origins do not receive CORS authorization headers."""
    bad_origin = "https://unauthorized-attacker.com"
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": bad_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # When origin is rejected by CORSMiddleware, access-control-allow-origin is omitted
    assert response.headers.get("access-control-allow-origin") is None
