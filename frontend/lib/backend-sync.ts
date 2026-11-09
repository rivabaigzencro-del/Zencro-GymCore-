/**
 * GYMCORE Backend Sync & Adaptation Layer
 * Connects FastAPI REST APIs (Days 1–7) with frontend state stores.
 * Normalizes backend schemas (full_name, amount_paise, ISO timestamps)
 * to frontend formats, maintaining reactivity and RBAC compliance.
 */

import {
  api,
  getStoredAuthToken,
  getActiveSession,
  isDemoModeEnabled,
} from "./api-client";
import {
  type Member,
  type AttendanceRecord,
  type PaymentRecord,
  type DueItem,
  type MembershipPlanItem,
  type StaffMember,
  saveMembers,
  getStoredMembers,
  saveAttendance,
  getStoredAttendance,
  savePayments,
  getStoredPayments,
  saveDues,
  savePlans,
  getStoredPlans,
  saveStaff,
  getStoredStaff,
} from "./mock-data";
import {
  type AuditRecord,
  type AuditActionType,
  type AuditEntityType,
  getStoredAuditLogs,
  AUDIT_STORAGE_KEY,
} from "./audit-trail";

export function isBackendConnected(): boolean {
  return !!getStoredAuthToken() && !isDemoModeEnabled();
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * MEMBERS MODULE SYNC
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncMembersFromBackend(): Promise<{ success: boolean; members: Member[]; error?: string }> {
  if (!getStoredAuthToken() && !isDemoModeEnabled()) {
    return { success: false, members: getStoredMembers(), error: "Not authenticated" };
  }
  const res = await api.members.list({ page: 1, page_size: 100 });
  if (res.success && res.data) {
    const backendMembers: Member[] = res.data.items.map((item) => {
      const statusMap: Record<string, "Active" | "Expired" | "Frozen"> = {
        ACTIVE: "Active",
        FROZEN: "Frozen",
        EXPIRED: "Expired",
        INACTIVE: "Expired",
        CANCELLED: "Expired",
      };
      return {
        id: String(item.id),
        name: item.full_name,
        email: item.email || "",
        phone: item.phone || "",
        plan: "Standard",
        joinDate: item.created_at ? new Date(item.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "Today",
        status: statusMap[item.status] || "Active",
        emergencyContact: item.emergency_contact_name || undefined,
        address: item.address || undefined,
      };
    });
    saveMembers(backendMembers);
    return { success: true, members: backendMembers };
  }
  return { success: false, members: getStoredMembers(), error: res.error };
}

export async function createMemberOnBackend(data: {
  name: string;
  email?: string;
  phone?: string;
  emergencyContact?: string;
  address?: string;
}): Promise<{ success: boolean; member?: Member; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.members.create({
      full_name: data.name.trim(),
      email: data.email?.trim() || undefined,
      phone: data.phone?.trim() || undefined,
      emergency_contact_name: data.emergencyContact?.trim() || undefined,
      address: data.address?.trim() || undefined,
    });
    if (!res.success || !res.data) {
      return { success: false, error: res.error || "Failed to create member on backend" };
    }
  }
  return { success: true };
}

export async function updateMemberOnBackend(
  id: string,
  data: {
    name?: string;
    email?: string;
    phone?: string;
    emergencyContact?: string;
    address?: string;
  }
): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.members.update(id, {
      full_name: data.name?.trim(),
      email: data.email?.trim(),
      phone: data.phone?.trim(),
      emergency_contact_name: data.emergencyContact?.trim(),
      address: data.address?.trim(),
    });
    if (!res.success) {
      return { success: false, error: res.error || "Failed to update member on backend" };
    }
  }
  return { success: true };
}

