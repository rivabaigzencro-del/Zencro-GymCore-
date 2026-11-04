"use client";

import { useState } from "react";
import {
  Users,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Eye,
  Edit2,
  Trash2,
  Phone,
  Mail,
  Shield,
  Activity,
  X,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  Briefcase,
  MapPin,
  Calendar,
  IndianRupee,
  Lock,
} from "lucide-react";
import {
  type StaffMember,
  type StaffRole,
  type StaffStatus,
  addStaff,
  updateStaff,
  deleteStaff,
  toggleStaffStatus,
  sortStaffByNumericId,
  logAuditAction,
} from "@/lib/mock-data";
import {
  setActiveSession,
  DEMO_ACCOUNTS,
} from "@/lib/api-client";
import { useSessionStore } from "@/lib/use-session-store";
import { useStaffStore } from "@/lib/use-staff-store";
import {
  isValidIndianMobile,
  formatIndianMobile,
  sanitizeIndianMobile,
} from "@/lib/phone-utils";

export function StaffView() {
  const staff = useStaffStore();
  const session = useSessionStore();

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("All");
  const [statusFilter, setStatusFilter] = useState<string>("All");

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [staffToView, setStaffToView] = useState<StaffMember | null>(null);
  const [staffToEdit, setStaffToEdit] = useState<StaffMember | null>(null);
  const [staffToDelete, setStaffToDelete] = useState<StaffMember | null>(null);

  // Toast
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const showNotification = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4500);
  };

  // Form state
  const [formData, setFormData] = useState<{
    name: string;
    role: StaffRole;
    phone: string;
    email: string;
    joiningDate: string;
    salary: number;
    status: StaffStatus;
    specialization: string;
    address: string;
  }>({
    name: "",
    role: "Personal Trainer",
    phone: "",
    email: "",
    joiningDate: new Date().toISOString().split("T")[0],
    salary: 40000,
    status: "Active",
    specialization: "",
    address: "",
  });

  const [formErrors, setFormErrors] = useState<{
    name?: string;
    phone?: string;
    email?: string;
    salary?: string;
  }>({});

  // Compute stats
  const totalStaff = staff.length;
  const activeStaff = staff.filter((s) => s.status === "Active").length;
  const inactiveStaff = staff.filter((s) => s.status === "Inactive").length;
  const trainersCount = staff.filter(
    (s) => s.role === "Personal Trainer" || s.role === "Fitness Instructor"
  ).length;

  // Open Add modal
  const openAddModal = () => {
    setFormData({
      name: "",
      role: "Personal Trainer",
      phone: "",
      email: "",
      joiningDate: new Date().toISOString().split("T")[0],
      salary: 45000,
      status: "Active",
      specialization: "Strength & Conditioning Coach",
      address: "Bangalore",
    });
    setFormErrors({});
    setIsAddModalOpen(true);
  };

  // Open Edit modal
  const openEditModal = (member: StaffMember) => {
    setStaffToEdit(member);
    setFormData({
      name: member.name,
      role: member.role,
      phone: member.phone,
      email: member.email,
      joiningDate: member.joiningDate,
      salary: member.salary,
      status: member.status,
      specialization: member.specialization || "",
      address: member.address || "",
    });
    setFormErrors({});
  };

  const handlePhoneChange = (val: string) => {
    const digits = sanitizeIndianMobile(val).slice(0, 10);
    setFormData((prev) => ({
      ...prev,
      phone: digits.length === 10 ? formatIndianMobile(digits) : val,
    }));
    if (formErrors.phone) {
      setFormErrors((prev) => ({ ...prev, phone: undefined }));
    }
  };

  const validateForm = (): boolean => {
    const errors: typeof formErrors = {};
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      errors.name = "Full name must be at least 2 characters.";
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const normalizedEmail = formData.email.trim().toLowerCase();
    if (!formData.email.trim() || !emailRegex.test(formData.email.trim())) {
      errors.email = "Please enter a valid email address.";
    } else {
      const duplicateEmail = staff.find(
        (s) =>
          s.email.toLowerCase() === normalizedEmail &&
          (!staffToEdit || s.id.toLowerCase() !== staffToEdit.id.toLowerCase())
      );
      if (duplicateEmail) {
        errors.email = `Email is already registered to ${duplicateEmail.name} (${duplicateEmail.id}).`;
      }
    }

    if (!isValidIndianMobile(formData.phone)) {
      errors.phone = "Enter a valid 10-digit Indian phone number (starts with 6, 7, 8, or 9).";
    } else {
      const normalizedPhone = sanitizeIndianMobile(formData.phone);
      const duplicatePhone = staff.find(
        (s) =>
          sanitizeIndianMobile(s.phone) === normalizedPhone &&
          (!staffToEdit || s.id.toLowerCase() !== staffToEdit.id.toLowerCase())
      );
      if (duplicatePhone) {
        errors.phone = `Mobile number is already registered to ${duplicatePhone.name} (${duplicatePhone.id}).`;
      }
    }

    if (!formData.salary || formData.salary < 1000) {
      errors.salary = "Salary must be at least ₹1,000.";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle Save (Add or Edit)
  const handleSaveStaff = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    if (staffToEdit) {
      // Update
      const updated: StaffMember = {
        ...staffToEdit,
        name: formData.name.trim(),
        role: formData.role,
        phone: formData.phone,
        email: formData.email.trim().toLowerCase(),
        salary: Number(formData.salary),
        status: formData.status,
        specialization: formData.specialization.trim() || undefined,
        address: formData.address.trim() || undefined,
      };
      updateStaff(updated);
      logAuditAction({
        action: "STAFF_UPDATE",
        actionLabel: "Staff Member Updated",
        entityType: "Staff",
        entityId: updated.id,
        entityName: updated.name,
        performedBy: "Administrator",
        description: `Updated profile details, role (${updated.role}), and salary (₹${updated.salary.toLocaleString("en-IN")}) for ${updated.name}.`,
        previousValue: {
          name: staffToEdit.name,
          role: staffToEdit.role,
          phone: staffToEdit.phone,
          email: staffToEdit.email,
          salary: staffToEdit.salary,
          status: staffToEdit.status,
        },
        updatedValue: {
          name: updated.name,
          role: updated.role,
          phone: updated.phone,
          email: updated.email,
          salary: updated.salary,
          status: updated.status,
        },
        severity: "info",
      });
      showNotification(`Staff member ${updated.name} updated successfully.`);
      setStaffToEdit(null);
    } else {
      // Add
      const added = addStaff({
        name: formData.name.trim(),
        role: formData.role,
        phone: formData.phone,
        email: formData.email.trim().toLowerCase(),
        joiningDate: formData.joiningDate,
        salary: Number(formData.salary),
        status: formData.status,
        specialization: formData.specialization.trim() || undefined,
        address: formData.address.trim() || undefined,
      });
      logAuditAction({
        action: "STAFF_CREATE",
        actionLabel: "Staff Member Created",
        entityType: "Staff",
        entityId: added.id,
        entityName: added.name,
        performedBy: "Administrator",
        description: `Registered new staff member ${added.name} (${added.id}) as ${added.role} with salary ₹${added.salary.toLocaleString("en-IN")}.`,
        previousValue: null,
        updatedValue: {
          id: added.id,
          name: added.name,
          role: added.role,
          salary: added.salary,
          status: added.status,
        },
        severity: "info",
      });
      showNotification(`Staff member ${added.name} (${added.id}) added successfully.`);
      setIsAddModalOpen(false);
    }
  };

  // Toggle status
  const handleToggleStatus = (id: string) => {
    const updated = toggleStaffStatus(id);
    if (updated) {
      logAuditAction({
        action: updated.status === "Active" ? "STAFF_ACTIVATE" : "STAFF_DEACTIVATE",
        actionLabel: `Staff Member ${updated.status === "Active" ? "Activated" : "Deactivated"}`,
        entityType: "Staff",
        entityId: updated.id,
        entityName: updated.name,
        performedBy: "Administrator",
        description: `Changed staff employment status for ${updated.name} (${updated.id}) to ${updated.status}.`,
        previousValue: { status: updated.status === "Active" ? "Inactive" : "Active" },
        updatedValue: { status: updated.status },
        severity: updated.status === "Inactive" ? "warning" : "info",
      });
      showNotification(
        `Staff status for ${updated.name} changed to ${updated.status}.`
      );
    }
  };

  // Confirm delete
  const handleConfirmDelete = () => {
    if (!staffToDelete) return;
    deleteStaff(staffToDelete.id);
    logAuditAction({
      action: "STAFF_DELETE",
      actionLabel: "Staff Member Deleted",
      entityType: "Staff",
      entityId: staffToDelete.id,
      entityName: staffToDelete.name,
      performedBy: "Administrator",
      description: `Removed staff member ${staffToDelete.name} (${staffToDelete.id}) from active staff roster.`,
      previousValue: {
        id: staffToDelete.id,
        name: staffToDelete.name,
        role: staffToDelete.role,
        salary: staffToDelete.salary,
      },
      updatedValue: null,
      severity: "warning",
    });
    showNotification(`Staff member ${staffToDelete.name} (${staffToDelete.id}) removed.`);
    setStaffToDelete(null);
  };

  // Filter staff
  const filteredStaff = sortStaffByNumericId(
    staff.filter((s) => {
      if (roleFilter !== "All" && s.role !== roleFilter) {
        return false;
      }
      if (statusFilter !== "All" && s.status !== statusFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const match =
          s.name.toLowerCase().includes(q) ||
          s.id.toLowerCase().includes(q) ||
          s.email.toLowerCase().includes(q) ||
          s.role.toLowerCase().includes(q) ||
          s.phone.toLowerCase().includes(q);
        if (!match) return false;
      }
      return true;
    })
  );

  const getRoleBadge = (role: StaffRole) => {
    switch (role) {
      case "Gym Manager":
        return "border-[#C9A04F]/30 bg-[#C9A04F]/10 text-[#C9A04F]";
      case "Personal Trainer":
        return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
      case "Fitness Instructor":
        return "border-sky-500/30 bg-sky-500/10 text-sky-400";
      case "Receptionist":
        return "border-purple-500/30 bg-purple-500/10 text-purple-400";
      case "Cleaning Staff":
        return "border-zinc-500/30 bg-zinc-500/10 text-zinc-400";
      default:
        return "border-border bg-card text-foreground";
    }
  };

  if (session?.role === "Front Desk") {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-8 sm:p-12 text-center max-w-xl mx-auto shadow-sm">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500">
            <Lock size={28} />
          </div>
          <h2 className="mt-4 text-xl font-bold text-foreground">Access Restricted — Front Desk Demo Role</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Front Desk staff have permissions for Member Registration, Membership Assignment, Payment Collection, Receipts, and Attendance Check-in only.
          </p>
          <p className="mt-2 text-xs text-muted-foreground/80">
            Staff management, salary records, and employee rosters are restricted to Gym Owners and Managers.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={() => setActiveSession(DEMO_ACCOUNTS["owner@gymcore.com"])}
              className="rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black hover:bg-[#b68d3e] transition"
            >
              Switch to Owner (Vikram)
            </button>
            <button
              onClick={() => setActiveSession(DEMO_ACCOUNTS["manager@gymcore.com"])}
              className="rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-foreground hover:bg-muted transition"
            >
              Switch to Manager (Rajesh)
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
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

      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-card via-card to-[#C9A04F]/10 p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#C9A04F]">
              <Sparkles size={14} />
              <span>Team & Human Resources</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Staff & Trainers Directory
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Manage personal trainers, floor managers, instructors, and front-desk staff. Track
              compensation, roles, and employment status.
            </p>
          </div>

          <button
            onClick={openAddModal}
            className="flex items-center gap-2 rounded-xl bg-[#C9A04F] px-5 py-3 text-sm font-bold text-black transition-all hover:bg-[#b68d3e] shadow-lg shadow-[#C9A04F]/10"
          >
            <Plus size={18} />
            <span>Add Staff Member</span>
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Staff
            </span>
            <div className="rounded-xl bg-[#C9A04F]/10 p-2.5 text-[#C9A04F]">
              <Users size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{totalStaff}</span>
            <span className="text-xs text-muted-foreground">employees</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">All registered team members</p>
        </div>

        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-5 transition-colors hover:border-emerald-500/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Active Staff
            </span>
            <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-400">
              <Activity size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">{activeStaff}</span>
            <span className="text-xs text-emerald-500/80">currently on duty</span>
          </div>
          <p className="mt-1 text-xs text-emerald-500/80">Active workforce</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Trainers & Coaches
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
              <Briefcase size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{trainersCount}</span>
            <span className="text-xs text-muted-foreground">certified experts</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Personal trainers & instructors</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Inactive Staff
            </span>
            <div className="rounded-xl bg-zinc-500/10 p-2.5 text-zinc-400">
              <Shield size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{inactiveStaff}</span>
            <span className="text-xs text-muted-foreground">on leave / inactive</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Inactive records</p>
        </div>
      </div>

      {/* Staff Directory Table Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground">Staff Directory</h2>
            <p className="text-xs text-muted-foreground">
              Complete roster with contact details, roles, and status management
            </p>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search */}
            <div className="relative min-w-[220px]">
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                placeholder="Search staff, role, email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
              />
            </div>

            {/* Role Filter */}
            <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
              <Filter size={13} className="text-muted-foreground" />
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-transparent text-xs text-foreground focus:outline-none"
              >
                <option value="All">All Roles</option>
                <option value="Gym Manager">Gym Manager</option>
                <option value="Personal Trainer">Personal Trainer</option>
                <option value="Fitness Instructor">Fitness Instructor</option>
                <option value="Receptionist">Receptionist</option>
                <option value="Cleaning Staff">Cleaning Staff</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
              <Filter size={13} className="text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-transparent text-xs text-foreground focus:outline-none"
              >
                <option value="All">All Statuses</option>
                <option value="Active">Active Only</option>
                <option value="Inactive">Inactive Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="pb-3 pl-2">Staff Member</th>
                <th className="pb-3">Role</th>
                <th className="pb-3">Contact</th>
                <th className="pb-3">Monthly Salary</th>
                <th className="pb-3">Joining Date</th>
                <th className="pb-3">Status</th>
                <th className="pb-3 pr-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50 text-foreground">
              {filteredStaff.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-xs text-muted-foreground">
                    No staff members match your search criteria.
                  </td>
                </tr>
              ) : (
                filteredStaff.map((member) => (
                  <tr key={member.id} className="transition-colors hover:bg-muted/30">
                    <td className="py-3.5 pl-2">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#C9A04F]/10 font-bold text-xs text-[#C9A04F]">
                          {member.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </div>
                        <div>
                          <div className="font-semibold text-foreground">{member.name}</div>
                          <div className="text-[11px] font-mono text-[#C9A04F]">{member.id}</div>
                          {member.specialization && (
                            <div className="text-[11px] text-muted-foreground">
                              {member.specialization}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5">
                      <span
                        className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getRoleBadge(
                          member.role
                        )}`}
                      >
                        {member.role}
                      </span>
                    </td>
                    <td className="py-3.5 text-xs">
                      <div className="flex items-center gap-1 text-foreground">
                        <Phone size={11} className="text-muted-foreground" />
                        <span>{member.phone}</span>
                      </div>
                      <div className="flex items-center gap-1 text-muted-foreground mt-0.5">
                        <Mail size={11} />
                        <span className="truncate max-w-[150px]">{member.email}</span>
                      </div>
                    </td>
                    <td className="py-3.5 font-bold text-foreground text-xs">
                      ₹{member.salary.toLocaleString("en-IN")}
                    </td>
                    <td className="py-3.5 text-xs text-muted-foreground">{member.joiningDate}</td>
                    <td className="py-3.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          member.status === "Active"
                            ? "border border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                            : "border border-zinc-500/20 bg-zinc-500/10 text-zinc-400"
                        }`}
                      >
                        {member.status}
                      </span>
                    </td>
                    <td className="py-3.5 pr-2 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setStaffToView(member);
                          }}
                          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-[#C9A04F]/10 hover:text-[#C9A04F]"
                          title="View Staff Details"
                          aria-label={`View details for ${member.name}`}
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleToggleStatus(member.id);
                          }}
                          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          title={`Mark ${member.status === "Active" ? "Inactive" : "Active"}`}
                          aria-label={`Toggle status for ${member.name}`}
                        >
                          {member.status === "Active" ? (
                            <ToggleRight size={18} className="text-emerald-400" />
                          ) : (
                            <ToggleLeft size={18} className="text-zinc-500" />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEditModal(member);
                          }}
                          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          title="Edit Staff"
                          aria-label={`Edit ${member.name}`}
                        >
                          <Edit2 size={15} />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setStaffToDelete(member);
                          }}
                          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-red-500/10 hover:text-red-400"
                          title="Delete Staff"
                          aria-label={`Delete ${member.name}`}
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
      </div>

      {/* Add / Edit Staff Modal */}
      {(isAddModalOpen || staffToEdit) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <button
              onClick={() => {
                setIsAddModalOpen(false);
                setStaffToEdit(null);
              }}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 border-b border-border pb-4">
              <Briefcase size={20} className="text-[#C9A04F]" />
              <h2 className="text-lg font-bold text-foreground">
                {staffToEdit ? `Edit Staff Member (${staffToEdit.id})` : "Add New Staff Member"}
              </h2>
            </div>

            <form onSubmit={handleSaveStaff} className="mt-5 space-y-4">
              {/* Name & Role */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="staff-name" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Full Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    id="staff-name"
                    type="text"
                    placeholder="e.g. Vikram Rathore"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                  {formErrors.name && (
                    <p className="mt-1 text-xs text-red-400">{formErrors.name}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="staff-role" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Role / Designation
                  </label>
                  <select
                    id="staff-role"
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({ ...formData, role: e.target.value as StaffRole })
                    }
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  >
                    <option value="Gym Manager">Gym Manager</option>
                    <option value="Personal Trainer">Personal Trainer</option>
                    <option value="Fitness Instructor">Fitness Instructor</option>
                    <option value="Receptionist">Receptionist</option>
                    <option value="Cleaning Staff">Cleaning Staff</option>
                  </select>
                </div>
              </div>

              {/* Phone & Email */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="staff-phone" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Mobile Number <span className="text-red-400">*</span>
                  </label>
                  <input
                    id="staff-phone"
                    type="tel"
                    placeholder="+91 98450 12345"
                    value={formData.phone}
                    onChange={(e) => handlePhoneChange(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                  {formErrors.phone && (
                    <p className="mt-1 text-xs text-red-400">{formErrors.phone}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="staff-email" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Email Address <span className="text-red-400">*</span>
                  </label>
                  <input
                    id="staff-email"
                    type="email"
                    placeholder="vikram@gymcore.fit"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                  {formErrors.email && (
                    <p className="mt-1 text-xs text-red-400">{formErrors.email}</p>
                  )}
                </div>
              </div>

              {/* Salary & Joining Date */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="staff-salary" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Monthly Salary (INR ₹)
                  </label>
                  <div className="relative mt-1">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 font-bold text-muted-foreground">
                      ₹
                    </span>
                    <input
                      id="staff-salary"
                      type="number"
                      min={1000}
                      step={500}
                      value={formData.salary}
                      onChange={(e) =>
                        setFormData({ ...formData, salary: Number(e.target.value) })
                      }
                      className="w-full rounded-xl border border-border bg-background py-2.5 pl-8 pr-3 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                  {formErrors.salary && (
                    <p className="mt-1 text-xs text-red-400">{formErrors.salary}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="staff-joining-date" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Joining Date
                  </label>
                  <input
                    id="staff-joining-date"
                    type="date"
                    value={formData.joiningDate}
                    onChange={(e) =>
                      setFormData({ ...formData, joiningDate: e.target.value })
                    }
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>
              </div>

              {/* Specialization & Status */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="staff-specialization" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Specialization / Skills
                  </label>
                  <input
                    id="staff-specialization"
                    type="text"
                    placeholder="e.g. CrossFit, Nutrition Coach"
                    value={formData.specialization}
                    onChange={(e) =>
                      setFormData({ ...formData, specialization: e.target.value })
                    }
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>

                <div>
                  <label htmlFor="staff-status" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Employment Status
                  </label>
                  <select
                    id="staff-status"
                    value={formData.status}
                    onChange={(e) =>
                      setFormData({ ...formData, status: e.target.value as StaffStatus })
                    }
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>

              {/* Address */}
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Residential Address
                </label>
                <input
                  type="text"
                  placeholder="e.g. Indiranagar, Bangalore"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                />
              </div>

              {/* Modal Actions */}
              <div className="mt-6 flex items-center justify-end gap-3 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setIsAddModalOpen(false);
                    setStaffToEdit(null);
                  }}
                  className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-[#C9A04F] px-5 py-2.5 text-sm font-bold text-black transition-all hover:bg-[#b68d3e]"
                >
                  {staffToEdit ? "Update Staff Record" : "Add Staff Member"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Read-Only Staff Details Modal */}
      {staffToView && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm overflow-y-auto"
          onClick={() => setStaffToView(null)}
        >
          <div
            className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-[#C9A04F]/10 p-2 text-[#C9A04F]">
                  <Eye size={18} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-foreground">Staff Profile Details</h2>
                    <span className="rounded-md border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-2 py-0.5 font-mono text-xs font-semibold text-[#C9A04F]">
                      {staffToView.id}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Read-only employee record from the GYMCORE registry
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setStaffToView(null)}
                className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                aria-label="Close details"
              >
                <X size={18} />
              </button>
            </div>

            {/* Profile Summary Card */}
            <div className="mt-5 flex items-center gap-4 rounded-xl border border-border bg-background/50 p-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#C9A04F]/15 text-lg font-extrabold text-[#C9A04F] ring-1 ring-[#C9A04F]/30">
                {staffToView.name
                  .split(" ")
                  .map((n) => n[0])
                  .join("")}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-bold text-foreground truncate">{staffToView.name}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/50 px-2 py-0.5 font-medium text-foreground">
                    <Briefcase size={12} className="text-[#C9A04F]" />
                    {staffToView.role}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      staffToView.status === "Active"
                        ? "border border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                        : "border border-zinc-500/20 bg-zinc-500/10 text-zinc-400"
                    }`}
                  >
                    {staffToView.status}
                  </span>
                </div>
              </div>
            </div>

            {/* Details Grid */}
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
              <div className="rounded-xl border border-border bg-background/40 p-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Phone size={13} className="text-[#C9A04F]" />
                  <span>Mobile Phone</span>
                </div>
                <div className="mt-1 font-semibold text-foreground">{staffToView.phone}</div>
              </div>

              <div className="rounded-xl border border-border bg-background/40 p-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Mail size={13} className="text-[#C9A04F]" />
                  <span>Email Address</span>
                </div>
                <div className="mt-1 font-semibold text-foreground truncate">{staffToView.email}</div>
              </div>

              <div className="rounded-xl border border-border bg-background/40 p-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <IndianRupee size={13} className="text-[#C9A04F]" />
                  <span>Monthly Compensation</span>
                </div>
                <div className="mt-1 font-bold text-foreground">
                  ₹{staffToView.salary.toLocaleString("en-IN")}
                </div>
              </div>

              <div className="rounded-xl border border-border bg-background/40 p-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Calendar size={13} className="text-[#C9A04F]" />
                  <span>Joining Date</span>
                </div>
                <div className="mt-1 font-semibold text-foreground">{staffToView.joiningDate}</div>
              </div>

              <div className="sm:col-span-2 rounded-xl border border-border bg-background/40 p-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Shield size={13} className="text-[#C9A04F]" />
                  <span>Specialization & Expertise</span>
                </div>
                <div className="mt-1 font-medium text-foreground">
                  {staffToView.specialization || "General Gym Operations & Floor Management"}
                </div>
              </div>

              <div className="sm:col-span-2 rounded-xl border border-border bg-background/40 p-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <MapPin size={13} className="text-[#C9A04F]" />
                  <span>Residential Address</span>
                </div>
                <div className="mt-1 font-medium text-foreground">
                  {staffToView.address || "No residential address provided on file"}
                </div>
              </div>
            </div>

            {/* Read-Only Notice */}
            <div className="mt-4 rounded-xl border border-border/60 bg-muted/20 p-2.5 text-center text-[11px] text-muted-foreground">
              This is a read-only employee profile. To change compensation or roles, use the Edit action in the table.
            </div>

            {/* Modal Footer */}
            <div className="mt-5 flex items-center justify-end border-t border-border pt-4">
              <button
                type="button"
                onClick={() => setStaffToView(null)}
                className="rounded-xl bg-[#C9A04F] px-5 py-2 text-xs font-bold text-black transition-all hover:bg-[#b68d3e]"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Staff Confirmation Modal */}
      {staffToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <AlertCircle size={24} />
              <h2 className="text-lg font-bold text-foreground">Remove Staff Member?</h2>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Are you sure you want to remove{" "}
              <strong className="text-foreground">
                {staffToDelete.name} ({staffToDelete.id})
              </strong>
              ? This action will permanently remove their profile and records.
            </p>
            {session?.role === "Manager" ? (
              <div className="mt-4 space-y-3">
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                  <strong>Manager Permission Notice:</strong> Permanent employee deletion is restricted to Owner privileges. Managers may toggle status to &quot;Inactive&quot; instead.
                </div>
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => setStaffToDelete(null)}
                    className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted"
                  >
                    Close
                  </button>
                  <button
                    onClick={() => {
                      setActiveSession(DEMO_ACCOUNTS["owner@gymcore.com"]);
                      showNotification("Switched to Owner demo role with deletion privileges");
                    }}
                    className="rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black hover:bg-[#b68d3e]"
                  >
                    Switch to Owner to Delete
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  onClick={() => setStaffToDelete(null)}
                  className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  className="rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 transition-colors"
                >
                  Confirm Remove
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
