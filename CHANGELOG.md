# Historial de cambios

Este archivo registra cambios relevantes para quien usa o mantiene Altoidss. Los commits anteriores al inicio del versionado se conservan en Git; no se les asignan versiones retrospectivamente.

## Sin publicar — 0.1.0-dev

### En desarrollo — orden del Dashboard

- Selector de incorporaciones más nuevas o más antiguas en la tabla de administración; nuevas primero por defecto.
- Mismo orden y selector en el catálogo público, tanto en tarjetas como en lista, manteniendo búsqueda, filtros y paginación; la elección de orden se conserva en la URL.
- Referencia histórica por fila de Google Sheets/Excel cuando no existe fecha exacta; sin fabricar fechas ni usar el año de estreno.
- Fecha de incorporación para nuevas importaciones y protección de fechas existentes al editar contenido o noticias.
- Pruebas de ordenación, fechas equivalentes, filas históricas y conservación del arreglo original; pruebas de catálogo real con búsqueda, paginación y recarga. Integración mediante pull request pendiente.

### En desarrollo — distribución de filtros del catálogo

- Panel horizontal en lugar de barra lateral, con letras A–Z, iniciales no alfabéticas, tipo, género, año de estreno y estado de producción.
- Búsqueda y limpieza visibles; temporadas, visualización y rango de años agrupados en «Más filtros».
- Resultados a la izquierda y ordenación a la derecha, conservando los controles de categorías, seguimiento y vista.
- Distribución adaptable a móvil y pruebas de navegador de filtros, teclado y ordenación. No se añaden criterios de popularidad o puntuación sin datos adecuados.

### En desarrollo — catálogo móvil

- Dos tarjetas por fila en móvil, incluso por debajo de 420 px, con portada 2:3 y título legible debajo de la imagen.
- Filtros principales plegables mediante «Filtros»; iniciales siempre visibles.
- Barra de controles compacta junto a resultados y densidad de escritorio mediante selector 3/5/7; móvil mantiene dos columnas.
- Pruebas de navegador a 320, 360, 412, 600 y 768 px.

### En desarrollo — menú lateral del catálogo

- Búsqueda, limpieza, filtros avanzados, categorías, seguimiento y controles de vista en la barra lateral izquierda fija original, siempre visible en escritorio, no en un diálogo.
- Letras, filtros principales, resultados y ordenación permanecen en el contenido central; en móvil la barra lateral se convierte en un bloque plegable sobre el catálogo.
- Contenido centrado en el espacio disponible a la derecha del sidebar, con márgenes equilibrados en pantallas amplias sin agrandar las tarjetas.
- Verificación de búsqueda, categorías, filtros avanzados, posición fija y adaptación móvil mediante pruebas de navegador.

### Documentación

- Roadmap con página dinámica de contenido, reproductor local, listas colapsables y orden cronológico del Dashboard.
- Etapas futuras de evaluación de Vite/Next.js y SQLite/Supabase, sin decisiones de migración tomadas.
- Flujo de ramas, pull requests, validaciones y publicación de versiones.
- Archivo `VERSION` y plantilla de pull request.

### Pendientes antes de un lanzamiento

- El flujo inicial se integró mediante PR #1; revisar e integrar la preparación del entorno aislado en su propio pull request.
- Configurar protección de `main` y validar funcionalmente el entorno aislado.
- Elegir el alcance de la primera versión estable de esta fase y validar la aplicación.

No hay una etiqueta `v0.1.0` creada por esta preparación. Las funciones futuras descritas en el roadmap todavía no están implementadas.
