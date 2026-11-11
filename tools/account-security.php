<?php
declare(strict_types=1);
// Local operator pipe only. No HTTP endpoint and no password argv.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require_once __DIR__ . '/../api/core/ApiException.php';
require_once __DIR__ . '/../api/core/JsonStorage.php';
require_once __DIR__ . '/../api/services/AccountSecurityService.php';

try {
    if ($argc !== 3) { throw new RuntimeException('Use el operador Python con entrada protegida.'); }
    $app = realpath($argv[1]);
    $canonical = strtolower(str_replace('\\', '/', (string) $app));
    $allowed = ['c:/users/alvar/projects/altoids/proyectofinal/aplication',
                'c:/users/alvar/projects/altoids/desarrollo/aplication'];
    if ($app === false || !in_array($canonical, $allowed, true) || $app !== realpath(dirname(__DIR__))) {
        throw new RuntimeException('La operación solo está permitida en las instalaciones C: previstas.');
    }
    $environment = str_contains($canonical, '/proyectofinal/') ? 'produccion' : 'desarrollo';
    $descriptor = dirname($app) . '/catalog-storage.local.json';
    $settings = json_decode((string) file_get_contents($descriptor), true, 32, JSON_THROW_ON_ERROR);
    $catalog = realpath((string) ($settings['catalogDir'] ?? ''));
    $expectedPrefix = 'c:/users/alvar/projects/altoids/datos/' . $environment . '/';
    if (($settings['environment'] ?? '') !== $environment || $catalog === false
        || !str_starts_with(strtolower(str_replace('\\', '/', $catalog)), $expectedPrefix)) {
        throw new RuntimeException('El almacenamiento no corresponde al entorno C: previsto.');
    }
    foreach ([$app . '/data', $catalog] as $directory) {
        if (is_file($directory . '/.transaction.json')) { throw new RuntimeException('Revisar la transacción pendiente antes de operar.'); }
    }
    putenv('ALTOIDSS_STORAGE_CONFIG=' . $descriptor);
    $action = $argv[2];
    $input = stream_get_contents(STDIN, 65537);
    if ($input === false || strlen($input) > 65536) { throw new RuntimeException('Entrada inválida.'); }
    $payload = json_decode($input, true, 8, JSON_THROW_ON_ERROR);
    if (!is_array($payload)) { throw new RuntimeException('Entrada inválida.'); }
    $storage = new JsonStorage($app . '/data', $app . '/backups');
    if ($action === 'list') {
        $result = array_map(fn($u) => ['id'=>$u['id'], 'name'=>$u['name'], 'role'=>$u['role'], 'status'=>$u['status']],
                           $storage->read('usuarios.json'));
    } elseif (in_array($action, ['reset', 'revoke'], true)) {
        $password = $action === 'reset' ? (string) ($payload['password'] ?? '') : null;
        $result = (new AccountSecurityService($storage))->change((string) ($payload['userId'] ?? ''), $password);
        if ($password !== null) {
            $verified = false;
            foreach ($storage->read('usuarios.json') as $user) {
                if (($user['id'] ?? '') === $result['id']) {
                    $verified = CredentialService::verify($password, (string) ($user['passwordHash'] ?? ''))
                        && (int) ($user['authVersion'] ?? 0) === $result['authVersion'];
                    break;
                }
            }
            if (!$verified) { throw new RuntimeException('No se pudo verificar el restablecimiento.'); }
            $result['storedPasswordVerified'] = true;
        }
        unset($payload, $password);
    } else { throw new RuntimeException('Operación inválida.'); }
    echo json_encode(['ok'=>true, 'result'=>$result], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
} catch (Throwable $error) {
    // Never echo input, hash, exception trace or a credential in operator output.
    $message = $error instanceof ApiException ? $error->getMessage() : 'El operador local no pudo completar la operación.';
    fwrite(STDERR, $message . PHP_EOL);
    exit(1);
}

