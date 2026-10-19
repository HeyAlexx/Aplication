const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
const browser=await chromium.launch({channel:'msedge',headless:true});
try {
const page=await browser.newPage();
await page.goto(`${process.env.ALTOIDSS_TEST_URL||'http://127.0.0.1:8092'}/Html/catalogo.html?category=anime`,{waitUntil:'networkidle'});
for(const width of [320,412,480,768,820,1024]) {
await page.setViewportSize({width,height:900});
const measurement=await page.locator('.nav-toggle').evaluate(button=>{
const b=button.getBoundingClientRect(),i=button.querySelector('.navbar-toggler-icon').getBoundingClientRect();
return {dx:(i.left+i.right-b.left-b.right)/2,dy:(i.top+i.bottom-b.top-b.bottom)/2,inside:i.left>=b.left&&i.right<=b.right&&i.top>=b.top&&i.bottom<=b.bottom};
});
assert.ok(Math.abs(measurement.dx)<1&&Math.abs(measurement.dy)<1&&measurement.inside,JSON.stringify({width,...measurement}));
await page.locator('.nav-toggle').click();
await page.waitForFunction(()=>document.querySelector('#site-navigation').classList.contains('show'));
await page.waitForTimeout(400);
await page.locator('.nav-toggle').click();
await page.waitForTimeout(400);
}
await page.setViewportSize({width:480,height:900});
await page.screenshot({path:'outputs/menu-icon-centered-480.png'});
await page.setViewportSize({width:1512,height:900});
assert.ok(await page.locator('.nav-toggle').isHidden());
console.log('OK: menú centrado horizontal y vertical a 320/412/480/768/820/1024; abre y cierra; oculto en escritorio.');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
