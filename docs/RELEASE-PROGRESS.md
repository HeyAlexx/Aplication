# Avance de preparación para GitHub y producción

Actualizado: 2026-10-19. Punto de reanudación tras la aprobación final del usuario.

## Límites vigentes

- Publicar solo código, pruebas y documentación mediante commits selectivos y PR.
- Paso 6 autorizado por el usuario el 2026-10-19: integrar e instalar el código revisado y usar la sincronización de novedades de producción como prueba final. Esto no autoriza aplicar la migración histórica pendiente ni aprobar revisiones reales manualmente.
- Google Sheets seguirá apagado durante la instalación; ejecutar primero una sincronización controlada de producción solo después de validar el código instalado. No iniciar sincronización de desarrollo ni usar el launcher raíz indiscriminadamente.
- No copiar datos de desarrollo a producción, ni publicar configuración privada, OAuth, usuarios, favoritos, historial, catálogos operativos o respaldos.
- Mantener Cloudflare Access. Conservar los cambios locales de producción; no usar reset/checkout forzados.

## Pasos numerados actuales

| Paso | Trabajo | Estado |
| --- | --- | --- |
| 1 | Revisión final del usuario en desarrollo | APROBADO |
| 2 | Respaldo, auditoría, commits selectivos, push y PR | COMPLETADO; PR #3 en borrador |
| 3 | Preparar instalación de código conservando producción sucia | COMPLETADO; paquete y ensayo aislados, sin desplegar |
| 4 | Vista previa y migración histórica propia de producción | PREPARACIÓN/ENSAYO COMPLETADOS; aplicación real pendiente |
| 5 | Respaldo final, copia independiente y recuperación coordinada | COMPLETADO; ZIP independiente y restauración integral aislada aprobados |
| 6 | Despliegue autorizado y smoke test protegido | CÓDIGO INSTALADO Y VALIDADO; primera sincronización real en curso |

6.6: primera sincronización real completada (13:21:37–13:32:56, Costa Rica), tras renovar OAuth de producción. 808 registros de la hoja: 781 anteriores y 27 nuevos, sin duplicados/faltantes. Los 27 comparten fecha real de lote, 23 con metadatos verificados y cuatro con revisión (tres pendientes, uno rechazado automático); los datos siguen presentes. Catálogo: 811 animes y 836 contenidos. Comparación fresca de hoja/espejo/estado y reejecución idempotente aprobadas, sin cambios de fechas ni catálogo en el segundo pase. Orden nuevo del lote 4497→4471 y UI real en 360/820/1440 px correctos. Cero devoluciones a Sheets: esta prueba NO demuestra writeback real de producción. Sin monitor continuo.

6.6a: se detectó que un lote incremental eliminaba revisiones pendientes de códigos no procesados. Se recuperó exactamente la revisión 4462 del respaldo previo de producción, conservando las cuatro nuevas, sin aprobación ni escritura Sheets. Corrección con pruebas de regresión en preparación: conservar pendientes ajenas al lote; retirar solo casos reprocesados/resueltos o retirados de la fuente, conservando decisiones manuales.

6.7: el usuario autorizó expresamente aplicar el histórico SOLO a los 781 anteriores, protegiendo las 27 altas reales y los tres registros previos sin fila actual de espejo (dos conservan códigos huérfanos). Nuevo procedimiento `tools/production_history.py`: baseline verificado de producción, plan/hash y código del plan fijados, ensayo de orden de los 808 vinculados, PHP detenido, exclusión con el watcher y respaldo independiente obligatorio en F: antes de escribir. La utilidad original de desarrollo sigue bloqueada para producción. Aplicación real aún pendiente de cierre del ensayo/instalación de esta corrección. No usar la propuesta vieja contra los 811 actuales ni copiar datos de desarrollo.

El usuario aceptó continuar con el riesgo del BSOD aún sin causa identificada y el timeout de Jikan, condicionado al fallback y demás pruebas correctos. MAL/AniList/Kitsu/Watchmode y búsqueda con fallback AniList respondieron; 64 pruebas Python, 10 Node, dos suites PHP y 38 comprobaciones HTTP aisladas pasan. Snapshot previo de 572 archivos verificado. PR #3 integrado en `main`, commit `750dcc72278b4aaa7008c3b12521960b28ba1591`. Paquete final de 126 archivos ensayado y después instalado con originales/diario preservados; 31 archivos protegidos intactos y cero diferencias en los 126 hashes instalados. No se cambió la rama/HEAD de la instalación sucia: el SHA real instalado se registra fuera de Git.

