<?php
declare(strict_types=1);

// Public resources are explicit: Windows path aliases must never open private files.
function altoidss_router_not_found(): bool
{
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Recurso no disponible.';
    return true;
}

function altoidss_router_asset(string $path): bool
{
    if (!preg_match('#^/(css|js|img)/.+\.([a-z0-9]+)$#iD', $path, $matches)) {
        return false;
    }
    $extensions = [
        'css' => ['css', 'woff', 'woff2', 'ttf'],
        'js' => ['js'],
        'img' => ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'ico', 'avif'],
    ];
    return in_array(strtolower($matches[2]), $extensions[strtolower($matches[1])], true);
}

$requestPath = rawurldecode((string) (parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/'));
$requestPath = '/' . ltrim(str_replace('\\', '/', $requestPath), '/');
if (preg_match('/[\x00-\x1f\x7f:%]/', $requestPath)
    || str_contains($requestPath, '//')
    || str_contains($requestPath, '/.')
    || str_contains($requestPath, '.tmp-')) {
    return altoidss_router_not_found();
}

if ($requestPath === '/') {
    header('Location: /Html/index.html', true, 302);
    return true;
}

$publicPages = array_map(
    fn(string $name): string => '/Html/' . $name . '.html',
    ['index', 'catalogo', 'dashboard', 'favoritos', 'login', 'noticias']
);
$publicCatalog = [
    '/data/anime.json' => 'anime',
    '/data/peliculas.json' => 'movies',
    '/data/series.json' => 'series',
    '/data/noticias.json' => 'news',
];

// Legacy read-only URLs expose the same filtered representation as public API reads.
if (isset($publicCatalog[$requestPath])) {
    require_once __DIR__ . '/api/core/ApiException.php';
    require_once __DIR__ . '/api/core/JsonStorage.php';
    require_once __DIR__ . '/api/services/CatalogService.php';
    require_once __DIR__ . '/api/services/NewsService.php';
    try {
        $storage = new JsonStorage(__DIR__ . '/data', __DIR__ . '/backups');
        $type = $publicCatalog[$requestPath];
        $records = $type === 'news'
            ? (new NewsService($storage))->published()
            : (new CatalogService($storage))->byType($type);
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

$isApi = $requestPath === '/api/index.php';
$isPage = in_array($requestPath, $publicPages, true);
if (!$isApi && !$isPage && !altoidss_router_asset($requestPath)) {
    return altoidss_router_not_found();
}

$documentRoot = realpath(__DIR__);
$target = realpath(__DIR__ . $requestPath);
if ($documentRoot === false || $target === false || !is_file($target)) {
    return altoidss_router_not_found();
}
$prefix = $documentRoot . DIRECTORY_SEPARATOR;
$inside = PHP_OS_FAMILY === 'Windows'
    ? strncasecmp($target, $prefix, strlen($prefix)) === 0
    : str_starts_with($target, $prefix);
if (!$inside) {
    return altoidss_router_not_found();
}
$resolvedPath = '/' . str_replace('\\', '/', substr($target, strlen($prefix)));

// Validate the resolved target too: a public-looking link cannot expose a private file.
if ($isApi) {
    if ($resolvedPath !== '/api/index.php') {
        return altoidss_router_not_found();
    }
    try {
        require $target;
    } catch (Throwable $error) {
        error_log('Altoidss API initialization failed: ' . get_class($error));
        http_response_code(503);
        header('Content-Type: application/json; charset=utf-8');
        echo '{"ok":false,"error":{"message":"API temporalmente no disponible."}}';
    }
    return true;
}
if (($isPage && !in_array($resolvedPath, $publicPages, true))
    || (!$isPage && !altoidss_router_asset($resolvedPath))) {
    return altoidss_router_not_found();
}

$contentTypes = [
    'html' => 'text/html; charset=utf-8', 'css' => 'text/css; charset=utf-8',
    'js' => 'text/javascript; charset=utf-8', 'svg' => 'image/svg+xml',
    'png' => 'image/png', 'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg',
    'webp' => 'image/webp', 'gif' => 'image/gif', 'ico' => 'image/x-icon',
    'avif' => 'image/avif', 'woff' => 'font/woff', 'woff2' => 'font/woff2',
    'ttf' => 'font/ttf',
];
header('Content-Type: ' . $contentTypes[strtolower(pathinfo($target, PATHINFO_EXTENSION))]);
readfile($target);
return true;
