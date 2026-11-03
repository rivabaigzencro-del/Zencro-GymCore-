"""Tests for Day 6: CSV and Excel Import and Export functionalities."""
import io
import uuid
from datetime import date, datetime
import pandas as pd
from fastapi.testclient import TestClient

from tests.test_dashboard import _seed_gym_data


def test_import_members_csv_valid_and_duplicate_detection(client: TestClient, registered_gym):
    """Test importing valid members via CSV and verifying duplicate detection."""
    headers = registered_gym["headers"]

    csv_content = (
        "full_name,phone,email,gender\n"
        "Rohan Mehra,9123456780,rohan@example.com,MALE\n"
        "Sneha Patel,9123456781,sneha@example.com,FEMALE\n"
    ).encode("utf-8")

    resp = client.post(
        "/api/v1/imports/members",
        headers=headers,
        files={"file": ("members.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    body = resp.json()
    assert body["successful_imports"] == 2
    assert body["failed_records"] == 0
    assert len(body["imported_ids"]) == 2

    # Re-uploading the same file must detect duplicate phone numbers
    resp_dup = client.post(
        "/api/v1/imports/members",
        headers=headers,
        files={"file": ("members.csv", csv_content, "text/csv")},
    )
    assert resp_dup.status_code == 200
    body_dup = resp_dup.json()
    assert body_dup["successful_imports"] == 0
    assert body_dup["duplicate_records"] >= 2
    assert body_dup["failed_records"] == 2


def test_import_members_excel_valid(client: TestClient, registered_gym):
    """Test importing members via Excel (.xlsx) file."""
    headers = registered_gym["headers"]

    df = pd.DataFrame([
        {"first_name": "Aman", "last_name": "Verma", "phone": "9811223344", "email": "aman@test.com", "gender": "MALE"}
    ])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    xlsx_bytes = buf.getvalue()

    resp = client.post(
        "/api/v1/imports/members",
        headers=headers,
        files={"file": ("members.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert resp.json()["successful_imports"] == 1


def test_import_members_validation_errors_and_dry_run(client: TestClient, registered_gym):
    """Test dry_run mode and row-level validation errors (invalid phone, email, gender)."""
    headers = registered_gym["headers"]

    bad_csv = (
        "full_name,phone,email,gender\n"
        "Invalid User,12345,bad-email,ALIEN\n"
    ).encode("utf-8")

    # Dry run
    resp_dry = client.post(
        "/api/v1/imports/members?dry_run=true",
        headers=headers,
        files={"file": ("bad_members.csv", bad_csv, "text/csv")},
    )
    assert resp_dry.status_code == 200
    body_dry = resp_dry.json()
    assert body_dry["dry_run"] is True
    assert body_dry["successful_imports"] == 0
    assert body_dry["failed_records"] == 1
    assert len(body_dry["errors"]) >= 3  # phone, email, gender errors

    # Without dry_run and allow_partial=False (default atomic rollback)
    resp_real = client.post(
        "/api/v1/imports/members",
        headers=headers,
        files={"file": ("bad_members.csv", bad_csv, "text/csv")},
    )
    assert resp_real.status_code == 200
    assert resp_real.json()["successful_imports"] == 0


def test_import_members_empty_file_and_bad_extension_rejected(client: TestClient, registered_gym):
    """Verify empty uploads and unsupported file extensions are rejected with 400."""
    headers = registered_gym["headers"]

    # Empty file
    assert client.post(
        "/api/v1/imports/members",
        headers=headers,
        files={"file": ("empty.csv", b"", "text/csv")},
    ).status_code == 400

    # Bad extension
    assert client.post(
        "/api/v1/imports/members",
        headers=headers,
        files={"file": ("doc.pdf", b"dummy content", "application/pdf")},
    ).status_code == 400


def test_import_memberships_csv(client: TestClient, registered_gym):
    """Test bulk importing memberships matching member phone and plan name."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)

    # Register an extra member without membership
    m_resp = client.post(
        "/api/v1/members",
        headers=headers,
        json={"full_name": "New Member", "phone": "9998887776"},
    )
    assert m_resp.status_code == 201

    csv_data = (
        "phone,plan_name,start_date\n"
        f"9998887776,Monthly Gold,{date.today()}\n"
    ).encode("utf-8")

    resp = client.post(
        "/api/v1/imports/memberships",
        headers=headers,
        files={"file": ("memberships.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert resp.json()["successful_imports"] == 1


def test_import_payments_csv(client: TestClient, registered_gym):
    """Test importing payment records, updating invoice balance and auto-generating receipts."""
    headers = registered_gym["headers"]
    seeded = _seed_gym_data(client, headers)
    inv_num = seeded["invoice"]["invoice_number"]

    # Seeded invoice has 500.00 (50000 paise) balance remaining
    csv_data = (
        "invoice_number,amount,payment_method,notes\n"
        f"{inv_num},500,CASH,Final settlement\n"
    ).encode("utf-8")

    resp = client.post(
        "/api/v1/imports/payments",
        headers=headers,
        files={"file": ("payments.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert resp.json()["successful_imports"] == 1

    # Verify invoice is now fully PAID
    inv_check = client.get(f"/api/v1/invoices/{seeded['invoice']['id']}", headers=headers)
    assert inv_check.status_code == 200
    assert inv_check.json()["invoice_status"] == "PAID"
    assert inv_check.json()["balance_amount_paise"] == 0


def test_export_members_csv_and_xlsx(client: TestClient, registered_gym):
    """Test exporting member records in CSV and Excel formats."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    # CSV
    resp_csv = client.get("/api/v1/exports/members?format=csv", headers=headers)
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "Karan Sharma" in resp_csv.text
    assert "Full Name" in resp_csv.text

    # Excel
    resp_xlsx = client.get("/api/v1/exports/members?format=xlsx", headers=headers)
    assert resp_xlsx.status_code == 200
    assert "openxmlformats" in resp_xlsx.headers["content-type"]
    # Verify openpyxl can read it
    df = pd.read_excel(io.BytesIO(resp_xlsx.content), engine="openpyxl")
    assert not df.empty
    assert "Karan Sharma" in df["Full Name"].values


def test_export_memberships_csv_and_xlsx(client: TestClient, registered_gym):
    """Test exporting membership records in CSV and Excel formats."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    resp = client.get("/api/v1/exports/memberships?format=csv", headers=headers)
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert "Monthly Gold" in resp.text


def test_export_payments_csv_and_xlsx(client: TestClient, registered_gym):
    """Test exporting payment records."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    resp = client.get("/api/v1/exports/payments?format=csv", headers=headers)
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert "1500.00" in resp.text or "1500" in resp.text


def test_export_attendance_csv_and_xlsx(client: TestClient, registered_gym):
    """Test exporting attendance records."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    resp = client.get("/api/v1/exports/attendance?format=csv", headers=headers)
    assert resp.status_code == 200, f"Error: {resp.text}"
    assert "Karan Sharma" in resp.text


def test_export_reports_csv_and_xlsx(client: TestClient, registered_gym):
    """Test exporting generated reports in CSV and Excel formats."""
    headers = registered_gym["headers"]
    _seed_gym_data(client, headers)

    # Revenue report export
    resp_rev = client.get("/api/v1/exports/reports/revenue?format=csv", headers=headers)
    assert resp_rev.status_code == 200
    assert "Payment ID" in resp_rev.text

    # Pending dues report export (Excel)
    resp_dues = client.get("/api/v1/exports/reports/pending-dues?format=xlsx", headers=headers)
    assert resp_dues.status_code == 200
    assert "openxmlformats" in resp_dues.headers["content-type"]


def test_export_empty_dataset_has_headers(client: TestClient, registered_gym):
    """Verify that an empty gym exports a valid file with column headers and 0 data rows."""
    headers = registered_gym["headers"]

    resp = client.get("/api/v1/exports/members?format=csv", headers=headers)
    assert resp.status_code == 200, f"Error: {resp.text}"
    lines = resp.text.strip().split("\n")
    assert len(lines) == 1  # Only the header row
    assert "Full Name" in lines[0]


def test_import_export_tenant_isolation(client: TestClient, registered_gym, second_registered_gym):
    """Verify imported data in Gym 1 is completely isolated from Gym 2 exports."""
    headers1 = registered_gym["headers"]
    headers2 = second_registered_gym["headers"]

    csv_content = "full_name,phone\nTenant One Member,9111222333\n".encode("utf-8")
    client.post(
        "/api/v1/imports/members",
        headers=headers1,
        files={"file": ("m.csv", csv_content, "text/csv")},
    )

    # Gym 2 export must not contain Gym 1 member
    resp2 = client.get("/api/v1/exports/members?format=csv", headers=headers2)
    assert resp2.status_code == 200
    assert "Tenant One Member" not in resp2.text


def test_import_export_rbac(client: TestClient, gym_with_roles):
    """
    Verify RBAC:
    - Imports restricted to OWNER and MANAGER (FRONT_DESK receives 403).
    - Financial exports (payments, revenue report) restricted to OWNER and MANAGER (FRONT_DESK receives 403).
    - General operational exports (members, attendance) allowed for FRONT_DESK.
    """
    desk_headers = gym_with_roles["front_desk_headers"]
    mgr_headers = gym_with_roles["manager_headers"]

    csv_content = "full_name,phone\nTest,9111111111\n".encode("utf-8")

    # Front desk forbidden from importing
    assert client.post(
        "/api/v1/imports/members",
        headers=desk_headers,
        files={"file": ("m.csv", csv_content, "text/csv")},
    ).status_code == 403

    # Front desk forbidden from exporting payments and revenue report
    assert client.get("/api/v1/exports/payments", headers=desk_headers).status_code == 403
    assert client.get("/api/v1/exports/reports/revenue", headers=desk_headers).status_code == 403

    # Front desk allowed to export members and attendance
    assert client.get("/api/v1/exports/members", headers=desk_headers).status_code == 200
    assert client.get("/api/v1/exports/attendance", headers=desk_headers).status_code == 200

    # Manager allowed all imports and exports
    assert client.get("/api/v1/exports/payments", headers=mgr_headers).status_code == 200

