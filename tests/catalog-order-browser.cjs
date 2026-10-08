// Requiere el servidor de desarrollo activo y Playwright disponible en NODE_PATH.
const assert = require("node:assert/strict");
const { chromium } = require("playwright");
const { sort } = require("../js/content-order.js");

(async () => {
    const browser = await chromium.launch({ channel: "msedge", headless: true });
    try {
        const page = await browser.newPage();
        const errors = [];
        page.on("pageerror", error => errors.push(error.message));
        const base = process.env.ALTOIDSS_TEST_URL || "http://127.0.0.1:8092";
        const ids = () => page.locator(".catalog-panel.is-active .anime-card").evaluateAll(cards => cards.map(card => card.dataset.contentId));
        await page.goto(`${base}/Html/catalogo.html?category=anime`, { waitUntil: "networkidle" });
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card[data-content-id]").length === 35);
        const items = await page.evaluate(() => AltoidssStore.read().filter(item => item.type === "anime"));
        assert.equal(await page.locator("#catalogDateOrder").inputValue(), "newest");
        assert.deepEqual(await ids(), sort(items).slice(0, 35).map(item => item.id));
        await page.locator('#catalog-anime [aria-label="Ir a la página 2"]').click();
        assert.deepEqual(await ids(), sort(items).slice(35, 70).map(item => item.id));
        await page.selectOption("#catalogDateOrder", "oldest");
        assert.deepEqual(await ids(), sort(items, "oldest").slice(0, 35).map(item => item.id));
        assert.equal(new URL(page.url()).searchParams.get("page"), null);
        assert.equal(new URL(page.url()).searchParams.get("order"), "oldest");
        await page.reload({ waitUntil: "networkidle" });
        assert.equal(await page.locator("#catalogDateOrder").inputValue(), "oldest");
        assert.deepEqual(await ids(), sort(items, "oldest").slice(0, 35).map(item => item.id));
        await page.locator("#sidebar-search").fill("Princess");
        await page.locator("#sidebar-search").press("Enter");
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card").length < 35);
        const searched = await ids();
        assert.ok(searched.length > 0);
        const matched = items.filter(item => searched.includes(item.id));
        assert.deepEqual(searched, sort(matched, "oldest").map(item => item.id));
        await page.selectOption("#catalogDateOrder", "newest");
        assert.deepEqual(await ids(), sort(matched).map(item => item.id));
        assert.equal(new URL(page.url()).searchParams.get("query"), "Princess");
        await page.locator("#clearCatalogFilters").click();
        await page.waitForFunction(() => document.querySelectorAll("#catalog-anime .anime-card").length === 35);
        await page.locator('[data-category-view="movies"]').click();
        const movies = await page.evaluate(() => AltoidssStore.read().filter(item => item.type === "movies"));
        assert.deepEqual(await ids(), sort(movies).slice(0, 35).map(item => item.id));
        await page.setViewportSize({ width: 360, height: 800 });
        assert.ok(await page.locator("#catalogDateOrder").isVisible());
        assert.ok(await page.locator(".catalog-order-tools").evaluate(element => element.scrollWidth <= element.clientWidth));
        // La navegación superior puede desbordar sin Bootstrap externo; comprobar
        // que el nuevo control no aumenta ese desbordamiento previo.
        assert.ok(await page.evaluate(() => {
            const width = document.documentElement.scrollWidth;
            const tools = document.querySelector(".catalog-order-tools");
            tools.style.display = "none";
            const previousWidth = document.documentElement.scrollWidth;
            tools.style.display = "";
            return width <= previousWidth;
        }));
        assert.deepEqual(errors, []);
        console.log("OK: catálogo real, ambos órdenes, paginación, recarga, búsqueda, categorías y móvil; sin errores de JavaScript.");
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
