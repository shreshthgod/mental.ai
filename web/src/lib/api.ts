/**
 * mental.ai API client - the single transport layer to the FastAPI backend.
 * No component performs fetch() directly.
 */

import type { AnalysisResult, ConfigurationResponse, PredictResponse } from "./contract";
import { parseConfiguration, parsePrediction } from "./analysisView";
export type { AnalysisResult, ConfigurationResponse, PredictResponse, PrimaryResult, UrgencyResult } from "./contract";

/**
 * A session as the service returns it.
 *
 * `token` is the Supabase access token FastAPI verifies on every call.
 * `refresh_token` is exchanged for a new access token without asking the
 * visitor to sign in again. `user_id` is the authoritative Supabase Auth UUID;
 * `user` is the human-facing id the interface already displays.
 */
export interface SessionPayload {
  token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  expires_at: number;
  user: string;
  user_id: string;
  name: string;
}

/** One stored screening, as returned by GET /screenings. */
export interface ScreeningSummary {
  id: string;
  created_at: string;
  condition_label?: string | null;
  condition_probabilities?: Record<string, number>;
  urgency_label?: string | null;
  urgency_probability?: number | null;
  urgency_flagged?: boolean;
  provenance_caveat?: string | null;
  analysis_result: AnalysisResult | null;
  assessment_kind: "authoritative" | "legacy_unassessed";
}

export interface HealthResponse {
  status: string;
  service_version: string;
  artifacts_ok: boolean;
  artifacts_detail: Record<string, string>;
  screener_available: boolean;
}

/**
 * Sign-in returns the same shape as a refresh.
 *
 * Kept as a name so the sign-in call site reads as sign-in; there is exactly one
 * payload shape in the system.
 */
export type LoginResponse = SessionPayload;

export interface SessionResponse {
  user: string;
  /** Authoritative Supabase Auth user id. Never displayed. */
  user_id: string;
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
  retryAfterSeconds?: number;

  constructor(kind: ApiErrorKind, message: string, status?: number, requestId?: string, retryAfterSeconds?: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.requestId = requestId;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

const HEALTH_TIMEOUT_MS = 8_000;
// Covers maximum provider wait30s + inference30s + save12s, with delivery margin.
const PREDICT_TIMEOUT_MS = 80_000;
const AUTH_TIMEOUT_MS = 35_000;

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

function combineSignals(a: AbortSignal, b: AbortSignal): { signal: AbortSignal; cleanup: () => void } {
  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort(a.aborted ? a.reason : b.reason);
  if (a.aborted || b.aborted) onAbort();
  else {
    a.addEventListener("abort", onAbort, { once: true });
    b.addEventListener("abort", onAbort, { once: true });
  }
  return { signal: ctrl.signal, cleanup: () => {
    a.removeEventListener("abort", onAbort);
    b.removeEventListener("abort", onAbort);
  } };
}

async function doRequest<T>(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  callerSignal?: AbortSignal
): Promise<T> {
  const timeoutCtrl = new AbortController();
  const timer = setTimeout(() => timeoutCtrl.abort("timeout"), timeoutMs);
  const combined = callerSignal ? combineSignals(callerSignal, timeoutCtrl.signal) : { signal: timeoutCtrl.signal, cleanup: () => {} };
  const signal = combined.signal;
  try {
    if (callerSignal?.aborted) throw new DOMException("Request cancelled", "AbortError");
    const headers = new Headers(init.headers);
    if (authToken && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${authToken}`);
    const res = await fetch(`${BASE}${path}`, { ...init, headers, signal });
    const requestId = res.headers.get("X-Request-ID") ?? undefined;
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") detail = body.detail;
        else if (Array.isArray(body?.detail)) detail = "Request validation failed.";
      } catch { /* non-JSON body; abort is checked below */ }
      if (signal.aborted) throw new DOMException("Request aborted", "AbortError");
      const retry = res.headers.get("Retry-After");
      const retrySeconds = retry && /^\d{1,6}$/.test(retry) ? Number(retry) : undefined;
      if (res.status === 401) throw new ApiError("unauthorized", detail, res.status, requestId);
      if (res.status === 429) throw new ApiError("throttled", detail, res.status, requestId, retrySeconds);
      if (res.status === 422 || res.status === 413) throw new ApiError("validation", detail, res.status, requestId);
      if (res.status === 503) throw new ApiError("unavailable", detail, res.status, requestId);
      throw new ApiError("server", detail, res.status, requestId);
    }
    const value = await res.json();
    if (signal.aborted) throw new DOMException("Request aborted", "AbortError");
    return value as T;
  } catch (err) {
    if (callerSignal?.aborted) throw new DOMException("Request cancelled", "AbortError");
    if (timeoutCtrl.signal.aborted) throw new ApiError("timeout", `Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    if (err instanceof ApiError) throw err;
    throw new ApiError("unavailable", "The assessment service could not be reached or returned an unusable response.");
  } finally {
    clearTimeout(timer);
    combined.cleanup();
  }
}

async function prediction(text: string, signal?: AbortSignal): Promise<PredictResponse> {
  const value = await doRequest<unknown>("/predict", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
  }, PREDICT_TIMEOUT_MS, signal);
  try {
    return parsePrediction(value);
  } catch {
    throw new ApiError("unavailable", "The service returned an unsupported analysis response.");
  }
}

export const api = {
  predict: prediction,
  async configuration(signal?: AbortSignal): Promise<ConfigurationResponse> {
    const value = await doRequest<unknown>("/configuration", { method: "GET" }, HEALTH_TIMEOUT_MS, signal);
    try {
      return parseConfiguration(value);
    } catch {
      throw new ApiError("unavailable", "The service input configuration is unavailable.");
    }
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
  session(signal?: AbortSignal, candidateToken?: string): Promise<SessionResponse> {
    return doRequest<SessionResponse>("/auth/session", { method: "GET", headers: candidateToken === undefined ? undefined : { Authorization: `Bearer ${candidateToken}` } }, AUTH_TIMEOUT_MS, signal);
  },
  /**
   * Exchange a refresh token for a new access token.
   *
   * Sent with an explicitly empty Authorization header for the same reason as
   * sign-in: a stale access token must not be attached to a renewal.
   */
  refresh(refreshToken: string, signal?: AbortSignal): Promise<SessionPayload> {
    return doRequest<SessionPayload>(
      "/auth/refresh",
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
      AUTH_TIMEOUT_MS,
      signal
    );
  },
  /** Which sign-in methods this deployment offers. */
  providers(signal?: AbortSignal): Promise<{ email_password: boolean; google: boolean }> {
    return doRequest("/auth/providers", { method: "GET" }, HEALTH_TIMEOUT_MS, signal);
  },
  /**
   * The signed-in account's screening history from Supabase.
   *
   * Scoped server-side to the verified token subject.
   */
  screenings(limit = 25, signal?: AbortSignal): Promise<{ screenings: ScreeningSummary[]; count: number }> {
    return doRequest(
      `/screenings?limit=${limit}`,
      { method: "GET" },
      AUTH_TIMEOUT_MS,
      signal
    );
  },
  /** Remove the signed-in account's screening history. */
  deleteScreenings(signal?: AbortSignal): Promise<{ deleted: number }> {
    return doRequest("/screenings", { method: "DELETE" }, AUTH_TIMEOUT_MS, signal);
  },
};
