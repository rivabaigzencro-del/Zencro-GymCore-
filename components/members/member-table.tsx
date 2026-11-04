"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Plus,
  X,
  UserRound,
  ChevronRight,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Phone,
  Mail,
  Calendar,
  Sparkles,
  Upload,
  Download,
} from "lucide-react";
import {
  type Member,
  addMember as saveNewMember,
  deleteMember,
  getNextMemberId,
  sortMembersByNumericId,
} from "@/lib/mock-data";
import { useMembersStore } from "@/lib/use-members-store";
import { usePlansStore } from "@/lib/use-plans-store";
import {
  isValidIndianMobile,
  formatIndianMobile,
  sanitizeIndianMobile,
} from "@/lib/phone-utils";
import { ImportMembersDialog } from "./import-members-dialog";

export function MemberTable() {
  const router = useRouter();
  const members = useMembersStore();
  const plans = usePlansStore();

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [isAddMemberOpen, setIsAddMemberOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const exportMembersCsv = () => {
    const headers = [
      "Member ID",
      "Full Name",
      "Email",
      "Phone",
      "Plan",
      "Join Date",
      "Valid Until",
      "Status",
      "Total Visits",
      "Emergency Contact",
      "Address",
    ];

    const rows = members.map((m) => [
      `"${m.id}"`,
      `"${m.name.replace(/"/g, '""')}"`,
      `"${m.email}"`,
      `"${m.phone}"`,
      `"${m.plan}"`,
      `"${m.joinDate}"`,
      `"${m.validUntil || ""}"`,
      `"${m.status}"`,
      `"${m.totalVisits || 0}"`,
      `"${(m.emergencyContact || "").replace(/"/g, '""')}"`,
      `"${(m.address || "").replace(/"/g, '""')}"`,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `gymcore_members_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setNotification({ type: "success", message: "Exported members list to CSV successfully!" });
  };

  // Delete confirmation modal state
  const [memberToDelete, setMemberToDelete] = useState<Member | null>(null);

  // Add Member Form state & field-level errors
  const [newMember, setNewMember] = useState({
    name: "",
    email: "",
    phone: "",
    plan: "Standard",
    joinDate: "",
    emergencyContact: "",
    address: "",
  });

  const [formErrors, setFormErrors] = useState<{
    name?: string;
    email?: string;
    phone?: string;
    plan?: string;
    joinDate?: string;
  }>({});

  const showNotification = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4000);
  };

  const handlePhoneChange = (val: string) => {
    // Strip non-digits and limit to 10 digits
    const digits = sanitizeIndianMobile(val).slice(0, 10);
    setNewMember((prev) => ({
      ...prev,
      phone: digits.length === 10 ? formatIndianMobile(digits) : val,
    }));
    if (formErrors.phone) {
      setFormErrors((prev) => ({ ...prev, phone: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const errors: typeof formErrors = {};

    if (!newMember.name.trim() || newMember.name.trim().length < 2) {
      errors.name = "Full name must be at least 2 characters.";
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const normalizedEmail = newMember.email.trim().toLowerCase();
    if (!newMember.email.trim() || !emailRegex.test(newMember.email.trim())) {
      errors.email = "Please enter a valid email address (e.g. name@gym.com).";
    } else {
      const existingEmail = members.find((m) => m.email.toLowerCase() === normalizedEmail);
      if (existingEmail) {
        errors.email = `Email is already registered to ${existingEmail.name} (${existingEmail.id}).`;
      }
    }

    if (!isValidIndianMobile(newMember.phone)) {
      errors.phone = "Please enter a valid 10-digit Indian mobile number (starts with 6, 7, 8, or 9).";
    } else {
      const normalizedPhone = sanitizeIndianMobile(newMember.phone);
      const existingPhone = members.find((m) => sanitizeIndianMobile(m.phone) === normalizedPhone);
      if (existingPhone) {
        errors.phone = `Phone number is already registered to ${existingPhone.name} (${existingPhone.id}).`;
      }
    }

    if (!newMember.plan) {
      errors.plan = "Please select a membership plan.";
    }

    if (!newMember.joinDate) {
      errors.joinDate = "Please choose a valid joining date.";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleAddMember = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Centrally generate the next sequential Member ID (highest numeric suffix + 1)
    const newId = getNextMemberId(members);

    // Calculate initial validity (default 12 months from join date)
    const joinDateObj = new Date(`${newMember.joinDate}T00:00:00`);
    const validUntilObj = new Date(joinDateObj);
    validUntilObj.setFullYear(validUntilObj.getFullYear() + 1);

    const memberToAdd: Member = {
      id: newId,
      name: newMember.name.trim(),
      email: newMember.email.trim().toLowerCase(),
      phone: formatIndianMobile(newMember.phone),
      plan: newMember.plan,
      joinDate: joinDateObj.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
      status: "Active",
      validUntil: validUntilObj.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
      emergencyContact: newMember.emergencyContact.trim() || undefined,
      address: newMember.address.trim() || undefined,
      totalVisits: 0,
      lastVisit: "Just Joined",
    };

    saveNewMember(memberToAdd);

    setNewMember({
      name: "",
      email: "",
      phone: "",
      plan: "Standard",
      joinDate: new Date().toISOString().split("T")[0],
      emergencyContact: "",
      address: "",
    });
    setFormErrors({});
    setIsAddMemberOpen(false);

    showNotification(
      `Member ${memberToAdd.name} (${memberToAdd.id}) was successfully added!`
    );
  };

  const confirmDeleteMember = () => {
    if (!memberToDelete) return;
    deleteMember(memberToDelete.id);
    showNotification(`Member ${memberToDelete.name} (${memberToDelete.id}) was removed.`);
    setMemberToDelete(null);
  };

  const filteredMembers = sortMembersByNumericId(
    members.filter((member) => {
      const searchTarget = `${member.id} ${member.name} ${member.email} ${member.phone} ${member.plan}`.toLowerCase();
      const matchesSearch = searchTarget.includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === "All" || member.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
  );

  const getStatusStyle = (status: Member["status"]) => {
    switch (status) {
      case "Active":
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      case "Expired":
        return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      case "Frozen":
        return "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20";
      default:
        return "bg-muted text-muted-foreground border border-border";
    }
  };

  const openMemberProfile = (memberId: string) => {
    router.push(`/members/${memberId}`);
  };

  return (
    <div className="space-y-4">
      {/* Toast Feedback */}
      {notification && (
        <div
          className={`flex items-center gap-2 rounded-xl p-4 text-sm font-medium animate-in fade-in slide-in-from-top-2 border ${
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

      {/* Search, Filter and Add Member Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by membership status"
          className="rounded-lg border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
        >
          <option value="All">All Statuses ({members.length})</option>
          <option value="Active">
            Active ({members.filter((m) => m.status === "Active").length})
          </option>
          <option value="Expired">
            Expired ({members.filter((m) => m.status === "Expired").length})
          </option>
          <option value="Frozen">
            Frozen ({members.filter((m) => m.status === "Frozen").length})
          </option>
        </select>

        {/* Live Search */}
        <div className="relative max-w-sm flex-1">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />

          <input
            type="text"
            placeholder="Search by name, ID, phone, email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-border bg-background py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-[#C9A04F]"
          />
        </div>

        {/* Action Buttons: Import, Export, Add Member */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={exportMembersCsv}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-border bg-background px-3 py-2.5 text-xs font-semibold text-foreground transition hover:border-[#C9A04F] hover:text-[#C9A04F]"
            title="Export Members to CSV"
          >
            <Download size={14} className="text-[#C9A04F]" />
            <span className="hidden sm:inline">Export CSV</span>
          </button>

          <button
            type="button"
            onClick={() => setIsImportOpen(true)}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-border bg-background px-3 py-2.5 text-xs font-semibold text-foreground transition hover:border-[#C9A04F] hover:text-[#C9A04F]"
            title="Import Members from CSV"
          >
            <Upload size={14} className="text-[#C9A04F]" />
            <span>Import CSV</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setNewMember((prev) => ({
                ...prev,
                joinDate: prev.joinDate || new Date().toISOString().split("T")[0],
              }));
              setFormErrors({});
              setIsAddMemberOpen(true);
            }}
            className="flex items-center justify-center gap-2 rounded-lg bg-[#C9A04F] px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-[#b68d3e]"
          >
            <Plus size={18} />
            <span>Add Member</span>
          </button>
        </div>
      </div>

      {/* Member Table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider font-semibold">
            <tr>
              <th className="p-4">Member ID</th>
              <th className="p-4">Member</th>
              <th className="p-4">Phone</th>
              <th className="p-4">Plan</th>
              <th className="p-4">Join Date</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {filteredMembers.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  className="p-12 text-center text-muted-foreground"
                >
                  <UserRound size={32} className="mx-auto mb-2 opacity-40" />
                  <p className="font-medium text-foreground">No members found</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Try adjusting your search terms or status filter.
                  </p>
                </td>
              </tr>
            ) : (
              filteredMembers.map((member) => (
                <tr
                  key={member.id}
                  onClick={() => openMemberProfile(member.id)}
                  tabIndex={0}
                  role="link"
                  aria-label={`View profile of ${member.name}`}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      openMemberProfile(member.id);
                    }
                  }}
                  className="cursor-pointer transition hover:bg-muted/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#C9A04F]"
                >
                  <td className="p-4 font-mono font-semibold text-[#C9A04F]">
                    {member.id}
                  </td>

                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#C9A04F]/15 text-xs font-bold text-[#C9A04F]">
                        {member.name.charAt(0)}
                      </div>
                      <div>
                        <p className="font-medium text-foreground">{member.name}</p>
                        <p className="text-xs text-muted-foreground">{member.email}</p>
                      </div>
                    </div>
                  </td>

                  <td className="p-4 font-mono text-xs text-muted-foreground">
                    {formatIndianMobile(member.phone)}
                  </td>

                  <td className="p-4">
                    <span className="inline-flex items-center gap-1 font-medium text-foreground">
                      <Sparkles size={13} className="text-[#C9A04F]" />
                      {member.plan}
                    </span>
                  </td>

                  <td className="p-4 text-xs text-muted-foreground">
                    {member.joinDate}
                  </td>

                  <td className="p-4">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusStyle(
                        member.status
                      )}`}
                    >
                      {member.status}
                    </span>
                  </td>

                  <td className="p-4 text-right">
                    <div className="inline-flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => openMemberProfile(member.id)}
                        aria-label={`View ${member.name}'s profile`}
                        className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium text-[#C9A04F] transition hover:bg-[#C9A04F]/10"
                      >
                        <span>View</span>
                        <ChevronRight size={14} />
                      </button>

                      <button
                        type="button"
                        onClick={() => setMemberToDelete(member)}
                        aria-label={`Delete ${member.name}`}
                        className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-red-500/10 hover:text-red-500"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <p>
          Showing <span className="font-semibold text-foreground">{filteredMembers.length}</span> of{" "}
          <span className="font-semibold text-foreground">{members.length}</span> total members
        </p>
        <p className="hidden sm:block">Click any row to open the complete member profile</p>
      </div>

      {/* Add Member Dialog */}
      {isAddMemberOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
              <div>
                <h2 className="text-xl font-bold">Add New Member</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Register a gym member and assign a membership tier
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsAddMemberOpen(false)}
                aria-label="Close dialog"
                className="rounded-lg p-2 text-muted-foreground transition hover:bg-muted"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddMember} className="space-y-4">
              {/* Full Name */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium">
                  <UserRound size={14} className="text-[#C9A04F]" />
                  <span>Full Name *</span>
                </label>
                <input
                  type="text"
                  placeholder="Enter member's full name"
                  value={newMember.name}
                  onChange={(e) => {
                    setNewMember({ ...newMember, name: e.target.value });
                    if (formErrors.name) setFormErrors({ ...formErrors, name: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none transition focus:border-[#C9A04F] ${
                    formErrors.name ? "border-red-500" : "border-border"
                  }`}
                />
                {formErrors.name && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.name}</p>
                )}
              </div>

              {/* Email Address */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium">
                  <Mail size={14} className="text-[#C9A04F]" />
                  <span>Email Address *</span>
                </label>
                <input
                  type="email"
                  placeholder="Enter email address"
                  value={newMember.email}
                  onChange={(e) => {
                    setNewMember({ ...newMember, email: e.target.value });
                    if (formErrors.email) setFormErrors({ ...formErrors, email: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none transition focus:border-[#C9A04F] ${
                    formErrors.email ? "border-red-500" : "border-border"
                  }`}
                />
                {formErrors.email && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.email}</p>
                )}
              </div>

              {/* Indian Phone Number */}
              <div>
                <label className="mb-1.5 flex items-center justify-between text-xs font-medium">
                  <span className="flex items-center gap-1.5">
                    <Phone size={14} className="text-[#C9A04F]" />
                    <span>Indian Mobile Number *</span>
                  </span>
                  <span className="text-[11px] text-muted-foreground">10 digits (6-9 prefix)</span>
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    placeholder="Enter 10-digit mobile number"
                    value={newMember.phone}
                    onChange={(e) => handlePhoneChange(e.target.value)}
                    className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none transition focus:border-[#C9A04F] ${
                      formErrors.phone ? "border-red-500" : "border-border"
                    }`}
                  />
                </div>
                {formErrors.phone && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.phone}</p>
                )}
              </div>

              {/* Membership Plan */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium">
                  <Sparkles size={14} className="text-[#C9A04F]" />
                  <span>Membership Plan *</span>
                </label>
                <select
                  value={newMember.plan}
                  onChange={(e) => {
                    setNewMember({ ...newMember, plan: e.target.value });
                    if (formErrors.plan) setFormErrors({ ...formErrors, plan: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                    formErrors.plan ? "border-red-500" : "border-border"
                  }`}
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.name}>
                      {p.name} Plan — ₹{p.price.toLocaleString("en-IN")} ({p.durationLabel})
                    </option>
                  ))}
                </select>
                {formErrors.plan && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.plan}</p>
                )}
              </div>

              {/* Joining Date */}
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium">
                  <Calendar size={14} className="text-[#C9A04F]" />
                  <span>Joining Date *</span>
                </label>
                <input
                  type="date"
                  value={newMember.joinDate}
                  onChange={(e) => {
                    setNewMember({ ...newMember, joinDate: e.target.value });
                    if (formErrors.joinDate) setFormErrors({ ...formErrors, joinDate: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                    formErrors.joinDate ? "border-red-500" : "border-border"
                  }`}
                />
                {formErrors.joinDate && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.joinDate}</p>
                )}
              </div>

              {/* Emergency Contact */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                  Emergency Contact (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Enter emergency contact details"
                  value={newMember.emergencyContact}
                  onChange={(e) =>
                    setNewMember({ ...newMember, emergencyContact: e.target.value })
                  }
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsAddMemberOpen(false)}
                  className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium transition hover:bg-muted"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="rounded-lg bg-[#C9A04F] px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-[#b68d3e]"
                >
                  Save Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {memberToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-500 shrink-0">
                <Trash2 size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold">Remove Member</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Are you sure you want to delete {memberToDelete.name}?
                </p>
              </div>
            </div>

            <p className="mt-4 text-xs text-muted-foreground">
              Member ID <span className="font-mono text-foreground font-semibold">{memberToDelete.id}</span> and all associated records will be permanently removed from this browser session.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setMemberToDelete(null)}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDeleteMember}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
              >
                Delete Member
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Bulk CSV Import Dialog */}
      <ImportMembersDialog
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        existingMembers={members}
        plans={plans}
        onImportSuccess={(count) =>
          setNotification({
            type: "success",
            message: `Successfully imported and registered ${count} member(s)!`,
          })
        }
      />
    </div>
  );
}
