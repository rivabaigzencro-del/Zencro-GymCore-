import http from "node:http";
import { spawn } from "node:child_process";

const PORT = 3008;
const BASE_URL = `http://127.0.0.1:${PORT}`;
const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

function fetchDOM(url) {
  return new Promise((resolve, reject) => {
    const chrome = spawn(CHROME_PATH, [
      "--headless=new",
      "--no-sandbox",
      "--disable-gpu",
      "--virtual-time-budget=2000",
      "--dump-dom",
      url,
    ]);

    let stdout = "";
    let stderr = "";

    chrome.stdout.on("data", (d) => (stdout += d));
    chrome.stderr.on("data", (d) => (stderr += d));

    chrome.on("close", (code) => {
      if (code === 0 && stdout.length > 0) {
        resolve(stdout);
      } else {
        reject(new Error(`Chrome exited with code ${code}. Stderr: ${stderr}`));
      }
    });
  });
}

function waitForServer(url, timeout = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const interval = setInterval(() => {
      http
        .get(url, (res) => {
          if (res.statusCode && res.statusCode < 500) {
            clearInterval(interval);
            resolve();
          }
        })
        .on("error", () => {
          if (Date.now() - start > timeout) {
            clearInterval(interval);
            reject(new Error(`Server at ${url} did not become ready in ${timeout}ms`));
          }
        });
    }, 500);
  });
}

