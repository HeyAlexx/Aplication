const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
const base=process.env.ALTOIDSS_TEST_URL;
const css=fs.readFileSync('C:/Users/Alvar/Projects/Altoids/work/cloud-staging-pilot/web/vendor/bootstrap.min.css');
const js=fs.readFileSync('C:/Users/Alvar/Projects/Altoids/work/cloud-staging-pilot/web/vendor/bootstrap.bundle.min.js');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:360,height:1000}});
  const login=await context.request.post(base+'/api/index.php?route=/auth/login',
    {data:{email:'admin@example.invalid',password:process.env.ALTOIDSS_FIXTURE_PASSWORD}});
  assert.equal(login.status(),200);
  await context.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.origin===base)return route.continue();
   if(url.pathname==='/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css')return route.fulfill({contentType:'text/css',body:css});
   if(url.pathname==='/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js')return route.fulfill({contentType:'text/javascript',body:js});
   return route.abort();
  });
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

