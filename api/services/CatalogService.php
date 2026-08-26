<?php

final class CatalogService
{
    private const FILES = [
        'movies' => 'peliculas.json',
        'series' => 'series.json',
        'anime' => 'anime.json',
    ];

    private JsonStorage $storage;

    public function __construct(JsonStorage $storage)
    {
        $this->storage = $storage;
    }

    public function all(): array
    {
        $items = [];

        foreach (self::FILES as $file) {
            $items = array_merge($items, $this->storage->read($file));
        }

        return array_values(array_filter($items, fn(array $item): bool => ($item['status'] ?? '') !== 'Oculto'));
    }

    public function byType(string $type): array
    {
        $file = $this->fileForType($type);

        return array_values(array_filter(
            $this->storage->read($file),
            fn(array $item): bool => ($item['status'] ?? '') !== 'Oculto'
        ));
    }

    public function find(string $id): ?array
    {
        foreach ($this->all() as $item) {
            if (($item['id'] ?? '') === $id) {
                return $item;
            }
        }

        return null;
    }

    public function create(array $payload): array
    {
        $item = $this->validate($payload);
        $file = $this->fileForType($item['type']);
        $items = $this->storage->read($file);
        $item['id'] = $this->resolveNewId($payload, $item['type']);
        $item['createdAt'] = date(DATE_ATOM);
        $items[] = $item;
        $this->storage->write($file, $items);

        return $item;
    }

    public function update(string $id, array $payload): array
    {
        $current = $this->find($id);

        if ($current === null) {
            throw new ApiException('El contenido solicitado no existe.', 404);
        }

        $next = $this->validate(array_merge($current, $payload));
        $next['id'] = $id;
        $next['updatedAt'] = date(DATE_ATOM);
        $oldFile = $this->fileForType($current['type']);
        $newFile = $this->fileForType($next['type']);

        $oldItems = array_values(array_filter(
            $this->storage->read($oldFile),
            fn(array $item): bool => ($item['id'] ?? '') !== $id
        ));
        $this->storage->write($oldFile, $oldItems);

        $newItems = $oldFile === $newFile ? $oldItems : $this->storage->read($newFile);
        $newItems[] = $next;
        $this->storage->write($newFile, $newItems);

        return $next;
    }

    public function delete(string $id): void
    {
        $current = $this->find($id);

        if ($current === null) {
            throw new ApiException('El contenido solicitado no existe.', 404);
        }

        $file = $this->fileForType($current['type']);
        $items = $this->storage->read($file);

        foreach ($items as &$item) {
            if (($item['id'] ?? '') === $id) {
                $item['status'] = 'Oculto';
                $item['hiddenAt'] = date(DATE_ATOM);
                break;
            }
        }
        unset($item);

        $this->storage->write($file, $items);
    }

    public function importExternal(string $id, array $payload): array
    {
        $existing = $this->find($id);

        if ($existing !== null) {
            return $existing;
        }

        $source = (string) ($payload['source'] ?? '');
        $type = (string) ($payload['type'] ?? '');
        $title = trim((string) ($payload['title'] ?? ''));

        if (!in_array($source, ['watchmode', 'jikan', 'anilist', 'kitsu'], true)) {
            throw new ApiException('El proveedor externo no es válido.');
        }

        if (!array_key_exists($type, self::FILES) || $title === '') {
            throw new ApiException('El resultado externo no contiene información válida.');
        }

        if (($source === 'watchmode' && !str_starts_with($id, 'watchmode-'))
            || ($source === 'jikan' && !str_starts_with($id, 'jikan-'))
            || ($source === 'anilist' && !str_starts_with($id, 'anilist-'))
            || ($source === 'kitsu' && !str_starts_with($id, 'kitsu-'))) {
            throw new ApiException('El identificador externo no coincide con su proveedor.');
        }

        $image = trim((string) ($payload['image'] ?? ''));
        if ($image !== '' && (!filter_var($image, FILTER_VALIDATE_URL) || !str_starts_with($image, 'https://'))) {
            $image = '';
        }

        $item = array_merge($payload, [
            'id' => $id,
            'title' => $title,
            'type' => $type,
            'categoryGeneral' => $type === 'anime' ? 'Anime' : ($type === 'movies' ? 'Películas' : 'Series TV'),
            'genre' => trim((string) ($payload['genre'] ?? 'General')) ?: 'General',
            'tags' => array_values(array_filter($payload['tags'] ?? [], 'is_string')),
            'image' => $image,
            'status' => 'Activo',
            'importedAt' => date(DATE_ATOM),
        ]);
        $file = $this->fileForType($type);
        $items = $this->storage->read($file);
        $items[] = $item;
        $this->storage->write($file, $items);

        return $item;
    }

    private function validate(array $payload): array
    {
        $title = trim((string) ($payload['title'] ?? ''));
        $type = (string) ($payload['type'] ?? '');
        $genre = trim((string) ($payload['genre'] ?? ''));
        $emissionYear = (int) ($payload['emissionYear'] ?? $payload['year'] ?? 0);
        $emissionSeason = (string) ($payload['emissionSeason'] ?? '');
        $seasonNumber = (int) ($payload['seasonsCount'] ?? 0);
        $allowedEmissionSeasons = ['Winter', 'Spring', 'Summer', 'Fall'];
        $currentYear = (int) date('Y');

        if ($title === '') {
            throw new ApiException('El título es obligatorio.');
        }

        if (!array_key_exists($type, self::FILES)) {
            throw new ApiException('La categoría general no es válida.');
        }

        if ($genre === '') {
            throw new ApiException('El género principal es obligatorio.');
        }

        if ($emissionYear < 1900 || $emissionYear > $currentYear + 2) {
            throw new ApiException("El año de emisión debe estar entre 1900 y " . ($currentYear + 2) . '.');
        }

        if (!in_array($emissionSeason, $allowedEmissionSeasons, true)) {
            throw new ApiException('Seleccione una temporada de emisión válida.');
        }

        if ($seasonNumber < 1) {
            throw new ApiException('N. temporada debe ser un número mayor o igual a 1.');
        }

        return array_merge($payload, [
            'title' => $title,
            'type' => $type,
            'genre' => $genre,
            'year' => (string) $emissionYear,
            'emissionYear' => $emissionYear,
            'emissionSeason' => $emissionSeason,
            'seasonsCount' => $seasonNumber,
            'tags' => array_values(array_filter($payload['tags'] ?? [], 'is_string')),
            'status' => $payload['status'] ?? 'Activo',
        ]);
    }

    private function fileForType(string $type): string
    {
        return self::FILES[$type] ?? throw new ApiException('Tipo de contenido no válido.');
    }

    private function makeId(string $type): string
    {
        return rtrim($type, 's') . '-' . bin2hex(random_bytes(8));
    }

    private function resolveNewId(array $payload, string $type): string
    {
        $candidate = trim((string) ($payload['id'] ?? ''));

        if ($candidate === '') {
            return $this->makeId($type);
        }

        if ($this->find($candidate) !== null) {
            throw new ApiException('Ya existe contenido con ese identificador.', 409);
        }

        return $candidate;
    }
}
