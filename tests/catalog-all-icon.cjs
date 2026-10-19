const assert = require('node:assert/strict');
const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({channel: 'msedge', headless: true});
    try {
        const page = await browser.newPage();
        const errors = [];
        page.on('pageerror', e => errors.push(e.message));
        await page.goto(`${process.env.ALTOIDSS_TEST_URL || 'http://127.0.0.1:8092'}/Html/catalogo.html?category=anime`, {waitUntil:'domcontentloaded'});
        await page.waitForFunction(() => document.querySelectorAll('#catalog-anime .anime-card').length === 35);
        const all = page.getByRole('button', {name:'Todas las iniciales', exact:true});
        assert.equal(await all.locator('svg[aria-hidden="true"]').count(), 1);
        assert.equal(await all.innerText(), '');
        for (const width of [320,412,768,820,1024,1512,1920]) {
            await page.setViewportSize({width,height:1000});
            assert.ok(await all.evaluate(e => {
                const b=e.getBoundingClientRect(), s=e.querySelector('svg').getBoundingClientRect();
                return e.scrollWidth<=e.clientWidth && s.left>=b.left && s.right<=b.right && Math.abs((s.left+s.right-b.left-b.right)/2)<1;
            }), `Icono centrado sin desbordar a ${width}px`);
            await page.locator('[data-catalog-initial="P"]').click();
            assert.equal(await all.getAttribute('aria-pressed'), 'false');
            await all.locator('svg').click();
            assert.equal(await all.getAttribute('aria-pressed'), 'true');
            assert.equal(await page.locator('#catalog-anime .anime-card').count(), 35);
            await page.locator('[data-catalog-initial="P"]').click();
            await all.focus();
            await page.keyboard.press('Enter');
            assert.equal(await all.getAttribute('aria-pressed'), 'true');
        }
        await page.setViewportSize({width:820,height:1180});
        await page.screenshot({path:'outputs/catalog-infinity-820.png'});
        assert.deepEqual(errors, []);
        console.log('OK: SVG centrado a 320/412/768/820/1024/1512/1920; clic en icono y teclado restauran todas las iniciales.');
    } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
