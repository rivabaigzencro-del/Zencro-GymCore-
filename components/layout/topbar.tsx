"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import {
  Bell,
  Search,
  ChevronDown,
  Menu,
  Sun,
  Moon,
  X,
  LayoutDashboard,
  Users,
  CreditCard,
  Wallet,
  CalendarCheck,
  UserCog,
  BarChart3,
  Settings,
  Dumbbell,
  LogOut,
  UserCheck,
  ShieldCheck,
  AlertTriangle,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { useMounted } from "@/lib/use-mounted";
import { clearStoredAuthTokens } from "@/lib/api-client";

const navigation = [
  { name: "Overview", icon: LayoutDashboard, href: "/" },
  { name: "Members", icon: Users, href: "/members" },
  { name: "Memberships", icon: CreditCard, href: "/memberships" },
  { name: "Payments", icon: Wallet, href: "/payments" },
  { name: "Attendance", icon: CalendarCheck, href: "/attendance" },
  { name: "Staff", icon: UserCog, href: "/staff" },
  { name: "Reports", icon: BarChart3, href: "/reports" },
  { name: "Audit Logs", icon: ShieldCheck, href: "/audit" },
];

function getHeaderInfo(pathname: string): { title: string; subtitle: string } {
  if (pathname === "/") {
    return { title: "Overview", subtitle: "Welcome back to GYMCORE" };
  }
  if (pathname === "/members") {
    return { title: "Members", subtitle: "Manage gym members and their status" };
  }
  if (pathname.startsWith("/members/")) {
    return { title: "Member Profile", subtitle: "View and manage member details" };
  }
  if (pathname.startsWith("/memberships")) {
    return { title: "Memberships", subtitle: "Manage membership plans and pricing" };
  }
  if (pathname.startsWith("/payments")) {
    return { title: "Payments", subtitle: "Billing history and transaction logs" };
  }
  if (pathname.startsWith("/attendance")) {
    return { title: "Attendance", subtitle: "Daily check-in system and records" };
  }
  if (pathname.startsWith("/staff")) {
    return { title: "Staff", subtitle: "Manage trainers and gym team" };
  }
  if (pathname.startsWith("/reports")) {
    return { title: "Reports", subtitle: "Analytics and performance insights" };
  }
  if (pathname.startsWith("/audit")) {
    return { title: "Audit Trail", subtitle: "Immutable administrative governance and compliance logs" };
  }
  if (pathname.startsWith("/settings")) {
    return { title: "Settings", subtitle: "System configuration and preferences" };
  }
  return { title: "GYMCORE", subtitle: "Stronger Business. Healthier Community." };
}

export function Topbar() {
  return (
    <Suspense
      fallback={
        <header className="flex h-20 items-center justify-between border-b border-border bg-background px-4 sm:px-6 lg:px-8" />
      }
    >
      <TopbarContent />
    </Suspense>
  );
}

