<?php
declare(strict_types=1);
// Only called with a disposable fixture by sheets-roundtrip-live.py.
require_once __DIR__ . '/../api/core/ApiException.php';
require_once __DIR__ . '/../api/core/JsonStorage.php';
require_once __DIR__ . '/../api/services/CatalogService.php';
require_once __DIR__ . '/../api/services/AnimeReviewService.php';
$root = realpath($argv[1]);
if (!$root || !is_file($root . '/.qa-fixture')) { throw new RuntimeException('Falta el marcador de fixture.'); }
$storage = new JsonStorage($root . '/data', $root . '/backups');
$record = $storage->read('anime.json')[0];
$catalog = new CatalogService($storage);
switch ($argv[2]) {
    case 'edit':
        $catalog->update($record['id'], ['chapters'=>(int)$argv[3]]);
        break;
    case 'review':
        $review = ['id'=>'qa-live-review', 'contentId'=>$record['id'], 'sourceCode'=>$record['sourceCode'],
            'sourceRow'=>$record['sourceRow'], 'title'=>$record['title'], 'original'=>$record, 'status'=>'Pendiente'];
        $storage->write('anime-revisiones.json', [$review]);
        $record['chapters'] = (int)$argv[3];
        (new AnimeReviewService($storage))->decide('qa-live-review',
            ['decision'=>'save','finalData'=>$record], ['displayName'=>'QA isolated']);
        break;
    case 'local':
        unset($record['id']);
        $catalog->create(array_merge($record, ['title'=>'QA local, no Sheet row']));
        if ($storage->read('anime-sheet-writeback.json') !== []) { throw new RuntimeException('Alta local creó una devolución.'); }
        break;
    default: throw new RuntimeException('Acción no admitida.');
}
echo "fixture-ok\n";
