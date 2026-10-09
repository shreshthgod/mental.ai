// Auth flow QA: the gate, validation, session persistence and route protection.
//
//   node scripts/authflow.mjs [baseUrl]
//
// Exercises the sign-in journey through the real UI against the real backend,
// and asserts the properties that are easy to regress: a protected route cannot
// be reached by typing its URL, a reload keeps the session, and signing out
// closes it again.
import { mkdirSync } from "node:fs";
import { expectedFirstName, launchChromium, qaCredentials as CREDS, seedSession, signIn } from "./auth.mjs";

const BASE = process.argv[2] ?? "http://localhost:5173";
const GREETING = expectedFirstName();
mkdirSync("shots", { recursive: true });

const results = [];
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  results.push(ok);
  console.log(`${ok ? "pass" : "FAIL"}  ${label}${ok ? "" : ` (got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)})`}`);
}

const browser = await launchChromium();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

const consoleErrors = [];
page.on("console", (m) => {
  // "Failed to load resource" is the browser narrating a response status. This
  // run deliberately provokes a 401, so those are expected; uncaught
  // exceptions and real script errors are not.
  if (m.type() === "error" && !m.text().includes("Failed to load resource")) {
    consoleErrors.push(m.text());
  }
});
page.on("pageerror", (e) => consoleErrors.push(String(e)));

// 1. Signed out, "/" is the entry experience and the call to action reads Login.
await page.goto(BASE, { waitUntil: "networkidle" });
check("signed out lands on the entry", new URL(page.url()).pathname, "/");
// innerText reflects the CSS uppercase, which is the intended rendering.
check("nav shows Login", await page.locator(".nav__cta").innerText(), "LOGIN");
check("nav hides the session control", await page.locator(".account__trigger").count(), 0);
check("nav hides account menu", await page.locator(".account__trigger").count(), 0);
await page.screenshot({ path: "shots/auth-1-gate.png" });

// 2. A protected route cannot be reached by typing it.
await page.goto(`${BASE}/screen`, { waitUntil: "networkidle" });
check("/screen redirects to the gate", new URL(page.url()).pathname, "/login");

// 3. Empty submit is caught in the browser, with no request made.
await page.click(".signin__submit");
check("empty user id error", await page.locator(".signin__msg--error").first().innerText(),
  "Enter your email address.");

// 4. Wrong password fails cleanly and stays on the gate.
await page.fill(".signin__input >> nth=0", CREDS.email);
await page.fill(".signin__input >> nth=1", "definitely-wrong");
await page.click(".signin__submit");
await page.waitForSelector(".signin__msg--request", { timeout: 15000 });
check("bad credentials message", await page.locator(".signin__msg--request").innerText(),
  "We couldn't sign you in with those details.");
check("still on /login", new URL(page.url()).pathname, "/login");
await page.screenshot({ path: "shots/auth-2-rejected.png" });

// 5. Password reveal toggles the input type and its label.
await page.click(".signin__reveal");
check("reveal switches type", await page.getAttribute(".signin__input >> nth=1", "type"), "text");
check("reveal label flips", await page.getAttribute(".signin__reveal", "aria-label"), "Hide password");
await page.click(".signin__reveal");

// 6. Correct credentials: loading state, greeting, then the screening entry.
//
// The greeting is observed with a MutationObserver rather than polled: it is
// only on screen for about a second, and under load a poll can easily miss it.
await page.evaluate(() => {
  window.__greetings = [];
  const seen = new Set();
  const record = () => {
    const el = document.querySelector(".entry__greeting-name");
    if (el && !seen.has(el)) {
      seen.add(el);
      window.__greetings.push(el.textContent);
    }
  };
  new MutationObserver(record).observe(document.body, {
    childList: true,
    subtree: true,
  });
});
await page.fill(".signin__input >> nth=1", CREDS.password);
await page.click(".signin__submit");

// The greeting is captured from the observer rather than read off the live
// DOM: it holds for about a second, which a slow or busy machine can pass
// through before a query lands on it.
await page.waitForSelector(".checkin__input", { timeout: 15000 });
const greetings = await page.evaluate(() => window.__greetings);
check("greeting shown before the transition", greetings[0], `${GREETING}.`);

// Best effort: the frame may already have advanced to the check-in.
if (greetings.length > 0) {
  await page.waitForSelector(".entry__greeting", { timeout: 800 }).catch(() => {});
}
await page.screenshot({ path: "shots/auth-3-checkin.png" });
check("arrives at step 1 of 4", await page.locator(".checkin__head .label").nth(1).innerText(),
  "STEP 1 OF 4");
check("first prompt preserved", await page.locator(".checkin__prompt").innerText(),
  "How are you today?");
await page.screenshot({ path: "shots/auth-4-checkin.png" });

// 7. Navigation now greets instead of offering Login.
const trigger = page.locator(".account__trigger");
check("nav greets the user", (await trigger.innerText()).replace(/\s+/g, " ").trim(),
  `HELLO, ${GREETING.toUpperCase()}`);
check("nav hides Login", await page.locator(".nav__cta").count(), 0);

// 8. The account panel opens, and Escape closes it.
await trigger.click();
await page.waitForSelector(".account__menu");
check("panel lists restart", await page.locator(".account__item").first().innerText(),
  "RESTART SCREENING");
check("panel lists sign out", await page.locator(".account__item").nth(1).innerText(), "LOG OUT");
await page.screenshot({ path: "shots/auth-5-account.png" });
await page.keyboard.press("Escape");
check("Escape closes the panel", await page.locator(".account__menu").count(), 0);

