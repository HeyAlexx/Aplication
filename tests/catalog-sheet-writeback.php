<?php
declare(strict_types=1);
require_once __DIR__ . '/../api/core/ApiException.php';
require_once __DIR__ . '/../api/core/JsonStorage.php';
require_once __DIR__ . '/../api/services/CatalogService.php';

$fixture = __DIR__ . '/../runtime/qa-fixtures/catalog-writeback-' . bin2hex(random_bytes(6));
$storage = new JsonStorage($fixture . '/data', $fixture . '/backups');
$catalog = new CatalogService($storage);
function check(bool $condition, string $message): void {
    if (!$condition) { throw new RuntimeException($message); }
}
$record = ['id'=>'qa-linked', 'type'=>'anime', 'title'=>'QA linked', 'genre'=>'Anime',
    'emissionYear'=>2026, 'emissionSeason'=>'Fall', 'seasonsCount'=>1, 'chapters'=>12,
    'format'=>'Serie', 'productionStatus'=>'Finalizado', 'viewingStatus'=>'Por Ver',
    'activeSeason'=>'S01', 'sourceCode'=>'9001', 'sourceRow'=>2, 'createdAt'=>'2020-01-01T00:00:00Z',
    'incorporatedAt'=>'2025-10-01T00:00:00-06:00', 'sheetImportBatchId'=>'historical-fixture',
    'sheetImportRow'=>2, 'incorporationDateBasis'=>'historical-quarter-estimate',
    'historicalOrderInitialization'=>['version'=>'sheet-history-v1', 'migrationId'=>'fixture']];
$storage->write('anime.json', [$record]);
$changed = $catalog->update('qa-linked', ['chapters'=>13, 'incorporatedAt'=>'2099-01-01T00:00:00Z',
    'sheetImportBatchId'=>'forged', 'sheetImportRow'=>999, 'incorporationDateBasis'=>'forged',
    'historicalOrderInitialization'=>['migrationId'=>'forged']]);
$queue = $storage->read('anime-sheet-writeback.json');
check(count($queue) === 1 && $queue[0]['values'][4] === 13, 'Editar un anime vinculado debe actualizar la cola de Sheets.');
check($changed['createdAt'] === $record['createdAt'], 'Editar no debe alterar la fecha de incorporación.');
foreach (['incorporatedAt', 'sheetImportBatchId', 'sheetImportRow', 'incorporationDateBasis', 'historicalOrderInitialization'] as $field) {
    check($changed[$field] === $record[$field], 'Editar no debe alterar la incorporación histórica ni su auditoría.');
}
check(($changed['sheetSyncStatus'] ?? '') === 'Pendiente', 'La respuesta debe informar que Sheets aún está pendiente.');
$version = $queue[0]['version'];
$catalog->update('qa-linked', ['image'=>'https://example.com/image.jpg']);
check($storage->read('anime-sheet-writeback.json')[0]['version'] === $version, 'Metadatos que no existen en Sheets no deben generar otra escritura.');
$catalog->update('qa-linked', ['title'=>'QA renamed', 'sourceCode'=>'otro', 'sourceRow'=>999]);
$queue = $storage->read('anime-sheet-writeback.json');
check(count($queue) === 1 && $queue[0]['sourceCode'] === '9001' && $queue[0]['targetRow'] === 2, 'La edición no debe cambiar la vinculación existente.');
check($queue[0]['values'][1] === 'QA renamed', 'La cola debe conservar la versión más reciente.');
$local = $catalog->create(array_merge($record, ['id'=>'qa-local', 'title'=>'QA local', 'sourceCode'=>'local', 'sourceRow'=>5]));
check(count($storage->read('anime-sheet-writeback.json')) === 1, 'Crear desde la página no debe añadir filas ni escrituras a Sheets.');
check(!isset($local['sourceCode']) && !isset($local['sourceRow']), 'Crear desde la página no debe inventar una vinculación de Sheets.');
check(!isset($local['incorporatedAt']) && !isset($local['historicalOrderInitialization']), 'Un alta local no puede forjar incorporación histórica.');
$catalog->update('qa-local', ['chapters'=>24]);
check(count($storage->read('anime-sheet-writeback.json')) === 1, 'Editar una obra local tampoco debe crear filas en Sheets.');
$external = $catalog->importExternal('kitsu-qa', ['source'=>'kitsu', 'type'=>'anime', 'title'=>'QA external', 'sourceCode'=>'fake', 'sourceRow'=>5]);
check(!isset($external['sourceCode']) && !isset($external['sourceRow']), 'Importar desde la página tampoco debe inventar un vínculo con Sheets.');
check(count($storage->read('anime-sheet-writeback.json')) === 1, 'Importar desde proveedores no debe añadir filas en Sheets.');
echo "OK: edición vinculada, fechas, metadatos, vínculo estable, última versión y altas locales sin filas de Sheets.\n";
