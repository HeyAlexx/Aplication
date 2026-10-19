# Avance de preparación para GitHub y producción

Actualizado: 2026-10-19. Punto de reanudación tras la aprobación final del usuario.

## Límites vigentes

- Publicar solo código, pruebas y documentación mediante commits selectivos y PR.
- No integrar el PR ni desplegar producción sin autorización explícita.
- Google Sheets permanece apagado en ambos entornos: hay cambios nuevos que el usuario todavía no desea cargar. No ejecutar el launcher raíz que inicia el monitor.
- No copiar datos de desarrollo a producción, ni publicar configuración privada, OAuth, usuarios, favoritos, historial, catálogos operativos o respaldos.
- Mantener Cloudflare Access. Conservar los cambios locales de producción; no usar reset/checkout forzados.

## Pasos numerados actuales

| Paso | Trabajo | Estado |
| --- | --- | --- |
| 1 | Revisión final del usuario en desarrollo | APROBADO |
| 2 | Respaldo, auditoría, commits selectivos, push y PR | EN CURSO |
| 3 | Preparar instalación de código conservando producción sucia | PENDIENTE; sin despliegue autorizado |
| 4 | Vista previa y migración histórica propia de producción | PENDIENTE; no copiar JSON de desarrollo |
| 5 | Respaldo final, copia independiente y recuperación coordinada | PENDIENTE |
| 6 | Despliegue autorizado y smoke test protegido | PENDIENTE |

Reanudar desde el paso 2. La preparación del PR no autoriza su integración, el despliegue ni la sincronización.

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
