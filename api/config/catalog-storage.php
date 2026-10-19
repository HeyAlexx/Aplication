<?php
// External deployment configuration survives Git checkouts; never infer production.
function altoidss_catalog_storage(): ?array
{
    $configPath = getenv('ALTOIDSS_STORAGE_CONFIG')
        ?: dirname(__DIR__, 3) . '/catalog-storage.local.json';
    if (!is_file($configPath)) {
        if (getenv('ALTOIDSS_STORAGE_CONFIG')) {
            throw new RuntimeException('No existe el descriptor central solicitado.');
        }
        return null; // Portable installations keep their existing local data.
    }
    $config = json_decode((string) file_get_contents($configPath), true, 512, JSON_THROW_ON_ERROR);
    foreach (['catalogDir', 'syncStateDir'] as $key) {
        if (empty($config[$key]) || !is_dir($config[$key])) {
            throw new RuntimeException('Almacenamiento central no disponible: ' . $key);
        }
    }
    return $config;
}
function altoidss_catalog_files(): array
{
    return ['anime.json', 'peliculas.json', 'series.json', 'noticias.json',
        'temporadas.json', 'episodios.json', 'anime-revisiones.json',
        'anime-sheet-writeback.json', 'anime-hoja.json'];
}
