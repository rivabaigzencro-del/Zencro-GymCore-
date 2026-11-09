/**
 * GYMCORE Centralized API Client Layer
 * Connected to FastAPI backend (Days 1–7) at http://localhost:8000/api/v1
 *
 * Implements real JWT authentication, strict session lifecycle, RBAC mapping,
 * FormData file uploads (without manual Content-Type corruption), binary export downloads,
 * and typed endpoints for all GYMCORE modules.
 */

export interface ApiClientConfig {
  baseUrl: string;
  timeoutMs: number;
}

const DEFAULT_API_URL = "http://localhost:8000/api/v1";
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;

export const API_CONFIG: ApiClientConfig = {
  baseUrl: rawApiUrl.replace(/\/+$/, ""),
  timeoutMs: 15000,
};

export function getApiBaseUrl(): string {
  return API_CONFIG.baseUrl;
}

const TOKEN_STORAGE_KEY = "gymcore_auth_token_jwt";
const REFRESH_TOKEN_STORAGE_KEY = "gymcore_refresh_token_jwt";
const SESSION_STORAGE_KEY = "gymcore_user_session";
const DEMO_MODE_STORAGE_KEY = "gymcore_demo_mode_enabled";

export type UserRole = "Owner" | "Manager" | "Front Desk";
export type BackendRole = "OWNER" | "MANAGER" | "FRONT_DESK";

export interface UserSession {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  title?: string;
  tenantId?: string;
  phone?: string;
}

export function normalizeRole(role: string): UserRole {
  const upper = String(role || "").toUpperCase().replace(/[\s_-]+/g, "");
  if (upper === "OWNER") return "Owner";
  if (upper === "MANAGER") return "Manager";
  if (upper === "FRONTDESK") return "Front Desk";
  return "Front Desk";
}

export function toBackendRole(role: string): BackendRole {
  const upper = String(role || "").toUpperCase().replace(/[\s_-]+/g, "");
  if (upper === "OWNER") return "OWNER";
  if (upper === "MANAGER") return "MANAGER";
  if (upper === "FRONTDESK") return "FRONT_DESK";
  return "FRONT_DESK";
}

export const DEMO_ACCOUNTS: Record<string, UserSession & { password: string; title: string }> = {
  "admin@gymcore.com": {
    id: "USR-001",
    name: "Vikram Malhotra",
    email: "admin@gymcore.com",
    role: "Owner",
    title: "Gym Owner and Administrator",
    password: "admin123",
  },
  "owner@gymcore.com": {
    id: "USR-001",
    name: "Vikram Malhotra",
    email: "owner@gymcore.com",
    role: "Owner",
    title: "Gym Owner and Administrator",
    password: "owner123",
  },
  "manager@gymcore.com": {
    id: "USR-002",
    name: "Rajesh Khanna",
    email: "manager@gymcore.com",
    role: "Manager",
    title: "Floor and Operations Manager",
    password: "manager123",
  },
  "frontdesk@gymcore.com": {
    id: "USR-003",
    name: "Ananya Sen",
    email: "frontdesk@gymcore.com",
    role: "Front Desk",
    title: "Front Desk and Reception Staff",
    password: "frontdesk123",
  },
};

export function isDemoModeEnabled(): boolean {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_ENABLE_DEMO === "true";
  }
  return (
    process.env.NEXT_PUBLIC_ENABLE_DEMO === "true" ||
    localStorage.getItem(DEMO_MODE_STORAGE_KEY) === "true"
  );
}

export function setDemoModeEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  if (enabled) {
    localStorage.setItem(DEMO_MODE_STORAGE_KEY, "true");
  } else {
    localStorage.removeItem(DEMO_MODE_STORAGE_KEY);
  }
}

let cachedSession: UserSession | null = null;
let cachedRaw: string | null = null;

export function getActiveSession(): UserSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) {
      cachedSession = null;
      cachedRaw = null;
      return null;
    }
    if (raw === cachedRaw && cachedSession) {
      return cachedSession;
    }
    cachedRaw = raw;
    cachedSession = JSON.parse(raw);
    return cachedSession;
  } catch {
    return null;
  }
}

export function setActiveSession(session: UserSession | null): void {
  if (typeof window === "undefined") return;
  if (!session) {
    clearActiveSession();
    return;
  }
  cachedRaw = JSON.stringify(session);
  cachedSession = session;
  localStorage.setItem(SESSION_STORAGE_KEY, cachedRaw);
  window.dispatchEvent(new Event("gymcore_session_change"));
}

