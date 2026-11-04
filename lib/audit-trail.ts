/**
 * GYMCORE Audit Trail Management System
 * Provides tamper-resistant administrative action logging, tracking, and compliance history.
 */

export type AuditActionType =
  | "MEMBER_CREATE"
  | "MEMBER_UPDATE"
  | "MEMBER_DELETE"
  | "MEMBERSHIP_ASSIGN"
  | "MEMBERSHIP_RENEW"
  | "MEMBERSHIP_FREEZE"
  | "MEMBERSHIP_UNFREEZE"
  | "PAYMENT_COLLECT"
  | "PAYMENT_PARTIAL"
  | "PAYMENT_REFUND"
  | "ATTENDANCE_CHECKIN"
  | "ATTENDANCE_CHECKOUT"
  | "ADMIN_OVERRIDE"
  | "STAFF_CREATE"
  | "STAFF_UPDATE"
  | "STAFF_ACTIVATE"
  | "STAFF_DEACTIVATE"
  | "STAFF_DELETE"
  | "SETTINGS_UPDATE";

export type AuditEntityType =
  | "Member"
  | "Membership"
  | "Payment"
  | "Attendance"
  | "Staff"
  | "Settings"
  | "System";

export type AuditSeverity = "info" | "warning" | "critical";

export interface AuditRecord {
  id: string; // e.g., "AUD-001"
  action: AuditActionType;
  actionLabel: string;
  entityType: AuditEntityType;
  entityId?: string; // e.g., "GYM001", "STF001", "TXN-1001"
  entityName?: string; // e.g., "Alex Johnson", "David Miller"
  performedBy: string; // e.g., "Admin (Vikram Malhotra)"
  timestamp: string; // ISO 8601 string
  description: string;
  previousValue?: Record<string, unknown> | null;
  updatedValue?: Record<string, unknown> | null;
  severity: AuditSeverity;
}

export const AUDIT_STORAGE_KEY = "gymcore_audit_trail_v1";

// Sensitive keys that must NEVER be logged in audit trail
const SENSITIVE_KEYS = new Set([
  "password",
  "newpassword",
  "confirmpassword",
  "currentpassword",
  "token",
  "refreshtoken",
  "accesstoken",
  "secret",
  "secretkey",
  "apikey",
  "creditcard",
  "cvv",
  "pin",
]);

/**
 * Strips sensitive keys recursively from audit values
 */
export function sanitizeAuditValue(
  value: Record<string, unknown> | null | undefined
): Record<string, unknown> | null {
  if (!value || typeof value !== "object") return null;

  const sanitized: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    const lowerKey = k.toLowerCase().replace(/[^a-z]/g, "");
    const isSensitive =
      SENSITIVE_KEYS.has(lowerKey) ||
      lowerKey.includes("password") ||
      lowerKey.includes("token") ||
      lowerKey.includes("secret") ||
      lowerKey.includes("apikey") ||
      lowerKey.includes("creditcard") ||
      lowerKey.includes("cvv") ||
      lowerKey.includes("pin");
    if (isSensitive) {
      sanitized[k] = "[REDACTED]";
    } else if (v && typeof v === "object" && !Array.isArray(v)) {
      sanitized[k] = sanitizeAuditValue(v as Record<string, unknown>);
    } else {
      sanitized[k] = v;
    }
  }
  return sanitized;
}

