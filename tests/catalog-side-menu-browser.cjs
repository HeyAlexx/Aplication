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
        assert.equal(await page.locator("#catalogSideMenu .catalog-controls .catalog-control-heading").count(), 4);
        assert.deepEqual(await page.locator("#catalogDensity option").allTextContents(), ["3", "5", "7"]);
        assert.equal(await page.locator("#catalogDensity").evaluate(element => getComputedStyle(element).textAlignLast), "center");
        assert.ok(await page.locator("#filter-seasons").isVisible());
        assert.equal(await page.locator(".catalog-more-filters summary").count(), 0);
        assert.ok(await page.locator("[data-quick-favorite]").evaluate(element => {
            const button = element.getBoundingClientRect();
            const group = element.parentElement.getBoundingClientRect();
            return Math.abs((button.left + button.right) / 2 - (group.left + group.right) / 2) < 1;
        }));
        assert.equal(await page.locator('[data-catalog-view="cards"]').innerText(), "▦");
        assert.equal(await page.locator('[data-catalog-view="list"]').innerText(), "☷");
        await page.locator('[data-quick-status="unseen"]').click();
        assert.equal(await page.locator('[data-quick-status="unseen"]').getAttribute("aria-pressed"), "true");
        assert.ok(await page.locator("#catalog-anime .anime-card").count() > 0);
        assert.ok(await page.locator("#catalog-anime .anime-card").evaluateAll(cards => cards.every(card => AltoidssStore.getViewingState(card.catalogItem) !== "completed")));
        await page.locator('[data-quick-status="unseen"]').click();
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
        assert.ok(await page.locator("#filter-seasons").isVisible());
        await page.locator('[data-category-view="movies"]').click();
        assert.ok(await page.locator("#filter-seasons-group").isHidden());
        await page.screenshot({ path: "outputs/catalog-side-menu-desktop.png" });
        assert.equal(await page.locator("#catalogSideMenu").evaluate(element => getComputedStyle(element).position), "fixed");
        assert.ok(await page.evaluate(() => document.querySelector("#catalogSideMenu").getBoundingClientRect().top >= document.querySelector(".topbar").getBoundingClientRect().bottom - 1));
        assert.ok(await page.locator("#catalogFilterToggle").isHidden());
        for (const width of [1512, 2545]) {
            await page.setViewportSize({ width, height: 1000 });
            assert.ok(await page.evaluate(() => {
                const content = document.querySelector(".content").getBoundingClientRect();
                const sidebar = document.querySelector("#catalogSideMenu").getBoundingClientRect();
                const leftGap = content.left - sidebar.right;
                const rightGap = document.documentElement.clientWidth - content.right;
                return leftGap >= 0 && Math.abs(leftGap - rightGap) <= 1;
            }), `Contenido centrado en el espacio libre a ${width}px`);
        }
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
