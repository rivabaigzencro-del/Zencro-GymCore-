import uuid
from datetime import timedelta
from fastapi import HTTPException
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import enforce_tenant_isolation, get_current_user
from app.core.security import create_access_token, hash_password
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
