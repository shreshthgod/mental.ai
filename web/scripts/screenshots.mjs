// Visual QA: renders the app at the required sizes and captures screenshots.
// Usage: node scripts/screenshots.mjs [baseURL]
import { mkdirSync } from "node:fs";
import { launchChromium, seedSession } from "./auth.mjs";


const BASE = process.argv[2] ?? "http://localhost:5173";
const SIZES = [
  [1440, 900],
  [1280, 800],
  [1024, 768],
  [768, 1024],
  [390, 844],
];
// The entry and /login are captured signed out on purpose: they are the first
// thing every visitor sees, so the unauthenticated state is the one worth
// reviewing. The long-form product page moved to /about when "/" became the
// entry experience.
const ROUTES = ["/", "/login", "/about", "/screen", "/research"];

mkdirSync("shots", { recursive: true });

const browser = await launchChromium();
for (const [w, h] of SIZES) {
  // A real token, so / and /screen render past the gate.
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await seedSession(page, BASE);

  // Second context with no session, used only for the /login capture.
  const anon = await browser.newPage({ viewport: { width: w, height: h } });

  for (const route of ROUTES) {
    if (route === "/" || route === "/login") {
      await anon.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
      await anon.waitForTimeout(1200);
      await anon.screenshot({ path: `shots/${route === "/" ? "entry" : "login"}-${w}x${h}.png` });
      console.log(`captured ${route} signed out @ ${w}x${h}`);
      continue;
    }
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
  await anon.close();
}
await browser.close();
console.log("done");
