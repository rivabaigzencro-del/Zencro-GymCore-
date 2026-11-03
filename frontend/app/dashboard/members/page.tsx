"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { membersApi, membershipsApi, MemberResponse, MemberStatus, MembershipResponse } from "@/lib/api";
import { formatDate, memberStatusClass, membershipStatusClass } from "@/lib/utils";

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl p-5">
      <p className="text-[#9B968C] text-sm">{label}</p>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
      {sub && <p className="text-[#9B968C] text-xs mt-1">{sub}</p>}
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

export default function MembersPage() {
  const [members, setMembers] = useState<MemberResponse[]>([]);
  const [memberships, setMemberships] = useState<Record<string, MembershipResponse>>({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<MemberStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Stats
  const [stats, setStats] = useState({ active: 0, expired: 0, newThisMonth: 0 });

  const fetchMembers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await membersApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        member_status: (statusFilter as MemberStatus) || undefined,
      });
      setMembers(res.items);
      setTotal(res.total);
      setPages(res.pages);

      // Compute stats from all members (first page stats only — approximate)
      const allRes = await membersApi.list({ page_size: 100 });
      const now = new Date();
      const thisMonth = (m: MemberResponse) => {
        const d = new Date(m.created_at);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
      };
      setStats({
        active: allRes.items.filter((m) => m.status === "ACTIVE").length,
        expired: allRes.items.filter((m) => m.status === "EXPIRED").length,
        newThisMonth: allRes.items.filter(thisMonth).length,
      });

      // Fetch latest memberships for displayed members
      const mRes = await membershipsApi.list({ page_size: 100 });
      const mMap: Record<string, MembershipResponse> = {};
      mRes.items.forEach((m) => {
        if (!mMap[m.member_id] || new Date(m.created_at) > new Date(mMap[m.member_id].created_at)) {
          mMap[m.member_id] = m;
        }
      });
      setMemberships(mMap);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load members");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Members</h1>
          <p className="text-[#9B968C] text-sm mt-0.5">{total} total members</p>
        </div>
        <Link
          href="/dashboard/members/new"
          className="bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-semibold px-5 py-2.5 rounded-lg text-sm transition-colors"
        >
          + Add Member
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Members" value={total} />
        <StatCard label="Active" value={stats.active} />
        <StatCard label="Expired" value={stats.expired} />
        <StatCard label="New This Month" value={stats.newThisMonth} />
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <input
          type="text"
          placeholder="Search by name, email or phone…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="flex-1 bg-[#1D1D1D] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-sm text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as MemberStatus | ""); setPage(1); }}
          className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-lg px-4 py-2.5 text-sm text-white focus:border-[#D4A84F] focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
          <option value="EXPIRED">Expired</option>
          <option value="SUSPENDED">Suspended</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">{error}</div>
      )}

      {/* Table */}
      <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-2 border-[#D4A84F] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : members.length === 0 ? (
          <div className="text-center py-16 text-[#9B968C]">
            <p className="text-4xl mb-3">👥</p>
            <p className="text-lg font-medium">No members found</p>
            <p className="text-sm mt-1">Add your first member to get started</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#2A2A2A] bg-[#151515]">
                  {["Member", "Phone", "Email", "Plan", "Expiry", "Status", "Actions"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-[#9B968C] font-medium text-xs uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {members.map((m, i) => {
                  const ms = memberships[m.id];
                  return (
                    <tr
                      key={m.id}
                      className={`border-b border-[#222] hover:bg-[#242424] transition-colors ${i % 2 === 0 ? "" : "bg-[#1A1A1A]"}`}
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-[#D4A84F]/15 flex items-center justify-center text-[#D4A84F] text-xs font-semibold flex-shrink-0">
                            {m.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-white">{m.full_name}</p>
                            <p className="text-[#9B968C] text-xs">{m.id.slice(0, 8)}…</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-[#9B968C]">{m.phone ?? "—"}</td>
                      <td className="px-5 py-4 text-[#9B968C]">{m.email ?? "—"}</td>
                      <td className="px-5 py-4 text-[#9B968C]">{ms?.membership_plan?.name ?? "—"}</td>
                      <td className="px-5 py-4 text-[#9B968C]">
                        {ms ? formatDate(ms.end_date) : "—"}
                      </td>
                      <td className="px-5 py-4">
                        <Badge status={m.status} classNameFn={memberStatusClass} />
                      </td>
                      <td className="px-5 py-4">
                        <Link
                          href={`/dashboard/members/${m.id}`}
                          className="text-[#D4A84F] hover:text-[#F0C96A] text-xs font-medium transition-colors"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-5">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg bg-[#1D1D1D] border border-[#2A2A2A] text-sm text-white disabled:opacity-40 hover:border-[#D4A84F] transition-colors"
          >
            Previous
          </button>
          <span className="text-[#9B968C] text-sm">
            Page {page} of {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="px-4 py-2 rounded-lg bg-[#1D1D1D] border border-[#2A2A2A] text-sm text-white disabled:opacity-40 hover:border-[#D4A84F] transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

