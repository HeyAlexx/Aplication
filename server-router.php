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

$documentRoot = realpath(__DIR__);
$target = realpath(__DIR__ . $requestPath);
if ($target === false || $documentRoot === false || !str_starts_with($target, $documentRoot)) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Recurso no encontrado.';
    return true;
}

return false;
