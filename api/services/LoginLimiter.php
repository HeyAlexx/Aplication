<?php
declare(strict_types=1);

final class LoginLimiter
{
    public function __construct(private JsonStorage $storage) {}

    public function reserve(string $email, string $origin, int $now): array
    {
        $account = hash('sha256', strtolower(trim($email)));
        $keys = [
            'pair-' . hash('sha256', $account . '|' . $origin) => 5,
            'account-' . $account => 10,
            'source-' . hash('sha256', $origin) => 100,
        ];
        return $this->storage->transaction(function () use ($keys, $now): array {
            $rows = array_values(array_filter($this->storage->read('attempts.json'),
                fn($row) => is_array($row) && (int) ($row['expiresAt'] ?? 0) > $now));
            $indexed = array_column($rows, null, 'key');
            foreach ($keys as $key => $limit) {
                if ((int) ($indexed[$key]['count'] ?? 0) >= $limit) {
                    // Rejected requests do not extend the fixed window.
                    throw new ApiException('Demasiados intentos. Espere antes de volver a intentarlo.', 429);
                }
            }
            if (count($indexed) + 3 > 10000) {
                throw new ApiException('Inicio de sesión temporalmente limitado. Inténtelo después.', 429);
            }
            foreach ($keys as $key => $_) {
                $row = $indexed[$key] ?? ['key'=>$key, 'count'=>0, 'expiresAt'=>$now + 900];
                $row['count']++;
                $indexed[$key] = $row;
            }
            $this->storage->write('attempts.json', array_values($indexed));
            return array_keys($keys);
        });
    }

    public function success(array $keys): void
    {
        $reset = array_flip(array_filter($keys, fn($key) => !str_starts_with($key, 'source-')));
        $this->storage->transaction(function () use ($reset): void {
            $this->storage->write('attempts.json', array_values(array_filter(
                $this->storage->read('attempts.json'), fn($row) => !isset($reset[$row['key'] ?? '']))));
        });
    }
}