// Initial seed history reflecting administrative events
export const INITIAL_AUDIT_LOGS: AuditRecord[] = [
  {
    id: "AUD-001",
    action: "STAFF_CREATE",
    actionLabel: "Staff Created",
    entityType: "Staff",
    entityId: "STF001",
    entityName: "Rajesh Khanna",
    performedBy: "System Administrator",
    timestamp: "2026-01-10T09:00:00.000Z",
    description: "Added Rajesh Khanna as Gym Manager with Operations role.",
    previousValue: null,
    updatedValue: { id: "STF001", name: "Rajesh Khanna", role: "Gym Manager", salary: 65000 },
    severity: "info",
  },
  {
    id: "AUD-002",
    action: "MEMBER_CREATE",
    actionLabel: "Member Registered",
    entityType: "Member",
    entityId: "GYM001",
    entityName: "Alex Johnson",
    performedBy: "Rajesh Khanna (Staff)",
    timestamp: "2026-01-15T10:30:00.000Z",
    description: "Enrolled Alex Johnson under VIP Annual Membership plan.",
    previousValue: null,
    updatedValue: { id: "GYM001", name: "Alex Johnson", plan: "VIP Annual", status: "Active" },
    severity: "info",
  },
  {
    id: "AUD-003",
    action: "PAYMENT_COLLECT",
    actionLabel: "Payment Collected",
    entityType: "Payment",
    entityId: "TXN-1001",
    entityName: "Alex Johnson",
    performedBy: "Rajesh Khanna (Staff)",
    timestamp: "2026-01-15T10:35:00.000Z",
    description: "Collected ₹14,999 via UPI for Annual VIP Membership. Receipt #RCP-2026-001 generated.",
    previousValue: null,
    updatedValue: { amount: 14999, method: "UPI", status: "Completed" },
    severity: "info",
  },
  {
    id: "AUD-004",
    action: "STAFF_CREATE",
    actionLabel: "Staff Created",
    entityType: "Staff",
    entityId: "STF002",
    entityName: "Priya Sen",
    performedBy: "System Administrator",
    timestamp: "2026-03-15T09:15:00.000Z",
    description: "Recruited Priya Sen as Personal Trainer (Strength & Hypertrophy Coach).",
    previousValue: null,
    updatedValue: { id: "STF002", name: "Priya Sen", role: "Personal Trainer", salary: 48000 },
    severity: "info",
  },
  {
    id: "AUD-005",
    action: "MEMBER_CREATE",
    actionLabel: "Member Registered",
    entityType: "Member",
    entityId: "GYM003",
    entityName: "David Miller",
    performedBy: "Priya Sen (Staff)",
    timestamp: "2026-04-10T11:00:00.000Z",
    description: "Enrolled David Miller under VIP Annual plan.",
    previousValue: null,
    updatedValue: { id: "GYM003", name: "David Miller", plan: "VIP Annual", status: "Active" },
    severity: "info",
  },
  {
    id: "AUD-006",
    action: "PAYMENT_PARTIAL",
    actionLabel: "Partial Payment Collected",
    entityType: "Payment",
    entityId: "TXN-1003",
    entityName: "David Miller",
    performedBy: "Rajesh Khanna (Staff)",
    timestamp: "2026-08-10T14:20:00.000Z",
    description: "Recorded partial deposit of ₹5,000 for Personal Trainer package. ₹5,000 remains pending.",
    previousValue: { pendingDues: 10000 },
    updatedValue: { paid: 5000, pendingDues: 5000 },
    severity: "warning",
  },
  {
    id: "AUD-007",
    action: "ADMIN_OVERRIDE",
    actionLabel: "Admin Override Granted",
    entityType: "Attendance",
    entityId: "GYM003",
    entityName: "David Miller",
    performedBy: "Rajesh Khanna (Gym Manager)",
    timestamp: "2026-11-04T08:30:00.000Z",
    description: "Granted floor access override despite ₹17,999 outstanding dues. Reason: Member promised clearance by evening.",
    previousValue: { accessAllowed: false, outstandingDues: 17999 },
    updatedValue: { accessAllowed: true, overrideApproved: true },
    severity: "critical",
  },
  {
    id: "AUD-008",
    action: "ATTENDANCE_CHECKIN",
    actionLabel: "Member Check-In",
    entityType: "Attendance",
    entityId: "ATT-1001",
    entityName: "Alex Johnson",
    performedBy: "QR Self-Scanner",
    timestamp: "2026-11-04T06:15:00.000Z",
    description: "Alex Johnson checked in successfully via front entrance turnstile scanner.",
    previousValue: null,
    updatedValue: { memberId: "GYM001", checkIn: "06:15 AM", status: "Present" },
    severity: "info",
  },
  {
    id: "AUD-009",
    action: "STAFF_ACTIVATE",
    actionLabel: "Staff Status Changed",
    entityType: "Staff",
    entityId: "STF007",
    entityName: "Deepak Joshi",
    performedBy: "System Administrator",
    timestamp: "2026-11-04T09:00:00.000Z",
    description: "Deepak Joshi status toggled from Inactive to Active following scheduled leave.",
    previousValue: { status: "Inactive" },
    updatedValue: { status: "Active" },
    severity: "info",
  },
  {
    id: "AUD-010",
    action: "SETTINGS_UPDATE",
    actionLabel: "System Settings Saved",
    entityType: "Settings",
    entityId: "SYSTEM",
    entityName: "GymCore Configuration",
    performedBy: "Vikram Malhotra (Super Admin)",
    timestamp: "2026-11-04T09:15:00.000Z",
    description: "Updated gym operational hours and tax invoice receipt branding parameters.",
    previousValue: { currency: "INR" },
    updatedValue: { currency: "INR", updatedFields: ["openingHours", "branding"] },
    severity: "info",
  },
];

let cachedLogs: AuditRecord[] | null = null;
let auditListeners: Array<() => void> = [];