Sobre HTTP de producción: 27 escenarios de catálogo / 360 comprobaciones y 18 escenarios de admin simulado aprobados, sin escrituras reales. Nueve rutas privadas responden 404, health 200 y Access 302. Evidencia y capturas por fase en `work/release-operations/20261019-122657-734`; informe del instalador en el plan `20261019-122522-634007-750dcc72278b/deployment-20261019-122704-086314`. Ambos servidores reanudados; no hay monitor Sheets. La aplicación real del histórico del paso 4 sigue pendiente de autorización y procedimiento específico. No marcar el paso 6 completo mientras no pase la prueba final de sincronización.

Incidente del 19 de octubre: apagado inesperado a las 10:26:44 y arranque a las 10:27:26 (Costa Rica), durante una captura local todavía `INCOMPLETE`. Ninguna de las tres carpetas anteriores de F: es un respaldo completo. No se restauró ni sobrescribió información operativa. Tras reiniciar: 24 archivos del baseline conservan SHA-256; catálogos de ambos entornos y espejo conservan sus hashes; JSON válidos, sin diarios pendientes, `git fsck` sin errores. Servidores reanudados con HTTP 200, túnel protegido por Access (302), sin monitor Sheets. Registro `0x124`, parámetro `0x10`: componente responsable no identificado. Los eventos SATA 129 anteriores no demuestran causalidad. Ver [recuperación coordinada](COORDINATED-RECOVERY.md).

Paso 5 repetido y completado el 19 de octubre, 10:48–10:58 (Costa Rica): 19.072 archivos / 3.114.526.734 bytes capturados directamente en ZIP de F:, sin copia completa intermedia en C:. CRC, SHA-256 e inventario verificados; pausa de HTTP 10:48:28–10:53:03. Restauración integral independiente en carpeta nueva de C:, hashes finales y objetos Git correctos; PHP CLI lee nueve colecciones centrales y cinco privadas por entorno, cuatro JSON de estado de producción y 809 contenidos por entorno. Cero peticiones Google y ninguna sesión restaurada activada. 59 pruebas Python y sintaxis PHP/PowerShell pasan. Ambos HTTP 200, Access 302 y cero monitores al cerrar; 24 hashes del baseline intactos. Respaldo privado `F:\Altoidss-Backups\20261019-104819-739-step5`, estado `BACKUP_AND_RECOVERY_VERIFIED`; ensayo `work/recovery-drills/coordinated-20261019-105306-379273/report.json: PASSED`. Este punto de recuperación precede al commit de documentación de cierre; no es una imagen del sistema ni resuelve el origen del BSOD.

Paso 4: propuesta nueva desde producción, sin Google ni datos de desarrollo como origen. 781 vinculados estimados, tres locales intactos, 20 candidatos de siguiente fila y 33 ajustes de secuencia; ocho fechas previas vinculadas ignoradas para ordenar, conservadas en auditoría. Informe idéntico por hash a la v4 ya validada; cero diferencias en cuatro campos de incorporación frente a los 781 vinculados de desarrollo. Ensayo sobre copia: orden completo en ambos sentidos, reejecución idempotente y ocho colecciones ajenas intactas; 31 archivos protegidos reales sin cambios. CLI de producción sigue bloqueada. 47 pruebas Python y 10 Node pasan. Ver [PRODUCTION-HISTORY-PLAN.md](PRODUCTION-HISTORY-PLAN.md). Evidencia privada: `work/historical-production-previews/20261019-090944-280-preview/`.

Paso 3: paquete del commit `71d96c14eb6072471d915ff167fb11e3949f2270`, 112 archivos permitidos. Se preservaron/revisaron 14 cambios locales de producción; 532 entradas de dependencias/generados quedan fuera. Ensayo PHP CLI con nueve colecciones copiadas de producción: 809 contenidos, 781 códigos de espejo presentes, cero inicializaciones históricas y ningún cambio en 31 archivos protegidos reales. No se copiaron cuentas/credenciales al ensayo ni se inició red/Sheets. Procedimiento y revisión archivo por archivo: [INSTALLATION-PLAN.md](INSTALLATION-PLAN.md). El código finalmente aprobado exigirá regenerar el plan y verificar los hashes del momento.

Validación del cierre: 41 pruebas Python (siete nuevas), dos suites PHP previas y arnés PHP aislado aprobados; se comprobó que el arnés rechaza la instalación real. Evidencia privada: `work/installation-plans/20261019-090139-850634-71d96c14eb60/manifest.json` y `rehearsal/report.json`. Es una preparación compatible con los datos actuales, no una instalación ni una migración realizada.

