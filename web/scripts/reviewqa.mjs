import assert from "node:assert/strict";
import fs from "node:fs";
import { launchChromium } from "./auth.mjs";

const base = process.argv[2] ?? "http://127.0.0.1:5173";
const browser = await launchChromium();
fs.mkdirSync("shots", { recursive: true });
try {
  for (const [width,height] of [[1440,900],[1280,720],[390,844]]) {
    const page = await browser.newPage({ viewport:{width,height} });
    const errors = [];
    page.on("pageerror",e => errors.push(e.message));
    // This test isolates layout and privacy from external auth/config availability.
    await page.route("**/api/**",route => route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({google:false,email_password:true,status:"ok",artifacts_ok:false})}));
    await page.addInitScript(() => {
      window.__reviewFrames = [];
      const started = performance.now();
      function sample() {
        const node = document.querySelector(".hero-stage__scene");
        const canvas = document.querySelector(".entry__stage canvas");
        if (node) {
          const scene = node.getBoundingClientRect();
          const word = document.querySelector(".entry__word-plane--front .entry__word").getBoundingClientRect();
          window.__reviewFrames.push({x:scene.x,w:scene.width,canvasWidth:canvas?.width,wordX:word.x,
            split:document.querySelector(".entry").classList.contains("entry--split")});
        }
        if (performance.now()-started<12000) requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
    });
    await page.goto(base, {waitUntil:"domcontentloaded"});
    await page.locator(".entry__stage canvas").waitFor();
    const canvas = await page.locator(".entry__stage canvas").elementHandle();
    await page.waitForFunction(() => document.querySelector(".entry").classList.contains("entry--split"));
    await page.waitForTimeout(1500);
    const samples = await page.evaluate(() => window.__reviewFrames);
    const initial = {x:samples[0].x,width:samples[0].w};
    const final = await page.locator(".hero-stage__scene").boundingBox();
    assert.equal(samples[0].split,false,"sequence must begin before split");
    if (width>1180) {
      assert.ok(final.x<initial.x-100,"scene must shift left");
      assert.ok(samples.every(s=>Math.abs(s.w-initial.width)<1),"scene must not resize during handover");
      assert.equal(new Set(samples.map(s=>s.canvasWidth).filter(Boolean)).size,1,"canvas backing buffer must remain stable");
      for (let i=1;i<samples.length;i++) {
        assert.ok(samples[i].x<=samples[i-1].x+0.1,"scene must move monotonically left");
        assert.ok(Math.abs((samples[i].wordX-samples[i].x)-(samples[0].wordX-samples[0].x))<1,"word and sculpture move together");
      }
      const hero=await page.locator(".hero-stage").boundingBox();
      const auth=await page.locator(".auth-stage").boundingBox();
      assert.ok(Math.abs(hero.width/(hero.width+auth.width)-0.7)<0.001);
    }
    assert.ok(await canvas.evaluate(n=>n===document.querySelector(".entry__stage canvas")),"canvas must not remount");
    assert.equal(await page.locator(".entry__word-plane--front .entry__letter:not(.entry__letter--behind)").count(),9);
    assert.equal(await page.locator(".entry__word-plane--back .entry__letter:not(.entry__letter--behind)").count(),0);
    assert.equal(await page.locator(".auth-stage").isVisible(),true);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    assert.deepEqual(errors,[]);
    await page.screenshot({path:`shots/review-settled-${width}.png`});
    await page.close();
  }
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  await page.route("**/api/**",route=>route.fulfill({status:200,contentType:"application/json",body:'{"google":false,"email_password":true}'}));
  await page.goto(base);
  await page.waitForFunction(()=>document.querySelector(".entry").classList.contains("entry--split"));
  assert.equal(await page.locator(".hero-stage__scene").evaluate(n=>getComputedStyle(n).transitionDuration),"0s");
  // Network inspection executes the production local-inference module in the browser.
  const outgoing=[];
  page.on("request",request=>outgoing.push({url:request.url(),body:request.postData()}));
  const sentinel="private-text-network-sentinel-7429";
  const result=await page.evaluate(async text=>{
    const {runOnDeviceInference}=await import("/src/lib/onDeviceInference.ts");
    return runOnDeviceInference(text);
  },sentinel);
  assert.equal(result.primary.status,"unavailable");
  assert.ok(outgoing.every(r=>!r.url.includes(sentinel)&&!r.body?.includes(sentinel)));
  assert.ok(outgoing.every(r=>!r.url.includes("/api/predict")));
  assert.equal(result.urgency.suicide_probability,null);
  fs.writeFileSync("shots/review-network.json",JSON.stringify(outgoing,null,2));
  console.log("Browser layout, layering, stable canvas, 70/30 handover, reduced motion and local text network checks passed");
} finally { await browser.close(); }
