<?php
// No bootstrap, OAuth, providers or sessions. Read restored files with explicit isolated routing.
if (PHP_SAPI !== 'cli') { throw new RuntimeException('Solo CLI.'); }
$app = realpath($argv[1] ?? '');
$descriptor = realpath(getenv('ALTOIDSS_STORAGE_CONFIG') ?: '');
if (!$app || !$descriptor || !str_contains(str_replace('\\', '/', $app), '/work/recovery-drills/coordinated-')) {
    throw new RuntimeException('Solo se admiten copias del ensayo de recuperación.');
}
$workspace = dirname($app, 2);
$folder = basename(dirname($app));
$environment = match ($folder) { 'ProyectoFinal' => 'produccion', 'Desarrollo' => 'desarrollo',
    default => throw new RuntimeException('Entorno de copia desconocido.') };
$settings = json_decode((string) file_get_contents($descriptor), true, 512, JSON_THROW_ON_ERROR);
$catalogDir = realpath($workspace . '/datos/' . $environment . '/catalogo');
$stateDir = realpath($workspace . '/datos/' . $environment . '/anime-sync');
if (basename($workspace) !== 'workspace' || dirname($descriptor) !== dirname($workspace)
    || ($settings['environment'] ?? '') !== 'isolated-recovery'
    || !$catalogDir || !$stateDir || realpath($settings['catalogDir'] ?? '') !== $catalogDir
    || realpath($settings['syncStateDir'] ?? '') !== $stateDir) {
    throw new RuntimeException('Descriptor de recuperación no aislado.');
}
require $app . '/api/core/ApiException.php';
require $app . '/api/core/JsonStorage.php';
require $app . '/api/services/CatalogService.php';
require $app . '/api/services/AnimeReviewService.php';
$storage = new JsonStorage($app . '/data', $app . '/backups');
$counts = [];
foreach (altoidss_catalog_files() as $name) {
    $expected = json_decode((string) file_get_contents($catalogDir . '/' . $name), true, 512, JSON_THROW_ON_ERROR);
    $actual = $storage->read($name);
    if ($actual !== $expected) { throw new RuntimeException('Colección restaurada incompatible: ' . $name); }
    $counts[$name] = count($actual);
}
$privateCounts = [];
foreach (['usuarios.json','perfiles.json','configuraciones.json','favoritos.json','historial.json'] as $name) {
    $expected = json_decode((string) file_get_contents($app . '/data/' . $name), true, 512, JSON_THROW_ON_ERROR);
    if ($storage->read($name) !== $expected) { throw new RuntimeException('Datos privados no aislados.'); }
    $privateCounts[$name] = count($expected);
}
$catalog = new CatalogService($storage);
$reviews = new AnimeReviewService($storage);
$stateJson = 0;
foreach (glob($stateDir . '/*.json') as $path) {
    json_decode(preg_replace('/^\xEF\xBB\xBF/', '', (string) file_get_contents($path)), true, 512, JSON_THROW_ON_ERROR);
    $stateJson++;
}
echo json_encode(['passed'=>true, 'centralCollections'=>$counts, 'privateCollections'=>$privateCounts,
    'syncStateJsonValidated'=>$stateJson, 'visibleContent'=>count($catalog->all()),
    'reviewsReadable'=>count($reviews->all()), 'networkRequests'=>0, 'sessionsStarted'=>false],
    JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
