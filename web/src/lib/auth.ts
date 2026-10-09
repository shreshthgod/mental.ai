/**
 * Session store for MENTAL.AI.
 *
 * Identity lives in Supabase Auth. This module is the adapter that keeps the
 * interface the application already depends on: an AuthState, a Session
 * snapshot, and login / refresh / logout. Consumers - the router, the
 * navigation account menu, the entry greeting, the screening screen - are
 * unchanged, because nothing here moves state around them.
 *
 * How a session is held
 * ---------------------
 * Supabase owns the tokens and their refresh. This store keeps three things:
 *
 *   1. the in-memory access token, read by api.ts for the Authorization header
 *   2. the refresh token, so a new access token can be requested after an
 *      expiry or a 401
 *   3. a mirror in localStorage or sessionStorage, chosen by "Remember me",
 *      so a page reload does not sign the visitor out
 *
 * The mirror is re-validated on boot, and the mirror is never trusted for
 * authorisation: FastAPI verifies every token against Supabase on every call.
 *
 * Why the token is refreshed here rather than by the Supabase client
 * ------------------------------------------------------------------
 * supabase-js normally keeps its own store and refreshes on its own schedule.
 * The visitor's "Remember me" choice decides whether a session outlives the tab,
 * and the access token handed to FastAPI has to be the current one, so this store
 * owns the copy instead. supabase.auth.onAuthStateChange still listens for
 * refreshes that happen elsewhere (notably a Google sign-in returning from a
 * redirect) and mirrors them.
 *
 * Module-level state plus a subscriber list, rather than React state, because the
 * sign-in flow and the authenticated screens both mutate the session and every
 * consumer has to observe it. Standard external-store shape, consumed via
 * useSyncExternalStore.
 */
import { useSyncExternalStore } from "react";
import { api, setAuthToken, type SessionPayload } from "./api";
import { googleProviderStatus, supabase, supabaseConfigured } from "./supabase";
import { setPrivateOwner } from "./privateStore";

const KEY = "mental.ai.auth";
const OAUTH_KEY = "mental.ai.oauth";
const OAUTH_TTL_MS = 15 * 60 * 1000;
interface OAuthIntent { remember: boolean; returnTo: string; startedAt: number }
let oauthReturnPath: string | null = null;

/** Only application paths can be OAuth return destinations. */
function safeReturnPath(value?: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") ||
      Array.from(value).some(char => char.charCodeAt(0) <= 32 || char.charCodeAt(0) === 127)) return "/screen";
  try {
    const parsed = new URL(value, window.location.origin);
    return parsed.origin === window.location.origin ? `${parsed.pathname}${parsed.search}${parsed.hash}` : "/screen";
  } catch { return "/screen"; }
}

function clearOAuthIntent(): void {
  try { sessionStorage.removeItem(OAUTH_KEY); } catch { /* storage unavailable */ }
}

function readOAuthIntent(): OAuthIntent | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(OAUTH_KEY) ?? "null") as Partial<OAuthIntent> | null;
    if (value && typeof value.remember === "boolean" && typeof value.returnTo === "string" &&
        typeof value.startedAt === "number" && Number.isFinite(value.startedAt) &&
        Date.now() >= value.startedAt && Date.now() - value.startedAt <= OAUTH_TTL_MS) {
      return { remember: value.remember, returnTo: safeReturnPath(value.returnTo), startedAt: value.startedAt };
    }
  } catch { /* malformed or unavailable storage */ }
  clearOAuthIntent();
  return null;
}

/** Consumed once by the router, only after server-verified OAuth adoption. */
export function consumeOAuthReturnPath(): string | null {
  const result = oauthReturnPath;
  oauthReturnPath = null;
  return result;
}

/**
 * `restoring`  a stored session is being re-validated, no route decision yet
 * `authed`     a Supabase-verified session is held
 * `anonymous`  no usable session; protected routes redirect to /login
 */
export type AuthState = "restoring" | "authed" | "anonymous";

