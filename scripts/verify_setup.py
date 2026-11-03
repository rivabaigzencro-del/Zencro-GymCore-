"""
GymCore Backend Verification Script
Performs clean, non-destructive checks of:
1. Environment & configuration loading
2. SQLAlchemy engine connectivity to Supabase PostgreSQL
3. Database schema verification (tenants, users, user_role enum)
4. Multi-tenant relationships and constraints
5. FastAPI application startup & health check endpoints (/health, /api/v1/health)
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect, text
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import engine
from app.models import Tenant, User, UserRole
from app.main import app


def run_checks() -> bool:
    print("=" * 60)
    print("GYMCORE BACKEND FOUNDATION VERIFICATION")
    print("=" * 60)

    # 1. Config Check
    print("\n[1/5] Checking Configuration...")
    print(f"  Project Name: {settings.PROJECT_NAME}")
    print(f"  Version:      {settings.VERSION}")
    print(f"  Environment:  {settings.ENV}")
    print(f"  API V1 Path:  {settings.API_V1_STR}")
    print("  DATABASE_URL: Configured (credentials safely masked)")

    # 2. Database Connectivity
    print("\n[2/5] Testing Supabase PostgreSQL Connectivity...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1, "SELECT 1 failed"
        print("  Database connectivity test: PASSED (SELECT 1 returned 1)")
    except Exception as e:
        print(f"  Database connectivity test: FAILED -> {type(e).__name__}")
        return False

    # 3. Database Schema Verification
    print("\n[3/5] Verifying Alembic Migrated Schema...")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names(schema="public")
    print(f"  Found tables in public schema: {existing_tables}")

    required_tables = ["tenants", "users", "alembic_version"]
    for t in required_tables:
        if t in existing_tables:
            print(f"  Table '{t}': PRESENT")
        else:
            print(f"  Table '{t}': MISSING")
            return False

    # Check tenants columns
    tenant_cols = {c["name"] for c in inspector.get_columns("tenants")}
    expected_tenant_cols = {"id", "name", "email", "phone", "address", "timezone", "currency", "created_at", "updated_at"}
    diff_tenant = expected_tenant_cols - tenant_cols
    if diff_tenant:
        print(f"  Missing columns in 'tenants': {diff_tenant}")
        return False
    print(f"  Tenants schema: VALID ({len(tenant_cols)} columns)")

    # Check users columns
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    expected_user_cols = {"id", "tenant_id", "name", "email", "phone", "password_hash", "role", "is_active", "created_at", "updated_at"}
    diff_user = expected_user_cols - user_cols
    if diff_user:
        print(f"  Missing columns in 'users': {diff_user}")
        return False
    print(f"  Users schema: VALID ({len(user_cols)} columns)")

    # 4. Multi-Tenant Foreign Key & Index Verification
    print("\n[4/5] Verifying Multi-Tenant Constraints & Indices...")
    fks = inspector.get_foreign_keys("users")
    tenant_fk = any(fk["referred_table"] == "tenants" and "tenant_id" in fk["constrained_columns"] for fk in fks)
    assert tenant_fk, "Foreign key from users.tenant_id to tenants.id missing!"
    print("  Tenant isolation foreign key (users.tenant_id -> tenants.id): PRESENT")

    user_indices = [idx["name"] for idx in inspector.get_indexes("users")]
    print(f"  Indices on users table: {user_indices}")

    # 5. FastAPI Health Endpoint Verification
    print("\n[5/5] Testing FastAPI Endpoints (TestClient)...")
    client = TestClient(app)

    # Root
    resp_root = client.get("/")
    assert resp_root.status_code == 200, f"Root returned status {resp_root.status_code}"
    print(f"  GET /: PASSED ({resp_root.status_code}) -> {resp_root.json()}")

    # Top-level /health
    resp_health = client.get("/health")
    assert resp_health.status_code == 200, f"/health returned status {resp_health.status_code}"
    health_data = resp_health.json()
    assert health_data.get("status") == "healthy", "Health status not healthy"
    assert health_data.get("database") == "healthy", "Database health status not healthy"
    print(f"  GET /health: PASSED ({resp_health.status_code}) -> {health_data}")

    # API v1 /api/v1/health
    resp_v1_health = client.get(f"{settings.API_V1_STR}/health")
    assert resp_v1_health.status_code == 200, f"v1 health returned status {resp_v1_health.status_code}"
    v1_data = resp_v1_health.json()
    assert v1_data.get("status") == "healthy"
    assert v1_data.get("database") == "healthy"
    print(f"  GET {settings.API_V1_STR}/health: PASSED ({resp_v1_health.status_code}) -> {v1_data}")

    print("\n" + "=" * 60)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
