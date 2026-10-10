// Entry-experience QA: composition across resolutions, the greeting stage, and
// the WebGL degradation path.
//
//   node scripts/entryqa.mjs [baseUrl]
//
// Checks the things a screenshot review would otherwise have to catch by eye:
// that the oversized wordmark stays inside its zone, that the credentials never
// collide with the copy, that the sculpture is actually mounted and painting,
// and that the login form survives a machine with no WebGL at all.
import { mkdirSync } from "node:fs";
import { expectedFirstName, launchChromium, qaCredentials as CREDS, seedSession } from "./auth.mjs";

const BASE = process.argv[2] ?? "http://localhost:5173";
const GREETING = expectedFirstName();
mkdirSync("shots", { recursive: true });

const results = [];
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  results.push(ok);
  console.log(`${ok ? "pass" : "FAIL"}  ${label}${ok ? "" : ` (got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)})`}`);
}
const near = (a, b, tol = 1.5) => Math.abs(a - b) <= tol;

const DESKTOP = [
  [1920, 1080],
  [1600, 900],
  [1536, 1024],
  [1536, 864],
  [1440, 900],
  [1366, 768],
  [1280, 800],
  [1280, 720],
];
const TABLET = [[1024, 768], [900, 1000]];
const MOBILE = [[430, 932], [390, 844], [412, 915], [360, 800]];

const browser = await launchChromium();

// Composition at every required size
for (const [w, h] of [...DESKTOP, ...TABLET, ...MOBILE]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error" && !m.text().includes("Failed to load resource")) errors.push(m.text());
  });

  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForSelector(".signin__submit", { timeout: 30000 });
  // Let the whole entrance finish so measurements are of the settled layout:
  // the intro assembles to ~3140ms and the hand-over to the 70/30 composition
  // then runs for --entry-handover (1200ms), so 5s clears both with margin.
  await page.waitForTimeout(6000);

  const m = await page.evaluate(() => {
    const box = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        x: r.x, y: r.y, w: r.width, h: r.height,
        right: r.right, bottom: r.bottom,
      };
    };
    const canvas = document.querySelector(".entry__stage canvas");
    const dpr = window.devicePixelRatio || 1;
    return {
      hero: box(".hero-stage"),
      auth: box(".auth-stage"),
      word: box(".entry__word-plane--back .entry__word"),
      panel: box(".entry__panel-inner"),
      panelSlot: box(".entry__panel-slot"),
      copy: box(".entry__copy"),
      cta: box(".entry__ctas"),
      headline: box(".entry__headline"),
      foot: box(".auth-stage__foot"),
      logo: box(".nav__wordmark"),
      navCta: box(".nav__cta"),
      input: box(".signin__input"),
      submit: box(".signin__submit"),
      // The render buffer must match the canvas box it is stretched over, or
      // the stage is being scaled and everything inside it drifts.
      buffer: canvas
        ? { cw: canvas.clientWidth, ch: canvas.clientHeight, bw: canvas.width, bh: canvas.height, dpr }
        : null,
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
      scrollH: document.documentElement.scrollHeight,
      innerH: window.innerHeight,
      engine: canvas?.dataset.engine,
      sideBySide: getComputedStyle(document.querySelector(".entry__main")).gridTemplateColumns.split(" ").length > 1,
    };
  });

  const tag = `${w}x${h}`;
  const near = (a, b, tol = 1.5) => Math.abs(a - b) <= tol;
  // No horizontal scroll at any size.
  check(`${tag} no horizontal overflow`, m.scrollW <= m.innerW + 1, true);
  // The wordmark must stay inside the viewport horizontally.
  check(`${tag} wordmark inside viewport`, m.word.x >= -2 && m.word.right <= m.innerW + 2, true);

  // Alignment: the composition is one grid, so these edges are equal by
  // construction. Any drift means something is positioned independently.
  // The two-column invariants only hold where the layout is two columns.
  check(`${tag} wordmark inside hero stage`, m.word.right <= m.hero.right + 1, true);
  // On the two-column frame the word hangs off the stage's left edge, which is
  // the page gutter. On a phone the band is its own plate and the word is
  // centred in it instead; either is deliberate, an arbitrary offset is not.
  check(
    `${tag} wordmark anchored in the stage`,
    near(m.word.x, m.hero.x, 1.5) || near(m.word.x + m.word.w / 2, m.hero.x + m.hero.w / 2, 2),
    true
  );
  check(`${tag} hero copy on the logo line`, near(m.copy.x, m.logo.x, 1.5), true);
  check(`${tag} input and submit share edges`,
    near(m.input.x, m.submit.x, 0.5) && near(m.input.right, m.submit.right, 0.5), true);
  check(`${tag} headline holds one line`, m.headline.h < m.headline.w * 0.6, true);
  if (m.sideBySide) {
    check(`${tag} copy left of the auth stage`, m.copy.right < m.auth.x, true);
    check(`${tag} panel right on the nav edge`, near(m.panel.right, m.navCta.right, 1.5), true);
    // The annotation is dropped on windows too short to give it a row without
    // pushing the form off screen. When it is present it must sit on the panel's
    // right edge and clear of it.
    if (m.foot.w > 0) {
      check(`${tag} foot right on the panel edge`, near(m.foot.right, m.panel.right, 1.5), true);
      check(`${tag} foot clear of the panel`, m.foot.y > m.panel.bottom - 1, true);
    }
  }
  // The wordmark's box carries descender space below the baseline; the copy
  // has to clear the painted letters, not the box.
  check(`${tag} copy clear of the wordmark`, m.copy.y > m.word.bottom - m.word.h * 0.12, true);
  check(`${tag} panel below the header`, m.panel.y > m.hero.y - 1, true);

  // The canvas covers the stage exactly, at the renderer's own resolution.
  if (m.buffer) {
    check(`${tag} canvas matches the stage`,
      near(m.buffer.bw, m.buffer.cw * m.buffer.dpr, 1.5) && near(m.buffer.bh, m.buffer.ch * m.buffer.dpr, 1.5),
      true);
  }

  // Copy and credentials must not overlap. They sit in separate grid columns,
  // so this has to test both axes: sharing a row means their vertical ranges
  // coincide even though the columns do not.
  const overlaps = (a, b) =>
    !!a && !!b && a.x < b.right && b.x < a.right && a.y < b.y + b.h && b.y < a.y + a.h;
  check(`${tag} copy and panel do not overlap`, overlaps(m.panelSlot, m.copy), false);
  check(`${tag} CTA clear of the panel`, overlaps(m.cta, m.panel), false);
  check(`${tag} engine mounted`, m.engine !== "none", true);
  check(`${tag} submit reachable`, await page.locator(".signin__submit").isVisible(), true);
  // isVisible() passes for content that is laid out but clipped by an
  // overflow:hidden ancestor, so check the box is actually on the page.
  check(`${tag} CTA not clipped away`, m.cta.y + m.cta.h <= m.scrollH + 1, true);
  check(`${tag} panel not clipped away`, m.panel.y + m.panel.h <= m.scrollH + 1, true);
  // When the page does not scroll, everything has to fit the first screen.
  if (m.scrollH <= m.innerH + 1) {
    check(`${tag} CTA within the fold`, m.cta.y + m.cta.h <= m.innerH + 1, true);
    check(`${tag} panel within the fold`, m.panel.y + m.panel.h <= m.innerH + 1, true);
    check(`${tag} foot within the fold`, m.foot.bottom <= m.innerH + 1, true);
  }
  check(`${tag} no console errors`, errors, []);

  await page.screenshot({ path: `shots/entry-${w}x${h}.png` });
  await page.close();
}

