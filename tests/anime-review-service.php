<?php

declare(strict_types=1);

require_once __DIR__ . '/../api/core/ApiException.php';
require_once __DIR__ . '/../api/core/JsonStorage.php';
require_once __DIR__ . '/../api/services/AnimeReviewService.php';

function assertSameValue(mixed $expected, mixed $actual, string $message): void
{
    if ($expected !== $actual) {
        throw new RuntimeException($message . ' Esperado: ' . json_encode($expected) . '; recibido: ' . json_encode($actual));
    }
}

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'altoidss-review-' . bin2hex(random_bytes(5));
$data = $root . DIRECTORY_SEPARATOR . 'data';
$backups = $root . DIRECTORY_SEPARATOR . 'backups';
mkdir($data, 0775, true);
mkdir($backups, 0775, true);

try {
    file_put_contents($data . DIRECTORY_SEPARATOR . 'anime.json', "[]\n");
    file_put_contents($data . DIRECTORY_SEPARATOR . 'anime-revisiones.json', json_encode([[
        'id' => 'anime-review-9001',
        'contentId' => 'anime-sheet-9001',
        'sourceCode' => '9001',
        'sourceRow' => 55,
        'title' => 'Anime pendiente',
        'status' => 'Pendiente',
        'original' => [
            'sourceCode' => '9001',
            'title' => 'Anime pendiente',
            'format' => 'Serie',
            'productionStatus' => 'Emisión',
            'viewingStatus' => 'Por Ver',
            'chapters' => 0,
            'seasonsCount' => 1,
            'activeSeason' => 'S01',
            'emissionYear' => 2026,
            'emissionSeason' => 'Summer',
        ],
    ]], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    $service = new AnimeReviewService(new JsonStorage($data, $backups));
    $result = $service->decide('anime-review-9001', [
        'decision' => 'save',
        'notes' => 'Validado manualmente',
        'finalData' => [
            'title' => 'Anime definitivo',
            'format' => 'ONA',
            'productionStatus' => 'Emisión',
            'chapters' => 12,
            'seasonsCount' => 1,
            'activeSeason' => 'S01',
            'emissionYear' => 2026,
            'emissionSeason' => 'Summer',
            'genre' => 'Anime',
            'description' => 'Sinopsis validada.',
        ],
    ], ['displayName' => 'Administrador']);

    $anime = json_decode(file_get_contents($data . DIRECTORY_SEPARATOR . 'anime.json'), true, 512, JSON_THROW_ON_ERROR);
    assertSameValue('Aprobado', $result['status'], 'La revisión debe quedar aprobada.');
    assertSameValue(1, count($anime), 'Debe crearse un anime cuando la revisión no tiene registro previo.');
    assertSameValue('anime-sheet-9001', $anime[0]['id'], 'Debe conservarse el identificador de la revisión.');
    assertSameValue('9001', $anime[0]['sourceCode'], 'Debe conservarse el código de la hoja.');
    assertSameValue('Anime definitivo', $anime[0]['title'], 'Debe aplicarse la versión final.');
    assertSameValue('Por Ver', $anime[0]['viewingStatus'], 'Debe conservarse el estado de visualización original.');
    assertSameValue(false, $anime[0]['metadataNeedsReview'], 'El anime debe quedar marcado como revisado.');
    assertSameValue(55, $anime[0]['sourceRow'], 'Las altas aprobadas conservan la fila de origen.');
    assertSameValue('Pendiente', $result['sheetSyncStatus'], 'Guardar en JSON no significa confirmar Google.');
    $queue = json_decode(file_get_contents($data . '/anime-sheet-writeback.json'), true, 512, JSON_THROW_ON_ERROR);
    assertSameValue(1, count($queue), 'La aprobación debe generar una devolución.');
    assertSameValue(['9001', 'Anime definitivo', 'Emision', 'ONA', 12, 1, 'S01', 'Por Ver', 2026, 3], $queue[0]['values'], 'La cola representa los mismos diez campos del catálogo.');
    $createdAt = $anime[0]['createdAt'];
    $service->decide('anime-review-9001', ['decision' => 'save', 'finalData' => ['title' => 'Anime corregido']], []);
    $queue = json_decode(file_get_contents($data . '/anime-sheet-writeback.json'), true, 512, JSON_THROW_ON_ERROR);
    $anime = json_decode(file_get_contents($data . '/anime.json'), true, 512, JSON_THROW_ON_ERROR);
    assertSameValue(1, count($queue), 'Una nueva decisión reemplaza la cola del mismo código.');
    assertSameValue('Anime corregido', $queue[0]['values'][1], 'La cola conserva la última decisión.');
    assertSameValue($createdAt, $anime[0]['createdAt'], 'Editar conserva la incorporación.');
    assertSameValue('Sinopsis validada.', $anime[0]['description'], 'Editar conserva los metadatos no enviados.');
    $service->decide('anime-review-9001', ['decision' => 'reject'], []);
    assertSameValue($queue, json_decode(file_get_contents($data . '/anime-sheet-writeback.json'), true, 512, JSON_THROW_ON_ERROR), 'Rechazar no crea ni cambia una devolución.');

    echo "OK: las revisiones nuevas se guardan y crean su anime.\n";
} finally {
    if (is_dir($root)) {
        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::CHILD_FIRST
        );
        foreach ($iterator as $entry) {
            $entry->isDir() ? rmdir($entry->getPathname()) : unlink($entry->getPathname());
        }
        rmdir($root);
    }
}
