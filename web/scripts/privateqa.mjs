import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import ts from "typescript";

const work = fs.mkdtempSync(path.join(os.tmpdir(), "mental-private-"));
const require = createRequire(import.meta.url);
try {
  for (const name of ["onDeviceInference", "personalization", "privateStore", "analysisView", "history"]) {
    fs.writeFileSync(path.join(work, `${name}.js`), ts.transpileModule(
      fs.readFileSync(`src/lib/${name}.ts`, "utf8"),
      { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }
    ).outputText);
  }
  const storage = new Map();
  globalThis.localStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
  };
  globalThis.fetch = () => { throw new Error("Private inference made a network request"); };
  globalThis.XMLHttpRequest = class { constructor() { throw new Error("XHR forbidden"); } };
  globalThis.WebSocket = class { constructor() { throw new Error("WebSocket forbidden"); } };
  const { runOnDeviceInference, evaluateOnDeviceEmotions } = require(path.join(work, "onDeviceInference.js"));
  const { parsePrediction, analysisView } = require(path.join(work, "analysisView.js"));
  const { setPrivateOwner } = require(path.join(work, "privateStore.js"));
  const prefs = require(path.join(work, "personalization.js"));
  const history = require(path.join(work, "history.js"));
  for (const text of ["I am happy", "I am anxious", "I want to kill myself tonight", "मुझे मदद चाहिए", "mujhe bahut udaas lag raha hai"]) {
    const result = parsePrediction(await runOnDeviceInference(text));
    assert.equal(result.primary.status, "unavailable");
    assert.equal(result.primary.predicted_class, null);
    assert.deepEqual(result.primary.class_probabilities, {});
    assert.equal(result.urgency.status, "unavailable");
    assert.equal(result.urgency.suicide_probability, null);
    assert.equal(result.components.preprocessing, "unavailable");
    assert.equal(result.persistence.status, "not_saved");
    assert.ok(result.model_version);
    if (text.includes("kill myself")) assert.equal(analysisView(result).urgent, true);
    if (text.includes("मुझे") || text.includes("mujhe")) assert.equal(result.safety.level, "UNKNOWN");
  }
  assert.equal(evaluateOnDeviceEmotions("I am happy").status, "disabled");
  assert.deepEqual(evaluateOnDeviceEmotions("I am happy").emotions, []);
  setPrivateOwner("account-a");
  assert.equal(prefs.loadPersonalizationPrefs().enabled, false);
  prefs.recordSessionVisit("work and sleep");
  assert.equal(storage.size, 0);
  prefs.savePersonalizationPrefs({ enabled: true });
  prefs.recordSessionVisit("work and sleep");
  assert.ok(prefs.loadPersonalizationPrefs().rememberedThemes.length > 0);
  prefs.clearRememberedThemes();
  assert.deepEqual(prefs.loadPersonalizationPrefs().rememberedThemes, []);
  prefs.recordSessionVisit("work");
  prefs.savePersonalizationPrefs({ enabled: false });
  assert.deepEqual(prefs.loadPersonalizationPrefs().rememberedThemes, []);
  prefs.clearAllPersonalization();
  assert.equal(prefs.loadPersonalizationPrefs().enabled, false);
  const result = await runOnDeviceInference("private account a text");
  history.saveScreening("private account a text", result);
  const beforeMerge = new Map(storage);
  history.mergeAccountHistory([{ id: "server-record", created_at: new Date().toISOString(), analysis_result: null }]);
  assert.deepEqual(storage, beforeMerge, "Fetched server history must not persist without local consent");
  setPrivateOwner("account-b");
  assert.deepEqual(history.loadHistory(), []);
  assert.equal(prefs.loadPersonalizationPrefs().enabled, false);
  setPrivateOwner(null);
  assert.deepEqual(history.loadHistory(), []);
  setPrivateOwner("account-a");
  assert.equal(history.loadHistory()[0].text, "private account a text");
  assert.equal(history.clearHistory(), true);
  assert.deepEqual(history.loadHistory(), []);
  console.log("Private inference, consent, deletion and account isolation checks passed");
} finally {
  fs.rmSync(work, { recursive: true, force: true });
}
