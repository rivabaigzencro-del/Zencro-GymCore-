"use client";

import { useState, useEffect, useMemo } from "react";
import {
  ShieldCheck,
  Search,
  Filter,
  Download,
  AlertTriangle,
  UserCog,
  Activity,
  Calendar,
  Eye,
  X,
  FileText,
  Clock,
  ArrowUpDown,
  Lock,
} from "lucide-react";
import {
  type AuditRecord,
  type AuditEntityType,
  type AuditSeverity,
  generateAuditCsv,
} from "@/lib/audit-trail";
import {
  setActiveSession,
  DEMO_ACCOUNTS,
  isDemoModeEnabled,
} from "@/lib/api-client";
import { useSessionStore } from "@/lib/use-session-store";
import { useAuditStore } from "@/lib/use-audit-store";
import {
  syncAuditLogsFromBackend,
  isBackendConnected,
} from "@/lib/backend-sync";

export function AuditView() {
  const auditLogs = useAuditStore();
  const session = useSessionStore();

  useEffect(() => {
    if (isBackendConnected()) {
      syncAuditLogsFromBackend().catch(() => {});
    }
  }, []);

  // Search & Filter States
  const [searchQuery, setSearchQuery] = useState("");
  const [entityFilter, setEntityFilter] = useState<string>("All");
  const [severityFilter, setSeverityFilter] = useState<string>("All");
  const [dateFilter, setDateFilter] = useState<"all" | "today" | "7days" | "month">("all");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");

  // Selected Log for Details Modal
  const [selectedLog, setSelectedLog] = useState<AuditRecord | null>(null);

  // Compute Metrics
  const totalEvents = auditLogs.length;
  const criticalEvents = auditLogs.filter((l) => l.severity === "critical").length;
  const staffEvents = auditLogs.filter((l) => l.entityType === "Staff").length;
  const memberEvents = auditLogs.filter(
    (l) => l.entityType === "Member" || l.entityType === "Membership" || l.entityType === "Payment"
  ).length;

  // Filtered & Sorted Logs
  const filteredLogs = useMemo(() => {
    const now = new Date();
    const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const sevenDaysAgo = todayMidnight - 7 * 24 * 60 * 60 * 1000;
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).getTime();

    return auditLogs
      .filter((log) => {
        // Category Filter
        if (entityFilter !== "All" && log.entityType !== entityFilter) {
          return false;
        }

        // Severity Filter
        if (severityFilter !== "All" && log.severity !== severityFilter) {
          return false;
        }

        // Date Filter
        if (dateFilter !== "all") {
          const logTime = new Date(log.timestamp).getTime();
          if (dateFilter === "today" && logTime < todayMidnight) return false;
          if (dateFilter === "7days" && logTime < sevenDaysAgo) return false;
          if (dateFilter === "month" && logTime < monthStart) return false;
        }

        // Search Query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const match =
            log.id.toLowerCase().includes(q) ||
            log.actionLabel.toLowerCase().includes(q) ||
            log.action.toLowerCase().includes(q) ||
            log.description.toLowerCase().includes(q) ||
            log.performedBy.toLowerCase().includes(q) ||
            (log.entityId && log.entityId.toLowerCase().includes(q)) ||
            (log.entityName && log.entityName.toLowerCase().includes(q));
          if (!match) return false;
        }

        return true;
      })
      .sort((a, b) => {
        const timeA = new Date(a.timestamp).getTime();
        const timeB = new Date(b.timestamp).getTime();
        return sortOrder === "desc" ? timeB - timeA : timeA - timeB;
      });
  }, [auditLogs, entityFilter, severityFilter, dateFilter, searchQuery, sortOrder]);

  // Export to CSV
  const handleExportCSV = () => {
    const csvContent = generateAuditCsv(filteredLogs);
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `GYMCORE_Audit_Trail_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Helper for Severity Badges
  const renderSeverityBadge = (severity: AuditSeverity) => {
    switch (severity) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[11px] font-bold text-red-400">
            <span className="h-1.5 w-1.5 rounded-full bg-red-400 animate-pulse" />
            CRITICAL
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            WARNING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
            INFO
          </span>
        );
    }
  };

  // Helper for Entity Type Badges
  const renderEntityBadge = (type: AuditEntityType) => {
    switch (type) {
      case "Staff":
        return (
          <span className="rounded-md border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[11px] font-semibold text-blue-400">
            Staff
          </span>
        );
      case "Member":
      case "Membership":
        return (
          <span className="rounded-md border border-[#C9A04F]/40 bg-[#C9A04F]/10 px-2 py-0.5 text-[11px] font-semibold text-[#C9A04F]">
            {type}
          </span>
        );
      case "Payment":
        return (
          <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">
            Payment
          </span>
        );
      case "Attendance":
        return (
          <span className="rounded-md border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[11px] font-semibold text-purple-400">
            Attendance
          </span>
        );
      case "Settings":
      case "System":
        return (
          <span className="rounded-md border border-zinc-500/30 bg-zinc-500/10 px-2 py-0.5 text-[11px] font-semibold text-zinc-300">
            {type}
          </span>
        );
    }
  };

  if (session?.role === "Front Desk") {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-8 sm:p-12 text-center max-w-xl mx-auto shadow-sm">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-500">
            <Lock size={28} />
          </div>
          <h2 className="mt-4 text-xl font-bold text-foreground">Access Restricted</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Front Desk staff have permissions for Member Registration, Membership Assignment, Payment Collection, Receipts, and Attendance Check-in only.
          </p>
          <p className="mt-2 text-xs text-muted-foreground/80">
            Audit logs and compliance monitoring are restricted to Gym Owners and Managers.
          </p>
          {isDemoModeEnabled() && (
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
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-card via-card/95 to-background p-6 lg:p-8 shadow-sm">
        <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-3 py-1 text-xs font-semibold text-[#C9A04F]">
              <Lock size={12} />
              <span>Immutable Regulatory Logs</span>
            </div>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-foreground lg:text-3xl">
              Audit Trail & Governance
            </h1>
            <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
              Comprehensive chronological log of all administrative actions, overrides, and membership lifecycle changes
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3.5 py-2 text-xs font-semibold text-foreground transition-all hover:border-[#C9A04F] hover:text-[#C9A04F]"
              title="Download Compliance CSV"
            >
              <Download size={14} className="text-[#C9A04F]" />
              <span>Export Audit CSV</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Logged Events
            </span>
            <div className="rounded-xl bg-[#C9A04F]/10 p-2.5 text-[#C9A04F]">
              <FileText size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{totalEvents}</span>
            <span className="text-xs text-muted-foreground">records</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">All operational activities</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-red-500/40">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-red-400">
              Critical & Overrides
            </span>
            <div className="rounded-xl bg-red-500/10 p-2.5 text-red-400">
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-red-400">{criticalEvents}</span>
            <span className="text-xs text-red-500/80">admin overrides</span>
          </div>
          <p className="mt-1 text-xs text-red-500/80">Require supervisor review</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-blue-500/40">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">
              Staff Operations
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
              <UserCog size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{staffEvents}</span>
            <span className="text-xs text-blue-400">staff actions</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Additions, updates & status</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-emerald-500/40">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Member & Billing
            </span>
            <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-400">
              <Activity size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{memberEvents}</span>
            <span className="text-xs text-emerald-400">member events</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Enrolment & transactions</p>
        </div>
      </div>

      {/* Main Audit Log Table Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground">Audit Activity Log</h2>
            <p className="text-xs text-muted-foreground">
              Showing {filteredLogs.length} of {totalEvents} recorded actions
            </p>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search Input */}
            <div className="relative min-w-[220px]">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                placeholder="Search action, actor, ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
              />
            </div>

            {/* Category Filter */}
            <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
              <Filter size={13} className="text-muted-foreground" />
              <select
                value={entityFilter}
                onChange={(e) => setEntityFilter(e.target.value)}
                className="bg-transparent text-xs text-foreground focus:outline-none"
              >
                <option value="All" className="bg-card text-foreground">All Categories</option>
                <option value="Member" className="bg-card text-foreground">Member</option>
                <option value="Membership" className="bg-card text-foreground">Membership</option>
                <option value="Payment" className="bg-card text-foreground">Payment</option>
                <option value="Attendance" className="bg-card text-foreground">Attendance</option>
                <option value="Staff" className="bg-card text-foreground">Staff</option>
                <option value="Settings" className="bg-card text-foreground">Settings</option>
              </select>
            </div>

            {/* Severity Filter */}
            <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
              <span className="text-[11px] text-muted-foreground">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-transparent text-xs text-foreground focus:outline-none"
              >
                <option value="All" className="bg-card text-foreground">All</option>
                <option value="info" className="bg-card text-foreground">Info</option>
                <option value="warning" className="bg-card text-foreground">Warning</option>
                <option value="critical" className="bg-card text-foreground">Critical</option>
              </select>
            </div>

            {/* Date Quick Filter Pills */}
            <div className="flex rounded-xl border border-border bg-background p-1 text-xs">
              {(
                [
                  { id: "all", label: "All Time" },
                  { id: "today", label: "Today" },
                  { id: "7days", label: "7 Days" },
                  { id: "month", label: "This Month" },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setDateFilter(tab.id)}
                  className={`rounded-lg px-2.5 py-1 font-medium transition-colors ${
                    dateFilter === tab.id
                      ? "bg-[#C9A04F] text-black font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Sort Toggle */}
            <button
              type="button"
              onClick={() => setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"))}
              className="flex items-center gap-1 rounded-xl border border-border bg-background px-2.5 py-1.5 text-xs text-muted-foreground hover:border-[#C9A04F] hover:text-[#C9A04F]"
              title={`Sorting: ${sortOrder === "desc" ? "Newest First" : "Oldest First"}`}
            >
              <ArrowUpDown size={13} />
              <span>{sortOrder === "desc" ? "Newest" : "Oldest"}</span>
            </button>
          </div>
        </div>

        {/* Audit Table */}
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                <th className="pb-3 pl-2">Audit ID</th>
                <th className="pb-3">Timestamp</th>
                <th className="pb-3">Action & Severity</th>
                <th className="pb-3">Category</th>
                <th className="pb-3">Target Entity</th>
                <th className="pb-3">Performed By</th>
                <th className="pb-3">Description</th>
                <th className="pb-3 pr-2 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <div className="rounded-2xl bg-muted/30 p-3 text-muted-foreground">
                        <ShieldCheck size={28} />
                      </div>
                      <p className="text-sm font-semibold text-foreground">No audit records match your filters</p>
                      <p className="text-xs text-muted-foreground">
                        Try resetting your search query or broadening the date filter
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => {
                  const logDate = new Date(log.timestamp);
                  const formattedDate = logDate.toLocaleDateString("en-GB", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  });
                  const formattedTime = logDate.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                  });

                  return (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className="cursor-pointer transition-colors hover:bg-muted/40"
                    >
                      <td className="py-3.5 pl-2 font-mono text-xs font-semibold text-[#C9A04F]">
                        {log.id}
                      </td>
                      <td className="py-3.5 text-xs text-foreground whitespace-nowrap">
                        <div className="flex items-center gap-1 font-medium">
                          <Calendar size={11} className="text-muted-foreground" />
                          <span>{formattedDate}</span>
                        </div>
                        <div className="flex items-center gap-1 text-[11px] text-muted-foreground mt-0.5 font-mono">
                          <Clock size={10} />
                          <span>{formattedTime}</span>
                        </div>
                      </td>
                      <td className="py-3.5 whitespace-nowrap">
                        <div className="flex flex-col gap-1 items-start">
                          <span className="text-xs font-bold text-foreground">
                            {log.actionLabel}
                          </span>
                          {renderSeverityBadge(log.severity)}
                        </div>
                      </td>
                      <td className="py-3.5 whitespace-nowrap">
                        {renderEntityBadge(log.entityType)}
                      </td>
                      <td className="py-3.5 text-xs">
                        {log.entityId ? (
                          <div>
                            <span className="font-semibold text-foreground">
                              {log.entityName || log.entityId}
                            </span>
                            <span className="ml-1 font-mono text-[11px] text-muted-foreground">
                              ({log.entityId})
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="py-3.5 text-xs font-medium text-foreground whitespace-nowrap">
                        {log.performedBy}
                      </td>
                      <td className="py-3.5 text-xs text-muted-foreground max-w-xs truncate" title={log.description}>
                        {log.description}
                      </td>
                      <td className="py-3.5 pr-2 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedLog(log);
                          }}
                          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-[#C9A04F]/10 hover:text-[#C9A04F]"
                          title="View Audit Details"
                          aria-label={`View audit details for ${log.id}`}
                        >
                          <Eye size={15} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-2xl rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border pb-4">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-[#C9A04F]/10 p-2.5 text-[#C9A04F]">
                  <ShieldCheck size={22} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-foreground">
                      Audit Event Details
                    </h2>
                    <span className="font-mono text-xs font-semibold text-[#C9A04F]">
                      {selectedLog.id}
                    </span>
                    {renderSeverityBadge(selectedLog.severity)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Action performed on {new Date(selectedLog.timestamp).toUTCString()}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="mt-5 space-y-4 text-xs">
              {/* Event Metadata Grid */}
              <div className="grid grid-cols-2 gap-3 rounded-xl border border-border bg-background/50 p-4 sm:grid-cols-4">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Action
                  </span>
                  <p className="mt-0.5 font-bold text-foreground">{selectedLog.actionLabel}</p>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Entity Type
                  </span>
                  <div className="mt-0.5">{renderEntityBadge(selectedLog.entityType)}</div>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Target Reference
                  </span>
                  <p className="mt-0.5 font-semibold text-foreground">
                    {selectedLog.entityName || selectedLog.entityId || "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Actor
                  </span>
                  <p className="mt-0.5 font-medium text-foreground">{selectedLog.performedBy}</p>
                </div>
              </div>

              {/* Event Description */}
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Event Description
                </span>
                <p className="mt-1 rounded-xl border border-border bg-background p-3 text-xs text-foreground leading-relaxed">
                  {selectedLog.description}
                </p>
              </div>

              {/* Diff Viewer (Previous vs Updated Values) */}
              {(selectedLog.previousValue || selectedLog.updatedValue) && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                      Previous State
                    </span>
                    <pre className="mt-1 max-h-48 overflow-y-auto rounded-xl border border-border bg-background p-3 font-mono text-[11px] text-muted-foreground">
                      {selectedLog.previousValue
                        ? JSON.stringify(selectedLog.previousValue, null, 2)
                        : "// Initial state / None"}
                    </pre>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                      Updated State
                    </span>
                    <pre className="mt-1 max-h-48 overflow-y-auto rounded-xl border border-border bg-background p-3 font-mono text-[11px] text-emerald-400">
                      {selectedLog.updatedValue
                        ? JSON.stringify(selectedLog.updatedValue, null, 2)
                        : "// Target removed"}
                    </pre>
                  </div>
                </div>
              )}

              {/* Security & Immutability Notice */}
              <div className="flex items-center gap-2 rounded-xl border border-border/80 bg-muted/20 px-3.5 py-2.5 text-[11px] text-muted-foreground">
                <Lock size={14} className="text-[#C9A04F] shrink-0" />
                <span>
                  <strong>Security Guarantee:</strong> This audit entry is cryptographically tracked and tamper-evident. Ordinary administrative users cannot alter or purge recorded log entries.
                </span>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="rounded-xl border border-border bg-background px-4 py-2 text-xs font-semibold text-foreground transition-all hover:bg-muted"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

