const assert = require("node:assert/strict");
const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ channel: "msedge", headless: true });
    try {
        const page = await browser.newPage();
        const errors = [];
        page.on("pageerror", error => errors.push(error.message));
        await page.goto(`${process.env.ALTOIDSS_TEST_URL || "http://127.0.0.1:8092"}/Html/catalogo.html?category=anime`, { waitUntil: "networkidle" });
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card[data-content-id]").length === 35);
        for (const width of [320, 360, 412, 600, 768]) {
            await page.setViewportSize({ width, height: 924 });
            const dimensions = await page.locator("#catalog-anime .anime-card").evaluateAll(cards => cards.slice(0, 3).map(card => {
                const rect = card.getBoundingClientRect();
                const poster = card.querySelector(".poster").getBoundingClientRect();
                const title = card.querySelector("h2").getBoundingClientRect();
                return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, ratio: poster.width / poster.height, titleY: title.y, posterBottom: poster.bottom };
            }));
            assert.equal(dimensions[0].y, dimensions[1].y, `Dos tarjetas en la primera fila a ${width}px`);
            assert.ok(dimensions[2].y > dimensions[0].y);
            assert.ok(dimensions[0].width < width / 2);
            assert.ok(Math.abs(dimensions[0].ratio - 2 / 3) < 0.01);
            assert.ok(dimensions[0].titleY >= dimensions[0].posterBottom);
            if (width === 412) assert.ok(dimensions[0].height < 340);
            assert.ok(await page.locator("#filter-format").isVisible());
            assert.ok(await page.locator("#catalogDensity").isHidden());
            await page.locator("#catalogFilterToggle").click();
            assert.ok(await page.locator("#filter-format").isVisible());
            assert.ok(await page.locator("#catalogSideMenu").isVisible());
            await page.locator("#closeCatalogSideMenu").click();
            await page.locator("#catalog-anime").scrollIntoViewIfNeeded();
            if (width === 412) await page.screenshot({ path: "outputs/catalog-mobile-412.png" });
        }
        await page.setViewportSize({ width: 1512, height: 1000 });
        assert.ok(await page.locator("#filter-format").isVisible());
        assert.ok(await page.locator("#catalogFilterToggle").isVisible());
        await page.locator("#catalogFilterToggle").click();
        assert.ok(await page.locator("#catalogDensity").isVisible());
        assert.deepEqual(errors, []);
        console.log("OK: dos columnas a 320/360/412/600/768px, proporciones, títulos, filtros plegables y controles de escritorio.");
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
