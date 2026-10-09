// Actual auth modules with a controlled SDK/fetch; no Google/Supabase account is contacted.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import ts from "typescript";

const require = createRequire(import.meta.url);
const work = fs.mkdtempSync(path.join(os.tmpdir(), "mental-ai-oauth-"));
let checked = 0;
try {
  fs.symlinkSync(path.resolve("node_modules"), path.join(work, "node_modules"));
  for (const name of ["api", "analysisView", "privateStore", "auth"]) {
    const source = fs.readFileSync(`src/lib/${name}.ts`, "utf8").replaceAll("import.meta.env", "({})");
    fs.writeFileSync(path.join(work, `${name}.js`), ts.transpileModule(source, {
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS },
    }).outputText);
  }
  fs.writeFileSync(path.join(work, "supabase.js"), `
exports.supabaseConfigured = true;
exports.googleProviderStatus = async () => globalThis.__providerStatus ?? "enabled";
exports.supabase = {auth:{
  signInWithOAuth: async options => globalThis.__oauth(options),
  getSession: async () => ({data:{session:globalThis.__remoteSession},error:globalThis.__sessionError}),
  initialize: async () => globalThis.__initializeHang ? new Promise(()=>{}) : ({error:globalThis.__initializeError}),
  onAuthStateChange: callback => { globalThis.__authEvent=callback; return {data:{subscription:{unsubscribe(){}}}}; },
  signOut: async () => ({error:null})
}};
`);
  const stores = [new Map(), new Map()];
  const storage = data => ({ getItem:key=>data.get(key) ?? null,
    setItem:(key,value)=>data.set(key,value), removeItem:key=>data.delete(key) });
  globalThis.localStorage = storage(stores[0]);
  globalThis.sessionStorage = storage(stores[1]);
  globalThis.window = { location: { origin: "http://127.0.0.1:5199", href: "http://127.0.0.1:5199/login" } };
  const auth = require(path.join(work, "auth.js"));
  const identity = { user_id:"sdk-owner",user:"fixture@example.com",name:"Fixture" };
  globalThis.fetch = async (_url, init) => {
    assert.equal(init.headers.get("Authorization"), "Bearer synthetic-oauth-token");
    return new Response(JSON.stringify(identity),{status:200});
  };
  globalThis.__remoteSession = {
    access_token:"synthetic-oauth-token",refresh_token:"synthetic-refresh",expires_at:1800000000,
    user:{id:"untrusted-browser-owner",email:"fixture@example.com",user_metadata:{name:"Unverified"}},
  };
  let request;
  globalThis.__oauth = async options => { request=options; return {error:null}; };
  await auth.signInWithGoogle({remember:true,returnTo:"/screen?source=fixture#history"});
  assert.equal(request.options.redirectTo,"http://127.0.0.1:5199/screen?source=fixture#history");
  checked++;
  await auth.validateSession();
  assert.equal(auth.currentUserId(),"sdk-owner");
  assert.ok(stores[0].get("mental.ai.auth"),"Google Remember me must survive the redirect");
  assert.equal(stores[1].get("mental.ai.auth"),undefined);
  assert.equal(auth.consumeOAuthReturnPath(),"/screen?source=fixture#history");
  assert.equal(auth.consumeOAuthReturnPath(),null);
  checked++;
  auth.logout();
  await auth.signInWithGoogle({remember:false,returnTo:"//untrusted.example"});
  assert.equal(request.options.redirectTo,"http://127.0.0.1:5199/screen");
  await auth.validateSession();
  assert.ok(stores[1].get("mental.ai.auth"));
  assert.equal(stores[0].get("mental.ai.auth"),undefined);
  checked++;
  auth.logout();
  globalThis.__oauth = async () => ({error:{message:"Synthetic provider failure"}});
  await assert.rejects(auth.signInWithGoogle({remember:true}),/Google sign-in could not be started/);
  assert.equal(stores[1].get("mental.ai.oauth"),undefined,"Failed initiation must clear pending intent");
  checked++;
  auth.logout();
  globalThis.__oauth = async options => { request=options; return {error:null}; };
  for (const returnTo of ["https://untrusted.example", "/\\untrusted.example", "/screen\nignored"]) {
    await auth.signInWithGoogle({returnTo});
    assert.equal(request.options.redirectTo,"http://127.0.0.1:5199/screen");
    checked++;
  }
  auth.logout();
  stores[1].set("mental.ai.oauth", JSON.stringify({remember:true,returnTo:"/screen#history",startedAt:Date.now()-16*60*1000}));
  await auth.validateSession();
  assert.ok(stores[1].get("mental.ai.auth"),"Expired OAuth intent must default to tab scope");
  assert.equal(stores[0].get("mental.ai.auth"),undefined);
  assert.equal(auth.consumeOAuthReturnPath(),null);
  checked++;
  auth.logout();
  globalThis.__sessionError = {message:"Synthetic callback error containing private provider details"};
  await auth.signInWithGoogle();
  await auth.validateSession();
  assert.equal(auth.currentSession(),null);
  assert.equal(auth.authError(),"Sign-in could not be completed. Please try again.");
  assert.equal(stores[1].get("mental.ai.oauth"),undefined);
  checked++;
  globalThis.__sessionError = null;
  globalThis.__remoteSession.expires_at = undefined;
  await auth.validateSession();
  assert.equal(auth.currentSession(),null,"Missing expiry must not fabricate an hour-long session");
  checked++;
  globalThis.__remoteSession.expires_at = 1800000000;
  await auth.signInWithGoogle({returnTo:"/screen#history"});
  let verificationStarted;
  const started = new Promise(resolve => { verificationStarted=resolve; });
  let finishVerification;
  globalThis.fetch = async () => {
    verificationStarted();
    return new Promise(resolve => { finishVerification=()=>resolve(new Response(JSON.stringify(identity),{status:200})); });
  };
  const restoring = auth.validateSession();
  await started;
  auth.logout();
  finishVerification();
  await restoring;
  assert.equal(auth.currentSession(),null,"Late SDK verification must not undo logout");
  assert.equal(auth.consumeOAuthReturnPath(),null);
  assert.equal(stores[1].get("mental.ai.oauth"),undefined);
  checked++;
  auth.logout();
  let oauthCalls=0;
  globalThis.__oauth = async () => { oauthCalls++; return {error:null}; };
  for (const status of ["disabled","unavailable"]) {
    globalThis.__providerStatus = status;
    await assert.rejects(auth.signInWithGoogle(), status === "disabled" ? /not enabled/ : /temporarily unavailable/);
    assert.equal(oauthCalls,0,"Unavailable Google provider must not redirect");
    assert.equal(stores[1].get("mental.ai.oauth"),undefined);
    checked++;
  }
  globalThis.__providerStatus = "enabled";
  auth.logout();
  globalThis.__initializeError = {message:"Private initialization detail"};
  await auth.validateSession();
  assert.equal(auth.currentSession(),null);
  assert.equal(auth.authError(),"Sign-in could not be completed. Please try again.");
  checked++;
  globalThis.__initializeError = null;
  globalThis.__initializeHang = true;
  const realTimeout = globalThis.setTimeout;
  try {
    globalThis.setTimeout = (callback, _ms) => realTimeout(callback,1);
    await auth.validateSession();
    assert.equal(auth.currentSession(),null,"Stalled SDK boot must not leave restoring forever");
    assert.equal(auth.authError(),"Sign-in could not be completed. Please try again.");
    checked++;
  } finally { globalThis.setTimeout = realTimeout; globalThis.__initializeHang=false; }
  const actualSource = fs.readFileSync("src/lib/supabase.ts","utf8")
    .replaceAll("import.meta.env", "({VITE_SUPABASE_URL:'http://127.0.0.1:54321',VITE_SUPABASE_PUBLISHABLE_KEY:'synthetic-public-key'})");
  const compiled = ts.transpileModule(actualSource, {
    compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS},
  }).outputText.replace('require("@supabase/supabase-js")','require("./sdkfixture")');
  fs.writeFileSync(path.join(work,"sdkfixture.js"),'exports.createClient=()=>({auth:{}});');
  fs.writeFileSync(path.join(work,"actual-supabase.js"),compiled);
  const {googleProviderStatus} = require(path.join(work,"actual-supabase.js"));
  for (const [response,expected] of [
    [{external:{google:true}},"enabled"], [{external:{google:false}},"disabled"],
    [{external:{google:"true"}},"unavailable"], [{external:{}},"unavailable"], [null,"unavailable"],
  ]) {
    globalThis.fetch = async (url,init) => {
      assert.equal(url,"http://127.0.0.1:54321/auth/v1/settings");
      assert.deepEqual(init.headers,{apikey:"synthetic-public-key"});
      assert.equal(init.credentials,"omit");
      assert.equal(init.redirect,"error");
      return new Response(JSON.stringify(response),{status:200});
    };
    assert.equal(await googleProviderStatus(),expected);
    checked++;
  }
  globalThis.fetch = async ()=>new Response("private provider response",{status:503});
  assert.equal(await googleProviderStatus(),"unavailable");checked++;
  globalThis.fetch = async ()=>{throw new Error("private network detail");};
  assert.equal(await googleProviderStatus(),"unavailable");checked++;
  try {
    globalThis.setTimeout = (callback,_ms)=>realTimeout(callback,1);
    globalThis.fetch = async (_url,init)=>new Promise((_resolve,reject)=>{
      init.signal.addEventListener("abort",()=>reject(new DOMException("Synthetic timeout","AbortError")),{once:true});
    });
    assert.equal(await googleProviderStatus(),"unavailable");checked++;
  } finally { globalThis.setTimeout = realTimeout; }
  // Execute the actual legacy QA failure diagnostic with synthetic private storage.
  const diagnostic = fs.readFileSync("scripts/authflow.mjs","utf8")
    .split("if (gateInputs !== 0) {")[1].split('\n}\ncheck("seeded session')[0];
  const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
  const logs=[];
  stores[0].set("mental.ai.auth",JSON.stringify({token:"PRIVATE_FIXTURE_TOKEN"}));
  await new AsyncFunction("console","seededResponses","seeded",diagnostic)(
    {log:(...items)=>logs.push(items)},["401 session"],
    {url:()=>"http://127.0.0.1:5199/login",evaluate:async fn=>fn()});
  assert.ok(!JSON.stringify(logs).includes("PRIVATE_FIXTURE_TOKEN"),"QA failure diagnostics must not log authentication mirrors");
  stores[0].delete("mental.ai.auth");
  checked++;
  console.log(`OAuth QA: ${checked} required checks passed; actual modules, SDK/fetch mocked`);
} finally {
  fs.rmSync(work,{recursive:true,force:true});
}
