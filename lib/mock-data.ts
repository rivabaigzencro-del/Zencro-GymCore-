import { formatIndianMobile } from "./phone-utils.ts";
import {
  sortMembersByNumericId,
  sortStaffByNumericId,
  getNextMemberId,
  getNextStaffId,
  updateMemberCounterHighWaterMark,
  updateStaffCounterHighWaterMark,
} from "./id-utils.ts";
import { logAuditAction } from "./audit-trail.ts";

export * from "./id-utils.ts";
export * from "./phone-utils.ts";

export type MemberStatus = "Active" | "Expired" | "Frozen";
export type MembershipPlan = "Basic" | "Standard" | "Premium" | string;

export type Member = {
  id: string;
  name: string;
  email: string;
  phone: string;
  plan: MembershipPlan;
  joinDate: string;
  status: MemberStatus;
  emergencyContact?: string;
  address?: string;
  gender?: string;
  dob?: string;
  validUntil?: string;
  totalVisits?: number;
  lastVisit?: string;
};

export type MembershipPlanItem = {
  id: string;
  name: string;
  price: number;
  durationMonths: number;
  durationLabel: string;
  tagline: string;
  features: string[];
  popular?: boolean;
  color?: string;
  badge?: string;
};

export const INITIAL_MEMBERS: Member[] = [
  {
    id: "GYM001",
    name: "Alex Johnson",
    email: "alex@example.com",
    phone: "+91 98765 43210",
    plan: "Premium",
    joinDate: "12 Jan 2026",
    status: "Active",
    emergencyContact: "+91 98765 00001 (Sarah Johnson - Spouse)",
    address: "Flat 402, Golden Heights, MG Road, Bangalore",
    gender: "Male",
    dob: "1994-06-15",
    validUntil: "12 Jan 2027",
    totalVisits: 84,
    lastVisit: "Today, 08:30 AM",
  },
  {
    id: "GYM002",
    name: "Rahul Sharma",
    email: "rahul@example.com",
    phone: "+91 98765 12345",
    plan: "Standard",
    joinDate: "18 Feb 2026",
    status: "Active",
    emergencyContact: "+91 98765 00002 (Sunita Sharma - Mother)",
    address: "Villa 12, Palm Meadows, Whitefield, Bangalore",
    gender: "Male",
    dob: "1998-03-22",
    validUntil: "18 Aug 2026",
    totalVisits: 42,
    lastVisit: "Yesterday, 06:15 PM",
  },
  {
    id: "GYM003",
    name: "David Miller",
    email: "david@example.com",
    phone: "+91 98765 67890",
    plan: "Premium",
    joinDate: "05 Mar 2026",
    status: "Expired",
    emergencyContact: "+91 98765 00003 (Emma Miller - Sister)",
    address: "24 Kensington Park, Indiranagar, Bangalore",
    gender: "Male",
    dob: "1991-11-08",
    validUntil: "05 Sep 2026",
    totalVisits: 65,
    lastVisit: "2 weeks ago",
  },
  {
    id: "GYM004",
    name: "Arjun Patel",
    email: "arjun@example.com",
    phone: "+91 98765 98765",
    plan: "Basic",
    joinDate: "21 Apr 2026",
    status: "Frozen",
    emergencyContact: "+91 98765 00004 (Kavita Patel - Wife)",
    address: "Sector 4, HSR Layout, Bangalore",
    gender: "Male",
    dob: "1995-09-30",
    validUntil: "21 Oct 2026",
    totalVisits: 19,
    lastVisit: "1 month ago",
  },
  {
    id: "GYM005",
    name: "Michael Brown",
    email: "michael@example.com",
    phone: "+91 98765 55555",
    plan: "Standard",
    joinDate: "10 May 2026",
    status: "Active",
    emergencyContact: "+91 98765 00005 (John Brown - Brother)",
    address: "88 Orchid Enclave, Koramangala, Bangalore",
    gender: "Male",
    dob: "1999-01-14",
    validUntil: "10 Nov 2026",
    totalVisits: 31,
    lastVisit: "Today, 07:45 AM",
  },
  {
    id: "GYM006",
    name: "Rihan Fazlani",
    email: "rihan@example.com",
    phone: "+91 98765 24680",
    plan: "Premium",
    joinDate: "01 Jun 2026",
    status: "Active",
    emergencyContact: "+91 98765 00006 (Imran Fazlani - Father)",
    address: "Penthouse 3, Prestige Tower, Richmond Town, Bangalore",
    gender: "Male",
    dob: "1997-07-19",
    validUntil: "01 Jun 2027",
    totalVisits: 56,
    lastVisit: "Today, 09:15 AM",
  },
];

export const INITIAL_PLANS: MembershipPlanItem[] = [
  {
    id: "plan-basic",
    name: "Basic",
    price: 1499,
    durationMonths: 1,
    durationLabel: "1 Month",
    tagline: "Essential gym floor access for self-paced training",
    popular: false,
    color: "border-border",
    badge: "STARTER",
    features: [
      "Access to full gym floor & free weights",
      "Locker room & shower facilities",
      "General equipment orientation session",
      "GYMCORE mobile check-in support",
      "Water station & locker access",
    ],
  },
  {
    id: "plan-standard",
    name: "Standard",
    price: 3999,
    durationMonths: 3,
    durationLabel: "3 Months",
    tagline: "Balanced fitness with cardio zone and group classes",
    popular: true,
    color: "border-[#C9A04F]",
    badge: "MOST POPULAR",
    features: [
      "All Basic Plan amenities included",
      "Cardio & functional cross-training area",
      "Steam room & recovery sauna access",
      "1 Complimentary personal trainer session / mo",
      "Free quarterly fitness & BMI assessment",
      "1 Free membership freeze per quarter (15 days)",
    ],
  },
  {
    id: "plan-premium",
    name: "Premium",
    price: 12999,
    durationMonths: 12,
    durationLabel: "12 Months (1 Year)",
    tagline: "All-inclusive VIP fitness, personal trainer & recovery",
    popular: false,
    color: "border-[#C9A04F]/60",
    badge: "BEST VALUE",
    features: [
      "All Standard Plan amenities included",
      "Unlimited group classes (HIIT, Yoga, Zumba)",
      "Personalized nutrition & diet chart by certified coach",
      "2 Free guest passes every month",
      "Dedicated personal locker & towel service",
      "Priority equipment & slot booking",
      "Zero membership freeze fees anytime",
    ],
  },
];

const MEMBERS_STORAGE_KEY = "gymcore_members_data";
const PLANS_STORAGE_KEY = "gymcore_plans_data";

// ---------------- Members Store ----------------

let cachedMembers: Member[] | null = null;
let memberListeners: Array<() => void> = [];

function emitMemberChange() {
  for (const listener of memberListeners) {
    listener();
  }
}

export function subscribeMembers(listener: () => void) {
  memberListeners = [...memberListeners, listener];
  return () => {
    memberListeners = memberListeners.filter((l) => l !== listener);
  };
}

