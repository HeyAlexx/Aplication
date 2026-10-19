<?php
require_once __DIR__ . '/../config/catalog-storage.php';

final class JsonStorage
{
    private string $dataDir;
    private string $backupDir;
    private ?array $catalogStorage = null;
    private bool $inTransaction = false;
    private array $staged = [];

    private function transactionDir(): string
    {
        return $this->catalogStorage['catalogDir'] ?? $this->dataDir;
    }

    public function transaction(callable $action): mixed
    {
        if ($this->inTransaction) {
            return $action();
        }
        $lock = fopen($this->transactionDir() . '/.storage.lock', 'c+b');
        if ($lock === false) {
            throw new ApiException('No se pudo abrir el bloqueo del entorno.', 503);
        }
        $deadline = microtime(true) + 15;
        while (!flock($lock, LOCK_EX | LOCK_NB)) {
            if (microtime(true) >= $deadline) {
                fclose($lock);
                throw new ApiException('Almacenamiento ocupado; vuelva a intentar.', 503);
            }
            usleep(10000);
        }
        $this->inTransaction = true;
        $this->staged = [];
        try {
            $this->recoverTransaction();
            $result = $action();
            if ($this->staged !== []) {
                $directories = array_unique(array_map(fn($file) => dirname($this->path($file)), array_keys($this->staged)));
                if (count($directories) !== 1) {
                    throw new ApiException('No mezclar datos privados y catálogo en una transacción.', 500);
                }
                $journal = reset($directories) . '/.transaction.json';
                $this->atomicPayload($journal, ['version'=>1, 'files'=>$this->staged]);
                $this->recoverTransaction();
            }
            return $result;
        } finally {
            $this->staged = [];
            $this->inTransaction = false;
            flock($lock, LOCK_UN);
            fclose($lock);
            // Never unlink a shared lock: waiters must keep the same file identity.
        }
    }

    private function atomicPayload(string $path, array $payload): void
    {
        $temporary = $path . '.tmp-' . bin2hex(random_bytes(8));
        $handle = fopen($temporary, 'xb');
        if ($handle === false) {
            throw new ApiException('No se pudo preparar una transacción.', 500);
        }
        try {
            $json = json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE
                | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . PHP_EOL;
            $offset = 0;
            while ($offset < strlen($json)) {
                $written = fwrite($handle, substr($json, $offset));
                if ($written === false || $written === 0) {
                    throw new ApiException('No se pudo completar una transacción.', 500);
                }
                $offset += $written;
            }
            fflush($handle);
            if (function_exists('fsync')) { fsync($handle); }
        } finally {
            fclose($handle);
        }
        if (!@rename($temporary, $path)) {
            @unlink($temporary);
            throw new ApiException('No se pudo reemplazar un archivo; el diario conserva la operación.', 500);
        }
    }

    private function recoverTransaction(): void
    {
        foreach (array_unique([$this->transactionDir(), $this->dataDir]) as $directory) {
            $this->recoverDirectory($directory);
        }
    }

    private function recoverDirectory(string $directory): void
    {
        $journal = $directory . '/.transaction.json';
        if (!is_file($journal)) { return; }
        $payload = json_decode((string) file_get_contents($journal), true, 512, JSON_THROW_ON_ERROR);
        if (($payload['version'] ?? null) !== 1 || !is_array($payload['files'] ?? null)) {
            throw new ApiException('Diario de transacción inválido; requiere revisión.', 500);
        }
        foreach ($payload['files'] as $file => $records) {
            if (!is_array($records)) { throw new ApiException('Colección de recuperación inválida.', 500); }
            $path = $this->path($file);
            if (dirname($path) !== $directory) {
                throw new ApiException('El diario no corresponde al directorio esperado.', 500);
            }
            if (is_file($path)) {
                $backup = $this->backupDir . '/' . pathinfo($file, PATHINFO_FILENAME)
                    . '-' . date('Ymd-His') . '-' . bin2hex(random_bytes(4)) . '.json';
                if (!copy($path, $backup)) { throw new ApiException('No se pudo respaldar la colección.', 500); }
            }
            $this->atomicPayload($path, array_values($records));
        }
        if (!unlink($journal)) { throw new ApiException('No se pudo confirmar la transacción.', 500); }
    }

    public function __construct(string $dataDir, string $backupDir)
    {
        $this->dataDir = $dataDir;
        $this->backupDir = $backupDir;
        if (realpath($dataDir) === realpath(dirname(__DIR__, 2) . '/data')) {
            $this->catalogStorage = altoidss_catalog_storage();
        }
        $this->ensureDirectory($this->dataDir);
        $this->ensureDirectory($this->backupDir);
    }

    public function status(): array
    {
        return [
            'dataWritable' => is_writable($this->dataDir)
                && ($this->catalogStorage === null || is_writable($this->catalogStorage['catalogDir'])),
            'backupWritable' => is_writable($this->backupDir),
        ];
    }

    public function read(string $file): array
    {
        if (!$this->inTransaction) {
            return $this->transaction(fn() => $this->read($file));
        }
        if (array_key_exists($file, $this->staged)) { return $this->staged[$file]; }
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
        if (!$this->inTransaction) {
            $this->transaction(fn() => $this->write($file, $records));
            return;
        }
        $this->path($file); // Validate before recording anything in the journal.
        $this->staged[$file] = array_values($records);
        return;
    }

    private function path(string $file): string
    {
        if (!preg_match('/^[a-z0-9-]+\.json$/i', $file)) {
            throw new ApiException('Nombre de archivo de datos no permitido.', 500);
        }

        $directory = $this->catalogStorage && in_array($file, altoidss_catalog_files(), true)
            ? $this->catalogStorage['catalogDir'] : $this->dataDir;
        return $directory . DIRECTORY_SEPARATOR . $file;
    }

    private function ensureDirectory(string $directory): void
    {
        if (!is_dir($directory) && !mkdir($directory, 0775, true) && !is_dir($directory)) {
            throw new ApiException("No se pudo crear el directorio {$directory}.", 500);
        }
    }
}
