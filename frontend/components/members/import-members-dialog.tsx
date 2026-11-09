"use client";

import { useState, useRef } from "react";
import {
  Upload,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  X,
  Download,
  Sparkles,
  FileText,
} from "lucide-react";
import {
  type Member,
  type MembershipPlanItem,
  addMember,
  generateNextMemberIds,
} from "@/lib/mock-data";
import { isValidIndianMobile, formatIndianMobile, sanitizeIndianMobile } from "@/lib/phone-utils";
import { api } from "@/lib/api-client";
import { isBackendConnected } from "@/lib/backend-sync";

type ParsedRow = {
  rawIndex: number;
  name: string;
  email: string;
  phone: string;
  plan: string;
  joinDate?: string;
  emergencyContact?: string;
  address?: string;
  gender?: string;
  status: "valid" | "invalid" | "duplicate";
  issues: string[];
};

type ImportMembersDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  existingMembers: Member[];
  plans: MembershipPlanItem[];
  onImportSuccess: (count: number) => void;
};

export function ImportMembersDialog({
  isOpen,
  onClose,
  existingMembers,
  plans,
  onImportSuccess,
}: ImportMembersDialogProps) {
  const [activeTab, setActiveTab] = useState<"upload" | "paste">("upload");
  const [fileName, setFileName] = useState<string>("");
  const [selectedRawFile, setSelectedRawFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState<string>("");
  const [parsedRows, setParsedRows] = useState<ParsedRow[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  if (!isOpen) return null;

  const validCount = parsedRows.filter((r) => r.status === "valid").length;
  const invalidCount = parsedRows.filter((r) => r.status === "invalid").length;
  const duplicateCount = parsedRows.filter((r) => r.status === "duplicate").length;

  // Split CSV line taking quotes into account
  const parseCsvLine = (line: string): string[] => {
    const result: string[] = [];
    let current = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === "," && !inQuotes) {
        result.push(current.trim());
        current = "";
      } else {
        current += char;
      }
    }
    result.push(current.trim());
    return result;
  };

  const processCsvContent = (content: string, sourceName: string) => {
    setIsProcessing(true);
    setFileName(sourceName);

    const lines = content
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length === 0) {
      setParsedRows([]);
      setIsProcessing(false);
      return;
    }

    // Determine if first row is header
    const firstLine = lines[0].toLowerCase();
    const hasHeader =
      firstLine.includes("name") ||
      firstLine.includes("email") ||
      firstLine.includes("phone") ||
      firstLine.includes("plan");

    const dataLines = hasHeader ? lines.slice(1) : lines;

    const existingEmailSet = new Set(
      existingMembers.map((m) => m.email.toLowerCase().trim())
    );
    const existingPhoneDigits = new Set(
      existingMembers.map((m) => sanitizeIndianMobile(m.phone))
    );

    const batchPhoneDigits = new Set<string>();
    const batchEmailSet = new Set<string>();

    const rows: ParsedRow[] = dataLines.map((line, idx) => {
      const cols = parseCsvLine(line);
      const name = cols[0] || "";
      const email = (cols[1] || "").toLowerCase().trim();
      const rawPhone = cols[2] || "";
      const planNameInput = cols[3] || "";
      const joinDate = cols[4] || new Date().toISOString().split("T")[0];
      const emergencyContact = cols[5] || "";
      const address = cols[6] || "";

      const issues: string[] = [];

      // Validate Name
      if (!name.trim() || name.trim().length < 2) {
        issues.push("Name is required (min 2 chars).");
      }

      // Validate Email
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!email || !emailRegex.test(email)) {
        issues.push("Invalid email format.");
      }

      // Validate Phone
      if (!isValidIndianMobile(rawPhone)) {
        issues.push("Phone must be 10 digits starting with 6-9.");
      }

      // Match Plan
      let resolvedPlan = plans[0]?.name || "Standard";
      if (!planNameInput.trim()) {
        issues.push("Membership plan is required.");
      } else {
        const matched = plans.find(
          (p) => p.name.toLowerCase() === planNameInput.trim().toLowerCase()
        );
        if (matched) {
          resolvedPlan = matched.name;
        } else {
          issues.push(
            `Unknown plan "${planNameInput}". Available: ${plans.map((p) => p.name).join(", ")}`
          );
        }
      }

      // Duplicate Check
      const sanitizedPhone = sanitizeIndianMobile(rawPhone);

      if (existingEmailSet.has(email)) {
        issues.push(`Email already registered in gym directory.`);
      } else if (existingPhoneDigits.has(sanitizedPhone)) {
        issues.push(`Phone already belongs to an existing member.`);
      } else if (batchEmailSet.has(email)) {
        issues.push(`Duplicate email found in this import batch.`);
      } else if (sanitizedPhone && batchPhoneDigits.has(sanitizedPhone)) {
        issues.push(`Duplicate phone found in this import batch.`);
      }

      if (sanitizedPhone) batchPhoneDigits.add(sanitizedPhone);
      if (email) batchEmailSet.add(email);

      let status: "valid" | "invalid" | "duplicate" = "valid";
      if (issues.some((i) => i.includes("already") || i.includes("Duplicate"))) {
        status = "duplicate";
      } else if (issues.length > 0) {
        status = "invalid";
      }

      return {
        rawIndex: idx + 1,
        name: name.trim(),
        email,
        phone: rawPhone.trim(),
        plan: resolvedPlan,
        joinDate,
        emergencyContact,
        address,
        status,
        issues,
      };
    });

    setParsedRows(rows);
    setIsProcessing(false);
  };

  const handleFileSelect = (file: File) => {
    if (!file) return;
    setSelectedRawFile(file);
    if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
      setFileName(file.name);
      setParsedRows([
        {
          rawIndex: 1,
          name: "Excel Workbook Uploaded (.xlsx / .xls)",
          email: "-",
          phone: "-",
          plan: "-",
          status: "invalid",
          issues: [
            `"${file.name}" is an Excel workbook. GYMCORE imports standard CSV (.csv) files for secure client-side validation. Please open your spreadsheet in Excel or Google Sheets, select "Save As" -> "CSV (Comma delimited) (*.csv)", and upload the exported .csv file.`,
          ],
        },
      ]);
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      processCsvContent(text, file.name);
    };
    reader.readAsText(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFileSelect(files[0]);
    }
  };

  const handlePasteSubmit = () => {
    if (!pastedText.trim()) return;
    processCsvContent(pastedText.trim(), "Pasted Data");
  };

  const handleDownloadSample = () => {
    const sampleCsv = `Full Name,Email Address,Mobile Number,Plan,Join Date,Emergency Contact,Address
Rohit Verma,rohit.verma@example.com,9876511223,Premium,2026-11-01,"+91 98765 00010 (Brother)","Indiranagar, Bangalore"
Pooja Nair,pooja.nair@example.com,9823456789,Standard,2026-11-02,"+91 98765 00011 (Father)","Koramangala, Bangalore"
Vikram Malhotra,vikram.m@example.com,9712345678,Basic,2026-11-03,"+91 98765 00012 (Spouse)","HSR Layout, Bangalore"`;

    const blob = new Blob([sampleCsv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "gymcore_sample_members_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExecuteImport = () => {
    const validRows = parsedRows.filter((r) => r.status === "valid");
    if (validRows.length === 0) return;

    // Generate sequential IDs based on current members and persistent high-water mark counter
    const generatedIds = generateNextMemberIds(validRows.length, existingMembers);

    validRows.forEach((row, idx) => {
      const newId = generatedIds[idx];

      const planObj = plans.find((p) => p.name.toLowerCase() === row.plan.toLowerCase());
      const durationMonths = planObj?.durationMonths || 12;

      const rawJoinDate = row.joinDate?.trim() || new Date().toISOString().split("T")[0];
      const parsedDate = new Date(rawJoinDate.includes("T") ? rawJoinDate : `${rawJoinDate}T00:00:00`);
      const joinDateObj = isNaN(parsedDate.getTime()) ? new Date() : parsedDate;

      const validUntilObj = new Date(joinDateObj);
      validUntilObj.setMonth(validUntilObj.getMonth() + durationMonths);

      const day = String(validUntilObj.getDate()).padStart(2, "0");
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const validUntil = `${day} ${months[validUntilObj.getMonth()]} ${validUntilObj.getFullYear()}`;

      const joinDay = String(joinDateObj.getDate()).padStart(2, "0");
      const formattedJoinDate = `${joinDay} ${months[joinDateObj.getMonth()]} ${joinDateObj.getFullYear()}`;

      const newMember: Member = {
        id: newId,
        name: row.name,
        email: row.email,
        phone: formatIndianMobile(row.phone),
        plan: row.plan,
        joinDate: formattedJoinDate,
        status: "Active",
        validUntil,
        emergencyContact: row.emergencyContact,
        address: row.address,
        totalVisits: 0,
        lastVisit: "Not visited yet",
      };

      addMember(newMember);
    });

    if (isBackendConnected() && selectedRawFile) {
      api.imports.importMembers(selectedRawFile, false).catch(() => {});
    }

    onImportSuccess(validRows.length);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl rounded-2xl border border-border bg-card p-6 shadow-2xl animate-in fade-in zoom-in-95 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-[#C9A04F]/10 p-2 text-[#C9A04F]">
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-foreground">Import Members</h2>
                <span className="rounded-md border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-2 py-0.5 text-[11px] font-semibold text-[#C9A04F]">
                  CSV Member Import
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Bulk upload member records via CSV with automatic duplicate detection & format validation
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Controls & Template Download */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded-xl border border-border bg-background p-1 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab("upload")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                activeTab === "upload"
                  ? "bg-[#C9A04F] text-black font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Upload File
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("paste")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                activeTab === "paste"
                  ? "bg-[#C9A04F] text-black font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Paste CSV Text
            </button>
          </div>

          <button
            type="button"
            onClick={handleDownloadSample}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:border-[#C9A04F] hover:text-[#C9A04F]"
          >
            <Download size={13} className="text-[#C9A04F]" />
            <span>Download CSV Template</span>
          </button>
        </div>

        {/* Content Area */}
        {activeTab === "upload" ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`mt-4 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
              isDragging
                ? "border-[#C9A04F] bg-[#C9A04F]/10"
                : "border-border bg-background/40 hover:border-[#C9A04F]/50"
            }`}
          >
            <input
              id="member-csv-file"
              type="file"
              ref={fileInputRef}
              accept=".csv, text/csv"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
              className="hidden"
            />
            <div className="rounded-2xl bg-[#C9A04F]/15 p-3 text-[#C9A04F]">
              <Upload size={24} />
            </div>
            <h3 className="mt-3 text-sm font-bold text-foreground">
              Drag & Drop your member CSV file here
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Supports .csv (Comma-Separated Values) format • Excel users can save as CSV before upload
            </p>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black transition-all hover:bg-[#b68d3e]"
            >
              Browse Computer
            </button>
            {fileName && (
              <div className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-2.5 py-1 text-xs font-semibold text-[#C9A04F]">
                <FileText size={13} />
                <span>Selected: {fileName}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            <label htmlFor="member-csv-paste" className="sr-only">Paste CSV Text</label>
            <textarea
              id="member-csv-paste"
              rows={4}
              placeholder="Paste raw CSV text here (e.g. Name, Email, Phone, Plan)..."
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              className="w-full rounded-xl border border-border bg-background p-3 text-xs font-mono text-foreground placeholder:text-muted-foreground focus:border-[#C9A04F] focus:outline-none"
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handlePasteSubmit}
                className="rounded-xl bg-[#C9A04F] px-4 py-2 text-xs font-bold text-black hover:bg-[#b68d3e]"
              >
                Parse Pasted Content
              </button>
            </div>
          </div>
        )}

        {/* Validation & Preview Summary */}
        {parsedRows.length > 0 && (
          <div className="mt-6 space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-border bg-background/50 p-3 text-center">
                <div className="text-[11px] font-semibold uppercase text-muted-foreground">Total Rows</div>
                <div className="mt-1 text-xl font-extrabold text-foreground">{parsedRows.length}</div>
              </div>
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-center">
                <div className="text-[11px] font-semibold uppercase text-emerald-400">Ready to Import</div>
                <div className="mt-1 text-xl font-extrabold text-emerald-400">{validCount}</div>
              </div>
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-center">
                <div className="text-[11px] font-semibold uppercase text-amber-400">Duplicates</div>
                <div className="mt-1 text-xl font-extrabold text-amber-400">{duplicateCount}</div>
              </div>
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-center">
                <div className="text-[11px] font-semibold uppercase text-red-400">Format Errors</div>
                <div className="mt-1 text-xl font-extrabold text-red-400">{invalidCount}</div>
              </div>
            </div>

            {/* Preview Table */}
            <div className="max-h-60 overflow-x-auto overflow-y-auto rounded-xl border border-border bg-background/30">
              <table className="w-full min-w-[550px] text-left text-xs">
                <thead className="sticky top-0 border-b border-border bg-card text-[11px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="p-2.5">Row</th>
                    <th className="p-2.5">Status</th>
                    <th className="p-2.5">Name</th>
                    <th className="p-2.5">Contact</th>
                    <th className="p-2.5">Plan</th>
                    <th className="p-2.5">Validation Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 text-foreground">
                  {parsedRows.map((row) => (
                    <tr
                      key={row.rawIndex}
                      className={
                        row.status === "valid"
                          ? "bg-emerald-500/5 hover:bg-emerald-500/10"
                          : row.status === "duplicate"
                          ? "bg-amber-500/5 hover:bg-amber-500/10"
                          : "bg-red-500/5 hover:bg-red-500/10"
                      }
                    >
                      <td className="p-2.5 font-mono text-muted-foreground">#{row.rawIndex}</td>
                      <td className="p-2.5">
                        {row.status === "valid" ? (
                          <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                            <CheckCircle2 size={11} /> Valid
                          </span>
                        ) : row.status === "duplicate" ? (
                          <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                            <AlertTriangle size={11} /> Duplicate
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-400">
                            <AlertCircle size={11} /> Invalid
                          </span>
                        )}
                      </td>
                      <td className="p-2.5 font-semibold text-foreground">{row.name || "—"}</td>
                      <td className="p-2.5 text-muted-foreground">
                        <div>{row.email || "—"}</div>
                        <div className="font-mono text-[11px]">{row.phone || "—"}</div>
                      </td>
                      <td className="p-2.5 font-medium">{row.plan}</td>
                      <td className="p-2.5 text-[11px]">
                        {row.issues.length > 0 ? (
                          <span className="text-red-400 font-medium">{row.issues.join("; ")}</span>
                        ) : (
                          <span className="text-emerald-400 font-medium">Ready to import</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={validCount === 0 || isProcessing}
            onClick={handleExecuteImport}
            className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-bold transition-all ${
              validCount > 0 && !isProcessing
                ? "bg-[#C9A04F] text-black hover:bg-[#b68d3e] shadow-lg shadow-[#C9A04F]/10 cursor-pointer"
                : "bg-muted text-muted-foreground cursor-not-allowed opacity-50"
            }`}
          >
            <Sparkles size={14} />
            <span>
              {validCount > 0
                ? `Import ${validCount} Valid Member${validCount > 1 ? "s" : ""}`
                : "No Valid Records to Import"}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
