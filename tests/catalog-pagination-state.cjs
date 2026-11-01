// Regresion de visualizacion y pagina; procedimiento: docs/CI-CD.md.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../js/catalogo.js"), "utf8");

// Ejecuta las funciones de produccion con DOM y catalogo aislados, sin datos reales.
const extract = (name) => {
    const match = source.match(new RegExp(`const ${name} = [\\s\\S]*?\\n};`));
    assert.ok(match, `Funcion disponible: ${name}`);
    return match[0];
};
const context = vm.createContext({
    document: { querySelector: () => ({ replaceChildren() {}, style: { setProperty() {} } }) },
});
vm.runInContext(`
    const currentPages = { anime: 2 }; const ITEMS_PER_PAGE = 35;
    let count = 80; let urlPage;
    const getCategoryItems = () => Array.from({length: count}, (_, id) => ({id}));
    const createCatalogCard = item => item;
    const AltoidssStore = { getProfile: () => ({settings: {}}) };
    const renderPagination = () => {}; const enhanceCatalogCards = () => {};
    const updateFilterResultCount = () => {};
    const updatePageInUrl = (category, page) => { urlPage = page; };
    ${extract("renderCatalogPage")}
    ${extract("applyCurrentFilters")}
`, context);

// Cubre pagina conservada, ultima pagina eliminada, cero resultados y filtro nuevo.
for (const [count, initial, preserve, expected] of [
    [80, 2, true, 2], [35, 2, true, 1], [0, 2, true, 1],
    [80, 2, false, 1], [71, 3, true, 3], [70, 3, true, 2],
]) {
    vm.runInContext(`count=${count}; currentPages.anime=${initial};
        applyCurrentFilters('anime', {preservePage:${preserve}});`, context);
    assert.equal(vm.runInContext("currentPages.anime", context), expected);
    assert.equal(vm.runInContext("urlPage", context), expected);
}
// Comprueba tambien que el flujo de cambio de estado solicita conservar pagina.
assert.match(source, /setTimeout\(\(\) => applyCurrentFilters\(category, \{ preservePage: true \}\), 180\)/);
console.log("OK: seis escenarios de paginacion y actualizacion de URL.");
