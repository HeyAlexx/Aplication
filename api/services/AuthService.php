<?php

require_once __DIR__ . '/CredentialService.php';

final class AuthService
{
    private JsonStorage $storage;
    private ?array $sessionCache = null;

    public function __construct(JsonStorage $storage, private ?LoginLimiter $limiter = null)
    {
        $this->storage = $storage;
        $this->csrfToken();
    }

    public function session(bool $fresh = false): array
    {
        if (!$fresh && $this->sessionCache !== null) {
            return $this->sessionCache;
        }
        $session = $_SESSION['user'] ?? null;
        $security = $_SESSION['auth'] ?? [];
        if (!is_array($session) || !($session['isAuthenticated'] ?? false)) {
            return $this->sessionCache = $this->visitor();
        }
        $now = time();
        $issued = $security['issuedAt'] ?? null;
        $seen = $security['seenAt'] ?? null;
        $valid = is_int($issued) && is_int($seen) && $issued <= $now && $seen <= $now
            && $now - $seen < 1800 && $now - $issued < 28800;
        $current = null;
        if ($valid) {
            foreach ($this->storage->read('usuarios.json') as $account) {
                if (($account['id'] ?? null) === ($session['id'] ?? null)) { $current = $account; break; }
            }
        }
        if ($current === null || !CredentialService::active($current)
            || ($security['version'] ?? null) !== (int) ($current['authVersion'] ?? 0)
            || !hash_equals((string) ($security['stamp'] ?? ''), CredentialService::stamp($current))
            || ($session['role'] ?? null) !== $current['role']) {
            $this->logout();
            return $this->sessionCache = $this->visitor();
        }
        $_SESSION['auth']['seenAt'] = $now;
        $_SESSION['user'] = array_merge($session, ['name'=>$current['name'], 'email'=>$current['email'],
            'role'=>$current['role'], 'profileMode'=>$current['role'] === 'admin' ? 'admin' : 'user']);
        return $this->sessionCache = $_SESSION['user'];
    }

    public function login(array $payload): array
    {
        if (!is_string($payload['email'] ?? null) || !is_string($payload['password'] ?? null)) {
            throw new ApiException('Correo o contraseña incorrectos.', 401);
        }
        $email = strtolower(trim((string) ($payload['email'] ?? '')));
        $password = (string) ($payload['password'] ?? '');
        $users = $this->storage->read('usuarios.json');

        $reservation = $this->limiter?->reserve($email, (string) ($_SERVER['REMOTE_ADDR'] ?? 'local-cli'), time()) ?? [];
        $matched = null;
        foreach ($users as $user) {
            if (strtolower((string) ($user['email'] ?? '')) !== $email) {
                continue;
            }

            $matched = $user;
            break;
        }
        $verified = CredentialService::verify($password, (string) ($matched['passwordHash'] ?? ''));
        if ($matched === null || !$verified || !CredentialService::active($matched)) {
            throw new ApiException('Correo o contraseña incorrectos.', 401);
        }
        $oldHash = (string) $matched['passwordHash'];
        $newHash = password_needs_rehash($oldHash, PASSWORD_DEFAULT) ? password_hash($password, PASSWORD_DEFAULT) : $oldHash;
        $current = $this->storage->transaction(function () use ($matched, $oldHash, $newHash): array {
            $users = $this->storage->read('usuarios.json');
            foreach ($users as $index => $account) {
                if (($account['id'] ?? '') !== $matched['id']) { continue; }
                if (!CredentialService::active($account) || !hash_equals((string) $account['passwordHash'], $oldHash)) {
                    break;
                }
                $account['passwordHash'] = $newHash;
                if ($newHash !== $oldHash) {
                    $users[$index] = $account;
                    $this->storage->write('usuarios.json', $users);
                }
                return $account;
            }
            throw new ApiException('Correo o contraseña incorrectos.', 401);
        });
        $this->limiter?->success($reservation);
        return $this->startSession($current);
    }

    public function register(array $payload): array
    {
        foreach (['name','email','password'] as $field) {
            if (!is_string($payload[$field] ?? null)) { throw new ApiException('Datos de registro inválidos.'); }
        }
        $name = trim((string) ($payload['name'] ?? ''));
        $email = strtolower(trim((string) ($payload['email'] ?? '')));
        $password = (string) ($payload['password'] ?? '');

        if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new ApiException('Ingrese un nombre y un correo válidos.');
        }
        CredentialService::validateNew($password);

