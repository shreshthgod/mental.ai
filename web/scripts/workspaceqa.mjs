import assert from "node:assert/strict";
import { launchChromium } from "./auth.mjs";

const browser=await launchChromium();
const base=process.argv[2]??"http://127.0.0.1:5173";
try {
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:"reduce"});
  const requests=[];
  page.on("request",r=>requests.push({url:r.url(),body:r.postData()}));
  await page.route("**/api/**",async route=>{
    const r=route.request(), path=new URL(r.url()).pathname;
    let body={};
    if(path.endsWith("/auth/login")) {
      const user=r.postDataJSON().user_id;
      body={token:user,refresh_token:`refresh-${user}`,user,user_id:user,name:user,
        expires_in:3600,expires_at:Math.floor(Date.now()/1000)+3600,token_type:"bearer"};
    } else if(path.endsWith("/auth/session")) {
      const user=(await r.allHeaders()).authorization?.replace("Bearer ","")??"account-a";
      body={user,user_id:user,name:user,issued_at:Date.now()/1000,expires_at:Date.now()/1000+3600,service_version:"synthetic-test"};
    } else if(path.endsWith("/configuration")) {
      body={schema_version:"1.0",max_text_length:10000,max_body_bytes:124096,urgency_threshold:null,policy_version:null,semantic_status:"disabled"};
    } else if(path.includes("/screenings")) body={screenings:[],count:0};
    else if(path.endsWith("/predict")) throw new Error("Unexpected raw-text request during private test");
    await route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(body)});
  });
  await page.addInitScript(()=>sessionStorage.setItem("mental.ai.auth",JSON.stringify({token:"account-a",refreshToken:"refresh-a",user:"a@test.invalid",userId:"account-a",name:"A",expiresAt:Date.now()+3600000})));
  await page.goto(`${base}/screen`);
  const input=page.locator(".checkin__input");
  await input.fill("account-a-private-disclosure");
  await page.getByLabel("Save check-in answers",{exact:false}).check();
  await page.evaluate(async()=>{const auth=await import("/src/lib/auth.ts");await auth.login("account-b","synthetic-password",false);});
  await page.waitForFunction(()=>document.querySelector(".checkin__input")?.value==="");
  assert.equal(await input.inputValue(),"");
  assert.equal(await page.getByLabel("Save check-in answers",{exact:false}).isChecked(),false);
  await input.fill("work-private-sentinel-7429");
  for(let i=0;i<3;i++) await page.locator(".checkin__submit").click();
  await page.locator(".checkin__submit").click();
  await page.locator("#screen-input").waitFor();
  await page.getByRole("button",{name:/^Analyze/}).click();
  await page.getByRole("region",{name:"Analysis result"}).waitFor();
  assert.ok(requests.every(r=>!r.body?.includes("work-private-sentinel")&&!r.url.includes("work-private-sentinel")));
  assert.equal(await page.evaluate(()=>localStorage.getItem("mental.ai.history.account-b")),null);
  assert.equal(await page.evaluate(()=>localStorage.getItem("mental.ai.personalization.account-b")),null);
  await page.locator("summary").filter({hasText:"Personalization"}).click();
  assert.equal(await page.getByLabel("Remember themes").isChecked(),false);
  await page.getByLabel("Remember themes").check();
  await page.getByRole("button",{name:/^Analyze/}).click();
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem("mental.ai.personalization.account-b"))?.rememberedThemes.includes("work and responsibilities"));
  await page.getByRole("button",{name:"Clear personalization and disable",exact:true}).click();
  await page.waitForFunction(()=>localStorage.getItem("mental.ai.personalization.account-b")===null);
  assert.equal(await page.getByLabel("Remember themes").isChecked(),false);
  await page.getByLabel("Save text and results",{exact:false}).check();
  await page.getByRole("button",{name:/^Analyze/}).click();
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem("mental.ai.history.account-b"))?.length===1);
  await page.getByRole("button",{name:"Legacy server models",exact:true}).click();
  await page.getByRole("button",{name:/^Analyze/}).click();
  await page.getByText("Consent to sending this text to the server before analysis.",{exact:true}).waitFor();
  assert.ok(requests.every(r=>!r.url.endsWith("/predict")));
  await page.getByRole("button",{name:"Delete local history, check-in and personalization",exact:true}).click();
  await page.locator(".checkin__input").waitFor();
  assert.equal(await page.locator(".checkin__input").inputValue(),"");
  assert.equal(await page.evaluate(()=>localStorage.getItem("mental.ai.history.account-b")),null);
  await page.evaluate(async()=>{const auth=await import("/src/lib/auth.ts");auth.logout();});
  await page.waitForURL("**/login");
  assert.equal(await page.locator("#screen-input").count(),0);
  assert.ok(!(await page.locator("body").innerText()).includes("work-private-sentinel"));
  console.log("Rendered account switch, local network privacy, storage consent, personalization deletion, server consent and logout passed (synthetic API)");
} finally {await browser.close();}
