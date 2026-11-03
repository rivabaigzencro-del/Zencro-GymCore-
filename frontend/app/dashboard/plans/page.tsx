"use client";

import { useState, useEffect } from "react";
import { plansApi, MembershipPlanResponse } from "@/lib/api";
import { formatINR, formatDuration } from "@/lib/utils";

function PlanCard({
  plan,
  onEdit,
  onDeactivate,
}: {
  plan: MembershipPlanResponse;
  onEdit: (plan: MembershipPlanResponse) => void;
  onDeactivate: (id: string) => void;
}) {
  return (
    <div className={`bg-[#1D1D1D] border rounded-xl p-5 transition-all ${plan.is_active ? "border-[#2A2A2A]" : "border-[#2A2A2A] opacity-60"}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-white">{plan.name}</h3>
          <p className="text-[#9B968C] text-xs mt-0.5">{formatDuration(plan.duration, plan.duration_unit)}</p>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full ${plan.is_active ? "bg-[#D4A84F]/20 text-[#D4A84F]" : "bg-gray-700 text-gray-400"}`}>
          {plan.is_active ? "Active" : "Inactive"}
        </span>
      </div>

      <p className="text-2xl font-bold text-[#D4A84F] mb-2">{formatINR(plan.price)}</p>

      {plan.description && (
        <p className="text-[#9B968C] text-xs mb-4 line-clamp-2">{plan.description}</p>
      )}

      <div className="flex gap-2 pt-3 border-t border-[#2A2A2A]">
        <button
          onClick={() => onEdit(plan)}
          className="flex-1 py-2 rounded-lg border border-[#2A2A2A] text-sm text-white hover:border-[#D4A84F] transition-colors"
        >
          Edit
        </button>
        {plan.is_active && (
          <button
            onClick={() => onDeactivate(plan.id)}
            className="flex-1 py-2 rounded-lg border border-red-800/50 text-sm text-red-400 hover:bg-red-900/20 transition-colors"
          >
            Deactivate
          </button>
        )}
      </div>
    </div>
  );
}

function PlanModal({
  plan,
  onClose,
  onSave,
}: {
  plan: Partial<MembershipPlanResponse> | null;
  onClose: () => void;
  onSave: (data: any) => Promise<void>;
}) {
  const [form, setForm] = useState({
    name: plan?.name ?? "",
    description: plan?.description ?? "",
    duration: String(plan?.duration ?? 1),
    duration_unit: plan?.duration_unit ?? "MONTHS",
    price: String(plan?.price ?? ""),
    is_active: plan?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave({
        name: form.name,
        description: form.description || undefined,
        duration: parseInt(form.duration),
        duration_unit: form.duration_unit,
        price: parseFloat(form.price),
        is_active: form.is_active,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save plan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-2xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">{plan?.id ? "Edit Plan" : "Create Plan"}</h3>

        {error && <div className="mb-3 p-2.5 rounded-lg bg-red-900/30 text-red-400 text-sm">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-[#9B968C] mb-1.5">Plan Name *</label>
            <input required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Monthly, Quarterly Premium"
              className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
          </div>
          <div>
            <label className="block text-sm text-[#9B968C] mb-1.5">Description</label>
            <input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Optional plan description"
              className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Duration *</label>
              <input type="number" min="1" required value={form.duration} onChange={(e) => setForm((f) => ({ ...f, duration: e.target.value }))}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Unit</label>
              <select value={form.duration_unit} onChange={(e) => setForm((f) => ({ ...f, duration_unit: e.target.value as any }))}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm">
                <option value="MONTHS">Months</option>
                <option value="DAYS">Days</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm text-[#9B968C] mb-1.5">Price (₹) *</label>
            <input type="number" min="1" step="0.01" required value={form.price} onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
              placeholder="1500"
              className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="is_active" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              className="accent-[#D4A84F] w-4 h-4" />
            <label htmlFor="is_active" className="text-sm text-[#9B968C]">Active (available for new memberships)</label>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-lg border border-[#2A2A2A] text-sm text-[#9B968C]">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-lg bg-[#D4A84F] text-black font-medium text-sm disabled:opacity-50">
              {saving ? "Saving…" : plan?.id ? "Save Changes" : "Create Plan"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function PlansPage() {
  const [plans, setPlans] = useState<MembershipPlanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Partial<MembershipPlanResponse> | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const res = await plansApi.list(showInactive);
      setPlans(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load plans");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPlans(); }, [showInactive]);

  const handleSave = async (data: any) => {
    if (editingPlan?.id) {
      await plansApi.update(editingPlan.id, data);
      showToast("Plan updated");
    } else {
      await plansApi.create(data);
      showToast("Plan created");
    }
    fetchPlans();
  };

  const handleDeactivate = async (id: string) => {
    if (!confirm("Deactivate this plan? Members with active memberships will not be affected.")) return;
    try {
      await plansApi.deactivate(id);
      showToast("Plan deactivated");
      fetchPlans();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to deactivate plan");
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 bg-[#D4A84F] text-black font-medium px-4 py-3 rounded-lg shadow-lg z-50 text-sm">{toast}</div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Membership Plans</h1>
          <p className="text-[#9B968C] text-sm mt-0.5">{plans.length} plans</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-[#9B968C] cursor-pointer">
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} className="accent-[#D4A84F]" />
            Show inactive
          </label>
          <button
            onClick={() => { setEditingPlan({}); setShowModal(true); }}
            className="bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-semibold px-5 py-2.5 rounded-lg text-sm transition-colors"
          >
            + Create Plan
          </button>
        </div>
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-8 h-8 border-2 border-[#D4A84F] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : plans.length === 0 ? (
        <div className="text-center py-16 text-[#9B968C]">
          <p className="text-4xl mb-3">📋</p>
          <p className="text-lg font-medium">No plans yet</p>
          <p className="text-sm mt-1">Create your first membership plan to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              onEdit={(p) => { setEditingPlan(p); setShowModal(true); }}
              onDeactivate={handleDeactivate}
            />
          ))}
        </div>
      )}

      {showModal && (
        <PlanModal
          plan={editingPlan}
          onClose={() => { setShowModal(false); setEditingPlan(null); }}
          onSave={handleSave}
        />
      )}
    </div>
  );
}

