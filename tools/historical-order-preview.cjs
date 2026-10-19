// Read-only proposal. No apply mode, network access, or writes to catalog/Sheets.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { sort, timestamp } = require('../js/content-order.js');

const QUARTER_MONTHS = { 1: '01', 2: '04', 3: '07', 4: '10' };
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function quarterAnchor(row) {
    // Literal Sheet columns I (year) and J (quarter). G / activeSeason is
    // unrelated, and emissionSeason is a legacy normalized name, not our input.
    const year = Number(row.raw?.[8]);
    const quarter = Number(row.raw?.[9]);
    const month = QUARTER_MONTHS[quarter];
    if (!Number.isInteger(year) || year < 1900 || year > 2100 || !month) return null;
    // Computational anchor only: not a claim of an actual addition day/time.
    return `${year}-${month}-01T00:00:00-06:00`;
}

function preview(catalog, mirror, cutoff, { rebaseSheetHistory = false } = {}) {
    if (!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(cutoff) || !Number.isFinite(Date.parse(cutoff))) {
        throw Error('cutoff debe ser ISO con zona horaria: límite documentado, no fecha histórica real.');
    }
    const rows = [...mirror].sort((a, b) => a.row - b.row);
    const byCode = new Map();
    const byRow = new Set();
    for (const row of rows) {
        if (!row.sourceCode || !Number.isInteger(row.row) || row.row < 2 || byCode.has(String(row.sourceCode)) || byRow.has(row.row)) {
            throw Error('Espejo inválido: códigos/filas duplicados o referencia ausente.');
        }
        byCode.set(String(row.sourceCode), row);
        byRow.add(row.row);
    }
    const suggestions = new Map();
    rows.forEach((row, index) => {
        const anchor = quarterAnchor(row);
        const previous = quarterAnchor(rows[index - 1] || {});
        const next = quarterAnchor(rows[index + 1] || {});
        // No arbitrary year threshold. Isolated dip relative to BOTH neighbors.
        // These are review candidates, not evidence of a historical import.
        const dip = anchor && previous && next && Date.parse(anchor) < Date.parse(previous) && Date.parse(anchor) < Date.parse(next);
        const chosen = dip ? next : anchor;
        const capped = chosen && Date.parse(chosen) > Date.parse(cutoff);
        suggestions.set(String(row.sourceCode), {
            anchor, proposedAt: capped ? cutoff : chosen,
            basis: !chosen ? 'unresolved' : dip ? 'historical-next-row-estimate' : 'historical-quarter-estimate',
            borrowedCode: dip ? String(rows[index + 1].sourceCode) : null,
            candidateNeedsReview: Boolean(dip), capped: Boolean(capped),
        });
    });
    if (rebaseSheetHistory) {
        // The Sheet sequence is authoritative for initialization. Quarter dates
        // must be nondecreasing down the Sheet, not override the row chronology.
        // First retain the explicit isolated-old-title -> next-row proposal,
        // then raise any backwards reference to the preceding effective date.
        let previous = null;
        rows.forEach((row, index) => {
            const estimate = suggestions.get(String(row.sourceCode));
            if (!estimate.proposedAt) {
                const next = rows.slice(index + 1).find(r => suggestions.get(String(r.sourceCode)).proposedAt);
                const reference = previous || (next && { code: String(next.sourceCode),
                    date: suggestions.get(String(next.sourceCode)).proposedAt });
                if (!reference) throw Error('No hay referencia año/quarter válida para inicializar el histórico.');
                estimate.proposedAt = reference.date;
                estimate.borrowedCode = reference.code;
                estimate.basis = 'historical-sheet-order-estimate';
            }
            if (previous && Date.parse(estimate.proposedAt) < Date.parse(previous.date)) {
                estimate.proposedAt = previous.date;
                estimate.borrowedCode = previous.code;
                estimate.basis = 'historical-sheet-order-estimate';
            }
            previous = { code: String(row.sourceCode), date: estimate.proposedAt };
        });
    }
    const seen = new Set();
    const details = [];
    const proposed = catalog.map(item => {
        if (!item.id || seen.has(item.id)) throw Error('Catálogo inválido: ID duplicado o ausente.');
        seen.add(item.id);
        const row = byCode.get(String(item.sourceCode));
        const existing = timestamp(item);
        const estimate = row && suggestions.get(String(row.sourceCode));
        const keep = existing !== null && (!row || !rebaseSheetHistory);
        const applied = !keep && estimate?.proposedAt;
        details.push({ id: item.id, code: item.sourceCode || null, title: item.title,
            row: row?.row || null, existingAt: existing !== null ? new Date(existing).toISOString() : null,
            quarter: row ? Number(row.raw?.[9]) || null : null,
            quarterAnchor: estimate?.anchor || null,
            proposedAt: keep ? new Date(existing).toISOString() : estimate?.proposedAt || null,
            basis: keep ? 'existing-date-preserved' : estimate?.basis || 'local-unresolved',
            borrowedCode: applied ? estimate.borrowedCode : null,
            candidateNeedsReview: Boolean(applied && estimate.candidateNeedsReview),
            capped: Boolean(applied && estimate.capped),
            existingSheetDateIgnored: Boolean(row && rebaseSheetHistory && existing !== null),
        });
        if (!applied) return { ...item };
        return { ...item, incorporatedAt: estimate.proposedAt,
            sheetImportBatchId: 'historical-' + digest(estimate.proposedAt).slice(0, 24),
            sheetImportRow: row.row, incorporationDateBasis: estimate.basis };
    });
    const oldRanks = new Map(sort(catalog).map((item, index) => [item.id, index + 1]));
    const newRanks = new Map(sort(proposed).map((item, index) => [item.id, index + 1]));
    details.forEach(detail => {
        detail.currentRank = oldRanks.get(detail.id);
        detail.proposedRank = newRanks.get(detail.id);
    });
    details.sort((a, b) => a.proposedRank - b.proposedRank);
    const missingCodes = rows.filter(r => !catalog.some(item => String(item.sourceCode) === String(r.sourceCode))).map(r => String(r.sourceCode));
    const expectedCodes = [...rows].reverse().map(r => String(r.sourceCode));
    const sortedCodes = details.filter(d => d.row !== null).map(d => String(d.code));
    const sheetOrderMatches = JSON.stringify(expectedCodes) === JSON.stringify(sortedCodes);
    if (rebaseSheetHistory && (!sheetOrderMatches || missingCodes.length)) {
        throw Error('El orden propuesto no reproduce TODAS las referencias de la hoja; no es una inicialización válida.');
    }
    return { mode: 'preview-only', strategy: rebaseSheetHistory ? 'rebase-all-linked-sheet-row-order' : 'preserve-existing-dates',
        cutoff, total: catalog.length, mirrorRows: rows.length, sheetOrderMatches,
        preserved: details.filter(d => d.basis === 'existing-date-preserved').length,
        estimated: details.filter(d => d.basis.startsWith('historical-')).length,
        unresolved: details.filter(d => d.basis.endsWith('unresolved')).length,
        nextRowCandidates: details.filter(d => d.candidateNeedsReview).length,
        capped: details.filter(d => d.capped).length,
        existingSheetDatesIgnored: details.filter(d => d.existingSheetDateIgnored).length,
        rowOrderAdjustments: details.filter(d => d.basis === 'historical-sheet-order-estimate').length,
        missingCodes,
        rows: details };
}

