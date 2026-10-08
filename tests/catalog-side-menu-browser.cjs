const assert = require("node:assert/strict");
const { chromium } = require("playwright");
(async () => {
    const browser = await chromium.launch({ channel: "msedge", headless: true });
    try {
        const page = await browser.newPage({ viewport: { width: 1512, height: 1000 } });
        const errors = [];
        page.on("pageerror", error => errors.push(error.message));
        await page.goto(`${process.env.ALTOIDSS_TEST_URL || "http://127.0.0.1:8092"}/Html/catalogo.html?category=anime`, { waitUntil: "networkidle" });
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card[data-content-id]").length === 35);
        assert.ok(await page.locator("#catalogSideMenu").isVisible());
        assert.ok(await page.locator("#filter-format").isVisible());
        for (const selector of [".catalog-search-tools", ".catalog-more-filters", ".catalog-controls"]) {
            assert.equal(await page.locator(`#catalogSideMenu ${selector}`).count(), 1);
        }
        assert.ok(await page.locator("#catalogSideMenu").isVisible());
        await page.locator("#sidebar-search").fill("Princess");
        await page.locator('#catalogSideMenu button[type="submit"]').click();
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card").length < 35);
        assert.ok(await page.locator("#catalog-anime .anime-card").count() > 0);
        assert.equal(new URL(page.url()).searchParams.get("query"), "Princess");
        await page.locator("#clearCatalogFilters").click();
        await page.locator(".catalog-more-filters summary").click();
        assert.ok(await page.locator("#filter-seasons").isVisible());
        await page.locator('[data-category-view="movies"]').click();
        assert.ok(await page.locator("#filter-seasons-group").isHidden());
        await page.screenshot({ path: "outputs/catalog-side-menu-desktop.png" });
        assert.equal(await page.locator("#catalogSideMenu").evaluate(element => getComputedStyle(element).position), "fixed");
        assert.ok(await page.evaluate(() => document.querySelector("#catalogSideMenu").getBoundingClientRect().top >= document.querySelector(".topbar").getBoundingClientRect().bottom - 1));
        assert.ok(await page.locator("#catalogFilterToggle").isHidden());
        await page.setViewportSize({ width: 412, height: 924 });
        await page.locator("#catalogFilterToggle").click();
        const box = await page.locator("#catalogSideMenu").boundingBox();
        assert.ok(box.x >= 0 && box.width <= 412);
        assert.ok(await page.locator("#sidebar-search").isVisible());
        await page.screenshot({ path: "outputs/catalog-side-menu-mobile.png" });
        await page.locator("#closeCatalogSideMenu").click();
        assert.ok(await page.locator("#catalogSideMenu").isHidden());
        assert.ok(await page.locator("#filter-format").isVisible());
        assert.deepEqual(errors, []);
        console.log("OK: sidebar fijo izquierdo, búsqueda, categorías, filtros avanzados y panel adaptable en móvil.");
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
