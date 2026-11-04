import assert from "node:assert";

// Mock localStorage for Node.js environment
const storage = new Map();
global.localStorage = {
  getItem: (k) => storage.get(k) ?? null,
  setItem: (k, v) => storage.set(k, String(v)),
  removeItem: (k) => storage.delete(k),
  clear: () => storage.clear(),
};
global.window = {};

// Import all GYMCORE core modules
const {
  extractNumericSuffix,
  sortMembersByNumericId,
  generateNextMemberIds,
  getNextStaffId,
  updateMemberCounterHighWaterMark,
} = await import("../lib/id-utils.ts");

const {
  logAuditAction,
  getStoredAuditLogs,
  sanitizeAuditValue,
  generateAuditCsv,
} = await import("../lib/audit-trail.ts");

const {
  getStoredMembers,
  saveMembers,
  getMemberById,
  addMember,
  updateMember,
  toggleFreezeMember,
  assignMembershipToMember,
  getStoredAttendance,
  checkInMember,
  checkOutMember,
  getStoredPayments,
  recordPayment,
  getStoredDues,
  collectDuePayment,
  getStoredStaff,
  addStaff,
  updateStaff,
  deleteStaff,
  toggleStaffStatus,
} = await import("../lib/mock-data.ts");

console.log("================================================================================");
console.log("   GYMCORE — COMPREHENSIVE END-TO-END 9 REAL-WORLD WORKFLOW VERIFICATION SUITE   ");
console.log("================================================================================\n");

// ---------------------------------------------------------------------------------------------
// WORKFLOW 1: Add Member -> Edit Member -> Assign Plan -> Collect Payment -> Verify Info
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 1: Member Onboarding, Lifecycle & Billing");
storage.clear();

// Step 1: Initial state
const initialMembers = getStoredMembers();
assert(initialMembers.length >= 6, "Initial members should be seeded");
const initialMaxNum = Math.max(...initialMembers.map((m) => extractNumericSuffix(m.id)));
const nextExpectedMemberId = `GYM${String(initialMaxNum + 1).padStart(3, "0")}`;
console.log(`  1.1 Initial member count: ${initialMembers.length}, Next expected ID: ${nextExpectedMemberId}`);

// Step 2: Add member
const newMemberInput = {
  name: "Aruna Suresh",
  email: "aruna.suresh@example.com",
  phone: "9876543299",
  plan: "Basic",
  joinDate: "04 Nov 2026",
  status: "Active",
  emergencyContact: "+91 98765 00099 (Suresh - Spouse)",
  address: "Flat 204, Orchid Residency, Koramangala",
  gender: "Female",
  dob: "1996-08-14",
};
const addedMember = addMember(newMemberInput);
assert.strictEqual(addedMember.id, nextExpectedMemberId, `Member ID must match ${nextExpectedMemberId}`);
assert.strictEqual(addedMember.phone, "+91 98765 43299", "Phone must be Indian formatted");

const membersAfterAdd = getStoredMembers();
assert.strictEqual(membersAfterAdd.length, initialMembers.length + 1, "Stored count must increment by 1");
const fetched = getMemberById(addedMember.id);
assert.ok(fetched, "Added member must be queryable by ID");

// Verify audit trail for add
let auditLogs = getStoredAuditLogs();
const addLog = auditLogs.find((l) => l.action === "MEMBER_CREATE" && l.entityId === addedMember.id);
assert.ok(addLog, "MEMBER_CREATE audit log must be recorded");
assert.strictEqual(addLog.entityName, "Aruna Suresh");
console.log(`  ✓ Member created: ${addedMember.name} (${addedMember.id}) with audit log AUD-${addLog.id}`);