export interface Session {
  /** Supabase access token. Sent as `Authorization: Bearer` to FastAPI. */
  token: string;
  /** Used to obtain a new access token without asking the visitor to sign in. */
  refreshToken: string;
  /** Account id as the interface shows it (the email). */
  user: string;
  /** Authoritative Supabase Auth user id. Never shown; never a display value. */
  userId: string;
  /** Display name reported by Supabase, used for greetings. */
  name: string;
  /** Epoch ms. Mirrors the token expiry; used only to fail fast. */
  expiresAt: number;
}

let state: AuthState = "restoring";
let session: Session | null = null;
let lastError: string | null = null;
let sessionGeneration = 0;
function requireCurrent(generation: number): void {
  if (generation !== sessionGeneration) throw new DOMException("Session operation superseded", "AbortError");
}
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

function setState(next: AuthState, value: Session | null): void {
  state = next;
  session = value;
  setPrivateOwner(next === "authed" ? value?.userId ?? null : null);
  emit();
}

/** The last sign-in failure, for the interface to render. Cleared on success. */
export function authError(): string | null {
  return lastError;
}

// ------------------------------------------------------------------
// Storage mirror
// ------------------------------------------------------------------

/**
 * Look in the persistent scope first, then the tab scope.
 *
 * The order only decides which copy is authoritative when both somehow exist;
 * sign-out clears both.
 */
