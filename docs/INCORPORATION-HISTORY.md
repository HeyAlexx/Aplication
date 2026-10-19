# Incorporación: histórico inicial y futuras altas

**Estado actual: inicialización APLICADA SOLO EN DESARROLLO el 2026-10-09 a las 02:43:52 -06:00**, tras aprobación del usuario. 781 registros vinculados inicializados, con los originales preservados en auditoría/respaldo. No se movió ninguna fila ni se escribió Sheets. Producción conserva su catálogo anterior. Las variantes de vista previa de las secciones siguientes explican el método aprobado, no una migración todavía pendiente.

## 1. Decisión confirmada — 2026-10-09

La estimación por **año y quarter (trimestre)** y referencia de la siguiente fila se limita a la **inicialización del histórico**. Quarter y temporada activa son datos diferentes: la temporada activa NO participa. No es un cambio a los datos de estreno ni una fecha histórica demostrada. No debe ejecutarse de nuevo en cada sincronización, en cada rama ni al editar metadatos.

Decisión posterior: inicializar **todos** los registros vinculados a la hoja, ignorando sus fechas de incorporación anteriores para presentar el histórico en orden de filas. Los registros locales de app conservan sus fechas. El orden de filas es autoritativo; año/quarter solo orienta las referencias estimadas y debe ajustarse si contradice esa secuencia. Los campos originales de fechas no se borran en la propuesta: `incorporatedAt` pasa a tener prioridad para el orden, con procedencia explícita. Esto no autoriza cambiar el estreno, escribir Sheets ni copiar desarrollo a producción.

Para el resto se mantiene la regla solicitada:

1. Alta en la app: conservar su fecha real de creación/importación. Editar o aprobar después no la reinicia.
2. Primera incorporación de un lote nuevo de Sheets: una fecha real de primera sincronización para todos los registros nuevos del lote, capturada antes de las consultas a proveedores.
3. Orden interno del lote: congelar la fila de incorporación; la fila actual puede actualizarse como referencia de Sheets sin cambiar el orden original del lote.
4. Nuevos lotes y altas de app comparten una cronología. Una alta a las 01:50 precede a un lote a las 01:51 en orden antiguo primero; en más recientes primero el lote va antes. Una alta posterior a las 01:52 va delante del lote.

La fecha de sincronización posterior, la edición y la aprobación no son nuevas incorporaciones.

## 2. Vista previa histórica, todavía sin aplicar

Herramienta de solo lectura: `tools/historical-order-preview.cjs`. No tiene modo de aplicación ni acceso de red. Lee el catálogo y su espejo; utiliza el mismo comparador de presentación para simular el resultado. Comprueba las huellas de entrada y escribe informes fuera de los directorios de datos.

Regla actual de la vista previa v3 (`--rebase-sheet-history`):

- Se inicializan referencias de incorporación para los 781 vinculados, tengan o no fecha previa. Las fechas previas se muestran en el informe para auditoría, pero no ordenan. Solo se conservan como referencia activa las fechas de registros locales sin vínculo.
- Históricos sin fecha: año literal de columna I (`raw[8]`) y quarter de columna J (`raw[9]`) del espejo de Sheets. Q1→enero-marzo (ancla enero), Q2→abril-junio (abril), Q3→julio-septiembre (julio), Q4→octubre-diciembre (octubre). Día 1 y hora 00:00 son anclas técnicas, **no precisión histórica**; la interfaz final deberá distinguirlas de fechas reales.
- Columna G (`raw[6]` / `activeSeason`, p. ej. S01, S02) es la temporada activa de emisión: no se usa para estimar fechas. El importador tiene el nombre heredado `emissionSeason` para normalizar quarter 1–4 a Winter/Spring/Summer/Fall; la vista previa ya no depende de ese nombre ambiguo ni de valores enriquecidos de proveedores. No se renombra el esquema de sincronización en este cambio.
- Si la referencia año/quarter de un registro es estrictamente anterior a la de AMBAS filas adyacentes, se propone el año/quarter de la siguiente fila y se marca para revisión. Es una detección provisional de un título antiguo aislado, no una inferencia demostrada. No identifica por sí sola bloques antiguos, extremos ni casos ambiguos: esos quedan sujetos al ajuste de secuencia siguiente, no a una supuesta fecha histórica recuperada.
- Ajuste de secuencia adicional: recorrer filas de arriba abajo; si una referencia retrocede, tomar la referencia efectiva de la fila anterior y registrar esa procedencia. Si falta año/quarter, usar esa referencia anterior o la siguiente válida cuando todavía no exista anterior. La fila original resuelve empates. No inventar segundos para forzar posiciones. Esto garantiza fechas no decrecientes por fila y, por tanto, el mismo orden de filas descendentes en «Más recientes». Fallar si faltan registros, hay duplicados, no existe ninguna referencia válida o la secuencia completa no coincide.
- Referencias estimadas futuras se limitan por la recuperación documentada `2026-10-09T00:58:35-06:00`. Ese límite no sustituye por sí solo todas las fechas históricas.
- Registro local sin fecha: pendiente, sin inventar referencia ni vincularlo por parecido de título.

Cowboy Bebop actual es local y tiene `importedAt`: se conserva. No se usa como prueba de un título antiguo insertado entre filas de Sheets.

