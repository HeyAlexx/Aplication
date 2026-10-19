# Pruebas de preproducción — 2026-10-07

Este informe conserva la ejecución histórica. Para la ronda posterior al desbloqueo de la terminal, consultar `QA-2026-10-08.md`; cambió el conjunto de datos de desarrollo.

Estado: validación funcional del catálogo aprobada; revisión visual con pendientes. No se ha desplegado a producción.

## Entorno y datos

- Rama: `fix/sheets-approval-writeback`.
- Desarrollo local: `http://127.0.0.1:8092`.
- Microsoft Edge con Playwright, modo headless. Son pruebas por tamaño de ventana, no pruebas en dispositivos físicos ni en Safari/Firefox.
- Datos reales del JSON de desarrollo: 784 animes, 15 películas y 10 series.
- Las 46 incorporaciones nuevas todavía no tienen imagen ni enriquecimiento externo.
- Las preferencias y otras escrituras desde la nueva matriz se interceptaron para no alterar datos del usuario. La búsqueda de descubrimiento devuelve un error 503 controlado para probar el respaldo en el JSON real; no valida proveedores externos en vivo.

## Matriz responsive

| Grupo | Tamaños (ancho × alto) | Categorías |
| --- | --- | --- |
| Móvil | 320×740, 360×800, 412×924 | Anime, películas, series |
| Pantallas intermedias y tablet | 600×960, 768×1024, 820×1180, 1024×768 | Anime, películas, series |
| Escritorio | 1512×1000, 1920×1080 | Anime, películas, series |

Resultado final: **27 escenarios, 360 comprobaciones aprobadas**, sin errores de JavaScript ni fallos de red en las dependencias registradas. Los resultados son de la ejecución final; las primeras ejecuciones sirvieron para ajustar selectores, apertura del menú móvil y espera de operaciones asíncronas del propio test.

Se comprobó: cantidad real de registros; 35 tarjetas por página cuando corresponde; ausencia de desbordamiento horizontal de la página; título debajo del encabezado al iniciar arriba; Bootstrap disponible; dos columnas en móvil; sidebar fijo en tablet/escritorio; selección de orden y URL; búsqueda con título real; búsqueda local sin resultados; limpiar filtros; selección de lista y tarjetas; selección de densidad 3/5/7. La comprobación de densidad valida el estado del control, no garantiza ese número de columnas en todos los breakpoints.

También pasaron los cinco scripts existentes de orden/filtros/sidebar/móvil, ocho pruebas Python del flujo de aprobaciones y las pruebas PHP de aprobación, conversión de MyAnimeList y validación de fuentes. Las pruebas PHP de MyAnimeList verifican conversión de datos, no conexión live al proveedor.

Evidencia automatizada y 27 capturas iniciales: `outputs/qa-responsive/report.json` y `outputs/qa-responsive/{categoria}-{ancho}.png`.

## Revisión visual y encabezado

Se inspeccionaron capturas de 412, 820 y 1920 px. Además se abrió y cerró el menú superior a 412, 820 y 1024 px, y se desplazó la página 130 px.

- **Corregido: botón Todos a 820 px.** Se sustituyó el texto por el SVG de infinito proporcionado por el usuario, con nombre accesible «Todas las iniciales». La prueba `tests/catalog-all-icon.cjs` verifica centrado y ausencia de desbordamiento a 320/412/768/820/1024/1512/1920 px, y que clic sobre el icono y teclado restauran todas las iniciales. Captura: `outputs/catalog-infinity-820.png`. Cambio en la rama `fix/catalog-all-infinity`, todavía sin desplegar.
- **Pendiente de contenido: 46 portadas faltantes.** Las tarjetas muestran «Buscando imagen» para entradas que no tienen imagen. No es un fallo de red ni una imagen que se esté descargando en esta prueba. Conviene completar metadatos o usar un texto de placeholder que no prometa una búsqueda activa.
- El menú superior abre correctamente. En tablet el sidebar se recoloca debajo del encabezado expandido; el título también queda debajo.
- La captura del usuario es compatible con una página desplazada: al desplazar 130 px, el título pasa por detrás del encabezado sticky. Al volver arriba no se reprodujo un solapamiento inicial. Esta observación no demuestra el estado exacto del navegador del usuario; todavía queda revisar navegación con scroll restaurado y decidir si se quiere otro comportamiento visual.

Evidencia adicional: `outputs/qa-responsive/visual-checks.json` y `scrolled-412.png`, `scrolled-820.png`, `scrolled-1024.png`.

## Límites antes de producción

Corrección tras prueba en celular (2026-10-08): el sidebar móvil heredaba `overflow-y: auto` y `overscroll-behavior: contain` del escritorio, aunque su altura era automática y no tenía recorrido interno de scroll. Se restauró `overflow: visible` y `overscroll-behavior: auto` exclusivamente en móvil. Se quitó el foco automático del buscador: abrir el panel enfoca el botón de cierre, no un campo que active el teclado virtual. El desplazamiento de apertura es inmediato y respeta la altura del encabezado. La prueba `tests/catalog-mobile-filter-scroll.cjs` reprodujo la configuración anterior y pasó después con contexto móvil táctil, gesto swipe por CDP, controles seleccionables y alturas 840/440 px. Es emulación, no sustituye la confirmación en el teléfono del usuario. Rama: `fix/catalog-mobile-filter-scroll`.

Actualización de interacción móvil: las opciones de orden usan botones propios de al menos 48 px de alto a anchos de hasta 768 px. `tests/catalog-touch-order.cjs` pasó a 320/360/412/600/768 px: área táctil, menú dentro de pantalla, cambio de orden y URL, cierre con Escape y selector nativo conservado en escritorio. Se mantiene la lógica de orden original. Rama: `fix/catalog-mobile-order-touch`. La matriz general se adaptó al nuevo control; sus 360 comprobaciones documentadas corresponden a la ejecución previa a este cambio.

Todavía pendientes: los puntos visuales anteriores; autenticación real y permisos con una cuenta administradora; favoritos y estados con persistencia real en un entorno de prueba; prueba de descubrimiento/enriquecimiento live; dispositivos físicos y otros navegadores. No se ejecutaron aprobaciones en la hoja original durante esta ronda. La prueba real de writeback anterior se realizó exclusivamente sobre la hoja duplicada y sus valores de prueba se restauraron.

No se fusionó la rama, no se publicó en GitHub y no se activó el monitor automático en producción. Los cambios anteriores en `data/anime.json` y `data/configuraciones.json` se conservaron.
