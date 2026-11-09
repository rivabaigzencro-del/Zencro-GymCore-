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
  UserCog,
  UserCheck,
  Building,
  Server,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMounted } from "@/lib/use-mounted";
import {
  setStoredAuthToken,
  setActiveSession,
  DEMO_ACCOUNTS,
  isDemoModeEnabled,
  setDemoModeEnabled,
  normalizeRole,
  api,
  type UserRole,
  type UserSession,
} from "@/lib/api-client";
import { logAuditAction } from "@/lib/mock-data";

export default function LoginPage() {
  const router = useRouter();
  const mounted = useMounted();
  const { resolvedTheme, setTheme } = useTheme();

  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState<UserRole>("Owner");
  const [email, setEmail] = useState("owner@gymcore.com");
  const [password, setPassword] = useState("owner123");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isForgotOpen, setIsForgotOpen] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(() => isDemoModeEnabled());

  const isDark = resolvedTheme === "dark";

  const handleToggleDemoMode = () => {
    const next = !isDemoMode;
    setIsDemoMode(next);
    setDemoModeEnabled(next);
    setErrorMsg("");
  };

  const handleSelectDemoRole = (role: UserRole) => {
    setSelectedRole(role);
    setErrorMsg("");
    if (role === "Owner") {
      setEmail("owner@gymcore.com");
      setPassword("owner123");
    } else if (role === "Manager") {
      setEmail("manager@gymcore.com");
      setPassword("manager123");
    } else if (role === "Front Desk") {
      setEmail("frontdesk@gymcore.com");
      setPassword("frontdesk123");
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setErrorMsg("Please enter both email address and password.");
      return;
    }

    setIsLoading(true);

    try {
      // 1. Primary: Authenticate against FastAPI backend endpoint (/api/v1/auth/login)
      const res = await api.auth.login({
        email: trimmedEmail,
        password: trimmedPassword,
      });

      if (res.success && res.data) {
        const { access_token, user } = res.data;
        setStoredAuthToken(access_token);
        const role = normalizeRole(user.role);
        const sessionUser: UserSession = {
          id: String(user.id),
          name: user.name || trimmedEmail.split("@")[0].toUpperCase(),
          email: user.email,
          role,
          title: `${role} User`,
          tenantId: String(user.tenant_id),
        };

        setActiveSession(sessionUser);

        logAuditAction({
          action: "SETTINGS_UPDATE",
          actionLabel: `${sessionUser.role} Signed In`,
          entityType: "System",
          entityId: sessionUser.id,
          entityName: sessionUser.name,
          performedBy: sessionUser.name,
          description: `${sessionUser.name} (${sessionUser.role}) signed into GYMCORE operations console via FastAPI backend.`,
          severity: "info",
        });

        router.push("/");
        return;
      }

      // 2. Demo fallback: only if demo mode is explicitly enabled
      if (isDemoMode || isDemoModeEnabled()) {
        const matchedDemo = DEMO_ACCOUNTS[trimmedEmail];
        if (matchedDemo && matchedDemo.password === trimmedPassword) {
          const sessionUser: UserSession = {
            id: matchedDemo.id,
            name: matchedDemo.name,
            email: matchedDemo.email,
            role: matchedDemo.role,
            title: matchedDemo.title,
          };

          setActiveSession(sessionUser);
          setStoredAuthToken(`gymcore_${sessionUser.role.toLowerCase().replace(/\s+/g, "_")}_jwt_active`, "gymcore_refresh_token_active");

          logAuditAction({
            action: "SETTINGS_UPDATE",
            actionLabel: `${sessionUser.role} Signed In (Demo)`,
            entityType: "System",
            entityId: sessionUser.id,
            entityName: sessionUser.name,
            performedBy: sessionUser.name,
            description: `${sessionUser.name} (${sessionUser.role}) signed into GYMCORE in Demo mode.`,
            severity: "info",
          });

          router.push("/");
          return;
        }
      }

      setErrorMsg(res.error || "Authentication failed. Invalid email or password.");
    } catch (err: unknown) {
      setErrorMsg((err as Error)?.message || "Network error while connecting to FastAPI backend.");
    } finally {
      setIsLoading(false);
    }
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
        <div className="mb-6 flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#C9A04F] text-black shadow-[0_0_20px_rgba(201,160,79,0.3)]">
            <Dumbbell size={30} />
          </div>

          <h1 className="text-3xl font-bold tracking-widest text-foreground">
            GYMCORE
          </h1>

          <p className="mt-1 text-xs font-semibold tracking-wider text-[#C9A04F]">
            STRONGER BUSINESS • HEALTHIER COMMUNITY
          </p>
        </div>

        {/* Login Card */}
        <div className="relative rounded-2xl border border-border/80 bg-card/95 backdrop-blur-md p-6 sm:p-8 shadow-2xl overflow-hidden">
          {/* Subtle top gold accent bar */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#C9A04F] to-transparent" />

          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              Welcome back
            </h2>
            <button
              type="button"
              onClick={handleToggleDemoMode}
              className={`text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded-md border transition-all ${
                isDemoMode
                  ? "border-[#C9A04F] bg-[#C9A04F]/20 text-[#C9A04F]"
                  : "border-border/60 bg-muted/40 text-muted-foreground hover:text-foreground"
              }`}
            >
              {isDemoMode ? "Demo Mode ON" : "Demo Mode OFF"}
            </button>
          </div>

          <p className="mt-1 text-xs text-muted-foreground">
            {isDemoMode
              ? "Demo mode is active for client-side evaluation without a running backend."
              : "Sign in using your registered FastAPI backend credentials."}
          </p>

          {/* Role Switcher Presets when Demo Mode is Active */}
          {isDemoMode && (
            <div className="mt-5">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-2">
                Select Demo Persona
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["Owner", "Manager", "Front Desk"] as UserRole[]).map((role) => {
                  const isSelected = selectedRole === role;
                  return (
                    <button
                      key={role}
                      type="button"
                      onClick={() => handleSelectDemoRole(role)}
                      className={`flex flex-col items-center justify-center p-2.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                        isSelected
                          ? "border-[#C9A04F] bg-[#C9A04F]/15 text-[#C9A04F] shadow-[0_0_12px_rgba(201,160,79,0.2)]"
                          : "border-border/70 bg-muted/30 text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                      }`}
                    >
                      {role === "Owner" && <Building size={16} className="mb-1" />}
                      {role === "Manager" && <UserCog size={16} className="mb-1" />}
                      {role === "Front Desk" && <UserCheck size={16} className="mb-1" />}
                      <span>{role}</span>
                    </button>
                  );
                })}
              </div>

              {/* Role Permissions Preview */}
              <div className="mt-2.5 rounded-lg bg-muted/40 p-2 text-[11px] text-muted-foreground border border-border/50">
                {selectedRole === "Owner" && (
                  <span>👑 <strong>Owner:</strong> Full administrative access across all modules, settings, staff, and financial reports.</span>
                )}
                {selectedRole === "Manager" && (
                  <span>💼 <strong>Manager:</strong> Operational control over members, attendance, plans, and payments. Restricted from staff deletion & gym ownership settings.</span>
                )}
                {selectedRole === "Front Desk" && (
                  <span>📋 <strong>Front Desk:</strong> Daily operations: member registration, membership assignment, payment collection, receipts, and attendance.</span>
                )}
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
              <AlertCircle size={15} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form noValidate onSubmit={handleLogin} className="mt-5 space-y-4">
            {/* Email */}
            <div className="space-y-1.5">
              <label htmlFor="login-email" className="text-xs font-semibold text-foreground">
                Email address
              </label>

              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={17} />

                <Input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errorMsg) setErrorMsg("");
                  }}
                  placeholder="name@gymcore.com"
                  className="pl-10 rounded-xl border-border/80 bg-muted/40 focus:border-[#C9A04F]"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="text-xs font-semibold text-foreground">
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
                  id="login-password"
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

          {/* Backend Info Notice */}
          <div className="mt-5 rounded-xl border border-border/60 bg-muted/30 p-3 text-[11px] text-muted-foreground leading-relaxed flex items-start gap-2">
            <Server size={14} className="shrink-0 text-[#C9A04F] mt-0.5" />
            <span>
              Connected to FastAPI backend at <code>http://localhost:8000/api/v1</code>. JWT authentication, tenant isolation & RBAC are enforced on every request.
            </span>
          </div>
        </div>

        <p className="text-center text-[#9B968C] text-xs mt-6">
          GymCore &copy; 2026 • Stronger Business. Healthier Community.
        </p>
      </div>

      {/* Forgot Password Modal */}
      {isForgotOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-xs"
            onClick={() => setIsForgotOpen(false)}
          />

          <div className="relative w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
                <HelpCircle size={17} className="text-[#C9A04F]" />
                <span>Password Recovery</span>
              </div>
              <button
                type="button"
                onClick={() => setIsForgotOpen(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close modal"
              >
                <X size={17} />
              </button>
            </div>

            <div className="py-4 space-y-3 text-xs text-muted-foreground leading-relaxed">
              <p>
                In standalone demo mode, password resets are managed locally. You can sign in using any of the preset demo roles:
              </p>
              <div className="space-y-1.5 font-mono text-[11px] rounded-lg bg-muted p-2.5 border border-border/60">
                <p>• Owner: <span className="text-[#C9A04F]">owner@gymcore.com</span> / owner123</p>
                <p>• Manager: <span className="text-[#C9A04F]">manager@gymcore.com</span> / manager123</p>
                <p>• Front Desk: <span className="text-[#C9A04F]">frontdesk@gymcore.com</span> / frontdesk123</p>
              </div>
              <p className="text-[11px] text-muted-foreground/80">
                In production, password reset requests generate a secure time-limited token delivered via SMTP.
              </p>
            </div>

            <Button
              type="button"
              onClick={() => setIsForgotOpen(false)}
              className="w-full rounded-xl bg-[#C9A04F] font-semibold text-black hover:bg-[#b68d3e]"
            >
              Understood
            </Button>
          </div>
        </div>
      )}
    </main>
  );
}
