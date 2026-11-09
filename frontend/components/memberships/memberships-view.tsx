"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  CreditCard,
  Check,
  Plus,
  Edit,
  Trash2,
  Sparkles,
  Users,
  Search,
  X,
  CheckCircle2,
  AlertCircle,
  Calendar,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import {
  type MembershipPlanItem,
  addPlan,
  updatePlan,
  deletePlan,
  assignMembershipToMember,
  sortMembersByNumericId,
} from "@/lib/mock-data";
import { usePlansStore } from "@/lib/use-plans-store";
import { useMembersStore } from "@/lib/use-members-store";
import {
  syncPlansFromBackend,
  createPlanOnBackend,
  isBackendConnected,
} from "@/lib/backend-sync";

export function MembershipsView() {
  const plans = usePlansStore();
  const members = useMembersStore();

  useEffect(() => {
    if (isBackendConnected()) {
      syncPlansFromBackend().catch(() => {});
    }
  }, []);

  const [searchQuery, setSearchQuery] = useState("");
  const [durationFilter, setDurationFilter] = useState("All");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [planToEdit, setPlanToEdit] = useState<MembershipPlanItem | null>(null);
  const [planToDelete, setPlanToDelete] = useState<MembershipPlanItem | null>(null);
  const [assigningPlan, setAssigningPlan] = useState<MembershipPlanItem | null>(null);

  // Assign modal state
  const [selectedMemberId, setSelectedMemberId] = useState("");

  // Toast notification
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Form state for Create / Edit
  const [formData, setFormData] = useState({
    name: "",
    price: 1999,
    durationMonths: 1,
    durationLabel: "1 Month",
    tagline: "",
    popular: false,
    featuresText: "",
  });

  const [formErrors, setFormErrors] = useState<{
    name?: string;
    price?: string;
    features?: string;
  }>({});

  const showNotification = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4500);
  };

  // Open Create Modal
  const openCreateModal = () => {
    setFormData({
      name: "",
      price: 2499,
      durationMonths: 1,
      durationLabel: "1 Month",
      tagline: "Tailored gym experience for fitness enthusiasts",
      popular: false,
      featuresText:
        "Full gym floor access\nLocker room access\n1 Personal training session\nMobile app check-in",
    });
    setFormErrors({});
    setIsCreateOpen(true);
  };

  // Open Edit Modal
  const openEditModal = (plan: MembershipPlanItem) => {
    setPlanToEdit(plan);
    setFormData({
      name: plan.name,
      price: plan.price,
      durationMonths: plan.durationMonths,
      durationLabel: plan.durationLabel,
      tagline: plan.tagline,
      popular: !!plan.popular,
      featuresText: plan.features.join("\n"),
    });
    setFormErrors({});
  };

  // Validate Plan Form
  const validatePlanForm = (): boolean => {
    const errors: typeof formErrors = {};
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      errors.name = "Plan name must be at least 2 characters.";
    }
    if (!formData.price || formData.price <= 0) {
      errors.price = "Price must be greater than 0.";
    }
    const featuresList = formData.featuresText
      .split("\n")
      .map((f) => f.trim())
      .filter(Boolean);
    if (featuresList.length === 0) {
      errors.features = "Please add at least one plan feature.";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle Save (Create or Update)
  const handleSavePlan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validatePlanForm()) return;

    const features = formData.featuresText
      .split("\n")
      .map((f) => f.trim())
      .filter(Boolean);

    const durationLabel =
      formData.durationMonths === 1
        ? "1 Month"
        : formData.durationMonths === 12
        ? "12 Months (1 Year)"
        : `${formData.durationMonths} Months`;

    if (planToEdit) {
      const updated: MembershipPlanItem = {
        ...planToEdit,
        name: formData.name.trim(),
        price: Number(formData.price),
        durationMonths: Number(formData.durationMonths),
        durationLabel,
        tagline: formData.tagline.trim(),
        popular: formData.popular,
        features,
        color: formData.popular ? "border-[#C9A04F]" : "border-border",
        badge: formData.popular ? "POPULAR" : undefined,
      };
      updatePlan(updated);
      setPlanToEdit(null);
      showNotification(`Membership plan "${updated.name}" has been updated.`);
    } else {
      const newId = `plan-${formData.name.toLowerCase().replace(/\s+/g, "-")}-${Date.now().toString().slice(-4)}`;
      const created: MembershipPlanItem = {
        id: newId,
        name: formData.name.trim(),
        price: Number(formData.price),
        durationMonths: Number(formData.durationMonths),
        durationLabel,
        tagline: formData.tagline.trim(),
        popular: formData.popular,
        features,
        color: formData.popular ? "border-[#C9A04F]" : "border-border",
        badge: formData.popular ? "POPULAR" : "CUSTOM",
      };
      addPlan(created);
      if (isBackendConnected()) {
        createPlanOnBackend({
          name: created.name,
          durationMonths: created.durationMonths,
          price: created.price,
          description: created.tagline,
        }).catch(() => {});
      }
      setIsCreateOpen(false);
      showNotification(`New membership plan "${created.name}" created!`);
    }
  };

  // Handle Delete
  const handleConfirmDelete = () => {
    if (!planToDelete) return;
    deletePlan(planToDelete.id);
    showNotification(`Plan "${planToDelete.name}" was removed.`);
    setPlanToDelete(null);
  };

  // Open Assign Modal
  const openAssignModal = (plan: MembershipPlanItem) => {
    setAssigningPlan(plan);
    setSelectedMemberId(members[0]?.id || "");
  };

  // Handle Assign Plan to Member
  const handleConfirmAssign = (e: React.FormEvent) => {
    e.preventDefault();
    if (!assigningPlan || !selectedMemberId) return;

    const res = assignMembershipToMember(
      selectedMemberId,
      assigningPlan.name,
      assigningPlan.durationMonths
    );

    if (res.success) {
      showNotification(res.message);
      setAssigningPlan(null);
    } else {
      showNotification(res.message, "error");
    }
  };

  // Filter plans
  const filteredPlans = plans.filter((plan) => {
    const matchesQuery =
      plan.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      plan.tagline.toLowerCase().includes(searchQuery.toLowerCase()) ||
      plan.features.some((f) => f.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesDuration =
      durationFilter === "All" ||
      (durationFilter === "1" && plan.durationMonths === 1) ||
      (durationFilter === "3" && plan.durationMonths === 3) ||
      (durationFilter === "12" && plan.durationMonths === 12);

    return matchesQuery && matchesDuration;
  });

  // Calculate subscribers per plan
  const getSubscriberCount = (planName: string) => {
    return members.filter((m) => m.plan.toLowerCase() === planName.toLowerCase()).length;
  };

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
            <div className="inline-flex items-center gap-2 rounded-full bg-[#C9A04F]/15 px-3 py-1 text-xs font-semibold text-[#C9A04F]">
              <Sparkles size={14} />
              <span>MEMBERSHIP TIERS & PRICING</span>
            </div>

            <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Gym Membership Packages
            </h1>

            <p className="mt-1 text-sm text-muted-foreground">
              Define membership packages, included fitness amenities, pricing models, and assign plans directly to registered members.
            </p>
          </div>

          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 rounded-lg bg-[#C9A04F] px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-[#b68d3e] shadow-sm"
          >
            <Plus size={18} />
            <span>Create New Plan</span>
          </button>
        </div>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Available Tiers</span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#C9A04F]/10 text-[#C9A04F]">
              <CreditCard size={18} />
            </div>
          </div>
          <p className="mt-3 text-2xl font-bold">{plans.length} Active Plans</p>
          <p className="mt-1 text-xs text-muted-foreground">Basic, Standard, Premium & Custom</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Subscribers</span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-500/10 text-green-500">
              <Users size={18} />
            </div>
          </div>
          <p className="mt-3 text-2xl font-bold">{members.length} Enrolled</p>
          <p className="mt-1 text-xs text-muted-foreground">Across all gym membership tiers</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Most Chosen Tier</span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
              <TrendingUp size={18} />
            </div>
          </div>
          <p className="mt-3 text-2xl font-bold">Standard Tier</p>
          <p className="mt-1 text-xs text-muted-foreground">3 Months • ₹3,999</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Backend Status</span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500">
              <ShieldCheck size={18} />
            </div>
          </div>
          <p className="mt-3 text-lg font-bold">Frontend Demo Data</p>
          <p className="mt-1 text-xs text-muted-foreground">Ready for Riva&apos;s FastAPI backend</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <select
          value={durationFilter}
          onChange={(e) => setDurationFilter(e.target.value)}
          aria-label="Filter by billing duration"
          className="rounded-lg border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
        >
          <option value="All">All Durations</option>
          <option value="1">1 Month (Monthly)</option>
          <option value="3">3 Months (Quarterly)</option>
          <option value="12">12 Months (Annual)</option>
        </select>

        <div className="relative max-w-sm flex-1">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="text"
            placeholder="Search plans by name, amenity, feature..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-border bg-background py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-[#C9A04F]"
          />
        </div>
      </div>

      {/* Plans Cards Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredPlans.length === 0 ? (
          <div className="col-span-full rounded-2xl border border-border bg-card p-12 text-center text-muted-foreground">
            <CreditCard size={36} className="mx-auto mb-2 opacity-40" />
            <p className="text-base font-semibold text-foreground">No membership plans match your search</p>
            <p className="text-xs text-muted-foreground mt-1">Try clearing your search query or filters.</p>
          </div>
        ) : (
          filteredPlans.map((plan) => {
            const subscribers = getSubscriberCount(plan.name);

            return (
              <div
                key={plan.id}
                className={`group relative flex flex-col justify-between rounded-2xl border bg-card p-6 shadow-sm transition hover:shadow-md ${
                  plan.popular
                    ? "border-[#C9A04F] ring-1 ring-[#C9A04F]/40"
                    : "border-border hover:border-[#C9A04F]/40"
                }`}
              >
                {/* Popular or Custom Badge */}
                {plan.badge && (
                  <div className="absolute -top-3 right-6">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[10px] font-bold tracking-wider uppercase shadow-xs ${
                        plan.popular
                          ? "bg-[#C9A04F] text-black"
                          : "bg-muted border border-border text-foreground"
                      }`}
                    >
                      <Sparkles size={11} />
                      {plan.badge}
                    </span>
                  </div>
                )}

                <div>
                  {/* Title & Tagline */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-bold tracking-tight text-foreground">
                        {plan.name}
                      </h3>
                      <p className="mt-1 text-xs text-muted-foreground min-h-[32px]">
                        {plan.tagline}
                      </p>
                    </div>
                  </div>

                  {/* Price */}
                  <div className="mt-5 flex items-baseline gap-1 border-b border-border pb-5">
                    <span className="text-3xl font-extrabold text-foreground">
                      ₹{plan.price.toLocaleString("en-IN")}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      / {plan.durationLabel}
                    </span>
                  </div>

                  {/* Subscriber Counter & Duration */}
                  <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1.5 font-medium text-foreground">
                      <Users size={14} className="text-[#C9A04F]" />
                      <span>{subscribers} members enrolled</span>
                    </span>
                    <span className="rounded-md bg-muted px-2 py-0.5 font-mono text-[11px]">
                      {plan.durationMonths} mo validity
                    </span>
                  </div>

                  {/* Features List */}
                  <div className="mt-5 space-y-2.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Included Amenities:
                    </p>
                    <ul className="space-y-2">
                      {plan.features.map((feature, idx) => (
                        <li key={idx} className="flex items-start gap-2.5 text-xs text-foreground/90">
                          <div className="mt-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#C9A04F]/20 text-[#C9A04F] shrink-0">
                            <Check size={11} />
                          </div>
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Card Actions Footer */}
                <div className="mt-8 pt-5 border-t border-border space-y-2">
                  <button
                    onClick={() => openAssignModal(plan)}
                    className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#C9A04F] px-4 py-2.5 text-xs font-semibold text-black transition hover:bg-[#b68d3e]"
                  >
                    <UserPlus size={15} />
                    <span>Assign Plan to Member</span>
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openEditModal(plan)}
                      className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-border py-2 text-xs font-medium text-foreground transition hover:bg-muted"
                    >
                      <Edit size={13} />
                      <span>Edit Details</span>
                    </button>

                    <button
                      onClick={() => setPlanToDelete(plan)}
                      aria-label={`Delete ${plan.name} plan`}
                      className="rounded-lg border border-border p-2 text-muted-foreground transition hover:bg-red-500/10 hover:text-red-500 hover:border-red-500/30"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Member Enrollment Summary Table */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div>
            <h2 className="text-base font-semibold text-foreground">
              Current Member Plan Distribution
            </h2>
            <p className="text-xs text-muted-foreground">
              Active subscriptions and their upcoming renewal dates
            </p>
          </div>
          <Link
            href="/members"
            className="inline-flex items-center gap-1 text-xs font-semibold text-[#C9A04F] hover:underline"
          >
            <span>Manage Members</span>
            <ArrowRight size={13} />
          </Link>
        </div>

        <div className="mt-4 divide-y divide-border overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-muted-foreground uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-2.5">Member</th>
                <th className="py-2.5">Assigned Plan</th>
                <th className="py-2.5">Status</th>
                <th className="py-2.5">Renewal Due</th>
                <th className="py-2.5 text-right">Profile</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortMembersByNumericId(members).map((m) => (
                <tr key={m.id} className="hover:bg-muted/40 transition">
                  <td className="py-3 font-medium text-foreground">
                    <div>
                      <p className="font-semibold">{m.name}</p>
                      <p className="text-[11px] font-mono text-muted-foreground">{m.id}</p>
                    </div>
                  </td>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1 font-medium text-foreground">
                      <Sparkles size={12} className="text-[#C9A04F]" />
                      {m.plan}
                    </span>
                  </td>
                  <td className="py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        m.status === "Active"
                          ? "bg-green-500/10 text-green-500"
                          : m.status === "Expired"
                          ? "bg-red-500/10 text-red-500"
                          : "bg-blue-500/10 text-blue-500"
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                  <td className="py-3 font-mono text-muted-foreground">
                    {m.validUntil || "Active"}
                  </td>
                  <td className="py-3 text-right">
                    <Link
                      href={`/members/${m.id}`}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-[#C9A04F] hover:bg-[#C9A04F]/10 transition"
                    >
                      <span>View</span>
                      <ArrowRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Assign Plan Modal */}
      {assigningPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div>
                <h3 className="text-lg font-bold">Assign Membership Plan</h3>
                <p className="text-xs text-muted-foreground">
                  Assign &quot;{assigningPlan.name}&quot; (₹{assigningPlan.price.toLocaleString("en-IN")})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAssigningPlan(null)}
                className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleConfirmAssign} className="mt-4 space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium">Select Gym Member</label>
                <select
                  value={selectedMemberId}
                  onChange={(e) => setSelectedMemberId(e.target.value)}
                  required
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                >
                  {sortMembersByNumericId(members).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.id}) — Currently on {m.plan}
                    </option>
                  ))}
                </select>
              </div>

              <div className="rounded-xl border border-border bg-muted/30 p-3.5 text-xs text-muted-foreground space-y-1.5">
                <p className="font-semibold text-foreground flex items-center gap-1.5">
                  <Calendar size={14} className="text-[#C9A04F]" />
                  <span>Subscription Duration</span>
                </p>
                <p>
                  This membership will be valid for <strong>{assigningPlan.durationMonths} month(s)</strong> from today. The member status will be set to <strong>Active</strong>.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setAssigningPlan(null)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-[#C9A04F] px-4 py-2 text-sm font-semibold text-black hover:bg-[#b68d3e]"
                >
                  Confirm Assignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create / Edit Plan Modal */}
      {(isCreateOpen || planToEdit) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
              <div>
                <h3 className="text-xl font-bold">
                  {planToEdit ? `Edit ${planToEdit.name} Plan` : "Create New Membership Plan"}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Configure plan pricing, duration, and feature amenities
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsCreateOpen(false);
                  setPlanToEdit(null);
                }}
                className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSavePlan} className="space-y-4">
              {/* Plan Name */}
              <div>
                <label className="mb-1.5 block text-xs font-medium">Plan Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Platinum, Student Pass, Elite"
                  value={formData.name}
                  onChange={(e) => {
                    setFormData({ ...formData, name: e.target.value });
                    if (formErrors.name) setFormErrors({ ...formErrors, name: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                    formErrors.name ? "border-red-500" : "border-border"
                  }`}
                />
                {formErrors.name && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.name}</p>
                )}
              </div>

              {/* Price & Duration */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium">Price (INR ₹) *</label>
                  <input
                    type="number"
                    min="1"
                    placeholder="2999"
                    value={formData.price}
                    onChange={(e) => {
                      setFormData({ ...formData, price: Number(e.target.value) });
                      if (formErrors.price) setFormErrors({ ...formErrors, price: undefined });
                    }}
                    className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F] ${
                      formErrors.price ? "border-red-500" : "border-border"
                    }`}
                  />
                  {formErrors.price && (
                    <p className="mt-1 text-xs text-red-500">{formErrors.price}</p>
                  )}
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium">Duration (Months) *</label>
                  <select
                    value={formData.durationMonths}
                    onChange={(e) =>
                      setFormData({ ...formData, durationMonths: Number(e.target.value) })
                    }
                    className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                  >
                    <option value={1}>1 Month (Monthly)</option>
                    <option value={2}>2 Months</option>
                    <option value={3}>3 Months (Quarterly)</option>
                    <option value={6}>6 Months (Half-Year)</option>
                    <option value={12}>12 Months (1 Year)</option>
                  </select>
                </div>
              </div>

              {/* Tagline */}
              <div>
                <label className="mb-1.5 block text-xs font-medium">Tagline / Short Description</label>
                <input
                  type="text"
                  placeholder="e.g. Recommended for weight loss and bodybuilding"
                  value={formData.tagline}
                  onChange={(e) => setFormData({ ...formData, tagline: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background px-3.5 py-2.5 text-sm outline-none focus:border-[#C9A04F]"
                />
              </div>

              {/* Popular Checkbox */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="popular-plan"
                  checked={formData.popular}
                  onChange={(e) => setFormData({ ...formData, popular: e.target.checked })}
                  className="h-4 w-4 rounded border-border accent-[#C9A04F]"
                />
                <label htmlFor="popular-plan" className="text-xs font-medium cursor-pointer">
                  Feature this plan as &quot;Most Popular&quot; with gold highlight
                </label>
              </div>

              {/* Features List */}
              <div>
                <label className="mb-1.5 block text-xs font-medium">
                  Included Amenities (Enter one feature per line) *
                </label>
                <textarea
                  rows={4}
                  placeholder="Full gym floor access&#10;Locker room & shower&#10;1 Trainer session"
                  value={formData.featuresText}
                  onChange={(e) => {
                    setFormData({ ...formData, featuresText: e.target.value });
                    if (formErrors.features) setFormErrors({ ...formErrors, features: undefined });
                  }}
                  className={`w-full rounded-lg border bg-background px-3.5 py-2.5 text-xs outline-none focus:border-[#C9A04F] ${
                    formErrors.features ? "border-red-500" : "border-border"
                  }`}
                />
                {formErrors.features && (
                  <p className="mt-1 text-xs text-red-500">{formErrors.features}</p>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreateOpen(false);
                    setPlanToEdit(null);
                  }}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-[#C9A04F] px-5 py-2 text-sm font-semibold text-black hover:bg-[#b68d3e]"
                >
                  {planToEdit ? "Save Changes" : "Create Plan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {planToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-border bg-background p-6 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-500 shrink-0">
                <Trash2 size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold">Delete Membership Plan</h3>
                <p className="text-xs text-muted-foreground">Plan: {planToDelete.name}</p>
              </div>
            </div>

            <p className="mt-4 text-xs text-muted-foreground">
              Are you sure you want to delete the <strong>{planToDelete.name}</strong> plan? Members currently enrolled in this plan will retain their tier until reassigned.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setPlanToDelete(null)}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
              >
                Delete Plan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