export function clearActiveSession(): void {
  if (typeof window === "undefined") return;
  cachedRaw = null;
  cachedSession = null;
  localStorage.removeItem(SESSION_STORAGE_KEY);
  clearStoredAuthTokens();
  window.dispatchEvent(new Event("gymcore_session_change"));
}

export function subscribeSession(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("gymcore_session_change", callback);
  return () => {
    window.removeEventListener("gymcore_session_change", callback);
  };
}

export function getStoredAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredAuthToken(accessToken: string, refreshToken?: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken);
  }
}

export function clearStoredAuthTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  statusCode?: number;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = getStoredAuthToken();
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Only set Content-Type if NOT sending FormData (browser automatically sets boundary for multipart)
  if (!isFormData && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${API_CONFIG.baseUrl}${cleanEndpoint}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // On 401 Unauthorized, automatically clear token and invalidate invalid session
    if (response.status === 401) {
      clearStoredAuthTokens();
      if (typeof window !== "undefined") {
        localStorage.removeItem(SESSION_STORAGE_KEY);
        window.dispatchEvent(new Event("gymcore_session_change"));
      }
      return {
        success: false,
        error: "Session expired or unauthorized. Please re-authenticate.",
        statusCode: 401,
      };
    }

    const json = await response.json().catch(() => null);

    if (!response.ok) {
      let errorMsg = `API error (${response.status}): ${response.statusText}`;
      if (json) {
        if (typeof json.detail === "string") {
          errorMsg = json.detail;
        } else if (Array.isArray(json.detail)) {
          errorMsg = json.detail.map((d: { msg?: string; loc?: string[] }) => d.msg || JSON.stringify(d)).join("; ");
        } else if (json.message) {
          errorMsg = json.message;
        }
      }
      return {
        success: false,
        error: errorMsg,
        statusCode: response.status,
      };
    }

    return {
      success: true,
      data: json as T,
      statusCode: response.status,
    };
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    const isAbort = (err as { name?: string })?.name === "AbortError";
    return {
      success: false,
      error: isAbort
        ? "API request timed out (FastAPI backend unreachable)"
        : `Network error: ${(err as Error)?.message || "Backend offline"}`,
      statusCode: 0,
    };
  }
}

/**
 * Binary file downloader for CSV and Excel exports
 */
