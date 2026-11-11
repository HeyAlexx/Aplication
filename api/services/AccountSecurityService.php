<?php
declare(strict_types=1);
require_once __DIR__ . '/CredentialService.php';

final class AccountSecurityService
{
    public function __construct(private JsonStorage $storage) {}

    public function change(string $userId, ?string $password): array
    {
        if ($password !== null) {
            CredentialService::validateNew($password);
            $hash = password_hash($password, PASSWORD_DEFAULT);
        } else { $hash = null; }
        return $this->storage->transaction(function () use ($userId, $password, $hash): array {
            $users = $this->storage->read('usuarios.json');
            foreach ($users as $index => $user) {
                if (($user['id'] ?? '') !== $userId) { continue; }
                if ($password !== null && CredentialService::verify($password, (string) ($user['passwordHash'] ?? ''))) {
                    throw new ApiException('La contraseña nueva debe ser distinta de la anterior.');
                }
                if ($hash !== null) { $user['passwordHash'] = $hash; }
                $user['authVersion'] = (int) ($user['authVersion'] ?? 0) + 1;
                $user['sessionsRevokedAt'] = date(DATE_ATOM);
                if ($hash !== null) { $user['passwordChangedAt'] = date(DATE_ATOM); }
                $users[$index] = $user;
                $this->storage->write('usuarios.json', $users);
                return ['id'=>$userId, 'authVersion'=>$user['authVersion'],
                        'passwordChanged'=>$hash !== null, 'sessionsRevoked'=>true];
            }
            throw new ApiException('No se encontró la cuenta.', 404);
        });
    }
}

