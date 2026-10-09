/**
 * Supabase client for the browser.
 *
 * One client for the whole application. Identity and the session live in
 * Supabase Auth; this file only knows how to reach it.
 *
 * What the browser holds
 * ---------------------
 * The publishable key. It is public by design - Supabase ships it in every
 * browser app and relies on Row Level Security, not on hiding it. The secret /
 * service-role key is deliberately absent from this file and from every VITE_
 * variable: anything prefixed VITE_ is inlined into the JavaScript bundle.
 *
 * Where the API key material lives
 * --------------------------------
 *   VITE_SUPABASE_URL              project URL            public
 *   VITE_SUPABASE_PUBLISHABLE_KEY  publishable key        public
 *   SUPABASE_SECRET_KEY             server writes          SECRET, FastAPI only
 *
 * An absent configuration disables the SDK path. Provider availability is
 * checked separately before starting a Google redirect.
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

/**
 * Whether Supabase is configured at all.
 *
 * The interface uses this to hide the social sign-in control rather than
 * offering a button that cannot work. Local development without a .env keeps
 * every existing screen usable; only the social path is withheld.
 */
export const supabaseConfigured: boolean = Boolean(url && publishableKey);

function build(): SupabaseClient {
  if (!url || !publishableKey) {
    throw new Error(
      "Supabase is not configured. Set VITE_SUPABASE_URL and " +
        "VITE_SUPABASE_PUBLISHABLE_KEY in web/.env.local (see .env.example)."
    );
  }
  return createClient(url, publishableKey, {
    auth: {
      // Google and email-confirmation links return with tokens in the URL
      // fragment. Supabase reads them on load and clears the fragment, so no
      // separate /auth/callback route is needed.
      detectSessionInUrl: true,
      // The store in auth.ts decides whether a session survives a browser
      // restart ("Remember me"), so Supabase must not keep its own copy
      // regardless of what the visitor chose here.
      persistSession: false,
      autoRefreshToken: false,
      storage: undefined,
    },
  });
}

/**
 * The Supabase client, or null when unconfigured.
 *
 * Null rather than a throwing wrapper: a missing env should degrade the social
 * sign-in path, not take the whole application down on import.
 */
export const supabase: SupabaseClient | null = supabaseConfigured ? build() : null;

/** Provider identifier used by the social sign-in control. */
export const GOOGLE_PROVIDER = "google" as const;

/** Public provider configuration only; no user token or server key is sent. */
export async function googleProviderStatus(): Promise<"enabled" | "disabled" | "unavailable"> {
  if (!supabaseConfigured || !url || !publishableKey) return "unavailable";
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`${url.replace(/\/$/, "")}/auth/v1/settings`, {
      headers: { apikey: publishableKey }, signal: controller.signal,
      credentials: "omit", redirect: "error",
    });
    if (!response.ok) return "unavailable";
    const settings: unknown = await response.json();
    if (!settings || typeof settings !== "object" || !("external" in settings)) return "unavailable";
    const external = settings.external;
    if (!external || typeof external !== "object" || !("google" in external) || typeof external.google !== "boolean") return "unavailable";
    return external.google ? "enabled" : "disabled";
  } catch { return "unavailable"; }
  finally { clearTimeout(timer); }
}
