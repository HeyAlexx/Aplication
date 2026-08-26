<?php

final class WatchmodeService
{
    private string $apiKey;
    private string $baseUrl;

    public function __construct(string $apiKey, string $baseUrl)
    {
        $this->apiKey = trim($apiKey);
        $this->baseUrl = rtrim($baseUrl, '/');
    }

    public function isConfigured(): bool
    {
        return $this->apiKey !== '';
    }

    public function search(string $type, string $query): array
    {
        $query = trim($query);

        if (!in_array($type, ['movies', 'series'], true)) {
            throw new ApiException('Watchmode solo se utiliza para películas y series.');
        }

        if (mb_strlen($query) < 2) {
            throw new ApiException('Escriba al menos dos caracteres para buscar.');
        }

        if (!$this->isConfigured()) {
            throw new ApiException('Watchmode no está configurado.', 503);
        }

        $searchType = $type === 'movies' ? 3 : 4;
        $url = $this->baseUrl . '/autocomplete-search/?' . http_build_query([
            'search_value' => $query,
            'search_type' => $searchType,
        ]);
        $payload = $this->request($url);

        return array_values(array_map(
            fn(array $item): array => $this->normalizeResult($item, $type),
            array_slice(array_filter(
                $payload['results'] ?? [],
                fn($item): bool => is_array($item) && ($item['result_type'] ?? 'title') === 'title'
            ),
            0,
            20)
        ));
    }

    public function searchAnime(string $query): array
    {
        $series = $this->search('series', $query);
        $movies = $this->search('movies', $query);
        $results = [];

        foreach (array_merge($series, $movies) as $item) {
            $providerId = (string) ($item['watchmodeId'] ?? '');
            $format = ($item['type'] ?? '') === 'movies' ? 'Película' : 'Serie';
            $item['id'] = 'watchmode-anime-' . $providerId;
            $item['type'] = 'anime';
            $item['categoryGeneral'] = 'Anime';
            $item['format'] = $format;
            $item['genre'] = 'Anime';
            $item['tags'] = ['Anime', 'Watchmode', $format];
            $item['description'] = 'Resultado de respaldo obtenido mediante Watchmode para la búsqueda de anime.';
            $results[$item['id']] = $item;
        }

        return array_values(array_slice($results, 0, 20, true));
    }

    private function request(string $url): array
    {
        $handle = curl_init($url);

        if ($handle === false) {
            throw new ApiException('No se pudo iniciar la conexión con Watchmode.', 502);
        }

        curl_setopt_array($handle, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 12,
            CURLOPT_HTTPHEADER => [
                'Accept: application/json',
                'X-API-Key: ' . $this->apiKey,
                'User-Agent: Altoidss/1.0 (academic project)',
            ],
        ]);

        $body = curl_exec($handle);
        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        $curlCode = curl_errno($handle);
        $curlError = curl_error($handle);
        curl_close($handle);

        if ($body === false || $curlError !== '') {
            error_log(sprintf('Watchmode cURL error %d: %s', $curlCode, $curlError));
            throw new ApiException(sprintf('Watchmode no está disponible en este momento (cURL %d).', $curlCode), 502);
        }

        try {
            $payload = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $error) {
            throw new ApiException('Watchmode devolvió una respuesta inválida.', 502);
        }

        if ($status < 200 || $status >= 300) {
            $message = $status === 401
                ? 'La clave de Watchmode no fue aceptada.'
                : 'Watchmode no pudo completar la búsqueda.';
            throw new ApiException($message, $status === 429 ? 429 : 502);
        }

        return $payload;
    }

    private function normalizeResult(array $item, string $type): array
    {
        $id = (string) ($item['id'] ?? '');
        $year = (int) ($item['year'] ?? 0);

        return [
            'id' => 'watchmode-' . $id,
            'watchmodeId' => $id,
            'title' => trim((string) ($item['name'] ?? 'Título sin nombre')),
            'type' => $type,
            'format' => $type === 'movies' ? 'Película' : 'Serie TV',
            'genre' => $type === 'movies' ? 'Película' : 'Serie',
            'year' => $year > 0 ? (string) $year : '',
            'emissionYear' => $year > 0 ? $year : null,
            'tags' => ['Watchmode'],
            'image' => (string) ($item['image_url'] ?? ''),
            'description' => 'Resultado externo obtenido mediante Watchmode.',
            'source' => 'watchmode',
            'status' => 'Activo',
        ];
    }
}
