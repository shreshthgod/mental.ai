// Interaction QA: intro frames, screening flow, error states.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.argv[2] ?? "http://localhost:5173";
mkdirSync("shots", { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

// 1. Intro assembly frames (fresh session)
await page.goto(BASE, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(450);
await page.screenshot({ path: "shots/intro-1-assembly.png" });
await page.waitForTimeout(500);
await page.screenshot({ path: "shots/intro-2-converge.png" });
await page.waitForTimeout(1200);
await page.screenshot({ path: "shots/intro-3-live.png" });

// 2. Screening flow - real backend
await page.goto(`${BASE}/screen`, { waitUntil: "networkidle" });
await page.waitForSelector(".status--ready, .status--down", { timeout: 15000 });
await page.fill("#screen-input", "I have been feeling empty and hopeless for weeks. I do not enjoy anything anymore and I cannot sleep.");
await page.click("button[type=submit]");
await page.waitForTimeout(700);
await page.screenshot({ path: "shots/flow-1-analyzing.png" });
await page.waitForSelector(".results", { timeout: 30000 });
await page.waitForTimeout(1300);
await page.screenshot({ path: "shots/flow-2-results.png", fullPage: true });

// 3. Urgent text
await page.click("text=New analysis");
await page.fill("#screen-input", "I want to end my life. There is no reason to keep going and nobody would miss me.");
await page.click("button[type=submit]");
await page.waitForSelector(".results", { timeout: 30000 });
await page.waitForTimeout(1300);
await page.screenshot({ path: "shots/flow-3-urgent.png", fullPage: true });

// 4. Empty input validation
await page.click("text=New analysis");
await page.fill("#screen-input", "");
await page.screenshot({ path: "shots/flow-4-empty.png" });

console.log("interaction QA done");
await browser.close();
