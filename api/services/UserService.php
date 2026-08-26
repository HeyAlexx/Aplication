<?php

final class UserService
{
    private JsonStorage $storage;
    private CatalogService $catalog;

    public function __construct(JsonStorage $storage, CatalogService $catalog)
    {
        $this->storage = $storage;
        $this->catalog = $catalog;
    }

    public function profile(array $session): array
    {
        if (!($session['isAuthenticated'] ?? false)) {
            return $this->visitorProfile();
        }

        $profile = $this->findByUser('perfiles.json', $session['id']) ?? [];
        $settings = $this->settings($session);
        $favorites = $this->favoriteItems($session['id']);
        $history = $this->historyFor($session['id']);

        return array_merge([
            'id' => $session['id'],
            'role' => $session['role'],
            'displayName' => $session['name'],
            'email' => $session['email'],
            'socialLinks' => '',
            'about' => '',
            'avatar' => '',
            'lastVisit' => 'Hoy',
        ], $profile, [
            'id' => $session['id'],
            'role' => $session['role'],
            'settings' => $settings,
            'favoriteIds' => array_values(array_column($favorites, 'id')),
            'favoriteItems' => $this->indexById($favorites),
            'seenIds' => array_values(array_map(
                fn(array $row): string => (string) $row['contentId'],
                array_filter($history, fn(array $row): bool => (bool) ($row['watched'] ?? false))
            )),
            'watchTimeMinutes' => array_sum(array_column($history, 'minutes')),
        ]);
    }

    public function updateProfile(array $session, array $payload): array
    {
        $records = $this->storage->read('perfiles.json');
        $updated = [
            'userId' => $session['id'],
            'displayName' => trim((string) ($payload['displayName'] ?? $session['name'])),
            'email' => trim((string) ($payload['email'] ?? $session['email'])),
            'socialLinks' => trim((string) ($payload['socialLinks'] ?? '')),
            'about' => trim((string) ($payload['about'] ?? '')),
            'avatar' => trim((string) ($payload['avatar'] ?? '')),
            'lastVisit' => 'Hoy',
            'updatedAt' => date(DATE_ATOM),
        ];
        $records = $this->upsertByUser($records, $updated);
        $this->storage->write('perfiles.json', $records);
        return $this->profile($session);
    }

    public function settings(array $session): array
    {
        if (!($session['isAuthenticated'] ?? false)) {
            return ['cardsPerRow' => 5, 'preferredView' => 'cards', 'compactMode' => false];
        }

        return array_merge(
            ['cardsPerRow' => 5, 'preferredView' => 'cards', 'compactMode' => false],
            $this->findByUser('configuraciones.json', $session['id']) ?? []
        );
    }

    public function updateSettings(array $session, array $payload): array
    {
        $cardsPerRow = (int) ($payload['cardsPerRow'] ?? 5);

        if (!in_array($cardsPerRow, [3, 5, 7], true)) {
            throw new ApiException('La cantidad de tarjetas debe ser 3, 5 o 7.');
        }

        $settings = [
            'userId' => $session['id'],
            'cardsPerRow' => $cardsPerRow,
            'preferredView' => (string) ($payload['preferredView'] ?? 'cards'),
            'compactMode' => (bool) ($payload['compactMode'] ?? false),
            'updatedAt' => date(DATE_ATOM),
        ];
        $records = $this->upsertByUser($this->storage->read('configuraciones.json'), $settings);
        $this->storage->write('configuraciones.json', $records);
        return $settings;
    }

    public function favorites(array $session): array
    {
        return $this->favoriteItems($session['id']);
    }

    public function addFavorite(array $session, string $contentId, array $contentPayload = []): array
    {
        $content = $this->catalog->find($contentId);

        if ($content === null && $contentPayload !== []) {
            $content = $this->catalog->importExternal($contentId, $contentPayload);
        }

        if ($content === null) {
            throw new ApiException('El contenido no existe.', 404);
        }

        $records = $this->storage->read('favoritos.json');
        $exists = array_filter($records, fn(array $row): bool =>
            ($row['userId'] ?? '') === $session['id'] && ($row['contentId'] ?? '') === $contentId
        );

        if (!$exists) {
            $records[] = ['userId' => $session['id'], 'contentId' => $contentId, 'createdAt' => date(DATE_ATOM)];
            $this->storage->write('favoritos.json', $records);
        }

        return $this->favorites($session);
    }

    public function removeFavorite(array $session, string $contentId): array
    {
        $records = array_values(array_filter(
            $this->storage->read('favoritos.json'),
            fn(array $row): bool => !(($row['userId'] ?? '') === $session['id'] && ($row['contentId'] ?? '') === $contentId)
        ));
        $this->storage->write('favoritos.json', $records);
        return $this->favorites($session);
    }

