<?php

final class NewsService
{
    private JsonStorage $storage;

    public function __construct(JsonStorage $storage)
    {
        $this->storage = $storage;
    }

    public function all(): array
    {
        return array_values(array_filter(
            $this->storage->read('noticias.json'),
            fn(array $item): bool => ($item['visibilityStatus'] ?? 'Visible') !== 'Oculto'
        ));
    }

    public function create(array $payload): array
    {
        $item = $this->validate($payload);
        $item['id'] = $payload['id'] ?? 'news-' . bin2hex(random_bytes(8));
        $item['createdAt'] = date(DATE_ATOM);
        $items = $this->storage->read('noticias.json');
        $items[] = $item;
        $this->storage->write('noticias.json', $items);
        return $item;
    }

    public function update(string $id, array $payload): array
    {
        $items = $this->storage->read('noticias.json');
        $found = false;
        $updated = [];

        foreach ($items as &$item) {
            if (($item['id'] ?? '') === $id && ($item['visibilityStatus'] ?? 'Visible') !== 'Oculto') {
                $item = $this->validate(array_merge($item, $payload));
                $item['id'] = $id;
                $item['updatedAt'] = date(DATE_ATOM);
                $updated = $item;
                $found = true;
                break;
            }
        }
        unset($item);

        if (!$found) {
            throw new ApiException('La noticia solicitada no existe.', 404);
        }

        $this->storage->write('noticias.json', $items);
        return $updated;
    }

    public function delete(string $id): void
    {
        $items = $this->storage->read('noticias.json');
        $found = false;

        foreach ($items as &$item) {
            if (($item['id'] ?? '') === $id && ($item['visibilityStatus'] ?? 'Visible') !== 'Oculto') {
                $item['visibilityStatus'] = 'Oculto';
                $item['hiddenAt'] = date(DATE_ATOM);
                $found = true;
                break;
            }
        }
        unset($item);

        if (!$found) {
            throw new ApiException('La noticia solicitada no existe.', 404);
        }

        $this->storage->write('noticias.json', $items);
    }

    private function validate(array $payload): array
    {
        $title = trim((string) ($payload['title'] ?? ''));

        if ($title === '') {
            throw new ApiException('El título de la noticia es obligatorio.');
        }

        $allowedStatuses = ['borrador', 'publicada', 'archivada'];
        $status = (string) ($payload['status'] ?? 'borrador');

        if (!in_array($status, $allowedStatuses, true)) {
            throw new ApiException('El estado editorial no es válido.');
        }

        $trailerUrl = trim((string) ($payload['trailerUrl'] ?? ''));

        if ($trailerUrl !== '') {
            $host = strtolower((string) parse_url($trailerUrl, PHP_URL_HOST));
            $allowedVideoHosts = ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'youtube-nocookie.com', 'www.youtube-nocookie.com'];

            if (!filter_var($trailerUrl, FILTER_VALIDATE_URL) || !in_array($host, $allowedVideoHosts, true)) {
                throw new ApiException('El tráiler debe usar una URL válida de YouTube.');
            }
        }

        return array_merge($payload, [
            'title' => $title,
            'status' => $status,
            'trailerUrl' => $trailerUrl,
            'trailerLabel' => trim((string) ($payload['trailerLabel'] ?? 'Tráiler oficial')),
            'relatedContent' => array_values(array_filter($payload['relatedContent'] ?? [], 'is_string')),
        ]);
    }
}
