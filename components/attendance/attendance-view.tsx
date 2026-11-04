"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  UserCheck,
  Users,
  Clock,
  LogOut,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Sparkles,
  ShieldCheck,
  UserX,
  QrCode,
  Camera,
  ShieldAlert,
  AlertTriangle,
  X,
} from "lucide-react";
import {
  type Member,
  getTodayDateString,
  checkInMember,
  checkOutMember,
  getMemberWarning,
  getMemberOutstandingDues,
  sortMembersByNumericId,
} from "@/lib/mock-data";
import { useAttendanceStore } from "@/lib/use-attendance-store";
import { useMembersStore } from "@/lib/use-members-store";

export function AttendanceView() {
  const attendance = useAttendanceStore();
  const members = useMembersStore();

  const todayStr = getTodayDateString();

  // Search & filters for the history table
  const [historySearch, setHistorySearch] = useState("");
  const [dateFilter, setDateFilter] = useState<"today" | "all">("today");
  const [statusFilter, setStatusFilter] = useState<"All" | "Present" | "Checked Out">("All");

  // Fast Check-In Search Bar state
  const [fastSearchQuery, setFastSearchQuery] = useState("");
  const [isSearchDropdownOpen, setIsSearchDropdownOpen] = useState(false);

  // QR Scanner Modal state
  const [isQrScannerOpen, setIsQrScannerOpen] = useState(false);
  const isQrScannerOpenRef = useRef(false);
  const [cameraState, setCameraState] = useState<"idle" | "requesting" | "active" | "denied" | "unsupported">("idle");
  const [manualQrInput, setManualQrInput] = useState("");
  const [cameraErrorMsg, setCameraErrorMsg] = useState("");
  const [scannerNotification, setScannerNotification] = useState<{
    type: "success" | "error" | "warning";
    message: string;
  } | null>(null);
  const scannerTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Manual Override Modal state
  const [overrideTargetMember, setOverrideTargetMember] = useState<Member | null>(null);
  const [overrideReason, setOverrideReason] = useState("Manager Approved Grace Access");
  const [customOverrideReason, setCustomOverrideReason] = useState("");
  const [overrideBlockedCause, setOverrideBlockedCause] = useState("");

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

  const showScannerNotification = (
    message: string,
    type: "success" | "error" | "warning" = "warning"
  ) => {
    if (scannerTimeoutRef.current) {
      clearTimeout(scannerTimeoutRef.current);
    }
    setScannerNotification({ message, type });
    scannerTimeoutRef.current = setTimeout(() => {
      setScannerNotification(null);
    }, 6000);
  };

  // Compute stats for today
  const todayRecords = attendance.filter((a) => a.date === todayStr);
  const currentlyPresentRecords = todayRecords.filter((a) => a.status === "Present");
  const checkedOutTodayRecords = todayRecords.filter((a) => a.status === "Checked Out");

  const activeMembers = members.filter((m) => m.status === "Active");
  const checkedInMemberIdsToday = new Set(todayRecords.map((a) => a.memberId.toLowerCase()));
  const notCheckedInTodayCount = activeMembers.filter(
    (m) => !checkedInMemberIdsToday.has(m.id.toLowerCase())
  ).length;

  // Fast Search matching members
  const fastSearchMatches = sortMembersByNumericId(
    members.filter((m) => {
      if (!fastSearchQuery.trim()) return false;
      const q = fastSearchQuery.toLowerCase().trim();
      return (
        m.id.toLowerCase().includes(q) ||
        m.name.toLowerCase().includes(q) ||
        m.phone.toLowerCase().includes(q)
      );
    })
  );

  // Handle standard Check In execution
  const executeCheckIn = (
    memberInput: string,
    options?: { fromScanner?: boolean }
  ) => {
    const isFromScanner = Boolean(
      options?.fromScanner || isQrScannerOpen || isQrScannerOpenRef.current
    );
    const trimmed = memberInput.trim();
    if (!trimmed) return;

    // Resolve member by exact ID (case-insensitive), phone digits, or full name
    const member = members.find((m) => {
      const idMatch = m.id.toLowerCase() === trimmed.toLowerCase();
      const phoneDigits = m.phone.replace(/\D/g, "");
      const inputDigits = trimmed.replace(/\D/g, "");
      const phoneMatch = inputDigits.length >= 7 && (phoneDigits === inputDigits || phoneDigits.endsWith(inputDigits));
      const nameMatch = m.name.toLowerCase() === trimmed.toLowerCase();
      return idMatch || phoneMatch || nameMatch;
    });

    if (!member) {
      const notFoundMsg = `Member "${trimmed}" was not found in gym registry.`;
      if (isFromScanner) {
        showScannerNotification(notFoundMsg, "error");
      } else {
        showNotification(notFoundMsg, "error");
      }
      return;
    }

    const res = checkInMember(member.id);

    if (res.success) {
      if (scannerTimeoutRef.current) {
        clearTimeout(scannerTimeoutRef.current);
        scannerTimeoutRef.current = null;
      }
      setScannerNotification(null);
      showNotification(res.message, "success");
      setFastSearchQuery("");
      setManualQrInput("");
      setIsSearchDropdownOpen(false);
      if (isFromScanner) {
        closeQrScanner();
      }
    } else {
      if (res.blockedReason === "expired" || res.blockedReason === "frozen") {
        if (isFromScanner) {
          showScannerNotification(res.message, "warning");
        }
        // Trigger Admin Override option
        setOverrideTargetMember(member);
        setOverrideBlockedCause(res.message);
      } else if (res.blockedReason === "already_present") {
        if (isFromScanner) {
          showScannerNotification(res.message, "warning");
        } else {
          showNotification(res.message, "warning");
        }
      } else {
        if (isFromScanner) {
          showScannerNotification(res.message, "error");
        } else {
          showNotification(res.message, "error");
        }
      }
    }
  };

  // Handle Admin Override Confirm
  const handleConfirmOverride = () => {
    if (!overrideTargetMember) return;
    const finalReason =
      overrideReason === "Other"
        ? customOverrideReason.trim() || "Administrative Discretion"
        : overrideReason;

    const res = checkInMember(overrideTargetMember.id, {
      isOverride: true,
      overrideReason: finalReason,
      overriddenBy: "Gymcore Admin",
    });

    if (res.success) {
      showNotification(res.message, "warning");
      setOverrideTargetMember(null);
      setCustomOverrideReason("");
      setFastSearchQuery("");
      setIsSearchDropdownOpen(false);
      if (isQrScannerOpen) {
        closeQrScanner();
      }
    } else {
      showNotification(res.message, "error");
    }
  };

  // Handle Check Out
  const handleCheckOut = (recordId: string) => {
    const res = checkOutMember(recordId);
    if (res.success) {
      showNotification(res.message, "success");
    } else {
      showNotification(res.message, "error");
    }
  };

  // Camera stream management for QR Scanner
  const startCamera = async () => {
    setCameraState("requesting");
    setCameraErrorMsg("");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraState("unsupported");
      setCameraErrorMsg("Camera access is not supported by your browser. Please use manual entry.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraState("active");
    } catch (err: unknown) {
      const error = err as { name?: string; message?: string };
      console.warn("Camera access error:", error);
      if (error?.name === "NotAllowedError" || error?.name === "PermissionDeniedError") {
        setCameraState("denied");
        setCameraErrorMsg("Camera access was denied. Please allow permissions in browser settings or use manual entry.");
      } else {
        setCameraState("unsupported");
        setCameraErrorMsg("No compatible camera device found. Please enter Member ID below.");
      }
    }
  };

  const openQrScanner = () => {
    isQrScannerOpenRef.current = true;
    if (scannerTimeoutRef.current) {
      clearTimeout(scannerTimeoutRef.current);
      scannerTimeoutRef.current = null;
    }
    setScannerNotification(null);
    setManualQrInput("");
    setIsQrScannerOpen(true);
    startCamera();
  };

  const closeQrScanner = () => {
    isQrScannerOpenRef.current = false;
    if (scannerTimeoutRef.current) {
      clearTimeout(scannerTimeoutRef.current);
      scannerTimeoutRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraState("idle");
    setIsQrScannerOpen(false);
    setManualQrInput("");
    setScannerNotification(null);
  };

  useEffect(() => {
    return () => {
      if (scannerTimeoutRef.current) {
        clearTimeout(scannerTimeoutRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  // Filtered attendance history records
  const filteredRecords = attendance.filter((record) => {
    if (dateFilter === "today" && record.date !== todayStr) {
      return false;
    }
    if (statusFilter !== "All" && record.status !== statusFilter) {
      return false;
    }
    if (historySearch.trim()) {
      const q = historySearch.toLowerCase();
      const match =
        record.memberName.toLowerCase().includes(q) ||
        record.memberId.toLowerCase().includes(q) ||
        record.memberPlan.toLowerCase().includes(q) ||
        (record.overrideReason && record.overrideReason.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  return (
    <div className="space-y-8">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-6 right-6 z-[70] max-w-md shadow-2xl flex items-center justify-between gap-3 rounded-xl border p-4 text-sm font-medium animate-in fade-in slide-in-from-top-2 backdrop-blur-md ${notification.type === "success"
            ? "border-emerald-500/40 bg-zinc-950/95 text-emerald-400"
            : notification.type === "warning"
              ? "border-amber-500/40 bg-zinc-950/95 text-amber-300"
              : "border-red-500/40 bg-zinc-950/95 text-red-400"
            }`}
        >
          <div className="flex items-center gap-2.5">
            {notification.type === "success" ? (
              <CheckCircle2 size={18} className="shrink-0 text-emerald-400" />
            ) : notification.type === "warning" ? (
              <AlertTriangle size={18} className="shrink-0 text-amber-400" />
            ) : (
              <AlertCircle size={18} className="shrink-0 text-red-400" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-card via-card to-[#C9A04F]/10 p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#C9A04F]">
              <Sparkles size={14} />
              <span>Day 4 Enhanced Floor Operations</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Daily Attendance System
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Fast member check-ins with instant search, camera-ready QR scanner interface, membership
              expiry alerts, and administrative override logging.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={openQrScanner}
              className="flex items-center gap-2 rounded-xl bg-[#C9A04F] px-4 py-2.5 text-xs font-bold text-black transition-all hover:bg-[#b68d3e] shadow-lg shadow-[#C9A04F]/10"
            >
              <QrCode size={16} />
              <span>Open QR Scanner</span>
            </button>
            <div className="hidden sm:flex items-center gap-2 rounded-xl border border-border bg-background/60 px-3.5 py-2 backdrop-blur-sm">
              <Calendar size={16} className="text-[#C9A04F]" />
              <div className="text-right">
                <div className="text-[10px] text-muted-foreground">Today</div>
                <div className="text-xs font-bold text-foreground">{todayStr}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Today&apos;s Check-ins
            </span>
            <div className="rounded-xl bg-[#C9A04F]/10 p-2.5 text-[#C9A04F]">
              <UserCheck size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">{todayRecords.length}</span>
            <span className="text-xs text-muted-foreground">sessions recorded</span>
          </div>
        </div>

        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-5 transition-colors hover:border-emerald-500/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              Currently Present
            </span>
            <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-400">
              <Clock size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400">
              {currentlyPresentRecords.length}
            </span>
            <span className="text-xs text-emerald-500/80">on gym floor</span>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Checked Out Today
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2.5 text-blue-400">
              <LogOut size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">
              {checkedOutTodayRecords.length}
            </span>
            <span className="text-xs text-muted-foreground">finished workout</span>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 transition-colors hover:border-[#C9A04F]/50">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Not Checked In Yet
            </span>
            <div className="rounded-xl bg-zinc-500/10 p-2.5 text-zinc-400">
              <UserX size={20} />
            </div>
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-foreground">
              {notCheckedInTodayCount}
            </span>
            <span className="text-xs text-muted-foreground">active members</span>
          </div>
        </div>
      </div>

      {/* Fast Check-In Search Bar & Floor Operations */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Fast Check-In Panel */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm lg:col-span-1">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <ShieldCheck size={20} className="text-[#C9A04F]" />
              <h2 className="text-lg font-bold text-foreground">Fast Member Check-In</h2>
            </div>
            <button
              onClick={openQrScanner}
              className="text-xs font-semibold text-[#C9A04F] hover:underline flex items-center gap-1"
            >
              <QrCode size={13} />
              <span>QR Scan</span>
            </button>
          </div>

          <div className="mt-5 space-y-4">
            {/* Live Search Input */}
            <div className="relative">
              <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Search by Name, ID, or Phone
              </label>
              <div className="relative mt-1.5">
                <Search
                  size={16}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <input
                  type="text"
                  placeholder="Enter Member ID, name, or phone..."
                  value={fastSearchQuery}
                  onChange={(e) => {
                    setFastSearchQuery(e.target.value);
                    setIsSearchDropdownOpen(true);
                  }}
                  onFocus={() => setIsSearchDropdownOpen(true)}
                  className="w-full rounded-xl border border-border bg-background py-2.5 pl-10 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
                />
                {fastSearchQuery && (
                  <button
                    onClick={() => {
                      setFastSearchQuery("");
                      setIsSearchDropdownOpen(false);
                    }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>

              {/* Instant Search Results Dropdown */}
              {isSearchDropdownOpen && fastSearchQuery.trim() && (
                <div className="absolute left-0 right-0 z-30 mt-2 max-h-72 overflow-y-auto rounded-xl border border-border bg-card p-2 shadow-2xl">
                  {fastSearchMatches.length === 0 ? (
                    <div className="p-4 text-center text-xs text-muted-foreground">
                      No matching members found for &quot;{fastSearchQuery}&quot;.
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {fastSearchMatches.map((m) => {
                        const isPresent = currentlyPresentRecords.some(
                          (a) => a.memberId.toLowerCase() === m.id.toLowerCase()
                        );
                        const warning = getMemberWarning(m);
                        const dues = getMemberOutstandingDues(m.id);

                        return (
                          <div
                            key={m.id}
                            className="rounded-lg border border-border/60 bg-background/60 p-3 transition-colors hover:border-[#C9A04F]/50"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-xs font-bold text-[#C9A04F]">
                                    {m.id}
                                  </span>
                                  <span className="text-sm font-bold text-foreground">
                                    {m.name}
                                  </span>
                                </div>
                                <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                                  <span>{m.plan}</span>
                                  <span>•</span>
                                  <span>{m.phone}</span>
                                </div>
                              </div>

                              <div>
                                {isPresent ? (
                                  <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-400">
                                    <Clock size={11} /> On Floor
                                  </span>
                                ) : m.status === "Active" ? (
                                  <button
                                    onClick={() => executeCheckIn(m.id)}
                                    className="rounded-lg bg-[#C9A04F] px-3 py-1 text-xs font-bold text-black transition-all hover:bg-[#b68d3e]"
                                  >
                                    Check In
                                  </button>
                                ) : (
                                  <div className="flex items-center gap-1.5">
                                    <span className="rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-400">
                                      {m.status}
                                    </span>
                                    <button
                                      onClick={() => {
                                        setOverrideTargetMember(m);
                                        setOverrideBlockedCause(
                                          `Membership status is ${m.status}. Normal check-in is restricted.`
                                        );
                                      }}
                                      className="rounded-md border border-amber-500/40 bg-amber-500/15 px-2 py-1 text-[11px] font-bold text-amber-300 hover:bg-amber-500/25"
                                    >
                                      Override
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Warnings row */}
                            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                              {warning.level !== "active" && (
                                <span className={`rounded px-1.5 py-0.5 font-semibold ${warning.badgeColor}`}>
                                  {warning.text}
                                </span>
                              )}
                              {dues > 0 && (
                                <span className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 font-semibold text-amber-300">
                                  Dues: ₹{dues.toLocaleString("en-IN")} Pending
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Quick Sample Check-In Chips */}
            <div className="pt-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Quick Select Active Member:
              </span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {sortMembersByNumericId(activeMembers).map((m) => (
                  <button
                    key={m.id}
                    onClick={() => executeCheckIn(m.id)}
                    className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:border-[#C9A04F] hover:text-[#C9A04F]"
                  >
                    {m.id} - {m.name.split(" ")[0]}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Currently on Floor Section */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
              </span>
              <h2 className="text-lg font-bold text-foreground">
                Currently Inside Gym Floor ({currentlyPresentRecords.length})
              </h2>
            </div>
            <span className="text-xs text-muted-foreground">Live occupancy</span>
          </div>

          <div className="mt-4">
            {currentlyPresentRecords.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="rounded-full bg-muted/20 p-4 text-muted-foreground">
                  <Users size={32} />
                </div>
                <h3 className="mt-3 text-sm font-semibold text-foreground">
                  Gym Floor is Currently Empty
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Use the quick check-in search or QR scanner to log members entering the facility.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {currentlyPresentRecords.map((record) => (
                  <div
                    key={record.id}
                    className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-4 transition-colors hover:border-[#C9A04F]/40"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#C9A04F]/10 font-bold text-[#C9A04F]">
                        {record.memberName
                          .split(" ")
                          .map((n) => n[0])
                          .join("")}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/members/${record.memberId}`}
                            className="truncate text-sm font-bold text-foreground hover:text-[#C9A04F] transition-colors"
                          >
                            {record.memberName}
                          </Link>
                          {record.isOverride && (
                            <span
                              className="rounded border border-amber-500/40 bg-amber-500/15 px-1.5 py-0.2 text-[9px] font-bold text-amber-300"
                              title={`Admin Override: ${record.overrideReason}`}
                            >
                              OVERRIDE
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{record.memberId}</span>
                          <span>•</span>
                          <span className="text-[#C9A04F]">{record.memberPlan}</span>
                        </div>
                        <div className="mt-1 flex items-center gap-1 text-[11px] text-emerald-400">
                          <Clock size={12} />
                          <span>In since {record.checkInTime}</span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleCheckOut(record.id)}
                      className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-muted-foreground transition-all hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400"
                      title="Check out member"
                    >
                      <LogOut size={13} />
                      <span className="hidden sm:inline">Check Out</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Attendance History Table Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground">Attendance Logs & Audit Trail</h2>
            <p className="text-xs text-muted-foreground">
              Complete history of member visits, timestamps, and manual admin overrides
            </p>
          </div>

          {/* Filter controls */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative min-w-[200px]">
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                placeholder="Search member, ID, or override..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
              />
            </div>

            {/* Date filter */}
            <div className="flex rounded-xl border border-border bg-background p-1 text-xs">
              <button
                onClick={() => setDateFilter("today")}
                className={`rounded-lg px-3 py-1 font-medium transition-colors ${dateFilter === "today"
                  ? "bg-[#C9A04F] text-black font-semibold"
                  : "text-muted-foreground hover:text-foreground"
                  }`}
              >
                Today
              </button>
              <button
                onClick={() => setDateFilter("all")}
                className={`rounded-lg px-3 py-1 font-medium transition-colors ${dateFilter === "all"
                  ? "bg-[#C9A04F] text-black font-semibold"
                  : "text-muted-foreground hover:text-foreground"
                  }`}
              >
                All History
              </button>
            </div>

            {/* Status filter */}
            <div className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 py-1 text-xs">
              <Filter size={13} className="text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(e.target.value as "All" | "Present" | "Checked Out")
                }
                className="bg-transparent text-xs text-foreground focus:outline-none"
              >
                <option value="All">All Statuses</option>
                <option value="Present">Present Only</option>
                <option value="Checked Out">Checked Out Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="pb-3 pl-2">Member</th>
                <th className="pb-3">Plan</th>
                <th className="pb-3">Date</th>
                <th className="pb-3">Check-In</th>
                <th className="pb-3">Check-Out</th>
                <th className="pb-3">Status</th>
                <th className="pb-3">Verification / Audit</th>
                <th className="pb-3 pr-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50 text-foreground">
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-xs text-muted-foreground">
                    No attendance records match your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((record) => (
                  <tr key={record.id} className="transition-colors hover:bg-muted/30">
                    <td className="py-3.5 pl-2">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#C9A04F]/10 font-bold text-xs text-[#C9A04F]">
                          {record.memberName
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </div>
                        <div>
                          <Link
                            href={`/members/${record.memberId}`}
                            className="font-medium hover:text-[#C9A04F] transition-colors"
                          >
                            {record.memberName}
                          </Link>
                          <div className="text-[11px] text-muted-foreground">{record.memberId}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5">
                      <span className="rounded-md border border-border bg-background px-2 py-0.5 text-xs font-semibold text-[#C9A04F]">
                        {record.memberPlan}
                      </span>
                    </td>
                    <td className="py-3.5 text-xs text-muted-foreground">{record.date}</td>
                    <td className="py-3.5">
                      <div className="flex items-center gap-1.5 text-xs text-foreground">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                        <span>{record.checkInTime}</span>
                      </div>
                    </td>
                    <td className="py-3.5 text-xs">
                      {record.checkOutTime ? (
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <span className="h-1.5 w-1.5 rounded-full bg-zinc-400"></span>
                          <span>{record.checkOutTime}</span>
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
                          <Clock size={11} /> Still on floor
                        </span>
                      )}
                    </td>
                    <td className="py-3.5">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${record.status === "Present"
                          ? "border border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                          : "border border-zinc-500/20 bg-zinc-500/10 text-zinc-400"
                          }`}
                      >
                        {record.status}
                      </span>
                    </td>
                    <td className="py-3.5 text-xs">
                      {record.isOverride ? (
                        <div>
                          <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                            <ShieldAlert size={10} /> Override Logged
                          </span>
                          <div className="text-[10px] text-muted-foreground mt-0.5 max-w-[180px] truncate" title={record.overrideReason}>
                            Reason: {record.overrideReason}
                          </div>
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                          <ShieldCheck size={12} className="text-emerald-400" /> Standard Validated
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 pr-2 text-right">
                      {record.status === "Present" ? (
                        <button
                          onClick={() => handleCheckOut(record.id)}
                          className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium text-muted-foreground hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                        >
                          Check Out
                        </button>
                      ) : (
                        <span className="text-xs text-muted-foreground/60">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* QR Scanner Modal (Module 5) */}
      {isQrScannerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <button
              onClick={closeQrScanner}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 border-b border-border pb-4">
              <Camera size={20} className="text-[#C9A04F]" />
              <h2 className="text-lg font-bold text-foreground">Member QR Check-In Scanner</h2>
            </div>

            {/* In-Modal Top Alert Banner */}
            {scannerNotification && (
              <div
                className={`mt-4 flex items-start justify-between gap-2.5 rounded-xl border p-3.5 text-xs font-medium animate-in fade-in slide-in-from-top-1 ${scannerNotification.type === "warning"
                  ? "border-amber-500/40 bg-amber-500/15 text-amber-300"
                  : scannerNotification.type === "error"
                    ? "border-red-500/30 bg-red-500/15 text-red-400"
                    : "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  }`}
              >
                <div className="flex items-start gap-2">
                  {scannerNotification.type === "warning" ? (
                    <AlertTriangle size={16} className="shrink-0 text-amber-400 mt-0.5" />
                  ) : scannerNotification.type === "error" ? (
                    <AlertCircle size={16} className="shrink-0 text-red-400 mt-0.5" />
                  ) : (
                    <CheckCircle2 size={16} className="shrink-0 text-emerald-400 mt-0.5" />
                  )}
                  <span className="leading-relaxed">{scannerNotification.message}</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (scannerTimeoutRef.current) {
                      clearTimeout(scannerTimeoutRef.current);
                      scannerTimeoutRef.current = null;
                    }
                    setScannerNotification(null);
                  }}
                  className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground"
                  aria-label="Dismiss notification"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Camera Viewport Area */}
            <div className="mt-5 space-y-4">
              <div className="relative mx-auto h-56 w-full overflow-hidden rounded-xl border border-border bg-black flex items-center justify-center">
                {cameraState === "active" ? (
                  <>
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="h-full w-full object-cover"
                    />
                    {/* Viewport Reticle */}
                    <div className="pointer-events-none absolute inset-6 rounded-xl border-2 border-dashed border-[#C9A04F] flex items-center justify-center">
                      <div className="h-0.5 w-full bg-[#C9A04F]/60 animate-pulse"></div>
                    </div>
                  </>
                ) : (
                  <div className="p-4 text-center">
                    <Camera size={36} className="mx-auto text-muted-foreground/40 mb-2" />
                    <p className="text-xs font-semibold text-foreground">
                      {cameraState === "requesting"
                        ? "Requesting camera permissions..."
                        : cameraState === "denied"
                          ? "Camera Permission Denied"
                          : "Camera Unavailable"}
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-1 max-w-xs mx-auto">
                      {cameraErrorMsg || "Use the manual Member ID entry fallback below to complete check-in."}
                    </p>
                  </div>
                )}
              </div>

              {/* Status Note */}
              <div className="rounded-xl border border-border bg-background/50 p-3 text-xs text-muted-foreground flex items-center justify-between">
                <span>Scanner Status:</span>
                <span className="font-semibold text-foreground">
                  {cameraState === "active" ? "Camera Live (Waiting for code)" : "Manual Fallback Active"}
                </span>
              </div>

              {/* Manual Member ID Entry Fallback */}
              <div className="border-t border-border pt-4 space-y-3">
                <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Manual Member ID / QR Code Fallback
                </label>

                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter Member ID (e.g. GYM001)"
                    value={manualQrInput}
                    onChange={(e) => {
                      setManualQrInput(e.target.value);
                      if (scannerNotification) {
                        if (scannerTimeoutRef.current) {
                          clearTimeout(scannerTimeoutRef.current);
                          scannerTimeoutRef.current = null;
                        }
                        setScannerNotification(null);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        if (!manualQrInput.trim()) {
                          showScannerNotification("Please enter a Member ID.", "error");
                          return;
                        }
                        executeCheckIn(manualQrInput.trim(), { fromScanner: true });
                      }
                    }}
                    className="flex-1 rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (!manualQrInput.trim()) {
                        showScannerNotification("Please enter a Member ID.", "error");
                        return;
                      }
                      executeCheckIn(manualQrInput.trim(), { fromScanner: true });
                    }}
                    className="rounded-xl bg-[#C9A04F] px-4 py-2.5 text-xs font-bold text-black hover:bg-[#b68d3e]"
                  >
                    Check In
                  </button>
                </div>

                {/* Sample member chips */}
                <div className="pt-1">
                  <span className="text-[10px] text-muted-foreground">Quick test member codes:</span>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {sortMembersByNumericId(members).map((m) => (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => executeCheckIn(m.id, { fromScanner: true })}
                        className="rounded-md border border-border bg-background px-2 py-0.5 text-[10px] font-mono text-muted-foreground hover:border-[#C9A04F] hover:text-[#C9A04F]"
                      >
                        {m.id}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="mt-6 flex justify-end border-t border-border pt-4">
                <button
                  type="button"
                  onClick={closeQrScanner}
                  className="rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  Close Scanner
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual Check-In Override Dialog (Module 7) */}
      {overrideTargetMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-amber-500/40 bg-card p-6 shadow-2xl">
            <button
              onClick={() => setOverrideTargetMember(null)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 text-amber-400 border-b border-border pb-4">
              <ShieldAlert size={22} />
              <h2 className="text-lg font-bold text-foreground">Administrator Check-In Override</h2>
            </div>

            <div className="mt-4 space-y-4 text-xs">
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-amber-300 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertTriangle size={14} /> Normal Check-In Blocked
                </div>
                <p className="text-[11px] leading-relaxed">
                  {overrideBlockedCause || "Member status is not Active. Normal floor entry was denied."}
                </p>
              </div>

              <div className="rounded-xl border border-border bg-background/50 p-3 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Member:</span>
                  <span className="font-bold text-foreground">{overrideTargetMember.name} ({overrideTargetMember.id})</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Current Plan:</span>
                  <span className="font-semibold text-[#C9A04F]">{overrideTargetMember.plan}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Membership Status:</span>
                  <span className="font-bold text-red-400">{overrideTargetMember.status}</span>
                </div>
              </div>

              <div>
                <label className="font-medium text-foreground uppercase tracking-wider text-[11px]">
                  Select Override Authorization Reason <span className="text-red-400">*</span>
                </label>
                <select
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-[#C9A04F] focus:outline-none"
                >
                  <option value="Manager Approved Grace Access">Manager Approved Grace Access (1 Day)</option>
                  <option value="Renewal Payment Promised Tomorrow">Renewal Payment Promised Tomorrow</option>
                  <option value="Facility Tour / Accompanied Guest">Facility Tour / Accompanied Guest</option>
                  <option value="Locker Room / Personal Belongings Access Only">Locker Room / Belongings Access Only</option>
                  <option value="Other">Other (Specify Below)</option>
                </select>
              </div>

              {overrideReason === "Other" && (
                <div>
                  <label className="font-medium text-foreground uppercase tracking-wider text-[11px]">
                    Specify Reason
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Special VIP complimentary floor session"
                    value={customOverrideReason}
                    onChange={(e) => setCustomOverrideReason(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>
              )}

              <p className="text-[11px] text-muted-foreground">
                <span className="font-semibold text-foreground">Audit Notice:</span> This action will be recorded with timestamp and reason in the public attendance audit logs.
              </p>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3 border-t border-border pt-4">
              <button
                type="button"
                onClick={() => setOverrideTargetMember(null)}
                className="rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmOverride}
                className="rounded-xl bg-amber-500 px-4 py-2 text-xs font-bold text-black hover:bg-amber-400 transition-colors"
              >
                Authorize & Check In
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
