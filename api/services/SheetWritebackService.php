<?php

/** Solo modifica filas ya vinculadas; nunca solicita crear filas de Sheets. */
final class SheetWritebackService
{
    public static function valuesFor(array $record): array
    {
        $quarter = ['Winter'=>1, 'Spring'=>2, 'Summer'=>3, 'Fall'=>4][$record['emissionSeason'] ?? ''] ?? '';
        return [
            trim((string) ($record['sourceCode'] ?? '')),
            (string) ($record['title'] ?? ''),
            ($record['productionStatus'] ?? '') === 'Emisión' ? 'Emision' : (string) ($record['productionStatus'] ?? ''),
            ($record['format'] ?? '') === 'Película' ? 'Movie' : (string) ($record['format'] ?? ''),
            (int) ($record['chapters'] ?? 0), (int) ($record['seasonsCount'] ?? 0),
            (string) ($record['activeSeason'] ?? ''),
            ($record['viewingStatus'] ?? '') === 'No Visto' ? 'No visto' : (string) ($record['viewingStatus'] ?? ''),
            (int) ($record['emissionYear'] ?? 0) ?: '', $quarter,
        ];
    }

    public static function queue(JsonStorage $storage, array $record): string
    {
        $sourceCode = trim((string) ($record['sourceCode'] ?? ''));
        $targetRow = (int) ($record['sourceRow'] ?? 0);
        if ($sourceCode === '' || $targetRow < 2) {
            return 'Sin referencia de hoja';
        }
        $queue = array_values(array_filter($storage->read('anime-sheet-writeback.json'),
            static fn(array $entry): bool => (string) ($entry['sourceCode'] ?? '') !== $sourceCode));
        $queue[] = ['sourceCode'=>$sourceCode, 'targetRow'=>$targetRow,
            'values'=>self::valuesFor($record), 'queuedAt'=>date(DATE_ATOM), 'version'=>bin2hex(random_bytes(8))];
        $storage->write('anime-sheet-writeback.json', $queue);
        return 'Pendiente';
    }
}