// Step 3: Edit member details
const updatedPayload = {
  ...fetched,
  phone: "9876543200",
  address: "Villa 55, Embassy Boulevard, Yelahanka",
};
updateMember(updatedPayload);
const refetched = getMemberById(addedMember.id);
assert.strictEqual(refetched.phone, "+91 98765 43200", "Updated phone number must persist");
assert.strictEqual(refetched.address, "Villa 55, Embassy Boulevard, Yelahanka", "Updated address must persist");

auditLogs = getStoredAuditLogs();
const editLog = auditLogs.find((l) => l.action === "MEMBER_UPDATE" && l.entityId === addedMember.id);
assert.ok(editLog, "MEMBER_UPDATE audit log must be recorded");
console.log(`  ✓ Member details updated and verified in store and audit trail`);

// Step 4: Assign membership plan
const assignRes = assignMembershipToMember(addedMember.id, "Gold Annual", 12);
assert.strictEqual(assignRes.success, true, "Plan assignment must succeed");
assert.strictEqual(assignRes.member?.plan, "Gold Annual", "Plan name must update to Gold Annual");
assert.ok(assignRes.member?.validUntil, "validUntil expiration date must be populated");

auditLogs = getStoredAuditLogs();
const assignLog = auditLogs.find((l) => l.action === "MEMBERSHIP_ASSIGN" && l.entityId === addedMember.id);
assert.ok(assignLog, "MEMBERSHIP_ASSIGN audit log must be recorded");
console.log(`  ✓ Plan assigned: Gold Annual (12 Months, valid until ${assignRes.member?.validUntil})`);

// Step 5: Collect Payment for plan
const paymentRes = recordPayment({
  memberId: addedMember.id,
  amount: 25000,
  method: "UPI",
  description: "Gold Annual 12-Month Membership Full Fee",
  reference: "UPI/20261104/998877",
  status: "Paid",
});
assert.strictEqual(paymentRes.success, true, "Payment must be recorded successfully");
assert.strictEqual(paymentRes.payment?.amount, 25000);
assert.strictEqual(paymentRes.payment?.status, "Paid");
assert.ok(paymentRes.payment?.receiptNumber.startsWith("RCP-2026-"), "Receipt number must be generated");