export function getStoredMembers(): Member[] {
  if (typeof window === "undefined") {
    return sortMembersByNumericId(INITIAL_MEMBERS);
  }
  if (cachedMembers) {
    return cachedMembers;
  }
  try {
    const raw = localStorage.getItem(MEMBERS_STORAGE_KEY);
    if (!raw) {
      const sorted = sortMembersByNumericId(INITIAL_MEMBERS);
      localStorage.setItem(MEMBERS_STORAGE_KEY, JSON.stringify(sorted));
      sorted.forEach((m) => updateMemberCounterHighWaterMark(m.id));
      cachedMembers = sorted;
      return sorted;
    }
    const parsed: Member[] = JSON.parse(raw);

    // Ensure all initial demo members exist (e.g. if GYM006 was added in code after initial storage set)
    const existingIds = new Set(parsed.map((m) => m.id.toLowerCase()));
    let merged = false;
    for (const initMember of INITIAL_MEMBERS) {
      if (!existingIds.has(initMember.id.toLowerCase())) {
        parsed.push(initMember);
        merged = true;
      }
    }

    const sorted = sortMembersByNumericId(parsed);
    sorted.forEach((m) => updateMemberCounterHighWaterMark(m.id));

    if (merged || JSON.stringify(sorted) !== raw) {
      localStorage.setItem(MEMBERS_STORAGE_KEY, JSON.stringify(sorted));
    }

    cachedMembers = sorted;
    return sorted;
  } catch {
    return sortMembersByNumericId(INITIAL_MEMBERS);
  }
}

export function saveMembers(members: Member[]): void {
  const sorted = sortMembersByNumericId(members);
  cachedMembers = sorted;
  if (typeof window !== "undefined") {
    try {
      sorted.forEach((m) => updateMemberCounterHighWaterMark(m.id));
      localStorage.setItem(MEMBERS_STORAGE_KEY, JSON.stringify(sorted));
    } catch (err) {
      console.error("Failed to save members to localStorage:", err);
    }
  }
  emitMemberChange();
}

export function getMemberById(id: string): Member | undefined {
  const members = getStoredMembers();
  return members.find(
    (m) => m.id.toLowerCase() === id.toLowerCase()
  );
}

export function addMember(newMember: Omit<Member, "id"> & { id?: string }): Member {
  const members = getStoredMembers();
  const id = newMember.id && newMember.id.trim() ? newMember.id.trim() : getNextMemberId(members);
  updateMemberCounterHighWaterMark(id);

  const formattedMember: Member = {
    ...newMember,
    id,
    phone: formatIndianMobile(newMember.phone),
  };
  const next = sortMembersByNumericId([
    formattedMember,
    ...members.filter((m) => m.id.toLowerCase() !== id.toLowerCase()),
  ]);
  saveMembers(next);

  logAuditAction({
    action: "MEMBER_CREATE",
    actionLabel: "Member Enrolled",
    entityType: "Member",
    entityId: formattedMember.id,
    entityName: formattedMember.name,
    performedBy: "Front Desk Administrator",
    description: `Enrolled new member ${formattedMember.name} (${formattedMember.id}) on ${formattedMember.plan} plan.`,
    previousValue: null,
    updatedValue: {
      id: formattedMember.id,
      name: formattedMember.name,
      email: formattedMember.email,
      phone: formattedMember.phone,
      plan: formattedMember.plan,
      status: formattedMember.status,
    },
    severity: "info",
  });

  return formattedMember;
}

export function updateMember(updated: Member): Member[] {
  const members = getStoredMembers();
  const previous = members.find((m) => m.id.toLowerCase() === updated.id.toLowerCase());
  const formattedMember: Member = {
    ...updated,
    phone: formatIndianMobile(updated.phone),
  };
  // IDs remain completely stable when editing
  const next = sortMembersByNumericId(members.map((m) => (m.id === updated.id ? formattedMember : m)));
  saveMembers(next);

  logAuditAction({
    action: "MEMBER_UPDATE",
    actionLabel: "Member Profile Updated",
    entityType: "Member",
    entityId: formattedMember.id,
    entityName: formattedMember.name,
    performedBy: "Staff Administrator",
    description: `Updated member profile details for ${formattedMember.name} (${formattedMember.id}).`,
    previousValue: previous
      ? { name: previous.name, plan: previous.plan, status: previous.status, phone: previous.phone }
      : null,
    updatedValue: {
      name: formattedMember.name,
      plan: formattedMember.plan,
      status: formattedMember.status,
      phone: formattedMember.phone,
    },
    severity: "info",
  });

  return next;
}

export function deleteMember(id: string): Member[] {
  const members = getStoredMembers();
  const target = members.find((m) => m.id.toLowerCase() === id.toLowerCase());
  // DO NOT decrease the member ID counter so deleted IDs are NEVER reused
  const next = members.filter((m) => m.id.toLowerCase() !== id.toLowerCase());
  saveMembers(next);

  logAuditAction({
    action: "MEMBER_DELETE",
    actionLabel: "Member Account Deleted",
    entityType: "Member",
    entityId: id,
    entityName: target?.name || id,
    performedBy: "Senior Administrator",
    description: `Permanently removed member ${target?.name || id} (${id}) from database. ID retired.`,
    previousValue: target ? { id: target.id, name: target.name, plan: target.plan } : null,
    updatedValue: null,
    severity: "critical",
  });

  return next;
}

export function toggleFreezeMember(id: string): Member | undefined {
  const members = getStoredMembers();
  const target = members.find((m) => m.id.toLowerCase() === id.toLowerCase());
  if (!target) return undefined;

  const newStatus: MemberStatus = target.status === "Frozen" ? "Active" : "Frozen";
  const updated: Member = { ...target, status: newStatus };
  updateMember(updated);

  logAuditAction({
    action: newStatus === "Frozen" ? "MEMBERSHIP_FREEZE" : "MEMBERSHIP_UNFREEZE",
    actionLabel: `Membership ${newStatus === "Frozen" ? "Frozen" : "Unfrozen"}`,
    entityType: "Membership",
    entityId: updated.id,
    entityName: updated.name,
    performedBy: "Desk Manager",
    description: `Toggled membership status for ${updated.name} (${updated.id}) to ${newStatus}.`,
    previousValue: { status: target.status },
    updatedValue: { status: newStatus },
    severity: "warning",
  });

  return updated;
}

export function renewMember(id: string, durationMonths = 12): Member | undefined {
  const members = getStoredMembers();
  const target = members.find((m) => m.id.toLowerCase() === id.toLowerCase());
  if (!target) return undefined;

  // Calculate new validUntil date
  const now = new Date();
  now.setMonth(now.getMonth() + durationMonths);
  const validUntilStr = now.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const updated: Member = {
    ...target,
    status: "Active",
    validUntil: validUntilStr,
  };
  updateMember(updated);

  logAuditAction({
    action: "MEMBERSHIP_RENEW",
    actionLabel: "Membership Renewed",
    entityType: "Membership",
    entityId: target.id,
    entityName: target.name,
    performedBy: "Front Desk Administrator",
    description: `Renewed membership for ${target.name} (${target.id}) by ${durationMonths} months until ${validUntilStr}.`,
    previousValue: { validUntil: target.validUntil, status: target.status },
    updatedValue: { validUntil: validUntilStr, status: "Active" },
    severity: "info",
  });

  return updated;
}

