<?php
declare(strict_types=1);
date_default_timezone_set('UTC');
// Consultas de lectura; no carga bootstrap, sesiones, colas ni OAuth de Sheets.
require_once __DIR__ . '/../api/core/ApiException.php';
foreach (['MyAnimeListService','JikanService','WatchmodeService'] as $service) {
    require_once __DIR__ . '/../api/services/' . $service . '.php';
}
$config = require ($argv[1] ?? __DIR__ . '/../api/config/app.php');
$mal = new MyAnimeListService($config['myanimelist_client_id']);
$anime = new JikanService($config['jikan_base_url'], $config['anilist_base_url'], $config['kitsu_base_url']);
$watchmode = new WatchmodeService($config['watchmode_api_key'], $config['watchmode_base_url']);
$report = ['timestamp'=>date(DATE_ATOM), 'readOnly'=>true, 'cases'=>[]];
$cases = [
    'myanimelist'=>fn()=>$mal->details(5114),
    'jikan'=>fn()=>$anime->fromSourceUrl('https://api.jikan.moe/v4/anime/5114'),
    'anilist'=>fn()=>$anime->fromSourceUrl('https://anilist.co/anime/5114'),
    'kitsu'=>fn()=>$anime->fromSourceUrl('https://kitsu.io/anime/fullmetal-alchemist-brotherhood'),
    'watchmode-movies'=>fn()=>$watchmode->search('movies','Inception'),
    'watchmode-series'=>fn()=>$watchmode->search('series','Breaking Bad'),
    'anime-search'=>fn()=>$anime->search('Cowboy Bebop'),
];
if (isset($argv[2])) {
    $cases = array_intersect_key($cases, array_fill_keys(explode(',', $argv[2]), true));
    if ($cases === []) { throw new InvalidArgumentException('Seleccione un proveedor válido.'); }
}
foreach ($cases as $provider=>$call) {
    $start = microtime(true);
    try {
        $result = $call();
        $isSearch = str_starts_with($provider,'watchmode') || $provider === 'anime-search';
        $items = $isSearch ? $result : [$result];
        $item = $items[0] ?? null;
        if (!is_array($item) || empty($item['title'])) { throw new RuntimeException('Sin respuesta válida del proveedor solicitado.'); }
        if (!$isSearch && ($item['metadataProvider'] ?? '') !== $provider) {
            throw new RuntimeException('La respuesta no identifica el proveedor solicitado.');
        }
        $report['cases'][] = ['provider'=>$provider, 'passed'=>true, 'title'=>$item['title'],
            'respondingProvider'=>$item['metadataProvider'] ?? $item['source'] ?? null,
            'results'=>count($items), 'hasImage'=>!empty($item['image']), 'seconds'=>round(microtime(true)-$start,2)];
    } catch (Throwable $error) {
        $report['cases'][] = ['provider'=>$provider, 'passed'=>false, 'error'=>$error->getMessage(),
            'seconds'=>round(microtime(true)-$start,2)];
    }
}
if (!is_dir(__DIR__.'/../outputs')) { mkdir(__DIR__.'/../outputs',0775,true); }
$reportFile = isset($argv[2]) ? 'providers-retry-report.json' : 'providers-live-report.json';
file_put_contents(__DIR__.'/../outputs/'.$reportFile, json_encode($report, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
echo json_encode($report, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE), "\n";
exit(count(array_filter($report['cases'], fn($case)=>!$case['passed'])) ? 1 : 0);
