// Actual configured login + real public Supabase settings only.
// Never submits a password, creates an account, or accesses screening records.
import assert from "node:assert/strict";
import fs from "node:fs";
import { launchChromium } from "./auth.mjs";
const BASE=process.argv[2]??"http://127.0.0.1:5199";
if(!["127.0.0.1","localhost"].includes(new URL(BASE).hostname))throw new Error("Configuration acceptance requires loopback app");
const PROJECT="https://omvjzcpcmkqgmgrzeesh.supabase.co";
const report={recorded_utc:new Date().toISOString(),layer:"actual local app + real public Supabase settings; no authenticated user or database operation",checks:[],forbidden_requests:[],errors:[]};
const check=label=>{report.checks.push({label,status:"PASSED"});console.log(`pass: ${label}`);};
const browser=await launchChromium();
try{
 const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:"reduce"});
 const page=await context.newPage();
 page.on("pageerror",e=>report.errors.push(e.message));
 await context.route(`${PROJECT}/**`,async route=>{
  const req=route.request();const url=new URL(req.url());
  if(url.pathname==="/auth/v1/settings"&&["GET","OPTIONS"].includes(req.method()))return route.continue();
  report.forbidden_requests.push({method:req.method(),path:url.pathname});await route.abort();
 });
 await context.route(`${new URL(BASE).origin}/api/**`,async route=>{
  const req=route.request();const path=new URL(req.url()).pathname;
  if(req.method()==="GET"&&["/api/configuration","/api/health","/api/ready","/api/live","/api/auth/providers"].includes(path))return route.continue();
  report.forbidden_requests.push({method:req.method(),path});await route.abort();
 });
 await page.goto(`${BASE}/login`);
 const google=page.getByRole("button",{name:"Continue with Google"});
 await google.waitFor({state:"visible",timeout:15000});
 assert.equal(await google.isEnabled(),true);
 check("Actual configured browser exposes enabled Google control");
 const service=await page.evaluate(async()=>{
  const responses=await Promise.all([fetch("/api/live"),fetch("/api/configuration")]);
  return {live_status:responses[0].status,configuration_status:responses[1].status,live:await responses[0].json(),configuration:await responses[1].json()};
 });
 assert.equal(service.live_status,200);assert.equal(service.live.alive,true);
 assert.equal(service.configuration_status,200);assert.equal(service.configuration.schema_version,"1.0");
 assert.ok(Number.isInteger(service.configuration.max_text_length)&&service.configuration.max_text_length>=1000);
 assert.equal(service.configuration.max_body_bytes,service.configuration.max_text_length*12+4096);
 report.local_public_api=service;
 check("Normal API proxy serves liveness and validated input configuration without authentication bypass");
 await page.getByRole("button",{name:"Create an account",exact:true}).click();
 assert.equal(await page.locator(".entry__heading").innerText(),"Create your account.");
 assert.equal(await page.locator(".signin__input").count(),2);
 check("Existing registration form available without submitting account/email");
 const response=page.waitForResponse(r=>r.url()===`${PROJECT}/auth/v1/settings`&&r.request().method()==="GET");
 await google.click();
 const settingsResponse=await response;
 assert.equal(settingsResponse.status(),200);
 const settings=await settingsResponse.json();
 assert.equal(settings.external.google,false,"Provider configuration changed; review actual Google enablement separately");
 report.remote_settings={http_status:200,email:settings.external.email,google:settings.external.google,mailer_autoconfirm:settings.mailer_autoconfirm};
 check("Browser reaches real project public settings with HTTP200");
 const error=page.locator(".signin__msg--request");
 await error.waitFor({timeout:15000});
 assert.ok((await error.innerText()).includes("Google sign-in is not enabled"));
 assert.ok(!(await page.locator(".entry__panel").innerText()).includes("Supabase is not configured"));
 assert.equal(new URL(page.url()).pathname,"/login");
 assert.equal(await google.isEnabled(),true);
 check("Configured SDK reports actual disabled provider instead of missing configuration");
 assert.deepEqual(report.forbidden_requests,[]);assert.deepEqual(report.errors,[]);
 check("No private/authentication/write requests or uncaught browser errors");
 await page.screenshot({path:"../reports/supabase-configured-login.png",fullPage:true});
 await context.close();
 console.log(`${report.checks.length} configuration browser checks passed; real public settings only`);
}catch(error){report.failure=error.message;throw error;}
finally{await browser.close();fs.writeFileSync("../reports/supabase-configured-browser.json",JSON.stringify(report,null,2)+"\n");}