// Opening motion and layering are covered by reviewqa.mjs.

// Reduced motion: the composed state, without the travel
{
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: "reduce",
  });
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForSelector(".signin__submit", { timeout: 30000 });
  await page.waitForTimeout(4600);

  const m = await page.evaluate(() => {
    const box = (sel) => {
      const node = document.querySelector(sel);
      if (!node) return null;
      const r = node.getBoundingClientRect();
      return { x: r.x, w: r.width };
    };
    return {
      split: document.querySelector(".entry").className.includes("entry--split"),
      hero: box(".hero-stage"),
      word: box(".entry__word-plane--back .entry__word"),
      // The grid and the word must not be mid-travel when reduced motion is on.
      gridTransition: getComputedStyle(document.querySelector(".entry__main")).transitionDuration,
      wordTransition: getComputedStyle(document.querySelector(".entry__word")).transitionDuration,
      submit: !!document.querySelector(".signin__submit")?.offsetParent,
    };
  });

  check("reduced motion still reaches the split state", m.split, true);
  check("reduced motion: no transform travel on the grid",
    m.gridTransition.split(",").every((d) => parseFloat(d) === 0), true);
  check("reduced motion: no transform travel on the word",
    m.wordTransition.split(",").every((d) => parseFloat(d) === 0), true);
  check("reduced motion: wordmark still on the stage edge", near(m.word.x, m.hero.x, 2), true);
  check("reduced motion: form still usable", m.submit, true);
  await page.screenshot({ path: "shots/entry-handover-reduced.png" });
  await page.close();
}

// Return visit: the composed state directly, no replay
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE, { waitUntil: "networkidle" });
  // Same session, so the intro key is already set: this is what a returning
  // visitor inside one browsing session sees.
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForSelector(".signin__submit", { timeout: 30000 });
  await page.waitForTimeout(900);

  const m = await page.evaluate(() => ({
    split: document.querySelector(".entry").className.includes("entry--split"),
    visible: getComputedStyle(document.querySelector(".auth-stage")).visibility,
  }));
  check("return visit reaches the composed state quickly", m.split, true);
  check("return visit reveals the credentials", m.visible, "visible");
  await page.close();
}