export async function deleteMemberOnBackend(id: string): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.members.delete(id);
    if (!res.success) {
      return { success: false, error: res.error || "Failed to deactivate member on backend" };
    }
  }
  return { success: true };
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * ATTENDANCE MODULE SYNC
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncAttendanceFromBackend(): Promise<{ success: boolean; records: AttendanceRecord[]; error?: string }> {
  const token = getStoredAuthToken();
  if (!token) {
    return { success: false, records: getStoredAttendance(), error: "Not authenticated" };
  }
  const res = await api.attendance.getToday();
  if (res.success && res.data) {
    const backendRecords: AttendanceRecord[] = res.data.map((item) => {
      const checkInDate = new Date(item.check_in_time);
      const checkInTimeStr = checkInDate.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      const checkOutTimeStr = item.check_out_time
        ? new Date(item.check_out_time).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        : undefined;

      return {
        id: String(item.id),
        memberId: String(item.member_id),
        memberName: item.member_name,
        memberPlan: "Standard",
        date: checkInDate.toISOString().slice(0, 10),
        checkInTime: checkInTimeStr,
        checkOutTime: checkOutTimeStr,
        status: (item.check_out_time ? "Checked Out" : "Present") as AttendanceRecord["status"],
        isOverride: !!item.override,
        overrideReason: item.override ? "Authorized administrative override" : undefined,
      };
    });
    saveAttendance(backendRecords);
    return { success: true, records: backendRecords };
  }
  return { success: false, records: getStoredAttendance(), error: res.error };
}

export async function checkInOnBackend(data: {
  memberId: string;
  override?: boolean;
  overrideReason?: string;
}): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.attendance.checkIn({
      member_id: data.memberId,
      override: !!data.override,
      override_reason: data.overrideReason?.trim() || undefined,
    });
    if (!res.success) {
      return { success: false, error: res.error || "Check-in failed" };
    }
  }
  return { success: true };
}

export async function checkOutOnBackend(attendanceId: string, notes?: string): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.attendance.checkOut(attendanceId, { notes });
    if (!res.success) {
      return { success: false, error: res.error || "Check-out failed" };
    }
  }
  return { success: true };
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * PAYMENTS & INVOICES MODULE SYNC
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncPaymentsFromBackend(): Promise<{ success: boolean; payments: PaymentRecord[]; error?: string }> {
  const token = getStoredAuthToken();
  if (!token) {
    return { success: false, payments: getStoredPayments(), error: "Not authenticated" };
  }
  const res = await api.payments.list({ page: 1, page_size: 100 });
  if (res.success && res.data) {
    const backendPayments: PaymentRecord[] = res.data.items.map((item) => {
      const methodMap: Record<string, "Cash" | "UPI" | "Card" | "Bank Transfer"> = {
        CASH: "Cash",
        UPI: "UPI",
        CARD: "Card",
        BANK_TRANSFER: "Bank Transfer",
        CHEQUE: "Bank Transfer",
      };
      const statusMap: Record<string, "Paid" | "Pending" | "Refunded"> = {
        COMPLETED: "Paid",
        PENDING: "Pending",
        FAILED: "Pending",
        REFUNDED: "Refunded",
        PARTIALLY_REFUNDED: "Paid",
        REVERSED: "Refunded",
      };

      const pDate = new Date(item.payment_date);
      const dateStr = pDate.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });

      return {
        id: String(item.id),
        receiptNumber: item.receipt_number || `RCP-${String(item.id).slice(-4)}`,
        memberId: String(item.member_id),
        memberName: "Gym Member",
        amount: Math.round(item.amount_paise / 100),
        paymentDate: dateStr,
        method: methodMap[item.payment_method] || "UPI",
        description: item.notes || "Membership Fee Payment",
        status: statusMap[item.payment_status] || "Paid",
      };
    });
    savePayments(backendPayments);
    return { success: true, payments: backendPayments };
  }
  return { success: false, payments: getStoredPayments(), error: res.error };
}

