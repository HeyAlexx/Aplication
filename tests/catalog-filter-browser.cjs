const assert = require("node:assert/strict");
const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ channel: "msedge", headless: true });
    try {
        const page = await browser.newPage({ viewport: { width: 1512, height: 1000 } });
        const errors = [];
        page.on("pageerror", error => errors.push(error.message));
        await page.goto(`${process.env.ALTOIDSS_TEST_URL || "http://127.0.0.1:8092"}/Html/catalogo.html?category=anime`, { waitUntil: "networkidle" });
        await page.waitForFunction(() => document.querySelectorAll("#catalogAlphabet button").length === 28);
        assert.equal(await page.locator(".sidebar").count(), 0);
        assert.equal(await page.locator(".section-heading h1").innerText(), "Catálogo de anime");
        await page.locator('[data-catalog-initial="P"]').click();
        assert.equal(await page.locator('[data-catalog-initial="P"]').getAttribute("aria-pressed"), "true");
        assert.ok(await page.locator("#catalog-anime .anime-card").count() > 0);
        assert.ok(await page.locator("#catalog-anime .anime-card").evaluateAll(cards => cards.every(card => card.catalogItem.title.toUpperCase().startsWith("P"))));
        await page.selectOption("#filter-year", "2022");
        assert.ok(await page.locator("#catalog-anime .anime-card").count() > 0);
        assert.ok(await page.locator("#catalog-anime .anime-card").evaluateAll(cards => cards.every(card => Number(card.catalogItem.emissionYear || card.catalogItem.year) === 2022)));
        await page.selectOption("#catalogDateOrder", "oldest");
        assert.equal(await page.locator("#filter-year").inputValue(), "2022");
        await page.locator("#clearCatalogFilters").click();
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card").length === 35);
        assert.equal(await page.locator("#filter-year").inputValue(), "");
        assert.equal(await page.locator('[data-catalog-initial=""]').getAttribute("aria-pressed"), "true");
        await page.locator(".catalog-more-filters summary").click();
        assert.ok(await page.locator("#filter-seasons").isVisible());
        await page.selectOption("#filter-seasons", "1");
        assert.ok(await page.locator("#catalog-anime .anime-card").evaluateAll(cards => cards.every(card => Number(card.catalogItem.seasonsCount) === 1)));
        await page.locator("#clearCatalogFilters").click();
        await page.locator('[data-category-view="movies"]').click();
        assert.ok(await page.locator("#filter-seasons-group").isHidden());
        await page.locator('[data-category-view="anime"]').click();
        await page.locator(".catalog-more-filters summary").click();
        await page.screenshot({ path: "outputs/catalog-filters-desktop.png", fullPage: false });
        await page.setViewportSize({ width: 360, height: 900 });
        for (const selector of [".catalog-alphabet", ".catalog-primary-filters", ".catalog-search-tools", ".catalog-order-tools"]) {
            assert.ok(await page.locator(selector).evaluate(element => element.scrollWidth <= element.clientWidth + 1), `${selector} debe caber en móvil`);
        }
        await page.locator('[data-catalog-initial="P"]').focus();
        await page.keyboard.press("Enter");
        assert.equal(await page.locator('[data-catalog-initial="P"]').getAttribute("aria-pressed"), "true");
        await page.screenshot({ path: "outputs/catalog-filters-mobile.png", fullPage: false });
        assert.deepEqual(errors, []);
        console.log("OK: iniciales, año, limpieza, temporadas, categorías, teclado y filtros móviles; sin errores de JavaScript.");
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
