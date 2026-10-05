<?php
declare(strict_types=1);

require_once __DIR__ . '/../api/core/ApiException.php';
require_once __DIR__ . '/../api/services/JikanService.php';

$service = new JikanService('https://api.jikan.moe/v4', 'https://graphql.anilist.co', 'https://kitsu.io/api/edge');
foreach (['https://example.com/anime/5114', 'https://myanimelist.net.evil.example/anime/5114'] as $url) {
    if ($service->fromSourceUrl($url) !== null) {
        throw new RuntimeException('Debe rechazar fuentes no compatibles.');
    }
}
if (in_array('--live', $argv, true)) {
    $useAniList = in_array('--anilist', $argv, true);
    $candidate = $service->fromSourceUrl($useAniList
        ? 'https://anilist.co/anime/5114/Fullmetal-Alchemist-Brotherhood/'
        : 'https://myanimelist.net/anime/5114/Fullmetal_Alchemist__Brotherhood');
    if ($candidate === null || empty($candidate['title'])) {
        throw new RuntimeException('No se recuperó el anime de prueba desde Jikan.');
    }
    echo json_encode(['title' => $candidate['title'], 'provider' => $candidate['metadataProvider'], 'chapters' => $candidate['chapters']], JSON_UNESCAPED_UNICODE) . PHP_EOL;
}
echo "OK: validación de fuentes.\n";
