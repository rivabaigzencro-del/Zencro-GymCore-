"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import {
  Users,
  Dumbbell,
  CalendarCheck,
  Wallet,
  TrendingUp,
  UserPlus,
  CreditCard,
  AlertCircle,
  ChevronRight,
  Sparkles,
  ArrowUpRight,
  Activity,
  Flame,
  Calendar,
  IndianRupee,
  Clock,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useMembersStore } from "@/lib/use-members-store";
import { useAttendanceStore } from "@/lib/use-attendance-store";
import { usePaymentsStore } from "@/lib/use-payments-store";
import { useDuesStore } from "@/lib/use-dues-store";
import { getTodayDateString } from "@/lib/mock-data";
import {
  syncMembersFromBackend,
  syncAttendanceFromBackend,
  syncPaymentsFromBackend,
  syncDuesFromBackend,
  isBackendConnected,
} from "@/lib/backend-sync";

export function DashboardOverview() {
  const members = useMembersStore();
  const attendance = useAttendanceStore();
  const payments = usePaymentsStore();
  const dues = useDuesStore();

  useEffect(() => {
    if (isBackendConnected()) {
      Promise.allSettled([
        syncMembersFromBackend(),
        syncAttendanceFromBackend(),
        syncPaymentsFromBackend(),
        syncDuesFromBackend(),
      ]).catch(() => {});
    }
  }, []);

  const isMounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const [chartView, setChartView] = useState<"daily" | "monthly">("daily");

  const todayStr = getTodayDateString();

  // Helper to check if a date string matches today across both formats ("04 Nov 2026" and ISO "2026-11-04")
  const isDateToday = (dateStr?: string): boolean => {
    if (!dateStr) return false;
    if (dateStr === todayStr || dateStr.includes(todayStr)) return true;
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return false;
    const now = new Date();
    return (
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear()
    );
  };

  // 1. KPI Calculations
  const totalMembers = members.length;
  const activeMembers = members.filter((m) => m.status === "Active").length;

  const todayPayments = payments.filter(
    (p) => isDateToday(p.paymentDate) && p.status === "Paid"
  );
  const todayCollection = todayPayments.reduce((sum, p) => sum + p.amount, 0);

  const pendingDuesTotal = dues
    .filter((d) => d.status !== "Paid")
    .reduce((sum, d) => sum + d.remainingBalance, 0);

  const todayAttendance = attendance.filter((a) => isDateToday(a.date));
  const currentlyPresent = todayAttendance.filter((a) => a.status === "Present");

  // Calculate days until expiry for members
  const now = new Date();
  const nowMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const membersWithExpiry = members
    .filter((m) => m.validUntil)
    .map((m) => {
      const expDate = new Date(m.validUntil || "");
      const isDateValid = !isNaN(expDate.getTime());
      if (!isDateValid) return { ...m, daysUntil: null, expDateObj: null };
      const expMidnight = new Date(expDate.getFullYear(), expDate.getMonth(), expDate.getDate());
      const diffDays = Math.ceil(
        (expMidnight.getTime() - nowMidnight.getTime()) / (1000 * 60 * 60 * 24)
      );
      return { ...m, daysUntil: diffDays, expDateObj: expDate };
    });

  const expiringThisWeek = membersWithExpiry.filter(
    (m) => m.daysUntil !== null && m.daysUntil >= 0 && m.daysUntil <= 7 && m.status === "Active"
  );

  const upcomingRenewals = membersWithExpiry
    .filter((m) => m.daysUntil !== null && m.daysUntil >= 0 && m.daysUntil <= 14)
    .sort((a, b) => (a.daysUntil ?? 999) - (b.daysUntil ?? 999))
    .slice(0, 5);

  const pendingDuesList = dues
    .filter((d) => d.status !== "Paid")
    .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime())
    .slice(0, 5);

  const recentActivity = attendance.slice(0, 6);

  // Revenue Chart Trends
  const currentDayIndex = new Date().getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat
  const currentDayName = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][currentDayIndex];

  const baseDailyData = [
    { name: "Mon", revenue: 14500, checkIns: 32 },
    { name: "Tue", revenue: 18200, checkIns: 41 },
    { name: "Wed", revenue: 12000, checkIns: 29 },
    { name: "Thu", revenue: 24800, checkIns: 48 },
    { name: "Fri", revenue: 31500, checkIns: 56 },
    { name: "Sat", revenue: 42000, checkIns: 68 },
    { name: "Sun", revenue: 28500, checkIns: 38 },
  ];

  const dailyChartData = baseDailyData.map((d) => {
    if (d.name === currentDayName) {
      return {
        ...d,
        revenue: todayCollection > 0 ? todayCollection : d.revenue,
        checkIns: todayAttendance.length > 0 ? todayAttendance.length : d.checkIns,
      };
    }
    return d;
  });

  const monthlyChartData = [
    { name: "Jun", revenue: 210000 },
    { name: "Jul", revenue: 245000 },
    { name: "Aug", revenue: 268000 },
    { name: "Sep", revenue: 295000 },
    { name: "Oct", revenue: 340000 },
    { name: "Nov", revenue: 385000 },
  ];

  const activeChartData = chartView === "daily" ? dailyChartData : monthlyChartData;

  const kpis = [
    {
      title: "Today's Collection",
      value: `₹${todayCollection.toLocaleString("en-IN")}`,
      subtitle: `${todayPayments.length} transactions today`,
      icon: IndianRupee,
      color: "text-[#C9A04F]",
      bgColor: "bg-[#C9A04F]/10",
      borderColor: "border-[#C9A04F]/30",
    },
    {
      title: "Active Members",
      value: activeMembers.toLocaleString(),
      subtitle: `${totalMembers > 0 ? Math.round((activeMembers / totalMembers) * 100) : 0}% retention rate`,
      icon: Dumbbell,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/20",
    },
    {
      title: "Pending Dues",
      value: `₹${pendingDuesTotal.toLocaleString("en-IN")}`,
      subtitle: `${dues.filter((d) => d.status !== "Paid").length} unpaid balances`,
      icon: Wallet,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/20",
    },
    {
      title: "Expiring This Week",
      value: expiringThisWeek.length.toLocaleString(),
      subtitle: "Requires renewal follow-up",
      icon: AlertCircle,
      color: "text-rose-400",
      bgColor: "bg-rose-500/10",
      borderColor: "border-rose-500/20",
    },
    {
      title: "Today's Check-ins",
      value: todayAttendance.length.toLocaleString(),
      subtitle: `${currentlyPresent.length} currently on floor`,
      icon: CalendarCheck,
      color: "text-blue-400",
      bgColor: "bg-blue-500/10",
      borderColor: "border-blue-500/20",
    },
    {
      title: "Total Members",
      value: totalMembers.toLocaleString(),
      subtitle: "Registered in gym registry",
      icon: Users,
      color: "text-purple-400",
      bgColor: "bg-purple-500/10",
      borderColor: "border-purple-500/20",
    },
  ];

  const quickActions = [
    {
      label: "Add Member",
      description: "Register new gym member",
      href: "/members",
      icon: UserPlus,
      primary: true,
    },
    {
      label: "QR Attendance",
      description: "Check in members on floor",
      href: "/attendance",
      icon: CalendarCheck,
      primary: false,
    },
    {
      label: "Record Payment",
      description: "Collect fees or settle dues",
      href: "/payments",
      icon: CreditCard,
      primary: false,
    },
    {
      label: "Membership Plans",
      description: "Manage packages & pricing",
      href: "/memberships",
      icon: Sparkles,
      primary: false,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-card via-card to-[#C9A04F]/10 p-6 sm:p-8">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-[#C9A04F]/15 px-3 py-1 text-xs font-semibold text-[#C9A04F]">
            <Flame size={14} />
            <span>GYMCORE OPERATIONS SUITE</span>
          </div>

          <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            Welcome back, Gym Administrator
          </h1>

          <p className="mt-2 text-sm text-muted-foreground">
            Live overview of membership activity, floor occupancy, today&apos;s collections, and pending dues.
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5 font-medium text-foreground">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Floor Status: Open
            </span>
            <span>•</span>
            <span>Today: {todayStr}</span>
            <span>•</span>
            <span>Live Floor Occupancy: {currentlyPresent.length} member(s)</span>
          </div>
        </div>
      </div>

      {/* 6 Dynamic KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.title}
              className={`rounded-2xl border ${kpi.borderColor} bg-card p-4 transition-all duration-200 hover:border-[#C9A04F]/50 hover:shadow-lg`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground truncate">
                  {kpi.title}
                </span>
                <div className={`rounded-xl ${kpi.bgColor} p-2 ${kpi.color}`}>
                  <Icon size={16} />
                </div>
              </div>

              <div className="mt-3">
                <p className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
                  {kpi.value}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground truncate">
                  {kpi.subtitle}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Action Shortcuts */}
      <div>
        <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Quick Operational Shortcuts
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <Link
                key={action.label}
                href={action.href}
                className={`flex items-center justify-between rounded-2xl p-4 transition-all duration-200 ${
                  action.primary
                    ? "bg-[#C9A04F] text-black font-semibold hover:bg-[#b68d3e] shadow-lg shadow-[#C9A04F]/15"
                    : "border border-border bg-card text-foreground hover:border-[#C9A04F]/40 hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                      action.primary ? "bg-black/10" : "bg-[#C9A04F]/10 text-[#C9A04F]"
                    }`}
                  >
                    <Icon size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-bold">{action.label}</p>
                    <p className={`text-[11px] ${action.primary ? "text-black/75" : "text-muted-foreground"}`}>
                      {action.description}
                    </p>
                  </div>
                </div>
                <ChevronRight size={16} className="opacity-60" />
              </Link>
            );
          })}
        </div>
      </div>

      {/* Revenue Trend Chart & Upcoming Renewals */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Revenue Trend Chart (2 Cols) */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm lg:col-span-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
            <div>
              <div className="flex items-center gap-2">
                <TrendingUp size={18} className="text-[#C9A04F]" />
                <h2 className="text-base font-bold text-foreground">Revenue Collection Trends</h2>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Financial performance and daily collection volume
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex rounded-xl border border-border bg-background p-1 text-xs">
                <button
                  type="button"
                  onClick={() => setChartView("daily")}
                  className={`rounded-lg px-2.5 py-1 font-medium transition-colors ${
                    chartView === "daily"
                      ? "bg-[#C9A04F] text-black font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  This Week
                </button>
                <button
                  type="button"
                  onClick={() => setChartView("monthly")}
                  className={`rounded-lg px-2.5 py-1 font-medium transition-colors ${
                    chartView === "monthly"
                      ? "bg-[#C9A04F] text-black font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  6 Months
                </button>
              </div>

              <Link
                href="/reports"
                className="inline-flex items-center gap-1 rounded-xl border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F]"
              >
                <span>Analytics</span>
                <ArrowUpRight size={13} />
              </Link>
            </div>
          </div>

          {/* Recharts Area Chart */}
          <div className="mt-6 h-64 w-full">
            {isMounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activeChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gymcoreGoldGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#C9A04F" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#C9A04F" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                  <XAxis
                    dataKey="name"
                    stroke="#71717a"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: "#27272a" }}
                  />
                  <YAxis
                    stroke="#71717a"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `₹${val >= 1000 ? `${Math.round(val / 1000)}k` : val}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#09090b",
                      borderColor: "rgba(201, 160, 79, 0.4)",
                      borderRadius: "12px",
                      fontSize: "12px",
                      color: "#f4f4f5",
                      boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)",
                    }}
                    formatter={(value: unknown) => [
                      `₹${Number(value).toLocaleString("en-IN")}`,
                      "Revenue",
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#C9A04F"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#gymcoreGoldGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                Loading revenue trend visualizer...
              </div>
            )}
          </div>
        </div>

        {/* Upcoming Membership Renewals (1 Col) */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <Calendar size={18} className="text-[#C9A04F]" />
              <h2 className="text-base font-bold text-foreground">Upcoming Renewals</h2>
            </div>
            <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-bold text-amber-400">
              {upcomingRenewals.length} Due Soon
            </span>
          </div>

          <div className="mt-4 divide-y divide-border/60">
            {upcomingRenewals.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle2 size={28} className="mx-auto text-emerald-400 opacity-60 mb-2" />
                <p className="text-xs font-semibold text-foreground">No upcoming expiries</p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  All active memberships are valid beyond 14 days.
                </p>
              </div>
            ) : (
              upcomingRenewals.map((m) => (
                <div key={m.id} className="flex items-center justify-between py-3 transition hover:bg-muted/20 px-1 rounded-lg">
                  <div>
                    <Link
                      href={`/members/${m.id}`}
                      className="text-xs font-bold text-foreground hover:text-[#C9A04F] transition-colors"
                    >
                      {m.name}
                    </Link>
                    <div className="text-[11px] text-muted-foreground">
                      {m.id} • {m.plan} Plan
                    </div>
                  </div>

                  <div className="text-right">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold ${
                        (m.daysUntil ?? 0) <= 3
                          ? "border border-red-500/30 bg-red-500/10 text-red-400"
                          : "border border-amber-500/30 bg-amber-500/10 text-amber-300"
                      }`}
                    >
                      {m.daysUntil === 0
                        ? "Expires Today"
                        : m.daysUntil === 1
                        ? "Expires Tomorrow"
                        : `${m.daysUntil} days left`}
                    </span>
                    <div className="text-[10px] text-muted-foreground mt-0.5">
                      {m.validUntil}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-4 border-t border-border pt-3">
            <Link
              href="/members"
              className="flex items-center justify-center gap-1.5 text-xs font-semibold text-[#C9A04F] hover:underline"
            >
              <span>View All Expiring Members</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </div>

      {/* Due Payments & Recent Activity Feed */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Due Payments Card */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <Wallet size={18} className="text-amber-400" />
              <div>
                <h2 className="text-base font-bold text-foreground">Outstanding Fee Dues</h2>
                <p className="text-xs text-muted-foreground">
                  Uncollected balances across member accounts
                </p>
              </div>
            </div>
            <Link
              href="/payments"
              className="inline-flex items-center gap-1 text-xs font-semibold text-[#C9A04F] hover:underline"
            >
              <span>Manage Dues</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>

          <div className="mt-4 divide-y divide-border/60">
            {pendingDuesList.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle2 size={28} className="mx-auto text-emerald-400 opacity-60 mb-2" />
                <p className="text-xs font-semibold text-foreground">All Dues Cleared</p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  There are no outstanding member dues in the system.
                </p>
              </div>
            ) : (
              pendingDuesList.map((due) => (
                <div key={due.id} className="flex items-center justify-between py-3 transition hover:bg-muted/20 px-1 rounded-lg">
                  <div>
                    <div className="text-xs font-bold text-foreground">{due.memberName}</div>
                    <div className="text-[11px] text-muted-foreground">
                      Due: {due.dueDate} • Inv #{due.id}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-xs font-bold text-amber-400">
                        ₹{due.remainingBalance.toLocaleString("en-IN")}
                      </div>
                      <span className="text-[10px] uppercase font-semibold text-muted-foreground">
                        {due.status}
                      </span>
                    </div>

                    <Link
                      href="/payments"
                      className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs font-semibold text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F]"
                    >
                      Collect
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Real-Time Gym Floor Activity */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-[#C9A04F]" />
              <div>
                <h2 className="text-base font-bold text-foreground">Recent Gym Activity</h2>
                <p className="text-xs text-muted-foreground">
                  Real-time floor check-ins and session check-outs
                </p>
              </div>
            </div>
            <Link
              href="/attendance"
              className="inline-flex items-center gap-1 text-xs font-semibold text-[#C9A04F] hover:underline"
            >
              <span>Live Attendance</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>

          <div className="mt-4 divide-y divide-border/60">
            {recentActivity.length === 0 ? (
              <div className="py-8 text-center">
                <Clock size={28} className="mx-auto text-muted-foreground opacity-50 mb-2" />
                <p className="text-xs font-semibold text-foreground">No recent check-ins</p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Start scanning or searching members to log floor sessions.
                </p>
              </div>
            ) : (
              recentActivity.map((rec) => (
                <div key={rec.id} className="flex items-center justify-between py-2.5 transition hover:bg-muted/20 px-1 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-xl text-xs font-bold ${
                        rec.status === "Present"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-blue-500/10 text-blue-400"
                      }`}
                    >
                      {rec.memberName.charAt(0)}
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-foreground">{rec.memberName}</span>
                        {rec.isOverride && (
                          <span className="rounded bg-amber-500/15 px-1 py-0.2 text-[9px] font-bold text-amber-300">
                            Override
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {rec.memberId} • In: {rec.checkInTime}
                        {rec.checkOutTime && ` • Out: ${rec.checkOutTime}`}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      rec.status === "Present"
                        ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : "border border-blue-500/30 bg-blue-500/10 text-blue-400"
                    }`}
                  >
                    {rec.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
