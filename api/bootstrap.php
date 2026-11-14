<?php

declare(strict_types=1);

$config = require __DIR__ . '/config/app.php';

$sessionDir = $config['session_dir'];
if (!is_dir($sessionDir) && !mkdir($sessionDir, 0775, true) && !is_dir($sessionDir)) {
    throw new RuntimeException('No se pudo preparar el almacenamiento de sesiones.');
}

session_save_path($sessionDir);
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
session_name($config['session_name']);
session_set_cookie_params([
    'httponly' => true,
    'samesite' => 'Lax',
    // Honour server policy for TLS-terminating proxies; never trust client forwarding headers.
    'secure' => (bool) ini_get('session.cookie_secure')
        || (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off'),
]);
session_start();

require_once __DIR__ . '/core/ApiException.php';
require_once __DIR__ . '/core/JsonStorage.php';
require_once __DIR__ . '/core/Response.php';
require_once __DIR__ . '/services/CatalogService.php';
require_once __DIR__ . '/services/AuthService.php';
require_once __DIR__ . '/services/LoginLimiter.php';
require_once __DIR__ . '/services/NewsService.php';
require_once __DIR__ . '/services/UserService.php';
require_once __DIR__ . '/services/WatchmodeService.php';
require_once __DIR__ . '/services/JikanService.php';
require_once __DIR__ . '/services/MyAnimeListService.php';
require_once __DIR__ . '/services/AnimeReviewService.php';
require_once __DIR__ . '/services/ExternalCatalogService.php';
require_once __DIR__ . '/services/CatalogRequestService.php';

$storage = new JsonStorage($config['data_dir'], $config['backup_dir']);
$catalogService = new CatalogService($storage);
$authState = new JsonStorage($config['backup_dir'] . '/security', $config['backup_dir'] . '/security-backups');
$authService = new AuthService($storage, new LoginLimiter($authState));
$newsService = new NewsService($storage);
$watchmodeService = new WatchmodeService($config['watchmode_api_key'], $config['watchmode_base_url']);
$jikanService = new JikanService(
    $config['jikan_base_url'],
    $config['anilist_base_url'],
    $config['kitsu_base_url'],
    new MyAnimeListService($config['myanimelist_client_id'])
);
$animeReviewService = new AnimeReviewService($storage);
$externalCatalog = new ExternalCatalogService($jikanService, $watchmodeService);
$catalogRequests = new CatalogRequestService($storage, $catalogService,
    fn(string $id): array => $externalCatalog->resolve($id),
    fn(): array => $authService->requireAdmin(), fn(): array => $authService->requireUser());
$userService = new UserService($storage, $catalogService, $catalogRequests);