Resultado de la vista previa v3 del catálogo de desarrollo: 784 animes, 781 códigos del espejo, cero códigos faltantes; **781 referencias estimadas, 8 fechas anteriores de Sheets ignoradas para ordenar, 1 fecha local conservada**, 20 propuestas de siguiente fila, 33 ajustes adicionales por secuencia, 2 locales sin referencia, cero fechas limitadas por recuperación. Las **781 posiciones relativas vinculadas coinciden exactamente con filas descendentes**. Nueve pruebas Node pasan, incluidas independencia de S01/S09, fechas anteriores ignoradas, bloques antiguos y quarter ausente sin alterar los originales.

La variante anterior v2 conservaba fechas de Sheets y dejaba 4470 cuarto: **queda sustituida por v3**. En v3 los primeros códigos son **4470, 4469, 4468, 4467 y 4466**. Los locales pueden intercalarse según sus fechas reales; no pertenecen a la secuencia de la hoja. Una estimación ajustada por fila no demuestra una fecha de incorporación real ni debe mostrarse como tal.

Informes privados, no publicar el catálogo íntegro en GitHub:

- `work/diagnostics/historical-order-preview-20261009-v4/historical-order-preview.md` (en la raíz del workspace; mismo algoritmo v3, encabezados aclarados).
- `work/diagnostics/historical-order-preview-20261009-v4/historical-order-preview.json` (detalle de las 784 posiciones y referencias).

En los informes «Posición propuesta/actual en catálogo» significa puesto dentro de la lista «Más recientes», incluyendo locales, **no número de fila de Sheets**. La columna «Fila de Sheets (sin cambios)» muestra la referencia original. Casos consultados: código 2911 sigue en fila 522, código 0200 sigue en fila 432, coincidentes en catálogo y espejo; las posiciones 262/264 y 352/354 solo describen la presentación en catálogo. V4 aclara ese texto, sin cambiar la estimación ni los originales; diez pruebas Node pasan.

## 3. Aplicación en desarrollo y recuperación

1. Resultado v3/v4 aprobado: prioridad de filas e inicialización de TODOS los vinculados. Los tres adicionales locales no se modificaron.
2. `tools/initialize_historical_order.py` aplica únicamente con el descriptor de desarrollo y el directorio central esperado, nunca producción. Requiere las huellas exactas de catálogo/espejo de la propuesta aprobada. Bloqueo PHP/Python compartido, respaldo verificado, escritura mediante diario recuperable y relectura final. No toca espejo, cola ni configuración Sheets.
3. Cada registro conserva las fechas originales en `historicalOrderInitialization.originalDates`, además de conservar sus campos previos; guarda procedencia, precisión estimada, referencia prestada, fila y fecha de inicialización. `incorporatedAt` es la referencia activa para ordenar. La API impide falsificar o reiniciar esos campos al crear/editar.
4. Reejecución con el mismo informe: `already-initialized`, cero cambios. Una inicialización diferente o parcial se rechaza. Una propuesta atrasada se rechaza antes de escribir. No se vuelve a estimar durante sincronización ni al crear ramas.
5. Respaldo completo: `work/preproduction-snapshots/20261009-023829-167-before-historical-initialization`, 437 archivos verificados. Respaldo exacto de datos y manifiesto: `work/historical-migrations/20261009-initialization-dev-v1`. Contienen datos privados; no publicar en GitHub.
6. La comparación posterior confirma conservación de todas las filas y campos ajenos a incorporación, mismo espejo y misma cola; 17 archivos JSON de catálogo adicionales, incluidos los de producción, coinciden con el respaldo. Los datos de incorporación dev/prod ahora difieren intencionalmente por esta prueba autorizada; no realizar una copia dev→prod.
7. Recuperación, solo si se solicita: detener escritores, comprobar bajo bloqueo que no hubo ediciones posteriores y usar `anime.before.json` del respaldo con el mecanismo de transacción. Si hubo ediciones nuevas, recuperar selectivamente los campos de incorporación originales por ID usando la auditoría, no reemplazar todo el catálogo y perder esas ediciones. No automatizar un rollback destructivo ni reactivar un watcher antes de validar.
8. Cualquier inicialización posterior en producción requiere su propia propuesta/respaldo/aplicación explícita sobre sus datos vigentes. La utilidad de desarrollo está deliberadamente bloqueada para producción. La liberación del código no migra datos por sí sola.

## 4. Verificación en el servidor

`tests/historical-order-server.cjs` lee la API y el JSON público reales en `http://192.168.100.19:8092`, compara con el catálogo central y verifica las 781 posiciones vinculadas en ambos sentidos. Las lecturas PHP pueden representar un mapa vacío de auditoría como `[]` en vez de `{}`; la prueba normaliza exclusivamente ese caso, no diferencias de datos.

Prueba de navegador: catálogo a 360/1280 px y administrador a 412 px. En el administrador solo se simula sesión/perfil; los GET de contenido son reales. Se bloquean todas las mutaciones. Fechas históricas muestran `≈` y explicación «No es una fecha de alta real». Reporte/capturas locales: `outputs/qa-historical-order`. La prueba física en el celular del usuario queda pendiente para este orden inicializado.

Validaciones locales: 34 pruebas Python, 10 Node y suites PHP de catálogo/revisiones pasan. Las pruebas de sincronización/API usan fixtures aislados, no escriben en Sheets. Ver `RELEASE-PROGRESS.md` para el punto de reanudación de la liberación.
