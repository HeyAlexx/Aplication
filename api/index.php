<?php

require __DIR__ . '/bootstrap.php';

$method = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
$route = '/' . trim((string) ($_GET['route'] ?? 'health'), '/');
$rawBody = file_get_contents('php://input');
$payload = [];

if ($rawBody !== false && trim($rawBody) !== '') {
    try {
        $payload = json_decode($rawBody, true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException $error) {
        Response::error('La solicitud contiene JSON inválido.', 400);
    }
}

if ($method === 'OPTIONS') {
    Response::success(null, 204);
}

try {
    $isMutation = in_array($method, ['POST', 'PUT', 'PATCH', 'DELETE'], true);
    $csrfExempt = in_array($route, ['/auth/login', '/auth/register'], true);

    if ($isMutation && !$csrfExempt) {
        $authService->assertCsrf();
    }

    if ($method === 'GET' && $route === '/health') {
        $storageStatus = $storage->status();
        Response::success([
            'app' => 'Altoidss API',
            'storage' => 'JSON',
            'status' => $storageStatus['dataWritable'] && $storageStatus['backupWritable'] ? 'ok' : 'warning',
            'phpVersion' => PHP_VERSION,
            'watchmode' => $watchmodeService->isConfigured() ? 'configured' : 'fallback-json',
            'directories' => $storageStatus,
        ], 200, ['csrfToken' => $authService->csrfToken()]);
    }

    if ($method === 'GET' && $route === '/auth/session') {
        Response::success($authService->session(), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'POST' && $route === '/auth/login') {
        Response::success($authService->login($payload), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'POST' && $route === '/auth/register') {
        Response::success($authService->register($payload), 201, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'POST' && $route === '/auth/logout') {
        $authService->logout();
        Response::success($authService->session(), 200, ['csrfToken' => $authService->csrfToken()]);
    }

    if ($method === 'GET' && $route === '/content') {
        Response::success($catalogService->all(), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'GET' && preg_match('#^/content/(movies|series|anime)$#', $route, $matches)) {
        Response::success($catalogService->byType($matches[1]), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'GET' && preg_match('#^/discover/(movies|series)/(.+)$#', $route, $matches)) {
        Response::success(
            $watchmodeService->search($matches[1], rawurldecode($matches[2])),
            200,
            ['csrfToken' => $authService->csrfToken()]
        );
    }
    if ($method === 'GET' && preg_match('#^/discover/anime-kitsu/(.+)$#', $route, $matches)) {
        Response::success(
            $jikanService->searchKitsuOnly(rawurldecode($matches[1])),
            200,
            ['csrfToken' => $authService->csrfToken()]
        );
    }
    if ($method === 'GET' && preg_match('#^/discover/anime/(.+)$#', $route, $matches)) {
        $animeQuery = rawurldecode($matches[1]);
        try {
            $animeResults = $jikanService->search($animeQuery);
        } catch (ApiException $animeProviderError) {
            error_log('Proveedores de anime no disponibles; se usará Watchmode: ' . $animeProviderError->getMessage());
            $animeResults = $watchmodeService->searchAnime($animeQuery);
        }
        Response::success(
            $animeResults,
            200,
            ['csrfToken' => $authService->csrfToken()]
        );
    }
    if ($method === 'POST' && $route === '/content') {
        $authService->requireAdmin();
        Response::success($catalogService->create($payload), 201, ['csrfToken' => $authService->csrfToken()]);
    }
    if (preg_match('#^/content/([^/]+)$#', $route, $matches)) {
        $id = rawurldecode($matches[1]);
        if ($method === 'GET') {
            $item = $catalogService->find($id);
            $item === null ? Response::error('El contenido no existe.', 404) : Response::success($item);
        }
        $authService->requireAdmin();
        if ($method === 'PUT') {
            Response::success($catalogService->update($id, $payload), 200, ['csrfToken' => $authService->csrfToken()]);
        }
        if ($method === 'DELETE') {
            $catalogService->delete($id);
            Response::success(['deletedId' => $id], 200, ['csrfToken' => $authService->csrfToken()]);
        }
    }

    if ($method === 'GET' && $route === '/news') {
        Response::success($newsService->all(), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'POST' && $route === '/news') {
        $authService->requireAdmin();
        Response::success($newsService->create($payload), 201, ['csrfToken' => $authService->csrfToken()]);
    }
    if (preg_match('#^/news/([^/]+)$#', $route, $matches)) {
        $authService->requireAdmin();
        $id = rawurldecode($matches[1]);
        if ($method === 'PUT') {
            Response::success($newsService->update($id, $payload), 200, ['csrfToken' => $authService->csrfToken()]);
        }
        if ($method === 'DELETE') {
            $newsService->delete($id);
            Response::success(['deletedId' => $id], 200, ['csrfToken' => $authService->csrfToken()]);
        }
    }

    if ($method === 'GET' && $route === '/profile') {
        Response::success($userService->profile($authService->session()), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'PUT' && $route === '/profile') {
        Response::success($userService->updateProfile($authService->requireUser(), $payload), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'GET' && $route === '/settings') {
        Response::success($userService->settings($authService->session()), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'PUT' && $route === '/settings') {
        Response::success($userService->updateSettings($authService->requireUser(), $payload), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'GET' && $route === '/favorites') {
        Response::success(($authService->session()['isAuthenticated'] ?? false) ? $userService->favorites($authService->session()) : []);
    }
    if (preg_match('#^/favorites/([^/]+)$#', $route, $matches)) {
        $session = $authService->requireUser();
        $id = rawurldecode($matches[1]);
        if ($method === 'POST') {
            Response::success($userService->addFavorite($session, $id, $payload), 200, ['csrfToken' => $authService->csrfToken()]);
        }
        if ($method === 'DELETE') {
            Response::success($userService->removeFavorite($session, $id), 200, ['csrfToken' => $authService->csrfToken()]);
        }
    }
    if ($method === 'PUT' && preg_match('#^/viewing/([^/]+)$#', $route, $matches)) {
        Response::success(
            $userService->updateViewing($authService->requireUser(), rawurldecode($matches[1]), $payload),
            200,
            ['csrfToken' => $authService->csrfToken()]
        );
    }
    if ($method === 'GET' && $route === '/dashboard') {
        Response::success($userService->dashboard($authService->session()), 200, ['csrfToken' => $authService->csrfToken()]);
    }
    if ($method === 'GET' && $route === '/export') {
        $authService->requireAdmin();
        Response::success([
            'contents' => $catalogService->all(),
            'news' => $newsService->all(),
            'profiles' => $storage->read('perfiles.json'),
            'favorites' => $storage->read('favoritos.json'),
            'history' => $storage->read('historial.json'),
        ]);
    }

    Response::error('La ruta solicitada no existe.', 404);
} catch (ApiException $error) {
    Response::error($error->getMessage(), $error->statusCode());
} catch (Throwable $error) {
    error_log($error->__toString());
    Response::error('Ocurrió un error interno en Altoidss.', 500);
}
