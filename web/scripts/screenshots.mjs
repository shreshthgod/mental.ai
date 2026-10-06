// Visual QA: renders the app at the required sizes and captures screenshots.
// Usage: node scripts/screenshots.mjs [baseURL]
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.argv[2] ?? "http://localhost:5173";
const SIZES = [
  [1440, 900],
  [1280, 800],
  [1024, 768],
  [768, 1024],
  [390, 844],
];
const ROUTES = ["/", "/login", "/screen", "/research"];

mkdirSync("shots", { recursive: true });

const browser = await chromium.launch();
for (const [w, h] of SIZES) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  // Seed the demo session so /screen renders past the login gate.
  await page.addInitScript(() =>
    window.localStorage.setItem(
      "vantage.auth",
      JSON.stringify({ user: "admin", at: Date.now() })
    )
  );
  for (const route of ROUTES) {
    const name = route === "/" ? "home" : route.slice(1);
    await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(3400); // let the intro + emergence settle
    await page.screenshot({ path: `shots/${name}-${w}x${h}.png` });
    if (route === "/") {
      await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight * 0.45 }));
      await page.waitForTimeout(1400);
      await page.screenshot({ path: `shots/${name}-mid-${w}x${h}.png` });
      await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight }));
      await page.waitForTimeout(1400);
      await page.screenshot({ path: `shots/${name}-end-${w}x${h}.png` });
    }
    console.log(`captured ${name} @ ${w}x${h}`);
  }
  await page.close();
}
await browser.close();
console.log("done");
