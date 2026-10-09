// Built-bundle public-route checks; run against an explicitly isolated preview.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { launchChromium } from './auth.mjs';
const base=process.argv[2] ?? 'http://127.0.0.1:5200';
if (!['localhost','127.0.0.1'].includes(new URL(base).hostname)) throw new Error('Synthetic built-route QA requires loopback');
const source=JSON.parse(execFileSync('python3',[new URL('../../scripts/source_fingerprint.py',import.meta.url).pathname],{encoding:'utf8'}));
const assets=new URL('../dist/assets/',import.meta.url);
const bundle=Object.fromEntries(fs.readdirSync(assets).sort().map(name=>[name,
  createHash('sha256').update(fs.readFileSync(new URL(name,assets))).digest('hex')]));
const report={started_at:new Date().toISOString(),source,built_asset_sha256:bundle,
  layer:'built frontend Chromium/loopback public routes; isolated backend, no user data',checks:[],errors:[]};
const browser=await launchChromium();
let active, activePage;
try {
  for (const width of [1440,390]) {
    const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce'});
    activePage=page;
    page.on('pageerror',error=>report.errors.push(error.message));
    for (const route of ['/','/login','/about','/research']) {
      active={route,width};
      const response=await page.goto(base+route,{waitUntil:'networkidle'});
      assert.equal(response.status(),200);
      await page.waitForSelector('#main');
      const text=await page.locator('#main').innerText();
      assert.ok(text.length>40);
      if (route==='/about') {
        for (const claim of ['routed to human review','routes text to people','a human absorbs the false positives']) {
          assert.ok(!text.includes(claim),`Unimplemented reviewer workflow: ${claim}`);
        }
        assert.ok(text.includes('selected on the test split'),'Consumed urgency threshold selection must be disclosed');
      }
      if (route==='/research') assert.equal(await page.locator('h1').innerText(),'RESEARCH');
      if (route==='/' || route==='/login') assert.equal(await page.locator('.signin__input').count(),2);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
      report.checks.push({route,width,status:'PASSED'});
      if (route==='/about' && width===1440) await page.screenshot({path:new URL('../../reports/browser-built-about.png',import.meta.url).pathname});
    }
    await page.goto(base+'/screen',{waitUntil:'networkidle'});
    assert.equal(new URL(page.url()).pathname,'/login');
    report.checks.push({route:'/screen protected redirect',width,status:'PASSED'});
    const live=await page.request.get(base+'/api/live');
    assert.equal(live.status(),200); assert.equal((await live.json()).alive,true);
    report.checks.push({route:'/api/live preview proxy',width,status:'PASSED'});
    await page.close();
  }
  assert.deepEqual(report.errors,[]);
  console.log(`${report.checks.length} built-route checks passed; no uncaught errors`);
} catch(error) {
  report.checks.push({...active,status:'FAILED',error_type:error.name});
  report.failure={type:error.name};
  if (activePage && !activePage.isClosed()) {
    report.overflow=await activePage.evaluate(()=>({viewport:window.innerWidth,document:document.documentElement.scrollWidth,
      elements:[...document.querySelectorAll('#main *')].map(element=>({tag:element.tagName,class:element.className,
        right:element.getBoundingClientRect().right,width:element.getBoundingClientRect().width,scroll:element.scrollWidth}))
        .filter(element=>element.right>window.innerWidth+1).slice(0,30)}));
    await activePage.screenshot({path:new URL('../../reports/browser-built-failure.png',import.meta.url).pathname});
  }
  throw error;
} finally {
  await browser.close();
  fs.writeFileSync(new URL('../../reports/browser-built-routes.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
}
