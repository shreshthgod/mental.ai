// Failure-mode + reduced-motion QA.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.argv[2] ?? "http://localhost:5173";
mkdirSync("shots", { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

// Oversized input (backend max 10,000) - fill 10,500 chars
await page.goto(`${BASE}/screen`, { waitUntil: "networkidle" });
await page.fill("#screen-input", "a".repeat(10_500));
await page.waitForTimeout(400);
await page.screenshot({ path: "shots/fail-1-oversize.png" });
const btnDisabled = await page.isDisabled("button[type=submit]");
console.log("oversize: analyze disabled =", btnDisabled);

// Backend down - block all API requests at the browser level
await page.context().route("**/api/**", (r) => r.abort());
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(2500);
await page.screenshot({ path: "shots/fail-2-status-offline.png" });
await page.fill("#screen-input", "test input for unavailable backend");
await page.click("button[type=submit]");
await page.waitForSelector(".error-panel", { timeout: 15000 });
await page.screenshot({ path: "shots/fail-3-unavailable.png" });
console.log("backend-down error panel shown");

// Reduced motion
const ctx2 = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
const p2 = await ctx2.newPage();
await p2.goto(BASE, { waitUntil: "networkidle" });
await p2.waitForTimeout(2500);
await p2.screenshot({ path: "shots/reduced-motion-home.png" });
console.log("reduced motion captured");

await browser.close();
console.log("failure QA done");
