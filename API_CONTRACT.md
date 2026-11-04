# GYMCORE — FastAPI Backend API Contract & Integration Specification

**Prepared for:** Riva (Backend Lead)  
**Consumer:** Next.js 16 Frontend (`GYMCORE`)  
**Technology Stack:** FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL / Supabase, JWT Authentication (HS256)  
**Base URL:** `http://localhost:8000/api/v1` (configurable via `NEXT_PUBLIC_API_URL`)

---

## 1. Authentication & Security Specification

All secured endpoints require an HTTP `Authorization` header containing a valid Bearer JWT:
```http
Authorization: Bearer <jwt_access_token>
```

### 1.1 POST `/auth/login`
Authenticates administrative users and staff members.

* **Request Body (JSON):**
  ```json
  {
    "username": "admin@gymcore.fit",
    "password": "SecurePassword123"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "USR-001",
      "name": "Vikram Malhotra",
      "email": "admin@gymcore.fit",
      "role": "Super Admin"
    }
  }
  ```
* **Error Response (`401 Unauthorized`):**
  ```json
  {
    "detail": "Invalid username or password."
  }
  ```

---

## 2. Staff Management Endpoints

### 2.1 GET `/staff`
Retrieves all staff members sorted in ascending numeric ID order (`STF001` < `STF002` < `STF010`).

* **Response (`200 OK`):**
  ```json
  [
    {
      "id": "STF001",
      "name": "Rajesh Khanna",
      "role": "Gym Manager",
      "phone": "+91 98450 11223",
      "email": "rajesh@gymcore.fit",
      "joiningDate": "10 Jan 2024",
      "salary": 65000,
      "status": "Active",
      "specialization": "Operations & Floor Management",
      "address": "Koramangala 4th Block, Bangalore"
    }
  ]
  ```

### 2.2 POST `/staff`
Registers a new staff member. Generates the next sequential ID (`STF008`) without reusing deleted IDs.

* **Validation Rules:**
  - Name: Minimum 2 characters.
  - Phone: Valid 10-digit Indian mobile number (`+91 9xxxx xxxxx`). Must be unique.
  - Email: Standard RFC email format. Must be unique.
  - Salary: Minimum ₹1,000.
* **Request Body (JSON):**
  ```json
  {
    "name": "Ananya Sen",
    "role": "Fitness Instructor",
    "phone": "+91 98765 43210",
    "email": "ananya@gymcore.fit",
    "joiningDate": "2026-11-04",
    "salary": 45000,
    "status": "Active",
    "specialization": "Aerobics & Pilates",
    "address": "Indiranagar, Bangalore"
  }
  ```

### 2.3 PUT `/staff/{id}`
Updates existing staff details. ID remains strictly immutable.

### 2.4 PATCH `/staff/{id}/status`
Toggles status between `"Active"` and `"Inactive"`. Does not modify other attributes.

### 2.5 DELETE `/staff/{id}`
Removes a staff member. **CRITICAL:** High-water mark counter must NOT decrement, ensuring the deleted ID is never re-assigned.

---

## 3. Audit Trail Endpoints

### 3.1 GET `/audit-logs`
Retrieves immutable governance and regulatory audit events.

* **Query Parameters:**
  - `search` (string, optional): Matches action, description, or entity ID.
  - `entity_type` (string, optional): `"Member" | "Staff" | "Payment" | "Attendance" | "Settings"`.
  - `severity` (string, optional): `"info" | "warning" | "critical"`.
  - `start_date` / `end_date` (ISO date, optional).
  - `page` / `limit` (integer, optional, default: 50).
* **Response (`200 OK`):**
  ```json
  [
    {
      "id": "AUD-001",
      "action": "STAFF_CREATE",
      "actionLabel": "Staff Member Created",
      "entityType": "Staff",
      "entityId": "STF001",
      "entityName": "Rajesh Khanna",
      "performedBy": "System Administrator",
      "timestamp": "2026-01-10T09:00:00.000Z",
      "description": "Added Rajesh Khanna as Gym Manager with Operations role.",
      "previousValue": null,
      "updatedValue": { "id": "STF001", "name": "Rajesh Khanna", "salary": 65000 },
      "severity": "info"
    }
  ]
  ```

### 3.2 POST `/audit-logs`
Appends an audit record. Automatically sanitizes and removes passwords/tokens.

---

## 4. Members, Attendance & Billing Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/members` | List members sorted by numeric ID (`GYM001`..`GYM007`) |
| `POST` | `/members` | Create member with unique numeric ID |
| `PUT` | `/members/{id}` | Update member profile |
| `DELETE` | `/members/{id}` | Delete member without ID reuse |
| `POST` | `/attendance/check-in` | Record member check-in / admin override |
| `POST` | `/attendance/{id}/check-out` | Record checkout timestamp |
| `GET` | `/payments` | List payment ledger transactions |
| `POST` | `/payments/collect` | Collect full or partial dues payment |

---

## 5. Day 7 Integration Checklist

- [ ] FastAPI service started on `http://localhost:8000`.
- [ ] CORS middleware configured to allow `http://localhost:3000` / `http://localhost:3008`.
- [ ] Database migrated with initial tables: `members`, `staff`, `attendance`, `payments`, `dues`, `audit_logs`.
- [ ] Test JWT authentication against `/auth/login`.
- [ ] Toggle `apiClient` live mode in frontend.

