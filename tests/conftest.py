import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
import app.main as app_main
from app.models.tenant import Tenant
from app.models.user import User, UserRole


# Isolated in-memory SQLite database to protect production Supabase DB
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the isolated test database and redirect app engine."""
    Base.metadata.create_all(bind=test_engine)
    original_engine = app_main.engine
    app_main.engine = test_engine
    yield
    app_main.engine = original_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def reset_test_db(setup_test_db):
    """Reset SQLite database tables before each test function to guarantee isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture(scope="function")
def db() -> Session:
    """Isolated transactional session for test setup."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client() -> TestClient:
    """TestClient configured with isolated in-memory database override."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    """Generate a unique test email address."""
    return f"test_owner_{uuid.uuid4().hex[:10]}@gymcoretest.com"


@pytest.fixture
def registered_gym(client: TestClient, db: Session):
    """
    Register a new gym tenant with an OWNER and return tokens and headers.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"gym_owner_{suffix}@test.com"
    password = "SecurePassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": f"Fitness Elite {suffix}",
            "name": f"Owner {suffix}",
            "email": email,
            "password": password,
            "phone": f"+91987{suffix[:7]}",
            "address": "123 Test Boulevard",
        },
    )
    assert resp.status_code == 201, f"Setup failed: {resp.text}"
    data = resp.json()
    token = data["access_token"]
    tenant_id = uuid.UUID(data["tenant"]["id"])
    owner_id = uuid.UUID(data["user"]["id"])

    return {
        "tenant_id": tenant_id,
        "owner_id": owner_id,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "email": email,
        "password": password,
    }


@pytest.fixture
def second_registered_gym(client: TestClient, db: Session):
    """
    Register a second distinct gym tenant to test cross-tenant isolation.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"second_gym_{suffix}@test.com"
    password = "SecurePassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "gym_name": f"Second Gym {suffix}",
            "name": f"Second Owner {suffix}",
            "email": email,
            "password": password,
            "phone": f"+91988{suffix[:7]}",
            "address": "456 Cross St",
        },
    )
    assert resp.status_code == 201, f"Setup failed: {resp.text}"
    data = resp.json()
    token = data["access_token"]

    return {
        "tenant_id": uuid.UUID(data["tenant"]["id"]),
        "owner_id": uuid.UUID(data["user"]["id"]),
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
def gym_with_roles(registered_gym, db: Session):
    """
    Creates MANAGER and FRONT_DESK accounts within the registered gym
    to enable thorough RBAC testing.
    """
    tenant_id = registered_gym["tenant_id"]
    suffix = uuid.uuid4().hex[:6]

    # Manager
    manager_email = f"mgr_{suffix}@test.com"
    manager = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=f"Manager {suffix}",
        email=manager_email,
        password_hash=hash_password("ManagerPass123!"),
        role=UserRole.MANAGER,
        is_active=True,
    )
    db.add(manager)

    # Front Desk
    desk_email = f"desk_{suffix}@test.com"
    front_desk = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=f"Desk {suffix}",
        email=desk_email,
        password_hash=hash_password("DeskPass123!"),
        role=UserRole.FRONT_DESK,
        is_active=True,
    )
    db.add(front_desk)
    db.commit()

    manager_token = create_access_token({"sub": str(manager.id), "tenant_id": str(tenant_id), "role": "MANAGER"})
    desk_token = create_access_token({"sub": str(front_desk.id), "tenant_id": str(tenant_id), "role": "FRONT_DESK"})

    return {
        **registered_gym,
        "manager_headers": {"Authorization": f"Bearer {manager_token}"},
        "front_desk_headers": {"Authorization": f"Bearer {desk_token}"},
        "manager_id": manager.id,
        "front_desk_id": front_desk.id,
    }
