<?php

final class JikanService
{
    private string $baseUrl;
    private string $anilistBaseUrl;
    private string $kitsuBaseUrl;

    public function __construct(string $baseUrl, string $anilistBaseUrl, string $kitsuBaseUrl)
    {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->anilistBaseUrl = rtrim($anilistBaseUrl, '/');
        $this->kitsuBaseUrl = rtrim($kitsuBaseUrl, '/');
    }

    public function search(string $query): array
    {
        $query = trim($query);

        if (mb_strlen($query) < 2) {
            throw new ApiException('Escriba al menos dos caracteres para buscar anime.');
        }

        $url = $this->baseUrl . '/anime?' . http_build_query([
            'q' => $query,
            'limit' => 20,
            'sfw' => 'true',
        ]);
        try {
            $payload = $this->request($url);

            return array_values(array_map(
                fn(array $item): array => $this->normalizeResult($item),
                array_filter($payload['data'] ?? [], 'is_array')
            ));
        } catch (ApiException $error) {
            error_log('Jikan no disponible; se usará AniList como respaldo: ' . $error->getMessage());
            try {
                return $this->searchAniList($query);
            } catch (ApiException $fallbackError) {
                error_log('AniList no disponible; se usará Kitsu como respaldo: ' . $fallbackError->getMessage());
                return $this->searchKitsuOnly($query);
            }
        }
    }

    public function searchKitsuOnly(string $query): array
    {
        $query = trim($query);

        if (mb_strlen($query) < 2) {
            throw new ApiException('Escriba al menos dos caracteres para buscar anime.');
        }

        $url = $this->kitsuBaseUrl . '/anime?' . http_build_query([
            'filter[text]' => $query,
            'page[limit]' => 20,
            'include' => 'categories',
        ]);
        $payload = $this->requestGet($url, 'Kitsu');
        $categories = [];

        foreach (array_filter($payload['included'] ?? [], 'is_array') as $included) {
            if (($included['type'] ?? '') !== 'categories') {
                continue;
            }

            $categoryName = trim((string) ($included['attributes']['title'] ?? ''));
            if ($categoryName !== '') {
                $categories[(string) ($included['id'] ?? '')] = $categoryName;
            }
        }

        return array_values(array_map(
            fn(array $item): array => $this->normalizeKitsuResult($item, $categories),
            array_filter($payload['data'] ?? [], 'is_array')
        ));
    }

    private function searchAniList(string $query): array
    {
        $graphql = <<<'GRAPHQL'
query ($search: String!, $page: Int!, $perPage: Int!) {
  Page(page: $page, perPage: $perPage) {
    media(search: $search, type: ANIME, isAdult: false) {
      id
      idMal
      title { romaji english native }
      format
      status
      episodes
      season
      seasonYear
      genres
      description(asHtml: false)
      averageScore
      siteUrl
      coverImage { extraLarge large medium }
    }
  }
}
GRAPHQL;
        $payload = $this->requestJson($this->anilistBaseUrl, [
            'query' => $graphql,
            'variables' => ['search' => $query, 'page' => 1, 'perPage' => 20],
        ], 'AniList');

        return array_values(array_map(
            fn(array $item): array => $this->normalizeAniListResult($item),
            array_filter($payload['data']['Page']['media'] ?? [], 'is_array')
        ));
    }

    private function request(string $url): array
    {
        $handle = curl_init($url);

        if ($handle === false) {
            throw new ApiException('No se pudo iniciar la conexión con Jikan.', 502);
        }

        curl_setopt_array($handle, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 12,
            CURLOPT_HTTPHEADER => [
                'Accept: application/json',
                'User-Agent: Altoidss/1.0 (academic project)',
            ],
        ]);

        $body = curl_exec($handle);
        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        $curlCode = curl_errno($handle);
        $curlError = curl_error($handle);
        curl_close($handle);

        if ($body === false || $curlError !== '') {
            error_log(sprintf('Jikan cURL error %d: %s', $curlCode, $curlError));
            throw new ApiException(sprintf('Jikan no está disponible en este momento (cURL %d).', $curlCode), 502);
        }

