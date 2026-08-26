<?php

$secretsPath = __DIR__ . DIRECTORY_SEPARATOR . 'secrets.local.php';
$secrets = is_file($secretsPath) ? require $secretsPath : [];

return [
    'app_name' => 'Altoidss',
    'data_dir' => dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'data',
    'backup_dir' => dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'backups',
    'session_dir' => dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'backups' . DIRECTORY_SEPARATOR . 'sessions',
    'session_name' => 'altoidss_session',
    'watchmode_api_key' => getenv('WATCHMODE_API_KEY') ?: ($secrets['watchmode_api_key'] ?? ''),
    'watchmode_base_url' => 'https://api.watchmode.com/v1',
    'jikan_base_url' => 'https://api.jikan.moe/v4',
    'anilist_base_url' => 'https://graphql.anilist.co',
    'kitsu_base_url' => 'https://kitsu.io/api/edge',
];
