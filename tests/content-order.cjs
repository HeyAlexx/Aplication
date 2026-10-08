const assert = require("node:assert/strict");
const { sort, timestamp } = require("../js/content-order.js");

const items = [
    { id: "unknown-z", title: "Zeta", emissionYear: 2099, updatedAt: "2099-01-01T00:00:00Z" },
    { id: "old", title: "Viejo", createdAt: "2026-01-01T00:00:00Z" },
    { id: "new", title: "Nuevo", importedAt: "2026-10-01T00:00:00Z", emissionYear: 1900 },
    { id: "unknown-a", title: "Alfa", createdAt: "no es fecha" },
];
const original = JSON.stringify(items);
assert.deepEqual(sort(items).map(item => item.id), ["new", "old", "unknown-a", "unknown-z"]);
assert.deepEqual(sort(items, "oldest").map(item => item.id), ["old", "new", "unknown-a", "unknown-z"]);
assert.equal(JSON.stringify(items), original, "El orden visual no debe modificar los datos originales.");
assert.equal(timestamp({ createdAt: "2026", year: 2026 }), null);
assert.equal(timestamp({ createdAt: "invalido", importedAt: "2026-01-01T00:00:00Z" }), Date.parse("2026-01-01T00:00:00Z"));
assert.equal(timestamp({ createdAt: "1970-01-01T00:00:00Z" }), 0);
assert.equal(timestamp({ createdAt: "2026-01-01T00:00:00Z", importedAt: "2026-10-01T00:00:00Z" }), Date.parse("2026-01-01T00:00:00Z"));
const ties = [{ id: "2", title: "Igual", createdAt: "2026-01-01T00:00:00Z" }, { id: "1", title: "Igual", createdAt: "2026-01-01T01:00:00+01:00" }];
assert.deepEqual(sort(ties).map(item => item.id), ["1", "2"]);
assert.deepEqual(sort(ties, "oldest").map(item => item.id), ["1", "2"]);
assert.deepEqual(sort([]), []);
const historical = [
    { id: "sheet-first", sourceRow: 2, title: "Zeta" },
    { id: "sheet-last", sourceRow: 739, title: "Alfa" },
    { id: "dated-new", createdAt: "2026-10-07T12:00:00Z" },
    { id: "no-reference", sourceRow: "invalid" },
];
assert.deepEqual(sort(historical).map(item => item.id), ["dated-new", "sheet-last", "sheet-first", "no-reference"]);
assert.deepEqual(sort(historical, "oldest").map(item => item.id), ["sheet-first", "sheet-last", "dated-new", "no-reference"]);
console.log("OK: orden cronologico, fechas desconocidas, desempates y datos originales preservados.");
