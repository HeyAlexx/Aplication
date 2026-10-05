# MyAnimeList API oficial

Las URLs de MyAnimeList en la revisión manual usan primero la API oficial cuando hay un Client ID configurado. Jikan queda como respaldo; las URLs de AniList y Kitsu usan sus propios proveedores.

Registra una aplicación en https://myanimelist.net/apiconfig y guarda únicamente el Client ID en `api/config/mal-client-id.local.txt`. Alternativamente, configura la variable de entorno `MAL_CLIENT_ID` o la clave `myanimelist_client_id` de `api/config/secrets.local.php`.

No se necesita Client Secret ni OAuth para consultar metadatos públicos. Las credenciales locales están excluidas de Git. No se modifican listas personales de MyAnimeList.

Para verificar la integración:

```powershell
php tests/myanimelist-service.php
php tests/myanimelist-service.php --live
```

El botón **Obtener datos desde URL** carga la propuesta en el editor y muestra un aviso cuando no hay datos compatibles. Los cambios del catálogo requieren guardar la versión final.

Referencia: https://myanimelist.net/apiconfig/references/api/v2
