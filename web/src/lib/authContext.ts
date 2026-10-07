/**
 * Session state for route guards and authenticated screens.
 *
 * The store in auth.ts owns the state; this module only adapts it for React and
 * provides the sign-out action. Kept separate from auth.ts so screens can read
 * the session without importing the store's internals, and separate from
 * App.tsx to avoid an import cycle with the router.
 */
import { useSyncExternalStore } from "react";
import {
  currentSession,
  firstName,
  logout,
  onSessionChange,
  type Session,
} from "./auth";
import { useAuthState, type AuthState } from "./auth";

export type { AuthState };

/** `restoring` | `authed` | `anonymous`, observable across route changes. */
export function useAuth(): AuthState {
  return useAuthState();
}

/**
 * The live session, or null while anonymous or still restoring.
 *
 * Subscribes to the store rather than reading it once, so navigation and the
 * account menu update the moment sign-in or sign-out happens.
 */
export function useSession(): Session | null {
  return useSyncExternalStore(onSessionChange, currentSession, () => null);
}

export interface Account {
  /** Full name as the server reports it. */
  name: string;
  /** First word, sentence-cased, for greetings. */
  firstName: string;
  /** Account id, shown in the menu and used as the email-line fallback. */
  user: string;
}

/** Name details for the greeting and the navigation menu. */
export function useAccount(): Account | null {
  const session = useSession();
  if (!session) return null;
  return {
    name: session.name,
    firstName: firstName(session.name) || firstName(session.user),
    user: session.user,
  };
}

/** End the session and publish `anonymous`, which the guards react to. */
export function useSignOut(): () => void {
  return logout;
}