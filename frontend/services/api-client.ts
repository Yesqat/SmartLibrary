import { kk } from "@/locales/kk";
import { catalogErrors } from "@/locales/catalog";
import { searchText } from "@/locales/search";
import { reservationErrors } from "@/locales/reservations";
import { circulationErrors } from "@/locales/circulation";
import { adminErrors } from "@/locales/admin";
import { recommendations } from "@/locales/recommendations";
import { categorization } from "@/locales/categorization";
import { assistant } from "@/locales/assistant";
import { reports } from "@/locales/reports";
import type { components } from "@/types/api.generated";

export type User = components["schemas"]["UserResponse"];
type AuthResponse = components["schemas"]["AuthResponse"];
export type Session = components["schemas"]["SessionResponse"];
export type AuthState = {
  status: "loading" | "authenticated" | "anonymous" | "error";
  user: User | null;
};
let accessToken: string | null = null;
let state: AuthState = { status: "loading", user: null };
const serverState: AuthState = { status: "loading", user: null };
const listeners = new Set<() => void>();
let refreshPromise: Promise<User | null> | null = null;
let revision = 0;

export const getAuthState = () => state;
export const getServerAuthState = () => serverState;
export function subscribeAuth(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
function publish(next: AuthState) {
  state = next;
  listeners.forEach((listener) => listener());
}
function acceptSession(result: AuthResponse) {
  revision += 1;
  accessToken = result.access_token;
  publish({ status: "authenticated", user: result.user });
}
export function clearSession() {
  revision += 1;
  accessToken = null;
  publish({ status: "anonymous", user: null });
}
function notifyLogout() {
  if (typeof BroadcastChannel !== "undefined") {
    const channel = new BroadcastChannel("smartlibrary-auth");
    channel.postMessage("logout");
    channel.close();
  }
}
// Serializes cookie rotation across tabs. No credential is stored in browser storage.
async function sessionLock<T>(operation: () => Promise<T>): Promise<T> {
  if (typeof navigator !== "undefined" && navigator.locks) {
    return navigator.locks.request("smartlibrary-auth", operation);
  }
  return operation();
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
  ) {
    super(
      kk.auth.errors[code as keyof typeof kk.auth.errors] ??
        adminErrors[code] ??
        catalogErrors[code as keyof typeof catalogErrors] ??
        reservationErrors[code] ??
        circulationErrors[code] ??
        (code === "REPORT_GENERATION_FAILED" ? reports.failed : undefined) ??
        (code === "REPORT_TOO_LARGE" ? reports.large : undefined) ??
        (code === "AI_SERVICE_UNAVAILABLE"
          ? assistant.unavailable
          : undefined) ??
        (code === "AI_TURN_IN_PROGRESS" ? assistant.busy : undefined) ??
        (code === "AI_TURN_INTERRUPTED" ? assistant.interrupted : undefined) ??
        (code === "AI_LIMIT_REACHED" ? assistant.limit : undefined) ??
        (code === "CATEGORIZATION_UNAVAILABLE"
          ? categorization.unavailable
          : undefined) ??
        (code === "STALE_PREDICTION" ? categorization.stale : undefined) ??
        (code === "PREDICTION_ALREADY_REVIEWED"
          ? categorization.reviewed
          : undefined) ??
        (code === "INVALID_RECOMMENDATION"
          ? recommendations.invalid
          : undefined) ??
        (code === "SEMANTIC_SEARCH_UNAVAILABLE"
          ? searchText.semanticUnavailable
          : undefined) ??
        (code === "SEARCH_FAILED" ? searchText.failed : undefined) ??
        kk.error,
    );
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  decode?: (response: Response) => Promise<T>,
): Promise<T> {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("\\"))
    throw new Error("API path must be relative");
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const code =
      body &&
      typeof body === "object" &&
      "error" in body &&
      body.error &&
      typeof body.error === "object" &&
      "code" in body.error &&
      typeof body.error.code === "string"
        ? body.error.code
        : "REQUEST_FAILED";
    throw new ApiError(response.status, code);
  }
  if (response.status === 204) return undefined as T;
  if (decode) return decode(response);
  return response.json() as Promise<T>;
}

async function csrfHeaders(): Promise<Headers> {
  const result =
    await request<components["schemas"]["CSRFResponse"]>("/auth/csrf");
  return new Headers({
    "X-CSRF-Token": result.csrf_token,
    "Content-Type": "application/json",
  });
}

