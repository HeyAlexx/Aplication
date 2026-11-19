<?php
declare(strict_types=1);

/** Trusted account data only. Management UI and account mutations belong to a later batch. */
final class AccessPolicy
{
    private const ADMIN = ['catalog.create', 'catalog.update', 'catalog.hide', 'catalog.review',
        'news.manage', 'anime.review', 'data.export', 'accounts.nominate', 'accounts.suspend'];
    private const KNOWN = ['catalog.propose', 'catalog.create', 'catalog.update', 'catalog.hide',
        'catalog.review', 'news.manage', 'anime.review', 'data.export', 'accounts.nominate',
        'accounts.suspend', 'accounts.restore', 'accounts.approve', 'accounts.inspect',
        'accounts.delete', 'accounts.credentials', 'permissions.manage', 'accounts.appoint'];
    private const MASTER_ONLY = ['permissions.manage', 'accounts.appoint'];
    private string $masterId;
    private array $profiles;

    public function __construct(array $config = [])
    {
        if (array_diff(array_keys($config), ['masterAccountId', 'profilePermissions'])) {
            throw new InvalidArgumentException('Configuración de autorización desconocida.');
        }
        $masterId = array_key_exists('masterAccountId', $config) ? $config['masterAccountId'] : '';
        $profiles = array_key_exists('profilePermissions', $config) ? $config['profilePermissions'] : [];
        if (!is_string($masterId) || !is_array($profiles)) {
            throw new InvalidArgumentException('Configuración de autorización inválida.');
        }
        $this->masterId = $masterId;
        if (strlen($this->masterId) > 128 || ($this->masterId !== '' && !preg_match('/^[A-Za-z0-9_-]+$/D', $this->masterId))) {
            throw new InvalidArgumentException('Identidad maestra configurada inválida.');
        }
        $this->profiles = $profiles;
        foreach ($this->profiles as $role => $permissions) {
            if (!in_array($role, ['admin', 'usuario'], true) || !self::validOverrides($permissions)) {
                throw new InvalidArgumentException('Permisos de perfil inválidos.');
            }
        }
    }

    public static function active(array $account): bool
    {
        return ($account['status'] ?? '') === 'Activo'
            && in_array($account['role'] ?? '', ['admin', 'usuario'], true)
            && (!array_key_exists('approvalStatus', $account) || $account['approvalStatus'] === 'approved');
    }

    private static function validOverrides(mixed $permissions): bool
    {
        if (!is_array($permissions)) { return false; }
        foreach ($permissions as $permission => $allowed) {
            if (!in_array($permission, self::KNOWN, true) || !is_bool($allowed)) { return false; }
        }
        return true;
    }

    public function isMaster(array $account): bool
    {
        return $this->masterId !== '' && ($account['id'] ?? '') === $this->masterId
            && ($account['role'] ?? '') === 'admin';
    }

    public function allows(array $account, string $permission): bool
    {
        if (!self::active($account) || !is_string($account['id'] ?? null) || $account['id'] === ''
            || !in_array($permission, self::KNOWN, true)) { return false; }
        $overrides = array_key_exists('permissionOverrides', $account) ? $account['permissionOverrides'] : [];
        if (!self::validOverrides($overrides)) { return false; }
        if (in_array($permission, self::MASTER_ONLY, true)) { return $this->isMaster($account); }
        if ($this->isMaster($account)) { return true; }
        if (array_key_exists($permission, $overrides)) { return $overrides[$permission]; }
        $profile = $this->profiles[$account['role']] ?? [];
        if (array_key_exists($permission, $profile)) { return $profile[$permission]; }
        return $permission === 'catalog.propose'
            || ($account['role'] === 'admin' && in_array($permission, self::ADMIN, true));
    }

    public function permissions(array $account): array
    {
        return array_values(array_filter(self::KNOWN, fn(string $p): bool => $this->allows($account, $p)));
    }

    public static function sessionAllows(array $session, string $permission): bool
    {
        return ($session['isAuthenticated'] ?? false) === true
            && is_array($session['permissions'] ?? null)
            && in_array($permission, $session['permissions'], true);
    }

    public function canApproveContent(array $actor, string $authorId): bool
    {
        return $authorId !== '' && ($actor['id'] ?? '') !== $authorId
            && $this->allows($actor, 'catalog.review');
    }

    /** Decision guards only: no account write, notification or lifecycle endpoint here. */
    public function canChangeAccount(array $actor, array $target, string $action): bool
    {
        $permission = ['nominate'=>'accounts.nominate', 'appoint'=>'accounts.appoint',
            'suspend'=>'accounts.suspend', 'restore'=>'accounts.restore', 'delete'=>'accounts.delete',
            'credentials'=>'accounts.credentials', 'demote'=>'permissions.manage'][$action] ?? '';
        if (!is_string($target['id'] ?? null) || $target['id'] === '' || !$this->allows($actor, $permission)) {
            return false;
        }
        if (in_array($action, ['nominate', 'appoint'], true) && ($actor['role'] ?? '') !== 'admin') { return false; }
        if (($target['role'] ?? '') === 'admin' && in_array($action, ['suspend', 'restore'], true)
            && ($actor['role'] ?? '') !== 'admin') { return false; }
        // Protect the configured identity even when a target record is stale or malformed.
        if ($target['id'] === $this->masterId) {
            return $action === 'credentials' && $this->isMaster($actor);
        }
        if (($target['role'] ?? '') === 'admin') {
            if ($action === 'delete' && ($actor['id'] === $target['id'] || !$this->isMaster($actor))) { return false; }
            if (in_array($action, ['demote', 'credentials', 'restore'], true) && !$this->isMaster($actor)) { return false; }
        }
        return true;
    }

    public function appointmentDecision(array $actor, array $target): string
    {
        $action = $this->isMaster($actor) ? 'appoint' : 'nominate';
        if (!$this->canChangeAccount($actor, $target, $action)) {
            throw new ApiException('Nombramiento no autorizado.', 403);
        }
        return $this->isMaster($actor) ? 'approved' : 'pending';
    }
}