// ---------------- Plans Store ----------------

let cachedPlans: MembershipPlanItem[] | null = null;
let planListeners: Array<() => void> = [];

function emitPlanChange() {
  for (const listener of planListeners) {
    listener();
  }
}

export function subscribePlans(listener: () => void) {
  planListeners = [...planListeners, listener];
  return () => {
    planListeners = planListeners.filter((l) => l !== listener);
  };
}

export function getStoredPlans(): MembershipPlanItem[] {
  if (typeof window === "undefined") {
    return INITIAL_PLANS;
  }
  if (cachedPlans) {
    return cachedPlans;
  }
  try {
    const raw = localStorage.getItem(PLANS_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(PLANS_STORAGE_KEY, JSON.stringify(INITIAL_PLANS));
      cachedPlans = INITIAL_PLANS;
      return INITIAL_PLANS;
    }
    cachedPlans = JSON.parse(raw);
    return cachedPlans || INITIAL_PLANS;
  } catch {
    return INITIAL_PLANS;
  }
}

export function savePlans(plans: MembershipPlanItem[]): void {
  cachedPlans = plans;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(PLANS_STORAGE_KEY, JSON.stringify(plans));
    } catch (err) {
      console.error("Failed to save plans to localStorage:", err);
    }
  }
  emitPlanChange();
}

export function addPlan(newPlan: MembershipPlanItem): MembershipPlanItem[] {
  const plans = getStoredPlans();
  const next = [...plans, newPlan];
  savePlans(next);
  return next;
}

export function updatePlan(updated: MembershipPlanItem): MembershipPlanItem[] {
  const plans = getStoredPlans();
  const next = plans.map((p) => (p.id === updated.id ? updated : p));
  savePlans(next);
  return next;
}

export function deletePlan(planId: string): MembershipPlanItem[] {
  const plans = getStoredPlans();
  const next = plans.filter((p) => p.id !== planId);
  savePlans(next);
  return next;
}

export function assignMembershipToMember(
  memberId: string,
  planName: string,
  durationMonths: number
): { success: boolean; message: string; member?: Member } {
  const member = getMemberById(memberId);
  if (!member) {
    return { success: false, message: `Member with ID ${memberId} not found.` };
  }

  const now = new Date();
  now.setMonth(now.getMonth() + durationMonths);
  const newValidUntil = now.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const updated: Member = {
    ...member,
    plan: planName,
    status: "Active",
    validUntil: newValidUntil,
  };

  updateMember(updated);

  logAuditAction({
    action: "MEMBERSHIP_ASSIGN",
    actionLabel: "Membership Plan Assigned",
    entityType: "Membership",
    entityId: member.id,
    entityName: member.name,
    performedBy: "Front Desk Administrator",
    description: `Assigned ${planName} plan (${durationMonths} months) to ${member.name} (${member.id}), valid until ${newValidUntil}.`,
    previousValue: { plan: member.plan, validUntil: member.validUntil },
    updatedValue: { plan: planName, validUntil: newValidUntil, status: "Active" },
    severity: "info",
  });

  return {
    success: true,
    message: `${member.name} (${member.id}) has been assigned to the ${planName} plan until ${newValidUntil}.`,
    member: updated,
  };
}

// ==========================================
// ---------------- Attendance Store --------
// ==========================================

export type AttendanceStatus = "Present" | "Checked Out";

export type AttendanceRecord = {
  id: string;
  memberId: string;
  memberName: string;
  memberPlan: string;
  date: string;
  checkInTime: string;
  checkOutTime?: string;
  status: AttendanceStatus;
  isOverride?: boolean;
  overrideReason?: string;
  overriddenBy?: string;
};

export function getTodayDateString(): string {
  return new Date().toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function getCurrentTimeString(): string {
  return new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export const INITIAL_ATTENDANCE: AttendanceRecord[] = [
  {
    id: "ATT-1001",
    memberId: "GYM001",
    memberName: "Alex Johnson",
    memberPlan: "Premium",
    date: getTodayDateString(),
    checkInTime: "08:30 AM",
    status: "Present",
  },
  {
    id: "ATT-1002",
    memberId: "GYM002",
    memberName: "Rahul Sharma",
    memberPlan: "Standard",
    date: getTodayDateString(),
    checkInTime: "07:15 AM",
    checkOutTime: "08:45 AM",
    status: "Checked Out",
  },
  {
    id: "ATT-1003",
    memberId: "GYM005",
    memberName: "Michael Brown",
    memberPlan: "Standard",
    date: getTodayDateString(),
    checkInTime: "07:45 AM",
    status: "Present",
  },
  {
    id: "ATT-1004",
    memberId: "GYM006",
    memberName: "Rihan Fazlani",
    memberPlan: "Premium",
    date: getTodayDateString(),
    checkInTime: "09:15 AM",
    status: "Present",
  },
  {
    id: "ATT-1005",
    memberId: "GYM001",
    memberName: "Alex Johnson",
    memberPlan: "Premium",
    date: "03 Nov 2026",
    checkInTime: "08:30 AM",
    checkOutTime: "10:00 AM",
    status: "Checked Out",
  },
  {
    id: "ATT-1006",
    memberId: "GYM004",
    memberName: "Arjun Patel",
    memberPlan: "Basic",
    date: "03 Nov 2026",
    checkInTime: "06:45 PM",
    checkOutTime: "08:00 PM",
    status: "Checked Out",
  },
  {
    id: "ATT-1007",
    memberId: "GYM002",
    memberName: "Rahul Sharma",
    memberPlan: "Standard",
    date: "02 Nov 2026",
    checkInTime: "07:30 AM",
    checkOutTime: "09:00 AM",
    status: "Checked Out",
  },
];

const ATTENDANCE_STORAGE_KEY = "gymcore_attendance_data";
let cachedAttendance: AttendanceRecord[] | null = null;
let attendanceListeners: Array<() => void> = [];

function emitAttendanceChange() {
  for (const listener of attendanceListeners) {
    listener();
  }
}

export function subscribeAttendance(listener: () => void) {
  attendanceListeners = [...attendanceListeners, listener];
  return () => {
    attendanceListeners = attendanceListeners.filter((l) => l !== listener);
  };
}

export function getStoredAttendance(): AttendanceRecord[] {
  if (typeof window === "undefined") {
    return INITIAL_ATTENDANCE;
  }
  if (cachedAttendance) {
    return cachedAttendance;
  }
  try {
    const raw = localStorage.getItem(ATTENDANCE_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(ATTENDANCE_STORAGE_KEY, JSON.stringify(INITIAL_ATTENDANCE));
      cachedAttendance = INITIAL_ATTENDANCE;
      return INITIAL_ATTENDANCE;
    }
    cachedAttendance = JSON.parse(raw);
    return cachedAttendance || INITIAL_ATTENDANCE;
  } catch {
    return INITIAL_ATTENDANCE;
  }
}

export function saveAttendance(records: AttendanceRecord[]): void {
  cachedAttendance = records;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(ATTENDANCE_STORAGE_KEY, JSON.stringify(records));
    } catch (err) {
      console.error("Failed to save attendance to localStorage:", err);
    }
  }
  emitAttendanceChange();
}