Publicado: [PR #3](https://github.com/HeyAlexx/Aplication/pull/3), rama `fix/admin-mobile-mockup` hacia `main`, abierto como borrador y sin conflictos informados por GitHub. Commits funcionales `7ed9977` (almacenamiento/orden) y `a930dd4` (interfaz); documentación inicial `6b053de`. No hay estados de CI ni ejecuciones de Actions en la comprobación remota; las pruebas son locales. Los tres JSON personales modificados permanecen sin commit.

Antes del push se repitieron 34 pruebas Python, 10 Node, dos suites PHP, 38 comprobaciones API, 18 escenarios admin y la verificación de las 781 referencias servidas en ambos sentidos. Sintaxis válida en 34 archivos JS/PHP/PowerShell. Auditoría de rutas/credenciales conocidas sin hallazgos; 37 archivos de datos/estado/preferencias iguales al respaldo. Servidores de producción/desarrollo activos, ningún monitor de Sheets.

## Estado comprobado el 2026-10-19

Proyecto trasladado al SSD en C: y verificado por hashes. No seguir trabajando sobre la copia antigua de G:. Código de desarrollo en rama `fix/admin-mobile-mockup`; instalación de producción conservada en `chore/dev-isolation`.

Ambos servidores responden y el acceso externo de producción sigue protegido. Ningún monitor de Sheets está activo. La comparación de datos se hizo contra la copia local de la hoja, no contra sus cambios nuevos: 784 animes, 781 códigos vinculados sin faltantes, 15 películas, 10 series y 4 noticias. Los tres animes adicionales son locales.

Desarrollo tiene 781 referencias históricas inicializadas; producción todavía no. Sus diferencias de fechas son deliberadas y no deben resolverse copiando datos de prueba. El inicializador actual rechaza producción: su futura migración requiere preparación y aprobación propias.

Pruebas repetidas: 34 Python, 10 Node, dos suites PHP, 38 comprobaciones de API aislada, 18 escenarios de administrador y 27 de catálogo (360 comprobaciones), además de orden histórico, controles táctiles y lectura de producción en tres tamaños. No se realizaron escrituras reales en Sheets en esta repetición.

MAL, AniList, Kitsu y Watchmode respondieron. Jikan agotó el tiempo de espera, también en reintento; el fallback AniList pasó. No declarar todas las APIs saludables.

## Respaldos y recuperación

Respaldo previo a commits: fase `before-selective-release`, 2026-10-19, 491 archivos con hashes verificados. Es privado y está fuera del repositorio. El snapshot conserva ambos checkouts, catálogo y estado central; la copia se hace secuencialmente y no ofrece un punto transaccional único si hay escritores activos.

El ensayo de restauración del 2026-10-19 recuperó ocho JSON de catálogo en una ubicación aislada. No demuestra recuperación completa de cola, revisiones, OAuth, sesiones o sistema. Antes de desplegar falta un ensayo coordinado con escritores detenidos y una copia independiente del SSD. Un BSOD o fallo físico no queda resuelto solo con Git o escrituras atómicas.

## Decisiones históricas ya cerradas

- Las 46 referencias faltantes se recuperaron; la comparación local cubre los 781 códigos vinculados.
- La inicialización histórica se aplicó solo en desarrollo el 2026-10-09: año y quarter literal de I/J, nunca temporada activa; referencias estimadas marcadas con `≈`, sin cambiar filas de Sheets.
- Las 781 posiciones relativas respetan el orden de filas; primeros códigos 4470, 4469, 4468, 4467 y 4466 en orden descendente.
- Las fechas previas vinculadas no deciden el orden histórico; se conservan en auditoría. Las altas locales conservan sus fechas originales.
- Futuras altas: fecha real de app; para Sheets, fecha común del primer lote y fila interna congelada. Ediciones y resincronizaciones no reinician esa fecha.
- El usuario confirmó el funcionamiento físico de filtros, desplazamiento con teclado y Editar/Ocultar; posteriormente aprobó la revisión final.

Vistas previas antiguas v1/v2/v3 fueron sustituidas por v4 y la inicialización autorizada. No son decisiones pendientes. Evidencia detallada en [histórico](INCORPORATION-HISTORY.md), [auditoría de orden](ORDER-AUDIT-2026-10-09.md) y [QA vigente](QA-RELEASE-2026-10-19.md).

## Documentación de operación

- [Ramas, datos centrales y diagramas](CATALOG-STORAGE.md)
- [Despliegue y reversión, con compuerta de autorización para Sheets](DEPLOYMENT-CENTRAL.md)
- [QA anterior, evidencia histórica del 9 de octubre](QA-RELEASE-2026-10-09.md)