function TopbarContent() {
  const pathname = usePathname();
  const router = useRouter();
  const mounted = useMounted();
  const { resolvedTheme, setTheme } = useTheme();

  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [unreadNotifications, setUnreadNotifications] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const isDark = resolvedTheme === "dark";
  const headerInfo = getHeaderInfo(pathname);

  return (
    <>
      <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-border bg-background/90 backdrop-blur-md px-4 sm:px-6 lg:px-8">

        {/* Left Section */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setMenuOpen(true)}
            className="rounded-lg p-2 text-muted-foreground transition hover:bg-muted hover:text-foreground lg:hidden"
            aria-label="Open navigation menu"
          >
            <Menu size={22} />
          </button>

          <div>
            <h2 className="text-lg font-bold tracking-tight text-foreground">
              {headerInfo.title}
            </h2>

            <p className="hidden text-xs text-muted-foreground sm:block">
              {headerInfo.subtitle}
            </p>
          </div>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-3 sm:gap-4">

          {/* Search */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (searchQuery.trim()) {
                router.push(`/members?q=${encodeURIComponent(searchQuery.trim())}`);
              }
            }}
            className="hidden items-center gap-2 rounded-xl border border-border/80 bg-muted/40 px-3 py-2 md:flex focus-within:border-[#C9A04F]/60 focus-within:bg-muted/70 transition-all"
          >
            <Search size={16} className="text-muted-foreground" />

            <input
              type="text"
              placeholder="Search GYMCORE..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-40 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground"
            />
          </form>

          {/* Theme Toggle */}
          <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="rounded-xl border border-border/60 bg-muted/30 p-2 text-muted-foreground transition hover:bg-muted hover:text-[#C9A04F]"
            aria-label="Toggle theme"
            disabled={!mounted}
          >
            {mounted && isDark ? (
              <Sun size={18} />
            ) : (
              <Moon size={18} />
            )}
          </button>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="relative rounded-xl border border-border/60 bg-muted/30 p-2 text-muted-foreground transition hover:bg-muted hover:text-[#C9A04F]"
              aria-label="Notifications"
            >
              <Bell size={18} />
              {unreadNotifications && (
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-[#C9A04F] shadow-[0_0_6px_#C9A04F]" />
              )}
            </button>

            {notificationsOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setNotificationsOpen(false)}
                />
                <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-border bg-card p-3 shadow-xl">
                  <div className="flex items-center justify-between border-b border-border pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-foreground">Notifications</span>
                      {unreadNotifications && (
                        <span className="rounded-full bg-[#C9A04F]/20 px-1.5 py-0.5 text-[10px] font-semibold text-[#C9A04F]">
                          3 New
                        </span>
                      )}
                    </div>
                    {unreadNotifications && (
                      <button
                        onClick={() => setUnreadNotifications(false)}
                        className="text-[11px] text-muted-foreground transition hover:text-[#C9A04F]"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="mt-2 space-y-2">
                    <Link
                      href="/payments"
                      onClick={() => setNotificationsOpen(false)}
                      className="flex items-start gap-2.5 rounded-lg p-2 transition hover:bg-muted"
                    >
                      <div className="mt-0.5 rounded-md bg-amber-500/10 p-1 text-amber-500">
                        <AlertTriangle size={14} />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-foreground">Payment Overdue</p>
                        <p className="text-[11px] text-muted-foreground">
                          David Miller has ₹3,000 pending dues for Gold Annual.
                        </p>
                        <span className="text-[10px] text-muted-foreground/70">10m ago</span>
                      </div>
                    </Link>

                    <Link
                      href="/members"
                      onClick={() => setNotificationsOpen(false)}
                      className="flex items-start gap-2.5 rounded-lg p-2 transition hover:bg-muted"
                    >
                      <div className="mt-0.5 rounded-md bg-[#C9A04F]/10 p-1 text-[#C9A04F]">
                        <Clock size={14} />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-foreground">Expiring Memberships</p>
                        <p className="text-[11px] text-muted-foreground">
                          2 memberships expiring within the next 7 days.
                        </p>
                        <span className="text-[10px] text-muted-foreground/70">1h ago</span>
                      </div>
                    </Link>

                    <Link
                      href="/attendance"
                      onClick={() => setNotificationsOpen(false)}
                      className="flex items-start gap-2.5 rounded-lg p-2 transition hover:bg-muted"
                    >
                      <div className="mt-0.5 rounded-md bg-emerald-500/10 p-1 text-emerald-500">
                        <CheckCircle2 size={14} />
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-foreground">Attendance Active</p>
                        <p className="text-[11px] text-muted-foreground">
                          Gym floor currently operating at optimal check-in capacity.
                        </p>
                        <span className="text-[10px] text-muted-foreground/70">2h ago</span>
                      </div>
                    </Link>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Profile Menu */}
          <div className="relative">
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2.5 rounded-xl border border-border/60 bg-muted/30 p-1.5 pr-2.5 transition hover:bg-muted hover:border-[#C9A04F]/40"
              aria-label="User profile menu"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#C9A04F] text-xs font-bold text-black shadow-sm">
                A
              </div>

              <div className="hidden text-left sm:block">
                <p className="text-xs font-semibold text-foreground leading-tight">
                  Admin
                </p>

                <p className="text-[10px] text-muted-foreground leading-tight">
                  Manager
                </p>
              </div>

              <ChevronDown
                size={14}
                className="hidden text-muted-foreground sm:block"
              />
            </button>

            {/* Profile Dropdown */}
            {profileOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setProfileOpen(false)}
                />
                <div className="absolute right-0 top-full z-50 mt-2 w-48 rounded-xl border border-border bg-card p-1.5 shadow-lg">
                  <div className="border-b border-border px-3 py-2">
                    <p className="text-xs font-semibold text-foreground">Gymcore Admin</p>
                    <p className="text-[11px] text-muted-foreground">admin@gymcore.com</p>
                  </div>
                  <Link
                    href="/settings"
                    onClick={() => setProfileOpen(false)}
                    className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs text-foreground transition hover:bg-muted"
                  >
                    <UserCheck size={14} className="text-muted-foreground" />
                    <span>Admin Settings</span>
                  </Link>
                  <Link
                    href="/login"
                    onClick={() => {
                      clearStoredAuthTokens();
                      setProfileOpen(false);
                    }}
                    className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs text-red-500 transition hover:bg-red-500/10"
                  >
                    <LogOut size={14} />
                    <span>Sign Out</span>
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">

          {/* Background Overlay */}
          <div
            className="absolute inset-0 h-full w-full bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation menu"
          />

          {/* Sidebar */}
          <aside className="relative flex h-full w-72 max-w-[85%] flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-2xl">

            {/* Logo */}
            <div className="flex h-20 items-center justify-between border-b border-sidebar-border px-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#C9A04F] text-black">
                  <Dumbbell size={23} />
                </div>

                <div>
                  <h1 className="text-lg font-bold tracking-[0.2em]">
                    GYMCORE
                  </h1>

                  <p className="text-[10px] tracking-wider text-muted-foreground">
                    STRONGER BUSINESS
                  </p>
                </div>
              </div>

              <button
                onClick={() => setMenuOpen(false)}
                className="rounded-lg p-2 text-muted-foreground hover:bg-accent"
                aria-label="Close menu"
              >
                <X size={21} />
              </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1.5 px-4 py-6 overflow-y-auto">
              <p className="mb-4 px-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Main Menu
              </p>

              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href + "/"));

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className={`flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-[#C9A04F]/15 text-[#C9A04F]"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    }`}
                  >
                    <Icon size={19} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Settings */}
            <div className="border-t border-sidebar-border p-4">
              <Link
                href="/settings"
                onClick={() => setMenuOpen(false)}
                className={`flex items-center gap-3 rounded-lg px-3 py-3 text-sm transition-colors ${
                  pathname === "/settings"
                    ? "bg-[#C9A04F]/15 text-[#C9A04F]"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <Settings size={19} />
                <span>Settings</span>
              </Link>

              <p className="mt-4 px-3 text-[10px] text-muted-foreground">
                GYMCORE © 2026
              </p>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