export async function recordPaymentOnBackend(data: {
  memberId: string;
  amount: number;
  method: "Cash" | "UPI" | "Card" | "Bank Transfer";
  invoiceId?: string;
  notes?: string;
}): Promise<{ success: boolean; receiptNumber?: string; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const methodEnumMap: Record<string, "CASH" | "UPI" | "CARD" | "BANK_TRANSFER" | "CHEQUE"> = {
      Cash: "CASH",
      UPI: "UPI",
      Card: "CARD",
      "Bank Transfer": "BANK_TRANSFER",
    };
    const res = await api.payments.create({
      member_id: data.memberId,
      amount_paise: Math.round(data.amount * 100),
      payment_method: methodEnumMap[data.method] || "UPI",
      invoice_id: data.invoiceId,
      notes: data.notes?.trim() || undefined,
      auto_generate_receipt: true,
    });
    if (!res.success || !res.data) {
      return { success: false, error: res.error || "Payment recording failed" };
    }
    return { success: true, receiptNumber: res.data.receipt_number };
  }
  return { success: true, receiptNumber: `RCP-${Date.now().toString().slice(-4)}` };
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * DUES & INVOICES SYNC
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncDuesFromBackend(): Promise<{ success: boolean; dues: DueItem[]; error?: string }> {
  const token = getStoredAuthToken();
  if (!token) return { success: false, dues: [], error: "Not authenticated" };

  const res = await api.invoices.list({ page: 1, page_size: 100, status: "ISSUED" });
  if (res.success && res.data) {
    const backendDues: DueItem[] = res.data.items.map((inv) => ({
      id: String(inv.id),
      memberId: String(inv.member_id),
      memberName: "Member",
      memberPlan: "Standard",
      totalAmount: Math.round(inv.amount_paise / 100),
      amountPaid: Math.round(inv.paid_amount_paise / 100),
      remainingBalance: Math.round(inv.balance_amount_paise / 100),
      dueDate: inv.due_date,
      planName: inv.description || "Gym Membership Dues",
      description: inv.description || "Gym Membership Dues",
      status: (inv.invoice_status === "PAID" ? "Paid" : inv.paid_amount_paise > 0 ? "Partially Paid" : "Pending") as DueItem["status"],
      createdAt: inv.issue_date,
      payments: [],
    }));
    saveDues(backendDues);
    return { success: true, dues: backendDues };
  }
  return { success: false, dues: [], error: res.error };
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * MEMBERSHIP PLANS SYNC
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncPlansFromBackend(): Promise<{ success: boolean; plans: MembershipPlanItem[]; error?: string }> {
  const token = getStoredAuthToken();
  if (!token) return { success: false, plans: getStoredPlans(), error: "Not authenticated" };

  const res = await api.membershipPlans.list({ include_inactive: false });
  if (res.success && res.data) {
    const backendPlans: MembershipPlanItem[] = res.data.map((p) => {
      const months = Math.max(1, Math.round(p.duration_days / 30));
      return {
        id: String(p.id),
        name: p.name,
        durationMonths: months,
        durationLabel: `${months} Month(s)`,
        tagline: "Full access gym membership",
        price: Math.round(p.price_paise / 100),
        description: p.description || `${p.name} Membership Plan`,
        features: ["Full Gym Floor Access", "Locker Room Access"],
      };
    });
    savePlans(backendPlans);
    return { success: true, plans: backendPlans };
  }
  return { success: false, plans: getStoredPlans(), error: res.error };
}

export async function createPlanOnBackend(data: {
  name: string;
  durationMonths: number;
  price: number;
  description?: string;
}): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.membershipPlans.create({
      name: data.name.trim(),
      duration_days: data.durationMonths * 30,
      price_paise: Math.round(data.price * 100),
      description: data.description?.trim(),
    });
    if (!res.success) {
      return { success: false, error: res.error || "Failed to create membership plan" };
    }
  }
  return { success: true };
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * STAFF MODULE SYNC (RBAC ENFORCED)
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncStaffFromBackend(): Promise<{ success: boolean; staff: StaffMember[]; error?: string }> {
  const token = getStoredAuthToken();
  const session = getActiveSession();
  if (!token || session?.role === "Front Desk") {
    return { success: false, staff: getStoredStaff(), error: "Front Desk does not have staff permissions" };
  }
  const res = await api.staff.list();
  if (res.success && res.data) {
    const backendStaff: StaffMember[] = res.data.items.map((s) => ({
      id: String(s.id),
      name: s.name || s.email.split("@")[0].toUpperCase(),
      role: s.role === "MANAGER" ? "Gym Manager" : "Receptionist",
      email: s.email,
      phone: s.phone || "9876543210",
      joiningDate: s.created_at ? new Date(s.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "Today",
      status: s.is_active ? "Active" : "Inactive",
      salary: 45000,
    }));
    saveStaff(backendStaff);
    return { success: true, staff: backendStaff };
  }
  return { success: false, staff: getStoredStaff(), error: res.error };
}

export async function createStaffOnBackend(data: {
  name: string;
  email: string;
  password?: string;
  role: "Manager" | "Front Desk";
  phone?: string;
}): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.staff.create({
      email: data.email.trim().toLowerCase(),
      name: data.name.trim(),
      password: data.password || "StaffPass@123",
      role: data.role === "Manager" ? "MANAGER" : "FRONT_DESK",
      phone: data.phone?.trim(),
    });
    if (!res.success) {
      return { success: false, error: res.error || "Failed to create staff account" };
    }
  }
  return { success: true };
}

