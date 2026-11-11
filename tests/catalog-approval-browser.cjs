const assert=require('node:assert/strict');
const {chromium}=require('./browser-runtime.cjs');
const base=process.env.ALTOIDSS_TEST_URL;
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:360,height:1000}});
  const login=await context.request.post(base+'/api/index.php?route=/auth/login',
    {data:{email:'admin@example.invalid',password:process.env.ALTOIDSS_FIXTURE_PASSWORD}});
  assert.equal(login.status(),200);
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/Html/dashboard.html?tab=review',{waitUntil:'networkidle'});
  const card=page.locator('#catalogRequestList [data-catalog-request]').first();
  await card.waitFor();
  assert.equal(await card.locator('img').count(),0);
  assert.match(await card.locator('h3').innerText(),/<img src=x/);
  await card.scrollIntoViewIfNeeded();
  page.once('dialog',d=>d.accept());
  await card.locator('[data-catalog-decision="approve"]').click();
  await page.waitForFunction(()=>document.querySelector('#catalogRequestList .review-status')?.textContent==='Aprobada');
  await page.setViewportSize({width:1024,height:900});
  assert.equal(await page.locator('#catalogRequestList [data-catalog-decision]').count(),0);
  assert.deepEqual(errors,[]);
  await context.close();
  console.log('OK: revisión con API real de fixture, CSRF, aprobación, texto seguro y estado final.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

