<?php

final class JsonStorage
{
    private string $dataDir;
    private string $backupDir;

    public function __construct(string $dataDir, string $backupDir)
    {
        $this->dataDir = $dataDir;
        $this->backupDir = $backupDir;
        $this->ensureDirectory($this->dataDir);
        $this->ensureDirectory($this->backupDir);
    }

    public function status(): array
    {
        return [
            'dataWritable' => is_writable($this->dataDir),
            'backupWritable' => is_writable($this->backupDir),
        ];
    }

    public function read(string $file): array
    {
        $path = $this->path($file);

        if (!is_file($path)) {
            return [];
        }

        $handle = fopen($path, 'rb');

        if ($handle === false) {
            throw new ApiException("No se pudo abrir {$file}.", 500);
        }

        try {
            flock($handle, LOCK_SH);
            $contents = stream_get_contents($handle);
            flock($handle, LOCK_UN);
        } finally {
            fclose($handle);
        }

        if ($contents === false || trim($contents) === '') {
            return [];
        }

        try {
            $decoded = json_decode($contents, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $error) {
            throw new ApiException("El archivo {$file} contiene JSON inválido.", 500);
        }

        if (!is_array($decoded)) {
            throw new ApiException("El archivo {$file} no contiene una colección válida.", 500);
        }

        return $decoded;
    }

    public function write(string $file, array $records): void
    {
        $path = $this->path($file);
        $lockPath = $path . '.lock';
        $lock = fopen($lockPath, 'c+');

        if ($lock === false) {
            throw new ApiException("No se pudo bloquear {$file}.", 500);
        }

        try {
            if (!flock($lock, LOCK_EX)) {
                throw new ApiException("No se pudo obtener acceso exclusivo a {$file}.", 500);
            }

            if (is_file($path)) {
                $backupName = pathinfo($file, PATHINFO_FILENAME)
                    . '-' . date('Ymd-His') . '-' . bin2hex(random_bytes(2)) . '.json';
                @copy($path, $this->backupDir . DIRECTORY_SEPARATOR . $backupName);
            }

            $json = json_encode(
                array_values($records),
                JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
            ) . PHP_EOL;
            $temporaryPath = $path . '.tmp-' . bin2hex(random_bytes(4));

            if (file_put_contents($temporaryPath, $json, LOCK_EX) === false) {
                throw new ApiException("No se pudo preparar la escritura de {$file}.", 500);
            }

            if (!@rename($temporaryPath, $path)) {
                if (!@copy($temporaryPath, $path)) {
                    @unlink($temporaryPath);
                    throw new ApiException("No se pudo actualizar {$file}.", 500);
                }
                @unlink($temporaryPath);
            }

            flock($lock, LOCK_UN);
        } finally {
            fclose($lock);
            @unlink($lockPath);
        }
    }

    private function path(string $file): string
    {
        if (!preg_match('/^[a-z0-9-]+\.json$/i', $file)) {
            throw new ApiException('Nombre de archivo de datos no permitido.', 500);
        }

        return $this->dataDir . DIRECTORY_SEPARATOR . $file;
    }

    private function ensureDirectory(string $directory): void
    {
        if (!is_dir($directory) && !mkdir($directory, 0775, true) && !is_dir($directory)) {
            throw new ApiException("No se pudo crear el directorio {$directory}.", 500);
        }
    }
}
