const assert = require('node:assert/strict');
const {chromium} = require('playwright');
(async () => {
    const browser = await chromium.launch({channel:'msedge',headless:true});
    try {
        const page = await browser.newPage();
        const errors=[];
        page.on('pageerror', e=>errors.push(e.message));
        const base = process.env.ALTOIDSS_TEST_URL || 'http://127.0.0.1:8092';
        await page.goto(`${base}/Html/catalogo.html?category=anime`,{waitUntil:'domcontentloaded'});
        await page.waitForFunction(()=>document.querySelectorAll('#catalog-anime .anime-card').length===35);
        for(const width of [320,360,412,600,768]) {
            await page.setViewportSize({width,height:1000});
            await page.locator('#catalogTouchOrderToggle').click();
            assert.ok(await page.locator('#catalogTouchOrderOptions button').evaluateAll(buttons=>buttons.every(b=>b.getBoundingClientRect().height>=48)));
            assert.ok(await page.locator('#catalogTouchOrderOptions').evaluate(e=>{const b=e.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth;}));
            await page.locator('[data-touch-order="oldest"]').click();
            assert.equal(await page.locator('#catalogDateOrder').inputValue(),'oldest');
            assert.equal(new URL(page.url()).searchParams.get('order'),'oldest');
            assert.equal(await page.locator('#catalogTouchOrderToggle').innerText(),'Más antiguos primero');
            await page.locator('#catalogTouchOrderToggle').click();
            await page.keyboard.press('Escape');
            assert.ok(await page.locator('#catalogTouchOrderOptions').isHidden());
            await page.locator('#catalogTouchOrderToggle').click();
            await page.locator('[data-touch-order="newest"]').click();
            assert.equal(await page.locator('#catalogDateOrder').inputValue(),'newest');
        }
        await page.setViewportSize({width:412,height:1000});
        await page.locator('#catalogTouchOrderToggle').click();
        await page.screenshot({path:'outputs/catalog-touch-order-412.png'});
        await page.keyboard.press('Escape');
        await page.setViewportSize({width:1512,height:1000});
        assert.ok(await page.locator('#catalogDateOrder').isVisible());
        assert.ok(await page.locator('#catalogTouchOrderToggle').isHidden());
        assert.deepEqual(errors,[]);
        console.log('OK: opciones táctiles >=48px a 320/360/412/600/768, orden/URL correctos, Escape y selector de escritorio intacto.');
    } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
