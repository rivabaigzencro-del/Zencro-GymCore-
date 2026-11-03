# GymCore - Backend

Production-ready backend API foundation for **GymCore** built with FastAPI, PostgreSQL/Supabase, SQLAlchemy, Alembic, and JWT Authentication.

---

## 🛠 Technology Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **ASGI Server:** [Uvicorn](https://www.uvicorn.org/)
* **Settings & Validation:** [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
* **Database & ORM:** PostgreSQL / Supabase, SQLAlchemy 2.0
* **Schema Migrations:** Alembic
* **Password Hashing:** Bcrypt (12 rounds)
* **Authentication & Authorization:** JWT (JSON Web Tokens), RBAC (OWNER, MANAGER, FRONT_DESK)
* **Testing:** Pytest
* **Language:** Python 3.10+

---

## 📁 Directory Structure

```text
GymCore ZenCro/
├── .env.example              # Sample environment variables template
├── .gitignore                # Git ignore rules (env files, caches, venv)
├── README.md                 # Project documentation and setup guide
├── alembic.ini               # Alembic migration configuration
├── requirements.txt          # Python dependencies
├── alembic/                  # Database migration management
│   ├── env.py                # Alembic runtime environment
│   ├── script.py.mako        # Migration template
│   └── versions/             # Migration revision files
│       └── 57b7d7a1cc70_create_initial_tenant_user_schema.py
├── app/                      # Main application package
│   ├── __init__.py
│   ├── main.py               # FastAPI application factory & middleware
│   ├── core/                 # Core configuration, security & database
│   │   ├── __init__.py
│   │   ├── auth.py           # JWT dependencies, RBAC guard, tenant isolation helper
│   │   ├── config.py         # Pydantic BaseSettings management
│   │   ├── database.py       # SQLAlchemy engine, SessionLocal, get_db
│   │   └── security.py       # Bcrypt hashing & PyJWT token creation/decoding
│   ├── models/               # SQLAlchemy multi-tenant data models
│   │   ├── __init__.py
│   │   ├── tenant.py         # Tenant / Gym entity
│   │   └── user.py           # User entity & UserRole enum
│   ├── schemas/              # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   └── auth.py           # Register, Login, Token, User & Tenant schemas
│   └── api/                  # API routes and versions
│       ├── __init__.py
│       └── v1/               # Version 1 endpoints
│           ├── __init__.py
│           ├── api.py        # Router aggregation for API v1
│           └── endpoints/    # Individual domain route handlers
│               ├── __init__.py
│               ├── auth.py   # Register, Login, Me, and RBAC guard endpoints
│               └── health.py # Service & database health check
├── scripts/                  # Utility and verification scripts
│   └── verify_setup.py       # Non-destructive end-to-end verification script
└── tests/                    # Automated test suite
    ├── conftest.py           # Pytest fixtures (client, db, email generator)
    └── test_auth.py          # 8 authentication, RBAC, and isolation test cases
```

---

## 🏛 Database & Authentication Architecture

### 1. Multi-Tenancy & Isolation
* **Tenant (`tenants`):** Root gym facility entity with contact details, default timezone `Asia/Kolkata` (IST), and currency `INR`.
* **User (`users`):** Scoped to a gym facility via `tenant_id` foreign key.
* **Isolation Guarantee:** Tenant context is strictly resolved from the authenticated JWT server-side (`current_user.tenant_id`). Tenant IDs submitted by frontend clients are never trusted for authorization.
* **Uniqueness:** Email uniqueness is enforced per tenant via compound constraint `(tenant_id, email)`.

### 2. Password Security & Tokens
* **Password Hashing:** Bcrypt with automatic salt generation (`12` rounds). Passwords are never stored or logged in plain text.
* **Password Exposure:** `password_hash` is explicitly excluded from all Pydantic response schemas.
* **JWT Access Tokens:** Signed with HMAC-SHA256 (`HS256`), containing claims: `sub` (user_id), `tenant_id`, `role`, `exp` (UTC expiration), and `iat`.

### 3. Role-Based Access Control (RBAC)
Supported roles within each tenant:
* `OWNER`: Full administrative control over facility, staff, and billing.
* `MANAGER`: Operational control over members and check-ins.
* `FRONT_DESK`: Front desk reception operations.

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure Python 3.10+ is installed:

```bash
python --version
```

### 2. Activate Virtual Environment

#### Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

#### macOS / Linux:
```bash
source venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables

Create `.env` based on `.env.example`:

```bash
copy .env.example .env
```

Key environment variables:
* `DATABASE_URL`: Connection pooler URL for Supabase PostgreSQL.
* `SECRET_KEY`: Secret key used for signing JWT tokens.
* `ALGORITHM`: Token signature algorithm (`HS256`).
* `ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime in minutes (`60`).

---

### 5. Run Database Migrations

Apply database migrations using Alembic:

```bash
alembic upgrade head
```

---

### 6. Run Automated Tests

Execute the comprehensive test suite with Pytest:

```bash
pytest tests -v
```

All 8 authentication, RBAC, and tenant isolation tests will run against the test client.

---

### 7. Run Database Verification Script

Confirm end-to-end database connectivity, schema tables, and health checks:

```bash
python scripts/verify_setup.py
```

---

### 8. Start the FastAPI Development Server

Run the development server with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔍 API Endpoints & Documentation

* **Interactive API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Alternative API Docs (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Authentication Endpoints (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new gym facility and its primary owner | No |
| `POST` | `/api/v1/auth/login` | Authenticate with email/password and obtain JWT | No |
| `GET` | `/api/v1/auth/me` | Retrieve profile of the authenticated user | Yes (Bearer JWT) |
| `GET` | `/api/v1/auth/test-owner-only` | Role guard test (OWNER only) | Yes (Bearer JWT) |
| `GET` | `/api/v1/auth/test-manager-only` | Role guard test (MANAGER or OWNER) | Yes (Bearer JWT) |

### System & Health Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API root welcome and documentation links |
| `GET` | `/health` | Top-level service & database health probe |
| `GET` | `/api/v1/health` | API v1 service & database health probe |