        try {
            $payload = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $error) {
            throw new ApiException('Jikan devolvió una respuesta inválida.', 502);
        }

        if ($status < 200 || $status >= 300) {
            throw new ApiException(
                $status === 429 ? 'Jikan alcanzó temporalmente su límite de consultas.' : 'Jikan no pudo completar la búsqueda.',
                $status === 429 ? 429 : 502
            );
        }

        return $payload;
    }

    private function normalizeResult(array $item): array
    {
        $malId = (string) ($item['mal_id'] ?? '');
        $format = $this->normalizeFormat((string) ($item['type'] ?? ''));
        $year = (int) ($item['year'] ?? $item['aired']['prop']['from']['year'] ?? 0);
        $genres = array_values(array_filter(array_map(
            fn($genre): string => is_array($genre) ? trim((string) ($genre['name'] ?? '')) : '',
            array_merge($item['genres'] ?? [], $item['themes'] ?? [], $item['demographics'] ?? [])
        )));
        $image = (string) (
            $item['images']['webp']['large_image_url']
            ?? $item['images']['jpg']['large_image_url']
            ?? $item['images']['jpg']['image_url']
            ?? ''
        );

        return [
            'id' => 'jikan-' . $malId,
            'jikanId' => $malId,
            'title' => trim((string) ($item['title'] ?? 'Anime sin título')),
            'alternativeTitle' => trim((string) ($item['title_english'] ?? '')),
            'type' => 'anime',
            'categoryGeneral' => 'Anime',
            'format' => $format,
            'productionStatus' => $this->normalizeStatus((string) ($item['status'] ?? '')),
            'genre' => $genres[0] ?? 'Anime',
            'year' => $year > 0 ? (string) $year : '',
            'emissionYear' => $year > 0 ? $year : null,
            'emissionSeason' => ucfirst(strtolower((string) ($item['season'] ?? ''))),
            'chapters' => max(0, (int) ($item['episodes'] ?? 0)),
            'seasonsCount' => 1,
            'tags' => array_slice($genres, 1, 3),
            'image' => $image,
            'description' => trim((string) ($item['synopsis'] ?? 'Información obtenida mediante Jikan.')),
            'rating' => isset($item['score']) ? (string) $item['score'] : '',
            'sourceUrl' => (string) ($item['url'] ?? ''),
            'source' => 'jikan',
            'status' => 'Activo',
        ];
    }

    private function normalizeAniListResult(array $item): array
    {
        $anilistId = (string) ($item['id'] ?? '');
        $genres = array_values(array_filter(array_map(
            fn($genre): string => trim((string) $genre),
            $item['genres'] ?? []
        )));
        $year = max(0, (int) ($item['seasonYear'] ?? 0));
        $description = trim(strip_tags(html_entity_decode(
            (string) ($item['description'] ?? ''),
            ENT_QUOTES | ENT_HTML5,
            'UTF-8'
        )));

        return [
            'id' => 'anilist-' . $anilistId,
            'anilistId' => $anilistId,
            'malId' => isset($item['idMal']) ? (string) $item['idMal'] : '',
            'title' => trim((string) ($item['title']['romaji'] ?? $item['title']['english'] ?? 'Anime sin título')),
            'alternativeTitle' => trim((string) ($item['title']['english'] ?? $item['title']['native'] ?? '')),
            'type' => 'anime',
            'categoryGeneral' => 'Anime',
            'format' => $this->normalizeAniListFormat((string) ($item['format'] ?? '')),
            'productionStatus' => $this->normalizeAniListStatus((string) ($item['status'] ?? '')),
            'genre' => $genres[0] ?? 'Anime',
            'year' => $year > 0 ? (string) $year : '',
            'emissionYear' => $year > 0 ? $year : null,
            'emissionSeason' => ucfirst(strtolower((string) ($item['season'] ?? ''))),
            'chapters' => max(0, (int) ($item['episodes'] ?? 0)),
            'seasonsCount' => 1,
            'tags' => array_slice($genres, 1, 3),
            'image' => (string) ($item['coverImage']['extraLarge'] ?? $item['coverImage']['large'] ?? $item['coverImage']['medium'] ?? ''),
            'description' => $description !== '' ? $description : 'Información obtenida mediante AniList.',
            'rating' => isset($item['averageScore']) ? number_format(((float) $item['averageScore']) / 10, 1) : '',
            'sourceUrl' => (string) ($item['siteUrl'] ?? ''),
            'source' => 'anilist',
            'status' => 'Activo',
        ];
    }

    private function normalizeKitsuResult(array $item, array $categoryMap = []): array
    {
        $attributes = is_array($item['attributes'] ?? null) ? $item['attributes'] : [];
        $kitsuId = (string) ($item['id'] ?? '');
        $startDate = (string) ($attributes['startDate'] ?? '');
        $year = preg_match('/^(\d{4})/', $startDate, $matches) ? (int) $matches[1] : 0;
        $month = preg_match('/^\d{4}-(\d{2})/', $startDate, $monthMatches) ? (int) $monthMatches[1] : 0;
        $emissionSeason = match (true) {
            $month >= 1 && $month <= 3 => 'Winter',
            $month >= 4 && $month <= 6 => 'Spring',
            $month >= 7 && $month <= 9 => 'Summer',
            $month >= 10 && $month <= 12 => 'Fall',
            default => '',
        };
        $rating = (float) ($attributes['averageRating'] ?? 0);
        $description = trim((string) ($attributes['synopsis'] ?? $attributes['description'] ?? ''));
        $genres = [];

        foreach ($item['relationships']['categories']['data'] ?? [] as $categoryReference) {
            $categoryId = (string) ($categoryReference['id'] ?? '');
            if (isset($categoryMap[$categoryId])) {
                $genres[] = $categoryMap[$categoryId];
            }
        }

        $slug = trim((string) ($attributes['slug'] ?? ''));

        return [
            'id' => 'kitsu-' . $kitsuId,
            'kitsuId' => $kitsuId,
            'title' => trim((string) ($attributes['canonicalTitle'] ?? 'Anime sin título')),
            'alternativeTitle' => trim((string) ($attributes['titles']['en_jp'] ?? $attributes['titles']['en'] ?? $attributes['titles']['ja_jp'] ?? '')),
            'alternativeTitles' => array_values(array_unique(array_filter(array_map(
                fn($title): string => trim((string) $title),
                is_array($attributes['titles'] ?? null) ? array_values($attributes['titles']) : []
            )))),
            'type' => 'anime',
            'categoryGeneral' => 'Anime',
            'format' => $this->normalizeKitsuFormat((string) ($attributes['subtype'] ?? '')),
            'productionStatus' => $this->normalizeKitsuStatus((string) ($attributes['status'] ?? '')),
            'genre' => $genres[0] ?? 'Anime',
            'year' => $year > 0 ? (string) $year : '',
            'emissionYear' => $year > 0 ? $year : null,
            'emissionSeason' => $emissionSeason,
            'chapters' => max(0, (int) ($attributes['episodeCount'] ?? 0)),
            'seasonsCount' => 1,
            'tags' => array_slice(array_values(array_filter(array_merge(array_slice($genres, 1, 3), [
                isset($attributes['ageRating']) ? (string) $attributes['ageRating'] : '',
                isset($attributes['showType']) ? (string) $attributes['showType'] : '',
            ]))), 0, 3),
            'image' => (string) ($attributes['posterImage']['original'] ?? $attributes['posterImage']['large'] ?? $attributes['posterImage']['medium'] ?? ''),
            'description' => $description !== '' ? $description : 'Información obtenida mediante Kitsu.',
            'rating' => $rating > 0 ? number_format($rating / 10, 1) : '',
            'sourceUrl' => $slug !== '' ? 'https://kitsu.app/anime/' . rawurlencode($slug) : (string) ($item['links']['self'] ?? ''),
            'source' => 'kitsu',
            'status' => 'Activo',
        ];
    }

    private function requestGet(string $url, string $provider): array
    {
        $handle = curl_init($url);

        if ($handle === false) {
            throw new ApiException("No se pudo iniciar la conexión con {$provider}.", 502);
        }

        curl_setopt_array($handle, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 12,
            CURLOPT_HTTPHEADER => [
                'Accept: application/vnd.api+json',
                'User-Agent: Altoidss/1.0 (academic project)',
            ],
        ]);

        $body = curl_exec($handle);
        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        $curlError = curl_error($handle);
        curl_close($handle);

        if ($body === false || $curlError !== '') {
            throw new ApiException("{$provider} no está disponible en este momento.", 502);
        }

        try {
            $payload = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $error) {
            throw new ApiException("{$provider} devolvió una respuesta inválida.", 502);
        }

        if ($status < 200 || $status >= 300 || isset($payload['errors'])) {
            error_log(sprintf('%s HTTP %d', $provider, $status));
            throw new ApiException("{$provider} no pudo completar la búsqueda.", $status === 429 ? 429 : 502);
        }

        return $payload;
    }

    private function requestJson(string $url, array $requestPayload, string $provider): array
    {
        $handle = curl_init($url);

        if ($handle === false) {
            throw new ApiException("No se pudo iniciar la conexión con {$provider}.", 502);
        }

        curl_setopt_array($handle, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 12,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($requestPayload, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR),
            CURLOPT_HTTPHEADER => [
                'Accept: application/json',
                'Content-Type: application/json',
                'User-Agent: Altoidss/1.0 (academic project)',
            ],
        ]);

        $body = curl_exec($handle);
        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        $curlCode = curl_errno($handle);
        $curlError = curl_error($handle);
        curl_close($handle);

        if ($body === false || $curlError !== '') {
            error_log(sprintf('%s cURL error %d: %s', $provider, $curlCode, $curlError));
            throw new ApiException("{$provider} no está disponible en este momento.", 502);
        }

        try {
            $payload = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $error) {
            throw new ApiException("{$provider} devolvió una respuesta inválida.", 502);
        }

        if ($status < 200 || $status >= 300 || isset($payload['errors'])) {
            error_log(sprintf(
                '%s HTTP %d: %s',
                $provider,
                $status,
                substr(json_encode($payload, JSON_UNESCAPED_UNICODE), 0, 500)
            ));
            throw new ApiException("{$provider} no pudo completar la búsqueda.", $status === 429 ? 429 : 502);
        }

        return $payload;
    }

    private function normalizeFormat(string $format): string
    {
        return match ($format) {
            'Movie' => 'Película',
            'OVA' => 'OVA',
            'ONA' => 'ONA',
            'Special', 'TV Special' => 'Especial',
            default => 'Serie',
        };
    }

    private function normalizeStatus(string $status): string
    {
        return match ($status) {
            'Finished Airing' => 'Finalizado',
            'Currently Airing' => 'Emisión',
            default => 'Pendiente',
        };
    }

    private function normalizeAniListFormat(string $format): string
    {
        return match ($format) {
            'MOVIE' => 'Película',
            'OVA' => 'OVA',
            'ONA' => 'ONA',
            'SPECIAL', 'MUSIC' => 'Especial',
            default => 'Serie',
        };
    }

    private function normalizeAniListStatus(string $status): string
    {
        return match ($status) {
            'FINISHED' => 'Finalizado',
            'RELEASING' => 'Emisión',
            default => 'Pendiente',
        };
    }

    private function normalizeKitsuFormat(string $format): string
    {
        return match (strtoupper($format)) {
            'MOVIE' => 'Película',
            'OVA' => 'OVA',
            'ONA' => 'ONA',
            'SPECIAL', 'MUSIC' => 'Especial',
            default => 'Serie',
        };
    }

    private function normalizeKitsuStatus(string $status): string
    {
        return match (strtolower($status)) {
            'finished' => 'Finalizado',
            'current' => 'Emisión',
            default => 'Pendiente',
        };
    }
}
