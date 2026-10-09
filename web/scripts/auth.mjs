// Shared helpers for the Playwright QA scripts.
// The app authenticates against the real backend, so QA runs need a genuine
// bearer token. Hand-writing one into localStorage would be rejected on every
// request, so scripts log in over HTTP and reuse the same storage key the app
// writes.
//
// Usage:
//   import { launchChromium, seedSession } from "./auth.mjs";
//   const browser = await launchChromium();

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SESSION_KEY = "mental.ai.auth";

/**
 * Credentials for QA runs.
 *
 * Identity lives in Supabase Auth, so there is no configured account to read
 * from the service any more: the account has to exist in the Supabase project.
 * Real environment variables win; otherwise the repo-root .env is read, because
 * `npm run dev` loads that file and a QA run against the same stack must use the
 * same project or it silently tests the wrong configuration.
 *
 *   MENTAL_AI_QA_EMAIL     account address
 *   MENTAL_AI_QA_PASSWORD  account password
 *
 * Or the conventional names, which the .env template documents:
 *   SUPABASE_QA_EMAIL / SUPABASE_QA_PASSWORD
 */
function resolveCredentials() {
  const envPath =
    process.env.MENTAL_AI_ENV_FILE ?? join(dirname(fileURLToPath(import.meta.url)), "..", "..", ".env");

  let fromFile = {};
  if (existsSync(envPath)) {
    for (const line of readFileSync(envPath, "utf8").split("\n")) {
      const match = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
      if (!match) continue;
      fromFile[match[1]] = match[2].replace(/^["']|["']$/g, "");
    }
  }

  const email =
    process.env.MENTAL_AI_QA_EMAIL ??
    fromFile.MENTAL_AI_QA_EMAIL ??
    process.env.SUPABASE_QA_EMAIL ??
    fromFile.SUPABASE_QA_EMAIL;
  const password =
    process.env.MENTAL_AI_QA_PASSWORD ??
    fromFile.MENTAL_AI_QA_PASSWORD ??
    process.env.SUPABASE_QA_PASSWORD ??
    fromFile.SUPABASE_QA_PASSWORD;

  return {
    email: email?.trim() ?? "",
    password: password ?? "",
    // Display name is whatever Supabase holds for the account; the greeting
    // assertions derive it rather than assume it.
    name: fromFile.MENTAL_AI_QA_NAME ?? "",
  };
}

/** Fail loudly rather than signing in as nobody and reporting a green run. */
export function requireCredentials() {
  if (!DEFAULT_EMAIL || !DEFAULT_PASSWORD) {
    throw new Error(
      "QA credentials are not configured. Accounts now live in Supabase Auth, so a run " +
        "needs a real one.\n" +
        "Set these, either in the environment or in the repo-root .env:\n" +
        "  MENTAL_AI_QA_EMAIL=you@example.com\n" +
        "  MENTAL_AI_QA_PASSWORD=your-password"
    );
  }
}

/**
 * The greeting a given account should produce.
 *
 * Mirrors the server: an explicit MENTAL_AI_AUTH_NAME, otherwise a name derived
 * from the user id, then the first word in sentence case - exactly what
 * lib/auth.ts does in the browser. Asserting on the real value is what stops a
 * QA run from passing only because both sides happened to say "Admin".
 */
export function expectedFirstName(email = DEFAULT_EMAIL, name = DEFAULT_NAME) {
  // Supabase supplies the real display name, so the greeting is asserted against
  // whatever the account actually carries rather than a derived guess.
  if (name.trim()) {
    const word = name.trim().split(/\s+/)[0] ?? "";
    return word ? word[0].toUpperCase() + word.slice(1).toLowerCase() : "";
  }
  return "";
}

const {
  email: DEFAULT_EMAIL,
  password: DEFAULT_PASSWORD,
  name: DEFAULT_NAME,
} = resolveCredentials();

/**
 * Origin the app's API calls actually go to.
 *
 * Same origin plus /api in the default dev setup, where Vite proxies it.
 * A build configured with VITE_API_URL talks to that host directly instead.
 */
/**
 * The configured QA account, or empty strings when unset.
 *
 * Exposed so the scripts can fill the real form without each one re-deriving
 * the environment lookup.
 */
export const qaCredentials = {
  get email() {
    return DEFAULT_EMAIL;
  },
  get password() {
    return DEFAULT_PASSWORD;
  },
};

export function apiOrigin(base) {
  const configured = process.env.MENTAL_AI_API_URL ?? process.env.VITE_API_URL;
  if (configured) return configured.replace(/\/$/, "");
  return `${base.replace(/\/$/, "")}/api`;
}

/**
 * Route pattern matching every API request the app makes.
 *
 * Used to simulate an unreachable backend. Derived from apiOrigin so the block
 * actually matches in both setups; a pattern aimed at the wrong URL silently
 * blocks nothing and the test passes for the wrong reason.
 */
export function apiPattern(base) {
  return `${apiOrigin(base)}/**`;
}

/**
 * Sign in over the API and pre-seed the browser session for `page`.
 *
 * Must be called before the first navigation: addInitScript applies to every
 * document the page loads afterwards.
 *
 * The request goes to the same origin's /api by default, which is what the dev
 * proxy serves. A build pointed straight at an API host sets
 * MENTAL_AI_API_URL, because a seeded session with no token would silently
 * validate as anonymous and every assertion after it would be meaningless.
 */
export async function seedSession(page, base, email = DEFAULT_EMAIL, password = DEFAULT_PASSWORD) {
  requireCredentials();
  const apiBase = apiOrigin(base);
  const res = await page.request.post(`${apiBase}/auth/login`, {
    data: { user_id: email, password },
  });
  if (!res.ok()) {
    throw new Error(
      `QA sign-in failed (${res.status()}). Is the backend running and are ` +
        `MENTAL_AI_AUTH_USER / MENTAL_AI_AUTH_PASSWORD correct?`
    );
  }
  const body = await res.json();
  if (typeof body?.token !== "string") {
    throw new Error(
      `QA sign-in returned no token from ${apiBase}. Set MENTAL_AI_API_URL to the ` +
        `API origin when the app is not served behind a same-origin /api proxy.`
    );
  }
  await page.addInitScript(
    ([key, session]) => window.localStorage.setItem(key, session),
    [
      SESSION_KEY,
      JSON.stringify({
        // The application store mirrors this shape in browser storage.
        token: body.token,
        refreshToken: body.refresh_token,
        user: body.user,
        userId: body.user_id,
        name: body.name,
        expiresAt: body.expires_at * 1000,
      }),
    ]
  );
  return body.token;
}

/**
 * Launch Chromium, tolerating a browser cache that does not match the
 * installed Playwright version.
 *
 * `npx playwright install chromium` is the real fix, but QA should not be
 * blocked when a compatible build is already on disk. Set
 * PLAYWRIGHT_CHROMIUM_PATH to point at one explicitly.
 */
export async function launchChromium() {
  const { chromium } = await import("playwright");
  const override = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  try {
    return await chromium.launch(override ? { executablePath: override } : {});
  } catch (err) {
    if (override) throw err;
    const fallback = findCachedChromium();
    if (!fallback) {
      throw new Error(
        "No usable Chromium found. Run `npx playwright install chromium`, or set " +
          "PLAYWRIGHT_CHROMIUM_PATH to a browser binary."
      );
    }
    console.warn(`Using cached Chromium at ${fallback}`);
    return chromium.launch({ executablePath: fallback });
  }
}

/** Newest full Chromium build in the Playwright cache, if any. */
function findCachedChromium() {
  const cache = process.env.PLAYWRIGHT_BROWSERS_PATH ?? `${homedir()}/.cache/ms-playwright`;
  if (!existsSync(cache)) return null;

  const candidates = readdirSync(cache)
    .filter((name) => name.startsWith("chromium-"))
    .sort()
    .reverse();

  for (const name of candidates) {
    for (const rel of ["chrome-linux64/chrome", "chrome-linux/chrome", "chrome-mac/Chromium.app/Contents/MacOS/Chromium"]) {
      const bin = `${cache}/${name}/${rel}`;
      if (existsSync(bin)) return bin;
    }
  }
  return null;
}

/** Fill the sign-in form and submit it through the real UI. */
export async function signIn(page, { email = DEFAULT_EMAIL, password = DEFAULT_PASSWORD } = {}) {
  requireCredentials();
  await page.waitForSelector(".signin__input", { timeout: 10000 });
  const fields = page.locator(".signin__input");
  await fields.nth(0).fill(email);
  await fields.nth(1).fill(password);
  await page.click("button[type=submit]");
}

/**
 * Walk the screening check-in questions.
 *
 * These now live behind the gate rather than inside it, so a run either seeds a
 * session first or signs in before calling this.
 */
export async function completeCheckIn(page, answers) {
  for (const answer of answers) {
    await page.waitForSelector(".checkin__input", { timeout: 10000 });
    await page.fill(".checkin__input", answer);
    await page.click("button[type=submit]");
  }
}