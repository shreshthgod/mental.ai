/**
 * mental.ai API client - the single transport layer to the FastAPI backend.
 * No component performs fetch() directly.
 */

export interface PrimaryResult {
  predicted_class: string;
  class_probabilities: Record<string, number>;
}

export interface UrgencyResult {
  predicted_class: string;
  suicide_probability: number;
  decision_threshold_used: number;
  flagged: boolean;
}

export interface PredictResponse {
  request_id: string;
  primary: PrimaryResult;
  urgency: UrgencyResult;
  cleaned_text?: string | null;
  lemmatized_text?: string | null;
  provenance_caveat?: string | null;
  service_version: string;
}

export interface HealthResponse {
  status: string;
  service_version: string;
  artifacts_ok: boolean;
  artifacts_detail: Record<string, string>;
  screener_available: boolean;
}

export interface LoginResponse {
  token: string;
  token_type: string;
  expires_in: number;
  expires_at: number;
  user: string;
  name: string;
}

export interface SessionResponse {
  user: string;
  name: string;
  issued_at: number;
  expires_at: number;
  service_version: string;
}

export type ApiErrorKind =
  | "validation"
  | "server"
  | "unavailable"
  | "timeout"
  | "unauthorized"
  | "throttled";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  requestId?: string;

  constructor(kind: ApiErrorKind, message: string, status?: number, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.requestId = requestId;
  }
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

const HEALTH_TIMEOUT_MS = 8_000;
const PREDICT_TIMEOUT_MS = 30_000;
const AUTH_TIMEOUT_MS = 10_000;

/**
 * Bearer token for authenticated calls.
 *
 * Held in memory by the auth store. Read lazily through this indirection so
 * api.ts never has to import the store (which would create a cycle) and so
 * sign-out takes effect on the very next request.
 */
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

function combineSignals(a: AbortSignal, b: AbortSignal): AbortSignal {
  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort(a.aborted ? a.reason : b.reason);
  a.addEventListener("abort", onAbort, { once: true });
  b.addEventListener("abort", onAbort, { once: true });
  return ctrl.signal;
}

async function doRequest<T>(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  callerSignal?: AbortSignal
): Promise<T> {
  const timeoutCtrl = new AbortController();
  const timer = setTimeout(() => timeoutCtrl.abort("timeout"), timeoutMs);
  const signal = callerSignal ? combineSignals(callerSignal, timeoutCtrl.signal) : timeoutCtrl.signal;

  let res: Response;
  try {
    const headers = new Headers(init.headers);
    if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
    res = await fetch(`${BASE}${path}`, { ...init, headers, signal });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      if (callerSignal?.aborted) throw err;
      throw new ApiError("timeout", `Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw new ApiError("unavailable", "The screening service could not be reached.");
  }
  clearTimeout(timer);

  const requestId = res.headers.get("X-Request-ID") ?? undefined;

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = "Request validation failed.";
    } catch {
      /* non-JSON error body */
    }
    if (res.status === 401) throw new ApiError("unauthorized", detail, res.status, requestId);
    if (res.status === 429) throw new ApiError("throttled", detail, res.status, requestId);
    if (res.status === 422) throw new ApiError("validation", detail, res.status, requestId);
    if (res.status === 503) throw new ApiError("unavailable", detail, res.status, requestId);
    throw new ApiError("server", detail, res.status, requestId);
  }

  return (await res.json()) as T;
}

export const api = {
  predict(text: string, signal?: AbortSignal): Promise<PredictResponse> {
    return doRequest<PredictResponse>(
      "/predict",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      },
      PREDICT_TIMEOUT_MS,
      signal
    );
  },
  health(signal?: AbortSignal): Promise<HealthResponse> {
    return doRequest<HealthResponse>("/health", { method: "GET" }, HEALTH_TIMEOUT_MS, signal);
  },
  ready(signal?: AbortSignal): Promise<{ ready: boolean; service_version: string }> {
    return doRequest("/ready", { method: "GET" }, HEALTH_TIMEOUT_MS, signal);
  },
  /**
   * Exchange credentials for a bearer token.
   *
   * Sent with an explicitly empty Authorization header: a stale token from a
   * previous session must never be attached to a sign-in attempt.
   */
  login(userId: string, password: string, signal?: AbortSignal): Promise<LoginResponse> {
    return doRequest<LoginResponse>(
      "/auth/login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "" },
        body: JSON.stringify({ user_id: userId, password }),
      },
      AUTH_TIMEOUT_MS,
      signal
    );
  },
  /** Validate the stored token. Used on boot to confirm a session is still live. */
  session(signal?: AbortSignal): Promise<SessionResponse> {
    return doRequest<SessionResponse>("/auth/session", { method: "GET" }, HEALTH_TIMEOUT_MS, signal);
  },
};

export const MAX_TEXT_LENGTH = 10_000;
