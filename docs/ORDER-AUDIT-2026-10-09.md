# Diagnóstico de «más recientes» — 2026-10-09

Solicitud del usuario: verificar el orden contra ambas hojas antes del push. Esta revisión no cambia el comparador, las fechas ni los datos de las hojas/catálogos.

## Hallazgos confirmados

1. Lectura live de `Catalogo!A1:J998` en producción y desarrollo: 781 códigos, mismas posiciones de fila y mismo orden de títulos originales en ambas hojas.
2. Cada catálogo central tiene 784 animes: 781 vinculados y tres adicionales locales. Cero códigos de la hoja ausentes. Todas las `sourceRow` vinculadas y las filas de `anime-hoja.json` coinciden con sus hojas actuales. No es una fila atrasada ni un dato faltante.
3. La función `AltoidssContentOrder.sort` (`js/content-order.js`) separa registros con fecha de registros históricos sin fecha. En «newest», cualquier `createdAt`/`importedAt` válido precede a todas las filas sin fecha. Solo después ordena por `sourceRow` descendente. No compara una fecha con la incorporación real de una fila histórica desconocida.
4. Hay nueve animes con fecha: ocho vinculados y Cowboy Bebop local. Los ocho vinculados se adelantan sin importar su posición de hoja. Entre los 781 vinculados, 37 posiciones difieren del orden de filas descendente.
5. Navegador real de desarrollo, visita nueva a `catalogo.html?category=anime`, sin filtros y con «newest»: Mononoke (4441), Magical Explorer (4453), Romelia Senki (4450) aparecen primero; Cowboy Bebop queda noveno y 4470 queda décimo. Se bloquearon todas las mutaciones API: cero escrituras.

| Posición | Desarrollo visible | Orden descendente de ambas hojas |
| --- | --- | --- |
| 1 | 4441 — Mononoke Movie 3 Hebigami | 4470 — Mouse Cursor… |
| 2 | 4453 — Magical Explorer… | 4469 — Dark Summoner to Dekiteiru |
| 3 | 4450 — Romelia Senki | 4468 — Kanata kara |

## Carga frente a presentación

`data-store.js` carga las colecciones por API PHP o, si falla, por rutas JSON públicas. `catalogo.js:getCategoryItems` aplica el comparador **antes de paginar**; `dashboard.js:renderContentTable` usa el mismo comparador. La diferencia se reproduce con el JSON activo y en la pantalla: no depende del orden de llegada de llamadas HTTP ni de una caché vieja en esta sesión.

El comparador se introdujo en el commit `62f4de5` del 2026-10-07 (orden por incorporación). Sus pruebas actuales validan precisamente la prioridad de fechas sobre históricos: pasan, pero ese criterio no reproduce el orden de la hoja que ahora solicita el usuario. No usar el código numérico ni el año de estreno como sustitutos de la fila.

## Decisión pendiente, sin implementación

Para respetar la hoja, todos los animes vinculados deben compararse por fila, tengan o no fecha; las fechas se conservan como información. Los locales sin vínculo necesitan una regla explícita de ubicación o un modo separado por fecha: no existe una cronología común demostrable entre fechas locales y filas históricas sin fecha. Pedir confirmación antes de cambiar esa semántica. No borrar fechas ni inventarlas.

Evidencia privada fuera de Git: `work/diagnostics/order-audit-20261009.json`, lectura de ambas hojas, reporte de navegador y captura `order-browser-412-20261009.png`. El análisis del catálogo de producción reutiliza el comparador de desarrollo sobre sus datos: no afirma haber inspeccionado su interfaz en esta ronda.

Preparación del PR pausada en el paso 4; retomar desde `RELEASE-PROGRESS.md` después de resolver el orden.

## Decisión posterior al diagnóstico

La sección «Decisión pendiente» describe el estado del diagnóstico original, no la decisión final: el usuario eligió una cronología común de altas reales de app y lotes de primera sincronización de Sheets, con filas internas congeladas. El 2026-10-09 confirmó que la estimación por año/temporada y siguiente fila solo se usa para inicializar el histórico. Ver `INCORPORATION-HISTORY.md` para la vista previa y sus límites; aún no se migraron los datos. La estimación no equivale a reconstruir fechas históricas demostradas ni garantiza toda la secuencia de la hoja.

Corrección terminológica posterior del usuario: la referencia histórica es **año y quarter (trimestre)**, no la temporada activa de emisión. Vista previa v2 toma las columnas I/J literales; G/`activeSeason` se excluye. El nombre heredado `emissionSeason` normaliza los quarters a nombres de estaciones, pero no se usa como entrada en v2. La regla de futuras altas no cambia.

Decisión más reciente: ignorar fechas previas de TODOS los vinculados al inicializar, para conservar el orden de la hoja. V3 añade ajuste de referencias año/quarter no decrecientes por fila y desempate por fila, conserva fechas locales y verifica igualdad de las 781 posiciones relativas vinculadas. 4470 pasa al primero en la simulación. Ver `INCORPORATION-HISTORY.md`; aún no hay migración aplicada, escritura de Sheets ni despliegue de producción.

**Estado posterior:** el usuario aprobó y se aplicó la inicialización en desarrollo el 2026-10-09 02:43:52 -06:00, usando la propuesta v4 (mismo algoritmo v3 con encabezados explícitos de fila vs posición). Las 781 referencias coinciden en ambos sentidos y el servidor devuelve los datos inicializados. Producción, espejo, cola y hojas no se modificaron. Esta actualización sustituye como estado actual los textos previos «sin aplicar»; los hallazgos originales quedan como evidencia histórica.