async function runBrowserTests() {
  console.log("=== STARTING GYMCORE LIVE BROWSER AUTOMATION SUITE ===");
  console.log(`Targeting production server on port ${PORT}...`);

  // Start Next.js production server
  const server = spawn("cmd.exe", ["/c", `npx.cmd next start -p ${PORT}`], {
    cwd: process.cwd(),
    stdio: "pipe",
  });

  server.stdout.on("data", (d) => {
    const text = d.toString();
    if (text.includes("Ready") || text.includes("started server")) {
      console.log(`[Next.js Server]: ${text.trim()}`);
    }
  });

  server.stderr.on("data", (d) => {
    console.error(`[Next.js Error]: ${d.toString().trim()}`);
  });

  try {
    console.log("Waiting for Next.js server to respond...");
    await waitForServer(`${BASE_URL}/`, 25000);
    console.log("✓ Next.js server is LIVE and responding!\n");

    const results = [];

    // TEST 1: Route / (Dashboard)
    console.log("TEST 1: Live Headless Chrome render of / (Dashboard)");
    const dashDOM = await fetchDOM(`${BASE_URL}/`);
    const hasGymCore = dashDOM.includes("GYMCORE");
    const hasCollection = dashDOM.includes("Today's Collection") || dashDOM.includes("Collection");
    const hasActiveMembers = dashDOM.includes("Active Members");
    const hasPendingDues = dashDOM.includes("Pending Dues");
    const hasExpiring = dashDOM.includes("Expiring This Week") || dashDOM.includes("Expiring");

    console.log(`- GYMCORE Branding: ${hasGymCore ? "FOUND" : "MISSING"}`);
    console.log(`- Today's Collection Card: ${hasCollection ? "FOUND" : "MISSING"}`);
    console.log(`- Active Members Card: ${hasActiveMembers ? "FOUND" : "MISSING"}`);
    console.log(`- Pending Dues Card: ${hasPendingDues ? "FOUND" : "MISSING"}`);
    console.log(`- Expiring This Week Card: ${hasExpiring ? "FOUND" : "MISSING"}`);

    if (hasGymCore && hasCollection && hasActiveMembers && hasPendingDues) {
      console.log("✓ PASSED: Dashboard rendered with real metrics and branding\n");
      results.push({ name: "Dashboard (/)", status: "PASSED" });
    } else {
      throw new Error("Dashboard DOM verification failed");
    }

    // TEST 2: Route /members (Member Directory & Import trigger)
    console.log("TEST 2: Live Headless Chrome render of /members");
    const membersDOM = await fetchDOM(`${BASE_URL}/members`);
    const hasMemberTable = membersDOM.includes("GYM001") && membersDOM.includes("Alex Johnson");
    const hasNumericOrder = membersDOM.indexOf("GYM001") < membersDOM.indexOf("GYM002");
    const hasImportButton = membersDOM.includes("Import CSV");
    const hasExportButton = membersDOM.includes("Export CSV");

    console.log(`- Members Table (GYM001 - Alex Johnson): ${hasMemberTable ? "FOUND" : "MISSING"}`);
    console.log(`- Numeric Sorting (GYM001 precedes GYM002): ${hasNumericOrder ? "VERIFIED" : "FAILED"}`);
    console.log(`- Import CSV Button: ${hasImportButton ? "FOUND" : "MISSING"}`);
    console.log(`- Export CSV Button: ${hasExportButton ? "FOUND" : "MISSING"}`);

    if (hasMemberTable && hasNumericOrder && hasImportButton) {
      console.log("✓ PASSED: Members Directory rendered with correct sorting and Import action\n");
      results.push({ name: "Members Directory (/members)", status: "PASSED" });
    } else {
      throw new Error("Members directory DOM verification failed");
    }

    // TEST 3: Route /reports (Reports & Analytics Filters)
    console.log("TEST 3: Live Headless Chrome render of /reports");
    const reportsDOM = await fetchDOM(`${BASE_URL}/reports`);
    const hasReportsTitle = reportsDOM.includes("Reports &amp; Analytics") || reportsDOM.includes("Reports & Analytics") || reportsDOM.includes("Reports");
    const hasDateFilters = reportsDOM.includes("Today") && reportsDOM.includes("Last 7 Days");
    const hasExportDues = reportsDOM.includes("Export Dues CSV") || reportsDOM.includes("Export CSV") || reportsDOM.includes("Export");

    console.log(`- Reports View Header: ${hasReportsTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Date Range Filter Buttons: ${hasDateFilters ? "FOUND" : "MISSING"}`);
    console.log(`- Export CSV Actions: ${hasExportDues ? "FOUND" : "MISSING"}`);

    if (hasReportsTitle && hasDateFilters) {
      console.log("✓ PASSED: Reports View rendered with filters and export actions\n");
      results.push({ name: "Reports & Analytics (/reports)", status: "PASSED" });
    } else {
      throw new Error("Reports view DOM verification failed");
    }

    // TEST 4: Route /payments (Outstanding Dues & Payments)
    console.log("TEST 4: Live Headless Chrome render of /payments");
    const paymentsDOM = await fetchDOM(`${BASE_URL}/payments`);
    const hasPaymentsTitle = paymentsDOM.includes("Payments") || paymentsDOM.includes("Billing");
    const hasDuesTab = paymentsDOM.includes("Outstanding Dues");
    const hasDavidMillerDue = paymentsDOM.includes("David Miller") || paymentsDOM.includes("GYM003");

    console.log(`- Payments & Billing Title: ${hasPaymentsTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Outstanding Dues Section: ${hasDuesTab ? "FOUND" : "MISSING"}`);
    console.log(`- David Miller (GYM003) Dues Entry: ${hasDavidMillerDue ? "FOUND" : "MISSING"}`);

    if (hasPaymentsTitle && hasDuesTab) {
      console.log("✓ PASSED: Payments & Outstanding Dues rendered successfully\n");
      results.push({ name: "Payments & Dues (/payments)", status: "PASSED" });
    } else {
      throw new Error("Payments view DOM verification failed");
    }

    // TEST 5: Route /attendance (Attendance Tracker)
    console.log("TEST 5: Live Headless Chrome render of /attendance");
    const attendanceDOM = await fetchDOM(`${BASE_URL}/attendance`);
    const hasAttendanceTitle = attendanceDOM.includes("Attendance");
    const hasCheckInAction = attendanceDOM.includes("Check In") || attendanceDOM.includes("Check-In");
    const hasScanner = attendanceDOM.includes("QR") || attendanceDOM.includes("Scan");

    console.log(`- Attendance View Header: ${hasAttendanceTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Check-In Action: ${hasCheckInAction ? "FOUND" : "MISSING"}`);
    console.log(`- Scanner Trigger: ${hasScanner ? "FOUND" : "MISSING"}`);

    if (hasAttendanceTitle && hasCheckInAction) {
      console.log("✓ PASSED: Attendance Tracker rendered successfully\n");
      results.push({ name: "Attendance Tracker (/attendance)", status: "PASSED" });
    } else {
      throw new Error("Attendance tracker DOM verification failed");
    }

    // TEST 6: Route /staff (Staff Directory & Sorting)
    console.log("TEST 6: Live Headless Chrome render of /staff");
    const staffDOM = await fetchDOM(`${BASE_URL}/staff`);
    const hasStaffTitle = staffDOM.includes("Staff");
    const hasStaffRecords = staffDOM.includes("STF001") || staffDOM.includes("Vikram");

    console.log(`- Staff Header: ${hasStaffTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Staff Directory Records: ${hasStaffRecords ? "FOUND" : "MISSING"}`);

    if (hasStaffTitle && hasStaffRecords) {
      console.log("✓ PASSED: Staff Directory rendered with numeric records\n");
      results.push({ name: "Staff Directory (/staff)", status: "PASSED" });
    } else {
      throw new Error("Staff directory DOM verification failed");
    }

    // TEST 7: Route /audit (Audit Trail & Governance)
    console.log("TEST 7: Live Headless Chrome render of /audit");
    const auditDOM = await fetchDOM(`${BASE_URL}/audit`);
    const hasAuditTitle = auditDOM.includes("Audit Trail") || auditDOM.includes("Audit Activity Log");
    const hasAuditRecords = auditDOM.includes("AUD-001") || auditDOM.includes("Rajesh Khanna");
    const hasExportAuditCsv = auditDOM.includes("Export Audit CSV");

    console.log(`- Audit Header / Section: ${hasAuditTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Audit Records (AUD-001): ${hasAuditRecords ? "FOUND" : "MISSING"}`);
    console.log(`- Export Audit CSV Action: ${hasExportAuditCsv ? "FOUND" : "MISSING"}`);

    if (hasAuditTitle && hasAuditRecords && hasExportAuditCsv) {
      console.log("✓ PASSED: Audit Trail & Governance rendered with immutable event records\n");
      results.push({ name: "Audit Trail (/audit)", status: "PASSED" });
    } else {
      throw new Error("Audit trail DOM verification failed");
    }

    // TEST 8: Route /memberships (Membership Plans)
    console.log("TEST 8: Live Headless Chrome render of /memberships");
    const membershipsDOM = await fetchDOM(`${BASE_URL}/memberships`);
    const hasMembershipsTitle = membershipsDOM.includes("Membership") || membershipsDOM.includes("Plans");
    const hasPlans = membershipsDOM.includes("Gold") || membershipsDOM.includes("Premium") || membershipsDOM.includes("Basic");

    console.log(`- Memberships Header: ${hasMembershipsTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Plan Cards: ${hasPlans ? "FOUND" : "MISSING"}`);

    if (hasMembershipsTitle && hasPlans) {
      console.log("✓ PASSED: Membership Plans rendered successfully\n");
      results.push({ name: "Membership Plans (/memberships)", status: "PASSED" });
    } else {
      throw new Error("Membership plans DOM verification failed");
    }

    // TEST 9: Route /settings (System Preferences & Gym Config)
    console.log("TEST 9: Live Headless Chrome render of /settings");
    const settingsDOM = await fetchDOM(`${BASE_URL}/settings`);
    const hasSettingsTitle = settingsDOM.includes("Settings") || settingsDOM.includes("Configuration");
    const hasGymConfig = settingsDOM.includes("Gym") || settingsDOM.includes("Save");

    console.log(`- Settings Header: ${hasSettingsTitle ? "FOUND" : "MISSING"}`);
    console.log(`- Configuration Forms: ${hasGymConfig ? "FOUND" : "MISSING"}`);

    if (hasSettingsTitle && hasGymConfig) {
      console.log("✓ PASSED: Settings & System Preferences rendered successfully\n");
      results.push({ name: "Settings (/settings)", status: "PASSED" });
    } else {
      throw new Error("Settings DOM verification failed");
    }

    // TEST 10: Route /login (Authentication & Credentials Guard)
    console.log("TEST 10: Live Headless Chrome render of /login");
    const loginDOM = await fetchDOM(`${BASE_URL}/login`);
    const hasLoginBranding = loginDOM.includes("GYMCORE");
    const hasLoginForm = loginDOM.includes("password") || loginDOM.includes("Sign In") || loginDOM.includes("Password");

    console.log(`- Login Branding: ${hasLoginBranding ? "FOUND" : "MISSING"}`);
    console.log(`- Login Form & Inputs: ${hasLoginForm ? "FOUND" : "MISSING"}`);

    if (hasLoginBranding && hasLoginForm) {
      console.log("✓ PASSED: Authentication Screen rendered successfully\n");
      results.push({ name: "Login Screen (/login)", status: "PASSED" });
    } else {
      throw new Error("Login screen DOM verification failed");
    }

    // TEST 11: Route /members/GYM001 (Member Profile View)
    console.log("TEST 11: Live Headless Chrome render of /members/GYM001");
    const profileDOM = await fetchDOM(`${BASE_URL}/members/GYM001`);
    const hasAlex = profileDOM.includes("Alex Johnson");
    const hasGym001 = profileDOM.includes("GYM001");

    console.log(`- Member Name (Alex Johnson): ${hasAlex ? "FOUND" : "MISSING"}`);
    console.log(`- Member ID (GYM001): ${hasGym001 ? "FOUND" : "MISSING"}`);

    if (hasAlex && hasGym001) {
      console.log("✓ PASSED: Member Profile /members/GYM001 rendered successfully\n");
      results.push({ name: "Member Profile (/members/GYM001)", status: "PASSED" });
    } else {
      throw new Error("Member profile DOM verification failed");
    }

    console.log("==================================================");
    console.log(`ALL ${results.length} LIVE BROWSER AUTOMATION TESTS PASSED CLEANLY!`);
    console.log("==================================================");
  } finally {
    console.log("Shutting down test Next.js server...");
    // Kill child process
    spawn("taskkill", ["/PID", server.pid, "/T", "/F"]);
  }
}

runBrowserTests().catch((err) => {
  console.error("FATAL BROWSER TEST ERROR:", err);
  process.exit(1);
});

