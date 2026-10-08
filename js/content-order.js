// La fecha de incorporación es independiente del estreno y de las ediciones.
const AltoidssContentOrder = (() => {
    const timestamp = (item) => {
        for (const key of ["createdAt", "importedAt"]) {
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

    const sort = (items, direction = "newest") => [...items].sort((left, right) => {
        const leftDate = timestamp(left);
        const rightDate = timestamp(right);
        const leftRow = sheetPosition(left);
        const rightRow = sheetPosition(right);
        // Los registros históricos de la hoja preceden a las altas fechadas.
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
        if (leftRow !== null && rightRow !== null && leftRow !== rightRow) {
            return direction === "oldest" ? leftRow - rightRow : rightRow - leftRow;
        }
        // Desempate estable: editar no cambia la posición por el orden del JSON.
        return String(left.title || "").localeCompare(String(right.title || ""), "es", { numeric: true })
            || String(left.id || "").localeCompare(String(right.id || ""), "es", { numeric: true });
    });

    return { timestamp, sheetPosition, sort };
})();

if (typeof module !== "undefined" && module.exports) module.exports = AltoidssContentOrder;
