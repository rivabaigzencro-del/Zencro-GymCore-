/**
 * GYMCORE API Integration Client Layer
 * Prepared for FastAPI backend developed by Riva (FastAPI, SQLAlchemy, Pydantic, JWT).
 * Dual-mode design: Gracefully routes requests to backend when reachable,
 * and seamlessly provides fallback so existing frontend functionality is never broken.
 */

export interface ApiClientConfig {
  baseUrl: string;
  timeoutMs: number;
}

const DEFAULT_CONFIG: ApiClientConfig = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  timeoutMs: 8000,
};

const TOKEN_STORAGE_KEY = "gymcore_auth_token_jwt";
const REFRESH_TOKEN_STORAGE_KEY = "gymcore_refresh_token_jwt";
const SESSION_STORAGE_KEY = "gymcore_user_session";

export type UserRole = "Owner" | "Manager" | "Front Desk";

export interface UserSession {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  title?: string;
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

let cachedSession: UserSession | null = null;
let cachedRaw: string | null = null;

export function getActiveSession(): UserSession {
  if (typeof window === "undefined") {
    return DEMO_ACCOUNTS["owner@gymcore.com"];
  }
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) {
      cachedSession = DEMO_ACCOUNTS["owner@gymcore.com"];
      cachedRaw = null;
      return cachedSession;
    }
    if (raw === cachedRaw && cachedSession) {
      return cachedSession;
    }
    cachedRaw = raw;
    cachedSession = JSON.parse(raw);
    return cachedSession!;
  } catch {
    return DEMO_ACCOUNTS["owner@gymcore.com"];
  }
}

export function setActiveSession(session: UserSession): void {
  if (typeof window === "undefined") return;
  cachedRaw = JSON.stringify(session);
  cachedSession = session;
  localStorage.setItem(SESSION_STORAGE_KEY, cachedRaw);
  window.dispatchEvent(new Event("gymcore_session_change"));
}

export function clearActiveSession(): void {
  if (typeof window === "undefined") return;
  cachedRaw = null;
  cachedSession = DEMO_ACCOUNTS["owner@gymcore.com"];
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

/**
 * Token Storage & Retrieval
 */
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

/**
 * Core HTTP Request Dispatcher
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = getStoredAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${DEFAULT_CONFIG.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_CONFIG.timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle 401 Unauthorized (Expired or invalid JWT)
    if (response.status === 401) {
      clearStoredAuthTokens();
      return {
        success: false,
        error: "Session expired or unauthorized. Please re-authenticate.",
        statusCode: 401,
      };
    }

    // Parse Response
    const json = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMsg = json?.detail || json?.message || `API error (${response.status}): ${response.statusText}`;
      return {
        success: false,
        error: typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg),
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
        ? "API request timed out (FastAPI server unreachable)"
        : `Network or connection failure: ${(err as Error)?.message || "FastAPI offline"}`,
      statusCode: 0,
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
    const res = await apiRequest<{ status: string; version?: string }>("/health");
    const latencyMs = Date.now() - start;
    if (res.success && res.data?.status === "ok") {
      return { isOnline: true, latencyMs, baseUrl: DEFAULT_CONFIG.baseUrl };
    }
    return {
      isOnline: false,
      latencyMs,
      baseUrl: DEFAULT_CONFIG.baseUrl,
      error: res.error || "Backend returned non-ok health status",
    };
  } catch (err) {
    return {
      isOnline: false,
      latencyMs: Date.now() - start,
      baseUrl: DEFAULT_CONFIG.baseUrl,
      error: (err as Error).message,
    };
  }
}

/**
 * Typed API Endpoints Spec
 */
export const api = {
  // Authentication
  auth: {
    login: (credentials: { username: string; password: string }) =>
      apiRequest<{ access_token: string; token_type: string; user: { id: string; name: string; role: string } }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify(credentials),
        }
      ),
    me: () =>
      apiRequest<{ id: string; name: string; email: string; role: string }>("/auth/me", {
        method: "GET",
      }),
    logout: () => {
      clearStoredAuthTokens();
      return Promise.resolve({ success: true });
    },
  },

  // Staff Management Endpoints
  staff: {
    list: () =>
      apiRequest<
        Array<{
          id: string;
          name: string;
          role: string;
          phone: string;
          email: string;
          joiningDate: string;
          salary: number;
          status: string;
        }>
      >("/staff", { method: "GET" }),
    getById: (id: string) => apiRequest<unknown>(`/staff/${encodeURIComponent(id)}`, { method: "GET" }),
    create: (staffData: unknown) =>
      apiRequest<unknown>("/staff", {
        method: "POST",
        body: JSON.stringify(staffData),
      }),
    update: (id: string, staffData: unknown) =>
      apiRequest<unknown>(`/staff/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(staffData),
      }),
    toggleStatus: (id: string) =>
      apiRequest<unknown>(`/staff/${encodeURIComponent(id)}/status`, {
        method: "PATCH",
      }),
    delete: (id: string) =>
      apiRequest<{ message: string }>(`/staff/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
  },

  // Audit Logs Endpoints
  audit: {
    list: (params?: {
      search?: string;
      entity_type?: string;
      severity?: string;
      page?: number;
      limit?: number;
    }) => {
      const query = new URLSearchParams();
      if (params?.search) query.set("search", params.search);
      if (params?.entity_type) query.set("entity_type", params.entity_type);
      if (params?.severity) query.set("severity", params.severity);
      if (params?.page) query.set("page", String(params.page));
      if (params?.limit) query.set("limit", String(params.limit));
      const qs = query.toString();
      return apiRequest<unknown[]>(`/audit-logs${qs ? `?${qs}` : ""}`, {
        method: "GET",
      });
    },
    create: (logData: unknown) =>
      apiRequest<unknown>("/audit-logs", {
        method: "POST",
        body: JSON.stringify(logData),
      }),
  },

  // Members Endpoints
  members: {
    list: () => apiRequest<unknown[]>("/members", { method: "GET" }),
    getById: (id: string) => apiRequest<unknown>(`/members/${encodeURIComponent(id)}`, { method: "GET" }),
    create: (data: unknown) =>
      apiRequest<unknown>("/members", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: unknown) =>
      apiRequest<unknown>(`/members/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) =>
      apiRequest<{ message: string }>(`/members/${encodeURIComponent(id)}`, { method: "DELETE" }),
  },

  // Attendance Endpoints
  attendance: {
    list: () => apiRequest<unknown[]>("/attendance", { method: "GET" }),
    checkIn: (payload: { memberId: string; overrideReason?: string }) =>
      apiRequest<unknown>("/attendance/check-in", { method: "POST", body: JSON.stringify(payload) }),
    checkOut: (attendanceId: string) =>
      apiRequest<unknown>(`/attendance/${encodeURIComponent(attendanceId)}/check-out`, { method: "POST" }),
  },

  // Payments Endpoints
  payments: {
    list: () => apiRequest<unknown[]>("/payments", { method: "GET" }),
    collect: (data: unknown) =>
      apiRequest<unknown>("/payments/collect", { method: "POST", body: JSON.stringify(data) }),
  },
};