    public function updateViewing(array $session, string $contentId, array $payload): array
    {
        if ($this->catalog->find($contentId) === null) {
            throw new ApiException('El contenido no existe.', 404);
        }

        $records = $this->storage->read('historial.json');
        $watched = (bool) ($payload['watched'] ?? true);
        $hasMinutes = array_key_exists('minutes', $payload);
        $row = [
            'userId' => $session['id'],
            'contentId' => $contentId,
            'watched' => $watched,
            'minutes' => $hasMinutes ? max(0, (int) $payload['minutes']) : 0,
            'watchedAt' => $watched ? date(DATE_ATOM) : null,
            'updatedAt' => date(DATE_ATOM),
        ];
        $found = false;

        foreach ($records as &$record) {
            if (($record['userId'] ?? '') === $session['id'] && ($record['contentId'] ?? '') === $contentId) {
                if (!$hasMinutes) {
                    $row['minutes'] = max(0, (int) ($record['minutes'] ?? 0));
                }
                if ($watched && !empty($record['watchedAt'])) {
                    $row['watchedAt'] = $record['watchedAt'];
                }
                $record = array_merge($record, $row);
                $found = true;
                break;
            }
        }
        unset($record);

        if (!$found) {
            $records[] = $row;
        }

        $this->storage->write('historial.json', $records);
        return $this->profile($session);
    }

    public function dashboard(array $session): array
    {
        $profile = $this->profile($session);
        $items = $this->catalog->all();
        $seenSet = array_flip($profile['seenIds']);
        $seenItems = array_values(array_filter($items, fn(array $item): bool => isset($seenSet[$item['id'] ?? ''])));
        $favoriteItems = array_values($profile['favoriteItems'] ?? []);
        $genreCounts = [];

        foreach ($seenItems as $item) {
            $genre = $item['genre'] ?? 'General';
            $genreCounts[$genre] = ($genreCounts[$genre] ?? 0) + 1;
        }
        arsort($genreCounts);

        return [
            'profile' => $profile,
            'totalContent' => count($items),
            'seenTotal' => count($seenItems),
            'favoriteTotal' => count($profile['favoriteIds']),
            'moviesSeen' => $this->countType($seenItems, 'movies'),
            'seriesSeen' => $this->countType($seenItems, 'series'),
            'animeSeen' => $this->countType($seenItems, 'anime'),
            'favoriteMovies' => $this->countType($favoriteItems, 'movies'),
            'favoriteSeries' => $this->countType($favoriteItems, 'series'),
            'favoriteAnime' => $this->countType($favoriteItems, 'anime'),
            'topGenre' => array_key_first($genreCounts) ?? 'Sin datos',
            'lastVisit' => $profile['lastVisit'],
            'watchTimeMinutes' => $profile['watchTimeMinutes'],
        ];
    }

    private function favoriteItems(string $userId): array
    {
        $favoriteIds = array_column(array_filter(
            $this->storage->read('favoritos.json'),
            fn(array $row): bool => ($row['userId'] ?? '') === $userId
        ), 'contentId');
        $wanted = array_flip($favoriteIds);
        return array_values(array_filter($this->catalog->all(), fn(array $item): bool => isset($wanted[$item['id'] ?? ''])));
    }

    private function historyFor(string $userId): array
    {
        return array_values(array_filter(
            $this->storage->read('historial.json'),
            fn(array $row): bool => ($row['userId'] ?? '') === $userId
        ));
    }

    private function findByUser(string $file, string $userId): ?array
    {
        foreach ($this->storage->read($file) as $record) {
            if (($record['userId'] ?? '') === $userId) {
                return $record;
            }
        }
        return null;
    }

    private function upsertByUser(array $records, array $updated): array
    {
        $found = false;
        foreach ($records as &$record) {
            if (($record['userId'] ?? '') === $updated['userId']) {
                $record = array_merge($record, $updated);
                $found = true;
                break;
            }
        }
        unset($record);
        if (!$found) {
            $records[] = $updated;
        }
        return $records;
    }

    private function indexById(array $items): array
    {
        $indexed = [];
        foreach ($items as $item) {
            $indexed[$item['id']] = $item;
        }
        return $indexed;
    }

    private function countType(array $items, string $type): int
    {
        return count(array_filter($items, fn(array $item): bool => ($item['type'] ?? '') === $type));
    }

    private function visitorProfile(): array
    {
        return [
            'id' => 'visitor', 'role' => 'visitante', 'displayName' => 'Visitante', 'email' => '',
            'socialLinks' => '', 'about' => 'Explora el catálogo antes de crear una cuenta.', 'avatar' => '',
            'lastVisit' => 'Sesión actual', 'watchTimeMinutes' => 0, 'seenIds' => [], 'favoriteIds' => [],
            'favoriteItems' => [], 'settings' => $this->settings(['isAuthenticated' => false]),
        ];
    }
}
