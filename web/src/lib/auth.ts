/**
 * Session store for MENTAL.AI.
 *
 * The source of truth is the bearer token issued by POST /auth/login. It is
 * held in memory for the request path and mirrored to browser storage so a page
 * reload keeps the session; the mirror is re-validated against
 * GET /auth/session on boot, so a revoked or expired token cannot survive a
 * reload even though the local copy still looks valid.
 *
 * "Remember me" chooses the scope of that mirror, and is the only difference
 * between the two options: localStorage keeps the session across browser
 * restarts, sessionStorage drops it when the tab closes. The password is never
 * stored in either, and neither store is trusted for authorisation - the server
 * verifies the token on every call.
 *
 * Module-level state plus a subscriber list, rather than React state, because
 * the sign-in flow and the authenticated screens both mutate the session and
 * every consumer (router, navigation, screening) has to observe it. This is the
 * standard external-store shape, consumed via useSyncExternalStore.
 */
import { useSyncExternalStore } from "react";
import { api, setAuthToken } from "./api";

const KEY = "mental.ai.auth";

/**
 * `restoring`  a stored token is being re-validated, no route decision yet
 * `authed`     a server-verified session is held
 * `anonymous`  no usable session; protected routes redirect to /login
 */
export type AuthState = "restoring" | "authed" | "anonymous";

export interface Session {
  token: string;
  /** Account id, as configured on the server. */
  user: string;
  /** Display name reported by the server, used for greetings. */
  name: string;
  /** Epoch ms. Mirrors the server's expiry; used only to fail fast. */
  expiresAt: number;
}

let state: AuthState = "restoring";
let session: Session | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function getSnapshot(): AuthState {
  return state;
}

/**
 * Look in the persistent scope first, then the tab scope.
 *
 * The order only decides which copy is authoritative when both somehow exist;
 * sign-out clears both.
 */
function readStored(): { value: Session; store: Storage } | null {
  for (const store of [localStorage, sessionStorage]) {
    try {
      const raw = store.getItem(KEY);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as Partial<Session>;
      if (typeof parsed?.token !== "string" || typeof parsed?.user !== "string") continue;
      if (typeof parsed?.expiresAt !== "number" || parsed.expiresAt <= Date.now()) {
        store.removeItem(KEY);
        continue;
      }
      return {
        value: {
          token: parsed.token,
          user: parsed.user,
          // Tokens issued before the name was introduced still validate; the id
          // stands in until the next sign-in.
          name:
            typeof parsed.name === "string" && parsed.name.trim().length > 0
              ? parsed.name
              : parsed.user,
          expiresAt: parsed.expiresAt,
        },
        store,
      };
    } catch {
      /* storage unavailable or malformed: try the next scope */
    }
  }
  return null;
}

function persist(value: Session, remember: boolean): void {
  try {
    (remember ? localStorage : sessionStorage).setItem(KEY, JSON.stringify(value));
  } catch {
    /* storage unavailable or full: the in-memory token still carries this visit */
  }
}

function clearStored(): void {
  for (const store of [localStorage, sessionStorage]) {
    try {
      store.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }
}

function setState(next: AuthState, value: Session | null): void {
  state = next;
  session = value;
  emit();
}

export function currentSession(): Session | null {
  return session;
}

export function currentUser(): string | null {
  return session?.user ?? null;
}

export function currentName(): string | null {
  return session?.name ?? null;
}

/**
 * First name for greeting, in natural sentence case.
 *
 * "kArTiK gupta" reads as "Kartik", so the greeting looks like a sentence
 * while the navigation control uppercases the same string through CSS. An empty
 * name yields an empty string rather than a placeholder, and callers decide
 * whether to fall back to the account id.
 */
export function firstName(name: string | null | undefined): string {
  const word = (name ?? "").trim().split(/\s+/)[0] ?? "";
  if (!word) return "";
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}

/**
 * True when a token whose local expiry has not passed is held.
 *
 * Not proof the server still accepts it: that is settled by validateSession()
 * on boot and by any 401 on a live request.
 */
export function isAuthed(): boolean {
  return state === "authed" && session !== null && session.expiresAt > Date.now();
}

/** Subscribe to session changes. Returns an unsubscribe function. */
export function onSessionChange(fn: () => void): () => void {
  return subscribe(fn);
}

/** Read-only session state for React consumers. */
export function useAuthState(): AuthState {
  return useSyncExternalStore(subscribe, getSnapshot, () => "anonymous" as AuthState);
}

/**
 * Rehydrate a stored session and confirm it against the server.
 *
 * Any failure (expired, tampered, revoked, or the backend simply being down)
 * lands on `anonymous`, which routes the user to the sign-in gate rather than
 * pretending to be signed in. The server's name wins over the cached copy so a
 * display-name change takes effect without forcing a re-login.
 */
export async function validateSession(): Promise<void> {
  const stored = readStored();
  if (!stored) {
    setAuthToken(null);
    setState("anonymous", null);
    return;
  }

  setAuthToken(stored.value.token);
  try {
    const remote = await api.session();
    if (remote.user !== stored.value.user) throw new Error("Session subject changed");
    const next: Session = {
      ...stored.value,
      name: remote.name?.trim() || stored.value.name,
      expiresAt: remote.expires_at * 1000,
    };
    // Keep the session in the scope it was created in, so an unchecked
    // "remember me" is not quietly promoted to persistent on reload.
    persist(next, stored.store === localStorage);
    setState("authed", next);
  } catch {
    setAuthToken(null);
    clearStored();
    setState("anonymous", null);
  }
}

/**
 * Authenticate and adopt the returned session.
 *
 * Publishes `authed` on success, which is what lets the router proceed past the
 * gate without a reload. Throws ApiError on failure.
 *
 * `remember` selects only the persistence scope of the mirrored token. It
 * changes how long this browser keeps the session, never what the server will
 * accept.
 */
export async function login(
  userId: string,
  password: string,
  remember = true
): Promise<Session> {
  const res = await api.login(userId, password);
  const next: Session = {
    token: res.token,
    user: res.user,
    name: res.name?.trim() || res.user,
    expiresAt: res.expires_at * 1000,
  };
  setAuthToken(res.token);
  // Replace any session left in the other scope, so switching the box off does
  // not leave the previous persistent copy behind to be picked up later.
  clearStored();
  persist(next, remember);
  setState("authed", next);
  return next;
}

/** End the session: drop the token, the stored copy, and publish `anonymous`. */
export function logout(): void {
  setAuthToken(null);
  clearStored();
  setState("anonymous", null);
}

/**
 * Drop the session when the server has rejected it mid-visit.
 *
 * Called from the 401 path so an expired token returns the user to the gate
 * instead of leaving the UI in a state where every request fails.
 */
export function invalidateIfRejected(error: { kind?: string }): void {
  if (error.kind === "unauthorized") logout();
}