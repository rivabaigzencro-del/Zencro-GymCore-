"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { membersApi, MemberResponse } from "@/lib/api";

export default function EditMemberPage({ params }: { params: Promise<{ member_id: string }> }) {
  const { member_id } = use(params);
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    gender: "",
    date_of_birth: "",
    address: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    status: "ACTIVE",
  });

  useEffect(() => {
    membersApi.get(member_id).then((m: MemberResponse) => {
      setForm({
        full_name: m.full_name,
        email: m.email ?? "",
        phone: m.phone ?? "",
        gender: m.gender ?? "",
        date_of_birth: m.date_of_birth ?? "",
        address: m.address ?? "",
        emergency_contact_name: m.emergency_contact_name ?? "",
        emergency_contact_phone: m.emergency_contact_phone ?? "",
        status: m.status,
      });
      setLoading(false);
    }).catch(() => { setError("Failed to load member"); setLoading(false); });
  }, [member_id]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await membersApi.update(member_id, {
        full_name: form.full_name,
        email: form.email || undefined,
        phone: form.phone || undefined,
        gender: (form.gender as any) || undefined,
        date_of_birth: form.date_of_birth || undefined,
        address: form.address || undefined,
        emergency_contact_name: form.emergency_contact_name || undefined,
        emergency_contact_phone: form.emergency_contact_phone || undefined,
        status: form.status as any,
      });
      router.push(`/dashboard/members/${member_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center py-16"><div className="w-8 h-8 border-2 border-[#D4A84F] border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <button onClick={() => router.back()} className="text-[#9B968C] hover:text-white text-sm mb-4 transition-colors">← Back</button>
        <h1 className="text-2xl font-bold">Edit Member</h1>
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Personal Information</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm text-[#9B968C] mb-1.5">Full Name *</label>
              <input name="full_name" required value={form.full_name} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Phone</label>
              <input name="phone" value={form.phone} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Email</label>
              <input type="email" name="email" value={form.email} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Gender</label>
              <select name="gender" value={form.gender} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm">
                <option value="">Select gender</option>
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
                <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Date of Birth</label>
              <input type="date" name="date_of_birth" value={form.date_of_birth} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Status</label>
              <select name="status" value={form.status} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm">
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
                <option value="EXPIRED">Expired</option>
                <option value="SUSPENDED">Suspended</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm text-[#9B968C] mb-1.5">Address</label>
              <textarea name="address" value={form.address} onChange={handleChange} rows={2}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm resize-none" />
            </div>
          </div>
        </div>

        <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4 text-[#D4A84F]">Emergency Contact</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Contact Name</label>
              <input name="emergency_contact_name" value={form.emergency_contact_name} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Contact Phone</label>
              <input name="emergency_contact_phone" value={form.emergency_contact_phone} onChange={handleChange}
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-white focus:border-[#D4A84F] focus:outline-none text-sm" />
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button type="button" onClick={() => router.back()} className="flex-1 py-3 rounded-lg border border-[#2A2A2A] text-[#9B968C] hover:text-white text-sm transition-colors">Cancel</button>
          <button type="submit" disabled={saving} className="flex-1 py-3 rounded-lg bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-semibold text-sm transition-colors disabled:opacity-50">
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}