function readStored(includeExpired = false): { value: Session; store: Storage } | null {
  for (const store of [localStorage, sessionStorage]) {
    try {
      const raw = store.getItem(KEY);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as Partial<Session>;
      if (typeof parsed?.token !== "string" || typeof parsed?.refreshToken !== "string") continue;
      if (typeof parsed?.expiresAt !== "number" || !Number.isFinite(parsed.expiresAt) || (!includeExpired && parsed.expiresAt <= Date.now())) {
        // An expired access token is not the end of the session: the refresh
        // token can still produce a new one. Kept only so validateSession can
        // use it below, so this branch simply skips the copy.
        continue;
      }
      return {
        value: {
          token: parsed.token,
          refreshToken: parsed.refreshToken,
          user: typeof parsed.user === "string" ? parsed.user : "",
          userId: typeof parsed.userId === "string" ? parsed.userId : "",
          name: typeof parsed.name === "string" ? parsed.name : "",
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

/**
 * Read the mirror even when the access token has expired.
 *
 * Only the refresh token is needed to recover, so it is kept separately from the
 * expiry check above.
 */
function readRefreshToken(): string | null {
  for (const store of [sessionStorage, localStorage]) {
    try {
      const parsed = JSON.parse(store.getItem(KEY) ?? "null") as Partial<Session> | null;
      if (parsed && typeof parsed.refreshToken === "string" && parsed.refreshToken.length > 0) {
        return parsed.refreshToken;
      }
    } catch {
      /* ignore malformed mirrors */
    }
  }
  return null;
}

/** Which scope the current session lives in, so reload keeps it there. */
function persistedInLocalStorage(): boolean {
  try {
    return localStorage.getItem(KEY) !== null;
  } catch {
    return false;
  }
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

// ------------------------------------------------------------------
// Reads
// ------------------------------------------------------------------
export function currentSession(): Session | null {
  return session;
}

export function currentUser(): string | null {
  return session?.user ?? null;
}

export function currentName(): string | null {
  return session?.name ?? null;
}

export function currentUserId(): string | null {
  return session?.userId ?? null;
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

// ------------------------------------------------------------------
// Session adoption
// ------------------------------------------------------------------

/**
 * Publish a session: hand the access token to the API client, mirror it in the
 * chosen storage scope, and notify every consumer. The single place that
 * mutates the store.
 */
function publish(next: Session, remember: boolean, generation: number): Session {
  requireCurrent(generation);
  if (!next.userId || !Number.isFinite(next.expiresAt) || next.expiresAt <= Date.now()) throw new Error("Session identity or expiry is unavailable");
  clearStored();
  setAuthToken(next.token);
  persist(next, remember);
  setState("authed", next);
  lastError = null;
  return next;
}

/** Build the store's snapshot from an API session payload. */
function snapshotFrom(remote: SessionPayload): Session {
  return {
    token: remote.token,
    refreshToken: remote.refresh_token,
    user: remote.user ?? "",
    userId: remote.user_id ?? "",
    name: remote.name?.trim() || remote.user || "",
    expiresAt: remote.expires_at * 1000,
  };
}

/** Build the store's snapshot from a Supabase client session. */
function snapshotFromSupabase(
  remote: { access_token: string; refresh_token: string; expires_at?: number },
  identity: { email?: string; name?: string; userId: string }
): Session {
  return {
    token: remote.access_token,
    refreshToken: remote.refresh_token,
    user: identity.email ?? "",
    userId: identity.userId,
    name: identity.name?.trim() || identity.email || "",
    expiresAt: typeof remote.expires_at === "number" ? remote.expires_at * 1000 : Number.NaN,
  };
}

/**
 * Adopt a session the service issued, confirming it first.
 *
 * The extra round trip is what makes the server, not the browser, authoritative
 * for the display name and the account id: an operator-set name change takes
 * effect without forcing a re-login.
 */
async function adoptFromApi(candidate: Session, remember: boolean, generation: number, intent?: OAuthIntent | null): Promise<Session> {
  requireCurrent(generation);
  // Verify with an explicit candidate header without replacing the current account's token.
  const verified = await api.session(undefined, candidate.token);
  requireCurrent(generation);
  if (!verified.user_id) throw new Error("Verified identity is unavailable");
  if (intent) {
    oauthReturnPath = intent.returnTo;
    clearOAuthIntent();
  }
  return publish({ ...candidate, user: verified.user, userId: verified.user_id,
    name: verified.name?.trim() || verified.user }, remember, generation);
}

/** SDK sessions also need the same server identity verification before publication. */
async function adoptFromSupabase(
  remote: { access_token: string; refresh_token: string; expires_at?: number },
  remember: boolean,
  identity: { email?: string; name?: string; userId: string },
  generation: number
): Promise<Session> {
  return adoptFromApi(snapshotFromSupabase(remote, identity), remember, generation);
}

/** Read a Supabase client's current session, if it is holding one. */
async function sessionFromSupabaseClient(): Promise<Session | null> {
  if (!supabase) return null;
  const client = supabase;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const unavailable = "Sign-in could not be completed. Please try again.";
  const { data, error } = await Promise.race([
    (async () => {
      // SDK getSession does not surface an implicit callback initialization error.
      const initialized = await client.auth.initialize();
      if (initialized.error) throw new Error(unavailable);
      return client.auth.getSession();
    })(),
    new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error(unavailable)), 10000); }),
  ]).finally(() => { if (timer !== undefined) clearTimeout(timer); });
  if (error) throw new Error("Sign-in could not be completed. Please try again.");
  const remote = data.session;
  if (!remote?.access_token) return null;
  const user = remote.user;
  return snapshotFromSupabase(remote, {
    email: user?.email ?? "",
    name:
      (user?.user_metadata?.full_name as string) ?? (user?.user_metadata?.name as string) ?? "",
    userId: user?.id ?? "",
  });
}

/** OAuth metadata chooses storage/routing, never identity or authorization. */
async function adoptClientSession(candidate: Session, generation: number): Promise<Session> {
  const intent = readOAuthIntent();
  return adoptFromApi(candidate, intent?.remember ?? persistedInLocalStorage(), generation, intent);
}

// ------------------------------------------------------------------
// Lifecycle
// ------------------------------------------------------------------

/**
 * Mirror session changes the Supabase client makes on its own.
 *
 * The one that matters in practice is the Google redirect: the browser returns
 * with a session in the URL fragment, Supabase parses it during app boot, and
 * this listener is how that session reaches the rest of the application.
 */
function watchSupabase(): () => void {
  if (!supabase) return () => {};
  const { data } = supabase.auth.onAuthStateChange((event, next) => {
    if (event === "SIGNED_OUT") {
      // Forget locally only. Calling logout() here would call signOut() again,
      // and the resulting SIGNED_OUT event would call logout() again - a loop
      // that ends in a tab crash rather than a sign-out.
      forgetSession();
      return;
    }
    if (!next?.access_token || next.access_token === session?.token) return;
    const generation = ++sessionGeneration;
    const user = next.user;
    void adoptClientSession(snapshotFromSupabase(
      {
        access_token: next.access_token,
        refresh_token: next.refresh_token,
        expires_at: next.expires_at,
      },
      {
        email: user?.email ?? "",
        name: (user?.user_metadata?.full_name as string) ?? (user?.user_metadata?.name as string) ?? "",
        userId: user?.id ?? "",
      }), generation
    ).catch(() => {
      if (generation === sessionGeneration) {
        lastError = "Sign-in could not be verified. Please try again.";
        forgetSession();
      }
    });
  });
  return () => data.subscription.unsubscribe();
}

let stopWatching: (() => void) | null = null;

/**
 * Rehydrate a stored session and confirm it against the service.
 *
 * An expired access token with a usable refresh token is refreshed rather than
 * discarded. Any other failure lands on `anonymous`, which routes the visitor to
 * the sign-in panel rather than pretending to be signed in.
 */
export async function validateSession(): Promise<void> {
  const generation = ++sessionGeneration;
  if (!stopWatching) stopWatching = watchSupabase();

  // Prefer a usable mirror; retain an expired one only to attempt its own refresh.
  const stored = readStored() ?? readStored(true);
  if (!stored) {
    // Nothing in the mirror. Supabase may still be holding a session, which is
    // exactly the case when a Google sign-in has just redirected back.
    let fromClient: Session | null;
    try { fromClient = await sessionFromSupabaseClient(); }
    catch {
      if (generation === sessionGeneration) {
        lastError = "Sign-in could not be completed. Please try again.";
        forgetSession();
      }
      return;
    }
    if (generation !== sessionGeneration) return;
    if (fromClient) {
      try { await adoptClientSession(fromClient, generation); }
      catch {
        if (generation === sessionGeneration) {
          lastError = "Sign-in could not be verified. Please try again.";
          forgetSession();
        }
      }
      return;
    }
    clearOAuthIntent();
    setAuthToken(null);
    setState("anonymous", null);
    return;
  }

  try {
    await adoptFromApi(stored.value, stored.store === localStorage, generation);
  } catch {
    if (generation !== sessionGeneration) return;
    // The stored access token was rejected. A refresh token may still be good,
    // so recover once before signing the visitor out.
    const token = stored.value.refreshToken;
    if (!token) {
      setAuthToken(null);
      clearStored();
      setState("anonymous", null);
      return;
    }
    try {
      const renewed = await api.refresh(token);
      publish(snapshotFrom(renewed), persistedInLocalStorage(), generation);
    } catch {
      if (generation !== sessionGeneration) return;
      setAuthToken(null);
      clearStored();
      setState("anonymous", null);
    }
  }
}

/**
 * Refresh the access token from the stored refresh token.
 *
 * Returns the new session, or null when the refresh token is no longer valid -
 * at which point the caller signs the visitor out. Exported because a live 401
 * needs the same recovery a reload does.
 */
export async function refreshSession(): Promise<Session | null> {
  const generation = ++sessionGeneration;
  const token = readRefreshToken();
  if (!token) return null;
  try {
    const renewed = await api.refresh(token);
    return publish(snapshotFrom(renewed), persistedInLocalStorage(), generation);
  } catch {
    if (generation !== sessionGeneration) return null;
    setAuthToken(null);
    clearStored();
    setState("anonymous", null);
    return null;
  }
}

/**
 * Authenticate with email and password and adopt the resulting session.
 *
 * Publishes `authed` on success, which is what lets the router proceed past the
 * gate without a reload. Throws ApiError on failure, using the same error kinds
 * as before so the interface's existing wording still applies.
 *
 * `remember` selects only the persistence scope of the mirrored session. It
 * changes how long this browser keeps it, never what the server will accept.
 */
export async function login(
  email: string,
  password: string,
  remember = true
): Promise<Session> {
  const generation = ++sessionGeneration;
  const remote = await api.login(email, password);
  return adoptFromApi(snapshotFrom(remote), remember, generation);
}

/**
 * Create an account with email and password.
 *
 * Two outcomes, both handled here so the caller sees one result:
 *   - the project has email confirmation off, Supabase returns a session and
 *     the visitor is signed in immediately;
 *   - confirmation is on, Supabase returns no session and `confirmed` is false,
 *     so the interface can say what to expect instead of failing silently.
 */
export async function register(
  email: string,
  password: string,
  remember = true
): Promise<{ session: Session | null }> {
  const generation = ++sessionGeneration;
  if (!supabase) {
    throw new Error("Supabase is not configured.");
  }
  const { data, error } = await supabase.auth.signUp({
    email: (email ?? "").trim(),
    password,
  });
  requireCurrent(generation);
  if (error) {
    lastError = error.message;
    throw new Error(error.message);
  }
  // No session means the project requires email confirmation before sign-in.
  if (!data.session) {
    return { session: null };
  }
  const adopted = await adoptFromSupabase(
    {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      expires_at: data.session.expires_at,
    },
    remember,
    {
      email: data.user?.email ?? "",
      name:
        (data.user?.user_metadata?.full_name as string) ??
        (data.user?.user_metadata?.name as string) ??
        "",
      userId: data.user?.id ?? "",
    }, generation
  );
  return { session: adopted };
}

/**
 * Begin a Google sign-in.
 *
 * Hands the browser to Supabase, which hands it to Google, and returns. There is
 * no result to await: by the time this resolves, the page is navigating away.
 * The session arrives on the way back and validateSession() picks it up.
 */
export async function signInWithGoogle(options: { remember?: boolean; returnTo?: string } = {}): Promise<void> {
  if (!supabase) throw new Error("Supabase is not configured.");
  const generation = ++sessionGeneration;
  const intent: OAuthIntent = { remember: options.remember ?? true,
    returnTo: safeReturnPath(options.returnTo), startedAt: Date.now() };
  oauthReturnPath = null;
  lastError = null;
  let failureMessage = "Google sign-in could not be started. Please try again.";
  try {
    const provider = await googleProviderStatus();
    requireCurrent(generation);
    if (provider !== "enabled") {
      failureMessage = provider === "disabled"
        ? "Google sign-in is not enabled for this project. Use email and password."
        : "Google sign-in is temporarily unavailable. Use email and password or try again.";
      throw new Error(failureMessage);
    }
    // Metadata only. The SDK handles provider state and callback tokens.
    sessionStorage.setItem(OAUTH_KEY, JSON.stringify(intent));
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}${intent.returnTo}`,
        queryParams: { prompt: "select_account" },
      },
    });
    requireCurrent(generation);
    if (error) throw new Error("Google sign-in could not be started. Please try again.");
  } catch (error) {
    if (generation === sessionGeneration) {
      clearOAuthIntent();
      lastError = failureMessage;
    }
    throw error instanceof DOMException && error.name === "AbortError" ? error : new Error(failureMessage);
  }
}

/**
 * Forget the session locally, without telling Supabase.
 *
 * The one-way half of sign-out. Kept separate from logout() so the Supabase
 * SIGNED_OUT listener can respond to a sign-out that happened elsewhere without
 * asking Supabase to sign out again.
 */
function forgetSession(): void {
  sessionGeneration++;
  setAuthToken(null);
  clearStored();
  clearOAuthIntent();
  oauthReturnPath = null;
  stopWatching?.();
  stopWatching = null;
  setState("anonymous", null);
}

/** End the session: drop the token, the stored copy, and publish `anonymous`. */
export function logout(): void {
  // Local state first, so the interface is never left looking signed in, and so
  // the call is idempotent if it arrives twice.
  forgetSession();
  // Then sign out of Supabase, so the identity provider agrees with us and a
  // later visitor cannot pick the session up from this browser. A failure here
  // changes nothing locally: the mirror is already gone.
  void supabase?.auth.signOut().catch(() => undefined);
}

/**
 * Drop the session when the server has rejected it mid-visit.
 *
 * Called from the 401 path so an expired session returns the visitor to the gate
 * instead of leaving the interface in a state where every request fails.
 */
export function invalidateIfRejected(error: { kind?: string }): void {
  if (error.kind === "unauthorized") logout();
}

/** Whether the social sign-in control should be offered. */
export function socialSignInAvailable(): boolean {
  return supabaseConfigured;
}
