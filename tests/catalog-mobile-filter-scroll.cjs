const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base=process.env.ALTOIDSS_TEST_URL || 'http://127.0.0.1:8092';
(async()=>{
    const browser=await chromium.launch({channel:'msedge',headless:true});
    try {
        for(const height of [840,440]) {
            const context=await browser.newContext({viewport:{width:412,height},isMobile:true,hasTouch:true});
            const page=await context.newPage();
            await page.goto(`${base}/Html/catalogo.html?category=all`,{waitUntil:'domcontentloaded'});
            await page.waitForFunction(()=>document.querySelectorAll('.catalog-panel.is-active .anime-card').length>0);
            await page.locator('#catalogFilterToggle').tap();
            await page.waitForTimeout(700);
            const diagnostic=await page.locator('#catalogSideMenu').evaluate(e=>({
                overflowY:getComputedStyle(e).overflowY,overscrollY:getComputedStyle(e).overscrollBehaviorY,
                autoFocused:document.activeElement.id==='sidebar-search',height:e.clientHeight,scrollHeight:e.scrollHeight,
            }));
            console.log(JSON.stringify({height,...diagnostic}));
            assert.equal(diagnostic.autoFocused,false,'Abrir opciones no debe enfocar el buscador ni abrir el teclado.');
            assert.equal(diagnostic.overflowY,'visible');
            assert.equal(diagnostic.overscrollY,'auto');
            const before=await page.evaluate(()=>scrollY);
            const session=await context.newCDPSession(page);
            const y=Math.min(height-40,380);
            await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:6,y}]});
            for(let step=1;step<=8;step++) {
                await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:6,y:y-step*22}]});
                await page.waitForTimeout(25);
            }
            await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
            await page.waitForTimeout(350);
            assert.ok(await page.evaluate(()=>scrollY)>before+20,'Deslizar dentro del panel debe desplazar la página.');
            await page.locator('#filter-seasons').scrollIntoViewIfNeeded();
            await page.locator('#filter-seasons').selectOption('1');
            assert.equal(await page.locator('#filter-seasons').inputValue(),'1');
            await page.locator('#sidebar-search').tap();
            assert.equal(await page.evaluate(()=>document.activeElement.id),'sidebar-search');
            await page.locator('#sidebar-search').fill('Princess');
            await page.locator('#closeCatalogSideMenu').tap();
            assert.equal(await page.locator('#catalogFilterToggle').getAttribute('aria-expanded'),'false');
            await context.close();
        }
        console.log('OK: móvil táctil, swipe dentro de filtros, altura normal/reducida, opciones clicables y teclado solo al tocar buscador.');
    } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
