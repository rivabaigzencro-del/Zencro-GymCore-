"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  membersApi,
  membershipsApi,
  plansApi,
  MemberResponse,
  MembershipResponse,
  MembershipPlanResponse,
} from "@/lib/api";
import { formatDate, formatINR, formatDuration, memberStatusClass, membershipStatusClass } from "@/lib/utils";

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-1 py-3 border-b border-[#2A2A2A] last:border-0">
      <span className="text-[#9B968C] text-sm w-40 flex-shrink-0">{label}</span>
      <span className="text-white text-sm">{value || "—"}</span>
    </div>
  );
}

function Badge({ status, classNameFn }: { status: string; classNameFn: (s: string) => string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${classNameFn(status)}`}>
      {status}
    </span>
  );
}

export default function MemberDetailPage({ params }: { params: Promise<{ member_id: string }> }) {
  const { member_id } = use(params);
  const router = useRouter();

  const [member, setMember] = useState<MemberResponse | null>(null);
  const [memberships, setMemberships] = useState<MembershipResponse[]>([]);
  const [plans, setPlans] = useState<MembershipPlanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState("");
  const [toast, setToast] = useState("");

  // Modals state
  const [showFreezeModal, setShowFreezeModal] = useState(false);
  const [showRenewModal, setShowRenewModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);

  const [freezeForm, setFreezeForm] = useState({ freeze_start_date: "", freeze_end_date: "" });
  const [renewForm, setRenewForm] = useState({ membership_plan_id: "", start_date: "" });
  const [assignForm, setAssignForm] = useState({ membership_plan_id: "", start_date: new Date().toISOString().split("T")[0] });

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [m, ms, ps] = await Promise.all([
        membersApi.get(member_id),
        membershipsApi.list({ member_id, page_size: 50 }),
        plansApi.list(),
      ]);
      setMember(m);
      setMemberships(ms.items);
      setPlans(ps.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load member");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [member_id]);

  const activeMembership = memberships.find((m) => m.status === "ACTIVE" || m.status === "FROZEN");

  const handleDeactivate = async () => {
    if (!confirm("Deactivate this member?")) return;
    setActionLoading("deactivate");
    try {
      await membersApi.deactivate(member_id);
      showToast("Member deactivated");
      fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading("");
    }
  };

  const handleUnfreeze = async () => {
    if (!activeMembership) return;
    setActionLoading("unfreeze");
    try {
      await membershipsApi.unfreeze(activeMembership.id, {});
      showToast("Membership unfrozen");
      fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading("");
    }
  };

  const handleFreeze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMembership) return;
    setActionLoading("freeze");
    try {
      await membershipsApi.freeze(activeMembership.id, freezeForm);
      showToast("Membership frozen");
      setShowFreezeModal(false);
      fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading("");
    }
  };

  const handleRenew = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMembership) return;
    setActionLoading("renew");
    try {
      await membershipsApi.renew(activeMembership.id, {
        membership_plan_id: renewForm.membership_plan_id || undefined,
        start_date: renewForm.start_date || undefined,
      });
      showToast("Membership renewed");
      setShowRenewModal(false);
      fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading("");
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading("assign");
    try {
      await membershipsApi.create({
        member_id,
        membership_plan_id: assignForm.membership_plan_id,
        start_date: assignForm.start_date,
      });
      showToast("Membership assigned");
      setShowAssignModal(false);
      fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading("");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-2 border-[#D4A84F] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!member) {
    return (
      <div className="p-6 text-center text-red-400">{error || "Member not found"}</div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 bg-[#D4A84F] text-black font-medium px-4 py-3 rounded-lg shadow-lg z-50 text-sm">
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => router.back()} className="text-[#9B968C] hover:text-white text-sm mb-3 transition-colors">
            ← Back to Members
          </button>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-[#D4A84F]/15 flex items-center justify-center text-[#D4A84F] text-2xl font-bold">
              {member.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold">{member.full_name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge status={member.status} classNameFn={memberStatusClass} />
                <span className="text-[#9B968C] text-xs">since {formatDate(member.created_at)}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/dashboard/members/${member_id}/edit`}
            className="px-4 py-2 rounded-lg border border-[#2A2A2A] text-sm text-white hover:border-[#D4A84F] transition-colors"
          >
            Edit
          </Link>
          <button
            onClick={handleDeactivate}
            disabled={actionLoading === "deactivate"}
            className="px-4 py-2 rounded-lg border border-red-800/50 text-sm text-red-400 hover:bg-red-900/20 transition-colors"
          >
            Deactivate
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Personal Info */}
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5">
            <h2 className="text-base font-semibold mb-3 text-[#D4A84F]">Personal Information</h2>
            <InfoRow label="Full Name" value={member.full_name} />
            <InfoRow label="Email" value={member.email} />
            <InfoRow label="Phone" value={member.phone} />
            <InfoRow label="Gender" value={member.gender} />
            <InfoRow label="Date of Birth" value={formatDate(member.date_of_birth)} />
            <InfoRow label="Address" value={member.address} />
          </div>

          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5">
            <h2 className="text-base font-semibold mb-3 text-[#D4A84F]">Emergency Contact</h2>
            <InfoRow label="Contact Name" value={member.emergency_contact_name} />
            <InfoRow label="Contact Phone" value={member.emergency_contact_phone} />
          </div>

          {/* Membership History */}
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5">
            <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Membership History</h2>
            {memberships.length === 0 ? (
              <p className="text-[#9B968C] text-sm">No membership history</p>
            ) : (
              <div className="space-y-3">
                {memberships.map((ms) => (
                  <div key={ms.id} className="flex items-center justify-between p-3 bg-[#151515] rounded-lg">
                    <div>
                      <p className="text-sm font-medium">{ms.membership_plan?.name ?? "—"}</p>
                      <p className="text-xs text-[#9B968C] mt-0.5">
                        {formatDate(ms.start_date)} → {formatDate(ms.end_date)}
                        {ms.total_frozen_days > 0 && ` · ${ms.total_frozen_days} frozen days`}
                      </p>
                    </div>
                    <Badge status={ms.status} classNameFn={membershipStatusClass} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Placeholders */}
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5 opacity-50">
            <h2 className="text-base font-semibold text-[#9B968C]">Payment History</h2>
            <p className="text-xs text-[#9B968C] mt-2">Coming in next module</p>
          </div>
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5 opacity-50">
            <h2 className="text-base font-semibold text-[#9B968C]">Attendance History</h2>
            <p className="text-xs text-[#9B968C] mt-2">Coming in next module</p>
          </div>
        </div>

        {/* Membership Actions */}
        <div className="space-y-5">
          {/* Current Membership */}
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5">
            <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Current Membership</h2>
            {activeMembership ? (
              <div className="space-y-3">
                <div>
                  <p className="text-[#9B968C] text-xs">Plan</p>
                  <p className="text-white font-medium">{activeMembership.membership_plan?.name ?? "—"}</p>
                </div>
                <div>
                  <p className="text-[#9B968C] text-xs">Price</p>
                  <p className="text-white">{activeMembership.membership_plan ? formatINR(activeMembership.membership_plan.price) : "—"}</p>
                </div>
                <div>
                  <p className="text-[#9B968C] text-xs">Valid Until</p>
                  <p className="text-white font-medium">{formatDate(activeMembership.end_date)}</p>
                </div>
                <div>
                  <p className="text-[#9B968C] text-xs">Status</p>
                  <Badge status={activeMembership.status} classNameFn={membershipStatusClass} />
                </div>
                {activeMembership.total_frozen_days > 0 && (
                  <div>
                    <p className="text-[#9B968C] text-xs">Total Frozen Days</p>
                    <p className="text-white">{activeMembership.total_frozen_days}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="pt-3 space-y-2 border-t border-[#2A2A2A]">
                  {activeMembership.status === "ACTIVE" && (
                    <button
                      onClick={() => setShowFreezeModal(true)}
                      className="w-full py-2 rounded-lg border border-[#2A2A2A] text-sm text-white hover:border-[#D4A84F] transition-colors"
                    >
                      Freeze Membership
                    </button>
                  )}
                  {activeMembership.status === "FROZEN" && (
                    <button
                      onClick={handleUnfreeze}
                      disabled={actionLoading === "unfreeze"}
                      className="w-full py-2 rounded-lg border border-[#D4A84F]/50 text-sm text-[#D4A84F] hover:bg-[#D4A84F]/10 transition-colors"
                    >
                      {actionLoading === "unfreeze" ? "Unfreezing…" : "Unfreeze"}
                    </button>
                  )}
                  <button
                    onClick={() => setShowRenewModal(true)}
                    className="w-full py-2 rounded-lg bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-medium text-sm transition-colors"
                  >
                    Renew Membership
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-[#9B968C] text-sm mb-3">No active membership</p>
                <button
                  onClick={() => setShowAssignModal(true)}
                  className="w-full py-2 rounded-lg bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-medium text-sm transition-colors"
                >
                  Assign Membership
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Freeze Modal */}
      {showFreezeModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-2xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4">Freeze Membership</h3>
            <form onSubmit={handleFreeze} className="space-y-4">
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Freeze Start Date</label>
                <input type="date" required value={freezeForm.freeze_start_date} onChange={(e) => setFreezeForm((f) => ({ ...f, freeze_start_date: e.target.value }))}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
              </div>
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Freeze End Date</label>
                <input type="date" required value={freezeForm.freeze_end_date} onChange={(e) => setFreezeForm((f) => ({ ...f, freeze_end_date: e.target.value }))}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowFreezeModal(false)} className="flex-1 py-2.5 rounded-lg border border-[#2A2A2A] text-sm text-[#9B968C]">Cancel</button>
                <button type="submit" disabled={actionLoading === "freeze"} className="flex-1 py-2.5 rounded-lg bg-[#D4A84F] text-black font-medium text-sm disabled:opacity-50">
                  {actionLoading === "freeze" ? "Freezing…" : "Freeze"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Renew Modal */}
      {showRenewModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-2xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4">Renew Membership</h3>
            <form onSubmit={handleRenew} className="space-y-4">
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Plan (leave blank to keep current)</label>
                <select value={renewForm.membership_plan_id} onChange={(e) => setRenewForm((f) => ({ ...f, membership_plan_id: e.target.value }))}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm">
                  <option value="">Keep current plan</option>
                  {plans.map((p) => <option key={p.id} value={p.id}>{p.name} — ₹{p.price}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Start Date (leave blank for next day after expiry)</label>
                <input type="date" value={renewForm.start_date} onChange={(e) => setRenewForm((f) => ({ ...f, start_date: e.target.value }))}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowRenewModal(false)} className="flex-1 py-2.5 rounded-lg border border-[#2A2A2A] text-sm text-[#9B968C]">Cancel</button>
                <button type="submit" disabled={actionLoading === "renew"} className="flex-1 py-2.5 rounded-lg bg-[#D4A84F] text-black font-medium text-sm disabled:opacity-50">
                  {actionLoading === "renew" ? "Renewing…" : "Renew"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-2xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold mb-4">Assign Membership</h3>
            <form onSubmit={handleAssign} className="space-y-4">
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Plan *</label>
                <select required value={assignForm.membership_plan_id} onChange={(e) => setAssignForm((f) => ({ ...f, membership_plan_id: e.target.value }))}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm">
                  <option value="">Select plan</option>
                  {plans.map((p) => <option key={p.id} value={p.id}>{p.name} — ₹{p.price}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Start Date *</label>
                <input type="date" required value={assignForm.start_date} onChange={(e) => setAssignForm((f) => ({ ...f, start_date: e.target.value }))}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowAssignModal(false)} className="flex-1 py-2.5 rounded-lg border border-[#2A2A2A] text-sm text-[#9B968C]">Cancel</button>
                <button type="submit" disabled={actionLoading === "assign"} className="flex-1 py-2.5 rounded-lg bg-[#D4A84F] text-black font-medium text-sm disabled:opacity-50">
                  {actionLoading === "assign" ? "Assigning…" : "Assign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

