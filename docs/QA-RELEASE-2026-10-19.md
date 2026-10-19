# Verificación de liberación — 2026-10-19

Preparación de PR, no integración ni despliegue. El usuario aprobó la revisión final de desarrollo. Sheets permanece apagado y sus cambios nuevos no se consultaron ni cargaron durante esta ronda.

## Resultados

| Grupo | Resultado |
| --- | --- |
| Integridad del traslado a C: | 16 075 archivos comparados por SHA-256; enlaces de dependencias/Git reparados |
| Python aislado | 34 pruebas aprobadas; repetidas antes de publicar |
| Orden histórico Node | 10 pruebas aprobadas |
| Servicios PHP de revisión/writeback | Dos suites aprobadas |
| API HTTP en fixture aislado | 38 comprobaciones aprobadas |
| Administrador responsive | 18 escenarios en nueve anchos, 320–1920 px; sin errores JS ni mutaciones reales |
| Catálogo responsive | 27 escenarios y 360 comprobaciones aprobadas |
| Táctil y controles | Panel/scroll con altura reducida, selector de orden, infinito y menú aprobados en emulación |
| Orden de desarrollo | API y JSON público coinciden; 781 referencias vinculadas respetan filas en ambos sentidos |
| Producción, solo lectura | Tres tamaños, sin desbordamiento ni errores JS; no instala el nuevo código |
| Protección | Rutas privadas 404; revisiones sin sesión denegadas; acceso externo redirige a Cloudflare Access |
| Proveedores de lectura | MAL, AniList, Kitsu y Watchmode responden; fallback AniList aprobado |
| Jikan | Timeout repetido; no se declara saludable |

La prueba física de filtros, teclado y acciones fue confirmada por el usuario; la revisión final también fue aprobada. Emulación Edge no sustituye Safari/iOS o Firefox físico. El administrador usa sesión simulada para la matriz visual; roles y persistencia se prueban aparte con HTTP real en datos descartables.

## Datos y recuperación

Ambos entornos contienen 784 animes (781 códigos vinculados más tres locales), 15 películas, 10 series y cuatro noticias. La igualdad se verificó contra el espejo local, no contra los cambios recientes de Google. Desarrollo tiene 781 referencias históricas estimadas; producción no. No copiar el JSON de desarrollo para resolver esa diferencia.

Los hashes de 24 archivos de datos/estado permanecieron iguales durante las comprobaciones de operación. Respaldo previo a commits: fase `before-selective-release`, 491 archivos verificados, privado. Ensayo de recuperación: ocho JSON restaurados en una carpeta aislada; no cubre de forma integral cola, revisiones, OAuth, sesiones o sistema. Un snapshot secuencial no garantiza un punto consistente mientras haya escritores activos.

## Pendientes antes del despliegue

1. Revisar commits/PR y sus comprobaciones; no se integra automáticamente.
2. Preparar instalación selectiva sin perder los cambios locales de producción.
3. Preparar vista previa/migración histórica propia de producción; la utilidad vigente solo permite desarrollo.
4. Respaldo final con escritores detenidos, copia independiente y ensayo coordinado de recuperación.
5. Resolver o aceptar explícitamente la salvedad de Jikan y autorizar el despliegue.
6. Smoke test protegido tras instalar el código autorizado. Sheets sigue en espera hasta otra autorización.

No hay workflow de CI versionado en esta preparación: las pruebas descritas son locales. No confundir ausencia de comprobaciones remotas con resultado aprobado.

Evidencia privada: `work/operations/*-servers-no-sheets-sync`, `work/preproduction-snapshots`, `work/recovery-drills` y `outputs/qa-*`. No publicar sus datos, configuración o capturas privadas. La prueba real de Sheets del 9 de octubre queda como evidencia histórica en [su informe](QA-RELEASE-2026-10-09.md); no fue repetida ahora.

Continuación numerada: [RELEASE-PROGRESS.md](RELEASE-PROGRESS.md). Diagramas: [CATALOG-STORAGE.md](CATALOG-STORAGE.md).
