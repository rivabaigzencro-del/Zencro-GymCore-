"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import {
  Dumbbell,
  Eye,
  EyeOff,
  Lock,
  Mail,
  Sun,
  Moon,
  AlertCircle,
  HelpCircle,
  X,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMounted } from "@/lib/use-mounted";
import { setStoredAuthToken } from "@/lib/api-client";
import { logAuditAction } from "@/lib/mock-data";

export default function LoginPage() {
  const router = useRouter();
  const mounted = useMounted();
  const { resolvedTheme, setTheme } = useTheme();

  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("admin@gymcore.com");
  const [password, setPassword] = useState("admin123");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isForgotOpen, setIsForgotOpen] = useState(false);

  const isDark = resolvedTheme === "dark";

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!email.trim() || !password.trim()) {
      setErrorMsg("Please enter both email address and password.");
      return;
    }

    setIsLoading(true);

    setTimeout(() => {
      // Store session token
      setStoredAuthToken("gymcore_admin_session_jwt_active", "gymcore_refresh_token_active");

      // Audit log the login
      logAuditAction({
        action: "SETTINGS_UPDATE",
        actionLabel: "Administrator Signed In",
        entityType: "System",
        entityId: "AUTH-SESSION",
        entityName: email.trim(),
        performedBy: email.trim(),
        description: `Administrator ${email.trim()} signed into GYMCORE operations console.`,
        severity: "info",
      });

      router.push("/");
    }, 350);
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-background px-4 py-10 text-foreground">
      {/* Theme Toggle */}
      <button
        type="button"
        onClick={() => setTheme(isDark ? "light" : "dark")}
        className="absolute right-6 top-6 flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card text-foreground transition-colors hover:bg-muted"
        aria-label="Toggle theme"
      >
        {mounted && (isDark ? <Sun size={19} /> : <Moon size={19} />)}
      </button>

      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#C9A04F] text-black shadow-[0_0_20px_rgba(201,160,79,0.3)]">
            <Dumbbell size={30} />
          </div>

          <h1 className="text-3xl font-bold tracking-widest text-foreground">
            GYMCORE
          </h1>

          <p className="mt-2 text-xs font-semibold tracking-wider text-[#C9A04F]">
            STRONGER BUSINESS • HEALTHIER COMMUNITY
          </p>
        </div>

        {/* Login Card */}
        <div className="relative rounded-2xl border border-border/80 bg-card/95 backdrop-blur-md p-8 shadow-2xl overflow-hidden">
          {/* Subtle top gold accent bar */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#C9A04F] to-transparent" />

          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            Welcome back
          </h2>

          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to manage your fitness center operations.
          </p>

          {errorMsg && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
              <AlertCircle size={15} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form noValidate onSubmit={handleLogin} className="mt-6 space-y-4">
            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Email address
              </label>

              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={17} />

                <Input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errorMsg) setErrorMsg("");
                  }}
                  placeholder="admin@gymcore.com"
                  className="pl-10 rounded-xl border-border/80 bg-muted/40 focus:border-[#C9A04F]"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setIsForgotOpen(true)}
                  className="text-[11px] text-[#C9A04F] hover:underline cursor-pointer bg-transparent border-none p-0"
                >
                  Forgot password?
                </button>
              </div>

              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={17} />

                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errorMsg) setErrorMsg("");
                  }}
                  placeholder="Enter your password"
                  className="pl-10 pr-10 rounded-xl border-border/80 bg-muted/40 focus:border-[#C9A04F]"
                  required
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            {/* Sign In */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 rounded-xl bg-[#C9A04F] font-bold text-black hover:bg-[#b68d3e] shadow-[0_0_20px_rgba(201,160,79,0.25)] h-11"
            >
              {isLoading ? "Signing in..." : "Sign In to GYMCORE"}
            </Button>
          </form>

          {/* Quick Demo Credentials Banner */}
          <div className="mt-6 rounded-xl border border-border/60 bg-muted/30 p-3 text-center text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">Demo Credentials: </span>
            <span className="font-mono text-[#C9A04F]">admin@gymcore.com</span> /{" "}
            <span className="font-mono text-[#C9A04F]">admin123</span>
          </div>

          <p className="mt-5 text-center text-[11px] text-muted-foreground">
            GYMCORE © 2026. All rights reserved.
          </p>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {isForgotOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <div className="rounded-lg bg-[#C9A04F]/10 p-2 text-[#C9A04F]">
                  <HelpCircle size={18} />
                </div>
                <h3 className="text-sm font-bold text-foreground">Password Recovery</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsForgotOpen(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs text-muted-foreground">
              <p>
                Administrative access in GYMCORE requires verified identity protocols.
              </p>
              <div className="rounded-xl border border-border bg-background p-3 text-foreground font-medium">
                <div className="flex items-center gap-1.5 text-[#C9A04F] font-bold mb-1">
                  <ShieldCheck size={14} />
                  <span>Admin Recovery Protocol</span>
                </div>
                Contact your gym super-administrator or IT desk supervisor to issue a temporary access link.
              </div>
              <p className="text-[11px]">
                Demo master credentials remain: <span className="font-mono text-[#C9A04F]">admin123</span>
              </p>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={() => setIsForgotOpen(false)}
                className="rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black hover:bg-[#b68d3e]"
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
