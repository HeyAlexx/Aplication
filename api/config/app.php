<?php

$secretsPath = __DIR__ . DIRECTORY_SEPARATOR . 'secrets.local.php';
$secrets = is_file($secretsPath) ? require $secretsPath : [];
$malClientPath = __DIR__ . DIRECTORY_SEPARATOR . 'mal-client-id.local.txt';
$malClientId = is_file($malClientPath) ? trim((string) file_get_contents($malClientPath)) : '';

return [
    'app_name' => 'Altoidss',
    'data_dir' => dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'data',
    'backup_dir' => dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'backups',
    'session_dir' => dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'backups' . DIRECTORY_SEPARATOR . 'sessions',
    'session_name' => 'altoidss_session',
    'watchmode_api_key' => getenv('WATCHMODE_API_KEY') ?: ($secrets['watchmode_api_key'] ?? ''),
    'watchmode_base_url' => 'https://api.watchmode.com/v1',
    'myanimelist_client_id' => getenv('MAL_CLIENT_ID') ?: ($secrets['myanimelist_client_id'] ?? $malClientId),
    'jikan_base_url' => 'https://api.jikan.moe/v4',
    'anilist_base_url' => 'https://graphql.anilist.co',
    'kitsu_base_url' => 'https://kitsu.io/api/edge',
];
