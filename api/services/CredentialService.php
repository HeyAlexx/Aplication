<?php
declare(strict_types=1);

final class CredentialService
{
    // Only a timing equalizer for unknown/legacy accounts; never an account credential.
    private const DUMMY = '$2y$10$htNgcb.pjJCY7AUe0ThQKumJQ1hXvR6NAv4CVx5eyILUzGv.l2umK';

    public static function validateNew(string $password): void
    {
        if (!mb_check_encoding($password, 'UTF-8') || mb_strlen($password, 'UTF-8') < 15
            || strlen($password) > 72 || str_contains($password, "\0")) {
            throw new ApiException('Use una contraseña de al menos 15 caracteres y como máximo 72 bytes.');
        }
    }

    public static function verify(string $password, string $hash): bool
    {
        if (str_starts_with($hash, 'sha256$')) {
            password_verify($password, self::DUMMY);
            [, $salt, $digest] = array_pad(explode('$', $hash, 3), 3, '');
            return $salt !== '' && hash_equals($digest, hash('sha256', $salt . '|' . $password));
        }
        return password_verify($password, $hash !== '' ? $hash : self::DUMMY);
    }

    public static function stamp(array $account): string
    {
        return hash('sha256', (string) ($account['passwordHash'] ?? ''));
    }

    public static function active(array $account): bool
    {
        return ($account['status'] ?? '') === 'Activo'
            && in_array($account['role'] ?? '', ['admin', 'usuario'], true);
    }
}

