<?php

declare(strict_types=1);

$requestPath = rawurldecode((string) (parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/'));
$requestPath = '/' . ltrim(str_replace('\\', '/', $requestPath), '/');

$blockedPrefixes = [
    '/backups/',
    '/config/',
    '/runtime/',
    '/tools/',
    '/tests/',
    '/outputs/',
];
$publicDataFiles = [
    '/data/anime.json',
    '/data/noticias.json',
    '/data/peliculas.json',
    '/data/series.json',
];

$blocked = str_contains($requestPath, '/.')
    || str_ends_with($requestPath, '.lock')
    || str_contains($requestPath, '.tmp-');

foreach ($blockedPrefixes as $prefix) {
    if (str_starts_with($requestPath, $prefix)) {
        $blocked = true;
        break;
    }
}

if (str_starts_with($requestPath, '/data/') && !in_array($requestPath, $publicDataFiles, true)) {
    $blocked = true;
}

if (str_starts_with($requestPath, '/api/') && $requestPath !== '/api/index.php') {
    $blocked = true;
}

if ($blocked) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Recurso no disponible.';
    return true;
}

if ($requestPath === '/') {
    header('Location: /Html/index.html', true, 302);
    return true;
}

// Serve the same catalogue used by the API, including the static fallback.
if (in_array($requestPath, $publicDataFiles, true)) {
    require_once __DIR__ . '/api/core/ApiException.php';
    require_once __DIR__ . '/api/core/JsonStorage.php';
    try {
        $storage = new JsonStorage(__DIR__ . '/data', __DIR__ . '/backups');
        $records = $storage->read(basename($requestPath));
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        echo json_encode($records, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
    } catch (Throwable $error) {
        http_response_code(503);
        header('Content-Type: application/json; charset=utf-8');
        echo '{"error":"Catálogo temporalmente no disponible."}';
    }
    return true;
}

$documentRoot = realpath(__DIR__);
$target = realpath(__DIR__ . $requestPath);
if ($target === false || $documentRoot === false || !str_starts_with($target, $documentRoot)) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Recurso no encontrado.';
    return true;
}

return false;
