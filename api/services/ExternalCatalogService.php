<?php
declare(strict_types=1);

final class ExternalCatalogService
{
    public function __construct(private JikanService $anime, private WatchmodeService $watchmode) {}

    public static function identity(string $id): array
    {
        if (!preg_match('/^(jikan|anilist|kitsu|watchmode|watchmode-anime)-([1-9][0-9]{0,9})$/D', $id, $matches)
            || (int) $matches[2] > 2147483647) {
            throw new ApiException('El identificador externo no es válido.');
        }
        return ['source'=>str_starts_with($matches[1], 'watchmode') ? 'watchmode' : $matches[1],
                'providerId'=>$matches[2], 'animeAlias'=>$matches[1] === 'watchmode-anime'];
    }

    public function resolve(string $id): array
    {
        $identity = self::identity($id);
        $number = $identity['providerId'];
        if ($identity['source'] === 'watchmode') {
            return $this->watchmode->details($number, $identity['animeAlias']);
        }
        $url = match ($identity['source']) {
            'jikan'=>'https://api.jikan.moe/v4/anime/' . $number,
            'anilist'=>'https://anilist.co/anime/' . $number,
            'kitsu'=>'https://kitsu.app/anime/' . $number,
        };
        // URL and provider base are server-owned, never a client URL.
        $candidate = $this->anime->fromSourceUrl($url);
        if ($candidate === null || ($candidate['id'] ?? '') !== $id || ($candidate['source'] ?? '') !== $identity['source']) {
            throw new ApiException('No se pudo verificar el título con su proveedor. Inténtelo después.', 502);
        }
        return $candidate;
    }

    public static function snapshot(string $id, array $candidate): array
    {
        $identity = self::identity($id);
        if (($candidate['id'] ?? '') !== $id || ($candidate['source'] ?? '') !== $identity['source']
            || !in_array($candidate['type'] ?? '', ['anime','movies','series'], true)
            || trim((string) ($candidate['title'] ?? '')) === ''
            || ($identity['source'] !== 'watchmode' && $candidate['type'] !== 'anime')) {
            throw new ApiException('El proveedor devolvió una identidad inconsistente.', 502);
        }
        $allowed = ['id','source','title','type','description','format','genre','tags','image','sourceUrl',
                    'year','emissionYear','emissionSeason','chapters','seasonsCount','productionStatus',
                    'alternativeTitle','alternativeTitles','rating','watchmodeId','jikanId','anilistId','kitsuId','malId'];
        $item = array_intersect_key($candidate, array_flip($allowed));
        foreach (['title'=>300,'description'=>12000,'genre'=>150,'format'=>80] as $key=>$max) {
            $item[$key] = mb_substr((string) ($item[$key] ?? ''), 0, $max);
        }
        foreach (['image','sourceUrl'] as $field) {
            $value = (string) ($item[$field] ?? '');
            $item[$field] = strlen($value) <= 2048 && filter_var($value,FILTER_VALIDATE_URL)
                && strtolower((string) parse_url($value,PHP_URL_SCHEME)) === 'https' ? $value : '';
        }
        $item['status'] = 'Activo';
        return $item;
    }
}