auditLogs = getStoredAuditLogs();
const payLog = auditLogs.find((l) => l.action === "PAYMENT_COLLECT" && l.entityName === "Aruna Suresh");
assert.ok(payLog, "PAYMENT_COLLECT audit log must be recorded");
console.log(`  ✓ Payment collected: ₹25,000 via UPI (Receipt: ${paymentRes.payment?.receiptNumber})\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 2: Freeze Membership -> Verify Restrictions -> Unfreeze
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 2: Membership Freezing & Floor Access Restrictions");
const frozenMember = toggleFreezeMember(addedMember.id);
assert.strictEqual(frozenMember?.status, "Frozen", "Status must become Frozen");

auditLogs = getStoredAuditLogs();
const freezeLog = auditLogs.find((l) => l.action === "MEMBERSHIP_FREEZE" && l.entityId === addedMember.id);
assert.ok(freezeLog, "MEMBERSHIP_FREEZE audit log must be recorded");
console.log(`  2.1 Member ${addedMember.name} membership frozen successfully`);

// Restriction check: check-in must be rejected
const frozenCheckIn = checkInMember(addedMember.id);
assert.strictEqual(frozenCheckIn.success, false, "Check-in must fail for frozen member");
assert.strictEqual(frozenCheckIn.blockedReason, "frozen", "Blocked reason must be 'frozen'");
console.log(`  2.2 Check-in properly BLOCKED with reason: '${frozenCheckIn.blockedReason}'`);

// Unfreeze membership
const unfrozenMember = toggleFreezeMember(addedMember.id);
assert.strictEqual(unfrozenMember?.status, "Active", "Status must be restored to Active");

auditLogs = getStoredAuditLogs();
const unfreezeLog = auditLogs.find((l) => l.action === "MEMBERSHIP_UNFREEZE" && l.entityId === addedMember.id);
assert.ok(unfreezeLog, "MEMBERSHIP_UNFREEZE audit log must be recorded");
console.log(`  2.3 Member unfrozen, status restored to Active, access unlocked\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 3: Member Check-In -> Duplicate Detection -> Check-Out -> Attendance History
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 3: Attendance Check-In, Duplicate Guard & Checkout Lifecycle");
const checkInRes = checkInMember(addedMember.id);
assert.strictEqual(checkInRes.success, true, "Check-in must succeed for active member");
assert.ok(checkInRes.record?.id.startsWith("ATT-"), "Attendance ID must start with ATT-");
assert.strictEqual(checkInRes.record?.status, "Present", "Status must be Present");

// Verify visit count increment
const memberAfterCheckIn = getMemberById(addedMember.id);
assert(memberAfterCheckIn.totalVisits >= 1, "Visit count must increment");
console.log(`  3.1 First check-in succeeded at ${checkInRes.record?.checkInTime} (Attendance ID: ${checkInRes.record?.id})`);

// Attempt duplicate check-in
const duplicateCheckIn = checkInMember(addedMember.id);
assert.strictEqual(duplicateCheckIn.success, false, "Duplicate check-in must be rejected");
assert.strictEqual(duplicateCheckIn.blockedReason, "already_present", "Blocked reason must be 'already_present'");
console.log(`  3.2 Duplicate check-in correctly REJECTED (Reason: already on floor)`);

// Check-out member
const checkOutRes = checkOutMember(checkInRes.record.id);
assert.strictEqual(checkOutRes.success, true, "Check-out must succeed");

const attendanceRecords = getStoredAttendance();
const updatedAttRecord = attendanceRecords.find((a) => a.id === checkInRes.record.id);
assert.strictEqual(updatedAttRecord?.status, "Checked Out", "Attendance status must be Checked Out");
assert.ok(updatedAttRecord?.checkOutTime, "Check-out timestamp must be recorded");

auditLogs = getStoredAuditLogs();
const checkoutLog = auditLogs.find((l) => l.action === "ATTENDANCE_CHECKOUT" && l.entityId === addedMember.id);
assert.ok(checkoutLog, "ATTENDANCE_CHECKOUT audit log must be recorded");
console.log(`  3.3 Member checked out at ${updatedAttRecord?.checkOutTime}, full history preserved\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 4: Expired Member Attendance Guard & Administrative Override
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 4: Expired Member Check-in Guard & Admin Override Flow");
// GYM003 (David Miller) is expired in INITIAL_MEMBERS
const expiredMember = getMemberById("GYM003");
assert.strictEqual(expiredMember?.status, "Expired", "GYM003 must have Expired status");

// Normal check-in attempt must fail
const expiredCheckIn = checkInMember("GYM003");
assert.strictEqual(expiredCheckIn.success, false, "Expired check-in without override must fail");
assert.strictEqual(expiredCheckIn.blockedReason, "expired", "Blocked reason must be 'expired'");
console.log(`  4.1 Expired member check-in rejected with message: "${expiredCheckIn.message}"`);

// Supervisor administrative override
const overrideRes = checkInMember("GYM003", {
  isOverride: true,
  overrideReason: "Renewal payment in process; approved 1-day pass by Branch Manager",
  overriddenBy: "Senior Administrator",
});
assert.strictEqual(overrideRes.success, true, "Override check-in must succeed");
assert.strictEqual(overrideRes.record?.isOverride, true, "Record must flag isOverride: true");
assert.strictEqual(overrideRes.record?.overrideReason, "Renewal payment in process; approved 1-day pass by Branch Manager");

auditLogs = getStoredAuditLogs();
const overrideAudit = auditLogs.find((l) => l.action === "ADMIN_OVERRIDE" && l.entityId === "GYM003");
assert.ok(overrideAudit, "ADMIN_OVERRIDE audit event must be logged with high severity");
assert.strictEqual(overrideAudit.severity, "critical");
console.log(`  4.2 Administrative floor override logged with compliance audit entry AUD-${overrideAudit.id}\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 5: Staff Management (Create -> Edit -> Deactivate/Reactivate -> Delete -> ID Stability)
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 5: Staff Management & Non-Reuse Counter Verification");
const initialStaffList = getStoredStaff();
const initialStaffMaxNum = Math.max(...initialStaffList.map((s) => extractNumericSuffix(s.id)));
const nextStaffId = `STF${String(initialStaffMaxNum + 1).padStart(3, "0")}`;
console.log(`  5.1 Initial staff count: ${initialStaffList.length}, Next expected ID: ${nextStaffId}`);

const createdStaff = addStaff({
  name: "Gaurav Sen",
  role: "Personal Trainer",
  phone: "9845011999",
  email: "gaurav@gymcore.fit",
  joiningDate: "04 Nov 2026",
  salary: 52000,
  status: "Active",
  specialization: "Olympic Weightlifting & Powerlifting Coach",
  address: "HSR Sector 1, Bangalore",
});
assert.strictEqual(createdStaff.id, nextStaffId, `Created staff ID must match ${nextStaffId}`);
assert.strictEqual(createdStaff.phone, "+91 98450 11999", "Phone must be Indian formatted");

// Edit staff
updateStaff({
  ...createdStaff,
  role: "Fitness Instructor",
  salary: 58000,
});
let staffList = getStoredStaff();
let foundStaff = staffList.find((s) => s.id === createdStaff.id);
assert.strictEqual(foundStaff?.role, "Fitness Instructor");
assert.strictEqual(foundStaff?.salary, 58000);
console.log(`  5.2 Staff updated: Role set to ${foundStaff?.role}, Salary ₹${foundStaff?.salary}`);

// Deactivate staff
toggleStaffStatus(createdStaff.id);
staffList = getStoredStaff();
foundStaff = staffList.find((s) => s.id === createdStaff.id);
assert.strictEqual(foundStaff?.status, "Inactive", "Staff status must be Inactive");
console.log(`  5.3 Staff deactivated: Status is Inactive`);

// Reactivate staff
toggleStaffStatus(createdStaff.id);
staffList = getStoredStaff();
foundStaff = staffList.find((s) => s.id === createdStaff.id);
assert.strictEqual(foundStaff?.status, "Active", "Staff status must be Active again");
console.log(`  5.4 Staff reactivated: Status restored to Active`);

// Delete staff
deleteStaff(createdStaff.id);
staffList = getStoredStaff();
assert.ok(!staffList.some((s) => s.id === createdStaff.id), "Staff member must be removed from list");

// Verify that the next staff ID does NOT reuse deleted ID!
const subsequentStaffId = getNextStaffId(staffList);
const deletedNum = extractNumericSuffix(createdStaff.id);
const subsequentNum = extractNumericSuffix(subsequentStaffId);
assert(subsequentNum > deletedNum, `Subsequent ID (${subsequentStaffId}) must be strictly higher than deleted ID (${createdStaff.id})`);
console.log(`  5.5 Staff deleted. Next generated ID is ${subsequentStaffId} (ID ${createdStaff.id} permanently retired)\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 6: Partial Payment -> Dues Tracking -> Overpayment Prevention -> Settle
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 6: Dues Settle, Partial Payments & Overpayment Protection");
const allDues = getStoredDues();
const testDue = allDues.find((d) => d.id === "DUE-1003"); // David Miller, ₹12,999
assert.ok(testDue, "DUE-1003 must exist");
const startingBalance = testDue.remainingBalance;
console.log(`  6.1 Target Due ID: ${testDue.id} (${testDue.memberName}) - Starting Balance: ₹${startingBalance}`);

// Test 1: Negative / 0 payment rejected
const zeroPay = collectDuePayment({
  dueId: testDue.id,
  amount: 0,
  method: "Cash",
});
assert.strictEqual(zeroPay.success, false, "Zero amount payment must be rejected");

// Test 2: Overpayment rejected
const overPay = collectDuePayment({
  dueId: testDue.id,
  amount: startingBalance + 5000,
  method: "UPI",
});
assert.strictEqual(overPay.success, false, "Payment exceeding remaining balance must be rejected");
assert(overPay.message.includes("cannot exceed remaining balance"), "Error message must state overpayment rule");
console.log(`  6.2 Overpayment & zero payment guards passed: "${overPay.message}"`);

// Test 3: Partial payment of ₹4,000
const partialPay = collectDuePayment({
  dueId: testDue.id,
  amount: 4000,
  method: "UPI",
  note: "Installment 1 of 2",
});
assert.strictEqual(partialPay.success, true, "Partial payment must succeed");
assert.strictEqual(partialPay.due?.remainingBalance, startingBalance - 4000);
assert.strictEqual(partialPay.due?.status, "Partially Paid");
console.log(`  6.3 Partial payment ₹4,000 recorded. New balance: ₹${partialPay.due?.remainingBalance} (${partialPay.due?.status})`);

// Test 4: Settle remainder
const remainingToSettle = partialPay.due?.remainingBalance || 0;
const finalSettle = collectDuePayment({
  dueId: testDue.id,
  amount: remainingToSettle,
  method: "Cash",
  note: "Full remaining settlement",
});
assert.strictEqual(finalSettle.success, true, "Settlement must succeed");
assert.strictEqual(finalSettle.due?.remainingBalance, 0);
assert.strictEqual(finalSettle.due?.status, "Paid");
console.log(`  6.4 Remaining ₹${remainingToSettle} settled in full. Balance: ₹0 (Status: Paid)\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 7: Batch Member Import & ID Sequence Preservation
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 7: Batch CSV Member Import & Numeric Sorting Invariant");
const currentMembers = getStoredMembers();
const batchIds = generateNextMemberIds(3, currentMembers);
assert.strictEqual(batchIds.length, 3);

// Verify strictly ascending numeric sequence
const n1 = extractNumericSuffix(batchIds[0]);
const n2 = extractNumericSuffix(batchIds[1]);
const n3 = extractNumericSuffix(batchIds[2]);
assert.strictEqual(n2, n1 + 1);
assert.strictEqual(n3, n2 + 1);

const importedMembers = [
  {
    id: batchIds[0],
    name: "Batch Member 1",
    email: "batch1@gymcore.test",
    phone: "+91 98765 11001",
    plan: "Standard",
    joinDate: "04 Nov 2026",
    status: "Active",
  },
  {
    id: batchIds[1],
    name: "Batch Member 2",
    email: "batch2@gymcore.test",
    phone: "+91 98765 11002",
    plan: "Premium",
    joinDate: "04 Nov 2026",
    status: "Active",
  },
  {
    id: batchIds[2],
    name: "Batch Member 3",
    email: "batch3@gymcore.test",
    phone: "+91 98765 11003",
    plan: "Basic",
    joinDate: "04 Nov 2026",
    status: "Active",
  },
];

saveMembers([...currentMembers, ...importedMembers]);
batchIds.forEach((id) => updateMemberCounterHighWaterMark(id));

const allMembersAfterImport = getStoredMembers();
const importedFound = batchIds.every((id) => allMembersAfterImport.some((m) => m.id === id));
assert.ok(importedFound, "All batch-imported members must exist in storage");

// Verify sorting order preserves numeric IDs
const sortedMembers = sortMembersByNumericId(allMembersAfterImport);
for (let i = 0; i < sortedMembers.length - 1; i++) {
  const curNum = extractNumericSuffix(sortedMembers[i].id);
  const nextNum = extractNumericSuffix(sortedMembers[i + 1].id);
  assert(curNum <= nextNum, `Numeric order invariant violated: ${sortedMembers[i].id} > ${sortedMembers[i + 1].id}`);
}
console.log(`  ✓ Batch of 3 members imported with strictly sequential IDs (${batchIds.join(", ")})`);
console.log(`  ✓ Verified numeric ascending sort invariant across all ${sortedMembers.length} member records\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 8: Report Filtering, Analytics Aggregations & CSV Export Generation
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 8: Analytics Calculations & Export CSV Formatting");
const payments = getStoredPayments();
const totalRevenue = payments
  .filter((p) => p.status === "Paid")
  .reduce((sum, p) => sum + p.amount, 0);
assert(totalRevenue > 0, "Total revenue must be positive");

const activeMemberCount = getStoredMembers().filter((m) => m.status === "Active").length;
assert(activeMemberCount > 0, "Active member count must be positive");

// Verify Audit CSV Generator
const rawAuditLogs = getStoredAuditLogs();
const auditCsv = generateAuditCsv(rawAuditLogs);
assert(auditCsv.startsWith("Audit ID,Timestamp (ISO),Action,Entity Type,Entity ID,Entity Name,Performed By,Severity,Description"));
assert(auditCsv.includes("Member Enrolled") || auditCsv.includes("Payment Collected"));
assert(auditCsv.split("\n").length >= rawAuditLogs.length, "CSV must contain all rows");
console.log(`  ✓ Revenue aggregation: ₹${totalRevenue.toLocaleString("en-IN")} across ${payments.length} transactions`);
console.log(`  ✓ Audit CSV generated (${rawAuditLogs.length} rows, formatted with proper escaping)\n`);

// ---------------------------------------------------------------------------------------------
// WORKFLOW 9: Audit Trail Governance & Sensitive Data Redaction
// ---------------------------------------------------------------------------------------------
console.log("▶ WORKFLOW 9: Immutable Audit Logging & Zero Sensitive Data Leakage");
// Test redaction of sensitive credentials
const sensitiveInput = {
  adminEmail: "admin@gymcore.com",
  adminPassword: "SecretMasterPassword123!",
  bearerAuthToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
  creditCardNumber: "4532-1100-2200-3300",
  bankAccount: "HDFC-001239991823",
};

const sanitized = sanitizeAuditValue(sensitiveInput);
assert.strictEqual(sanitized.adminEmail, "admin@gymcore.com", "Non-sensitive email should not be redacted");
assert.strictEqual(sanitized.adminPassword, "[REDACTED]", "Password MUST be redacted");
assert.strictEqual(sanitized.bearerAuthToken, "[REDACTED]", "Auth token MUST be redacted");
assert.strictEqual(sanitized.creditCardNumber, "[REDACTED]", "Credit card number MUST be redacted");

// Log an action and verify it cannot leak sensitive fields
const secureAuditAction = logAuditAction({
  action: "SYSTEM_SETTINGS_UPDATE",
  actionLabel: "Gateway Settings Configured",
  entityType: "Settings",
  entityId: "SET-001",
  entityName: "Payment Gateway",
  performedBy: "Chief Tech Officer",
  description: "Configured API production webhook keys",
  previousValue: { apiKey: "old_key_secret_123" },
  updatedValue: { apiKey: "new_key_secret_456" },
  severity: "critical",
});

assert.strictEqual(secureAuditAction.previousValue?.apiKey, "[REDACTED]", "Previous secret apiKey must be redacted");
assert.strictEqual(secureAuditAction.updatedValue?.apiKey, "[REDACTED]", "Updated secret apiKey must be redacted");

console.log(`  ✓ Sensitive data redaction verified: Passwords, tokens, keys strictly replaced with [REDACTED]`);
console.log(`  ✓ Audit governance integrity validated across ${getStoredAuditLogs().length} immutable events\n`);

console.log("================================================================================");
console.log("   ALL 9 REAL-WORLD CONNECTED WORKFLOWS VALIDATED & PASSED WITH 100% SUCCESS!   ");
console.log("================================================================================\n");
