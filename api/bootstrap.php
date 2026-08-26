<?php

declare(strict_types=1);

$config = require __DIR__ . '/config/app.php';

$sessionDir = $config['session_dir'];
if (!is_dir($sessionDir) && !mkdir($sessionDir, 0775, true) && !is_dir($sessionDir)) {
    throw new RuntimeException('No se pudo preparar el almacenamiento de sesiones.');
}

session_save_path($sessionDir);
session_name($config['session_name']);
session_set_cookie_params([
    'httponly' => true,
    'samesite' => 'Lax',
    'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
]);
session_start();

require_once __DIR__ . '/core/ApiException.php';
require_once __DIR__ . '/core/JsonStorage.php';
require_once __DIR__ . '/core/Response.php';
require_once __DIR__ . '/services/CatalogService.php';
require_once __DIR__ . '/services/AuthService.php';
require_once __DIR__ . '/services/NewsService.php';
require_once __DIR__ . '/services/UserService.php';
require_once __DIR__ . '/services/WatchmodeService.php';
require_once __DIR__ . '/services/JikanService.php';

$storage = new JsonStorage($config['data_dir'], $config['backup_dir']);
$catalogService = new CatalogService($storage);
$authService = new AuthService($storage);
$newsService = new NewsService($storage);
$userService = new UserService($storage, $catalogService);
$watchmodeService = new WatchmodeService($config['watchmode_api_key'], $config['watchmode_base_url']);
$jikanService = new JikanService(
    $config['jikan_base_url'],
    $config['anilist_base_url'],
    $config['kitsu_base_url']
);
