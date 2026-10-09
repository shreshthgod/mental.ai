// Real browser/HTTP/model acceptance against tests/serve_synthetic_api.py only.
// Provider transport is an in-memory STUB. Failure-state responses below are explicit fixtures.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { launchChromium } from "./auth.mjs";
const BASE = process.argv[2] ?? "http://127.0.0.1:5173";
if (!["127.0.0.1", "localhost"].includes(new URL(BASE).hostname)) throw new Error("Synthetic acceptance requires loopback");
const report = { started_at: new Date().toISOString(), layer: "Chromium + HTTP + actual API/models; synthetic provider transport; explicit fixture overrides", checks: [], original: null, errors: [] };
const record = (label, details = {}) => {
  report.checks.push({ label, status: "PASSED", ...details });
  console.log(`pass: ${label}`);
};
const fixtures = JSON.parse(fs.readFileSync("../tests/contract/analysis-v1.json", "utf8"));
const browser = await launchChromium();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", e => report.errors.push(e.message));
  const signIn = async (email, password) => {
    await page.goto(`${BASE}/login`);
    await page.locator(".signin__input").nth(0).fill(email);
    await page.locator(".signin__input").nth(1).fill(password);
    await page.locator(".signin__submit").click();
    await page.waitForSelector(".checkin__input, #screen-input", { timeout: 15000 });
  };
  const checkIn = async () => {
    if (await page.locator("#screen-input").count()) return;
    for (let i = 0; i < 4; i++) {
      await page.locator(".checkin__input").fill(i === 0 ? "synthetic check-in" : "");
      await page.locator(".checkin__submit").click();
    }
  };
  const submit = async text => {
    if (await page.locator(".results").count()) await page.locator(".results__actions button").click();
    await page.locator("#screen-input").fill(text);
    const predicted = page.waitForResponse(r => r.url().endsWith("/predict") && r.request().method() === "POST");
    await page.locator(".screen-form button[type=submit]").click();
    return await predicted;
  };
  await signIn("alice@example.com", "alice-pass");
  record("Existing login authenticates synthetic identity");
  await checkIn();
  const originalHTTP = await submit("i wanna jump from 10th floor");
  const response = await originalHTTP.json();
  await page.waitForSelector(".results", { timeout: 15000 });
  const headline = await page.locator(".results__class").first().innerText();
  report.original = { http_status: originalHTTP.status(), raw_primary: response.primary, raw_urgency: response.urgency, safety: response.safety, components: response.components, persistence: response.persistence, displayed_headline: headline };
  assert.equal(response.safety.level, "HIGH"); assert.equal(response.primary.predicted_class, "Normal");
  assert.equal(response.safety.policy_version, fixtures.success_cases.find(c => c.name === "high").response.safety.policy_version);
  assert.equal(headline, "Urgent support");
  assert.ok((await page.locator(".support__lead").innerText()).includes("trust"));
  assert.ok(!(await page.locator(".results__class").allInnerTexts()).includes("Normal"));
  assert.ok((await page.locator(".results__class-sub").first().innerText()).includes("Normal"));
  assert.equal(response.safety.immediacy, "not_stated");
  record("Original: safety headline, honest raw Normal, useful support and unknown immediacy", { actual_models: true });
  await page.screenshot({ path: "../reports/browser-original-after.png", fullPage: true });
  const token = await page.evaluate(() => JSON.parse(localStorage.getItem("mental.ai.auth") ?? sessionStorage.getItem("mental.ai.auth")).token);
  const account = await page.request.get(`${BASE}/api/screenings`, { headers: { Authorization: `Bearer ${token}` } });
  assert.equal(account.status(), 200);
  const saved = (await account.json()).screenings.find(r => r.id === response.persistence.record_id);
  assert.deepEqual(saved.analysis_result.safety, response.safety);
  assert.equal(saved.analysis_result.model_version, response.model_version);
  record("Account read-back preserves original authoritative snapshot", { provider: "STUB" });
  await page.reload();
  await page.waitForSelector(".history__row", { timeout: 15000 });
  await page.locator(".history__row").filter({ hasText: "i wanna jump from 10th floor" }).first().click();
  assert.equal(await page.locator(".results__class").first().innerText(), "Urgent support");
  assert.equal(await page.locator(".results__title").innerText(), "Recorded support result");
  record("Reload/recorded history preserves safety and distinguishes recorded state");
  await page.evaluate(() => {
    const key = localStorage.getItem("mental.ai.auth") !== null ? localStorage : sessionStorage;
    const mirror = JSON.parse(key.getItem("mental.ai.auth"));
    mirror.expiresAt = Date.now() - 1000;
    key.setItem("mental.ai.auth", JSON.stringify(mirror));
  });
  const refreshed = page.waitForResponse(r => r.url().endsWith("/auth/refresh"));
  await page.reload();
  assert.equal((await refreshed).status(), 200);
  await page.waitForSelector("#screen-input", { timeout: 15000 });
  assert.ok((await page.locator(".account__trigger").innerText()).includes("ALICE"));
  record("Expired browser mirror attempts refresh and retains account", { provider: "STUB", actual_provider_expiry_not_tested: true });

  for (const item of [
    { name: "benign floor", text: "I live on the tenth floor", levels: ["NONE_DETECTED"], subject: "self" },
    { name: "fictional quotation", text: "In my novel, the character says I want to kill myself", levels: ["NONE_DETECTED"], subject: "fictional_or_quoted", temporal: "hypothetical" },
    { name: "historical recovery", text: "I tried to kill myself as a teenager. I am safe now.", levels: ["CONCERNING"], subject: "self", temporal: "historical" },
    { name: "another person", text: "My friend wants to kill himself", levels: ["HIGH"], subject: "another_person" },
    { name: "unsupported language", text: "Ich möchte heute sterben", levels: ["UNKNOWN"], capability: "unsupported" },
  ]) {
    const http = await submit(item.text); const output = await http.json();
    assert.equal(http.status(), 200); assert.ok(item.levels.includes(output.safety.level), `${item.name}: ${output.safety.level}`);
    if (item.subject) assert.equal(output.safety.subject, item.subject);
    if (item.temporal) assert.equal(output.safety.temporal_context, item.temporal);
    if (item.capability) assert.equal(output.safety.analysis_status, item.capability);
    await page.waitForSelector(".results");
    assert.equal(await page.locator(".support__lead").innerText(), output.safety.support_action);
    record(item.name, { actual_models: true, level: output.safety.level, subject: output.safety.subject, temporal: output.safety.temporal_context });
  }

  const titles = { HIGH: "Urgent support", IMMEDIATE: "Immediate support", CONCERNING: "Support recommended", NEEDS_CLARIFICATION: "More information needed", NONE_DETECTED: "No concern detected", UNKNOWN: "Assessment uncertain" };
  for (const fixture of fixtures.success_cases) {
    const value = structuredClone(fixture.response);
    value.request_id = `browser-${fixture.name}`;
    if (value.persistence.status === "saved") value.persistence.record_id = `browser-record-${fixture.name}`;
    await page.route("**/api/predict", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(value) }));
    await submit("synthetic fixture text");
    await page.waitForSelector(".results");
    assert.equal(await page.locator(".results__class").first().innerText(), titles[value.safety.level]);
    assert.equal(await page.locator(".support__lead").innerText(), value.safety.support_action);
    if (value.urgency.status === "unavailable") {
      assert.equal(await page.locator(".urgency-meter").count(), 0);
      assert.ok((await page.locator(".results").innerText()).includes("Raw urgency probability: Unavailable"));
      assert.ok(!(await page.locator(".results").innerText()).includes("Not elevated"));
    }
    if (value.primary.status === "unavailable") assert.equal(await page.locator(".probs__row").count(), 0);
    if (value.persistence.status === "not_saved") assert.ok((await page.locator(".support__note").innerText()).includes("Not saved to your account"));
    if (value.persistence.status === "unconfirmed") assert.ok((await page.locator(".support__note").innerText()).includes("Saving could not be confirmed"));
    const device = await page.evaluate(() => JSON.parse(localStorage.getItem("mental.ai.history.uuid-alice")));
    assert.deepEqual(device[0].response, value);
    await page.unroute("**/api/predict");
    record(`Rendered contract fixture: ${fixture.name}`, { mocked_response: true });
  }
  // React renders text safely even if a backend field contains markup characters.
  const markup = structuredClone(fixtures.success_cases.find(c => c.name === "high").response);
  markup.provenance_caveat = '<img src=x onerror="window.__unsafe = true">';
  await page.route("**/api/predict", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(markup) }));
  await submit("synthetic rendering fixture"); await page.waitForSelector(".results");
  assert.equal(await page.locator(".results__caveat img").count(), 0);
  assert.equal(await page.evaluate(() => window.__unsafe), undefined);
  await page.unroute("**/api/predict"); record("Returned text renders as text, not markup", { mocked_response: true });

  // An old result arriving after Cancel cannot replace a new one.
  let pending; const arrived = new Promise(resolve => { pending = resolve; });
  let oldRoute;
  await page.route("**/api/predict", route => { oldRoute = route; pending(); });
  if (await page.locator(".results").count()) await page.locator(".results__actions button").click();
  await page.locator("#screen-input").fill("synthetic old request");
  await page.locator(".screen-form button[type=submit]").click(); await arrived;
  await page.locator(".analysis__cancel").click();
  await page.unroute("**/api/predict");
  const newer = structuredClone(fixtures.success_cases.find(c => c.name === "high").response);
  newer.request_id = "browser-newer";
  await page.route("**/api/predict", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(newer) }));
  await submit("synthetic new request"); await page.waitForSelector(".results");
  await oldRoute.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixtures.success_cases.find(c => c.name === "none_detected").response) }).catch(() => {});
  assert.ok((await page.locator(".results__meta").innerText()).includes("browser-newer"));
  assert.equal(await page.locator(".results__class").first().innerText(), "Urgent support");
  await page.unroute("**/api/predict"); record("Cancelled/stale response cannot overwrite newer result", { mocked_response: true });

  for (const error of fixtures.error_cases.filter(c => c.status !== 401)) {
    await page.route("**/api/predict", route => route.fulfill({ status: error.status, contentType: "application/json", headers: error.retry_after ? { "Retry-After": error.retry_after } : {}, body: JSON.stringify(error.response) }));
    await submit("synthetic error text"); await page.waitForSelector(".error-panel");
    assert.equal(await page.locator(".results").count(), 0);
    if (error.status === 429) assert.ok((await page.locator(".error-panel__body").innerText()).includes("60 seconds"));
    await page.unroute("**/api/predict"); record(`HTTP error presentation ${error.status}`, { mocked_response: true });
  }
  await page.clock.install();
  await page.route("**/api/predict", () => {});
  if (await page.locator(".error-panel").count()) await page.locator(".error-panel__actions button").nth(1).click();
  await page.locator("#screen-input").fill("synthetic timeout");
  await page.locator(".screen-form button[type=submit]").click();
  await page.clock.fastForward(80001);
  await page.waitForSelector(".error-panel");
  assert.equal(await page.locator(".error-panel__title").innerText(), "Analysis timed out");
  assert.equal(await page.locator(".results").count(), 0);
  await page.unroute("**/api/predict"); record("Frontend deadline has explicit no-result support state", { mocked_hanging_fetch: true, clock_advanced_ms: 80001 });
  await page.clock.resume();

  const configHTTP = await page.request.get(`${BASE}/api/configuration`); const config = await configHTTP.json();
  await page.locator("#screen-input").fill("😀".repeat(config.max_text_length) + " I want to kill myself");
  assert.equal(await page.locator("#screen-input").inputValue(), "😀".repeat(config.max_text_length) + " I want to kill myself");
  assert.equal(await page.locator(".screen-form button[type=submit]").isDisabled(), true);
  record("Configured code-point limit preserves excess text and dangerous tail intact");

  await page.locator(".account__trigger").click();
  await page.locator(".account__item").filter({ hasText: "Log out" }).click();
  await page.waitForSelector(".signin__input");
  await signIn("bob@example.com", "bob-pass");
  assert.equal(await page.locator(".history__row").count(), 0);
  assert.equal(await page.locator(".results").count(), 0);
  await checkIn();
  assert.ok(!(await page.locator("#screen-input").inputValue()).includes("kill myself"));
  record("Account switch hides prior user's history/result/text", { provider: "STUB" });
  await page.route("**/api/predict", route => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Invalid token" }) }));
  await submit("synthetic unauthorized");
  await page.waitForSelector(".signin__input");
  assert.equal(await page.locator(".results").count(), 0);
  assert.equal(await page.evaluate(() => localStorage.getItem("mental.ai.auth")), null);
  record("Rejected token clears local session and returns to unchanged login", { mocked_response: true });
  assert.deepEqual(report.errors, []);
  record("No uncaught browser script errors");
} catch (err) { report.failure = { name: err.name, message: err.message }; throw err; }
finally {
  report.finished_at = new Date().toISOString(); report.passed = report.checks.length;
  const output = process.env.MENTAL_AI_BROWSER_REPORT ?? "../reports/browser-acceptance-current.json";
  fs.mkdirSync(path.dirname(output), { recursive: true }); fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
  await browser.close();
  console.log(`${report.passed} browser checks passed; provider STUB; ${output}`);
}