        // Hash outside the lock; uniqueness and all private records commit together.
        $passwordHash = password_hash($password, PASSWORD_DEFAULT);
        $user = $this->storage->transaction(function () use ($name, $email, $passwordHash): array {
            $users = $this->storage->read('usuarios.json');
            foreach ($users as $existing) {
                if (strtolower((string) ($existing['email'] ?? '')) === $email) {
                    throw new ApiException('Ese correo ya está registrado.', 409);
                }
            }
            $user = [
                'id' => 'user-' . bin2hex(random_bytes(8)),
                'name' => $name,
                'email' => $email,
                'passwordHash' => $passwordHash,
                'role' => 'usuario',
                'createdAt' => date(DATE_ATOM),
                'status' => 'Activo',
                'authVersion' => 1,
            ];
            $users[] = $user;
            $this->storage->write('usuarios.json', $users);
            $this->createUserRecords($user);
            return $user;
        });

        // Never authenticate a registration whose storage commit failed.
        return $this->startSession($user);
    }

    public function logout(): void
    {
        $_SESSION = [];
        if (session_status() === PHP_SESSION_ACTIVE) { session_regenerate_id(true); }
        $this->sessionCache = null;
        $this->csrfToken();
    }

    public function requireUser(): array
    {
        $session = $this->session(true);

        if (!($session['isAuthenticated'] ?? false)) {
            throw new ApiException('Debe iniciar sesión para realizar esta acción.', 401);
        }

        return $session;
    }

    public function requireAdmin(): array
    {
        $session = $this->requireUser();

        if (($session['role'] ?? '') !== 'admin') {
            throw new ApiException('Esta acción requiere un perfil administrador.', 403);
        }

        return $session;
    }

    public function assertCsrf(): void
    {
        $provided = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';

        if ($provided === '' || !hash_equals($this->csrfToken(), $provided)) {
            throw new ApiException('La sesión de seguridad no es válida. Recargue la página.', 419);
        }
    }

    public function csrfToken(): string
    {
        if (!isset($_SESSION['csrfToken'])) {
            $_SESSION['csrfToken'] = bin2hex(random_bytes(24));
        }

        return $_SESSION['csrfToken'];
    }

    private function startSession(array $user): array
    {
        if (session_status() === PHP_SESSION_ACTIVE) { session_regenerate_id(true); }
        $_SESSION['csrfToken'] = bin2hex(random_bytes(24));
        $_SESSION['user'] = [
            'id' => $user['id'],
            'name' => $user['name'],
            'email' => $user['email'],
            'role' => $user['role'],
            'profileMode' => $user['role'] === 'admin' ? 'admin' : 'user',
            'isAuthenticated' => true,
            'loginAt' => date(DATE_ATOM),
        ];
        $_SESSION['auth'] = ['version'=>(int) ($user['authVersion'] ?? 0),
            'stamp'=>CredentialService::stamp($user), 'issuedAt'=>time(), 'seenAt'=>time()];
        return $this->sessionCache = $_SESSION['user'];
    }

    private function visitor(): array
    {
        return [
            'id' => 'visitor',
            'name' => 'Visitante',
            'email' => '',
            'role' => 'visitante',
            'profileMode' => 'visitor',
            'isAuthenticated' => false,
        ];
    }

    private function createUserRecords(array $user): void
    {
        $profiles = $this->storage->read('perfiles.json');
        $profiles[] = [
            'userId' => $user['id'],
            'displayName' => $user['name'],
            'email' => $user['email'],
            'socialLinks' => '',
            'about' => 'Perfil de usuario de Altoidss.',
            'avatar' => '',
            'lastVisit' => 'Hoy',
        ];
        $this->storage->write('perfiles.json', $profiles);

        $settings = $this->storage->read('configuraciones.json');
        $settings[] = [
            'userId' => $user['id'],
            'cardsPerRow' => 5,
            'preferredView' => 'cards',
            'compactMode' => false,
        ];
        $this->storage->write('configuraciones.json', $settings);
    }
}
