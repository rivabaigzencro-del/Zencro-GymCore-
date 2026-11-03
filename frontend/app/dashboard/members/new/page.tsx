"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { plansApi, membersApi, MembershipPlanResponse, CreateMemberPayload } from "@/lib/api";

export default function NewMemberPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<MembershipPlanResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState<{
    full_name: string;
    email: string;
    phone: string;
    gender: string;
    date_of_birth: string;
    address: string;
    emergency_contact_name: string;
    emergency_contact_phone: string;
    plan_id: string;
    start_date: string;
  }>({
    full_name: "",
    email: "",
    phone: "",
    gender: "",
    date_of_birth: "",
    address: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    plan_id: "",
    start_date: new Date().toISOString().split("T")[0],
  });

  useEffect(() => {
    plansApi.list().then((r) => setPlans(r.items)).catch(() => {});
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const payload: CreateMemberPayload = {
        full_name: form.full_name,
        email: form.email || undefined,
        phone: form.phone || undefined,
        gender: (form.gender as any) || undefined,
        date_of_birth: form.date_of_birth || undefined,
        address: form.address || undefined,
        emergency_contact_name: form.emergency_contact_name || undefined,
        emergency_contact_phone: form.emergency_contact_phone || undefined,
      };

      const member = await membersApi.create(payload);

      // Assign membership if plan selected
      if (form.plan_id) {
        const { membershipsApi } = await import("@/lib/api");
        await membershipsApi.create({
          member_id: member.id,
          membership_plan_id: form.plan_id,
          start_date: form.start_date,
        });
      }

      setSuccess(true);
      setTimeout(() => router.push(`/dashboard/members/${member.id}`), 1000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create member");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <button onClick={() => router.back()} className="text-[#9B968C] hover:text-white text-sm mb-4 transition-colors">
          ← Back
        </button>
        <h1 className="text-2xl font-bold">Add New Member</h1>
        <p className="text-[#9B968C] text-sm mt-0.5">Register a new gym member</p>
      </div>

      {success && (
        <div className="mb-4 p-3 rounded-lg bg-[#D4A84F]/20 border border-[#D4A84F]/40 text-[#D4A84F] text-sm">
          Member created successfully! Redirecting…
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Personal Information */}
        <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Personal Information</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm text-[#9B968C] mb-1.5">Full Name *</label>
              <input
                name="full_name"
                required
                value={form.full_name}
                onChange={handleChange}
                placeholder="John Doe"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Phone</label>
              <input
                name="phone"
                value={form.phone}
                onChange={handleChange}
                placeholder="+91 98765 43210"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Email</label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="john@email.com"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Gender</label>
              <select
                name="gender"
                value={form.gender}
                onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm"
              >
                <option value="">Select gender</option>
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
                <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Date of Birth</label>
              <input
                type="date"
                name="date_of_birth"
                value={form.date_of_birth}
                onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm text-[#9B968C] mb-1.5">Address</label>
              <textarea
                name="address"
                value={form.address}
                onChange={handleChange}
                rows={2}
                placeholder="Residential address"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none text-sm resize-none"
              />
            </div>
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Emergency Contact</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Contact Name</label>
              <input
                name="emergency_contact_name"
                value={form.emergency_contact_name}
                onChange={handleChange}
                placeholder="Emergency contact name"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Contact Phone</label>
              <input
                name="emergency_contact_phone"
                value={form.emergency_contact_phone}
                onChange={handleChange}
                placeholder="+91 98765 43210"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none text-sm"
              />
            </div>
          </div>
        </div>

        {/* Membership */}
        <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Membership (Optional)</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Membership Plan</label>
              <select
                name="plan_id"
                value={form.plan_id}
                onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm"
              >
                <option value="">No plan (assign later)</option>
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — ₹{p.price} / {p.duration} {p.duration_unit}
                  </option>
                ))}
              </select>
            </div>
            {form.plan_id && (
              <div>
                <label className="block text-sm text-[#9B968C] mb-1.5">Start Date</label>
                <input
                  type="date"
                  name="start_date"
                  value={form.start_date}
                  onChange={handleChange}
                  className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm"
                />
              </div>
            )}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex-1 py-3 rounded-lg border border-[#2A2A2A] text-[#9B968C] hover:text-white text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-3 rounded-lg bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-semibold text-sm transition-colors disabled:opacity-50"
          >
            {loading ? "Creating…" : "Create Member"}
          </button>
        </div>
      </form>
    </div>
  );
}

