<?php

final class AuthService
{
    private JsonStorage $storage;

    public function __construct(JsonStorage $storage)
    {
        $this->storage = $storage;
        $this->csrfToken();
    }

    public function session(): array
    {
        return $_SESSION['user'] ?? $this->visitor();
    }

    public function login(array $payload): array
    {
        $email = strtolower(trim((string) ($payload['email'] ?? '')));
        $password = (string) ($payload['password'] ?? '');
        $users = $this->storage->read('usuarios.json');

        foreach ($users as $index => $user) {
            if (strtolower((string) ($user['email'] ?? '')) !== $email) {
                continue;
            }

            if (!$this->verifyPassword($password, (string) ($user['passwordHash'] ?? ''))) {
                break;
            }

            if ($this->startsWith((string) $user['passwordHash'], 'sha256$')) {
                $users[$index]['passwordHash'] = password_hash($password, PASSWORD_DEFAULT);
                $this->storage->write('usuarios.json', $users);
            }

            return $this->startSession($user);
        }

        throw new ApiException('Correo o contraseña incorrectos.', 401);
    }

    public function register(array $payload): array
    {
        $name = trim((string) ($payload['name'] ?? ''));
        $email = strtolower(trim((string) ($payload['email'] ?? '')));
        $password = (string) ($payload['password'] ?? '');

        if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            throw new ApiException('Ingrese un nombre y un correo válidos.');
        }

        if (strlen($password) < 6) {
            throw new ApiException('La contraseña debe tener al menos 6 caracteres.');
        }

        $users = $this->storage->read('usuarios.json');

        foreach ($users as $user) {
            if (strtolower((string) ($user['email'] ?? '')) === $email) {
                throw new ApiException('Ese correo ya está registrado.', 409);
            }
        }

        $user = [
            'id' => 'user-' . bin2hex(random_bytes(8)),
            'name' => $name,
            'email' => $email,
            'passwordHash' => password_hash($password, PASSWORD_DEFAULT),
            'role' => 'usuario',
            'createdAt' => date(DATE_ATOM),
            'status' => 'Activo',
        ];
        $users[] = $user;
        $this->storage->write('usuarios.json', $users);
        $this->createUserRecords($user);

        return $this->startSession($user);
    }

    public function logout(): void
    {
        $_SESSION = [];
        session_regenerate_id(true);
        $this->csrfToken();
    }

    public function requireUser(): array
    {
        $session = $this->session();

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
        session_regenerate_id(true);
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

        return $_SESSION['user'];
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

    private function verifyPassword(string $password, string $storedHash): bool
    {
        if ($this->startsWith($storedHash, 'sha256$')) {
            [, $salt, $hash] = array_pad(explode('$', $storedHash, 3), 3, '');
            return $salt !== '' && hash_equals($hash, hash('sha256', $salt . '|' . $password));
        }

        return $storedHash !== '' && password_verify($password, $storedHash);
    }

    private function startsWith(string $value, string $prefix): bool
    {
        return substr($value, 0, strlen($prefix)) === $prefix;
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
