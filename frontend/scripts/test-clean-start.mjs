import assert from "node:assert";

const storage = new Map();
global.localStorage = {
  getItem: (k) => storage.get(k) ?? null,
  setItem: (k, v) => storage.set(k, String(v)),
  removeItem: (k) => storage.delete(k),
  clear: () => storage.clear(),
};
global.window = {};
delete process.env.NEXT_PUBLIC_ENABLE_DEMO;

const {
  getStoredMembers,
  getStoredPlans,
  getStoredPayments,
  getStoredAttendance,
  getStoredDues,
  getStoredStaff,
  getStoredSettings,
} = await import("../lib/mock-data.ts");
const { getStoredAuditLogs } = await import("../lib/audit-trail.ts");
const { getActiveSession, isDemoModeEnabled } = await import("../lib/api-client.ts");

console.log("=== VERIFYING PRODUCTION CLEAN START ===");

// 1. Demo mode is disabled
assert.strictEqual(isDemoModeEnabled(), false, "Demo mode must be false by default");
console.log("✓ Demo mode is disabled by default");

// 2. Initial collections are completely empty
assert.strictEqual(getStoredMembers().length, 0, "Members must start with 0");
assert.strictEqual(getStoredPlans().length, 0, "Plans must start with 0");
assert.strictEqual(getStoredPayments().length, 0, "Payments must start with 0");
assert.strictEqual(getStoredAttendance().length, 0, "Attendance must start with 0");
assert.strictEqual(getStoredDues().length, 0, "Dues must start with 0");
assert.strictEqual(getStoredStaff().length, 0, "Staff must start with 0");
assert.strictEqual(getStoredAuditLogs().length, 0, "Audit logs must start with 0");
console.log("✓ All collections start at exactly 0 (clean workspace)");

// 3. Settings are clean defaults
const settings = getStoredSettings();
assert.strictEqual(settings.gymName, "My Gym");
assert.strictEqual(settings.phone, "");
assert.strictEqual(settings.email, "");
assert.strictEqual(settings.address, "");
console.log("✓ Clean settings default template verified");

// 4. Session is null (no auto demo login)
assert.strictEqual(getActiveSession(), null, "Active session must be null when unauthenticated");
console.log("✓ No automatic demo login verified");

console.log("\n=== ALL PRODUCTION CLEAN START CHECKS PASSED ===");

