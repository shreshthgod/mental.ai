// Actual app + installed Supabase SDK; all provider/API responses intercepted.
// Starts only its own loopback Vite process, uses no real project/accounts.
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { launchChromium } from "./auth.mjs";

const BASE = "http://127.0.0.1:5201";
const PROVIDER = "http://127.0.0.1:54321";
const built=process.argv.includes("--built");
if (process.argv.slice(2).some(arg=>arg!=="--built")) throw new Error("Only --built is supported; isolated loopback URLs are fixed");
const report = { layer:`Chromium + actual ${built ? "built" : "development"} app + installed SDK; provider/API INTERCEPTED; no account creation`, checks:[], errors:[] };
const record = label => { report.checks.push({label,status:"PASSED"}); console.log(`pass: ${label}`); };
const vite = spawn(process.execPath,["node_modules/vite/bin/vite.js",...(built ? ["preview"] : []),"--host","127.0.0.1","--port","5201","--strictPort"],{
  env:{...process.env,VITE_API_URL:"/api",VITE_SUPABASE_URL:PROVIDER,VITE_SUPABASE_PUBLISHABLE_KEY:"synthetic-public-key"},
  stdio:["ignore","pipe","pipe"],
});
let exited=false;
const exit = new Promise(resolve=>vite.once("exit",code=>{exited=true;resolve(code);}));
let browser;
try {
  const deadline=Date.now()+15000;
  while (true) {
    if (exited) throw new Error("Isolated Vite exited before startup (check port5201 availability)");
    try { const response=await fetch(BASE);if(response.ok)break; } catch { /* startup poll */ }
    if (Date.now()>deadline) throw new Error("Isolated Vite startup deadline expired");
    await delay(100);
  }
  browser=await launchChromium();
  const setup=async (provider="enabled",verify="valid")=>{
    const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
    const page=await context.newPage();
    page.on("pageerror",error=>report.errors.push(error.message));
    const user={id:"untrusted-sdk-owner",email:"fixture@example.com",user_metadata:{name:"Untrusted SDK"}};
    await context.route("**/*",async route=>{ try {
      const request=route.request();const url=new URL(request.url());
      const json=(value,status=200)=>route.fulfill({status,contentType:"application/json",headers:{"Access-Control-Allow-Origin":BASE,"Access-Control-Allow-Headers":"*","Access-Control-Allow-Methods":"GET,POST,OPTIONS"},body:JSON.stringify(value)});
      if (url.origin===PROVIDER) {
        if (request.method()==="OPTIONS") return json({});
        if (url.pathname!=="/auth/v1/authorize") assert.equal(request.headers().apikey,"synthetic-public-key");
        if (url.pathname==="/auth/v1/settings") {
          assert.equal(request.headers().authorization,undefined);
          return provider==="unavailable" ? json({},503) : json({external:{google:provider==="enabled"}});
        }
        if (url.pathname==="/auth/v1/authorize") return route.fulfill({contentType:"text/html",body:"<p>Synthetic provider redirect</p>"});
        if (url.pathname==="/auth/v1/user") return json(user);
        if (url.pathname==="/auth/v1/logout") return json({});
        throw new Error(`Unexpected synthetic provider route: ${url.pathname}`);
      }
      if (url.origin===BASE && url.pathname.startsWith("/api/")) {
        if (url.pathname==="/api/auth/session") {
          assert.ok(request.headers().authorization?.startsWith("Bearer "));
          return verify==="valid" ? json({user_id:"verified-owner",user:"fixture@example.com",name:"Verified Fixture"}) : json({detail:"Invalid session"},401);
        }
        if (url.pathname==="/api/configuration") return json({schema_version:"1.0",max_text_length:10000,max_body_bytes:124096,urgency_threshold:0.15,policy_version:"synthetic-policy",semantic_status:"disabled"});
        if (url.pathname==="/api/health") return json({status:"healthy",models_loaded:true,version:"synthetic"});
        if (url.pathname==="/api/screenings") return json({screenings:[],count:0});
        throw new Error(`Unexpected private API route: ${url.pathname}`);
      }
      if (url.origin!==BASE) throw new Error("Unexpected external network request in isolated OAuth QA");
      return route.continue();
    } catch(error) { report.errors.push(error.message);await route.abort(); }
    });
    return {context,page};
  };
  const callback = (destination="/screen?source=fixture",error=false)=>{
    const fragment=error ? "error=access_denied&error_description=Private_provider_detail" : new URLSearchParams({access_token:"synthetic-sdk-access",refresh_token:"synthetic-sdk-refresh",expires_in:"3600",token_type:"bearer"}).toString();
    return `${BASE}${destination}#${fragment}`;
  };
  for (const remember of [true,false]) {
    const {context,page}=await setup();
    try {
      await page.goto(`${BASE}/screen?source=fixture#history`);
      await page.waitForURL(`${BASE}/login`);
      await page.locator('.signin__check input').setChecked(remember);
      await page.getByRole("button",{name:"Continue with Google"}).click();
      await page.waitForURL(`${PROVIDER}/auth/v1/authorize**`);
      const redirect=new URL(page.url());
      assert.equal(redirect.searchParams.get("provider"),"google");
      assert.equal(redirect.searchParams.get("redirect_to"),`${BASE}/screen?source=fixture#history`);
      assert.equal(redirect.searchParams.get("access_type"),null);
      record(`Rendered Google control preserves destination and remember=${remember}`);
      await page.goto(callback());
      await page.waitForSelector(".checkin__input",{timeout:15000});
      await page.waitForURL(`${BASE}/screen?source=fixture#history`);
      const current=await page.evaluate(()=>{
        const session=JSON.parse(localStorage.getItem("mental.ai.auth")??sessionStorage.getItem("mental.ai.auth"));
        return {owner:session.userId,name:session.name,local:!!localStorage.getItem("mental.ai.auth"),tab:!!sessionStorage.getItem("mental.ai.auth"),pending:sessionStorage.getItem("mental.ai.oauth")};
      });
      assert.deepEqual(current,{owner:"verified-owner",name:"Verified Fixture",local:remember,tab:!remember,pending:null});
      record(`Installed SDK callback verifies owner, restores hash, honors scope=${remember}`);
      await page.reload();await page.waitForSelector(".checkin__input");
      record(`Reload verifies the Google session with scope=${remember}`);
      await page.locator(".account__trigger").click();
      await page.getByRole("menuitem",{name:"Log out"}).click();
      await page.waitForSelector(".signin__social");
      assert.equal(await page.evaluate(()=>localStorage.getItem("mental.ai.auth")??sessionStorage.getItem("mental.ai.auth")),null);
      record(`Existing sign-out control clears Google session with scope=${remember}`);
    } finally {await context.close();}
  }
  for (const provider of ["disabled","unavailable"]) {
    const {context,page}=await setup(provider);
    try {
      await page.goto(`${BASE}/login`);
      await page.getByRole("button",{name:"Continue with Google"}).click();
      const error=page.locator(".signin__msg--request");
      await error.waitFor();
      assert.ok((await error.innerText()).includes(provider==="disabled" ? "not enabled" : "temporarily unavailable"));
      assert.equal(new URL(page.url()).pathname,"/login");
      assert.equal(await page.getByRole("button",{name:"Continue with Google"}).isEnabled(),true);
      record(`Rendered ${provider} provider error keeps login usable`);
    } finally {await context.close();}
  }
  for (const kind of ["provider_cancelled","server_rejected"]) {
    const {context,page}=await setup("enabled",kind==="server_rejected" ? "invalid" : "valid");
    try {
      await page.goto(`${BASE}/login`);
      await page.getByRole("button",{name:"Continue with Google"}).click();
      await page.waitForURL(`${PROVIDER}/auth/v1/authorize**`);
      await page.goto(callback("/screen",kind==="provider_cancelled"));
      await page.waitForSelector(".signin__msg--request",{timeout:15000});
      const message=await page.locator(".signin__msg--request").innerText();
      assert.ok(message.includes("Please try again"));
      assert.ok(!message.includes("Private_provider_detail"));
      assert.equal(await page.locator(".checkin__input").count(),0);
      assert.equal(await page.evaluate(()=>sessionStorage.getItem("mental.ai.oauth")),null);
      record(`Actual SDK ${kind} callback fails anonymously without provider details`);
    } finally {await context.close();}
  }
  assert.deepEqual(report.errors,[]);
  record("No uncaught browser script errors");
  console.log(`OAuth browser QA: ${report.checks.length} required grouped checks passed; provider/API intercepted`);
} catch(error) {
  report.failure=error.message;throw error;
} finally {
  await browser?.close();
  if (!exited) vite.kill("SIGTERM");
  await exit;
  report.owned_vite_stopped=true;
  fs.writeFileSync(`../reports/browser-oauth${built ? "-built" : ""}.json`,JSON.stringify(report,null,2)+"\n");
}
