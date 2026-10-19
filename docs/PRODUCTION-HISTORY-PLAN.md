# Paso 4 — histórico propio de producción, preparado y ensayado

Fecha: 2026-10-19. **Aplicación real autorizada, pendiente de ejecución delimitada.** La CLI original del inicializador sigue bloqueada para producción. La sección 4.6 describe el nuevo procedimiento específico tras incorporar novedades reales.

## 4.1 Origen y regla

La propuesta se generó de nuevo leyendo exclusivamente `datos/produccion/catalogo/anime.json` y `anime-hoja.json`: 784 animes y 781 códigos de la copia local de la hoja, sin faltantes. No se importó el JSON de desarrollo ni se consultó Google. Los cambios recientes que el usuario mantiene en espera no forman parte de esta propuesta.

Regla ya aprobada para el histórico: todos los vinculados se ordenan por referencias estimadas a partir de año literal I, quarter J y secuencia de filas. La temporada activa G no interviene. Se ignoran para ordenar ocho fechas previas vinculadas, pero no se borran: siguen en los registros y en auditoría. Los tres registros locales se conservan íntegros; uno tiene fecha real y dos permanecen sin referencia.

Se mantiene el límite de recuperación documentado `2026-10-09T00:58:35-06:00`, no la fecha de ejecución de este ensayo. No es una fecha histórica de alta. Las estimaciones aparecen como `≈`. Para futuras altas se conserva fecha real de app o primera incorporación del lote y fila interna congelada; esta heurística no se repetirá durante sincronizaciones.

## 4.2 Resultado esperado

781 referencias estimadas; 20 candidatos de referencia a la siguiente fila y 33 ajustes adicionales para mantener fechas no decrecientes al recorrer las filas. Ninguna referencia necesitó limitarse por la fecha de recuperación. Las 781 posiciones vinculadas coinciden con el orden de filas en ambos sentidos.

| Código | Fila del espejo, sin cambios | Posición actual en catálogo | Posición propuesta en catálogo | Referencia estimada |
| --- | --- | --- | --- | --- |
| 4470 | 785 | 10 | 1 | 2026-10-01 |
| 4469 | 784 | 11 | 2 | 2026-10-01 |
| 4468 | 783 | 12 | 3 | 2026-10-01 |
| 4467 | 782 | 13 | 4 | 2026-10-01 |
| 4466 | 781 | 14 | 5 | 2026-10-01 |

Las columnas de posición describen presentación en la app, NO filas de Sheets. No se movió, renumeró ni escribió ninguna fila. Los días/horas de referencia no demuestran cuándo se agregó realmente un título.

La propuesta resultó idéntica por SHA-256 a la v4 que se validó para desarrollo: `0b763a3c3fcb266d3c78d28fa2c7de92aa352e73592c15e768ad60ffa4011079`. Esto se comprobó después de generarla desde producción; no se usó el catálogo de desarrollo como origen. Comparación adicional de `incorporatedAt`, `sheetImportBatchId`, `sheetImportRow` y `incorporationDateBasis` en 781 vinculados: cero diferencias con las referencias ya inicializadas en desarrollo. La fecha de ejecución/auditoría de una migración nueva será propia de esa operación.

## 4.3 Ensayo aislado

`tools/rehearse_production_history.py` exige una propuesta guardada en `work/historical-production-previews`, comprueba sus hashes contra producción y crea una carpeta nueva de ensayo. No ofrece opción de aplicación real ni copia cuentas, credenciales o configuración OAuth. Rechaza una propuesta obsoleta, un diario pendiente en producción o una salida fuera de la zona privada.

Se copiaron nueve colecciones y se ejecutó el motor de inicialización únicamente sobre esa copia, con respaldo exacto y etiqueta `isolated-rehearsal`. El motor no admite etiqueta `produccion`; la CLI continúa aceptando solo el descriptor de desarrollo. No intentar eludir esa protección cambiando etiquetas o importando el motor contra el catálogo real.

Resultado comprobado:

- 781 registros vinculados inicializados en la copia; tres locales idénticos.
- Mismos IDs, orden físico del JSON, códigos, filas, metadatos, estrenos y fechas originales.
- Auditoría de fechas/fila originales presente en cada vinculado.
- Orden nuevo/antiguo idéntico a todas las filas vinculadas usando el comparador real de la app.
- Reejecución: `already-initialized`, cero cambios.
- Otras ocho colecciones sin cambios, incluidos espejo, revisiones y cola.
- Los 31 archivos protegidos reales de producción permanecen iguales.
- La CLI rechazó el descriptor de producción antes de crear respaldo o escribir datos.

