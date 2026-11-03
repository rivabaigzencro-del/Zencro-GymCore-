"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard/members", label: "Members", icon: "👥" },
  { href: "/dashboard/plans", label: "Membership Plans", icon: "📋" },
  { href: "/dashboard/memberships", label: "Memberships", icon: "🎟️" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080808]">
        <div className="w-8 h-8 border-2 border-[#D4A84F] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#080808]">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-[#111111] border-r border-[#1E1E1E] flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-[#1E1E1E]">
          <h1 className="text-2xl font-bold">
            <span className="text-[#D4A84F]">GYM</span>
            <span className="text-white">CORE</span>
          </h1>
          <p className="text-[#9B968C] text-xs mt-1 truncate">{user.name}</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map(({ href, label, icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-[#D4A84F]/15 text-[#D4A84F] border border-[#D4A84F]/20"
                    : "text-[#9B968C] hover:bg-[#1D1D1D] hover:text-white"
                }`}
              >
                <span>{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-[#1E1E1E]">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-[#D4A84F]/20 flex items-center justify-center text-[#D4A84F] text-sm font-semibold">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.name}</p>
              <p className="text-xs text-[#9B968C]">{user.role}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full text-sm text-[#9B968C] hover:text-red-400 py-1.5 text-left transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

