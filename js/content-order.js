// La fecha de incorporación es independiente del estreno y de las ediciones.
const AltoidssContentOrder = (() => {
    const timestamp = (item) => {
        for (const key of ["incorporatedAt", "createdAt", "importedAt"]) {
            const value = item[key];
            if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T/.test(value)) continue;
            const parsed = Date.parse(value);
            if (Number.isFinite(parsed)) return parsed;
        }
        return null;
    };

    const sheetPosition = (item) => {
        const row = Number(item.sourceRow);
        return Number.isSafeInteger(row) && row >= 2 ? row : null;
    };

    const batchPosition = (item) => {
        const row = Number(item.sheetImportRow);
        return Number.isSafeInteger(row) && row >= 2 ? row : sheetPosition(item);
    };

    const sort = (items, direction = "newest") => [...items].sort((left, right) => {
        const leftDate = timestamp(left);
        const rightDate = timestamp(right);
        const leftRow = sheetPosition(left);
        const rightRow = sheetPosition(right);
        // App and Sheet batches share a timeline. Legacy undated rows are only a
        // compatibility fallback until an explicitly documented baseline is set.
        // Sin ninguna referencia de incorporación, el registro queda al final.
        const group = (date, row) => date !== null ? 2 : row !== null ? 1 : 0;
        const leftGroup = group(leftDate, leftRow);
        const rightGroup = group(rightDate, rightRow);
        if (leftGroup === 0 && rightGroup !== 0) return 1;
        if (rightGroup === 0 && leftGroup !== 0) return -1;
        if (leftGroup !== rightGroup) return direction === "oldest" ? leftGroup - rightGroup : rightGroup - leftGroup;
        if (leftDate !== null && rightDate !== null && leftDate !== rightDate) {
            return direction === "oldest" ? leftDate - rightDate : rightDate - leftDate;
        }
        if (left.sheetImportBatchId || right.sheetImportBatchId) {
            const leftBatch = String(left.sheetImportBatchId || `app:${left.id || left.title || ""}`);
            const rightBatch = String(right.sheetImportBatchId || `app:${right.id || right.title || ""}`);
            // Equal timestamps have no inferred chronology. Keep batches together
            // with a deterministic key, then use frozen row order inside a batch.
            if (leftBatch !== rightBatch) return leftBatch.localeCompare(rightBatch);
            const leftPosition = batchPosition(left), rightPosition = batchPosition(right);
            if (leftPosition !== null && rightPosition !== null && leftPosition !== rightPosition) {
                return direction === "oldest" ? leftPosition - rightPosition : rightPosition - leftPosition;
            }
        }
        if (leftRow !== null && rightRow !== null && leftRow !== rightRow) {
            return direction === "oldest" ? leftRow - rightRow : rightRow - leftRow;
        }
        // Desempate estable: editar no cambia la posición por el orden del JSON.
        return String(left.title || "").localeCompare(String(right.title || ""), "es", { numeric: true })
            || String(left.id || "").localeCompare(String(right.id || ""), "es", { numeric: true });
    });

    return { timestamp, sheetPosition, batchPosition, sort };
})();

if (typeof module !== "undefined" && module.exports) module.exports = AltoidssContentOrder;