// The greeting stage, inside the composition
if (!CREDS.email || !CREDS.password) {
  console.log("skip  greeting stage QA (no MENTAL_AI_QA_EMAIL / SUPABASE_QA_EMAIL configured)");
} else {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  // Hold the transition open so the stage can actually be captured.
  await page.addInitScript(() => {
    const orig = window.setTimeout;
    window.setTimeout = (fn, ms, ...rest) => orig(fn, ms > 1000 && ms < 1400 ? 20000 : ms, ...rest);
  });
  await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
  await page.waitForSelector(".signin__input", { timeout: 15000 });
  await page.fill(".signin__input >> nth=0", CREDS.email);
  await page.fill(".signin__input >> nth=1", CREDS.password);
  await page.click(".signin__submit");
  await page.waitForSelector(".entry__greeting", { timeout: 15000 });
  await page.waitForTimeout(900);

  check("greeting names the account",
    await page.locator(".entry__greeting-name").innerText(), `${GREETING}.`);
  check("greeting marked as session",
    (await page.locator(".entry__greeting .label").nth(1).innerText()), "AUTHENTICATION COMPLETE");
  check("wordmark dims during the greeting",
    await page.locator(".entry__word-plane--dim").count(), 2);
  // The panel swaps to the session state the moment the session is live, so the
  // credentials are unmounted rather than merely hidden.
  check("credentials are removed during the greeting",
    await page.locator(".signin__input").count(), 0);
  check("session panel replaces them",
    await page.locator(".entry__heading").innerText(), "You are signed in.");
  check("sculpture still running behind the greeting",
    await page.locator(".entry__stage canvas").count(), 1);
  await page.screenshot({ path: "shots/entry-greeting.png" });
  await page.close();
}

// WebGL unavailable: the form must still work
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(() => {
    // Break context creation the way a blocked or driverless GPU would.
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
      if (type === "webgl" || type === "webgl2" || type === "experimental-webgl") return null;
      return original.call(this, type, ...rest);
    };
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForSelector(".signin__input", { timeout: 15000 });
  await page.waitForTimeout(1200);

  check("no WebGL: engine falls back", await page.getAttribute(".entry__stage canvas", "data-engine"), "fallback-2d");
  check("no WebGL: form still usable", await page.locator(".signin__submit").isVisible(), true);
  // Only the crossing letters are painted in the front plane; the rest hold
  // their box with visibility:hidden, so assert on a painted one.
  check("no WebGL: wordmark still legible",
    await page.locator(".entry__word-plane--front .entry__letter:not(.entry__letter--behind)").first().isVisible(), true);
  // Browser-emitted context warnings are expected on a machine with no WebGL;
  // what must be absent is an uncaught exception taking the page down.
  check("no WebGL: no uncaught errors", errors, []);

  if (CREDS.email && CREDS.password) {
    await page.fill(".signin__input >> nth=0", CREDS.email);
    await page.fill(".signin__input >> nth=1", CREDS.password);
    await page.click(".signin__submit");
    await page.waitForSelector(".entry__greeting", { timeout: 20000 });
    check("no WebGL: sign-in still completes", true, true);
  }
  await page.screenshot({ path: "shots/entry-no-webgl.png" });
  await ctx.close();
}

// Return state for an authenticated visitor
if (!CREDS.email || !CREDS.password) {
  console.log("skip  authenticated visitor QA (no MENTAL_AI_QA_EMAIL / SUPABASE_QA_EMAIL configured)");
} else {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await seedSession(page, BASE);
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForSelector(".entry__panel-slot", { timeout: 15000 });
  await page.waitForTimeout(1600);
  check("signed in: session offered", await page.locator(".entry__heading").innerText(), "You are signed in.");
  check("signed in: continue control present", await page.locator(".entry__submit-link").isVisible(), true);
  check("signed in: no credential fields", await page.locator(".signin__input").count(), 0);
  await page.screenshot({ path: "shots/entry-signed-in.png" });
  await page.close();
}

// Resize without a reload, and remount
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForSelector(".entry__stage canvas", { timeout: 15000 });
  for (const [w, h] of [[800, 900], [500, 900], [1600, 900], [1440, 900]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(350);
  }
  const alive = await page.evaluate(() => {
    const c = document.querySelector(".entry__stage canvas");
    return c ? c.width > 0 && c.height > 0 : false;
  });
  check("canvas survives resizes", alive, true);
  // The stage is a grid column, so its width changes without the window doing
  // anything: the renderer has to follow the container, not the viewport.
  const reframed = await page.evaluate(() => {
    const c = document.querySelector(".entry__stage canvas");
    if (!c) return false;
    const dpr = window.devicePixelRatio || 1;
    return (
      Math.abs(c.width - c.clientWidth * dpr) <= 1.5 &&
      Math.abs(c.height - c.clientHeight * dpr) <= 1.5
    );
  });
  check("canvas re-frames to its container after resizes", reframed, true);
  check("no overflow after resizes",
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true);
  // Navigate away and back: the GL context must be released and rebuilt.
  await page.goto(`${BASE}/research`, { waitUntil: "networkidle" });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForSelector(".entry__stage canvas", { timeout: 15000 });
  check("stage rebuilds after navigation", await page.locator(".entry__stage canvas").count(), 1);
  await page.close();
}

await browser.close();
const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);