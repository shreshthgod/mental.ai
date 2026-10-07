// Failure-mode + reduced-motion QA.
import { mkdirSync } from "node:fs";
import { apiPattern, completeCheckIn, launchChromium, seedSession } from "./auth.mjs";


const BASE = process.argv[2] ?? "http://localhost:5173";
mkdirSync("shots", { recursive: true });

const browser = await launchChromium();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
// A real token, so /screen renders past the gate and only the failure being
// exercised below is the thing under test.
await seedSession(page, BASE);

// /screen opens on the check-in; the workspace sits behind it. Both steps are
// part of the flow under test here, since the rest of this script works against
// the workspace editor.
await page.goto(`${BASE}/screen`, { waitUntil: "networkidle" });
await page.waitForSelector(".checkin__input", { timeout: 15000 });
await completeCheckIn(page, [
  "Not great.",
  "Anxious.",
  "Work.",
  "Could not sleep.",
]);
await page.waitForSelector("#screen-input", { timeout: 15000 });

// Oversized input (backend max 10,000) - fill 10,500 chars
await page.fill("#screen-input", "a".repeat(10_500));
await page.waitForTimeout(400);
await page.screenshot({ path: "shots/fail-1-oversize.png" });
const btnDisabled = await page.isDisabled("button[type=submit]");
console.log("oversize: analyze disabled =", btnDisabled);

// Backend unreachable.
//
// The block is installed only now, after the page has loaded and the session has
// been validated. Blocking it earlier would make session validation fail too,
// which sends the visitor to the sign-in gate - correct behaviour, but it would
// mean this script never exercised the analysis error path it exists to cover.
await page.context().route(apiPattern(BASE), (r) => r.abort());
await page.fill("#screen-input", "test input for unavailable backend");
await page.click("button[type=submit]");
await page.waitForSelector(".error-panel", { timeout: 15000 });
await page.screenshot({ path: "shots/fail-2-unavailable.png" });
console.log("backend-down error panel shown");

// A blocked session check must land on the sign-in gate rather than the workspace.
const anon = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await anon.context().route(apiPattern(BASE), (r) => r.abort());
await anon.goto(`${BASE}/screen`, { waitUntil: "domcontentloaded" });
await anon.waitForSelector(".signin__input", { timeout: 15000 });
console.log("unverifiable session redirected to sign-in = true");
await anon.close();

// Status indicator must report offline rather than a hardcoded ready.
//
// Checked on /research, which is public: with every /api call blocked the
// session check fails first on /screen, so the workspace is never reachable and
// its status chip cannot be observed. A fresh page is also required because the
// chip polls on an interval and the one on the page above was checked while the
// backend was still up.
const publicPage = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await publicPage.context().route(apiPattern(BASE), (r) => r.abort());
await publicPage.goto(`${BASE}/research`, { waitUntil: "networkidle" });
await publicPage.waitForFunction(
  () => /offline|unavailable|degraded/i.test(document.body.innerText),
  { timeout: 20000 }
);
const statusText = (await publicPage.locator(".status").first().innerText())
  .replace(/\s+/g, " ")
  .trim();
console.log("status with backend blocked =", statusText);
await publicPage.screenshot({ path: "shots/fail-3-status-offline.png" });
await publicPage.close();

// Reduced motion
const ctx2 = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
const p2 = await ctx2.newPage();
await seedSession(p2, BASE);
await p2.goto(BASE, { waitUntil: "networkidle" });
await p2.waitForTimeout(2500);
await p2.screenshot({ path: "shots/reduced-motion-home.png" });
console.log("reduced motion captured");

await browser.close();
console.log("failure QA done");