export async function apiDownload(
  endpoint: string,
  filename: string
): Promise<{ success: boolean; error?: string }> {
  const token = getStoredAuthToken();
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${API_CONFIG.baseUrl}${cleanEndpoint}`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      const errJson = await response.json().catch(() => null);
      return {
        success: false,
        error: errJson?.detail || `Export failed with status ${response.status}`,
      };
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
    return { success: true };
  } catch (err) {
    return {
      success: false,
      error: (err as Error)?.message || "Failed to download export file",
    };
  }
}

/**
 * Health & Backend Connectivity Checker
 */
export async function checkBackendHealth(): Promise<{
  isOnline: boolean;
  latencyMs: number;
  baseUrl: string;
  error?: string;
}> {
  const start = Date.now();
  try {
    // Try top-level /health or /api/v1/health
    const res = await apiRequest<{ status: string }>("/health");
    const latencyMs = Date.now() - start;
    if (res.success && (res.data?.status === "ok" || res.data?.status === "healthy")) {
      return { isOnline: true, latencyMs, baseUrl: API_CONFIG.baseUrl };
    }
    // Also try direct /health at root
    const rootRes = await fetch(`${API_CONFIG.baseUrl.replace(/\/api\/v1\/?$/, "")}/health`).catch(() => null);
    if (rootRes && rootRes.ok) {
      return { isOnline: true, latencyMs: Date.now() - start, baseUrl: API_CONFIG.baseUrl };
    }
    return {
      isOnline: false,
      latencyMs,
      baseUrl: API_CONFIG.baseUrl,
      error: res.error || "Backend returned non-ok health status",
    };
  } catch (err) {
    return {
      isOnline: false,
      latencyMs: Date.now() - start,
      baseUrl: API_CONFIG.baseUrl,
      error: (err as Error).message,
    };
  }
}

/**
 * Complete Typed API Endpoints Map for GYMCORE Days 1-7
 */
export const api = {
  // Authentication & Users
  auth: {
    login: (credentials: { email: string; password: string }) =>
      apiRequest<{
        access_token: string;
        token_type: string;
        user: {
          id: string;
          email: string;
          tenant_id: string;
          role: string;
          is_active: boolean;
          name?: string;
        };
      }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      }),

    register: (data: {
      gym_name: string;
      name: string;
      email: string;
      password: string;
      phone?: string;
      address?: string;
    }) =>
      apiRequest<{
        message?: string;
        access_token: string;
        token_type: string;
        tenant?: {
          id: string;
          name: string;
          email?: string;
          phone?: string;
          address?: string;
          timezone?: string;
          currency?: string;
        };
        user: { id: string; email: string; name?: string; tenant_id: string; role: string };
      }>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    me: () =>
      apiRequest<{
        id: string;
        email: string;
        tenant_id: string;
        role: string;
        is_active: boolean;
        name?: string;
        created_at: string;
        updated_at: string;
      }>("/auth/me", { method: "GET" }),

    logout: () => {
      clearActiveSession();
      return Promise.resolve({ success: true });
    },
  },

  // Dashboard Aggregates & Feeds
  dashboard: {
    summary: () =>
      apiRequest<{
        tenant_id: string;
        as_of: string;
        member_stats: {
          total_members: number;
          active_members: number;
          inactive_members: number;
          expired_memberships: number;
        };
        financial_stats: {
          total_revenue_paise: number;
          total_revenue_rupees: number;
          today_collection_paise: number;
          today_collection_rupees: number;
          monthly_collection_paise: number;
          monthly_collection_rupees: number;
          pending_payments_count: number;
          outstanding_dues_paise: number;
          outstanding_dues_rupees: number;
        };
        membership_stats: {
          active_memberships: number;
          expired_memberships: number;
          expiring_this_week: number;
          upcoming_renewals: number;
        };
        attendance_stats: {
          today_check_ins: number;
          monthly_attendance: number;
          daily_trends: Array<{ date: string; day_name: string; check_ins: number }>;
        };
        recent_payments: Array<{
          payment_id: string;
          invoice_number?: string;
          member_name: string;
          member_id: string;
          amount_rupees: number;
          payment_method: string;
          payment_status: string;
          payment_date: string;
        }>;
        upcoming_renewals: Array<{
          membership_id: string;
          member_id: string;
          member_name: string;
          phone?: string;
          plan_name: string;
          end_date: string;
          days_remaining: number;
        }>;
        pending_dues: Array<{
          invoice_id: string;
          invoice_number: string;
          member_id: string;
          member_name: string;
          phone?: string;
          due_date: string;
          balance_amount_rupees: number;
          days_overdue: number;
        }>;
        recent_registrations: Array<{
          member_id: string;
          full_name: string;
          phone?: string;
          email?: string;
          status: string;
          created_at: string;
        }>;
        recent_attendance: Array<{
          attendance_id: string;
          member_id: string;
          member_name: string;
          phone?: string;
          check_in_time: string;
          check_out_time?: string;
          check_in_method: string;
        }>;
      }>("/dashboard/summary", { method: "GET" }),
  },

  // Members Management
  members: {
    list: (params?: { page?: number; page_size?: number; search?: string; member_status?: string }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.search) qs.set("search", params.search);
      if (params?.member_status) qs.set("member_status", params.member_status);
      const queryStr = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          tenant_id: string;
          full_name: string;
          email?: string;
          phone?: string;
          gender?: string;
          date_of_birth?: string;
          address?: string;
          emergency_contact_name?: string;
          emergency_contact_phone?: string;
          status: string;
          created_at: string;
          updated_at: string;
        }>;
        total: number;
        page: number;
        page_size: number;
        pages: number;
      }>(`/members${queryStr ? `?${queryStr}` : ""}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        tenant_id: string;
        full_name: string;
        email?: string;
        phone?: string;
        gender?: string;
        date_of_birth?: string;
        address?: string;
        emergency_contact_name?: string;
        emergency_contact_phone?: string;
        status: string;
        created_at: string;
        updated_at: string;
      }>(`/members/${encodeURIComponent(id)}`, { method: "GET" }),

    create: (data: {
      full_name: string;
      email?: string;
      phone?: string;
      gender?: string;
      date_of_birth?: string;
      address?: string;
      emergency_contact_name?: string;
      emergency_contact_phone?: string;
    }) =>
      apiRequest<{
        id: string;
        full_name: string;
        email?: string;
        phone?: string;
        status: string;
      }>("/members", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: string, data: {
      full_name?: string;
      email?: string;
      phone?: string;
      gender?: string;
      date_of_birth?: string;
      address?: string;
      emergency_contact_name?: string;
      emergency_contact_phone?: string;
    }) =>
      apiRequest<{
        id: string;
        full_name: string;
        email?: string;
        phone?: string;
        status: string;
      }>(`/members/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    delete: (id: string) =>
      apiRequest<{ message: string; member_id: string }>(`/members/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),

    search: (q: string, params?: { page?: number; page_size?: number }) => {
      const qs = new URLSearchParams({ q });
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      return apiRequest<{
        items: Array<{
          id: string;
          full_name: string;
          email?: string;
          phone?: string;
          status: string;
        }>;
        total: number;
      }>(`/members/search?${qs.toString()}`, { method: "GET" });
    },
  },

  // Membership Plans
  membershipPlans: {
    list: (params?: { include_inactive?: boolean }) => {
      const qs = params?.include_inactive ? "?include_inactive=true" : "";
      return apiRequest<
        Array<{
          id: string;
          tenant_id: string;
          name: string;
          description?: string;
          duration_days: number;
          price_paise: number;
          is_active: boolean;
          created_at: string;
        }>
      >(`/membership-plans${qs}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        name: string;
        description?: string;
        duration_days: number;
        price_paise: number;
        is_active: boolean;
      }>(`/membership-plans/${encodeURIComponent(id)}`, { method: "GET" }),

    create: (data: {
      name: string;
      description?: string;
      duration_days: number;
      price_paise: number;
      is_active?: boolean;
    }) =>
      apiRequest<{
        id: string;
        name: string;
        duration_days: number;
        price_paise: number;
      }>("/membership-plans", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: string, data: {
      name?: string;
      description?: string;
      duration_days?: number;
      price_paise?: number;
      is_active?: boolean;
    }) =>
      apiRequest<{
        id: string;
        name: string;
        duration_days: number;
        price_paise: number;
      }>(`/membership-plans/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    deactivate: (id: string) =>
      apiRequest<{ message: string; plan_id: string }>(`/membership-plans/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
  },

  // Memberships Subscriptions
  memberships: {
    list: (params?: { page?: number; page_size?: number }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      const q = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          member_id: string;
          plan_id: string;
          start_date: string;
          end_date: string;
          status: string;
          created_at: string;
        }>;
        total: number;
      }>(`/memberships${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        member_id: string;
        plan_id: string;
        start_date: string;
        end_date: string;
        status: string;
      }>(`/memberships/${encodeURIComponent(id)}`, { method: "GET" }),

    create: (data: {
      member_id: string;
      plan_id: string;
      start_date?: string;
      auto_generate_invoice?: boolean;
    }) =>
      apiRequest<{
        id: string;
        member_id: string;
        plan_id: string;
        start_date: string;
        end_date: string;
        status: string;
      }>("/memberships", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    freeze: (id: string, data: { freeze_start_date: string; freeze_end_date: string; reason?: string }) =>
      apiRequest<{ id: string; status: string }>(`/memberships/${encodeURIComponent(id)}/freeze`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    unfreeze: (id: string, data?: { unfreeze_date?: string; reason?: string }) =>
      apiRequest<{ id: string; status: string }>(`/memberships/${encodeURIComponent(id)}/unfreeze`, {
        method: "POST",
        body: JSON.stringify(data || {}),
      }),

    renew: (id: string, data: { plan_id?: string; duration_days?: number; start_date?: string }) =>
      apiRequest<{ id: string; end_date: string; status: string }>(`/memberships/${encodeURIComponent(id)}/renew`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    upgrade: (id: string, data: { new_plan_id: string; effective_date?: string }) =>
      apiRequest<{ id: string; plan_id: string; status: string }>(`/memberships/${encodeURIComponent(id)}/upgrade`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    cancel: (id: string, data?: { reason?: string }) =>
      apiRequest<{ id: string; status: string }>(`/memberships/${encodeURIComponent(id)}/cancel`, {
        method: "POST",
        body: JSON.stringify(data || {}),
      }),
  },

  // Invoices & Billing
  invoices: {
    list: (params?: { page?: number; page_size?: number; member_id?: string; status?: string }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.member_id) qs.set("member_id", params.member_id);
      if (params?.status) qs.set("status", params.status);
      const q = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          member_id: string;
          invoice_number: string;
          amount_paise: number;
          paid_amount_paise: number;
          balance_amount_paise: number;
          invoice_status: string;
          issue_date: string;
          due_date: string;
          description?: string;
        }>;
        total: number;
        page: number;
        page_size: number;
      }>(`/invoices${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        member_id: string;
        invoice_number: string;
        amount_paise: number;
        paid_amount_paise: number;
        balance_amount_paise: number;
        invoice_status: string;
        issue_date: string;
        due_date: string;
        description?: string;
      }>(`/invoices/${encodeURIComponent(id)}`, { method: "GET" }),

    create: (data: {
      member_id: string;
      amount_paise: number;
      issue_date?: string;
      due_date?: string;
      description?: string;
      membership_id?: string;
    }) =>
      apiRequest<{
        id: string;
        invoice_number: string;
        amount_paise: number;
        balance_amount_paise: number;
        invoice_status: string;
      }>("/invoices", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: string, data: { due_date?: string; description?: string }) =>
      apiRequest<{ id: string; invoice_number: string }>(`/invoices/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    cancel: (id: string, data?: { reason?: string }) =>
      apiRequest<{ id: string; invoice_status: string }>(`/invoices/${encodeURIComponent(id)}/cancel`, {
        method: "POST",
        body: JSON.stringify(data || {}),
      }),

    getOutstandingDues: (memberId?: string) => {
      const q = memberId ? `?member_id=${encodeURIComponent(memberId)}` : "";
      return apiRequest<{
        tenant_id: string;
        member_id?: string;
        total_invoiced_paise: number;
        total_paid_paise: number;
        total_outstanding_paise: number;
        overdue_invoices_count: number;
      }>(`/invoices/outstanding-dues${q}`, { method: "GET" });
    },
  },

  // Payments, Refunds & Reversals
  payments: {
    list: (params?: { page?: number; page_size?: number; member_id?: string; payment_method?: string; status?: string }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.member_id) qs.set("member_id", params.member_id);
      if (params?.payment_method) qs.set("payment_method", params.payment_method);
      if (params?.status) qs.set("status", params.status);
      const q = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          tenant_id: string;
          member_id: string;
          invoice_id?: string;
          amount_paise: number;
          payment_method: string;
          payment_status: string;
          transaction_reference?: string;
          payment_date: string;
          notes?: string;
          receipt_number?: string;
          receipt_id?: string;
        }>;
        total: number;
        page: number;
        page_size: number;
      }>(`/payments${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        member_id: string;
        amount_paise: number;
        payment_method: string;
        payment_status: string;
        receipt_number?: string;
        payment_date: string;
      }>(`/payments/${encodeURIComponent(id)}`, { method: "GET" }),

    create: (data: {
      member_id: string;
      amount_paise: number;
      payment_method: "CASH" | "UPI" | "CARD" | "BANK_TRANSFER" | "CHEQUE";
      invoice_id?: string;
      transaction_reference?: string;
      notes?: string;
      auto_generate_receipt?: boolean;
    }) =>
      apiRequest<{
        id: string;
        member_id: string;
        amount_paise: number;
        payment_method: string;
        payment_status: string;
        receipt_number?: string;
        receipt_id?: string;
      }>("/payments", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    refund: (id: string, data: { amount_paise: number; reason?: string }) =>
      apiRequest<{ id: string; refund_amount_paise: number; status: string }>(
        `/payments/${encodeURIComponent(id)}/refund`,
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),

    reverse: (id: string, data: { reason: string }) =>
      apiRequest<{ id: string; status: string }>(`/payments/${encodeURIComponent(id)}/reverse`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    getDailySummary: (date?: string) => {
      const q = date ? `?target_date=${encodeURIComponent(date)}` : "";
      return apiRequest<{
        tenant_id: string;
        summary_date: string;
        total_collected_paise: number;
        total_refunded_paise: number;
        net_collection_paise: number;
        cash_collection_paise: number;
        upi_collection_paise: number;
        card_collection_paise: number;
        bank_transfer_collection_paise: number;
        cheque_collection_paise: number;
        transactions_count: number;
      }>(`/payments/daily-summary${q}`, { method: "GET" });
    },
  },

  // Receipts
  receipts: {
    getByPaymentId: (paymentId: string) =>
      apiRequest<{
        id: string;
        receipt_number: string;
        payment_id: string;
        tenant_id: string;
        amount_paise: number;
        created_at: string;
      }>(`/payments/${encodeURIComponent(paymentId)}/receipt`, { method: "GET" }),
  },

  // Attendance & Check-in
  attendance: {
    checkIn: (data: { member_id: string; override?: boolean; override_reason?: string }) =>
      apiRequest<{
        id: string;
        member_id: string;
        check_in_time: string;
        check_in_method: string;
        override: boolean;
      }>("/attendance/check-in", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    qrCheckIn: (data: { qr_code: string; override?: boolean; override_reason?: string }) =>
      apiRequest<{
        id: string;
        member_id: string;
        check_in_time: string;
        check_in_method: string;
        override: boolean;
      }>("/attendance/qr-check-in", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    checkOut: (attendanceId: string, data?: { notes?: string }) =>
      apiRequest<{
        id: string;
        check_out_time: string;
      }>(`/attendance/${encodeURIComponent(attendanceId)}/check-out`, {
        method: "POST",
        body: JSON.stringify(data || {}),
      }),

    getToday: () =>
      apiRequest<
        Array<{
          id: string;
          member_id: string;
          member_name: string;
          phone?: string;
          check_in_time: string;
          check_out_time?: string;
          check_in_method: string;
          override: boolean;
        }>
      >("/attendance/today", { method: "GET" }),

    getHistory: (params?: { page?: number; page_size?: number; member_id?: string; date?: string }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      if (params?.member_id) qs.set("member_id", params.member_id);
      if (params?.date) qs.set("date", params.date);
      const q = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          member_id: string;
          member_name: string;
          check_in_time: string;
          check_out_time?: string;
          check_in_method: string;
        }>;
        total: number;
      }>(`/attendance/history${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getAnalytics: (days?: number) => {
      const q = days ? `?days=${days}` : "";
      return apiRequest<{
        total_visits: number;
        unique_members: number;
        peak_hours: Array<{ hour: number; count: number }>;
      }>(`/attendance/analytics${q}`, { method: "GET" });
    },

    searchMember: (q: string) =>
      apiRequest<
        Array<{
          id: string;
          full_name: string;
          phone?: string;
          status: string;
          has_active_membership: boolean;
          membership_status?: string;
        }>
      >(`/attendance/member-search?q=${encodeURIComponent(q)}`, { method: "GET" }),
  },

  // Reminders & Expiry Worklists
  reminders: {
    getExpiryWorklist: (params?: { category?: string; warning_days?: number }) => {
      const qs = new URLSearchParams();
      if (params?.category) qs.set("category", params.category);
      if (params?.warning_days) qs.set("warning_days", String(params.warning_days));
      const q = qs.toString();
      return apiRequest<
        Array<{
          member_id: string;
          member_name: string;
          phone?: string;
          plan_name: string;
          end_date: string;
          status: string;
          days_relative: number;
          dues_paise: number;
        }>
      >(`/reminders/expiry-worklist${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getRenewalFollowups: (params?: { status_filter?: string; q?: string }) => {
      const qs = new URLSearchParams();
      if (params?.status_filter) qs.set("status_filter", params.status_filter);
      if (params?.q) qs.set("q", params.q);
      const q = qs.toString();
      return apiRequest<
        Array<{
          followup_id?: string;
          member_id: string;
          member_name: string;
          phone?: string;
          plan_name: string;
          scheduled_date?: string;
          status: string;
        }>
      >(`/reminders/renewal-followup${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getOutstandingDues: (params?: { ageing?: string; q?: string }) => {
      const qs = new URLSearchParams();
      if (params?.ageing) qs.set("ageing", params.ageing);
      if (params?.q) qs.set("q", params.q);
      const q = qs.toString();
      return apiRequest<
        Array<{
          invoice_id: string;
          member_id: string;
          member_name: string;
          phone?: string;
          invoice_number: string;
          due_date: string;
          balance_paise: number;
          ageing_bucket: string;
        }>
      >(`/reminders/outstanding-dues${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getBirthdays: (params?: { upcoming_days?: number; is_today_only?: boolean }) => {
      const qs = new URLSearchParams();
      if (params?.upcoming_days) qs.set("upcoming_days", String(params.upcoming_days));
      if (params?.is_today_only) qs.set("is_today_only", "true");
      const q = qs.toString();
      return apiRequest<
        Array<{
          member_id: string;
          member_name: string;
          phone?: string;
          date_of_birth: string;
          is_today: boolean;
        }>
      >(`/reminders/birthday${q ? `?${q}` : ""}`, { method: "GET" });
    },

    generateWhatsAppMessage: (data: {
      template_type: "EXPIRY" | "RENEWAL" | "DUE" | "BIRTHDAY";
      member_id: string;
      membership_id?: string;
      invoice_id?: string;
    }) =>
      apiRequest<{
        message_text: string;
        recipient_phone: string;
        encoded_url: string;
      }>("/reminders/whatsapp-message", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    logContact: (data: {
      member_id: string;
      contact_method: "WHATSAPP" | "CALL" | "SMS" | "IN_PERSON";
      outcome: string;
      notes?: string;
    }) =>
      apiRequest<{ id: string; member_id: string; created_at: string }>("/reminders/log-contact", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    getContactHistory: (memberId: string, page = 1) =>
      apiRequest<{
        items: Array<{
          id: string;
          member_id: string;
          contact_method: string;
          outcome: string;
          notes?: string;
          created_at: string;
        }>;
        total: number;
      }>(`/reminders/contacts/${encodeURIComponent(memberId)}?page=${page}`, { method: "GET" }),

    scheduleFollowup: (data: {
      member_id: string;
      scheduled_date: string;
      task_type: string;
      notes?: string;
      staff_user_id?: string;
    }) =>
      apiRequest<{ id: string; member_id: string; scheduled_date: string }>("/reminders/schedule-followup", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    getScheduledFollowups: (params?: { is_overdue?: boolean; staff_user_id?: string }) => {
      const qs = new URLSearchParams();
      if (params?.is_overdue) qs.set("is_overdue", "true");
      if (params?.staff_user_id) qs.set("staff_user_id", params.staff_user_id);
      const q = qs.toString();
      return apiRequest<
        Array<{
          id: string;
          member_id: string;
          member_name: string;
          scheduled_date: string;
          is_overdue: boolean;
        }>
      >(`/reminders/followups${q ? `?${q}` : ""}`, { method: "GET" });
    },
  },

  // Reports
  reports: {
    getRevenue: (params?: { start_date?: string; end_date?: string; payment_method?: string }) => {
      const qs = new URLSearchParams();
      if (params?.start_date) qs.set("start_date", params.start_date);
      if (params?.end_date) qs.set("end_date", params.end_date);
      if (params?.payment_method) qs.set("payment_method", params.payment_method);
      const q = qs.toString();
      return apiRequest<{
        total_collected_rupees: number;
        total_refunded_rupees: number;
        net_revenue_rupees: number;
        items: Array<{
          payment_id: string;
          member_name: string;
          amount_rupees: number;
          payment_method: string;
          payment_date: string;
        }>;
      }>(`/reports/revenue${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getMemberships: (params?: { plan_id?: string; status?: string }) => {
      const qs = new URLSearchParams();
      if (params?.plan_id) qs.set("plan_id", params.plan_id);
      if (params?.status) qs.set("status", params.status);
      const q = qs.toString();
      return apiRequest<{
        total_memberships: number;
        items: Array<{
          membership_id: string;
          member_name: string;
          plan_name: string;
          status: string;
          start_date: string;
          end_date: string;
        }>;
      }>(`/reports/memberships${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getAttendance: (params?: { start_date?: string; end_date?: string }) => {
      const qs = new URLSearchParams();
      if (params?.start_date) qs.set("start_date", params.start_date);
      if (params?.end_date) qs.set("end_date", params.end_date);
      const q = qs.toString();
      return apiRequest<{
        total_check_ins: number;
        items: Array<{
          attendance_id: string;
          member_name: string;
          check_in_time: string;
          check_out_time?: string;
          check_in_method: string;
        }>;
      }>(`/reports/attendance${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getPendingDues: (params?: { ageing?: string }) => {
      const qs = new URLSearchParams();
      if (params?.ageing) qs.set("ageing", params.ageing);
      const q = qs.toString();
      return apiRequest<{
        total_outstanding_rupees: number;
        items: Array<{
          invoice_id: string;
          member_name: string;
          invoice_number: string;
          balance_rupees: number;
          due_date: string;
          days_overdue: number;
        }>;
      }>(`/reports/pending-dues${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getExpiries: (params?: { category?: string }) => {
      const qs = new URLSearchParams();
      if (params?.category) qs.set("category", params.category);
      const q = qs.toString();
      return apiRequest<{
        total_records: number;
        items: Array<{
          member_name: string;
          plan_name: string;
          end_date: string;
          status: string;
        }>;
      }>(`/reports/expiries${q ? `?${q}` : ""}`, { method: "GET" });
    },
  },

  // Imports
  imports: {
    importMembers: (file: File | Blob, dryRun = false) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiRequest<{
        success: boolean;
        total_rows: number;
        imported_count: number;
        failed_count: number;
        errors: Array<{ row: number; reason: string }>;
      }>(`/imports/members?dry_run=${dryRun ? "true" : "false"}`, {
        method: "POST",
        body: fd,
      });
    },

    importMemberships: (file: File | Blob, dryRun = false) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiRequest<{
        success: boolean;
        total_rows: number;
        imported_count: number;
        failed_count: number;
        errors: Array<{ row: number; reason: string }>;
      }>(`/imports/memberships?dry_run=${dryRun ? "true" : "false"}`, {
        method: "POST",
        body: fd,
      });
    },

    importPayments: (file: File | Blob, dryRun = false) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiRequest<{
        success: boolean;
        total_rows: number;
        imported_count: number;
        failed_count: number;
        errors: Array<{ row: number; reason: string }>;
      }>(`/imports/payments?dry_run=${dryRun ? "true" : "false"}`, {
        method: "POST",
        body: fd,
      });
    },
  },

  // Exports (Binary downloads)
  exports: {
    downloadMembers: (format: "csv" | "xlsx" = "csv", isActive?: boolean) => {
      const qs = new URLSearchParams({ format });
      if (typeof isActive === "boolean") qs.set("is_active", String(isActive));
      return apiDownload(`/exports/members?${qs.toString()}`, `members_export_${Date.now()}.${format}`);
    },

    downloadMemberships: (format: "csv" | "xlsx" = "csv", status?: string) => {
      const qs = new URLSearchParams({ format });
      if (status) qs.set("status", status);
      return apiDownload(`/exports/memberships?${qs.toString()}`, `memberships_export_${Date.now()}.${format}`);
    },

    downloadPayments: (format: "csv" | "xlsx" = "csv", paymentMethod?: string) => {
      const qs = new URLSearchParams({ format });
      if (paymentMethod) qs.set("payment_method", paymentMethod);
      return apiDownload(`/exports/payments?${qs.toString()}`, `payments_export_${Date.now()}.${format}`);
    },

    downloadAttendance: (format: "csv" | "xlsx" = "csv", startDate?: string) => {
      const qs = new URLSearchParams({ format });
      if (startDate) qs.set("start_date", startDate);
      return apiDownload(`/exports/attendance?${qs.toString()}`, `attendance_export_${Date.now()}.${format}`);
    },

    downloadReport: (reportType: "revenue" | "memberships" | "attendance" | "pending_dues" | "expiries", format: "csv" | "xlsx" = "csv") => {
      return apiDownload(`/exports/reports/${reportType}?format=${format}`, `${reportType}_report_${Date.now()}.${format}`);
    },
  },

  // Staff Management (RBAC Enforced)
  staff: {
    list: (params?: { role?: string; is_active?: boolean }) => {
      const qs = new URLSearchParams();
      if (params?.role) qs.set("role", params.role);
      if (typeof params?.is_active === "boolean") qs.set("is_active", String(params.is_active));
      const q = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          email: string;
          role: string;
          is_active: boolean;
          name?: string;
          phone?: string;
          created_at: string;
        }>;
        total: number;
        page: number;
        page_size: number;
        pages: number;
      }>(`/staff${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        email: string;
        role: string;
        is_active: boolean;
        name?: string;
        phone?: string;
        created_at: string;
      }>(`/staff/${encodeURIComponent(id)}`, { method: "GET" }),

    create: (data: {
      email: string;
      name?: string;
      password?: string;
      role: "MANAGER" | "FRONT_DESK";
      phone?: string;
    }) =>
      apiRequest<{
        id: string;
        email: string;
        role: string;
        is_active: boolean;
        name?: string;
      }>("/staff", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: string, data: { name?: string; email?: string; phone?: string }) =>
      apiRequest<{
        id: string;
        email: string;
        role: string;
        name?: string;
      }>(`/staff/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    updateStatus: (id: string, data: { is_active: boolean; reason?: string }) =>
      apiRequest<{
        id: string;
        email: string;
        is_active: boolean;
      }>(`/staff/${encodeURIComponent(id)}/status`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    updateRole: (id: string, data: { role: "MANAGER" | "FRONT_DESK"; reason?: string }) =>
      apiRequest<{
        id: string;
        email: string;
        role: string;
      }>(`/staff/${encodeURIComponent(id)}/role`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  // Audit Logs (Immutable Read-Only)
  audit: {
    list: (params?: {
      start_date?: string;
      end_date?: string;
      user_id?: string;
      action?: string;
      resource_type?: string;
      resource_id?: string;
      page?: number;
      page_size?: number;
    }) => {
      const qs = new URLSearchParams();
      if (params?.start_date) qs.set("start_date", params.start_date);
      if (params?.end_date) qs.set("end_date", params.end_date);
      if (params?.user_id) qs.set("user_id", params.user_id);
      if (params?.action) qs.set("action", params.action);
      if (params?.resource_type) qs.set("resource_type", params.resource_type);
      if (params?.resource_id) qs.set("resource_id", params.resource_id);
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      const q = qs.toString();
      return apiRequest<{
        items: Array<{
          id: string;
          tenant_id: string;
          user_id?: string;
          action: string;
          resource_type: string;
          resource_id?: string;
          details?: Record<string, unknown>;
          ip_address?: string;
          created_at: string;
        }>;
        total: number;
        page: number;
        page_size: number;
        pages: number;
      }>(`/audit-logs${q ? `?${q}` : ""}`, { method: "GET" });
    },

    getById: (id: string) =>
      apiRequest<{
        id: string;
        tenant_id: string;
        user_id?: string;
        action: string;
        resource_type: string;
        resource_id?: string;
        details?: Record<string, unknown>;
        ip_address?: string;
        created_at: string;
      }>(`/audit-logs/${encodeURIComponent(id)}`, { method: "GET" }),
  },
};
