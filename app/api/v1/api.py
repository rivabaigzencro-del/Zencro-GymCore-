from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    health,
    members,
    membership_plans,
    memberships,
    invoices,
    payments,
    receipts,
    attendance,
    reminders,
    dashboard,
    reports,
    imports,
    exports,
    staff,
    audit_logs,
)

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(members.router, prefix="/members", tags=["Members"])
api_router.include_router(
    membership_plans.router,
    prefix="/membership-plans",
    tags=["Membership Plans"],
)
api_router.include_router(
    memberships.router,
    prefix="/memberships",
    tags=["Memberships"],
)
api_router.include_router(
    invoices.router,
    prefix="/invoices",
    tags=["Invoices"],
)
api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"],
)
api_router.include_router(
    receipts.router,
    prefix="/receipts",
    tags=["Receipts"],
)
api_router.include_router(
    attendance.router,
    prefix="/attendance",
    tags=["Attendance"],
)
api_router.include_router(
    reminders.router,
    prefix="/reminders",
    tags=["Reminders & Follow-ups"],
)
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)
api_router.include_router(
    imports.router,
    prefix="/imports",
    tags=["Imports"],
)
api_router.include_router(
    exports.router,
    prefix="/exports",
    tags=["Exports"],
)
api_router.include_router(
    staff.router,
    prefix="/staff",
    tags=["Staff Management"],
)
api_router.include_router(
    audit_logs.router,
    prefix="/audit-logs",
    tags=["Audit Logs"],
)
