"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  CreditCard,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Receipt,
  Printer,
  X,
  IndianRupee,
  Clock,
  Sparkles,
  AlertTriangle,
  History,
  Check,
  TrendingDown,
} from "lucide-react";
import {
  type PaymentRecord,
  type PaymentMethod,
  type PaymentStatus,
  type DueItem,
  type DueStatus,
  type AgeingCategory,
  recordPayment,
  collectDuePayment,
  getDaysOverdue,
  getAgeingCategory,
  sortMembersByNumericId,
} from "@/lib/mock-data";
import { usePaymentsStore } from "@/lib/use-payments-store";
import { useMembersStore } from "@/lib/use-members-store";
import { useDuesStore } from "@/lib/use-dues-store";
import {
  syncPaymentsFromBackend,
  syncDuesFromBackend,
  recordPaymentOnBackend,
  isBackendConnected,
} from "@/lib/backend-sync";

export function PaymentsView() {
  const payments = usePaymentsStore();
  const members = useMembersStore();
  const dues = useDuesStore();

  useEffect(() => {
    if (isBackendConnected()) {
      Promise.allSettled([
        syncPaymentsFromBackend(),
        syncDuesFromBackend(),
      ]).catch(() => {});
    }
  }, []);

  // Active Tab: "dues" or "transactions"
  const [activeTab, setActiveTab] = useState<"dues" | "transactions">("dues");

  // Dues Search & Filters
  const [duesSearchQuery, setDuesSearchQuery] = useState("");
  const [duesStatusFilter, setDuesStatusFilter] = useState<string>("All");
  const [duesAgeingFilter, setDuesAgeingFilter] = useState<AgeingCategory>("All");
  const [duesSortBy, setDuesSortBy] = useState<"dueDate" | "amount" | "overdue">("overdue");

  // Transactions Search & Filters
  const [txnSearchQuery, setTxnSearchQuery] = useState("");
  const [txnMethodFilter, setTxnMethodFilter] = useState<string>("All");
  const [txnStatusFilter, setTxnStatusFilter] = useState<string>("All");

  // Modals state
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [receiptRecord, setReceiptRecord] = useState<PaymentRecord | null>(null);
  const [collectingDue, setCollectingDue] = useState<DueItem | null>(null);
  const [viewingDueDetails, setViewingDueDetails] = useState<DueItem | null>(null);

  // Partial / Full Collect Due Form state
  const [collectAmount, setCollectAmount] = useState<number>(0);
  const [collectMethod, setCollectMethod] = useState<PaymentMethod>("UPI");
  const [collectReference, setCollectReference] = useState("");
  const [collectNote, setCollectNote] = useState("");
  const [collectError, setCollectError] = useState("");

  // Direct Record Payment Form state
  const [formMemberId, setFormMemberId] = useState("");
  const [formAmount, setFormAmount] = useState<number>(3999);
  const [formMethod, setFormMethod] = useState<PaymentMethod>("UPI");
  const [formDescription, setFormDescription] = useState("Standard 3-Month Membership Fee");
  const [formReference, setFormReference] = useState("");
  const [formStatus, setFormStatus] = useState<PaymentStatus>("Paid");
  const [formErrors, setFormErrors] = useState<{
    memberId?: string;
    amount?: string;
    description?: string;
  }>({});

  // Toast Notification
  const [notification, setNotification] = useState<{
    type: "success" | "error" | "warning";
    message: string;
  } | null>(null);

  const showNotification = (message: string, type: "success" | "error" | "warning" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  // Compute Overall Stats
  const totalRevenue = payments
    .filter((p) => p.status === "Paid")
    .reduce((sum, p) => sum + p.amount, 0);

  const totalOutstandingAmount = dues
    .filter((d) => d.status !== "Paid")
    .reduce((sum, d) => sum + d.remainingBalance, 0);

  const membersWithPendingDuesCount = new Set(
    dues.filter((d) => d.status !== "Paid" && d.remainingBalance > 0).map((d) => d.memberId.toLowerCase())
  ).size;

  const overduePaymentsCount = dues.filter(
    (d) => d.status !== "Paid" && getDaysOverdue(d.dueDate) > 0
  ).length;

  const totalDuesCollected = dues.reduce((sum, d) => sum + d.amountPaid, 0);

  // Compute Ageing Breakdown Counts & Amounts
  const ageingBreakdown: Record<AgeingCategory, { count: number; amount: number }> = {
    All: { count: dues.length, amount: totalOutstandingAmount },
    "Not Yet Due": { count: 0, amount: 0 },
    "1-7 Days Overdue": { count: 0, amount: 0 },
    "8-30 Days Overdue": { count: 0, amount: 0 },
    "31-60 Days Overdue": { count: 0, amount: 0 },
    "More Than 60 Days Overdue": { count: 0, amount: 0 },
  };

  dues.forEach((d) => {
    if (d.status !== "Paid") {
      const cat = getAgeingCategory(d.dueDate, d.status);
      ageingBreakdown[cat].count += 1;
      ageingBreakdown[cat].amount += d.remainingBalance;
    }
  });

  // Open Collect Modal for a specific due
  const openCollectModal = (due: DueItem) => {
    setCollectingDue(due);
    setCollectAmount(due.remainingBalance);
    setCollectMethod("UPI");
    setCollectReference("");
    setCollectNote("Settlement for " + due.description);
    setCollectError("");
  };

  // Submit Collect Due Payment (Partial or Full)
  const handleCollectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!collectingDue) return;

    if (!collectAmount || collectAmount <= 0) {
      setCollectError("Please enter a valid amount greater than ₹0.");
      return;
    }

    if (collectAmount > collectingDue.remainingBalance) {
      setCollectError(
        `Amount cannot exceed the remaining balance of ₹${collectingDue.remainingBalance.toLocaleString("en-IN")}.`
      );
      return;
    }

    const res = collectDuePayment({
      dueId: collectingDue.id,
      amount: Number(collectAmount),
      method: collectMethod,
      reference: collectReference.trim() || undefined,
      note: collectNote.trim() || undefined,
    });

    if (res.success && res.payment) {
      showNotification(res.message, "success");
      setCollectingDue(null);
      // Offer receipt preview
      setReceiptRecord(res.payment);
    } else {
      showNotification(res.message || "Failed to collect payment", "error");
    }
  };

  // Submit Direct Payment Record
  const handleRecordPayment = (e: React.FormEvent) => {
    e.preventDefault();
    const errors: typeof formErrors = {};

    if (!formMemberId) {
      errors.memberId = "Please select a member.";
    }
    if (!formAmount || formAmount <= 0) {
      errors.amount = "Please enter a valid amount greater than ₹0.";
    }
    if (!formDescription.trim()) {
      errors.description = "Please enter a description for this transaction.";
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    const res = recordPayment({
      memberId: formMemberId,
      amount: Number(formAmount),
      method: formMethod,
      description: formDescription.trim(),
      reference: formReference.trim() || undefined,
      status: formStatus,
    });

    if (res.success && res.payment) {
      if (isBackendConnected()) {
        recordPaymentOnBackend({
          memberId: formMemberId,
          amount: Number(formAmount),
          method: formMethod,
          notes: formDescription.trim(),
        }).catch(() => {});
      }
      showNotification(res.message, "success");
      setIsRecordModalOpen(false);
      setFormMemberId("");
      setFormAmount(3999);
      setFormDescription("Standard 3-Month Membership Fee");
      setFormReference("");
      setFormStatus("Paid");
      setFormErrors({});
      setReceiptRecord(res.payment);
    } else {
      showNotification(res.message, "error");
    }
  };

  // Filtered Dues
  const filteredDues = dues
    .filter((due) => {
      // Ageing Filter
      if (duesAgeingFilter !== "All") {
        const cat = getAgeingCategory(due.dueDate, due.status);
        if (cat !== duesAgeingFilter) return false;
      }

      // Status Filter
      if (duesStatusFilter !== "All" && due.status !== duesStatusFilter) {
        return false;
      }

      // Search Query
      if (duesSearchQuery.trim()) {
        const q = duesSearchQuery.toLowerCase();
        const match =
          due.memberId.toLowerCase().includes(q) ||
          due.memberName.toLowerCase().includes(q) ||
          due.memberPlan.toLowerCase().includes(q) ||
          due.description.toLowerCase().includes(q) ||
          due.id.toLowerCase().includes(q);
        if (!match) return false;
      }

      return true;
    })
    .sort((a, b) => {
      if (duesSortBy === "overdue") {
        return getDaysOverdue(b.dueDate) - getDaysOverdue(a.dueDate);
      }
      if (duesSortBy === "amount") {
        return b.remainingBalance - a.remainingBalance;
      }
      if (duesSortBy === "dueDate") {
        return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
      }
      return 0;
    });

  // Filtered Payments (Transactions Tab)
  const filteredPayments = payments.filter((payment) => {
    if (txnMethodFilter !== "All" && payment.method !== txnMethodFilter) {
      return false;
    }
    if (txnStatusFilter !== "All" && payment.status !== txnStatusFilter) {
      return false;
    }
    if (txnSearchQuery.trim()) {
      const q = txnSearchQuery.toLowerCase();
      const match =
        payment.id.toLowerCase().includes(q) ||
        payment.receiptNumber.toLowerCase().includes(q) ||
        payment.memberName.toLowerCase().includes(q) ||
        payment.memberId.toLowerCase().includes(q) ||
        payment.description.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const getDueStatusBadge = (status: DueStatus) => {
    switch (status) {
      case "Paid":
        return "border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
      case "Partially Paid":
        return "border-sky-500/20 bg-sky-500/10 text-sky-400";
      case "Overdue":
        return "border-red-500/30 bg-red-500/15 text-red-400";
      case "Pending":
        return "border-amber-500/20 bg-amber-500/10 text-amber-400";
    }
  };

  const getMethodBadge = (method: PaymentMethod) => {
    switch (method) {
      case "UPI":
        return "border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
      case "Card":
        return "border-blue-500/20 bg-blue-500/10 text-blue-400";
      case "Cash":
        return "border-[#C9A04F]/20 bg-[#C9A04F]/10 text-[#C9A04F]";
      case "Bank Transfer":
        return "border-purple-500/20 bg-purple-500/10 text-purple-400";
      default:
        return "border-border bg-card text-foreground";
    }
  };

  return (
    <div className="space-y-8">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`flex items-center gap-2.5 rounded-xl border p-4 text-sm font-medium animate-in fade-in slide-in-from-top-2 ${
            notification.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
              : notification.type === "warning"
              ? "border-amber-500/40 bg-amber-500/15 text-amber-300"
              : "border-red-500/30 bg-red-500/15 text-red-400"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 size={18} className="shrink-0" />
          ) : notification.type === "warning" ? (
            <AlertTriangle size={18} className="shrink-0 text-amber-400" />
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
              <span>Financial Ledger & Billing Operations</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Payments & Outstanding Dues
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Monitor payment ageing buckets, collect partial or full settlements, issue itemized demo
              receipts, and track membership receivables.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setFormErrors({});
                setIsRecordModalOpen(true);
              }}
              className="flex items-center gap-2 rounded-xl bg-[#C9A04F] px-5 py-3 text-sm font-bold text-black transition-all hover:bg-[#b68d3e] shadow-lg shadow-[#C9A04F]/10"
            >
              <Plus size={18} />
              <span>Record Direct Payment</span>
            </button>
          </div>
        </div>
      </div>

      {/* Top Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Revenue Settled
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
          <p className="mt-1 text-xs text-muted-foreground">Paid collections to date</p>
        </div>

        <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-5 transition-colors hover:border-red-500/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-red-400">
              Total Outstanding Dues
            </span>
            <div className="rounded-xl bg-red-500/10 p-2.5 text-red-400">
              <TrendingDown size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-red-400">
              ₹{totalOutstandingAmount.toLocaleString("en-IN")}
            </span>
          </div>
          <p className="mt-1 text-xs text-red-500/80">Pending membership balances</p>
        </div>

        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5 transition-colors hover:border-amber-500/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Members with Dues
            </span>
            <div className="rounded-xl bg-amber-500/10 p-2.5 text-amber-400">
              <Clock size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-400">
              {membersWithPendingDuesCount}
            </span>
            <span className="text-xs text-amber-500/80">accounts pending</span>
          </div>
          <p className="mt-1 text-xs text-amber-500/80">{overduePaymentsCount} invoices overdue</p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Transactions
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
              <Receipt size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{payments.length}</span>
            <span className="text-xs text-muted-foreground">receipts issued</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">₹{totalDuesCollected.toLocaleString("en-IN")} via dues plan</p>
        </div>
      </div>

      {/* Main Tab Switcher */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab("dues")}
          className={`flex items-center gap-2 border-b-2 px-6 py-3.5 text-sm font-semibold transition-colors ${
            activeTab === "dues"
              ? "border-[#C9A04F] text-[#C9A04F]"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Clock size={16} />
          <span>Outstanding Dues & Ageing</span>
          {overduePaymentsCount > 0 && (
            <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[10px] font-bold text-red-400">
              {overduePaymentsCount} Overdue
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("transactions")}
          className={`flex items-center gap-2 border-b-2 px-6 py-3.5 text-sm font-semibold transition-colors ${
            activeTab === "transactions"
              ? "border-[#C9A04F] text-[#C9A04F]"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Receipt size={16} />
          <span>Invoices & Receipts Ledger</span>
          <span className="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
            {payments.length}
          </span>
        </button>
      </div>

      {/* TAB 1: OUTSTANDING DUES & AGEING */}
      {activeTab === "dues" && (
        <div className="space-y-6">
          {/* Ageing Filter Pills Bar (Module 2) */}
          <div className="rounded-2xl border border-border bg-card p-5">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <Clock size={14} className="text-[#C9A04F]" />
                <span>Payment Ageing Categories</span>
              </div>
              <span className="text-xs text-muted-foreground">Click category to filter table</span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
              {(
                [
                  "All",
                  "Not Yet Due",
                  "1-7 Days Overdue",
                  "8-30 Days Overdue",
                  "31-60 Days Overdue",
                  "More Than 60 Days Overdue",
                ] as AgeingCategory[]
              ).map((cat) => {
                const isSelected = duesAgeingFilter === cat;
                const info = ageingBreakdown[cat];

                return (
                  <button
                    key={cat}
                    onClick={() => setDuesAgeingFilter(cat)}
                    className={`rounded-xl border p-3 text-left transition-all ${
                      isSelected
                        ? "border-[#C9A04F] bg-[#C9A04F]/15 shadow-sm"
                        : "border-border bg-background/50 hover:border-[#C9A04F]/40 hover:bg-background"
                    }`}
                  >
                    <div className="text-[11px] font-semibold text-muted-foreground truncate">
                      {cat}
                    </div>
                    <div className="mt-1.5 flex items-baseline justify-between">
                      <span className="text-base font-extrabold text-foreground">{info.count}</span>
                      <span className="text-xs font-bold text-[#C9A04F]">
                        ₹{info.amount.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Dues Table Card */}
          <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">Outstanding Dues Directory</h2>
                <p className="text-xs text-muted-foreground">
                  Individual member balances, due dates, overdue ageing, and collection actions
                </p>
              </div>

              {/* Filters & Sorting */}
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Search */}
                <div className="relative min-w-[200px]">
                  <Search
                    size={15}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />
                  <input
                    type="text"
                    placeholder="Search member, ID, or due..."
                    value={duesSearchQuery}
                    onChange={(e) => setDuesSearchQuery(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>

                {/* Status Filter */}
                <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
                  <Filter size={13} className="text-muted-foreground" />
                  <select
                    value={duesStatusFilter}
                    onChange={(e) => setDuesStatusFilter(e.target.value)}
                    className="bg-transparent text-xs text-foreground focus:outline-none"
                  >
                    <option value="All">All Statuses</option>
                    <option value="Pending">Pending</option>
                    <option value="Partially Paid">Partially Paid</option>
                    <option value="Overdue">Overdue</option>
                    <option value="Paid">Paid / Settled</option>
                  </select>
                </div>

                {/* Sort dropdown */}
                <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
                  <span className="text-muted-foreground">Sort:</span>
                  <select
                    value={duesSortBy}
                    onChange={(e) =>
                      setDuesSortBy(e.target.value as "dueDate" | "amount" | "overdue")
                    }
                    className="bg-transparent text-xs text-foreground focus:outline-none"
                  >
                    <option value="overdue">Days Overdue</option>
                    <option value="amount">Outstanding Amount</option>
                    <option value="dueDate">Due Date</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Dues Table */}
            <div className="mt-6 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="pb-3 pl-2">Member</th>
                    <th className="pb-3">Description</th>
                    <th className="pb-3">Total Due</th>
                    <th className="pb-3">Paid</th>
                    <th className="pb-3">Remaining Balance</th>
                    <th className="pb-3">Due Date</th>
                    <th className="pb-3">Ageing / Overdue</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 pr-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 text-foreground">
                  {filteredDues.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-10 text-center text-xs text-muted-foreground">
                        No outstanding dues match your search and filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredDues.map((due) => {
                      const daysOverdue = getDaysOverdue(due.dueDate);
                      const isOverdue = daysOverdue > 0 && due.status !== "Paid";

                      return (
                        <tr key={due.id} className="transition-colors hover:bg-muted/30">
                          <td className="py-3.5 pl-2">
                            <div>
                              <Link
                                href={`/members/${due.memberId}`}
                                className="font-semibold text-foreground hover:text-[#C9A04F] transition-colors"
                              >
                                {due.memberName}
                              </Link>
                              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                                <span className="font-mono text-[#C9A04F]">{due.memberId}</span>
                                <span>•</span>
                                <span>{due.memberPlan}</span>
                              </div>
                            </div>
                          </td>

                          <td className="py-3.5 text-xs text-muted-foreground max-w-[180px] truncate" title={due.description}>
                            {due.description}
                          </td>

                          <td className="py-3.5 font-semibold text-xs text-foreground">
                            ₹{due.totalAmount.toLocaleString("en-IN")}
                          </td>

                          <td className="py-3.5 text-xs">
                            <span className="text-emerald-400 font-medium">
                              ₹{due.amountPaid.toLocaleString("en-IN")}
                            </span>
                            <div className="mt-1 h-1.5 w-16 overflow-hidden rounded-full bg-muted/50">
                              <div
                                className="h-full rounded-full bg-emerald-500"
                                style={{
                                  width: `${Math.min(
                                    100,
                                    Math.round((due.amountPaid / (due.totalAmount || 1)) * 100)
                                  )}%`,
                                }}
                              />
                            </div>
                          </td>

                          <td className="py-3.5">
                            <span
                              className={`text-sm font-extrabold ${
                                due.remainingBalance === 0
                                  ? "text-emerald-400"
                                  : isOverdue
                                  ? "text-red-400"
                                  : "text-[#C9A04F]"
                              }`}
                            >
                              ₹{due.remainingBalance.toLocaleString("en-IN")}
                            </span>
                          </td>

                          <td className="py-3.5 text-xs text-muted-foreground">
                            {due.dueDate}
                          </td>

                          <td className="py-3.5">
                            {due.status === "Paid" ? (
                              <span className="text-xs text-emerald-400">Settled in Full</span>
                            ) : isOverdue ? (
                              <span className="inline-flex items-center gap-1 rounded-md border border-red-500/30 bg-red-500/15 px-2 py-0.5 text-xs font-bold text-red-400">
                                <AlertTriangle size={11} /> {daysOverdue} Days Overdue
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">Not Yet Due</span>
                            )}
                          </td>

                          <td className="py-3.5">
                            <span
                              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getDueStatusBadge(
                                due.status
                              )}`}
                            >
                              {due.status}
                            </span>
                          </td>

                          <td className="py-3.5 pr-2 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5 flex-nowrap">
                              {due.remainingBalance > 0 ? (
                                <button
                                  onClick={() => openCollectModal(due)}
                                  className="rounded-lg bg-[#C9A04F] px-2.5 py-1 text-xs font-bold text-black transition-all hover:bg-[#b68d3e]"
                                >
                                  Collect
                                </button>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400">
                                  <Check size={14} /> Settled
                                </span>
                              )}
                              <button
                                onClick={() => setViewingDueDetails(due)}
                                className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                                title="View Dues Details"
                              >
                                Details
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: INVOICES & RECEIPTS LEDGER */}
      {activeTab === "transactions" && (
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-foreground">Transaction Logs</h2>
              <p className="text-xs text-muted-foreground">
                Chronological log of all gym membership collections and dues
              </p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="relative min-w-[220px]">
                <Search
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <input
                  type="text"
                  placeholder="Search Txn ID, Member, Receipt..."
                  value={txnSearchQuery}
                  onChange={(e) => setTxnSearchQuery(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                />
              </div>

              <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
                <Filter size={13} className="text-muted-foreground" />
                <select
                  value={txnMethodFilter}
                  onChange={(e) => setTxnMethodFilter(e.target.value)}
                  className="bg-transparent text-xs text-foreground focus:outline-none"
                >
                  <option value="All">All Methods</option>
                  <option value="UPI">UPI</option>
                  <option value="Card">Card</option>
                  <option value="Cash">Cash</option>
                  <option value="Bank Transfer">Bank Transfer</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
                <Filter size={13} className="text-muted-foreground" />
                <select
                  value={txnStatusFilter}
                  onChange={(e) => setTxnStatusFilter(e.target.value)}
                  className="bg-transparent text-xs text-foreground focus:outline-none"
                >
                  <option value="All">All Statuses</option>
                  <option value="Paid">Paid</option>
                  <option value="Pending">Pending</option>
                </select>
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="pb-3 pl-2">Transaction ID</th>
                  <th className="pb-3">Member</th>
                  <th className="pb-3">Description</th>
                  <th className="pb-3">Amount</th>
                  <th className="pb-3">Method</th>
                  <th className="pb-3">Date</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3 pr-2 text-right">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50 text-foreground">
                {filteredPayments.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-10 text-center text-xs text-muted-foreground">
                      No transactions match your search and filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredPayments.map((p) => (
                    <tr key={p.id} className="transition-colors hover:bg-muted/30">
                      <td className="py-3.5 pl-2 font-mono text-xs font-semibold text-foreground">
                        <div>{p.id}</div>
                        <div className="text-[11px] text-muted-foreground">{p.receiptNumber}</div>
                      </td>
                      <td className="py-3.5">
                        <div>
                          <Link
                            href={`/members/${p.memberId}`}
                            className="font-medium hover:text-[#C9A04F] transition-colors"
                          >
                            {p.memberName}
                          </Link>
                          <div className="text-[11px] text-muted-foreground">{p.memberId}</div>
                        </div>
                      </td>
                      <td className="py-3.5 text-xs text-muted-foreground max-w-[200px] truncate">
                        {p.description}
                      </td>
                      <td className="py-3.5 font-bold text-[#C9A04F]">
                        ₹{p.amount.toLocaleString("en-IN")}
                      </td>
                      <td className="py-3.5">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getMethodBadge(
                            p.method
                          )}`}
                        >
                          {p.method}
                        </span>
                      </td>
                      <td className="py-3.5 text-xs text-muted-foreground">{p.paymentDate}</td>
                      <td className="py-3.5">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                            p.status === "Paid"
                              ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                              : "border-amber-500/20 bg-amber-500/10 text-amber-400"
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                      <td className="py-3.5 pr-2 text-right whitespace-nowrap">
                        <button
                          onClick={() => setReceiptRecord(p)}
                          className="inline-flex items-center gap-1 whitespace-nowrap rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground hover:border-[#C9A04F] hover:text-[#C9A04F] transition-colors"
                        >
                          <Receipt size={13} />
                          <span>Receipt</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MODAL 1: COLLECT DUE PAYMENT (PARTIAL OR FULL) */}
      {collectingDue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <button
              onClick={() => setCollectingDue(null)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 border-b border-border pb-4">
              <CreditCard size={20} className="text-[#C9A04F]" />
              <h2 className="text-lg font-bold text-foreground">Collect Outstanding Due</h2>
            </div>

            <form onSubmit={handleCollectSubmit} noValidate className="mt-5 space-y-4">
              {/* Target Due Info */}
              <div className="rounded-xl border border-border bg-background/50 p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Member:</span>
                  <span className="font-bold text-foreground">
                    {collectingDue.memberName} ({collectingDue.memberId})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Dues Description:</span>
                  <span className="font-medium text-foreground">{collectingDue.description}</span>
                </div>
                <div className="flex justify-between border-t border-border/60 pt-2">
                  <span className="text-muted-foreground">Total Fee:</span>
                  <span className="font-semibold text-foreground">₹{collectingDue.totalAmount.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Already Paid:</span>
                  <span className="font-semibold text-emerald-400">₹{collectingDue.amountPaid.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between text-sm font-bold border-t border-border/60 pt-2">
                  <span className="text-foreground">Remaining Balance:</span>
                  <span className="text-[#C9A04F]">₹{collectingDue.remainingBalance.toLocaleString("en-IN")}</span>
                </div>
              </div>

              {/* Quick Amount Options */}
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Quick Amount Presets
                </label>
                <div className="mt-1.5 flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setCollectAmount(collectingDue.remainingBalance);
                      setCollectError("");
                    }}
                    className="flex-1 rounded-lg border border-[#C9A04F] bg-[#C9A04F]/10 py-1.5 text-xs font-bold text-[#C9A04F] hover:bg-[#C9A04F]/20"
                  >
                    Full Balance (₹{collectingDue.remainingBalance.toLocaleString("en-IN")})
                  </button>
                  {collectingDue.remainingBalance > 1000 && (
                    <button
                      type="button"
                      onClick={() => {
                        setCollectAmount(Math.round(collectingDue.remainingBalance / 2));
                        setCollectError("");
                      }}
                      className="flex-1 rounded-lg border border-border bg-background py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted"
                    >
                      50% Partial (₹{Math.round(collectingDue.remainingBalance / 2).toLocaleString("en-IN")})
                    </button>
                  )}
                </div>
              </div>

              {/* Amount & Method */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Payment Amount (INR ₹) <span className="text-red-400">*</span>
                  </label>
                  <div className="relative mt-1">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 font-bold text-muted-foreground">
                      ₹
                    </span>
                    <input
                      type="number"
                      min={1}
                      max={collectingDue.remainingBalance}
                      value={collectAmount}
                      onChange={(e) => {
                        setCollectAmount(Number(e.target.value));
                        setCollectError("");
                      }}
                      className="w-full rounded-xl border border-border bg-background py-2.5 pl-8 pr-3 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Payment Method
                  </label>
                  <select
                    value={collectMethod}
                    onChange={(e) => setCollectMethod(e.target.value as PaymentMethod)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  >
                    <option value="UPI">UPI / QR Code</option>
                    <option value="Card">Debit / Credit Card</option>
                    <option value="Cash">Cash</option>
                    <option value="Bank Transfer">Bank Transfer / NEFT</option>
                  </select>
                </div>
              </div>

              {collectError && <p className="text-xs text-red-400 font-medium">{collectError}</p>}

              {/* Reference & Note */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Reference / UTR
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. UPI/2026/123456"
                    value={collectReference}
                    onChange={(e) => setCollectReference(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Note / Remarks
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Partial installment paid"
                    value={collectNote}
                    onChange={(e) => setCollectNote(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground">
                Recording this payment will generate a sequential receipt number and update the member&apos;s
                outstanding ledger balance immediately.
              </p>

              {/* Actions */}
              <div className="mt-6 flex items-center justify-end gap-3 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setCollectingDue(null)}
                  className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-[#C9A04F] px-5 py-2.5 text-sm font-bold text-black transition-all hover:bg-[#b68d3e]"
                >
                  Confirm Collection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: DUES DETAILS & PAYMENT HISTORY (Module 1 & 3) */}
      {viewingDueDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-xl rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <button
              onClick={() => setViewingDueDetails(null)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 border-b border-border pb-4">
              <History size={20} className="text-[#C9A04F]" />
              <div>
                <h2 className="text-lg font-bold text-foreground">Dues Ledger & Payment History</h2>
                <span className="text-xs text-muted-foreground font-mono">{viewingDueDetails.id}</span>
              </div>
            </div>

            <div className="mt-5 space-y-5">
              {/* Member & Dues Summary */}
              <div className="grid grid-cols-2 gap-4 rounded-xl border border-border bg-background/50 p-4 text-xs">
                <div>
                  <span className="text-muted-foreground">Member:</span>
                  <div className="font-bold text-sm text-foreground mt-0.5">{viewingDueDetails.memberName}</div>
                  <div className="text-muted-foreground font-mono">{viewingDueDetails.memberId} • {viewingDueDetails.memberPlan}</div>
                </div>

                <div className="text-right">
                  <span className="text-muted-foreground">Status:</span>
                  <div className="mt-1">
                    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getDueStatusBadge(viewingDueDetails.status)}`}>
                      {viewingDueDetails.status}
                    </span>
                  </div>
                  <div className="text-muted-foreground mt-1 text-[11px]">Due Date: {viewingDueDetails.dueDate}</div>
                </div>
              </div>

              {/* Balance Progress Bar */}
              <div className="rounded-xl border border-border bg-card p-4 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Settlement Progress</span>
                  <span className="font-bold text-foreground">
                    ₹{viewingDueDetails.amountPaid.toLocaleString("en-IN")} of ₹{viewingDueDetails.totalAmount.toLocaleString("en-IN")} ({Math.round((viewingDueDetails.amountPaid / (viewingDueDetails.totalAmount || 1)) * 100)}%)
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted/50">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all"
                    style={{
                      width: `${Math.min(100, Math.round((viewingDueDetails.amountPaid / (viewingDueDetails.totalAmount || 1)) * 100))}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs pt-1">
                  <span className="text-muted-foreground">Remaining Balance:</span>
                  <span className="font-bold text-[#C9A04F]">₹{viewingDueDetails.remainingBalance.toLocaleString("en-IN")}</span>
                </div>
              </div>

              {/* Transactions History for this Dues Item */}
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                  Recorded Payments for this Invoice ({viewingDueDetails.payments.length})
                </h3>

                {viewingDueDetails.payments.length === 0 ? (
                  <div className="rounded-xl border border-border bg-background/40 p-6 text-center text-xs text-muted-foreground">
                    No payment transactions recorded yet against this due.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {viewingDueDetails.payments.map((pt) => (
                      <div
                        key={pt.txnId}
                        className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-3 text-xs"
                      >
                        <div>
                          <div className="font-bold font-mono text-[#C9A04F]">{pt.txnId}</div>
                          <div className="text-[11px] text-muted-foreground">{pt.receiptNumber} • {pt.paymentDate}</div>
                          {pt.reference && <div className="text-[10px] text-muted-foreground">Ref: {pt.reference}</div>}
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold text-emerald-400">₹{pt.amount.toLocaleString("en-IN")}</div>
                          <span className="rounded border border-border px-1.5 py-0.2 text-[10px] text-muted-foreground">
                            {pt.method}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-between border-t border-border pt-4">
                <button
                  onClick={() => setViewingDueDetails(null)}
                  className="rounded-xl border border-border bg-background px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted"
                >
                  Close
                </button>
                {viewingDueDetails.remainingBalance > 0 && (
                  <button
                    onClick={() => {
                      const due = viewingDueDetails;
                      setViewingDueDetails(null);
                      openCollectModal(due);
                    }}
                    className="rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black hover:bg-[#b68d3e]"
                  >
                    Collect Due Payment
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: DIRECT RECORD PAYMENT MODAL */}
      {isRecordModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <button
              type="button"
              onClick={() => setIsRecordModalOpen(false)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 border-b border-border pb-4">
              <CreditCard size={20} className="text-[#C9A04F]" />
              <h2 className="text-lg font-bold text-foreground">Record Member Payment</h2>
            </div>

            <form onSubmit={handleRecordPayment} noValidate className="mt-5 space-y-4">
              {/* Member select */}
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Member <span className="text-red-400">*</span>
                </label>
                <select
                  value={formMemberId}
                  onChange={(e) => setFormMemberId(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                >
                  <option value="">-- Choose Member --</option>
                  {sortMembersByNumericId(members).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id} - {m.name} ({m.plan})
                    </option>
                  ))}
                </select>
                {formErrors.memberId && (
                  <p className="mt-1 text-xs text-red-400">{formErrors.memberId}</p>
                )}
              </div>

              {/* Amount & Method */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Amount (INR ₹) <span className="text-red-400">*</span>
                  </label>
                  <div className="relative mt-1">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 font-bold text-muted-foreground">
                      ₹
                    </span>
                    <input
                      type="number"
                      min={1}
                      value={formAmount}
                      onChange={(e) => setFormAmount(Number(e.target.value))}
                      className="w-full rounded-xl border border-border bg-background py-2.5 pl-8 pr-3 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                  {formErrors.amount && (
                    <p className="mt-1 text-xs text-red-400">{formErrors.amount}</p>
                  )}
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Payment Method
                  </label>
                  <select
                    value={formMethod}
                    onChange={(e) => setFormMethod(e.target.value as PaymentMethod)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  >
                    <option value="UPI">UPI / QR Code</option>
                    <option value="Card">Debit / Credit Card</option>
                    <option value="Cash">Cash</option>
                    <option value="Bank Transfer">Bank Transfer / NEFT</option>
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Description / Purpose <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Standard 3-Month Membership Fee"
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                />
                {formErrors.description && (
                  <p className="mt-1 text-xs text-red-400">{formErrors.description}</p>
                )}
              </div>

              {/* Reference & Status */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Reference / UTR / Note
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. UPI/2026/123456"
                    value={formReference}
                    onChange={(e) => setFormReference(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Payment Status
                  </label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as PaymentStatus)}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  >
                    <option value="Paid">Paid</option>
                    <option value="Pending">Pending</option>
                  </select>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-6 flex items-center justify-end gap-3 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setIsRecordModalOpen(false)}
                  className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-[#C9A04F] px-5 py-2.5 text-sm font-bold text-black transition-all hover:bg-[#b68d3e]"
                >
                  Confirm & Save Payment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: PRINTABLE RECEIPT MODAL */}
      {receiptRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl sm:p-8">
            <button
              onClick={() => setReceiptRecord(null)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground print:hidden"
            >
              <X size={18} />
            </button>

            {/* Printable Receipt Sheet */}
            <div id="gymcore-receipt-content" className="space-y-6">
              {/* Receipt Header */}
              <div className="flex items-start justify-between border-b border-border pb-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xl font-black tracking-wider text-[#C9A04F]">
                      GYMCORE
                    </span>
                    <span className="rounded-md border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-1.5 py-0.5 text-[10px] font-bold text-[#C9A04F]">
                      PAYMENT RECEIPT (DEMO)
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Plot 88, 100ft Road, Indiranagar, Bangalore
                  </p>
                  <p className="text-xs text-muted-foreground">+91 80 4123 4567 • contact@gymcore.fit</p>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-[#C9A04F]">
                    {receiptRecord.receiptNumber}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    Txn: {receiptRecord.id}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Date: {receiptRecord.paymentDate}
                  </div>
                </div>
              </div>

              {/* Billed To */}
              <div className="rounded-xl border border-border bg-background/50 p-4">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Billed To
                </div>
                <div className="mt-1 flex items-baseline justify-between">
                  <div className="text-sm font-bold text-foreground">
                    {receiptRecord.memberName}
                  </div>
                  <div className="text-xs font-mono text-[#C9A04F]">
                    {receiptRecord.memberId}
                  </div>
                </div>
              </div>

              {/* Itemized Table */}
              <div className="rounded-xl border border-border overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-border bg-muted/40 uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="py-2.5 px-3">Item / Description</th>
                      <th className="py-2.5 px-3 text-center">Method</th>
                      <th className="py-2.5 px-3 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    <tr>
                      <td className="py-3 px-3 text-foreground font-medium">
                        {receiptRecord.description}
                        {receiptRecord.reference && (
                          <div className="text-[11px] text-muted-foreground">
                            Ref: {receiptRecord.reference}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className="rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-semibold">
                          {receiptRecord.method}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-[#C9A04F]">
                        ₹{receiptRecord.amount.toLocaleString("en-IN")}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Total & Summary */}
              <div className="space-y-1.5 border-t border-border pt-4 text-xs">
                <div className="flex justify-between text-muted-foreground">
                  <span>Subtotal</span>
                  <span>₹{Math.round(receiptRecord.amount / 1.18).toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>GST / Tax (18% inclusive)</span>
                  <span>
                    ₹
                    {(
                      receiptRecord.amount - Math.round(receiptRecord.amount / 1.18)
                    ).toLocaleString("en-IN")}
                  </span>
                </div>
                <div className="flex justify-between border-t border-border/60 pt-2 text-sm font-bold text-foreground">
                  <span>Total Amount Paid</span>
                  <span className="text-[#C9A04F]">
                    ₹{receiptRecord.amount.toLocaleString("en-IN")}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Payment Status:</span>
                  <span
                    className={`font-semibold ${
                      receiptRecord.status === "Paid" ? "text-emerald-400" : "text-amber-400"
                    }`}
                  >
                    {receiptRecord.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Footer Note */}
              <div className="border-t border-border pt-3 text-center text-[11px] text-muted-foreground">
                <p>Thank you for training with GYMCORE Fitness Club.</p>
                <p className="mt-0.5">This is a computer-generated membership payment receipt (Demo). For a statutory tax invoice, please contact the front desk.</p>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="mt-6 flex items-center justify-between border-t border-border pt-4 print:hidden">
              <button
                onClick={() => setReceiptRecord(null)}
                className="rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                Close
              </button>

              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black transition-all hover:bg-[#b68d3e]"
              >
                <Printer size={14} />
                <span>Print Official Receipt</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
