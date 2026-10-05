<?php

final class AnimeReviewService
{
    private const FILE = 'anime-revisiones.json';
    private const ANIME_FILE = 'anime.json';
    private const WRITEBACK_FILE = 'anime-sheet-writeback.json';

    private JsonStorage $storage;

    public function __construct(JsonStorage $storage)
    {
        $this->storage = $storage;
    }

    public function all(): array
    {
        $reviews = $this->storage->read(self::FILE);
        usort($reviews, static function (array $left, array $right): int {
            $priority = ['Pendiente' => 0, 'Rechazado automático' => 1, 'Aprobado' => 2, 'Rechazado' => 3];
            return ($priority[$left['status'] ?? 'Pendiente'] ?? 9) <=> ($priority[$right['status'] ?? 'Pendiente'] ?? 9);
        });

        return $reviews;
    }

    public function decide(string $id, array $payload, array $session): array
    {
        $decision = strtolower(trim((string) ($payload['decision'] ?? '')));
        if (!in_array($decision, ['approve', 'save', 'reject'], true)) {
            throw new ApiException('La decisión de revisión no es válida.');
        }

        $reviews = $this->storage->read(self::FILE);
        $reviewIndex = $this->findIndex($reviews, $id);
        if ($reviewIndex === null) {
            throw new ApiException('La revisión solicitada no existe.', 404);
        }

        if ($decision === 'approve') {
            $finalVersion = $this->normalizeVersion($reviews[$reviewIndex]['apiVersion'] ?? []);
            $updatedRecord = $this->applyVersion($reviews[$reviewIndex], $finalVersion);
            $reviews[$reviewIndex]['finalVersion'] = $finalVersion;
        } elseif ($decision === 'save') {
            $finalVersion = $this->normalizeVersion($payload['finalData'] ?? []);
            $updatedRecord = $this->applyVersion($reviews[$reviewIndex], $finalVersion);
            $reviews[$reviewIndex]['finalVersion'] = $finalVersion;
        }

        $reviews[$reviewIndex]['status'] = $decision === 'reject' ? 'Rechazado' : 'Aprobado';
        $reviews[$reviewIndex]['resolutionType'] = $decision === 'save' ? 'Combinación manual' : ($decision === 'approve' ? 'Versión API' : 'Rechazo');
        $reviews[$reviewIndex]['reviewNotes'] = trim((string) ($payload['notes'] ?? ''));
        $reviews[$reviewIndex]['reviewedAt'] = date(DATE_ATOM);
        $reviews[$reviewIndex]['reviewedBy'] = (string) ($session['displayName'] ?? $session['email'] ?? 'Administrador');
        $this->storage->write(self::FILE, $reviews);
        if ($decision !== 'reject') {
            $this->queueSheetWriteback($updatedRecord ?? []);
        }

        return $reviews[$reviewIndex];
    }

    public function sourceCandidate(string $id, ?array $candidate): ?array
    {
        if ($candidate === null) {
            return null;
        }
        $reviewIndex = $this->findIndex($this->storage->read(self::FILE), $id);
        if ($reviewIndex === null) {
            throw new ApiException('La revisión solicitada no existe.', 404);
        }
        $reviews = $this->storage->read(self::FILE);
        $review = $reviews[$reviewIndex];
        $expected = $this->searchableTitle((string) ($review['title'] ?? $review['original']['title'] ?? ''));
        $candidateTitles = array_merge(
            [(string) ($candidate['title'] ?? '')],
            is_array($candidate['alternativeTitles'] ?? null) ? $candidate['alternativeTitles'] : []
        );
        foreach ($candidateTitles as $title) {
            $actual = $this->searchableTitle((string) $title);
            similar_text($expected, $actual, $similarity);
            $shared = array_intersect(
                preg_split('/\s+/', $expected, -1, PREG_SPLIT_NO_EMPTY),
                preg_split('/\s+/', $actual, -1, PREG_SPLIT_NO_EMPTY)
            );
            if ($expected !== '' && ($expected === $actual || $similarity >= 45 || count($shared) >= 2)) {
                return $candidate;
            }
        }
        return null;
    }

    private function searchableTitle(string $value): string
    {
        $value = mb_strtolower($value);
        $value = preg_replace('/[^\p{L}\p{N}]+/u', ' ', $value) ?? '';
        return trim($value);
    }

    private function applyVersion(array $review, array $version): array
    {
        $items = $this->storage->read(self::ANIME_FILE);
        $contentId = (string) ($review['contentId'] ?? '');
        $sourceCode = (string) ($review['sourceCode'] ?? '');
        $itemIndex = null;

        foreach ($items as $index => $item) {
            if (($contentId !== '' && ($item['id'] ?? '') === $contentId)
                || ($sourceCode !== '' && (string) ($item['sourceCode'] ?? '') === $sourceCode)) {
                $itemIndex = $index;
                break;
            }
        }

        if ($itemIndex === null) {
            $itemId = $contentId !== '' ? $contentId : ($sourceCode !== '' ? 'anime-sheet-' . $sourceCode : '');
            if ($itemId === '') {
                throw new ApiException('La revisión no contiene un identificador de anime válido.');
            }

            $original = is_array($review['original'] ?? null) ? $review['original'] : [];
            $items[] = array_merge($original, [
                'id' => $itemId,
                'sourceCode' => $sourceCode,
                'type' => 'anime',
                'categoryGeneral' => 'Anime',
                'viewingStatus' => (string) ($original['viewingStatus'] ?? 'No Visto'),
                'featured' => false,
                'status' => 'Activo',
                'source' => 'google-sheet-anime',
                'sheetUpdatedAt' => date(DATE_ATOM),
                'createdAt' => date(DATE_ATOM),
            ]);
            $itemIndex = array_key_last($items);
        }

        foreach ($version as $field => $value) {
            $items[$itemIndex][$field] = $value;
        }

        if (!empty($items[$itemIndex]['emissionYear'])) {
            $items[$itemIndex]['year'] = (string) $items[$itemIndex]['emissionYear'];
        }
        $items[$itemIndex]['tags'] = array_values(array_filter([
            $items[$itemIndex]['format'] ?? '',
            $items[$itemIndex]['viewingStatus'] ?? '',
            $items[$itemIndex]['productionStatus'] ?? '',
        ]));
        $items[$itemIndex]['metadataVerified'] = true;
        $items[$itemIndex]['metadataNeedsReview'] = false;
        $items[$itemIndex]['metadataUpdatedAt'] = date(DATE_ATOM);
        $this->storage->write(self::ANIME_FILE, $items);
        return $items[$itemIndex];
    }