function markdown(report) {
    const safe = value => String(value ?? 'N/A').replaceAll('|', '\\|').replace(/[\r\n]/g, ' ');
    const table = items => ['| Posición propuesta en catálogo | Posición actual en catálogo | Fila de Sheets (sin cambios) | Código | Título | Referencia propuesta | Base |',
        '| --- | --- | --- | --- | --- | --- | --- |', ...items.map(d =>
            `| ${d.proposedRank} | ${d.currentRank} | ${safe(d.row)} | ${safe(d.code)} | ${safe(d.title)} | ${safe(d.proposedAt?.slice(0, 10))} | ${safe(d.basis)}${d.capped ? ' (limitada)' : ''} |`) ].join('\n');
    const rebase = report.strategy === 'rebase-all-linked-sheet-row-order';
    return `# Vista previa del histórico — NO APLICADA\n\n` +
        `Catálogo: ${report.total}; espejo: ${report.mirrorRows}; códigos faltantes: ${report.missingCodes.length}.\n\n` +
        `Posición propuesta/actual = puesto del registro en la lista del catálogo ordenada por «Más recientes», incluyendo registros locales. NO es el número de fila de Sheets. La columna «Fila de Sheets (sin cambios)» muestra la referencia original; no se mueve, renumera ni escribe ninguna fila. Cambia la presentación de la lista, no la hoja.\n\n` +
        `Fechas existentes conservadas: ${report.preserved}. Estimaciones: ${report.estimated}. Sin referencia: ${report.unresolved}. Candidatos a siguiente fila: ${report.nextRowCandidates}. Limitadas por fecha de recuperación: ${report.capped}.\n\n` +
        `Fechas existentes de Sheets ignoradas para ordenar: ${report.existingSheetDatesIgnored}. Ajustes adicionales para respetar filas: ${report.rowOrderAdjustments}. Orden vinculado idéntico a filas descendentes: ${report.sheetOrderMatches ? 'SÍ' : 'NO'}.\n\n` +
        `Solo inicialización histórica. No se modifica el catálogo, la hoja ni el estreno. Las fechas estimadas no prueban una fecha de alta real. Los días/horas son anclas de orden, no precisión histórica.\n\n` +
        `Regla de prueba: año de columna I y quarter de columna J. Q1→enero, Q2→abril, Q3→julio, Q4→octubre. La temporada activa (G / activeSeason) NO interviene. Un título estrictamente anterior a AMBAS filas vecinas se propone con el año/quarter de la siguiente fila y queda marcado para revisión. Límite: ${report.cutoff} (recuperación documentada). Las futuras altas NO usan esta heurística.\n\n` +
        (rebase ? `Inicialización de TODOS los vinculados: sus fechas previas no ordenan, pero permanecen disponibles como evidencia; el campo propuesto incorporatedAt tiene prioridad. Las fechas estimadas nunca retroceden al recorrer filas de arriba abajo: cualquier retroceso toma la referencia efectiva anterior. Empates se ordenan por fila. Solo locales conservan fechas existentes. Así se respeta toda la secuencia de Sheets, sin afirmar fechas históricas reales.\n\n` :
            `Esta variante conserva fechas existentes y no garantiza reproducir toda la secuencia de la hoja: estrenos y altas son conceptos diferentes.\n\n`) +
        `## Primeros 20, más recientes\n\n${table(report.rows.slice(0, 20))}\n\n` +
        `## Candidatos a tomar referencia de la siguiente fila\n\n${table(report.rows.filter(d => d.candidateNeedsReview))}\n\n` +
        `Todas las filas y referencias prestadas están en el JSON de este informe. Huellas de los archivos de entrada verificadas antes/después.\n`;
}