export function checkInMember(
  memberId: string,
  options?: {
    isOverride?: boolean;
    overrideReason?: string;
    overriddenBy?: string;
  }
): {
  success: boolean;
  message: string;
  record?: AttendanceRecord;
  blockedReason?: "expired" | "frozen" | "already_present" | "not_found";
} {
  const member = getMemberById(memberId);
  if (!member) {
    return { success: false, message: `Member with ID ${memberId} not found.`, blockedReason: "not_found" };
  }

  const isOverrideApproved = Boolean(options?.isOverride && options?.overrideReason?.trim());

  if (member.status === "Expired" && !isOverrideApproved) {
    return {
      success: false,
      message: `Cannot check in ${member.name}: Membership plan expired on ${member.validUntil || "earlier"}. Please renew first.`,
      blockedReason: "expired",
    };
  }

  if (member.status === "Frozen" && !isOverrideApproved) {
    return {
      success: false,
      message: `Cannot check in ${member.name}: Membership is currently frozen. Reactivate the membership to allow check-in.`,
      blockedReason: "frozen",
    };
  }

  const attendance = getStoredAttendance();
  const today = getTodayDateString();

  // Check if already checked in and still present today
  const existingActive = attendance.find(
    (a) => a.memberId.toLowerCase() === memberId.toLowerCase() && a.date === today && a.status === "Present"
  );

  if (existingActive) {
    return {
      success: false,
      message: `${member.name} is already checked in (since ${existingActive.checkInTime}) and currently on the floor.`,
      blockedReason: "already_present",
    };
  }

  const checkInTime = getCurrentTimeString();
  const nextNumber = attendance.length + 1001;
  const newRecord: AttendanceRecord = {
    id: `ATT-${nextNumber}`,
    memberId: member.id,
    memberName: member.name,
    memberPlan: member.plan,
    date: today,
    checkInTime,
    status: "Present",
    ...(isOverrideApproved
      ? {
        isOverride: true,
        overrideReason: options?.overrideReason?.trim(),
        overriddenBy: options?.overriddenBy || "Gymcore Admin",
      }
      : {}),
  };

  const nextList = [newRecord, ...attendance];
  saveAttendance(nextList);

  // Increment member visit count and update lastVisit
  const updatedMember: Member = {
    ...member,
    totalVisits: (member.totalVisits || 0) + 1,
    lastVisit: `Today, ${checkInTime}`,
  };
  updateMember(updatedMember);

  const prefix = isOverrideApproved ? `[OVERRIDE APPROVED] ` : "";

  if (isOverrideApproved) {
    logAuditAction({
      action: "ADMIN_OVERRIDE",
      actionLabel: "Admin Access Override Granted",
      entityType: "Attendance",
      entityId: member.id,
      entityName: member.name,
      performedBy: options?.overriddenBy || "Gymcore Admin",
      description: `Manual floor access override granted to ${member.name} (${member.id}) at ${checkInTime}. Reason: ${options?.overrideReason?.trim() || "Supervisor discretion"}`,
      previousValue: { hasOutstandingDues: true, overrideGranted: false },
      updatedValue: { overrideGranted: true, overrideReason: options?.overrideReason?.trim() },
      severity: "critical",
    });
  } else {
    logAuditAction({
      action: "ATTENDANCE_CHECKIN",
      actionLabel: "Member Check-In",
      entityType: "Attendance",
      entityId: member.id,
      entityName: member.name,
      performedBy: "Front Desk / QR Turnstile",
      description: `${member.name} (${member.id}) checked in successfully at ${checkInTime}.`,
      previousValue: null,
      updatedValue: { checkInTime, date: today },
      severity: "info",
    });
  }

  return {
    success: true,
    message: `${prefix}${member.name} (${member.id}) checked in successfully at ${checkInTime}.`,
    record: newRecord,
  };
}

export function checkOutMember(attendanceId: string): {
  success: boolean;
  message: string;
} {
  const attendance = getStoredAttendance();
  const record = attendance.find((a) => a.id === attendanceId);
  if (!record) {
    return { success: false, message: "Attendance record not found." };
  }

  const checkOutTime = getCurrentTimeString();
  const next = attendance.map((a) =>
    a.id === attendanceId ? { ...a, checkOutTime, status: "Checked Out" as const } : a
  );
  saveAttendance(next);

  logAuditAction({
    action: "ATTENDANCE_CHECKOUT",
    actionLabel: "Member Check-Out",
    entityType: "Attendance",
    entityId: record.memberId,
    entityName: record.memberName,
    performedBy: "Front Desk Staff",
    description: `${record.memberName} (${record.memberId}) checked out at ${checkOutTime}.`,
    previousValue: { status: "Present" },
    updatedValue: { status: "Checked Out", checkOutTime },
    severity: "info",
  });

  return {
    success: true,
    message: `${record.memberName} checked out successfully at ${checkOutTime}.`,
  };
}

// ==========================================
// ---------------- Payments Store ----------
// ==========================================

export type PaymentMethod = "Cash" | "UPI" | "Card" | "Bank Transfer";
export type PaymentStatus = "Paid" | "Pending" | "Refunded";

export type PaymentRecord = {
  id: string;
  receiptNumber: string;
  memberId: string;
  memberName: string;
  amount: number;
  paymentDate: string;
  method: PaymentMethod;
  description: string;
  reference?: string;
  status: PaymentStatus;
};

