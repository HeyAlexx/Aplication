const test = require('node:test');
const assert = require('node:assert/strict');
const { preview, quarterAnchor, markdown } = require('../tools/historical-order-preview.cjs');
const { sort } = require('../js/content-order.js');
const cutoff = '2026-10-09T00:58:35-06:00';
const row = (number, year, quarter = 4) => ({ row: number, sourceCode: String(number),
    emissionYear: year, activeSeason: 'S01',
    raw: [String(number), 'Title', 'Emision', 'Serie', '12', '1', 'S01', 'Por Ver', String(year ?? ''), String(quarter)] });
const item = number => ({ id: String(number), sourceCode: String(number), sourceRow: number, title: String(number) });

test('historical estimation is a pure preview; real app dates are preserved', () => {
    const catalog = [item(2), { id: 'cowboy', title: 'Cowboy Bebop', importedAt: '2026-08-23T17:56:06-06:00' }];
    const mirror = [row(2, 2026)];
    const before = JSON.stringify({ catalog, mirror });
    const result = preview(catalog, mirror, cutoff);
    assert.equal(JSON.stringify({ catalog, mirror }), before);
    assert.equal(result.preserved, 1);
    assert.equal(result.estimated, 1);
    assert.equal(result.rows.find(r => r.id === 'cowboy').basis, 'existing-date-preserved');
});

test('isolated older title borrows the following row, explicitly marked for review', () => {
    const result = preview([item(2), item(3), item(4)], [row(2, 2025), row(3, 1998), row(4, 2026)], cutoff);
    const old = result.rows.find(r => r.id === '3');
    assert.equal(old.proposedAt, '2026-10-01T00:00:00-06:00');
    assert.equal(old.borrowedCode, '4');
    assert.equal(old.candidateNeedsReview, true);
    assert.ok(result.rows.find(r => r.id === '4').proposedRank < old.proposedRank);
});

test('no inferred next-row rule at edges or ambiguous old blocks', () => {
    const result = preview([item(2), item(3), item(4)], [row(2, 1998), row(3, 1998), row(4, 2026)], cutoff);
    assert.equal(result.nextRowCandidates, 0);
});

test('missing quarter remains unresolved; future anchors cannot exceed recovery', () => {
    const result = preview([item(2), item(3)], [row(2, 2027), row(3, 2026, '')], cutoff);
    assert.equal(result.capped, 1);
    assert.equal(result.unresolved, 1);
    assert.equal(result.rows.find(r => r.id === '2').proposedAt, cutoff);
    assert.equal(quarterAnchor(row(2, null)), null);
});

test('quarter is the literal J value; active season and legacy labels never supply it', () => {
    for (const [quarter, month] of [[1, '01'], [2, '04'], [3, '07'], [4, '10']]) {
        const source = row(2, 2025, quarter);
        source.activeSeason = 'S09';
        source.raw[6] = 'S09';
        source.emissionSeason = 'Wrong legacy label';
        assert.equal(quarterAnchor(source), `2025-${month}-01T00:00:00-06:00`);
        source.raw[6] = 'S01';
        source.activeSeason = 'S01';
        assert.equal(quarterAnchor(source), `2025-${month}-01T00:00:00-06:00`);
    }
    const missing = row(2, 2026, '');
    missing.emissionSeason = 'Fall';
    assert.equal(quarterAnchor(missing), null);
    assert.equal(quarterAnchor(row(2, 2026, 5)), null);
});

test('duplicate source references or catalog IDs fail closed', () => {
    assert.throws(() => preview([item(2)], [row(2, 2026), row(2, 2025)], cutoff));
    assert.throws(() => preview([item(2), item(2)], [row(2, 2026)], cutoff));
});

test('future timeline: app 01:50 < Sheet batch 01:51; frozen rows, then later app', () => {
    const app = { id: 'app', createdAt: '2026-10-09T01:50:00-06:00' };
    const sheets = [2, 3].map(n => ({ ...item(n), incorporatedAt: '2026-10-09T01:51:00-06:00', sheetImportBatchId: 'same', sheetImportRow: n }));
    assert.deepEqual(sort([app, ...sheets]).map(r => r.id), ['3', '2', 'app']);
    // Reordering the Sheet must not rewrite the original internal import order.
    sheets[0].sourceRow = 100;
    assert.deepEqual(sort([app, ...sheets]).map(r => r.id), ['3', '2', 'app']);
    const later = { id: 'later', createdAt: '2026-10-09T01:52:00-06:00' };
    assert.deepEqual(sort([app, ...sheets, later]).map(r => r.id), ['later', '3', '2', 'app']);
    assert.deepEqual(sort([app, ...sheets, later], 'oldest').map(r => r.id), ['app', '2', '3', 'later']);
});

test('rebase all Sheet history ignores prior dates and preserves exact descending rows', () => {
    const catalog = [2, 3, 4, 5, 6].map(item);
    catalog[0].createdAt = '2026-10-08T22:00:00-06:00';
    catalog[2].incorporatedAt = '2026-10-09T00:30:00-06:00';
    catalog[2].sheetImportBatchId = 'old';
    catalog[2].sheetImportRow = 200;
    catalog.push({ id: 'app', importedAt: '2026-08-23T17:56:06-06:00' });
    const mirror = [row(2, 2022), row(3, 1998), row(4, 2024), row(5, 2010), row(6, 2026)];
    const before = JSON.stringify({ catalog, mirror });
    const result = preview(catalog, mirror, cutoff, { rebaseSheetHistory: true });
    assert.deepEqual(result.rows.filter(r => r.row !== null).map(r => r.code), ['6', '5', '4', '3', '2']);
    assert.equal(result.sheetOrderMatches, true);
    assert.equal(result.existingSheetDatesIgnored, 2);
    assert.equal(result.estimated, 5);
    assert.equal(result.preserved, 1);
    assert.equal(result.rows.find(r => r.id === 'app').existingAt, result.rows.find(r => r.id === 'app').proposedAt);
    assert.equal(JSON.stringify({ catalog, mirror }), before);
});

test('rebase handles old blocks and missing quarters without losing row order', () => {
    const result = preview([2, 3, 4, 5].map(item), [row(2, 2025), row(3, 1998), row(4, 1998), row(5, 2026, '')],
        cutoff, { rebaseSheetHistory: true });
    assert.equal(result.sheetOrderMatches, true);
    assert.equal(result.unresolved, 0);
    assert.ok(result.rowOrderAdjustments > 0);
    assert.throws(() => preview([item(2)], [row(2, 2026, '')], cutoff, { rebaseSheetHistory: true }));
    assert.throws(() => preview([], [row(2, 2026)], cutoff, { rebaseSheetHistory: true }));
});

test('report distinguishes catalog display rank from unchanged Sheet row', () => {
    const result = preview([item(522)], [row(522, 2026)], cutoff, { rebaseSheetHistory: true });
    const text = markdown(result);
    assert.ok(text.includes('Posición propuesta en catálogo'));
    assert.ok(text.includes('Fila de Sheets (sin cambios)'));
    assert.ok(text.includes('| 1 | 1 | 522 |'));
    assert.ok(text.includes('NO es el número de fila de Sheets'));
});
