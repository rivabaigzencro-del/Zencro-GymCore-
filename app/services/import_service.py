"""Import service — business logic for CSV and Excel bulk data imports with strict validation."""
import io
import re
import uuid
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo
import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.member import Member, MemberStatus, Gender
from app.models.membership_plan import MembershipPlan, DurationUnit
from app.models.membership import Membership, MembershipStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.receipt import Receipt
from app.schemas.imports import ImportSummaryResponse, ImportValidationError
from app.services.attendance_service import _generate_secure_qr_code
from app.services.invoice_service import get_gym_today
from app.services.membership_service import _calculate_end_date


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


def _load_file_to_df(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Parse CSV or Excel file bytes into a clean Pandas DataFrame.
    Validates extension, non-empty content, and normalizes column headers.
    """
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty",
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    lower_name = filename.lower()
    try:
        if lower_name.endswith(".csv"):
            # Try utf-8 first, fallback to latin-1
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False, encoding="latin-1")
        elif lower_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str, keep_default_na=False, engine="openpyxl")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload a .csv or .xlsx Excel file",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        )

    # Normalize column names: lowercase, strip, replace spaces/hyphens with underscores
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in df.columns
    ]

    # Filter out completely blank rows
    df = df.dropna(how="all")
    # Also drop rows where all values are empty strings
    mask = df.apply(lambda row: any(str(v).strip() != "" for v in row), axis=1)
    df = df[mask].reset_index(drop=True)

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no data rows",
        )

    return df


def _normalize_phone(raw_phone: str) -> Optional[str]:
    """Clean phone number, removing non-digits and country code prefixes."""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 else None


def _parse_date(raw_val: Any) -> Optional[date]:
    """Parse various date formats (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, etc.)."""
    if not raw_val or str(raw_val).strip() == "":
        return None
    val_str = str(raw_val).strip()
    # If string contains time part (e.g. 2026-11-01 00:00:00), split it
    if " " in val_str:
        val_str = val_str.split(" ")[0]
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 1. Members Bulk Import
# ──────────────────────────────────────────────────────────────────────────────

def import_members(
    db: Session,
    tenant_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    dry_run: bool = False,
    allow_partial: bool = False,
) -> ImportSummaryResponse:
    """
    Import member records from CSV or Excel file.
    Validates required fields, phone format, email syntax, gender enums, and duplicates.
    """
    df = _load_file_to_df(file_bytes, filename)
    cols = df.columns.tolist()

    # Determine full name resolution
    has_full_name = "full_name" in cols or "name" in cols
    has_first_name = "first_name" in cols
    if not has_full_name and not has_first_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required column: either 'full_name' or 'first_name' must be provided",
        )
    if "phone" not in cols and "mobile" not in cols and "contact" not in cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required column: 'phone' (or 'mobile')",
        )

    phone_col = "phone" if "phone" in cols else ("mobile" if "mobile" in cols else "contact")
    name_col = "full_name" if "full_name" in cols else ("name" if "name" in cols else None)

    # Pre-fetch existing phones and emails in this gym for fast uniqueness checks
    existing_members = db.query(Member.phone, Member.email).filter(Member.tenant_id == tenant_id).all()
    db_phones = {p for (p, _) in existing_members if p}
    db_emails = {e.lower() for (_, e) in existing_members if e}

    seen_file_phones: Set[str] = set()
    seen_file_emails: Set[str] = set()

    errors: List[ImportValidationError] = []
    valid_members_to_create: List[Member] = []
    duplicate_count = 0

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-based index (header is row 1)
        row_errors: List[ImportValidationError] = []

        # Name extraction
        if name_col:
            full_name = str(row.get(name_col, "")).strip()
        else:
            first = str(row.get("first_name", "")).strip()
            last = str(row.get("last_name", "")).strip()
            full_name = f"{first} {last}".strip()

        if not full_name:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="full_name",
                    error="Member name cannot be empty",
                    raw_value="",
                )
            )

        # Phone validation
        raw_phone = str(row.get(phone_col, "")).strip()
        clean_phone = _normalize_phone(raw_phone)
        if not clean_phone:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="phone",
                    error="Phone number must be a valid 10-digit mobile number",
                    raw_value=raw_phone,
                )
            )
        else:
            if clean_phone in seen_file_phones:
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="phone",
                        error=f"Duplicate phone number '{clean_phone}' found within the import file",
                        raw_value=clean_phone,
                    )
                )
                duplicate_count += 1
            elif clean_phone in db_phones:
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="phone",
                        error=f"A member with phone '{clean_phone}' already exists in this gym",
                        raw_value=clean_phone,
                    )
                )
                duplicate_count += 1
            else:
                seen_file_phones.add(clean_phone)

        # Email validation (optional)
        clean_email = None
        raw_email = str(row.get("email", "")).strip()
        if raw_email:
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", raw_email):
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="email",
                        error="Invalid email address format",
                        raw_value=raw_email,
                    )
                )
            else:
                low_email = raw_email.lower()
                if low_email in seen_file_emails:
                    row_errors.append(
                        ImportValidationError(
                            row_number=row_num,
                            field="email",
                            error=f"Duplicate email '{raw_email}' found within the import file",
                            raw_value=raw_email,
                        )
                    )
                    duplicate_count += 1
                elif low_email in db_emails:
                    row_errors.append(
                        ImportValidationError(
                            row_number=row_num,
                            field="email",
                            error=f"A member with email '{raw_email}' already exists in this gym",
                            raw_value=raw_email,
                        )
                    )
                    duplicate_count += 1
                else:
                    seen_file_emails.add(low_email)
                    clean_email = low_email

        # Gender validation (optional)
        gender_enum = None
        raw_gender = str(row.get("gender", "")).strip().upper()
        if raw_gender:
            try:
                gender_enum = Gender[raw_gender]
            except KeyError:
                if raw_gender in ("M", "MALE"):
                    gender_enum = Gender.MALE
                elif raw_gender in ("F", "FEMALE"):
                    gender_enum = Gender.FEMALE
                elif raw_gender in ("O", "OTHER"):
                    gender_enum = Gender.OTHER
                else:
                    row_errors.append(
                        ImportValidationError(
                            row_number=row_num,
                            field="gender",
                            error=f"Invalid gender '{raw_gender}'. Allowed: MALE, FEMALE, OTHER",
                            raw_value=raw_gender,
                        )
                    )

        # Date of birth validation (optional)
        dob = None
        raw_dob = row.get("date_of_birth") or row.get("dob")
        if raw_dob and str(raw_dob).strip():
            dob = _parse_date(raw_dob)
            if not dob:
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="date_of_birth",
                        error="Invalid date format for date_of_birth (expected YYYY-MM-DD or DD/MM/YYYY)",
                        raw_value=str(raw_dob),
                    )
                )
            elif dob > date.today():
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="date_of_birth",
                        error="Date of birth cannot be in the future",
                        raw_value=str(dob),
                    )
                )

        address = str(row.get("address", "")).strip() or None
        emer_name = str(row.get("emergency_contact_name", "")).strip() or None
        emer_phone = str(row.get("emergency_contact_phone", "")).strip() or None

        if row_errors:
            errors.extend(row_errors)
        else:
            member = Member(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                full_name=full_name,
                phone=clean_phone,
                email=clean_email,
                gender=gender_enum,
                date_of_birth=dob,
                address=address,
                emergency_contact_name=emer_name,
                emergency_contact_phone=emer_phone,
                status=MemberStatus.ACTIVE,
                qr_code=_generate_secure_qr_code(),
            )
            valid_members_to_create.append(member)

    total_rows = len(df)
    failed_count = len({e.row_number for e in errors})

    # Commit logic based on dry_run and allow_partial
    imported_ids: List[str] = []
    if not dry_run:
        # If allow_partial is False and there are errors, rollback and do not insert any
        if errors and not allow_partial:
            # Transaction safe: no records inserted
            valid_members_to_create.clear()
        else:
            for m in valid_members_to_create:
                db.add(m)
            try:
                db.commit()
                imported_ids = [str(m.id) for m in valid_members_to_create]
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during member import: {str(e)}",
                )

    return ImportSummaryResponse(
        entity="members",
        filename=filename,
        total_rows_processed=total_rows,
        successful_imports=len(valid_members_to_create) if not dry_run else 0,
        failed_records=failed_count,
        duplicate_records=duplicate_count,
        dry_run=dry_run,
        errors=errors,
        imported_ids=imported_ids,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. Memberships Bulk Import
# ──────────────────────────────────────────────────────────────────────────────

def import_memberships(
    db: Session,
    tenant_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    dry_run: bool = False,
    allow_partial: bool = False,
) -> ImportSummaryResponse:
    """
    Import membership subscriptions from CSV or Excel file.
    Resolves member by phone/email/id and plan by name/id.
    Validates dates and checks for active overlapping memberships.
    """
    df = _load_file_to_df(file_bytes, filename)
    cols = df.columns.tolist()

    has_member = any(c in cols for c in ("member_phone", "phone", "member_email", "email", "member_id"))
    has_plan = any(c in cols for c in ("plan_name", "plan", "plan_id"))
    has_start = any(c in cols for c in ("start_date", "start"))

    if not has_member or not has_plan or not has_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required columns: must contain member reference ('phone'), plan reference ('plan_name'), and 'start_date'",
        )

    # Pre-fetch plans
    plans = db.query(MembershipPlan).filter(MembershipPlan.tenant_id == tenant_id, MembershipPlan.is_active == True).all()
    plan_by_name = {p.name.strip().lower(): p for p in plans}
    plan_by_id = {str(p.id): p for p in plans}

    errors: List[ImportValidationError] = []
    valid_memberships: List[Membership] = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        row_errors: List[ImportValidationError] = []

        # Resolve member
        member = None
        raw_phone = str(row.get("member_phone") or row.get("phone", "")).strip()
        raw_email = str(row.get("member_email") or row.get("email", "")).strip()
        raw_mid = str(row.get("member_id", "")).strip()

        if raw_mid:
            try:
                m_uuid = uuid.UUID(raw_mid)
                member = db.query(Member).filter(Member.tenant_id == tenant_id, Member.id == m_uuid).first()
            except ValueError:
                pass

        if not member and raw_phone:
            clean_phone = _normalize_phone(raw_phone) or raw_phone
            member = db.query(Member).filter(Member.tenant_id == tenant_id, Member.phone == clean_phone).first()

        if not member and raw_email:
            member = db.query(Member).filter(Member.tenant_id == tenant_id, Member.email == raw_email.lower()).first()

        if not member:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="member",
                    error=f"Member not found with phone/email: '{raw_phone or raw_email or raw_mid}'",
                    raw_value=raw_phone or raw_email or raw_mid,
                )
            )

        # Resolve plan
        plan = None
        raw_plan = str(row.get("plan_name") or row.get("plan", "")).strip()
        raw_pid = str(row.get("plan_id", "")).strip()

        if raw_pid and raw_pid in plan_by_id:
            plan = plan_by_id[raw_pid]
        elif raw_plan and raw_plan.lower() in plan_by_name:
            plan = plan_by_name[raw_plan.lower()]

        if not plan:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="plan_name",
                    error=f"Active membership plan '{raw_plan or raw_pid}' not found",
                    raw_value=raw_plan or raw_pid,
                )
            )

        # Parse start date
        raw_start = row.get("start_date") or row.get("start")
        start_dt = _parse_date(raw_start)
        if not start_dt:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="start_date",
                    error="Invalid start_date format (expected YYYY-MM-DD or DD/MM/YYYY)",
                    raw_value=str(raw_start),
                )
            )

        # End date calculation
        end_dt = None
        raw_end = row.get("end_date") or row.get("end")
        if raw_end and str(raw_end).strip():
            end_dt = _parse_date(raw_end)

        if start_dt and plan and not end_dt:
            end_dt = _calculate_end_date(start_dt, plan)

        if start_dt and end_dt and end_dt < start_dt:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="end_date",
                    error="end_date cannot precede start_date",
                    raw_value=str(end_dt),
                )
            )

        # Overlapping membership validation
        if member and start_dt and end_dt:
            overlap = (
                db.query(Membership)
                .filter(
                    Membership.tenant_id == tenant_id,
                    Membership.member_id == member.id,
                    Membership.status.in_((MembershipStatus.ACTIVE, MembershipStatus.FROZEN)),
                    Membership.start_date <= end_dt,
                    Membership.end_date >= start_dt,
                )
                .first()
            )
            if overlap:
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="membership",
                        error=f"Member already has an active subscription overlapping with {start_dt} to {end_dt}",
                        raw_value=f"{start_dt} to {end_dt}",
                    )
                )

        if row_errors:
            errors.extend(row_errors)
        else:
            notes = str(row.get("notes", "")).strip() or None
            membership = Membership(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                member_id=member.id,
                membership_plan_id=plan.id,
                start_date=start_dt,
                end_date=end_dt,
                status=MembershipStatus.ACTIVE,
                notes=notes,
            )
            valid_memberships.append(membership)

    total_rows = len(df)
    failed_count = len({e.row_number for e in errors})

    imported_ids: List[str] = []
    if not dry_run:
        if errors and not allow_partial:
            valid_memberships.clear()
        else:
            for m in valid_memberships:
                db.add(m)
            try:
                db.commit()
                imported_ids = [str(m.id) for m in valid_memberships]
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during membership import: {str(e)}",
                )

    return ImportSummaryResponse(
        entity="memberships",
        filename=filename,
        total_rows_processed=total_rows,
        successful_imports=len(valid_memberships) if not dry_run else 0,
        failed_records=failed_count,
        duplicate_records=0,
        dry_run=dry_run,
        errors=errors,
        imported_ids=imported_ids,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 3. Payments Bulk Import
# ──────────────────────────────────────────────────────────────────────────────

def import_payments(
    db: Session,
    tenant_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    dry_run: bool = False,
    allow_partial: bool = False,
) -> ImportSummaryResponse:
    """
    Import payment collections from CSV or Excel file.
    Matches invoice by invoice_number or member phone.
    Updates invoice balance and automatically creates receipts within transaction.
    """
    df = _load_file_to_df(file_bytes, filename)
    cols = df.columns.tolist()

    has_inv = "invoice_number" in cols or "invoice" in cols or "phone" in cols
    has_amount = "amount" in cols or "amount_paise" in cols or "amount_rupees" in cols
    has_method = "payment_method" in cols or "method" in cols

    if not has_inv or not has_amount or not has_method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required columns: must contain 'invoice_number' (or 'phone'), 'amount', and 'payment_method'",
        )

    errors: List[ImportValidationError] = []
    payments_to_commit: List[Tuple[Payment, Invoice]] = []

    tz_str = db.query(Tenant.timezone).filter(Tenant.id == tenant_id).scalar() or "Asia/Kolkata"
    tz = ZoneInfo(tz_str)
    today = datetime.now(tz).date()

    for idx, row in df.iterrows():
        row_num = idx + 2
        row_errors: List[ImportValidationError] = []

        # Find invoice
        inv = None
        raw_inv = str(row.get("invoice_number") or row.get("invoice", "")).strip()
        raw_phone = str(row.get("phone", "")).strip()

        if raw_inv:
            inv = db.query(Invoice).filter(Invoice.tenant_id == tenant_id, Invoice.invoice_number == raw_inv).first()
        elif raw_phone:
            clean_phone = _normalize_phone(raw_phone) or raw_phone
            member = db.query(Member).filter(Member.tenant_id == tenant_id, Member.phone == clean_phone).first()
            if member:
                inv = (
                    db.query(Invoice)
                    .filter(
                        Invoice.tenant_id == tenant_id,
                        Invoice.member_id == member.id,
                        Invoice.invoice_status.in_((InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE)),
                    )
                    .order_by(Invoice.due_date.asc())
                    .first()
                )

        if not inv:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="invoice_number",
                    error=f"Unpaid invoice not found for reference: '{raw_inv or raw_phone}'",
                    raw_value=raw_inv or raw_phone,
                )
            )
        elif inv.invoice_status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="invoice_number",
                    error=f"Invoice '{inv.invoice_number}' is already {inv.invoice_status.value}",
                    raw_value=inv.invoice_number,
                )
            )

        # Amount validation
        amount_paise = 0
        raw_amount = str(row.get("amount") or row.get("amount_rupees") or row.get("amount_paise", "")).strip()
        try:
            amt_num = float(raw_amount)
            if "amount_paise" in cols:
                amount_paise = int(amt_num)
            else:
                amount_paise = int(round(amt_num * 100))

            if amount_paise <= 0:
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="amount",
                        error="Payment amount must be greater than zero",
                        raw_value=raw_amount,
                    )
                )
            elif inv and amount_paise > inv.balance_amount_paise:
                row_errors.append(
                    ImportValidationError(
                        row_number=row_num,
                        field="amount",
                        error=f"Payment amount ({amount_paise / 100:.2f}) exceeds outstanding invoice balance ({inv.balance_amount_paise / 100:.2f})",
                        raw_value=raw_amount,
                    )
                )
        except ValueError:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="amount",
                    error="Invalid numeric payment amount",
                    raw_value=raw_amount,
                )
            )

        # Method validation
        pm_enum = None
        raw_method = str(row.get("payment_method") or row.get("method", "")).strip().upper()
        try:
            pm_enum = PaymentMethod[raw_method]
        except KeyError:
            row_errors.append(
                ImportValidationError(
                    row_number=row_num,
                    field="payment_method",
                    error=f"Invalid payment method '{raw_method}'. Allowed: CASH, UPI, CARD, BANK_TRANSFER, CHEQUE",
                    raw_value=raw_method,
                )
            )

        # Date parsing
        pay_date = datetime.now(timezone.utc)
        raw_pdate = row.get("payment_date") or row.get("date")
        if raw_pdate and str(raw_pdate).strip():
            parsed_d = _parse_date(raw_pdate)
            if parsed_d:
                pay_date = datetime.combine(parsed_d, time(12, 0)).replace(tzinfo=timezone.utc)

        ref_no = str(row.get("reference_number", "")).strip() or None
        notes = str(row.get("notes", "")).strip() or None

        if row_errors:
            errors.extend(row_errors)
        else:
            payment = Payment(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                member_id=inv.member_id,
                invoice_id=inv.id,
                amount_paise=amount_paise,
                payment_method=pm_enum,
                payment_status=PaymentStatus.COMPLETED,
                payment_date=pay_date,
                transaction_reference=ref_no,
                notes=notes,
            )
            payments_to_commit.append((payment, inv))

    total_rows = len(df)
    failed_count = len({e.row_number for e in errors})

    imported_ids: List[str] = []
    if not dry_run:
        if errors and not allow_partial:
            payments_to_commit.clear()
        else:
            try:
                for payment, inv in payments_to_commit:
                    db.add(payment)
                    # Update invoice balance
                    inv.paid_amount_paise += payment.amount_paise
                    inv.balance_amount_paise -= payment.amount_paise
                    if inv.balance_amount_paise == 0:
                        inv.invoice_status = InvoiceStatus.PAID
                    else:
                        inv.invoice_status = InvoiceStatus.PARTIALLY_PAID

                    # Auto generate receipt
                    receipt_seq = (
                        db.query(func.count(Receipt.id))
                        .filter(Receipt.tenant_id == tenant_id)
                        .scalar()
                        or 0
                    ) + 1
                    receipt_num = f"REC-{today.strftime('%Y%m')}-{receipt_seq:04d}"
                    receipt = Receipt(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        payment_id=payment.id,
                        receipt_number=receipt_num,
                        issued_at=datetime.now(timezone.utc),
                    )
                    db.add(receipt)

                db.commit()
                imported_ids = [str(p.id) for p, _ in payments_to_commit]
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during payment import: {str(e)}",
                )

    return ImportSummaryResponse(
        entity="payments",
        filename=filename,
        total_rows_processed=total_rows,
        successful_imports=len(payments_to_commit) if not dry_run else 0,
        failed_records=failed_count,
        duplicate_records=0,
        dry_run=dry_run,
        errors=errors,
        imported_ids=imported_ids,
    )