export const INITIAL_PAYMENTS: PaymentRecord[] = [
  {
    id: "TXN-1001",
    receiptNumber: "RCP-2026-001",
    memberId: "GYM001",
    memberName: "Alex Johnson",
    amount: 12999,
    paymentDate: "01 Nov 2026",
    method: "UPI",
    description: "Annual Premium Membership Plan",
    reference: "UPI/20261101/987654",
    status: "Paid",
  },
  {
    id: "TXN-1002",
    receiptNumber: "RCP-2026-002",
    memberId: "GYM002",
    memberName: "Rahul Sharma",
    amount: 3999,
    paymentDate: "02 Nov 2026",
    method: "Card",
    description: "Standard 3-Month Plan Renewal",
    reference: "CARD-VISA-8821",
    status: "Paid",
  },
  {
    id: "TXN-1003",
    receiptNumber: "RCP-2026-003",
    memberId: "GYM005",
    memberName: "Michael Brown",
    amount: 3999,
    paymentDate: "03 Nov 2026",
    method: "UPI",
    description: "Standard 3-Month Plan Membership",
    reference: "UPI/20261103/554433",
    status: "Paid",
  },
  {
    id: "TXN-1004",
    receiptNumber: "RCP-2026-004",
    memberId: "GYM006",
    memberName: "Rihan Fazlani",
    amount: 12999,
    paymentDate: "03 Nov 2026",
    method: "Bank Transfer",
    description: "Annual VIP Premium Access Pass",
    reference: "NEFT-HDFC-991823",
    status: "Paid",
  },
  {
    id: "TXN-1005",
    receiptNumber: "RCP-2026-005",
    memberId: "GYM004",
    memberName: "Arjun Patel",
    amount: 1000,
    paymentDate: "20 Sep 2026",
    method: "Cash",
    description: "Basic Plan & Locker Advance Partial Deposit",
    reference: "CASH-REC-104",
    status: "Paid",
  },
  {
    id: "TXN-1006",
    receiptNumber: "RCP-2026-006",
    memberId: "GYM003",
    memberName: "David Miller",
    amount: 12999,
    paymentDate: "04 Nov 2026",
    method: "UPI",
    description: "Annual Premium Membership Renewal",
    reference: "PENDING-DUE-01",
    status: "Pending",
  },
  {
    id: "TXN-1007",
    receiptNumber: "RCP-2026-007",
    memberId: "GYM004",
    memberName: "Arjun Patel",
    amount: 1499,
    paymentDate: "04 Nov 2026",
    method: "Cash",
    description: "Basic 1-Month Plan Membership Renewal",
    reference: "CASH-REC-108",
    status: "Paid",
  },
  {
    id: "TXN-1008",
    receiptNumber: "RCP-2026-008",
    memberId: "GYM004",
    memberName: "Arjun Patel",
    amount: 500,
    paymentDate: "01 Oct 2026",
    method: "UPI",
    description: "Gym Floor Locker Access & Padlock Fee",
    reference: "UPI/20261001/112233",
    status: "Paid",
  },
];

const PAYMENTS_STORAGE_KEY = "gymcore_payments_data";
let cachedPayments: PaymentRecord[] | null = null;
let paymentListeners: Array<() => void> = [];

function emitPaymentChange() {
  for (const listener of paymentListeners) {
    listener();
  }
}

export function subscribePayments(listener: () => void) {
  paymentListeners = [...paymentListeners, listener];
  return () => {
    paymentListeners = paymentListeners.filter((l) => l !== listener);
  };
}

export function getStoredPayments(): PaymentRecord[] {
  if (typeof window === "undefined") {
    return INITIAL_PAYMENTS;
  }
  if (cachedPayments) {
    return cachedPayments;
  }
  try {
    const raw = localStorage.getItem(PAYMENTS_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(PAYMENTS_STORAGE_KEY, JSON.stringify(INITIAL_PAYMENTS));
      cachedPayments = INITIAL_PAYMENTS;
      return INITIAL_PAYMENTS;
    }
    const parsed: PaymentRecord[] = JSON.parse(raw);
    const existingIds = new Set(parsed.map((p) => p.id.toLowerCase()));
    let merged = false;
    for (const initPayment of INITIAL_PAYMENTS) {
      if (!existingIds.has(initPayment.id.toLowerCase())) {
        parsed.push(initPayment);
        merged = true;
      }
    }
    if (merged) {
      localStorage.setItem(PAYMENTS_STORAGE_KEY, JSON.stringify(parsed));
    }
    cachedPayments = parsed;
    return cachedPayments || INITIAL_PAYMENTS;
  } catch {
    return INITIAL_PAYMENTS;
  }
}

export function savePayments(payments: PaymentRecord[]): void {
  cachedPayments = payments;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(PAYMENTS_STORAGE_KEY, JSON.stringify(payments));
    } catch (err) {
      console.error("Failed to save payments to localStorage:", err);
    }
  }
  emitPaymentChange();
}

export function recordPayment(paymentData: {
  memberId: string;
  amount: number;
  paymentDate?: string;
  method: PaymentMethod;
  description: string;
  reference?: string;
  status?: PaymentStatus;
}): { success: boolean; message: string; payment?: PaymentRecord } {
  const member = getMemberById(paymentData.memberId);
  if (!member) {
    return { success: false, message: `Member with ID ${paymentData.memberId} not found.` };
  }

  const payments = getStoredPayments();
  const maxTxnNum = payments.reduce((max, p) => {
    const match = p.id.match(/\d+/);
    const num = match ? parseInt(match[0], 10) : 0;
    return num > max ? num : max;
  }, 1000);

  const nextTxnNum = maxTxnNum + 1;
  const txnId = `TXN-${nextTxnNum}`;
  const receiptNum = `RCP-2026-${String(nextTxnNum - 1000).padStart(3, "0")}`;

  const newPayment: PaymentRecord = {
    id: txnId,
    receiptNumber: receiptNum,
    memberId: member.id,
    memberName: member.name,
    amount: paymentData.amount,
    paymentDate: paymentData.paymentDate || getTodayDateString(),
    method: paymentData.method,
    description: paymentData.description,
    reference: paymentData.reference || undefined,
    status: paymentData.status || "Paid",
  };

  const nextList = [newPayment, ...payments];
  savePayments(nextList);

  logAuditAction({
    action: newPayment.status === "Paid" ? "PAYMENT_COLLECT" : "PAYMENT_PARTIAL",
    actionLabel: "Payment Collected",
    entityType: "Payment",
    entityId: newPayment.id,
    entityName: newPayment.memberName,
    performedBy: "Accounts Cashier",
    description: `Collected ₹${newPayment.amount.toLocaleString("en-IN")} via ${newPayment.method} from ${newPayment.memberName} (${newPayment.memberId}). Receipt #${newPayment.receiptNumber}.`,
    previousValue: null,
    updatedValue: {
      transactionId: newPayment.id,
      receiptNumber: newPayment.receiptNumber,
      amount: newPayment.amount,
      method: newPayment.method,
      status: newPayment.status,
    },
    severity: "info",
  });

  return {
    success: true,
    message: `Payment of ₹${paymentData.amount.toLocaleString("en-IN")} recorded successfully for ${member.name}.`,
    payment: newPayment,
  };
}

// ==========================================
// ---------------- Outstanding Dues Store --
// ==========================================

export type DueStatus = "Pending" | "Partially Paid" | "Overdue" | "Paid";

export type DuePaymentTransaction = {
  txnId: string;
  receiptNumber: string;
  amount: number;
  paymentDate: string;
  method: PaymentMethod;
  reference?: string;
  note?: string;
};

export type DueItem = {
  id: string;
  memberId: string;
  memberName: string;
  memberPlan: string;
  totalAmount: number;
  amountPaid: number;
  remainingBalance: number;
  dueDate: string;
  description: string;
  status: DueStatus;
  createdAt: string;
  payments: DuePaymentTransaction[];
};

export type AgeingCategory =
  | "All"
  | "Not Yet Due"
  | "1-7 Days Overdue"
  | "8-30 Days Overdue"
  | "31-60 Days Overdue"
  | "More Than 60 Days Overdue";

