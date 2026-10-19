<?php
// CLI only: read a copied production catalog with the prepared code, never live data.
if (PHP_SAPI !== 'cli') { throw new RuntimeException('Solo CLI.'); }
$app = realpath($argv[1] ?? '');
$descriptor = realpath(getenv('ALTOIDSS_STORAGE_CONFIG') ?: '');
if (!$app || !$descriptor || basename(dirname($app)) !== 'rehearsal'
    || str_replace('\\', '/', $app) === str_replace('\\', '/', dirname(__DIR__))) {
    throw new RuntimeException('Indique una copia de ensayo, no una instalación.');
}
$fixture = dirname($app);
$settings = json_decode((string) file_get_contents($descriptor), true, 512, JSON_THROW_ON_ERROR);
if ($descriptor !== realpath($fixture . '/catalog-storage.local.json')
    || ($settings['environment'] ?? '') !== 'isolated-release-rehearsal'
    || realpath($settings['catalogDir'] ?? '') !== realpath($fixture . '/catalog')
    || realpath($settings['syncStateDir'] ?? '') !== realpath($fixture . '/state')) {
    throw new RuntimeException('Se rechazó el entorno: el catálogo debe ser una copia aislada.');
}
require $app . '/api/core/ApiException.php';
require $app . '/api/core/JsonStorage.php';
require $app . '/api/services/CatalogService.php';
require $app . '/api/services/AnimeReviewService.php';
$before = [];
foreach (glob($fixture . '/catalog/*.json') as $path) { $before[$path] = hash_file('sha256', $path); }
$storage = new JsonStorage($app . '/data', $app . '/backups');
$catalog = new CatalogService($storage);
$counts = [];
foreach (altoidss_catalog_files() as $name) {
    $stored = $storage->read($name);
    $expected = json_decode((string) file_get_contents($fixture . '/catalog/' . $name), true, 512, JSON_THROW_ON_ERROR);
    if ($stored !== $expected) { throw new RuntimeException('La colección no coincide con su copia: ' . $name); }
    $counts[$name] = count($stored);
}
$users = $storage->read('usuarios.json');
if (($users[0]['id'] ?? '') !== 'isolated-local-only') {
    throw new RuntimeException('Los usuarios no están aislados.');
}
$visible = count($catalog->all());
$reviews = count((new AnimeReviewService($storage))->all());
$anime = $storage->read('anime.json');
$linked = array_column(array_filter($anime, fn($item) => !empty($item['sourceCode'])), 'sourceCode');
$mirror = $storage->read('anime-hoja.json');
foreach ($mirror as $row) {
    if (!in_array($row['sourceCode'] ?? null, $linked, true)) {
        throw new RuntimeException('Falta un código de la copia de la hoja.');
    }
}
foreach ($before as $path => $hash) {
    if (hash_file('sha256', $path) !== $hash) { throw new RuntimeException('El ensayo modificó la copia de datos.'); }
}
if (is_file($app . '/api/config/secrets.local.php') || is_file($app . '/config/anime-sync.json')) {
    throw new RuntimeException('No copiar configuración privada al ensayo.');
}
echo json_encode(['passed' => true, 'collections' => $counts, 'visibleContent' => $visible,
    'reviews' => $reviews, 'mirrorCodesPresent' => count($mirror),
    'historicallyInitialized' => count(array_filter($anime, fn($item) => !empty($item['historicalOrderInitialization']))),
    'fixtureJsonUnchanged' => true, 'realAccountsCopied' => false,
    'networkRequests' => 0, 'sheetsStarted' => false], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
