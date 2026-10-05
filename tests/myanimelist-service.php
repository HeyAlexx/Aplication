<?php
declare(strict_types=1);
require_once __DIR__ . '/../api/core/ApiException.php';
require_once __DIR__ . '/../api/services/MyAnimeListService.php';

$config = require __DIR__ . '/../api/config/app.php';
$service = new MyAnimeListService($config['myanimelist_client_id']);
if (in_array('--live', $argv, true)) {
    $candidate = $service->details(5114);
    echo json_encode(['provider' => $candidate['metadataProvider'], 'title' => $candidate['title'], 'chapters' => $candidate['chapters']], JSON_UNESCAPED_UNICODE) . PHP_EOL;
    exit(0);
}
$normalizer = new ReflectionMethod(MyAnimeListService::class, 'normalize');
$candidate = $normalizer->invoke($service, [
    'id' => 5114, 'title' => 'Fullmetal Alchemist: Brotherhood',
    'media_type' => 'tv', 'status' => 'finished_airing', 'num_episodes' => 64,
    'start_season' => ['year' => 2009, 'season' => 'spring'],
    'genres' => [['name' => 'Action'], ['name' => 'Adventure']],
    'alternative_titles' => ['en' => 'Fullmetal Alchemist: Brotherhood', 'synonyms' => ['FMA']],
]);
foreach (['format' => 'Serie', 'productionStatus' => 'Finalizado', 'chapters' => 64, 'emissionSeason' => 'Spring', 'jikanId' => '5114'] as $field => $expected) {
    if ($candidate[$field] !== $expected) {
        throw new RuntimeException('Conversión incorrecta de ' . $field);
    }
}
if (isset($candidate['seasonsCount']) || isset($candidate['activeSeason'])) {
    throw new RuntimeException('La API no debe alterar las temporadas del catálogo.');
}
echo "OK: campos de MyAnimeList convertidos al formato de revisión.\n";
