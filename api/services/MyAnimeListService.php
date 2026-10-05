<?php

final class MyAnimeListService
{
    private string $clientId;

    public function __construct(string $clientId)
    {
        $this->clientId = trim($clientId);
    }

    public function isConfigured(): bool
    {
        return $this->clientId !== '';
    }

    public function details(int $animeId): array
    {
        if (!$this->isConfigured() || $animeId < 1) {
            throw new ApiException('Falta configurar el Client ID de MyAnimeList.', 503);
        }
        $fields = 'id,title,main_picture,alternative_titles,start_date,synopsis,mean,media_type,status,genres,num_episodes,start_season';
        $url = 'https://api.myanimelist.net/v2/anime/' . $animeId . '?' . http_build_query(['fields' => $fields]);
        $handle = curl_init($url);
        if ($handle === false) {
            throw new ApiException('No se pudo conectar con MyAnimeList.', 502);
        }
        curl_setopt_array($handle, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 15,
            CURLOPT_HTTPHEADER => ['Accept: application/json', 'X-MAL-CLIENT-ID: ' . $this->clientId],
        ]);
        $body = curl_exec($handle);
        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        curl_close($handle);
        if ($body === false || $status < 200 || $status >= 300) {
            throw new ApiException('MyAnimeList no pudo completar la consulta (HTTP ' . $status . ').', 502);
        }
        $item = json_decode($body, true);
        if (!is_array($item) || (int) ($item['id'] ?? 0) !== $animeId || empty($item['title'])) {
            throw new ApiException('MyAnimeList no devolvió datos compatibles.', 502);
        }
        return $this->normalize($item);
    }

    private function normalize(array $item): array
    {
        $id = (string) $item['id'];
        $alternatives = $item['alternative_titles'] ?? [];
        $genres = array_values(array_filter(array_map(
            static fn (array $genre): string => trim((string) ($genre['name'] ?? '')),
            $item['genres'] ?? []
        )));
        $year = (int) ($item['start_season']['year'] ?? substr((string) ($item['start_date'] ?? ''), 0, 4));
        return [
            'jikanId' => $id,
            'malId' => $id,
            'title' => trim((string) $item['title']),
            'alternativeTitles' => array_values(array_unique(array_filter(array_merge(
                [(string) ($alternatives['en'] ?? ''), (string) ($alternatives['ja'] ?? '')],
                $alternatives['synonyms'] ?? []
            )))),
            'format' => match ($item['media_type'] ?? '') {
                'tv' => 'Serie', 'movie' => 'Película', 'ova' => 'OVA', 'ona' => 'ONA',
                'special', 'music' => 'Especial', default => '',
            },
            'productionStatus' => match ($item['status'] ?? '') {
                'finished_airing' => 'Finalizado', 'currently_airing' => 'Emisión',
                'not_yet_aired' => 'Próximamente', default => 'Pendiente',
            },
            'chapters' => max(0, (int) ($item['num_episodes'] ?? 0)),
            'emissionYear' => $year > 0 ? $year : null,
            'emissionSeason' => ucfirst(strtolower((string) ($item['start_season']['season'] ?? ''))),
            'genre' => $genres[0] ?? 'Anime',
            'metadataGenres' => $genres,
            'rating' => (float) ($item['mean'] ?? 0),
            'image' => (string) ($item['main_picture']['large'] ?? $item['main_picture']['medium'] ?? ''),
            'description' => trim((string) ($item['synopsis'] ?? '')),
            'sourceUrl' => 'https://myanimelist.net/anime/' . $id,
            'externalTitle' => trim((string) $item['title']),
            'metadataProvider' => 'myanimelist',
            'metadataMatchScore' => 1,
        ];
    }
}