export function refreshSession(): Promise<User | null> {
  if (!refreshPromise) {
    refreshPromise = sessionLock(async () => {
      const started = revision;
      try {
        const result = await request<AuthResponse>("/auth/refresh", {
          method: "POST",
          headers: await csrfHeaders(),
        });
        if (started !== revision) return state.user;
        acceptSession(result);
        return result.user;
      } catch (error) {
        if (started !== revision) return state.user;
        if (
          error instanceof ApiError &&
          (error.status === 401 ||
            ["USER_BLOCKED", "ACCOUNT_INACTIVE"].includes(error.code))
        ) {
          clearSession();
          return null;
        }
        accessToken = null;
        publish({ status: "error", user: null });
        throw error;
      }
    }).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  decode?: (response: Response) => Promise<T>,
): Promise<T> {
  const send = () => {
    const headers = new Headers(init.headers);
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    return request<T>(path, { ...init, headers }, decode);
  };
  try {
    return await send();
  } catch (error) {
    if (
      error instanceof ApiError &&
      accessToken &&
      error.status === 401 &&
      ["TOKEN_EXPIRED", "TOKEN_INVALID", "UNAUTHORIZED"].includes(error.code)
    ) {
      if (await refreshSession()) return send();
    }
    if (
      error instanceof ApiError &&
      ["USER_BLOCKED", "ACCOUNT_INACTIVE"].includes(error.code)
    )
      clearSession();
    throw error;
  }
}

// Domain mutations authenticate exclusively with Bearer tokens. The browser supplies Origin;
export type Download = { blob: Blob; filename: string; rows: number };
export function apiDownload(path: string, data: unknown): Promise<Download> {
  return apiRequest(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    async (response) => {
      const filename =
        response.headers
          .get("Content-Disposition")
          ?.match(/filename="([a-z0-9_.-]+)"/i)?.[1] ?? "smartlibrary_report";
      return {
        blob: await response.blob(),
        filename,
        rows: Number(response.headers.get("X-Report-Rows") ?? 0),
      };
    },
  );
}

// Domain mutations authenticate exclusively with Bearer tokens. The browser supplies Origin;
// cookie-authenticated auth routes retain their separate cookie-bound CSRF proof.
export function apiMutation<T>(
  path: string,
  method: "POST" | "PATCH" | "DELETE",
  data?: unknown,
) {
  const form = data instanceof FormData;
  return apiRequest<T>(path, {
    method,
    headers: form ? undefined : { "Content-Type": "application/json" },
    body: data === undefined ? undefined : form ? data : JSON.stringify(data),
  });
}

export async function register(data: components["schemas"]["RegisterInput"]) {
  return sessionLock(async () =>
    request<User>("/auth/register", {
      method: "POST",
      headers: await csrfHeaders(),
      body: JSON.stringify(data),
    }),
  );
}
export async function login(data: components["schemas"]["LoginInput"]) {
  return sessionLock(async () => {
    const result = await request<AuthResponse>("/auth/login", {
      method: "POST",
      headers: await csrfHeaders(),
      body: JSON.stringify(data),
    });
    acceptSession(result);
    return result.user;
  });
}
export async function logout() {
  return sessionLock(async () => {
    await request<void>("/auth/logout", {
      method: "POST",
      headers: await csrfHeaders(),
    });
    clearSession();
    notifyLogout();
  });
}
export async function checkSession() {
  if (!accessToken) return refreshSession();
  const started = revision;
  try {
    const user = await apiRequest<User>("/auth/me");
    if (started !== revision) return state.user;
    publish({ status: "authenticated", user });
    return user;
  } catch (error) {
    if (started !== revision) return state.user;
    if (error instanceof ApiError && [401, 403].includes(error.status))
      clearSession();
    else publish({ status: "error", user: null });
    throw error;
  }
}
export async function changePassword(
  data: components["schemas"]["PasswordChangeInput"],
) {
  await checkSession();
  return sessionLock(async () => {
    const headers = await csrfHeaders();
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    await request<void>("/auth/change-password", {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
    clearSession();
    notifyLogout();
  });
}
export async function revokeSession(session: Session) {
  await checkSession();
  return sessionLock(async () => {
    const headers = await csrfHeaders();
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    await request<void>(`/auth/sessions/${session.id}`, {
      method: "DELETE",
      headers,
    });
    if (session.current) {
      clearSession();
      notifyLogout();
    }
  });
}
