// Exercises the application's modules, compiled with the existing TypeScript dependency.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import ts from "typescript";

const root = path.resolve("..");
const work = fs.mkdtempSync(path.join(os.tmpdir(), "mental-ai-contract-"));
const require = createRequire(import.meta.url);
let checked = 0;
try {
  fs.symlinkSync(path.resolve("node_modules"), path.join(work, "node_modules"));
  fs.writeFileSync(path.join(work, "supabase.js"), "exports.supabase = null; exports.supabaseConfigured = false;\n");
  for (const name of ["analysisView", "api", "privateStore", "history", "checkin", "auth"]) {
    // Replace only Vite's environment object for this isolated Node test.
    const source = fs.readFileSync(`src/lib/${name}.ts`, "utf8").replaceAll("import.meta.env", "({})");
    fs.writeFileSync(path.join(work, `${name}.js`), ts.transpileModule(source, {
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
    }).outputText);
  }
  const { parsePrediction, analysisView, formatProbability, analysisErrorView } = require(path.join(work, "analysisView.js"));
  const { api, ApiError, setAuthToken } = require(path.join(work, "api.js"));
  const { setPrivateOwner, privateStorageKey } = require(path.join(work, "privateStore.js"));
  const history = require(path.join(work, "history.js"));
  const checkin = require(path.join(work, "checkin.js"));
  const fixtures = JSON.parse(fs.readFileSync(path.join(root, "tests/contract/analysis-v1.json"), "utf8"));
  for (const fixture of fixtures.success_cases) {
    const response = parsePrediction(structuredClone(fixture.response));
    assert.deepEqual(response, fixture.response);
    const view = analysisView(response);
    if (response.safety.level === "HIGH") assert.equal(view.title, "Urgent support");
    if (response.safety.level === "IMMEDIATE") assert.equal(view.title, "Immediate support");
    if (response.safety.level === "UNKNOWN") assert.equal(view.title, "Assessment uncertain");
    if (response.safety.analysis_status === "unsupported") assert.equal(view.capabilityTitle, "Unsupported analysis");
    if (response.primary.status === "unavailable") assert.equal(view.primaryLabel, "Unavailable");
    if (response.urgency.status === "unavailable") {
      assert.equal(view.urgencyLabel, "Unavailable");
      assert.equal(view.urgencyProbability, null);
      assert.equal(formatProbability(view.urgencyProbability), "Unavailable");
    }
    assert.equal(view.supportAction, response.safety.support_action);
    assert.equal(view.urgencyThreshold, response.urgency.decision_threshold_used);
    assert.deepEqual(response.primary.class_probabilities, fixture.response.primary.class_probabilities);
    checked++;
  }
  const oldStorage = globalThis.localStorage;
  const storage = new Map();
  globalThis.localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
  };
  try {
    const legacy = { id: "legacy-local", at: 1000, text: "synthetic old text", condition: "Normal", conditionProb: .9, urgencyFlagged: false, urgencyProb: .1 };
    const oldValue = JSON.stringify([legacy]);
    storage.set("mental.ai.history", oldValue);
    setPrivateOwner("synthetic-b");
    assert.equal(history.loadHistory().length, 0);
    assert.equal(storage.get("mental.ai.history"), oldValue); // Preserve unowned data, do not assign it.
    checked++;
    setPrivateOwner("synthetic-a");
    storage.set(privateStorageKey("mental.ai.history"), oldValue);
    assert.equal(history.loadHistory()[0].assessment, "legacy_unassessed");
    checked++;
    const response = structuredClone(fixtures.success_cases.find(c => c.name === "high").response);
    const saved = history.saveScreening("synthetic current text", response);
    assert.equal(saved.savedToDevice, true);
    assert.deepEqual(saved.records[0].response, response);
    setPrivateOwner("synthetic-b");
    assert.equal(history.loadHistory().length, 0);
    setPrivateOwner("synthetic-a");
    assert.deepEqual(history.loadHistory()[0].response, response);
    checked++;
    const answers = { greeting: "Hello", feeling: "I do not want to die", weighing: "My friend needs support", today: "Yesterday I got help" };
    checkin.saveCheckIn(answers);
    assert.equal(checkin.checkInToText(answers), Object.values(answers).join("\n"));
    setPrivateOwner("synthetic-b");
    assert.equal(checkin.loadCheckIn(), null);
    setPrivateOwner("synthetic-a");
    assert.deepEqual(checkin.loadCheckIn(), answers);
    checked++;
    for (const fixture of fixtures.success_cases) {
      const entry = history.saveScreening("synthetic fixture text", fixture.response);
      assert.deepEqual(entry.records[0].response, fixture.response);
      assert.deepEqual(history.loadHistory()[0].response, fixture.response);
      checked++;
    }
    const { persistence: _ack, ...snapshot } = response;
    history.clearHistory(); // Isolate this mapping check from the12-entry retention limit.
    const rows = history.mergeAccountHistory([
      { id: "synthetic-cloud", created_at: new Date().toISOString(), analysis_result: snapshot, assessment_kind: "authoritative" },
      { id: "synthetic-legacy", created_at: new Date().toISOString(), analysis_result: null, assessment_kind: "legacy_unassessed" },
      { id: "synthetic-corrupt", created_at: new Date().toISOString(), analysis_result: { schema_version: "1.0" }, assessment_kind: "authoritative" },
    ]);
    const cloud = rows.find(r => r.id === "synthetic-cloud");
    assert.equal(cloud.text, null);
    assert.deepEqual(cloud.response.safety, snapshot.safety);
    assert.equal(cloud.response.persistence.record_id, "synthetic-cloud");
    assert.equal(history.historyTitle(cloud), "Urgent support");
    assert.equal(history.historyTitle(rows.find(r => r.id === "synthetic-legacy")), "Legacy / unassessed");
    assert.equal(history.historyTitle(rows.find(r => r.id === "synthetic-corrupt")), "Recorded analysis unavailable");
    checked++;
    const storeWrite = globalThis.localStorage.setItem;
    globalThis.localStorage.setItem = () => { throw new Error("synthetic storage failure"); };
    assert.equal(history.saveScreening("synthetic", response).savedToDevice, false);
    globalThis.localStorage.setItem = storeWrite;
    checked++;
  } finally {
    setPrivateOwner(null);
    globalThis.localStorage = oldStorage;
  }
  const base = fixtures.success_cases.find(c => c.name === "high").response;
  for (const mutate of [
    v => { v.safety.level = "safe"; }, v => { v.safety.subject = "everyone"; },
    v => { v.safety.temporal_context = "immediate"; },
    v => { v.safety.support_action = "You're fine, no risk."; },
    v => { v.components.primary = "unavailable"; },
    v => { v.urgency.suicide_probability = null; },
    v => { v.primary.class_probabilities.Normal = Number.NaN; },
    v => { v.persistence.status = "saved"; v.persistence.record_id = null; },
  ]) {
    const wrong = structuredClone(base);
    mutate(wrong);
    assert.throws(() => parsePrediction(wrong));
    checked++;
  }
  const originalFetch = globalThis.fetch;
  try {
    let calls = 0;
    let authorization;
    globalThis.fetch = async (url, init) => {
      calls++;
      authorization = init.headers.get("Authorization");
      return new Response(JSON.stringify({}), { status: 200 });
    };
    setAuthToken("synthetic-stale-token");
    await api.login("synthetic@example.com", "synthetic-password");
    assert.equal(authorization, "");
    checked++;
    const cancelled = new AbortController();
    cancelled.abort();
    const before = calls;
    await assert.rejects(api.predict("synthetic", cancelled.signal), e => e.name === "AbortError");
    assert.equal(calls, before);
    checked++;
    for (const fixture of fixtures.error_cases) {
      globalThis.fetch = async () => new Response(JSON.stringify(fixture.response), {
        status: fixture.status, headers: fixture.retry_after ? { "Retry-After": fixture.retry_after } : {},
      });
      const expectedKind = { 401: "unauthorized", 422: "validation", 429: "throttled" }[fixture.status];
      await assert.rejects(api.predict("synthetic"), e => {
        assert.ok(e instanceof ApiError);
        assert.equal(e.kind, expectedKind);
        assert.ok(analysisErrorView(e).title);
        if (fixture.status === 429) assert.equal(e.retryAfterSeconds, 60);
        return true;
      });
      checked++;
    }
    globalThis.fetch = async () => new Response(JSON.stringify({ primary: { predicted_class: "Normal" } }), { status: 200 });
    await assert.rejects(api.predict("synthetic"), e => e.kind === "unavailable");
    checked++;
  } finally {
    globalThis.fetch = originalFetch;
    setAuthToken(null);
  }
  const auth = require(path.join(work, "auth.js"));
  const sessionStores = [globalThis.localStorage, globalThis.sessionStorage];
  const fetchBeforeAuth = globalThis.fetch;
  const authData = new Map();
  globalThis.localStorage = globalThis.sessionStorage = {
    getItem: key => authData.get(key) ?? null,
    setItem: (key, value) => authData.set(key, value), removeItem: key => authData.delete(key),
  };
  try {
    let completeVerification;
    let verificationStarted;
    const started = new Promise(resolve => { verificationStarted = resolve; });
    globalThis.fetch = async url => {
      if (url.endsWith("/auth/login")) return new Response(JSON.stringify({ token: "synthetic-token", refresh_token: "synthetic-refresh", user: "synthetic@example.com", user_id: "synthetic-owner", name: "Synthetic", expires_at: 1800000000 }), { status: 200 });
      verificationStarted();
      return new Promise(resolve => { completeVerification = resolve; });
    };
    const adoption = auth.login("synthetic@example.com", "synthetic-password");
    const outcome = adoption.then(() => "adopted", () => "cancelled");
    await started;
    auth.logout();
    completeVerification(new Response(JSON.stringify({ user: "synthetic@example.com", user_id: "synthetic-owner", name: "Synthetic" }), { status: 200 }));
    await outcome;
    assert.equal(auth.currentSession(), null, "late verification must not undo logout");
    assert.equal(require(path.join(work, "api.js")).getAuthToken(), null);
    checked++;
    let resolveOld;
    let oldStarted;
    const oldReady = new Promise(resolve => { oldStarted = resolve; });
    const identities = {
      a: { token: "synthetic-a", refresh_token: "synthetic-refresh-a", user: "a@example.com", user_id: "owner-a", name: "A", expires_at: 1800000000 },
      b: { token: "synthetic-b", refresh_token: "synthetic-refresh-b", user: "b@example.com", user_id: "owner-b", name: "B", expires_at: 1800000000 },
    };
    globalThis.fetch = async (url, init) => {
      if (url.endsWith("/auth/login")) {
        const identity = JSON.parse(init.body).user_id.startsWith("a") ? identities.a : identities.b;
        return new Response(JSON.stringify(identity), { status: 200 });
      }
      const token = init.headers.get("Authorization");
      if (token === "Bearer synthetic-a") {
        oldStarted(); return new Promise(resolve => { resolveOld = resolve; });
      }
      assert.equal(token, "Bearer synthetic-b"); // Candidate verified independently of current bearer.
      return new Response(JSON.stringify(identities.b), { status: 200 });
    };
    const old = auth.login("a@example.com", "synthetic-password").catch(() => null);
    await oldReady;
    await auth.login("b@example.com", "synthetic-password");
    resolveOld(new Response(JSON.stringify({ detail: "Rejected synthetic old candidate" }), { status: 401 }));
    await old;
    assert.equal(auth.currentUserId(), "owner-b");
    assert.equal(require(path.join(work, "api.js")).getAuthToken(), "synthetic-b");
    assert.equal(require(path.join(work, "privateStore.js")).privateOwner(), "owner-b");
    checked++;
    auth.logout();
    authData.set("mental.ai.auth", JSON.stringify({ token: "synthetic-expired", refreshToken: "synthetic-refresh-b", user: "b@example.com", userId: "owner-b", name: "B", expiresAt: Date.now() - 1000 }));
    let refreshCalls = 0;
    globalThis.fetch = async (url, init) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls++;
        assert.equal(JSON.parse(init.body).refresh_token, "synthetic-refresh-b");
        return new Response(JSON.stringify(identities.b), { status: 200 });
      }
      return new Response(JSON.stringify({ detail: "Expired synthetic access token" }), { status: 401 });
    };
    await auth.validateSession();
    assert.equal(auth.currentUserId(), "owner-b", "expired mirror must try its refresh token before signing out");
    assert.equal(refreshCalls, 1);
    checked++;
  } finally {
    auth.logout();
    [globalThis.localStorage, globalThis.sessionStorage] = sessionStores;
    globalThis.fetch = fetchBeforeAuth;
  }
  console.log(`contract QA: ${checked} checks passed; ${fixtures.success_cases.length} shared response states; mocked fetch, actual application modules`);
} finally {
  fs.rmSync(work, { recursive: true, force: true });
}
