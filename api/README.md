# API PHP + JSON de Altoidss



## Estructura

- `index.php`: punto unico de entrada para todas las rutas.
- `bootstrap.php`: carga configuracion, sesion y servicios.
- `config/app.php`: rutas de datos, respaldos y nombre de sesión.
- `core/JsonStorage.php`: lectura y escritura segura de JSON.
- `core/Response.php`: respuestas JSON estandarizadas.
- `core/ApiException.php`: errores controlados.
- `services/AuthService.php`: login, registro, logout y permisos.
- `services/CatalogService.php`: CRUD de peliculas, series y anime.
- `services/NewsService.php`: CRUD de noticias tipo blog.
- `services/UserService.php`: perfil, configuracion, favoritos, vistos y metricas.

## Flujo general

1. El navegador consulta por separado `api/index.php?route=/content/movies`, `/content/series` y `/content/anime`.
2. `index.php` valida metodo, ruta y token de seguridad si aplica.
3. El servicio correspondiente procesa la solicitud.
4. `JsonStorage` lee o actualiza los archivos JSON.
5. La respuesta vuelve al frontend como JSON.



## Proveedores del catalogo

- `movies`: usa `data/peliculas.json` y consulta Watchmode cuando se realiza una busqueda externa.
- `series`: usa `data/series.json` y consulta Watchmode cuando se realiza una busqueda externa.
- `anime`: conserva `data/anime.json` y su modelo propio de temporadas y capitulos. Las búsquedas externas usan Jikan, con respaldo automático en AniList y Kitsu. Si los tres servicios especializados fallan, Watchmode mantiene disponible la búsqueda.

Watchmode se conecta exclusivamente desde PHP mediante una clave privada. Si la clave no esta configurada o el servicio no responde, los JSON locales continuan disponibles como respaldo portable.

La clave local se guarda en `api/config/secrets.local.php`, archivo excluido mediante `.gitignore`. Para compartir el proyecto sin credenciales, se incluye `api/config/secrets.example.php`. También puede definirse la variable de entorno `WATCHMODE_API_KEY`.

Cuando un usuario marca como favorito un resultado de Watchmode, Jikan, AniList o Kitsu, el registro normalizado se agrega primero al JSON de su categoría. Después se guarda la relación del favorito con el perfil. Así el contenido continúa disponible localmente aunque el proveedor externo esté desconectado.
