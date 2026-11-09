"use client";

import { Suspense } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  Users,
  CreditCard,
  Wallet,
  CalendarCheck,
  UserCog,
  BarChart3,
  Settings,
  Dumbbell,
  ShieldCheck,
  Lock,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { useSessionStore } from "@/lib/use-session-store";
import { useMounted } from "@/lib/use-mounted";

const navigation = [
  { name: "Overview", icon: LayoutDashboard, href: "/", frontDeskAllowed: true },
  { name: "Members", icon: Users, href: "/members", frontDeskAllowed: true },
  { name: "Memberships", icon: CreditCard, href: "/memberships", frontDeskAllowed: true },
  { name: "Payments", icon: Wallet, href: "/payments", frontDeskAllowed: true },
  { name: "Attendance", icon: CalendarCheck, href: "/attendance", frontDeskAllowed: true },
  { name: "Staff", icon: UserCog, href: "/staff", frontDeskAllowed: false },
  { name: "Reports", icon: BarChart3, href: "/reports", frontDeskAllowed: false },
  { name: "Audit Logs", icon: ShieldCheck, href: "/audit", frontDeskAllowed: false },
];

export function Sidebar() {
  return (
    <Suspense
      fallback={
        <aside className="hidden h-screen w-64 shrink-0 border-r border-border bg-sidebar lg:block" />
      }
    >
      <SidebarContent />
    </Suspense>
  );
}

function SidebarContent() {
  const pathname = usePathname();
  const isSettingsActive = pathname.startsWith("/settings");

  const session = useSessionStore();
  const mounted = useMounted();

  const isFrontDesk = session?.role === "Front Desk";

  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground lg:sticky lg:top-0 lg:flex z-20">
      {/* Logo */}
      <div className="flex h-20 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#C9A04F] text-black shadow-[0_0_15px_rgba(201,160,79,0.25)]">
          <Dumbbell size={22} className="stroke-[2.2]" />
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-[0.2em] text-foreground">
            GYMCORE
          </h1>
          <p className="text-[10px] tracking-wider text-[#C9A04F] font-semibold">
            STRONGER BUSINESS
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1.5 px-3 py-5 overflow-y-auto">
        <div className="mb-3 px-3 flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/80">
            Main Menu
          </span>
          <span className="rounded bg-[#C9A04F]/15 px-1.5 py-0.5 text-[9px] font-bold text-[#C9A04F]">
            {mounted && session?.role ? session.role : "Console"}
          </span>
        </div>

        {navigation.map((item) => {
          const Icon = item.icon;
          const isRestricted = isFrontDesk && !item.frontDeskAllowed;

          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href + "/"));

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-all duration-150 ${
                isActive
                  ? "bg-[#C9A04F]/15 text-[#C9A04F] font-semibold border-l-[3px] border-[#C9A04F]"
                  : isRestricted
                  ? "text-muted-foreground/60 hover:bg-muted/30 hover:text-muted-foreground"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  size={18}
                  className={
                    isActive
                      ? "text-[#C9A04F]"
                      : isRestricted
                      ? "text-muted-foreground/50"
                      : "text-muted-foreground"
                  }
                />
                <span>{item.name}</span>
              </div>
              {isRestricted && (
                <span title="Restricted for Front Desk role">
                  <Lock size={12} className="text-amber-500/70" />
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Settings & Footer */}
      <div className="border-t border-sidebar-border p-3 space-y-2">
        <Link
          href="/settings"
          className={`flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-all duration-150 ${
            isSettingsActive
              ? "bg-[#C9A04F]/15 text-[#C9A04F] font-semibold border-l-[3px] border-[#C9A04F]"
              : isFrontDesk
              ? "text-muted-foreground/60 hover:bg-muted/30 hover:text-muted-foreground"
              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
          }`}
        >
          <div className="flex items-center gap-3">
            <Settings
              size={18}
              className={
                isSettingsActive
                  ? "text-[#C9A04F]"
                  : isFrontDesk
                  ? "text-muted-foreground/50"
                  : "text-muted-foreground"
              }
            />
            <span>Settings</span>
          </div>
          {isFrontDesk && (
            <span title="Settings restricted for Front Desk role">
              <Lock size={12} className="text-amber-500/70" />
            </span>
          )}
        </Link>

        {/* User Session Profile Card */}
        <div className="rounded-xl border border-border/60 bg-muted/20 p-2.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-foreground truncate max-w-[120px]">
              {mounted && (session?.name || session?.email) ? (session?.name || session?.email) : "Gym Staff"}
            </span>
            <span className="text-[10px] font-bold text-[#C9A04F]">
              {mounted && session?.role ? session.role : "Staff"}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
