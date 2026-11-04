"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Edit,
  Snowflake,
  RefreshCw,
  UserRound,
  CheckCircle2,
  Calendar,
  Phone,
  Mail,
  MapPin,
  Clock,
  ShieldAlert,
  Flame,
  X,
  Sparkles,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
import {
  type Member,
  updateMember,
  renewMember,
  toggleFreezeMember,
} from "@/lib/mock-data";
import { useMembersStore } from "@/lib/use-members-store";
import { usePlansStore } from "@/lib/use-plans-store";
import { useMounted } from "@/lib/use-mounted";
import {
  isValidIndianMobile,
  formatIndianMobile,
  sanitizeIndianMobile,
} from "@/lib/phone-utils";

type Props = {
  memberId: string;
};

export function MemberProfileView({ memberId }: Props) {
  const mounted = useMounted();
  const members = useMembersStore();
  const plans = usePlansStore();

  const member = members.find(
    (m) => m.id.toLowerCase() === memberId.toLowerCase()
  );

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isRenewOpen, setIsRenewOpen] = useState(false);
  const [renewMonths, setRenewMonths] = useState(12);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Edit form state & field errors
  const [editForm, setEditForm] = useState({
    name: "",
    email: "",
    phone: "",
    plan: "Standard",
    emergencyContact: "",
    address: "",
  });

  const [editErrors, setEditErrors] = useState<{
    name?: string;
    email?: string;
    phone?: string;
  }>({});

  const showFeedback = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4500);
  };

  const handleOpenEdit = () => {
    if (!member) return;
    setEditForm({
      name: member.name,
      email: member.email,
      phone: member.phone,
      plan: member.plan,
      emergencyContact: member.emergencyContact || "",
      address: member.address || "",
    });
    setEditErrors({});
    setIsEditOpen(true);
  };

  const handlePhoneChange = (val: string) => {
    const digits = sanitizeIndianMobile(val).slice(0, 10);
    setEditForm((prev) => ({
      ...prev,
      phone: digits.length === 10 ? formatIndianMobile(digits) : val,
    }));
    if (editErrors.phone) {
      setEditErrors((prev) => ({ ...prev, phone: undefined }));
    }
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!member) return;

    const errors: typeof editErrors = {};
    if (!editForm.name.trim() || editForm.name.trim().length < 2) {
      errors.name = "Full name must be at least 2 characters.";
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const normalizedEmail = editForm.email.trim().toLowerCase();
    if (!editForm.email.trim() || !emailRegex.test(editForm.email.trim())) {
      errors.email = "Please enter a valid email address.";
    } else {
      const duplicateEmail = members.find(
        (m) =>
          m.id.toLowerCase() !== member.id.toLowerCase() &&
          m.email.toLowerCase() === normalizedEmail
      );
      if (duplicateEmail) {
        errors.email = `Email is already registered to ${duplicateEmail.name} (${duplicateEmail.id}).`;
      }
    }

    if (!isValidIndianMobile(editForm.phone)) {
      errors.phone = "Please enter a valid 10-digit Indian mobile number.";
    } else {
      const normalizedPhone = sanitizeIndianMobile(editForm.phone);
      const duplicatePhone = members.find(
        (m) =>
          m.id.toLowerCase() !== member.id.toLowerCase() &&
          sanitizeIndianMobile(m.phone) === normalizedPhone
      );
      if (duplicatePhone) {
        errors.phone = `Phone number is already registered to ${duplicatePhone.name} (${duplicatePhone.id}).`;
      }
    }

    if (Object.keys(errors).length > 0) {
      setEditErrors(errors);
      return;
    }

    const updated: Member = {
      ...member,
      name: editForm.name.trim(),
      email: editForm.email.trim().toLowerCase(),
      phone: formatIndianMobile(editForm.phone),
      plan: editForm.plan,
      emergencyContact: editForm.emergencyContact.trim() || undefined,
      address: editForm.address.trim() || undefined,
    };

    updateMember(updated);
    setIsEditOpen(false);
    showFeedback(`Profile for ${updated.name} updated successfully!`);
  };

  const handleToggleFreeze = () => {
    if (!member) return;
    const updated = toggleFreezeMember(member.id);
    if (updated) {
      showFeedback(
        updated.status === "Frozen"
          ? `Membership for ${member.name} has been FROZEN.`
          : `Membership for ${member.name} has been REACTIVATED!`
      );
    }
  };

  const handleConfirmRenew = (e: React.FormEvent) => {
    e.preventDefault();
    if (!member) return;
    const updated = renewMember(member.id, renewMonths);
    if (updated) {
      setIsRenewOpen(false);
      showFeedback(
        `Membership for ${member.name} renewed until ${updated.validUntil}!`
      );
    }
  };

  // While mounting on client, show a subtle loading skeleton
  if (!mounted) {
    return (
      <div className="flex h-72 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-[#C9A04F] border-t-transparent" />
          <p className="text-xs text-muted-foreground">Loading member profile...</p>
        </div>
      </div>
    );
  }

  // Not Found state for genuinely unknown IDs
  if (!member) {
    return (
      <div className="rounded-2xl border border-border bg-card p-10 sm:p-14 text-center max-w-xl mx-auto shadow-sm">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500">
          <AlertCircle size={32} />
        </div>
        <h2 className="mt-4 text-2xl font-bold tracking-tight">Member Not Found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          No gym member found with ID <span className="font-mono font-semibold text-foreground">&quot;{memberId}&quot;</span>.
        </p>

        <div className="mt-4 rounded-xl border border-border bg-muted/30 p-4 text-left text-xs text-muted-foreground">
          <p className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
            <ShieldAlert size={14} className="text-[#C9A04F]" />
            Why might this happen?
          </p>
          <ul className="list-disc pl-4 space-y-1">
            <li>The member ID was mistyped or does not exist.</li>
            <li>If created in a different browser, data is currently saved in browser storage until Riva connects the FastAPI backend.</li>
          </ul>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/members"
            className="inline-flex items-center gap-2 rounded-lg bg-[#C9A04F] px-4 py-2.5 text-sm font-semibold text-black hover:bg-[#b68d3e] transition"
          >
            <ArrowLeft size={16} />
            <span>Return to Members List</span>
          </Link>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: Member["status"]) => {
    switch (status) {
      case "Active":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "Expired":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      case "Frozen":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      default:
        return "bg-muted text-muted-foreground border-border";
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`flex items-center gap-2.5 rounded-xl border p-4 text-sm font-medium animate-in fade-in slide-in-from-top-2 ${
            notification.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
              : "border-red-500/30 bg-red-500/15 text-red-400"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 size={18} className="shrink-0" />
          ) : (
            <AlertCircle size={18} className="shrink-0" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Header & Quick Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            href="/members"
            className="mb-3 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition"
          >
            <ArrowLeft size={16} />
            <span>Back to Members</span>
          </Link>

          <h1 className="text-2xl font-bold">Member Profile</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            View, edit, freeze, or renew member details and subscription status.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleOpenEdit}
            className="flex items-center gap-2 rounded-xl border border-border bg-card px-3.5 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium text-foreground transition hover:bg-muted touch-manipulation min-h-[40px]"
          >
            <Edit size={15} />
            <span>Edit Profile</span>
          </button>

          <button
            onClick={handleToggleFreeze}
            className={`flex items-center gap-2 rounded-xl border px-3.5 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-medium transition touch-manipulation min-h-[40px] ${
              member.status === "Frozen"
                ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20"
                : "border-border bg-card text-foreground hover:bg-muted"
            }`}
          >
            <Snowflake size={15} />
            <span>{member.status === "Frozen" ? "Unfreeze Plan" : "Freeze Plan"}</span>
          </button>

          <button
            onClick={() => setIsRenewOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-[#C9A04F] px-3.5 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm font-bold text-black transition hover:bg-[#b68d3e] touch-manipulation min-h-[40px]"
          >
            <RefreshCw size={15} />
            <span>Renew Membership</span>
          </button>
        </div>
      </div>

      {/* Profile Overview Card */}
      <div className="rounded-xl border border-border bg-card p-6 shadow-xs">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex h-18 w-18 items-center justify-center rounded-2xl bg-[#C9A04F]/15 text-[#C9A04F]">
            <UserRound size={34} />
          </div>

          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-foreground">{member.name}</h2>
              <span
                className={`inline-flex rounded-full border px-3 py-0.5 text-xs font-semibold ${getStatusBadge(
                  member.status
                )}`}
              >
                {member.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Member ID: <span className="font-mono font-semibold text-foreground">{member.id}</span>
              {" • "}
              Plan: <span className="text-[#C9A04F] font-semibold">{member.plan} Tier</span>
            </p>
          </div>

          <div className="ml-auto flex items-center gap-6 border-l border-border pl-6 hidden sm:flex">
            <div className="text-center">
              <p className="text-xs text-muted-foreground">Total Visits</p>
              <p className="mt-1 text-2xl font-bold text-foreground">
                {member.totalVisits ?? 0}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground">Valid Until</p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                {member.validUntil ?? "Active"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#C9A04F]/10 text-[#C9A04F]">
              <Sparkles size={18} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Membership Tier</p>
              <p className="font-semibold text-foreground">{member.plan} Plan</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10 text-green-500">
              <Calendar size={18} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Member Since</p>
              <p className="font-semibold text-foreground">{member.joinDate}</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500">
              <Clock size={18} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Last Check-in</p>
              <p className="font-semibold text-foreground">{member.lastVisit ?? "Recent"}</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500">
              <Flame size={18} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Workout Streak</p>
              <p className="font-semibold text-foreground">Active Trainer</p>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Details Sections */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Personal Details */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5 flex items-center gap-2 text-base font-semibold">
            <UserRound size={18} className="text-[#C9A04F]" />
            <span>Personal Information</span>
          </h2>

          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <Mail size={16} className="mt-1 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Email Address</p>
                <p className="font-medium text-foreground">{member.email}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Phone size={16} className="mt-1 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Phone Number (India)</p>
                <p className="font-mono font-medium text-foreground">
                  {formatIndianMobile(member.phone)}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <ShieldAlert size={16} className="mt-1 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Emergency Contact</p>
                <p className="font-medium text-foreground">
                  {member.emergencyContact || "None specified"}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin size={16} className="mt-1 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Residential Address</p>
                <p className="font-medium text-foreground">
                  {member.address || "Bangalore, Karnataka, India"}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Membership Details */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5 flex items-center gap-2 text-base font-semibold">
            <Calendar size={18} className="text-[#C9A04F]" />
            <span>Membership Plan Details</span>
          </h2>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground">Assigned Package</p>
              <p className="mt-1 font-semibold text-foreground flex items-center gap-1.5">
                <Sparkles size={14} className="text-[#C9A04F]" />
                {member.plan} Membership
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">Membership Status</p>
              <div className="mt-1">
                <span
                  className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getStatusBadge(
                    member.status
                  )}`}
                >
                  {member.status}
                </span>
              </div>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">Enrollment Date</p>
              <p className="mt-1 font-medium text-foreground">{member.joinDate}</p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">Valid Until / Renewal Due</p>
              <p className="mt-1 font-mono font-medium text-foreground">
                {member.validUntil || "Active"}
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* Edit Profile Modal */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
              <div>
                <h2 className="text-lg font-bold">Edit Member Profile</h2>
                <p className="text-xs text-muted-foreground">Member ID: {member.id}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsEditOpen(false)}
                className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
                aria-label="Close edit modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium">Full Name *</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => {
                    setEditForm({ ...editForm, name: e.target.value });
                    if (editErrors.name) setEditErrors({ ...editErrors, name: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                    editErrors.name ? "border-red-500" : "border-border"
                  }`}
                />
                {editErrors.name && (
                  <p className="mt-1 text-xs text-red-500">{editErrors.name}</p>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium">Email Address *</label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={(e) => {
                    setEditForm({ ...editForm, email: e.target.value });
                    if (editErrors.email) setEditErrors({ ...editErrors, email: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                    editErrors.email ? "border-red-500" : "border-border"
                  }`}
                />
                {editErrors.email && (
                  <p className="mt-1 text-xs text-red-500">{editErrors.email}</p>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium">Phone Number (10 digits) *</label>
                <input
                  type="tel"
                  placeholder="98765 43210"
                  value={editForm.phone}
                  onChange={(e) => handlePhoneChange(e.target.value)}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                    editErrors.phone ? "border-red-500" : "border-border"
                  }`}
                />
                {editErrors.phone && (
                  <p className="mt-1 text-xs text-red-500">{editErrors.phone}</p>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium">Membership Plan</label>
                <select
                  value={editForm.plan}
                  onChange={(e) => setEditForm({ ...editForm, plan: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.name}>
                      {p.name} Plan (₹{p.price.toLocaleString("en-IN")})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium">Emergency Contact</label>
                <input
                  type="text"
                  placeholder="+91 98765 00000 (Spouse / Family)"
                  value={editForm.emergencyContact}
                  onChange={(e) =>
                    setEditForm({ ...editForm, emergencyContact: e.target.value })
                  }
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium">Residential Address</label>
                <input
                  type="text"
                  placeholder="e.g. Indiranagar, Bangalore"
                  value={editForm.address}
                  onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-[#C9A04F] px-4 py-2 text-sm font-semibold text-black hover:bg-[#b68d3e]"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Renew Membership Modal */}
      {isRenewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <h3 className="text-lg font-bold">Renew Membership</h3>
                <p className="text-xs text-muted-foreground">Member: {member.name}</p>
              </div>
              <button
                type="button"
                onClick={() => setIsRenewOpen(false)}
                className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleConfirmRenew} className="mt-4 space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium">Select Renewal Duration</label>
                <select
                  value={renewMonths}
                  onChange={(e) => setRenewMonths(Number(e.target.value))}
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                >
                  <option value={1}>1 Month Extension</option>
                  <option value={3}>3 Months Extension</option>
                  <option value={6}>6 Months Extension</option>
                  <option value={12}>12 Months (1 Full Year) Extension</option>
                </select>
              </div>

              <div className="rounded-xl border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
                <p className="font-semibold text-foreground flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-[#C9A04F]" />
                  What happens upon renewal:
                </p>
                <p className="mt-1">
                  The member status is marked <strong>Active</strong> and the expiration date is updated automatically in local storage.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsRenewOpen(false)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-[#C9A04F] px-4 py-2 text-sm font-semibold text-black hover:bg-[#b68d3e]"
                >
                  Confirm Renewal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
