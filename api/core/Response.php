<?php

final class Response
{
    public static function success($data = null, int $status = 200, array $meta = []): void
    {
        self::send(['ok' => true, 'data' => $data, 'meta' => $meta], $status);
    }

    public static function error(string $message, int $status = 400, array $details = []): void
    {
        self::send(['ok' => false, 'error' => ['message' => $message, 'details' => $details]], $status);
    }

    private static function send(array $payload, int $status): void
    {
        http_response_code($status);
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }
}
