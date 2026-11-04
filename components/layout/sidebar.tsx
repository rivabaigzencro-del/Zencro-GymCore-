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
} from "lucide-react";
import { usePathname } from "next/navigation";

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
      <nav className="flex-1 space-y-1.5 px-3 py-6 overflow-y-auto">
        <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/80">
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
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 ${
                isActive
                  ? "bg-[#C9A04F]/15 text-[#C9A04F] font-semibold border-l-[3px] border-[#C9A04F]"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              }`}
            >
              <Icon size={18} className={isActive ? "text-[#C9A04F]" : "text-muted-foreground"} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Settings & Footer */}
      <div className="border-t border-sidebar-border p-3 space-y-2">
        <Link
          href="/settings"
          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-150 ${
            isSettingsActive
              ? "bg-[#C9A04F]/15 text-[#C9A04F] font-semibold border-l-[3px] border-[#C9A04F]"
              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
          }`}
        >
          <Settings size={18} className={isSettingsActive ? "text-[#C9A04F]" : "text-muted-foreground"} />
          <span>Settings</span>
        </Link>

        <div className="px-3 pt-2 pb-1 flex items-center justify-between text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] tracking-wide font-medium">SYSTEM ACTIVE</span>
          </div>
          <span className="text-[10px] opacity-70">v1.0</span>
        </div>
      </div>
    </aside>
  );
}