export function getDaysOverdue(dueDateStr: string): number {
  if (!dueDateStr) return 0;
  const due = new Date(dueDateStr);
  const now = new Date();
  const dueMidnight = new Date(due.getFullYear(), due.getMonth(), due.getDate()).getTime();
  const nowMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const diffTime = nowMidnight - dueMidnight;
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  return diffDays > 0 ? diffDays : 0;
}

export function getAgeingCategory(dueDateStr: string, status?: DueStatus): AgeingCategory {
  if (status === "Paid") return "Not Yet Due";
  const days = getDaysOverdue(dueDateStr);
  if (days <= 0) return "Not Yet Due";
  if (days <= 7) return "1-7 Days Overdue";
  if (days <= 30) return "8-30 Days Overdue";
  if (days <= 60) return "31-60 Days Overdue";
  return "More Than 60 Days Overdue";
}

export const INITIAL_DUES: DueItem[] = [
  {
    id: "DUE-1001",
    memberId: "GYM002",
    memberName: "Rahul Sharma",
    memberPlan: "Standard",
    totalAmount: 3999,
    amountPaid: 0,
    remainingBalance: 3999,
    dueDate: "2026-11-18",
    description: "Standard 3-Month Plan Renewal",
    status: "Pending",
    createdAt: "2026-11-01",
    payments: [],
  },
  {
    id: "DUE-1002",
    memberId: "GYM005",
    memberName: "Michael Brown",
    memberPlan: "Standard",
    totalAmount: 3999,
    amountPaid: 1500,
    remainingBalance: 2499,
    dueDate: "2026-10-31",
    description: "Standard 3-Month Membership (Installment 1 of 2)",
    status: "Partially Paid",
    createdAt: "2026-10-15",
    payments: [
      {
        txnId: "TXN-1003",
        receiptNumber: "RCP-2026-003",
        amount: 1500,
        paymentDate: "31 Oct 2026",
        method: "UPI",
        reference: "UPI/20261031/554433",
        note: "Initial installment deposit",
      },
    ],
  },
  {
    id: "DUE-1003",
    memberId: "GYM003",
    memberName: "David Miller",
    memberPlan: "Premium",
    totalAmount: 12999,
    amountPaid: 0,
    remainingBalance: 12999,
    dueDate: "2026-10-18",
    description: "Annual VIP Membership Renewal Dues",
    status: "Overdue",
    createdAt: "2026-10-01",
    payments: [],
  },
  {
    id: "DUE-1004",
    memberId: "GYM004",
    memberName: "Arjun Patel",
    memberPlan: "Basic",
    totalAmount: 2499,
    amountPaid: 1000,
    remainingBalance: 1499,
    dueDate: "2026-09-20",
    description: "Basic 1-Month Plan + Locker Access Fee",
    status: "Partially Paid",
    createdAt: "2026-09-01",
    payments: [
      {
        txnId: "TXN-1005",
        receiptNumber: "RCP-2026-005",
        amount: 1000,
        paymentDate: "20 Sep 2026",
        method: "Cash",
        reference: "CASH-REC-104",
        note: "Cash counter advance",
      },
    ],
  },
  {
    id: "DUE-1005",
    memberId: "GYM003",
    memberName: "David Miller",
    memberPlan: "Premium",
    totalAmount: 5000,
    amountPaid: 0,
    remainingBalance: 5000,
    dueDate: "2026-08-10",
    description: "Personal Trainer Package (10 Sessions) Outstanding",
    status: "Overdue",
    createdAt: "2026-07-25",
    payments: [],
  },
  {
    id: "DUE-1006",
    memberId: "GYM006",
    memberName: "Rihan Fazlani",
    memberPlan: "Premium",
    totalAmount: 12999,
    amountPaid: 12999,
    remainingBalance: 0,
    dueDate: "2026-11-01",
    description: "Annual VIP Premium Access Pass",
    status: "Paid",
    createdAt: "2026-10-25",
    payments: [
      {
        txnId: "TXN-1004",
        receiptNumber: "RCP-2026-004",
        amount: 12999,
        paymentDate: "03 Nov 2026",
        method: "Bank Transfer",
        reference: "NEFT-HDFC-991823",
        note: "Settled in full via NEFT",
      },
    ],
  },
];

const DUES_STORAGE_KEY = "gymcore_dues_data";
let cachedDues: DueItem[] | null = null;
let duesListeners: Array<() => void> = [];

function emitDuesChange() {
  for (const listener of duesListeners) {
    listener();
  }
}

export function subscribeDues(listener: () => void) {
  duesListeners = [...duesListeners, listener];
  return () => {
    duesListeners = duesListeners.filter((l) => l !== listener);
  };
}

export function getStoredDues(): DueItem[] {
  if (typeof window === "undefined") {
    return INITIAL_DUES;
  }
  if (cachedDues) {
    return cachedDues;
  }
  try {
    const raw = localStorage.getItem(DUES_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(DUES_STORAGE_KEY, JSON.stringify(INITIAL_DUES));
      cachedDues = INITIAL_DUES;
      return INITIAL_DUES;
    }
    cachedDues = JSON.parse(raw);
    return cachedDues || INITIAL_DUES;
  } catch {
    return INITIAL_DUES;
  }
}

export function saveDues(dues: DueItem[]): void {
  cachedDues = dues;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(DUES_STORAGE_KEY, JSON.stringify(dues));
    } catch (err) {
      console.error("Failed to save dues to localStorage:", err);
    }
  }
  emitDuesChange();
}

export function collectDuePayment(data: {
  dueId: string;
  amount: number;
  paymentDate?: string;
  method: PaymentMethod;
  reference?: string;
  note?: string;
}): { success: boolean; message: string; payment?: PaymentRecord; due?: DueItem } {
  const dues = getStoredDues();
  const targetDue = dues.find((d) => d.id === data.dueId);
  if (!targetDue) {
    return { success: false, message: `Dues record ${data.dueId} not found.` };
  }

  if (data.amount <= 0) {
    return { success: false, message: "Payment amount must be greater than ₹0." };
  }

  if (data.amount > targetDue.remainingBalance) {
    return {
      success: false,
      message: `Payment amount (₹${data.amount.toLocaleString("en-IN")}) cannot exceed remaining balance of ₹${targetDue.remainingBalance.toLocaleString("en-IN")}.`,
    };
  }

  // 1. Record payment in the general payments ledger (creates sequential TXN and RCP)
  const isSettlement = data.amount === targetDue.remainingBalance;
  const paymentDescription = `Payment for ${targetDue.description} (${isSettlement ? "Full Settlement" : "Partial Payment"})`;

  const paymentRes = recordPayment({
    memberId: targetDue.memberId,
    amount: data.amount,
    paymentDate: data.paymentDate || getTodayDateString(),
    method: data.method,
    description: paymentDescription,
    reference: data.reference,
    status: "Paid",
  });

  if (!paymentRes.success || !paymentRes.payment) {
    return { success: false, message: paymentRes.message || "Failed to record payment in ledger." };
  }

  // 2. Update Due Item balance and status
  const newAmountPaid = targetDue.amountPaid + data.amount;
  const newRemainingBalance = targetDue.remainingBalance - data.amount;
  const newStatus: DueStatus = newRemainingBalance === 0 ? "Paid" : "Partially Paid";

  const newTxnEntry: DuePaymentTransaction = {
    txnId: paymentRes.payment.id,
    receiptNumber: paymentRes.payment.receiptNumber,
    amount: data.amount,
    paymentDate: paymentRes.payment.paymentDate,
    method: data.method,
    reference: data.reference,
    note: data.note,
  };

  const updatedDue: DueItem = {
    ...targetDue,
    amountPaid: newAmountPaid,
    remainingBalance: newRemainingBalance,
    status: newStatus,
    payments: [...targetDue.payments, newTxnEntry],
  };

  const nextDues = dues.map((d) => (d.id === targetDue.id ? updatedDue : d));
  saveDues(nextDues);

  return {
    success: true,
    message: `Payment of ₹${data.amount.toLocaleString("en-IN")} recorded successfully for ${targetDue.memberName}. Remaining balance: ₹${newRemainingBalance.toLocaleString("en-IN")}.`,
    payment: paymentRes.payment,
    due: updatedDue,
  };
}