export async function updateStaffStatusOnBackend(
  id: string,
  isActive: boolean,
  reason?: string
): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.staff.updateStatus(id, { is_active: isActive, reason });
    if (!res.success) {
      return { success: false, error: res.error || "Failed to update staff status" };
    }
  }
  return { success: true };
}

export async function updateStaffRoleOnBackend(
  id: string,
  role: "Manager" | "Front Desk",
  reason?: string
): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  if (token) {
    const res = await api.staff.updateRole(id, {
      role: role === "Manager" ? "MANAGER" : "FRONT_DESK",
      reason,
    });
    if (!res.success) {
      return { success: false, error: res.error || "Failed to update staff role" };
    }
  }
  return { success: true };
}

/**
 * ─────────────────────────────────────────────────────────────────────────────
 * AUDIT LOGS MODULE SYNC (READ ONLY)
 * ─────────────────────────────────────────────────────────────────────────────
 */
export async function syncAuditLogsFromBackend(params?: {
  action?: string;
  resource_type?: string;
}): Promise<{ success: boolean; logs: AuditRecord[]; error?: string }> {
  const token = getStoredAuthToken();
  const session = getActiveSession();
  if (!token || session?.role === "Front Desk") {
    return { success: false, logs: getStoredAuditLogs(), error: "Audit logs restricted to Owner/Manager" };
  }
  const res = await api.audit.list(params);
  if (res.success && res.data) {
    const backendLogs: AuditRecord[] = res.data.items.map((log) => ({
      id: String(log.id),
      timestamp: log.created_at,
      action: log.action as AuditActionType,
      actionLabel: log.action.replace(/_/g, " "),
      entityType: (log.resource_type || "System") as AuditEntityType,
      entityId: log.resource_id || String(log.id),
      entityName: log.resource_type || "Record",
      performedBy: log.user_id ? "Staff Member" : "System",
      description: `${log.action} on ${log.resource_type} (${log.resource_id || "global"})`,
      severity: (log.action.includes("DELETE") || log.action.includes("CANCEL") ? "warning" : "info") as AuditRecord["severity"],
    }));
    if (typeof window !== "undefined") {
      localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(backendLogs));
      window.dispatchEvent(new Event("gymcore_audit_change"));
    }
    return { success: true, logs: backendLogs };
  }
  return { success: false, logs: getStoredAuditLogs(), error: res.error };
}