    private function queueSheetWriteback(array $record): void
    {
        $sourceCode = trim((string) ($record['sourceCode'] ?? ''));
        $targetRow = (int) ($record['sourceRow'] ?? 0);
        if ($sourceCode === '' || $targetRow < 2) {
            return;
        }

        $quarter = ['Winter' => 1, 'Spring' => 2, 'Summer' => 3, 'Fall' => 4][(string) ($record['emissionSeason'] ?? '')] ?? '';
        $values = [
            $sourceCode,
            (string) ($record['title'] ?? ''),
            ($record['productionStatus'] ?? '') === 'Emisión' ? 'Emision' : (string) ($record['productionStatus'] ?? ''),
            ($record['format'] ?? '') === 'Película' ? 'Movie' : (string) ($record['format'] ?? ''),
            (int) ($record['chapters'] ?? 0),
            (int) ($record['seasonsCount'] ?? 0),
            (string) ($record['activeSeason'] ?? ''),
            ($record['viewingStatus'] ?? '') === 'No Visto' ? 'No visto' : (string) ($record['viewingStatus'] ?? ''),
            (int) ($record['emissionYear'] ?? 0) ?: '',
            $quarter,
        ];
        $queue = $this->storage->read(self::WRITEBACK_FILE);
        $queue = array_values(array_filter($queue, static fn (array $item): bool => (string) ($item['sourceCode'] ?? '') !== $sourceCode));
        $queue[] = ['sourceCode' => $sourceCode, 'targetRow' => $targetRow, 'values' => $values, 'queuedAt' => date(DATE_ATOM)];
        $this->storage->write(self::WRITEBACK_FILE, $queue);
    }

    private function normalizeVersion(mixed $version): array
    {
        if (!is_array($version) || $version === []) {
            throw new ApiException('Debe completar la versión final antes de guardarla.');
        }

        $allowed = [
            'title', 'alternativeTitles', 'format', 'productionStatus', 'chapters', 'seasonsCount',
            'activeSeason', 'emissionYear', 'emissionSeason', 'genre', 'metadataGenres', 'rating',
            'image', 'description', 'sourceUrl', 'externalTitle', 'metadataProvider',
            'metadataMatchScore', 'jikanId', 'anilistId', 'kitsuId',
        ];
        $normalized = [];

        foreach ($allowed as $field) {
            if (!array_key_exists($field, $version)) {
                continue;
            }

            $value = $version[$field];
            if (in_array($field, ['alternativeTitles', 'metadataGenres'], true)) {
                if (!is_array($value)) {
                    throw new ApiException("El campo {$field} debe ser una lista.");
                }
                $normalized[$field] = array_values(array_unique(array_filter(array_map(
                    static fn ($item): string => trim((string) $item),
                    $value
                ))));
                continue;
            }

            if (in_array($field, ['chapters', 'seasonsCount', 'emissionYear'], true)) {
                if ($value === '' || $value === null) {
                    $normalized[$field] = 0;
                    continue;
                }
                if (filter_var($value, FILTER_VALIDATE_INT) === false || (int) $value < 0) {
                    throw new ApiException("El campo {$field} debe ser un número entero positivo.");
                }
                $normalized[$field] = (int) $value;
                continue;
            }

            if (in_array($field, ['rating', 'metadataMatchScore'], true)) {
                if ($value === '' || $value === null) {
                    $normalized[$field] = 0;
                    continue;
                }
                if (!is_numeric($value)) {
                    throw new ApiException("El campo {$field} debe ser numérico.");
                }
                $normalized[$field] = (float) $value;
                continue;
            }

            $normalized[$field] = trim((string) $value);
        }

        if (($normalized['title'] ?? '') === '') {
            throw new ApiException('El título final es obligatorio.');
        }

        foreach (['image', 'sourceUrl'] as $urlField) {
            $url = $normalized[$urlField] ?? '';
            if ($url !== '' && filter_var($url, FILTER_VALIDATE_URL) === false) {
                throw new ApiException("El campo {$urlField} debe contener una URL válida.");
            }
        }

        if (($normalized['rating'] ?? 0) < 0 || ($normalized['rating'] ?? 0) > 10) {
            throw new ApiException('La calificación debe estar entre 0 y 10.');
        }

        return $normalized;
    }

    private function findIndex(array $reviews, string $id): ?int
    {
        foreach ($reviews as $index => $review) {
            if (($review['id'] ?? '') === $id) {
                return $index;
            }
        }

        return null;
    }
}