export function getMemberOutstandingDues(memberId: string): number {
  const dues = getStoredDues();
  return dues
    .filter(
      (d) => d.memberId.toLowerCase() === memberId.toLowerCase() && d.status !== "Paid"
    )
    .reduce((sum, d) => sum + d.remainingBalance, 0);
}

export type ExpiryWarning = {
  level: "expired" | "frozen" | "1day" | "7days" | "active";
  badgeColor: string;
  text: string;
  urgent: boolean;
};

export function getMemberWarning(member: Member): ExpiryWarning {
  if (member.status === "Expired") {
    return {
      level: "expired",
      badgeColor: "border-red-500/30 bg-red-500/10 text-red-400",
      text: "Membership Expired - Renewal Required",
      urgent: true,
    };
  }
  if (member.status === "Frozen") {
    return {
      level: "frozen",
      badgeColor: "border-sky-500/30 bg-sky-500/10 text-sky-400",
      text: "Membership Frozen - Reactivate to Access",
      urgent: false,
    };
  }

  if (member.validUntil) {
    const validDate = new Date(member.validUntil);
    if (!isNaN(validDate.getTime())) {
      const now = new Date();
      const diffTime = validDate.getTime() - now.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      if (diffDays <= 0) {
        return {
          level: "expired",
          badgeColor: "border-red-500/30 bg-red-500/10 text-red-400",
          text: "Membership Expired",
          urgent: true,
        };
      }
      if (diffDays <= 1) {
        return {
          level: "1day",
          badgeColor: "border-rose-500/40 bg-rose-500/15 text-rose-300",
          text: "URGENT: Membership Expires in 24 Hours",
          urgent: true,
        };
      }
      if (diffDays <= 7) {
        return {
          level: "7days",
          badgeColor: "border-amber-500/30 bg-amber-500/10 text-amber-300",
          text: `Membership Expiring Soon (${diffDays} days left)`,
          urgent: false,
        };
      }
    }
  }

  return {
    level: "active",
    badgeColor: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    text: "Active Membership",
    urgent: false,
  };
}

// ==========================================
// ---------------- Staff Store -------------
// ==========================================

export type StaffRole =
  | "Gym Manager"
  | "Personal Trainer"
  | "Receptionist"
  | "Fitness Instructor"
  | "Cleaning Staff";

export type StaffStatus = "Active" | "Inactive";

export type StaffMember = {
  id: string;
  name: string;
  role: StaffRole;
  phone: string;
  email: string;
  joiningDate: string;
  salary: number;
  status: StaffStatus;
  specialization?: string;
  address?: string;
};

export const INITIAL_STAFF: StaffMember[] = [
  {
    id: "STF001",
    name: "Rajesh Khanna",
    role: "Gym Manager",
    phone: "+91 98450 11223",
    email: "rajesh@gymcore.fit",
    joiningDate: "10 Jan 2024",
    salary: 65000,
    status: "Active",
    specialization: "Operations & Floor Management",
    address: "Koramangala 4th Block, Bangalore",
  },
  {
    id: "STF002",
    name: "Priya Sen",
    role: "Personal Trainer",
    phone: "+91 98450 33445",
    email: "priya@gymcore.fit",
    joiningDate: "15 Mar 2024",
    salary: 48000,
    status: "Active",
    specialization: "Strength & Hypertrophy Coach",
    address: "Indiranagar 100ft Road, Bangalore",
  },
  {
    id: "STF003",
    name: "Vikram Rathore",
    role: "Fitness Instructor",
    phone: "+91 98450 55667",
    email: "vikram@gymcore.fit",
    joiningDate: "01 Jun 2024",
    salary: 42000,
    status: "Active",
    specialization: "CrossFit & High Intensity Training",
    address: "HSR Layout Sector 2, Bangalore",
  },
  {
    id: "STF004",
    name: "Neha Deshmukh",
    role: "Receptionist",
    phone: "+91 98450 77889",
    email: "neha@gymcore.fit",
    joiningDate: "20 Aug 2024",
    salary: 30000,
    status: "Active",
    specialization: "Member Relations & Front Desk",
    address: "BTM Layout 2nd Stage, Bangalore",
  },
  {
    id: "STF005",
    name: "Sunita Gowda",
    role: "Cleaning Staff",
    phone: "+91 98450 99001",
    email: "sunita@gymcore.fit",
    joiningDate: "01 Feb 2024",
    salary: 20000,
    status: "Active",
    specialization: "Facility Hygiene & Maintenance",
    address: "Jayanagar 9th Block, Bangalore",
  },
  {
    id: "STF006",
    name: "Amit Roy",
    role: "Personal Trainer",
    phone: "+91 98450 22334",
    email: "amit@gymcore.fit",
    joiningDate: "12 Nov 2024",
    salary: 45000,
    status: "Inactive",
    specialization: "Rehabilitation & Mobility Specialist",
    address: "Whitefield Inner Circle, Bangalore",
  },
];

const STAFF_STORAGE_KEY = "gymcore_staff_data";
let cachedStaff: StaffMember[] | null = null;
let staffListeners: Array<() => void> = [];

function emitStaffChange() {
  for (const listener of staffListeners) {
    listener();
  }
}

export function subscribeStaff(listener: () => void) {
  staffListeners = [...staffListeners, listener];
  return () => {
    staffListeners = staffListeners.filter((l) => l !== listener);
  };
}