function emitAuditChange() {
  for (const listener of auditListeners) {
    listener();
  }
}

export function subscribeAuditLogs(listener: () => void): () => void {
  auditListeners = [...auditListeners, listener];
  return () => {
    auditListeners = auditListeners.filter((l) => l !== listener);
  };
}

/**
 * Gets next sequential Audit ID (AUD-001, AUD-002, ...)
 */
export function getNextAuditId(existingLogs: AuditRecord[]): string {
  let maxNum = 0;
  for (const log of existingLogs) {
    const match = log.id.match(/\d+/);
    if (match) {
      const num = parseInt(match[0], 10);
      if (num > maxNum) maxNum = num;
    }
  }
  return `AUD-${String(maxNum + 1).padStart(3, "0")}`;
}

/**
 * Retrieves audit logs sorted chronologically (newest first by default)
 */
export function getStoredAuditLogs(): AuditRecord[] {
  if (typeof window === "undefined") {
    return [...INITIAL_AUDIT_LOGS].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  if (cachedLogs) {
    return cachedLogs;
  }

  try {
    const raw = localStorage.getItem(AUDIT_STORAGE_KEY);
    if (!raw) {
      const sorted = [...INITIAL_AUDIT_LOGS].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(sorted));
      cachedLogs = sorted;
      return sorted;
    }

    const parsed: AuditRecord[] = JSON.parse(raw);
    // Ensure all initial seeds are present
    const existingIds = new Set(parsed.map((l) => l.id));
    let merged = false;
    for (const seed of INITIAL_AUDIT_LOGS) {
      if (!existingIds.has(seed.id)) {
        parsed.push(seed);
        merged = true;
      }
    }

    const sorted = parsed.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    if (merged || JSON.stringify(sorted) !== raw) {
      localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(sorted));
    }

    cachedLogs = sorted;
    return sorted;
  } catch {
    return [...INITIAL_AUDIT_LOGS].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }
}

/**
 * Logs a new administrative audit action.
 * Automatically sanitizes values, generates sequential AUD-xxx IDs, and prevents rapid duplicate spam.
 */
export function logAuditAction(params: {
  action: AuditActionType;
  actionLabel: string;
  entityType: AuditEntityType;
  entityId?: string;
  entityName?: string;
  performedBy?: string;
  description: string;
  previousValue?: Record<string, unknown> | null;
  updatedValue?: Record<string, unknown> | null;
  severity?: AuditSeverity;
  timestamp?: string;
}): AuditRecord {
  const currentLogs = getStoredAuditLogs();
  const timestamp = params.timestamp || new Date().toISOString();

  // Deduplication guard: ignore exact identical action within 1.5 seconds on same entity
  const recentDuplicate = currentLogs.find((l) => {
    const isSameEntity = l.entityId === params.entityId && l.action === params.action;
    const timeDiffMs = Math.abs(new Date(timestamp).getTime() - new Date(l.timestamp).getTime());
    return isSameEntity && timeDiffMs < 1500;
  });

  if (recentDuplicate) {
    return recentDuplicate;
  }

  const newId = getNextAuditId(currentLogs);

  const newRecord: AuditRecord = {
    id: newId,
    action: params.action,
    actionLabel: params.actionLabel,
    entityType: params.entityType,
    entityId: params.entityId,
    entityName: params.entityName,
    performedBy: params.performedBy || "Administrator (System)",
    timestamp,
    description: params.description,
    previousValue: sanitizeAuditValue(params.previousValue),
    updatedValue: sanitizeAuditValue(params.updatedValue),
    severity: params.severity || "info",
  };

  const nextLogs = [newRecord, ...currentLogs].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  cachedLogs = nextLogs;

  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(nextLogs));
    } catch (err) {
      console.error("Failed to persist audit log:", err);
    }
  }

  emitAuditChange();
  return newRecord;
}

/**
 * Formats audit logs into a CSV string for regulatory and export requirements.
 */
export function generateAuditCsv(records: AuditRecord[]): string {
  const headers = [
    "Audit ID",
    "Timestamp (ISO)",
    "Action",
    "Entity Type",
    "Entity ID",
    "Entity Name",
    "Performed By",
    "Severity",
    "Description",
  ];

  const rows = records.map((r) => [
    `"${r.id}"`,
    `"${r.timestamp}"`,
    `"${r.actionLabel}"`,
    `"${r.entityType}"`,
    `"${r.entityId || ""}"`,
    `"${r.entityName || ""}"`,
    `"${r.performedBy}"`,
    `"${r.severity}"`,
    `"${r.description.replace(/"/g, '""')}"`,
  ]);

  return [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
}