if (require.main === module) {
    const [catalogPath, mirrorPath, cutoff, outputDir, strategy] = process.argv.slice(2);
    if (!outputDir) throw Error('Uso: node historical-order-preview.cjs catálogo.json espejo.json cutoffISO directorioInforme');
    if (strategy && strategy !== '--rebase-sheet-history') throw Error('Estrategia desconocida.');
    const inputs = [catalogPath, mirrorPath].map(p => path.resolve(p));
    const output = path.resolve(outputDir);
    // Reports must not reside in any source catalog directory.
    if (inputs.some(p => {
        const relative = path.relative(path.dirname(p), output);
        return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
    })) throw Error('El informe debe estar fuera de los directorios de datos originales.');
    const before = inputs.map(p => fs.readFileSync(p));
    const report = preview(JSON.parse(before[0]), JSON.parse(before[1]), cutoff,
        { rebaseSheetHistory: strategy === '--rebase-sheet-history' });
    report.inputSha256 = before.map(digest);
    if (inputs.some((p, i) => digest(fs.readFileSync(p)) !== report.inputSha256[i])) throw Error('Los datos cambiaron durante la lectura; repetir la vista previa.');
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(path.join(output, 'historical-order-preview.json'), JSON.stringify(report, null, 2), { flag: 'wx' });
    fs.writeFileSync(path.join(output, 'historical-order-preview.md'), markdown(report), { flag: 'wx' });
    console.log(JSON.stringify({ ...report, rows: report.rows.slice(0, 5) }, null, 2));
}

module.exports = { preview, quarterAnchor, markdown };