export function getStoredStaff(): StaffMember[] {
  if (typeof window === "undefined") {
    return sortStaffByNumericId(INITIAL_STAFF);
  }
  if (cachedStaff) {
    return cachedStaff;
  }
  try {
    const raw = localStorage.getItem(STAFF_STORAGE_KEY);
    if (!raw) {
      const sorted = sortStaffByNumericId(INITIAL_STAFF);
      localStorage.setItem(STAFF_STORAGE_KEY, JSON.stringify(sorted));
      sorted.forEach((s) => updateStaffCounterHighWaterMark(s.id));
      cachedStaff = sorted;
      return sorted;
    }
    const parsed: StaffMember[] = JSON.parse(raw);
    const existingIds = new Set(parsed.map((s) => s.id.toLowerCase()));
    let merged = false;
    for (const initStaff of INITIAL_STAFF) {
      if (!existingIds.has(initStaff.id.toLowerCase())) {
        parsed.push(initStaff);
        merged = true;
      }
    }

    const sorted = sortStaffByNumericId(parsed);
    sorted.forEach((s) => updateStaffCounterHighWaterMark(s.id));

    if (merged || JSON.stringify(sorted) !== raw) {
      localStorage.setItem(STAFF_STORAGE_KEY, JSON.stringify(sorted));
    }

    cachedStaff = sorted;
    return sorted;
  } catch {
    return sortStaffByNumericId(INITIAL_STAFF);
  }
}

export function saveStaff(staff: StaffMember[]): void {
  const sorted = sortStaffByNumericId(staff);
  cachedStaff = sorted;
  if (typeof window !== "undefined") {
    try {
      sorted.forEach((s) => updateStaffCounterHighWaterMark(s.id));
      localStorage.setItem(STAFF_STORAGE_KEY, JSON.stringify(sorted));
    } catch (err) {
      console.error("Failed to save staff to localStorage:", err);
    }
  }
  emitStaffChange();
}

export function addStaff(newStaff: Omit<StaffMember, "id"> & { id?: string }): StaffMember {
  const staff = getStoredStaff();
  const id = newStaff.id && newStaff.id.trim() ? newStaff.id.trim() : getNextStaffId(staff);
  updateStaffCounterHighWaterMark(id);

  const member: StaffMember = {
    ...newStaff,
    id,
    phone: formatIndianMobile(newStaff.phone),
  };

  const nextList = sortStaffByNumericId([
    member,
    ...staff.filter((s) => s.id.toLowerCase() !== id.toLowerCase()),
  ]);
  saveStaff(nextList);
  return member;
}

export function updateStaff(updated: StaffMember): StaffMember[] {
  const staff = getStoredStaff();
  const formatted: StaffMember = {
    ...updated,
    phone: formatIndianMobile(updated.phone),
  };
  const nextList = sortStaffByNumericId(staff.map((s) => (s.id === updated.id ? formatted : s)));
  saveStaff(nextList);
  return nextList;
}

export function deleteStaff(id: string): StaffMember[] {
  const staff = getStoredStaff();
  // DO NOT decrease the staff ID counter so deleted IDs are NEVER reused
  const nextList = staff.filter((s) => s.id.toLowerCase() !== id.toLowerCase());
  saveStaff(nextList);
  return nextList;
}

export function toggleStaffStatus(id: string): StaffMember | undefined {
  const staff = getStoredStaff();
  const target = staff.find((s) => s.id.toLowerCase() === id.toLowerCase());
  if (!target) return undefined;

  const newStatus: StaffStatus = target.status === "Active" ? "Inactive" : "Active";
  const updated: StaffMember = { ...target, status: newStatus };
  updateStaff(updated);
  return updated;
}

// ==========================================
// ---------------- Settings Store ----------
// ==========================================

export type GymSettings = {
  gymName: string;
  tagline: string;
  phone: string;
  email: string;
  address: string;
  city: string;
  postalCode: string;
  website: string;
  weekdayHours: string;
  weekendHours: string;
  peakHours: string;
  currency: string;
  currencySymbol: string;
  taxGstPercent: number;
  invoicePrefix: string;
  memberIdPrefix: string;
  expiryAlert7Days: boolean;
  expiryAlert1Day: boolean;
  autoEmailReceipt: boolean;
  dailySummaryReport: boolean;
  adminName: string;
  adminEmail: string;
  adminRole: string;
};

export const INITIAL_SETTINGS: GymSettings = {
  gymName: "GYMCORE Fitness Club",
  tagline: "Elite Strength & Conditioning Facility",
  phone: "+91 80 4123 4567",
  email: "contact@gymcore.fit",
  address: "Plot 88, 100 Feet Road, Indiranagar",
  city: "Bangalore",
  postalCode: "560038",
  website: "https://gymcore.fit",
  weekdayHours: "06:00 AM - 10:00 PM",
  weekendHours: "07:00 AM - 08:00 PM",
  peakHours: "06:30 AM - 09:30 AM & 05:30 PM - 08:30 PM",
  currency: "INR (₹)",
  currencySymbol: "₹",
  taxGstPercent: 18,
  invoicePrefix: "GYM-INV",
  memberIdPrefix: "GYM",
  expiryAlert7Days: true,
  expiryAlert1Day: true,
  autoEmailReceipt: true,
  dailySummaryReport: true,
  adminName: "Gymcore Admin",
  adminEmail: "admin@gymcore.fit",
  adminRole: "Super Admin",
};

const SETTINGS_STORAGE_KEY = "gymcore_settings_data";
let cachedSettings: GymSettings | null = null;
let settingsListeners: Array<() => void> = [];

function emitSettingsChange() {
  for (const listener of settingsListeners) {
    listener();
  }
}

export function subscribeSettings(listener: () => void) {
  settingsListeners = [...settingsListeners, listener];
  return () => {
    settingsListeners = settingsListeners.filter((l) => l !== listener);
  };
}

export function getStoredSettings(): GymSettings {
  if (typeof window === "undefined") {
    return INITIAL_SETTINGS;
  }
  if (cachedSettings) {
    return cachedSettings;
  }
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(INITIAL_SETTINGS));
      cachedSettings = INITIAL_SETTINGS;
      return INITIAL_SETTINGS;
    }
    cachedSettings = JSON.parse(raw);
    return cachedSettings || INITIAL_SETTINGS;
  } catch {
    return INITIAL_SETTINGS;
  }
}

export function saveSettings(settings: GymSettings): void {
  cachedSettings = settings;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch (err) {
      console.error("Failed to save settings to localStorage:", err);
    }
  }
  emitSettingsChange();

  logAuditAction({
    action: "SETTINGS_UPDATE",
    actionLabel: "Gym Settings Modified",
    entityType: "Settings",
    entityId: "SYSTEM",
    entityName: settings.gymName || "GYMCORE System",
    performedBy: "Administrator",
    description: `Updated configuration parameters for ${settings.gymName || "GYMCORE"} (Email: ${settings.email}).`,
    previousValue: null,
    updatedValue: {
      gymName: settings.gymName,
      email: settings.email,
      phone: settings.phone,
      currency: settings.currency,
    },
    severity: "info",
  });
}

export function resetSettingsToDefault(): GymSettings {
  saveSettings(INITIAL_SETTINGS);
  return INITIAL_SETTINGS;
}

// Re-export audit trail
export * from "./audit-trail.ts";

