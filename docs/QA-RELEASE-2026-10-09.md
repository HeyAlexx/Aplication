# Verificación previa al PR — 2026-10-09

Entorno de pruebas separado de producción; datos centrales de desarrollo tomados de producción, nunca en sentido inverso. Este informe no afirma que el código ya esté desplegado.

| Prueba | Resultado |
| --- | --- |
| Python, aprobaciones/completitud/almacenamiento/concurrencia | 30 pruebas, OK |
| PHP, revisiones y edición vinculada/alta local | Dos suites, OK |
| Admin responsive (Edge) | 18 escenarios en 9 anchos de 320 a 1920 px, cero errores JS y mutaciones reales |
| Catálogo responsive (Edge) | 27 escenarios, 360 comprobaciones, cero fallos registrados |
| API HTTP aislada | Autenticación, CSRF, roles, favoritos, estados, edición/alta/ocultación y rutas privadas: OK |
| Teléfono físico | Usuario confirmó panel, teclado/desplazamiento y Editar/Ocultar sin bloqueo/recorte |
| Google Sheets de desarrollo | Edición PHP y aprobación PHP → catálogo/cola → Google → lectura de confirmación: OK |
| Alta local sin fila de Sheets | OK; no aumentó el número de filas |
| Restauración tras prueba live | Valores y tipos numéricos originales restaurados, OK |
| MAL, AniList, Kitsu y Watchmode películas/series | Consultas reales de lectura: OK |
| Jikan | Timeout de conexión en ronda y reintento; NO validado saludable |
| Búsqueda anime con fallback | Respondió AniList ante timeout de Jikan |

Concurrencia real PHP/Python verificada en ambos sentidos; ocho ediciones PHP simultáneas conservaron ocho filas. El diario interrumpido recuperó catálogo y cola en ambos lenguajes. Una aprobación durante lectura remota invalida la sincronización sin sobrescribir la decisión. Monitores de un mismo entorno se excluyen, otro entorno puede operar independientemente.

La prueba de Sheets utilizó un catálogo descartable y una fila ya existente de la hoja **de desarrollo**. No copió OAuth ni modificó la hoja/catálogo de producción. Se conservaron validaciones y formato de celdas; lectura de valores/metadatos antes y después, sin redimensionar columnas ni editar fórmulas. En la primera ejecución falló el alta ficticia por reutilizar un ID: se corrigió el fixture y se repitió completa, con restauración verificada en ambas ejecuciones.

## Evidencia local (no publicar)

- `outputs/qa-admin/report.json`, capturas móvil/tablet/escritorio.
- `outputs/qa-responsive/report.json`, capturas y trazas de tres tamaños.
- `outputs/api-workflow-report.json` (ver ruta generada por el script si cambia).
- `outputs/qa-writeback/<fase>/report.json` y `restore-original.json`.
- `outputs/providers-live-report.json` y `providers-retry-report.json`.

Los reportes/capturas son artefactos generados, no credenciales ni archivos para Git. Los snapshots fuera del repositorio contienen datos/configuración privados.

## Límites y decisiones de liberación

- No se probó Safari/iOS ni Firefox físico. La emulación Edge no representa todos los navegadores.
- El administrador responsive usa sesión/respuestas simuladas; permisos y persistencia se validaron aparte mediante HTTP real en fixture aislado.
- Las portadas/metadatos incompletos no se inventan. Consultas actuales de Jikan fallaron; investigar disponibilidad/conectividad y revalidar antes de afirmar salud completa de proveedores.
- API/código probado aquí no cambia `main` ni producción. PR revisado, instalación del código, arranque de monitor nuevo y smoke test de producción siguen siendo pasos de liberación, no resultados de esta ronda.
- Recuperación de archivos verificada no equivale a respaldo completo de sistema; no incluye sesiones PHP/dependencias.

Comandos reutilizables: `python -m unittest discover -s tests -p 'test_*.py'`, `php tests/catalog-sheet-writeback.php`, `php tests/anime-review-service.php`, `node tests/admin-content-responsive.cjs`, `node tests/catalog-responsive-matrix.cjs`, `node tests/api-workflow.cjs`. Playwright/PHP/Python deben estar instalados. La prueba `tests/sheets-roundtrip-live.py` es opt-in: exige configuración, ID explícito de hoja de prueba y código existente; modifica/restaura esa fila y no debe ejecutarse contra producción.