Validación: 47 pruebas Python (seis nuevas del ensayo) y 10 Node aprobadas. Las seis pruebas nuevas cubren aislamiento/idempotencia, propuesta obsoleta, límites de ruta, diario pendiente, conservación de metadatos/locales y rechazo de etiqueta de producción. Las pruebas Node validan el método de quarter y la secuencia de filas.

## 4.4 Evidencia privada y repetición

Vista previa: `work/historical-production-previews/20261019-090944-280-preview/historical-order-preview.{json,md}`. Ensayo: subcarpeta `rehearsal-20261019-091335-682435`, con `report.json`, catálogo simulado y respaldo. El detalle contiene datos: no subir estos artefactos a GitHub ni servirlos por HTTP.

Ejemplo, desde desarrollo, con rutas propias y una salida nueva:

```powershell
node tools/historical-order-preview.cjs RUTA_PROD_ANIME_JSON RUTA_PROD_ESPEJO_JSON 2026-10-09T00:58:35-06:00 RUTA_INFORME_PRIVADO --rebase-sheet-history
python tools/rehearse_production_history.py --report RUTA_INFORME_PRIVADO/historical-order-preview.json
```

## 4.5 Aplicación real pendiente

La preparación/ensayo del paso 4 está terminada; **la migración real no está aplicada ni habilitada**. Continuar con el respaldo independiente y la recuperación coordinada del paso 5. Antes de cualquier aplicación real se necesita revisar la propuesta, autorizar esa operación y disponer de un procedimiento de producción específico con escritores detenidos, código compatible instalado, hashes vigentes, respaldo verificable y reversión.

No basta autorizar el despliegue de código o ejecutar la utilidad de desarrollo. Si se cargan cambios nuevos de Sheets o se edita el catálogo antes, esta propuesta queda obsoleta: regenerar, revisar y volver a ensayar sobre los nuevos datos. No reutilizarla para sobrescribir altas posteriores. Una reversión debe preservar ediciones nuevas y tratar conjuntamente catálogo, revisiones y cola; ver [despliegue](DEPLOYMENT-CENTRAL.md) y [avance numerado](RELEASE-PROGRESS.md).

## 4.6 Alcance posterior a la sincronización real, autorizado

La primera sincronización de producción añadió 27 registros con fecha real de lote.
El usuario autorizó inicializar solamente los 781 anteriores, dejando intactas
esas altas y los tres registros previos fuera del espejo. Dos de esos tres
conservan códigos antiguos huérfanos: se identifican por IDs del baseline, no
por tener `sourceCode` vacío. Hay 811 animes y 808 filas vinculadas actuales.

`tools/production_history.py prepare --baseline RUTA_SNAPSHOT_PRODUCCION/production-central/catalogo/anime.json`
comprueba el manifiesto/hashes del snapshot, selecciona los 781 antiguos desde
su espejo y compara literalmente sus filas contra el espejo actual. Estima
solo ese grupo por año I/quarter J, con el mismo límite histórico del 9 de octubre.
Ensaya la combinación completa y su orden con el comparador real de la app;
ningún metadato, fila, estreno o registro fuera del grupo puede cambiar.

El plan fija hashes de datos, propuesta e implementación. Para aplicar, PHP
de producción debe estar detenido; la CLI exige `apply --plan RUTA_PLAN
--approved-plan-sha SHA_PLAN --independent-backup CARPETA_NUEVA_EN_F`.
Se excluye al watcher, se rechazan diarios/colas pendientes, se copian y verifican
todos los archivos protegidos en F: **antes** de la primera escritura, y solo
entonces se confirma `anime.json` mediante diario transaccional. Es un
procedimiento nuevo de producción, no un cambio de etiqueta para eludir el
inicializador original. La reejecución no modifica una aplicación ya verificada.

Las referencias estimadas quedan marcadas como históricas y conservan auditoría
de las fechas originales. Los 27 `initial-sheet-sync` reales no se recalculan.
No se escribe ninguna celda de Sheets, no se usa el catálogo de desarrollo y
no se aplican propuestas obsoletas. Se requiere autorización explícita; un
plan preparado no prueba que se haya aplicado.
