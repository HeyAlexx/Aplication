# Altoidss - Segunda Entrega

Proyecto web academico para Programacion Internet.

## Como abrirlo

1. Copiar la carpeta `2Entrega` dentro de `htdocs` si se usa XAMPP.
2. Iniciar Apache.
3. Abrir `http://localhost/2Entrega/Html/index.html`.

La aplicacion no requiere MySQL ni inicializacion de base de datos. La persistencia final del proyecto funciona con PHP y archivos JSON ubicados en `data`. Se recomienda PHP 8.2, version utilizada durante las pruebas de entrega.

## Cuentas para la entrega

- Usuario: `usuario@altoidss.com` / `usuario123`
- Admin: `admin@altoidss.com` / `admin123`

El Dashboard muestra las herramientas disponibles segun el rol de la cuenta iniciada.

## Persistencia

El frontend consume una API PHP ubicada en `api/index.php`. Esa API lee y escribe los JSON de `data` con bloqueo de archivo y crea respaldos automaticos en `backups`.
Las sesiones se guardan dentro de `backups/sessions`, por lo que el proyecto no depende del directorio temporal configurado en XAMPP.

Para probar autenticacion, perfiles, favoritos, vistos y CRUD se debe ejecutar el proyecto mediante Apache o el servidor integrado de PHP. Abrir los HTML directamente solo permite una previsualizacion parcial.

## Rutas principales de la API

- `GET /health`
- `GET /content`
- `POST /content`
- `PUT /content/{id}`
- `DELETE /content/{id}`
- `GET /news`
- `POST /news`
- `PUT /news/{id}`
- `DELETE /news/{id}`
- `GET /profile`
- `PUT /profile`
- `PUT /settings`
- `POST /favorites/{id}`
- `DELETE /favorites/{id}`
- `PUT /viewing/{id}`

Todas las rutas se invocan mediante `api/index.php?route=/ruta`.
La ruta `GET /health` tambien informa la version de PHP y confirma si las carpetas de datos y respaldos tienen permisos de escritura.

## Archivos de datos

- `peliculas.json`
- `series.json`
- `anime.json`
- `noticias.json`
- `usuarios.json`
- `perfiles.json`
- `configuraciones.json`
- `favoritos.json`
- `historial.json`
- `temporadas.json`
- `episodios.json`

Los archivos `.htaccess` dentro de `data` y `backups` evitan que Apache exponga esos datos directamente.

## Pipeline de anime

El catálogo de anime dispone de un pipeline ETL independiente del funcionamiento normal del sitio:

1. Lee la copia configurada de Excel o una exportación XLSX de Google Sheets.
2. Normaliza formatos equivalentes como `TV`, `Serie TV`, `TV Series` y `Serie`.
3. Contrasta título, año, temporada, capítulos y estado con AniList, Jikan y Kitsu.
4. Conserva el título romanizado como principal y guarda los demás nombres como alternativos.
5. Rechaza automáticamente solo cuando no coinciden tanto el nombre como el año.
6. Envía las demás diferencias a `runtime/anime-sync/pending-review.json`.
7. Publica únicamente registros aprobados en `data/anime.json` mediante escritura atómica.

La fuente se configura en `config/anime-sync.json`. Para una ejecución única:

```bat
python tools\anime_sync_pipeline.py --config config\anime-sync.json --apply
```

`iniciar-sincronizacion-anime.cmd` mantiene la vigilancia activa cada cinco minutos. El estado, la última ejecución y una única copia de recuperación se guardan en `runtime/anime-sync`.

La descarga directa desde Google requiere que la pestaña de catálogo tenga una exportación legible sin sesión o que se configure OAuth. Mientras la hoja permanezca privada, el campo `googleExportUrl` debe quedar vacío y se utiliza la copia local indicada en `workbook`.
