"use client";

import { useState } from "react";
import {
  Building,
  Clock,
  IndianRupee,
  Bell,
  User,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Lock,
} from "lucide-react";
import {
  type GymSettings,
  saveSettings,
  resetSettingsToDefault,
} from "@/lib/mock-data";
import { useSettingsStore } from "@/lib/use-settings-store";

export function SettingsView() {
  const currentSettings = useSettingsStore();

  const [activeTab, setActiveTab] = useState<
    "profile" | "hours" | "business" | "notifications" | "account"
  >("profile");

  // Form state
  const [formData, setFormData] = useState<GymSettings>({ ...currentSettings });
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);

  // Security password state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");

  // Toast
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const showNotification = (message: string, type: "success" | "error" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4500);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();

    // Check password if filled
    if (newPassword || confirmPassword) {
      if (newPassword.length < 6) {
        setPasswordError("New password must be at least 6 characters.");
        return;
      }
      if (newPassword !== confirmPassword) {
        setPasswordError("New passwords do not match.");
        return;
      }
      setPasswordError("");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    }

    saveSettings(formData);
    showNotification("Settings saved and updated successfully!");
  };

  const handleReset = () => {
    const defaults = resetSettingsToDefault();
    setFormData({ ...defaults });
    setIsResetConfirmOpen(false);
    showNotification("Settings restored to factory defaults.");
  };

  return (
    <div className="space-y-8">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`flex items-center gap-2.5 rounded-xl border p-4 text-sm font-medium animate-in fade-in slide-in-from-top-2 ${
            notification.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
              : "border-red-500/30 bg-red-500/15 text-red-400"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 size={18} className="shrink-0" />
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
              <span>System Preferences</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              System Settings & Configuration
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Customize your fitness club identity, operating timings, invoice preferences, alert
              notifications, and administrative access.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setIsResetConfirmOpen(true)}
              className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-4 py-2.5 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <RotateCcw size={14} />
              <span>Reset Defaults</span>
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-1.5 rounded-xl bg-[#C9A04F] px-5 py-2.5 text-xs font-bold text-black transition-all hover:bg-[#b68d3e] shadow-lg shadow-[#C9A04F]/10"
            >
              <Save size={14} />
              <span>Save Changes</span>
            </button>
          </div>
        </div>
      </div>

      {/* Settings Navigation Tabs */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Left Sidebar Nav */}
        <div className="space-y-1 rounded-2xl border border-border bg-card p-3 shadow-sm lg:col-span-1">
          <button
            onClick={() => setActiveTab("profile")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "profile"
                ? "bg-[#C9A04F] text-black"
                : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            }`}
          >
            <Building size={18} />
            <span>Gym Profile</span>
          </button>

          <button
            onClick={() => setActiveTab("hours")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "hours"
                ? "bg-[#C9A04F] text-black"
                : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            }`}
          >
            <Clock size={18} />
            <span>Operating Hours</span>
          </button>

          <button
            onClick={() => setActiveTab("business")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "business"
                ? "bg-[#C9A04F] text-black"
                : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            }`}
          >
            <IndianRupee size={18} />
            <span>Business Preferences</span>
          </button>

          <button
            onClick={() => setActiveTab("notifications")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "notifications"
                ? "bg-[#C9A04F] text-black"
                : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            }`}
          >
            <Bell size={18} />
            <span>Notifications</span>
          </button>

          <button
            onClick={() => setActiveTab("account")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "account"
                ? "bg-[#C9A04F] text-black"
                : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            }`}
          >
            <User size={18} />
            <span>Admin & Security</span>
          </button>
        </div>

        {/* Right Form Panels */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm lg:col-span-3">
          <form onSubmit={handleSave} className="space-y-6">
            {/* Tab 1: Gym Profile */}
            {activeTab === "profile" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-foreground">Club Identity & Location</h2>
                  <p className="text-xs text-muted-foreground">
                    This branding appears on member receipts, agreements, and invoices
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Gym Name
                    </label>
                    <input
                      type="text"
                      value={formData.gymName}
                      onChange={(e) => setFormData({ ...formData, gymName: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Tagline / Slogan
                    </label>
                    <input
                      type="text"
                      value={formData.tagline}
                      onChange={(e) => setFormData({ ...formData, tagline: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Official Phone
                    </label>
                    <input
                      type="text"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Support Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Physical Facility Address
                  </label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      City
                    </label>
                    <input
                      type="text"
                      value={formData.city}
                      onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Postal / PIN Code
                    </label>
                    <input
                      type="text"
                      value={formData.postalCode}
                      onChange={(e) => setFormData({ ...formData, postalCode: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Website URL
                    </label>
                    <input
                      type="text"
                      value={formData.website}
                      onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: Operating Hours */}
            {activeTab === "hours" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-foreground">Facility Operating Timings</h2>
                  <p className="text-xs text-muted-foreground">
                    Configure daily check-in access periods and peak hours advisories
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Weekday Hours (Mon - Fri)
                    </label>
                    <input
                      type="text"
                      value={formData.weekdayHours}
                      onChange={(e) => setFormData({ ...formData, weekdayHours: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                    <p className="mt-1 text-[11px] text-muted-foreground">e.g. 06:00 AM - 10:00 PM</p>
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Weekend Hours (Sat - Sun)
                    </label>
                    <input
                      type="text"
                      value={formData.weekendHours}
                      onChange={(e) => setFormData({ ...formData, weekendHours: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                    <p className="mt-1 text-[11px] text-muted-foreground">e.g. 07:00 AM - 08:00 PM</p>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Peak Hours Schedule Advisory
                  </label>
                  <input
                    type="text"
                    value={formData.peakHours}
                    onChange={(e) => setFormData({ ...formData, peakHours: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                  />
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Displayed on attendance dashboard and member app for floor load balancing
                  </p>
                </div>
              </div>
            )}

            {/* Tab 3: Business Preferences */}
            {activeTab === "business" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-foreground">Billing & Currency Settings</h2>
                  <p className="text-xs text-muted-foreground">
                    Configure currency symbols, tax rates, and sequential ID prefixes
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Default Currency
                    </label>
                    <input
                      type="text"
                      disabled
                      value={formData.currency}
                      className="mt-1 w-full rounded-xl border border-border bg-background/50 px-3.5 py-2.5 text-sm text-foreground cursor-not-allowed opacity-80"
                    />
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Default currency is set to Indian Rupee (₹)
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      GST / Tax Percentage (%)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={40}
                      value={formData.taxGstPercent}
                      onChange={(e) =>
                        setFormData({ ...formData, taxGstPercent: Number(e.target.value) })
                      }
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Standard fitness facility GST rate in India is 18%
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Invoice Prefix
                    </label>
                    <input
                      type="text"
                      value={formData.invoicePrefix}
                      onChange={(e) =>
                        setFormData({ ...formData, invoicePrefix: e.target.value })
                      }
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Member ID Prefix
                    </label>
                    <input
                      type="text"
                      value={formData.memberIdPrefix}
                      onChange={(e) =>
                        setFormData({ ...formData, memberIdPrefix: e.target.value })
                      }
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                </div>

                {/* Teammate Riva Backend Note */}
                <div className="rounded-xl border border-[#C9A04F]/30 bg-[#C9A04F]/5 p-4 text-xs">
                  <div className="flex items-center gap-2 font-semibold text-[#C9A04F]">
                    <Sparkles size={14} />
                    <span>Backend Synchronization Notice</span>
                  </div>
                  <p className="mt-1 text-muted-foreground">
                    Frontend is currently persisting data to your browser&apos;s local storage.
                    Teammate Riva is building the FastAPI + PostgreSQL backend. Once ready, this
                    panel will provide the API Endpoint URL and JWT Auth Token configuration.
                  </p>
                </div>
              </div>
            )}

            {/* Tab 4: Notifications */}
            {activeTab === "notifications" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-foreground">Notification Preferences</h2>
                  <p className="text-xs text-muted-foreground">
                    Manage automated member alert triggers and daily admin reports
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-4">
                    <div>
                      <div className="text-sm font-semibold text-foreground">
                        Membership Expiry Alert (7 Days Prior)
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Automatically notify members 7 days before their membership plan expires
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.expiryAlert7Days}
                      onChange={(e) =>
                        setFormData({ ...formData, expiryAlert7Days: e.target.checked })
                      }
                      className="h-4 w-4 accent-[#C9A04F]"
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-4">
                    <div>
                      <div className="text-sm font-semibold text-foreground">
                        Urgent Expiry Warning (1 Day Prior)
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Send final SMS / Email reminder 24 hours before access expires
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.expiryAlert1Day}
                      onChange={(e) =>
                        setFormData({ ...formData, expiryAlert1Day: e.target.checked })
                      }
                      className="h-4 w-4 accent-[#C9A04F]"
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-4">
                    <div>
                      <div className="text-sm font-semibold text-foreground">
                        Auto-Email Payment Receipt
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Instantly send PDF receipt when a fee collection is recorded
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.autoEmailReceipt}
                      onChange={(e) =>
                        setFormData({ ...formData, autoEmailReceipt: e.target.checked })
                      }
                      className="h-4 w-4 accent-[#C9A04F]"
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-border bg-background/50 p-4">
                    <div>
                      <div className="text-sm font-semibold text-foreground">
                        Daily Attendance Summary
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Send daily check-in summary to the administrator email every night
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={formData.dailySummaryReport}
                      onChange={(e) =>
                        setFormData({ ...formData, dailySummaryReport: e.target.checked })
                      }
                      className="h-4 w-4 accent-[#C9A04F]"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Tab 5: Admin & Security */}
            {activeTab === "account" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-foreground">Administrator Profile & Security</h2>
                  <p className="text-xs text-muted-foreground">
                    Manage administrative credentials and system security
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Admin Name
                    </label>
                    <input
                      type="text"
                      value={formData.adminName}
                      onChange={(e) => setFormData({ ...formData, adminName: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Admin Email
                    </label>
                    <input
                      type="email"
                      value={formData.adminEmail}
                      onChange={(e) => setFormData({ ...formData, adminEmail: e.target.value })}
                      className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-muted-foreground">Account Role:</span>
                  <span className="rounded-full border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-2.5 py-0.5 text-xs font-bold text-[#C9A04F]">
                    {formData.adminRole}
                  </span>
                </div>

                {/* Change Password */}
                <div className="border-t border-border pt-4 space-y-4">
                  <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <Lock size={16} className="text-[#C9A04F]" />
                    <span>Change Admin Password</span>
                  </h3>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div>
                      <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Current Password
                      </label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        New Password
                      </label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground focus:border-[#C9A04F] focus:outline-none"
                      />
                    </div>
                  </div>

                  {passwordError && (
                    <p className="text-xs text-red-400 font-medium">{passwordError}</p>
                  )}
                </div>
              </div>
            )}

            {/* Bottom Actions */}
            <div className="flex items-center justify-end gap-3 border-t border-border pt-5">
              <button
                type="button"
                onClick={() => setFormData({ ...currentSettings })}
                className="rounded-xl border border-border bg-background px-4 py-2.5 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                Discard Changes
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 rounded-xl bg-[#C9A04F] px-5 py-2.5 text-xs font-bold text-black transition-all hover:bg-[#b68d3e]"
              >
                <Save size={14} />
                <span>Save Settings</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Reset Confirmation Dialog */}
      {isResetConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-[#C9A04F]">
              <AlertCircle size={24} />
              <h2 className="text-lg font-bold text-foreground">Reset All Settings?</h2>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Are you sure you want to restore GYMCORE settings to factory defaults? All custom
              timings, contact details, and preferences will be reset.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setIsResetConfirmOpen(false)}
                className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReset}
                className="rounded-xl bg-[#C9A04F] px-4 py-2 text-sm font-bold text-black hover:bg-[#b68d3e] transition-colors"
              >
                Confirm Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