// 9. A reload restores the session instead of bouncing to the gate.
await page.reload({ waitUntil: "networkidle" });
check("session survives reload", await page.locator(".account__trigger").count(), 1);
check("still authenticated after reload", new URL(page.url()).pathname, "/screen");

// 10. An authenticated visitor is offered the session, not the form, and the
//     same page answers at both entry paths.
for (const path of ["/", "/login"]) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  check(`authed ${path} hides the form`, await page.locator(".signin__input").count(), 0);
  check(`authed ${path} offers the session`,
    await page.locator(".entry__heading").innerText(), "You are signed in.");
}

// 11. Signing out closes the session, and back cannot reopen the workspace.
await page.locator(".account__trigger").click();
await page.locator(".account__menu .account__item", { hasText: "Log out" }).click();
await page.waitForSelector(".signin__input", { timeout: 10000 });
check("logout returns to /login", new URL(page.url()).pathname, "/login");
check("nav shows Login again", await page.locator(".nav__cta").innerText(), "LOGIN");
check("token cleared from storage",
  await page.evaluate(() =>
    window.localStorage.getItem("mental.ai.auth") === null &&
    window.sessionStorage.getItem("mental.ai.auth") === null), true);

// Back lands on the entry, which is public; what matters is that the protected
// route stays out of reach and the form is offered again rather than cached.
await page.goBack({ waitUntil: "networkidle" });
check("back cannot re-enter /screen", new URL(page.url()).pathname !== "/screen", true);
check("back shows the sign-in form", await page.locator(".signin__input").count(), 2);

// 12. Remember me off keeps the session out of localStorage; on puts it back.
await page.uncheck(".signin__check input");
await signIn(page, { password: CREDS.password });
await page.waitForSelector(".entry__greeting", { timeout: 15000 });
check("unchecked keeps token out of localStorage",
  await page.evaluate(() => window.localStorage.getItem("mental.ai.auth") === null), true);
check("unchecked still holds it for this tab",
  await page.evaluate(() => window.sessionStorage.getItem("mental.ai.auth") !== null), true);

check("reloading with the token gone signs the user out", await (async () => {
  await page.evaluate(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
  await page.reload({ waitUntil: "networkidle" });
  // The reload lands on the entry, which is public; the point is that the
  // session is gone and the protected route is not reachable from it.
  return (
    new URL(page.url()).pathname !== "/screen" &&
    (await page.locator(".signin__input").count()) === 2
  );
})(), true);

// 13. Keyboard only: tab from the user field reaches the submit control.
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
check("user field takes focus on arrival",
  await page.evaluate(() => document.activeElement?.getAttribute("name")), "username");
await page.keyboard.type(CREDS.email);
await page.keyboard.press("Tab");
check("tab from user field reaches the password field",
  await page.evaluate(() => document.activeElement?.getAttribute("name")), "password");
await page.keyboard.type(CREDS.password);
await page.keyboard.press("Enter");
// The greeting holds for about a second before the workspace is entered, so
// wait for the check-in rather than sampling immediately.
await page.waitForSelector(".entry__greeting", { timeout: 15000 });
await page.waitForSelector(".checkin__input", { timeout: 15000 });
check("Enter submits the form", await page.locator(".checkin__input").count(), 1);

// 14. Reduced motion still renders a usable field and completes the flow.
const reducedPage = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  reducedMotion: "reduce",
});
await reducedPage.goto(`${BASE}/login`, { waitUntil: "networkidle" });
check("field renders under reduced motion",
  await reducedPage.locator(".signin__input").count(), 2);
// The stage is a lazy chunk, so wait for it rather than sampling on first paint.
await reducedPage.waitForSelector(".entry__stage canvas", { timeout: 15000 });
check("sculpture present under reduced motion",
  await reducedPage.locator(".entry__stage canvas").count(), 1);
check("reduced motion picked an engine",
  await reducedPage.getAttribute(".entry__stage canvas", "data-engine") !== "none", true);
check("reduced motion still renders the wordmark",
  await reducedPage.locator(".entry__word").count(), 2);
await reducedPage.close();

// 15. Tablet and mobile keep the gate usable.
for (const [label, width, height] of [["tablet", 900, 1000], ["mobile", 390, 844]]) {
  const p = await browser.newPage({ viewport: { width, height } });
  await p.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  check(`${label}: form visible`, await p.locator(".signin__submit").isVisible(), true);
  check(`${label}: login control present`, await p.locator(".nav__cta, .nav__burger").count() > 0, true);
  check(`${label}: brand wordmark legible`, await p.locator(".entry__word").first().isVisible(), true);
  await p.screenshot({ path: `shots/auth-6-${label}.png` });
  await p.close();
}

// 16. Seeded session: /login must not render the form.
const seeded = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await seedSession(seeded, BASE);
const seededResponses = [];
seeded.on("response", (r) => {
  if (r.url().includes("/auth/")) seededResponses.push(`${r.status()} ${new URL(r.url()).pathname}`);
});
await seedSession(seeded, BASE);
await seeded.goto(`${BASE}/login`, { waitUntil: "networkidle" });
const gateInputs = await seeded.locator(".signin__input").count();
if (gateInputs !== 0) {
  console.log("  diag:", seededResponses.join(", "), "| path:", new URL(seeded.url()).pathname,
    "| mirror present:", await seeded.evaluate(() => ({
      persistent: localStorage.getItem("mental.ai.auth") !== null,
      tab: sessionStorage.getItem("mental.ai.auth") !== null,
    })));
}
check("seeded session skips the gate", gateInputs, 0);
await seeded.close();

check("zero console errors", consoleErrors, []);
if (consoleErrors.length) console.log(consoleErrors.slice(0, 5));

await browser.close();
const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
