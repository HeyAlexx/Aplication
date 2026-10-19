// Read-only server verification. Every browser mutation is blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const { sort } = require('../js/content-order.js');
const root = path.resolve(__dirname, '..');
const directory = require('./catalog-fixture-path.cjs');
const local = JSON.parse(fs.readFileSync(path.join(directory, 'anime.json')));
const mirror = JSON.parse(fs.readFileSync(path.join(directory, 'anime-hoja.json')));
const mirrorCodes = new Set(mirror.map(row => String(row.sourceCode)));
const isLinked = item => mirrorCodes.has(String(item.sourceCode));
const base = process.env.ALTOIDSS_TEST_URL || 'http://127.0.0.1:8092';
const output = path.join(root, 'outputs', 'qa-historical-order');
fs.mkdirSync(output, { recursive: true });
// PHP decodes associative JSON as arrays and serializes an empty object as [].
// Accept that representation ONLY for an empty originalDates audit map.
const canonical = records => JSON.stringify(records.map(item => {
    const copy = structuredClone(item);
    if (copy.historicalOrderInitialization && Array.isArray(copy.historicalOrderInitialization.originalDates)
        && copy.historicalOrderInitialization.originalDates.length === 0) copy.historicalOrderInitialization.originalDates = {};
    return copy;
}));

(async () => {
    const response = await fetch(`${base}/api/index.php?route=/content/anime`);
    assert.equal(response.status, 200);
    const api = (await response.json()).data;
    assert.ok(canonical(api) === canonical(local.filter(item => item.status !== 'Oculto')), 'API must match the central catalog (empty audit maps normalized).');
    const fallback = await fetch(`${base}/data/anime.json`);
    assert.equal(fallback.status, 200);
    assert.ok(canonical(await fallback.json()) === canonical(local), 'Public JSON must match the central catalog.');
    const expected = [...mirror].sort((a, b) => b.row - a.row).map(row => [String(row.sourceCode), row.row]);
    assert.deepEqual(sort(api).filter(isLinked).map(item => [String(item.sourceCode), item.sourceRow]), expected);
    assert.deepEqual(sort(api, 'oldest').filter(isLinked).map(item => [String(item.sourceCode), item.sourceRow]), [...expected].reverse());
    assert.equal(api.filter(isLinked).filter(item => item.historicalOrderInitialization).length, mirror.length);

    const report = { base, apiCount: api.length, linkedCount: mirror.length, exactAllRowsBothDirections: true,
        publicJsonMatches: true, firstCodes: sort(api).slice(0, 5).map(item => item.sourceCode),
        cases: [], errors: [], mutations: [] };
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        for (const width of [360, 1280]) {
            const context = await browser.newContext({ viewport: { width, height: 900 }, isMobile: width === 360, hasTouch: width === 360 });
            const page = await context.newPage();
            page.on('pageerror', error => report.errors.push(error.message));
            await page.route('**/api/index.php**', route => {
                if (route.request().method() !== 'GET') {
                    report.mutations.push(route.request().method());
                    return route.fulfill({ status: 403, body: '{}' });
                }
                if (route.request().url().includes('/discover')) return route.fulfill({ status: 503, body: '{}' });
                return route.continue();
            });
            await page.goto(`${base}/Html/catalogo.html?category=anime&order=newest`, { waitUntil: 'networkidle' });
            await page.waitForFunction(() => document.querySelectorAll('#catalog-anime .anime-card[data-content-id]').length === 35);
            const ids = () => page.locator('#catalog-anime .anime-card').evaluateAll(cards => cards.map(card => card.dataset.contentId));
            const loaded = await page.evaluate(() => AltoidssStore.read().filter(item => item.type === 'anime'));
            assert.deepEqual(loaded.map(item => item.id).sort(), api.map(item => item.id).sort());
            assert.deepEqual(await ids(), sort(api).slice(0, 35).map(item => item.id));
            await page.screenshot({ path: path.join(output, `catalog-${width}.png`), fullPage: false });
            await page.goto(`${base}/Html/catalogo.html?category=anime&order=oldest`, { waitUntil: 'networkidle' });
            await page.waitForFunction(() => document.querySelectorAll('#catalog-anime .anime-card[data-content-id]').length === 35);
            assert.deepEqual(await ids(), sort(api, 'oldest').slice(0, 35).map(item => item.id));
            report.cases.push({ page: 'catalog', width, newestAndOldest: 'passed', loaded: loaded.length });
            await context.close();
        }

        // Only the admin session/profile are simulated. Catalog GETs remain real.
        const context = await browser.newContext({ viewport: { width: 412, height: 915 }, isMobile: true, hasTouch: true });
        const page = await context.newPage();
        page.on('pageerror', error => report.errors.push(error.message));
        const session = { id: 'qa-admin', name: 'QA', role: 'admin', profileMode: 'admin', isAuthenticated: true, email: 'qa@example.invalid' };
        const profile = { ...session, displayName: 'QA', seenIds: [], viewingStates: {}, favoriteIds: [], favoriteItems: {}, settings: { cardsPerRow: 5, preferredView: 'cards' } };
        const mocks = { '/auth/session': session, '/profile': profile, '/reviews/anime': [],
            '/dashboard': { profile, totalContent: 809, seenTotal: 0, favoriteTotal: 0, moviesSeen: 0, seriesSeen: 0, animeSeen: 0, topGenre: 'Sin datos', lastVisit: 'Hoy', watchTimeMinutes: 0 } };
        await page.route('**/api/index.php**', route => {
            if (route.request().method() !== 'GET') {
                report.mutations.push(route.request().method());
                return route.fulfill({ status: 403, body: '{}' });
            }
            const endpoint = new URL(route.request().url()).searchParams.get('route');
            if (endpoint in mocks) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, data: mocks[endpoint], meta: {} }) });
            return route.continue();
        });
        await page.goto(`${base}/Html/dashboard.html?tab=table`, { waitUntil: 'networkidle' });
        await page.waitForSelector('body.is-admin-profile');
        const contentTab = page.locator('[data-dashboard-view="content"]');
        if (await contentTab.count()) await contentTab.click();
        await page.waitForFunction(() => document.querySelectorAll('#contentTableBody tr [data-edit-id]').length > 0);
        assert.ok((await page.locator('.incorporation-date').allTextContents()).some(text => text.startsWith('≈ ')));
        const title = await page.locator('.incorporation-date[title*="Referencia estimada"]').first().getAttribute('title');
        assert.ok(title.includes('No es una fecha de alta real'));
        assert.ok((await page.locator('#dashboardDateOrderNote').textContent()).includes('781 históricos'));
        await page.locator('#contentTableBody tr').first().scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(output, 'admin-412.png'), fullPage: false });
        report.cases.push({ page: 'admin', width: 412, simulatedAdminSession: true, realCatalogGets: true, estimatedDatesLabel: 'passed' });
        await context.close();
        assert.deepEqual(report.errors, []);
        assert.deepEqual(report.mutations, []);
        fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
        console.log(JSON.stringify(report, null, 2));
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
