# Cierre del despliegue — 19 de octubre de 2026

Estado comprobado a las 16:11, Costa Rica. Este informe sustituye los estados
«pendiente» de las bitácoras de preparación anteriores, no sus evidencias.

## Pasos y resultado

| Paso | Resultado |
| --- | --- |
| 1 | Revisión física/final de desarrollo aprobada por el usuario |
| 2 | Código integrado mediante PR #3 y #4, con commits selectivos |
| 3 | Paquete final de 128 archivos instalado; hashes verificados; instalación sucia y datos privados preservados |
| 4 | Histórico de 781 registros de producción aplicado con autorización específica, respaldo y ensayo |
| 5 | Respaldo completo en F: y restauración integral aislada aprobados; checkpoint posterior verificado |
| 6 | Importación real, repetición idempotente, comprobaciones HTTP/UI y sincronizador único de producción activos |

Código operativo instalado: `7af617fef113c1ac23a5732b2e28bc473e91e675`.
El HEAD del checkout de producción se conserva: no identifica por sí solo el
código operativo, instalado desde un paquete verificado. Un commit posterior
de documentación no cambia este SHA de ejecución.

## Datos y fechas

- La hoja actual tiene 808 filas vinculadas, presentes una sola vez en el JSON.
- Hay 811 animes: 781 anteriores inicializados, 27 nuevos con fecha real del
  primer lote y tres registros previos excluidos del histórico. Dos de estos
  últimos conservan códigos huérfanos; no son tres altas locales nuevas.
- Las 27 altas conservan `2026-10-19T13:21:37.934088-06:00` y su fila congelada.
- Los 781 históricos mantienen año I/quarter J y el orden de filas en ambos
  sentidos, con estimaciones identificadas y fechas originales auditadas.
  No se cambió ni renumeró ninguna fila de Google.
- La migración delimitada conserva metadatos, IDs y orden físico del JSON.
  Los 27 nuevos y los tres excluidos permanecieron intactos; su reejecución
  devolvió `already-initialized`. Otra consulta real de Google no deshizo las fechas.
- 23 altas nuevas quedaron verificadas; tres requieren revisión y una fue
  rechazada automáticamente por metadatos. Sus datos fuente siguen presentes.
  Se recuperó una revisión anterior (4462), sin aprobarla. Resultado: cuatro
  pendientes y un rechazo automático, cola de devoluciones vacía.
- La corrección de PR #4 conserva revisiones de códigos ajenos al lote
  incremental; no pierde pendientes solo porque otra fila haya cambiado.
- Producción contiene además 15 películas, 10 series y cuatro noticias:
  836 contenidos audiovisuales, sin contar noticias.

Plan histórico aprobado, SHA-256:
`86f10f1c965741327c32c07b677044dcf855b859ce7a5ad6b0e72b54c9a545c0`.
Migración: `29764cc82e9b9283d30065b7755950b61edb4209b51d4c853e6ddaae69277ff9`.
SHA-256 de `anime.json` después:
`ff97ccb39a4295ef19fd4f32d8b8962461fe7603a0fd2ddff0dbab4008fa0259`.

## Operación autorizada

El usuario autorizó **un sincronizador de producción** con
`--apply --watch --interval 300`. Inició a las 15:56; se comprobaron identidad
del proceso, PID registrado, reporte posterior al arranque y repeticiones
posteriores sin errores. El reporte de las 16:06:13 indica `unchanged`,
808 filas, cero faltantes y cero devoluciones. Esto es más que comprobar un PID.

Los 300 segundos son la espera **después** de finalizar cada ejecución, no
una garantía de que cada lote termine en cinco minutos. Un lote con consultas
externas lentas puede prolongar el ciclo. No hay arranque automático tras
reiniciar Windows configurado como parte de este cierre: después de un BSOD
se debe revisar el estado y arrancar una sola instancia.

Desarrollo permanece sin Google. Se renovaron únicamente sus siete colecciones
públicas desde producción, de forma unidireccional y transaccional; se verificó
igualdad semántica de las siete y hashes idénticos de anime/espejo. Usuarios,
preferencias, revisiones, cola, estado y credenciales propios no se copiaron.
No se transfirió ningún dato de desarrollo a producción. Una nueva rama usa
el descriptor externo del entorno, no los JSON antiguos versionados; ver los
diagramas de [almacenamiento central](CATALOG-STORAGE.md).

Producción local: `127.0.0.1:8091`; desarrollo LAN:
`http://192.168.100.19:8092/Html/catalogo.html`.
Ambos HTTP 200; nueve rutas privadas 404; acceso externo redirige a
Cloudflare Access (302). No se retiró la protección.

## Validación y límites

75 pruebas Python, 10 Node, dos suites PHP y 38 comprobaciones HTTP aisladas
aprobadas. Sobre producción instalada: 27 escenarios de catálogo/360
comprobaciones y 18 escenarios de administrador con autenticación/datos
simulados, sin escrituras reales. Repetición con los datos finales a
360/820/1440 px: 811 animes, primero 4497, sin desbordamiento ni errores JS.
La prueba física del usuario es una evidencia anterior aprobada; la emulación
no equivale a repetir pruebas físicas en todos los navegadores.

MAL, AniList, Kitsu y Watchmode respondieron; fallback AniList aprobado. Jikan
agotó el timeout, salvedad aceptada. El flujo por registro sigue consultando
AniList → Jikan → Kitsu, sin corte anticipado ni circuit breaker. Cada intento
usa timeout de operación de 35 s, no un plazo global del lote. No se modificó
esta política. La primera importación tardó aproximadamente 11 min 19 s.

No se aprobó ninguna revisión real como prueba ni se escribió una celda de
Sheets en este despliegue. La importación real pasó; el recorrido completo de
writeback de producción todavía no se ejercitó, porque la cola estaba vacía.
Las pruebas aisladas de aprobación/cola no sustituyen esa evidencia real.

El origen del BSOD continúa sin identificar. El usuario aceptó proceder con
esta limitación; las pruebas y copias verificadas no prueban salud del hardware.

## Recuperación y evidencia privada

Base completa: `F:\Altoidss-Backups\20261019-104819-739-step5\project.zip`,
19.072 archivos, CRC/SHA verificados y restauración integral aislada aprobada.
Antes del histórico se verificaron 31 archivos protegidos en la subcarpeta
`history-before-781-20261019`.

Checkpoint final: subcarpeta `post-deployment-7af617fef113`, estado `VERIFIED`:
54 archivos de datos/estado/configuración, ZIP de 128 archivos de código,
Git bundle verificado y 88 evidencias. Es un **delta sobre la base completa**,
no una nueva imagen completa ni del sistema operativo. El bundle precede al
commit de documentación de cierre. F: es otro disco físico interno; la copia
está protegida por ACL, pero no cifrada ni offline.

Evidencia no publicable, bajo `work/`:

- `release-operations/20261019-122657-734`: instalación inicial, importación y capturas.
- `historical-production-previews/scoped-20261019-143241-424005`: plan, ensayo y aplicación.
- `release-operations/20261019-144608-722`: instalación final, renovación de desarrollo y reporte de verificación del sincronizador.
- `release-operations/sheet-probe-20261019-132051-639062`: lecturas/conciliación de la fuente.

Tras una interrupción, empezar por comprobar JSON/diarios, reporte reciente,
identidad del proceso y puertos; no reutilizar PIDs, borrar bloqueos ni
restaurar automáticamente JSON antiguos encima de altas posteriores.
Ver [recuperación coordinada](COORDINATED-RECOVERY.md) y
[reversión segura](DEPLOYMENT-CENTRAL.md).
