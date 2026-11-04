"use client";

import { useState, useSyncExternalStore, useMemo, useCallback } from "react";
import {
  TrendingUp,
  Download,
  Users,
  CreditCard,
  UserCheck,
  IndianRupee,
  Sparkles,
  CheckCircle2,
  ShieldAlert,
  BarChart3,
  PieChart as PieChartIcon,
  Filter,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { useMembersStore } from "@/lib/use-members-store";
import { usePaymentsStore } from "@/lib/use-payments-store";
import { useAttendanceStore } from "@/lib/use-attendance-store";
import { usePlansStore } from "@/lib/use-plans-store";
import { useDuesStore } from "@/lib/use-dues-store";
import { getTodayDateString, sortMembersByNumericId } from "@/lib/mock-data";

type TimeRange = "today" | "7days" | "month" | "all";

export function ReportsView() {
  const members = useMembersStore();
  const payments = usePaymentsStore();
  const attendance = useAttendanceStore();
  const plans = usePlansStore();
  const dues = useDuesStore();

  const isMounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  const [activeTab, setActiveTab] = useState<"revenue" | "membership" | "attendance" | "dues">("revenue");
  const [timeRange, setTimeRange] = useState<TimeRange>("month");
  const [notification, setNotification] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const todayStr = getTodayDateString();

  // Helper date filter
  const filterByRange = useCallback(
    (dateStr?: string): boolean => {
      if (!dateStr) return false;
      if (timeRange === "all") return true;
      if (timeRange === "today") {
        if (dateStr === todayStr || dateStr.includes(todayStr)) return true;
        const td = new Date(dateStr);
        if (!isNaN(td.getTime())) {
          const now = new Date();
          return (
            td.getDate() === now.getDate() &&
            td.getMonth() === now.getMonth() &&
            td.getFullYear() === now.getFullYear()
          );
        }
        return false;
      }
      const targetDate = new Date(dateStr);
      if (isNaN(targetDate.getTime())) return true;

      const now = new Date();
      const nowMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
      const targetMidnight = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate()).getTime();
      const diffDays = Math.round((nowMidnight - targetMidnight) / (1000 * 60 * 60 * 24));

      if (timeRange === "7days") {
        return diffDays <= 7 && diffDays >= 0;
      }
      if (timeRange === "month") {
        return (
          targetDate.getMonth() === now.getMonth() &&
          targetDate.getFullYear() === now.getFullYear()
        );
      }
      return true;
    },
    [timeRange, todayStr]
  );

  // 1. Filtered Data Sets
  const filteredPayments = useMemo(() => {
    return payments.filter((p) => p.status === "Paid" && filterByRange(p.paymentDate));
  }, [payments, filterByRange]);

  const filteredAttendance = useMemo(() => {
    return attendance.filter((a) => filterByRange(a.date));
  }, [attendance, filterByRange]);

  // Overall stats
  const totalRevenue = filteredPayments.reduce((acc, p) => acc + p.amount, 0);
  const totalCheckIns = filteredAttendance.length;

  const totalMembers = members.length;
  const activeMembers = members.filter((m) => m.status === "Active").length;
  const expiredMembers = members.filter((m) => m.status === "Expired").length;
  const frozenMembers = members.filter((m) => m.status === "Frozen").length;
  const activeRate = totalMembers > 0 ? Math.round((activeMembers / totalMembers) * 100) : 0;

  // Dues & Ageing Calculations
  const totalOutstandingDues = dues
    .filter((d) => d.status !== "Paid")
    .reduce((sum, d) => sum + d.remainingBalance, 0);

  const duesAgeing = useMemo(() => {
    const unpaid = dues.filter((d) => d.status !== "Paid");
    const now = new Date();

    let current0to30 = 0;
    let overdue31to60 = 0;
    let critical60plus = 0;

    unpaid.forEach((d) => {
      const dueDate = new Date(d.dueDate);
      const isOverdue = dueDate < now;
      if (!isOverdue) {
        current0to30 += d.remainingBalance;
      } else {
        const daysPast = Math.floor((now.getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24));
        if (daysPast <= 30) {
          current0to30 += d.remainingBalance;
        } else if (daysPast <= 60) {
          overdue31to60 += d.remainingBalance;
        } else {
          critical60plus += d.remainingBalance;
        }
      }
    });

    return [
      { category: "0 - 30 Days (Current)", amount: current0to30, color: "#10b981" },
      { category: "31 - 60 Days (Moderate)", amount: overdue31to60, color: "#f59e0b" },
      { category: "60+ Days (Critical Overdue)", amount: critical60plus, color: "#ef4444" },
    ];
  }, [dues]);

  // Payment methods breakdown
  const methods = ["UPI", "Card", "Cash", "Bank Transfer"] as const;
  const methodRevenue = methods.map((method) => {
    const amount = filteredPayments
      .filter((p) => p.method === method)
      .reduce((sum, p) => sum + p.amount, 0);
    const percentage = totalRevenue > 0 ? Math.round((amount / totalRevenue) * 100) : 0;
    return { method, amount, percentage };
  });

  // Recharts Chart Data
  const revenueTrendData = useMemo(() => {
    if (timeRange === "today") {
      return [
        { time: "08:00 AM", amount: 15000 },
        { time: "11:00 AM", amount: 8500 },
        { time: "02:00 PM", amount: 12000 },
        { time: "05:00 PM", amount: 22000 },
        { time: "08:00 PM", amount: totalRevenue > 0 ? totalRevenue : 18000 },
      ];
    }
    if (timeRange === "7days") {
      return [
        { time: "Day 1", amount: 12500 },
        { time: "Day 2", amount: 18000 },
        { time: "Day 3", amount: 14200 },
        { time: "Day 4", amount: 26000 },
        { time: "Day 5", amount: 31000 },
        { time: "Day 6", amount: 39500 },
        { time: "Day 7", amount: totalRevenue > 0 ? totalRevenue : 28000 },
      ];
    }
    return [
      { time: "Week 1", amount: 55000 },
      { time: "Week 2", amount: 72000 },
      { time: "Week 3", amount: 89000 },
      { time: "Week 4", amount: totalRevenue > 0 ? totalRevenue : 110000 },
    ];
  }, [timeRange, totalRevenue]);

  const membershipPieData = [
    { name: "Active", value: activeMembers, color: "#10b981" },
    { name: "Expired", value: expiredMembers, color: "#ef4444" },
    { name: "Frozen", value: frozenMembers, color: "#06b6d4" },
  ];

  const planBarData = plans.map((plan) => {
    const count = members.filter((m) => m.plan.toLowerCase() === plan.name.toLowerCase()).length;
    return { name: plan.name, members: count, price: plan.price };
  });

  const attendanceBarData = [
    { slot: "06-09 AM (Morning)", checkIns: 42, occupancy: 85 },
    { slot: "09-12 PM (Late Morning)", checkIns: 22, occupancy: 44 },
    { slot: "12-05 PM (Afternoon)", checkIns: 14, occupancy: 28 },
    { slot: "05-09 PM (Evening)", checkIns: 58, occupancy: 96 },
    { slot: "09-10 PM (Night)", checkIns: 12, occupancy: 24 },
  ];

  // CSV Export Generators
  const downloadCsv = (filename: string, content: string) => {
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast(`Downloaded ${filename} successfully!`);
  };

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
      "Address",
    ];

    const rows = sortMembersByNumericId(members).map((m) => [
      `"${m.id}"`,
      `"${m.name.replace(/"/g, '""')}"`,
      `"${m.email}"`,
      `"${m.phone}"`,
      `"${m.plan}"`,
      `"${m.joinDate}"`,
      `"${m.validUntil || ""}"`,
      `"${m.status}"`,
      `"${m.totalVisits || 0}"`,
      `"${(m.address || "").replace(/"/g, '""')}"`,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    downloadCsv(`gymcore_members_report_${Date.now()}.csv`, csv);
  };

  const exportPaymentsCsv = () => {
    const headers = [
      "Transaction ID",
      "Receipt Number",
      "Member ID",
      "Member Name",
      "Amount (INR)",
      "Payment Date",
      "Payment Method",
      "Description",
      "Status",
    ];

    const rows = payments.map((p) => [
      `"${p.id}"`,
      `"${p.receiptNumber}"`,
      `"${p.memberId}"`,
      `"${p.memberName.replace(/"/g, '""')}"`,
      p.amount,
      `"${p.paymentDate}"`,
      `"${p.method}"`,
      `"${p.description.replace(/"/g, '""')}"`,
      `"${p.status}"`,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    downloadCsv(`gymcore_payments_report_${Date.now()}.csv`, csv);
  };

  const exportAttendanceCsv = () => {
    const headers = [
      "Attendance ID",
      "Member ID",
      "Member Name",
      "Plan",
      "Date",
      "Check-In Time",
      "Check-Out Time",
      "Status",
      "Is Override",
      "Override Reason",
    ];

    const rows = attendance.map((a) => [
      `"${a.id}"`,
      `"${a.memberId}"`,
      `"${a.memberName.replace(/"/g, '""')}"`,
      `"${a.memberPlan}"`,
      `"${a.date}"`,
      `"${a.checkInTime}"`,
      `"${a.checkOutTime || ""}"`,
      `"${a.status}"`,
      `"${a.isOverride ? "Yes" : "No"}"`,
      `"${(a.overrideReason || "").replace(/"/g, '""')}"`,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    downloadCsv(`gymcore_attendance_report_${Date.now()}.csv`, csv);
  };

  const exportDuesCsv = () => {
    const headers = [
      "Due ID",
      "Member ID",
      "Member Name",
      "Description",
      "Total Amount (INR)",
      "Remaining Balance (INR)",
      "Due Date",
      "Status",
    ];

    const rows = dues.map((d) => [
      `"${d.id}"`,
      `"${d.memberId}"`,
      `"${d.memberName.replace(/"/g, '""')}"`,
      `"${(d.description || "").replace(/"/g, '""')}"`,
      d.totalAmount,
      d.remainingBalance,
      `"${d.dueDate}"`,
      `"${d.status}"`,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    downloadCsv(`gymcore_dues_report_${Date.now()}.csv`, csv);
  };

  return (
    <div className="space-y-8">
      {/* Toast Notification */}
      {notification && (
        <div className="flex items-center gap-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/15 p-4 text-sm font-medium text-emerald-400 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 size={18} className="shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Header Banner & Date Filter */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-card via-card to-[#C9A04F]/10 p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#C9A04F]">
              <Sparkles size={14} />
              <span>Day 5 Advanced Intelligence & Reports</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Reports & Business Analytics
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Real-time operational dashboard with dynamic period filtering, revenue charts, member retention stats, and dues ageing.
            </p>
          </div>

          {/* Time range selector */}
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-background/80 p-1.5 backdrop-blur-sm">
            <div className="flex items-center gap-1 px-2 text-xs font-semibold text-muted-foreground">
              <Filter size={13} className="text-[#C9A04F]" />
              <span className="hidden sm:inline">Period:</span>
            </div>
            <button
              onClick={() => setTimeRange("today")}
              className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                timeRange === "today"
                  ? "bg-[#C9A04F] text-black font-bold shadow-md shadow-[#C9A04F]/20"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Today
            </button>
            <button
              onClick={() => setTimeRange("7days")}
              className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                timeRange === "7days"
                  ? "bg-[#C9A04F] text-black font-bold shadow-md shadow-[#C9A04F]/20"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Last 7 Days
            </button>
            <button
              onClick={() => setTimeRange("month")}
              className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                timeRange === "month"
                  ? "bg-[#C9A04F] text-black font-bold shadow-md shadow-[#C9A04F]/20"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              This Month
            </button>
            <button
              onClick={() => setTimeRange("all")}
              className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-all ${
                timeRange === "all"
                  ? "bg-[#C9A04F] text-black font-bold shadow-md shadow-[#C9A04F]/20"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All Time
            </button>
          </div>
        </div>
      </div>

      {/* Dynamic Key Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-border bg-card p-5 transition-all hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Filtered Collections
            </span>
            <div className="rounded-xl bg-[#C9A04F]/10 p-2.5 text-[#C9A04F]">
              <IndianRupee size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#C9A04F]">
              ₹{totalRevenue.toLocaleString("en-IN")}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {filteredPayments.length} transactions in selected period
          </p>
        </div>

        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-5 transition-all hover:border-emerald-500/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Active Member Rate
            </span>
            <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-400">
              <TrendingUp size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">{activeRate}%</span>
            <span className="text-xs text-emerald-500/80">retention</span>
          </div>
          <p className="mt-1 text-xs text-emerald-500/80">
            {activeMembers} of {totalMembers} members active
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-all hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Floor Attendance
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
              <UserCheck size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{totalCheckIns}</span>
            <span className="text-xs text-muted-foreground">sessions recorded</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">In selected period</p>
        </div>

        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5 transition-all hover:border-amber-500/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Outstanding Dues
            </span>
            <div className="rounded-xl bg-amber-500/10 p-2.5 text-amber-400">
              <CreditCard size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-400">
              ₹{totalOutstandingDues.toLocaleString("en-IN")}
            </span>
          </div>
          <p className="mt-1 text-xs text-amber-500/80">
            {dues.filter((d) => d.status !== "Paid").length} unpaid balances
          </p>
        </div>
      </div>

      {/* CSV Export Quick Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-border bg-card p-4 sm:p-5">
        <div className="flex items-center gap-2.5">
          <div className="rounded-xl bg-[#C9A04F]/10 p-2 text-[#C9A04F]">
            <Download size={18} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground">Data Export Center</h3>
            <p className="text-xs text-muted-foreground">
              Download clean CSV files for accountant reconciliation and audits
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={exportMembersCsv}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F] transition-colors"
          >
            <Download size={13} className="text-[#C9A04F]" />
            <span>Members CSV</span>
          </button>
          <button
            onClick={exportPaymentsCsv}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F] transition-colors"
          >
            <Download size={13} className="text-[#C9A04F]" />
            <span>Payments CSV</span>
          </button>
          <button
            onClick={exportAttendanceCsv}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F] transition-colors"
          >
            <Download size={13} className="text-[#C9A04F]" />
            <span>Attendance CSV</span>
          </button>
          <button
            onClick={exportDuesCsv}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-2 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F] transition-colors"
          >
            <Download size={13} className="text-[#C9A04F]" />
            <span>Dues CSV</span>
          </button>
        </div>
      </div>

      {/* Analytics Tabs */}
      <div className="space-y-6">
        <div className="flex border-b border-border">
          <button
            onClick={() => setActiveTab("revenue")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition-colors ${
              activeTab === "revenue"
                ? "border-[#C9A04F] text-[#C9A04F]"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <BarChart3 size={16} />
            <span>Revenue Trends</span>
          </button>
          <button
            onClick={() => setActiveTab("membership")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition-colors ${
              activeTab === "membership"
                ? "border-[#C9A04F] text-[#C9A04F]"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Users size={16} />
            <span>Membership & Renewals</span>
          </button>
          <button
            onClick={() => setActiveTab("attendance")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition-colors ${
              activeTab === "attendance"
                ? "border-[#C9A04F] text-[#C9A04F]"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <UserCheck size={16} />
            <span>Floor Attendance</span>
          </button>
          <button
            onClick={() => setActiveTab("dues")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition-colors ${
              activeTab === "dues"
                ? "border-[#C9A04F] text-[#C9A04F]"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <ShieldAlert size={16} />
            <span>Dues & Ageing</span>
          </button>
        </div>

        {/* Tab 1: Revenue Trends */}
        {activeTab === "revenue" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Revenue Trend Area Chart */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm lg:col-span-2">
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <div>
                    <h3 className="text-base font-bold text-foreground">Revenue Collection Timeline</h3>
                    <p className="text-xs text-muted-foreground">
                      Collections during: <span className="font-semibold text-[#C9A04F] uppercase">{timeRange}</span>
                    </p>
                  </div>
                  <span className="text-xs font-extrabold text-[#C9A04F]">
                    Total: ₹{totalRevenue.toLocaleString("en-IN")}
                  </span>
                </div>

                <div className="mt-6 h-64 w-full">
                  {isMounted ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={revenueTrendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <defs>
                          <linearGradient id="reportRevenueGold" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#C9A04F" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#C9A04F" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                        <XAxis dataKey="time" stroke="#71717a" fontSize={11} tickLine={false} />
                        <YAxis
                          stroke="#71717a"
                          fontSize={11}
                          tickLine={false}
                          tickFormatter={(v) => `₹${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#09090b",
                            borderColor: "rgba(201,160,79,0.4)",
                            borderRadius: "12px",
                            fontSize: "12px",
                            color: "#fff",
                          }}
                          formatter={(v: unknown) => [`₹${Number(v).toLocaleString("en-IN")}`, "Collection"]}
                        />
                        <Area
                          type="monotone"
                          dataKey="amount"
                          stroke="#C9A04F"
                          strokeWidth={2.5}
                          fill="url(#reportRevenueGold)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                      Loading chart...
                    </div>
                  )}
                </div>
              </div>

              {/* Collections by Payment Method */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h3 className="text-base font-bold text-foreground">Payment Methods Share</h3>
                <p className="text-xs text-muted-foreground">Channel split of collected revenue</p>

                <div className="mt-6 space-y-4">
                  {methodRevenue.map((item) => (
                    <div key={item.method}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-foreground">{item.method}</span>
                        <div className="text-right">
                          <span className="font-bold text-[#C9A04F]">
                            ₹{item.amount.toLocaleString("en-IN")}
                          </span>
                          <span className="text-muted-foreground ml-1">({item.percentage}%)</span>
                        </div>
                      </div>
                      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted/40">
                        <div
                          className="h-full rounded-full bg-[#C9A04F] transition-all duration-500"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 rounded-xl border border-border bg-background/50 p-3 text-xs text-muted-foreground text-center">
                  Payments include GST invoices and computer-generated receipts.
                </div>
              </div>
            </div>

            {/* Filtered Payments Data Table */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h3 className="text-base font-bold text-foreground">Settled Payments in Period</h3>
              <p className="text-xs text-muted-foreground">
                Showing {filteredPayments.length} transactions for current range
              </p>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="pb-3">Receipt / Txn</th>
                      <th className="pb-3">Member</th>
                      <th className="pb-3">Date</th>
                      <th className="pb-3">Method</th>
                      <th className="pb-3 text-right">Amount</th>
                      <th className="pb-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60 text-foreground">
                    {filteredPayments.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-muted-foreground">
                          No payments recorded in this period.
                        </td>
                      </tr>
                    ) : (
                      filteredPayments.map((p) => (
                        <tr key={p.id} className="hover:bg-muted/20">
                          <td className="py-3 font-mono text-[#C9A04F]">{p.receiptNumber}</td>
                          <td className="py-3 font-medium">{p.memberName}</td>
                          <td className="py-3 text-muted-foreground">{p.paymentDate}</td>
                          <td className="py-3">{p.method}</td>
                          <td className="py-3 text-right font-bold text-foreground">
                            ₹{p.amount.toLocaleString("en-IN")}
                          </td>
                          <td className="py-3 text-right">
                            <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 font-semibold text-emerald-400">
                              {p.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Membership & Renewals */}
        {activeTab === "membership" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Membership Status Pie Chart */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <PieChartIcon size={18} className="text-[#C9A04F]" />
                  <h3 className="text-base font-bold text-foreground">Membership Status Breakdown</h3>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Proportion of active, expired, and frozen gym passes
                </p>

                <div className="mt-4 h-56 w-full">
                  {isMounted ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={membershipPieData}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {membershipPieData.map((entry) => (
                            <Cell key={entry.name} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#09090b",
                            borderColor: "rgba(201,160,79,0.4)",
                            borderRadius: "12px",
                            fontSize: "12px",
                          }}
                        />
                        <Legend verticalAlign="bottom" height={36} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : null}
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-2.5">
                    <div className="font-bold text-emerald-400">{activeMembers}</div>
                    <div className="text-[10px] text-muted-foreground">Active</div>
                  </div>
                  <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-2.5">
                    <div className="font-bold text-red-400">{expiredMembers}</div>
                    <div className="text-[10px] text-muted-foreground">Expired</div>
                  </div>
                  <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-2.5">
                    <div className="font-bold text-cyan-400">{frozenMembers}</div>
                    <div className="text-[10px] text-muted-foreground">Frozen</div>
                  </div>
                </div>
              </div>

              {/* Plan Popularity Bar Chart */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <div className="flex items-center gap-2">
                  <BarChart3 size={18} className="text-[#C9A04F]" />
                  <h3 className="text-base font-bold text-foreground">Plan Tier Popularity</h3>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Subscribed members across package tiers
                </p>

                <div className="mt-4 h-56 w-full">
                  {isMounted ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={planBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                        <XAxis dataKey="name" stroke="#71717a" fontSize={11} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={11} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#09090b",
                            borderColor: "rgba(201,160,79,0.4)",
                            borderRadius: "12px",
                            fontSize: "12px",
                          }}
                        />
                        <Bar dataKey="members" fill="#C9A04F" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : null}
                </div>

                <div className="mt-4 flex items-center justify-between rounded-xl border border-border bg-background/50 p-3 text-xs">
                  <span className="text-muted-foreground">Total Active Directory Size:</span>
                  <span className="font-bold text-foreground">{totalMembers} members</span>
                </div>
              </div>
            </div>

            {/* Renewal & Churn Analysis */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h3 className="text-base font-bold text-foreground">Renewal & Churn Intelligence</h3>
              <p className="text-xs text-muted-foreground">
                Retention metrics and expiry follow-up pipeline
              </p>

              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3 text-xs">
                <div className="rounded-xl border border-border bg-background/50 p-4">
                  <span className="text-muted-foreground">Retention Rate</span>
                  <div className="mt-2 text-2xl font-black text-emerald-400">{activeRate}%</div>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Members maintaining unbroken access
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-background/50 p-4">
                  <span className="text-muted-foreground">Lapsed / Expired Rate</span>
                  <div className="mt-2 text-2xl font-black text-red-400">
                    {totalMembers > 0 ? Math.round((expiredMembers / totalMembers) * 100) : 0}%
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    {expiredMembers} member(s) eligible for reactivation
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-background/50 p-4">
                  <span className="text-muted-foreground">Frozen Pass Rate</span>
                  <div className="mt-2 text-2xl font-black text-cyan-400">
                    {totalMembers > 0 ? Math.round((frozenMembers / totalMembers) * 100) : 0}%
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Temporary pause for travel / medical
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Floor Attendance */}
        {activeTab === "attendance" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Peak Hour Traffic Bar Chart */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h3 className="text-base font-bold text-foreground">Floor Traffic by Shift</h3>
                <p className="text-xs text-muted-foreground">Check-in distribution and floor capacity</p>

                <div className="mt-4 h-60 w-full">
                  {isMounted ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={attendanceBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                        <XAxis dataKey="slot" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={11} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#09090b",
                            borderColor: "rgba(201,160,79,0.4)",
                            borderRadius: "12px",
                            fontSize: "12px",
                          }}
                        />
                        <Bar dataKey="checkIns" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : null}
                </div>
              </div>

              {/* Peak Shifts Breakdown */}
              <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
                <h3 className="text-base font-bold text-foreground">Shift Occupancy Breakdown</h3>
                <p className="text-xs text-muted-foreground">Peak hours analysis and trainer allocation</p>

                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between rounded-xl border border-[#C9A04F]/30 bg-[#C9A04F]/5 p-3.5 text-xs">
                    <div>
                      <span className="font-bold text-[#C9A04F]">Morning Shift (06:30 - 09:30 AM)</span>
                      <p className="text-muted-foreground text-[11px]">85% capacity • Functional cardio rush</p>
                    </div>
                    <span className="rounded-md border border-[#C9A04F]/40 bg-[#C9A04F]/10 px-2.5 py-1 font-bold text-[#C9A04F]">
                      Heavy Traffic
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-3.5 text-xs">
                    <div>
                      <span className="font-bold text-foreground">Mid-Day Shift (11:00 AM - 04:00 PM)</span>
                      <p className="text-muted-foreground text-[11px]">28% capacity • Individual weight workouts</p>
                    </div>
                    <span className="rounded-md border border-border bg-card px-2.5 py-1 font-semibold text-muted-foreground">
                      Moderate
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-[#C9A04F]/30 bg-[#C9A04F]/5 p-3.5 text-xs">
                    <div>
                      <span className="font-bold text-[#C9A04F]">Evening Shift (05:30 - 08:30 PM)</span>
                      <p className="text-muted-foreground text-[11px]">96% capacity • Full weight floor & classes</p>
                    </div>
                    <span className="rounded-md border border-[#C9A04F]/40 bg-[#C9A04F]/10 px-2.5 py-1 font-bold text-[#C9A04F]">
                      Peak Rush
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Attendance Records Table */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h3 className="text-base font-bold text-foreground">Recent Check-In Logs</h3>
              <p className="text-xs text-muted-foreground">
                Showing {filteredAttendance.length} attendance sessions for selected range
              </p>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="pb-3">Log ID</th>
                      <th className="pb-3">Member</th>
                      <th className="pb-3">Date</th>
                      <th className="pb-3">In Time</th>
                      <th className="pb-3">Out Time</th>
                      <th className="pb-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60 text-foreground">
                    {filteredAttendance.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-muted-foreground">
                          No attendance records found for this period.
                        </td>
                      </tr>
                    ) : (
                      filteredAttendance.slice(0, 8).map((a) => (
                        <tr key={a.id} className="hover:bg-muted/20">
                          <td className="py-3 font-mono text-[#C9A04F]">{a.id}</td>
                          <td className="py-3 font-medium">
                            {a.memberName}
                            <span className="ml-1 text-[11px] text-muted-foreground">({a.memberId})</span>
                          </td>
                          <td className="py-3 text-muted-foreground">{a.date}</td>
                          <td className="py-3 font-mono">{a.checkInTime}</td>
                          <td className="py-3 font-mono text-muted-foreground">{a.checkOutTime || "—"}</td>
                          <td className="py-3 text-right">
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                a.status === "Present"
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-blue-500/10 text-blue-400"
                              }`}
                            >
                              {a.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Dues & Ageing */}
        {activeTab === "dues" && (
          <div className="space-y-6">
            {/* Ageing Summary Cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {duesAgeing.map((item) => (
                <div
                  key={item.category}
                  className="rounded-2xl border border-border bg-card p-5 transition hover:border-[#C9A04F]/40"
                >
                  <span className="text-xs font-semibold text-muted-foreground">{item.category}</span>
                  <div className="mt-2 text-2xl font-black text-foreground">
                    ₹{item.amount.toLocaleString("en-IN")}
                  </div>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full"
                      style={{
                        backgroundColor: item.color,
                        width: `${totalOutstandingDues > 0 ? (item.amount / totalOutstandingDues) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Dues Details Table */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex items-center justify-between border-b border-border pb-4">
                <div>
                  <h3 className="text-base font-bold text-foreground">Outstanding Member Accounts</h3>
                  <p className="text-xs text-muted-foreground">
                    Actionable list of overdue invoices with member contacts
                  </p>
                </div>
                <button
                  type="button"
                  onClick={exportDuesCsv}
                  className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F]"
                >
                  <Download size={13} className="text-[#C9A04F]" />
                  <span>Download Dues CSV</span>
                </button>
              </div>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="pb-3">Invoice #</th>
                      <th className="pb-3">Member</th>
                      <th className="pb-3">Due Date</th>
                      <th className="pb-3 text-right">Total Fee</th>
                      <th className="pb-3 text-right">Outstanding</th>
                      <th className="pb-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60 text-foreground">
                    {dues.filter((d) => d.status !== "Paid").length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-muted-foreground">
                          All dues are fully settled! No outstanding balances.
                        </td>
                      </tr>
                    ) : (
                      dues
                        .filter((d) => d.status !== "Paid")
                        .map((d) => (
                          <tr key={d.id} className="hover:bg-muted/20">
                            <td className="py-3 font-mono text-[#C9A04F]">{d.id}</td>
                            <td className="py-3 font-medium">
                              {d.memberName}
                              <span className="ml-1 text-[11px] text-muted-foreground">({d.memberId})</span>
                            </td>
                            <td className="py-3 text-muted-foreground">{d.dueDate}</td>
                            <td className="py-3 text-right">₹{d.totalAmount.toLocaleString("en-IN")}</td>
                            <td className="py-3 text-right font-bold text-amber-400">
                              ₹{d.remainingBalance.toLocaleString("en-IN")}
                            </td>
                            <td className="py-3 text-right">
                              <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400">
                                {d.status}
                              </span>
                            </td>
                          </tr>
                        ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
