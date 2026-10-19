# Historial de cambios

Este archivo registra cambios relevantes para quien usa o mantiene Altoidss. Los commits anteriores al inicio del versionado se conservan en Git; no se les asignan versiones retrospectivamente.

## Sin publicar — 0.1.0-dev

### Catálogo central, redundancia y administrador móvil

- Datos operativos separados de ramas Git por entorno; copia literal completa de Sheets y detección de códigos ausentes incluso cuando el hash no cambia. Recuperación local de los 46 códigos omitidos sin sobrescribir metadatos aprobados.
- Edición/aprobación vinculada guarda catálogo y cola recuperable; devolución por código único con lectura de confirmación. Las altas desde la página no crean filas de Sheets.
- Bloqueo PHP/Python compartido, un monitor por entorno, recuperación hacia adelante y protección de aprobaciones concurrentes durante consultas externas. Utilidades masivas antiguas rechazan escribir en almacenamiento central.
- Administrador móvil con cabecera 3–1–1, año centrado, fecha corta/N/A y Editar/Ocultar visibles; interacción verde al 40 %. Ajustes de desplazamiento de filtros, iconos y opciones táctiles del catálogo.
- Diagramas, launcher central versionado, avance numerado, respaldo/ensayo de recuperación e informe QA. 34 pruebas Python, 10 Node, suites PHP y matriz Edge; prueba histórica en Sheets de desarrollo con restauración. Revalidación local el 19 de octubre y revisión final aprobada. Jikan continúa con timeout. Sheets permanece apagado; sin despliegue ni integración automática.

### En desarrollo — aprobaciones y devolución a Google Sheets

- Altas aprobadas conservan su fila de origen y generan una devolución de los campos A:J desde la misma versión guardada en el catálogo JSON.
- Dashboard recarga el catálogo después de aprobar y muestra por separado el estado pendiente o confirmado de Google.
- Devolución por código único, valores literales y lectura de confirmación; cola conservada ante fallos y aprobaciones nuevas durante el envío.
- Previsualización e inicialización no procesan devoluciones. Pruebas aisladas y escritura real en la hoja de prueba con valores originales restaurados; ver informe de liberación 2026-10-09.

### En desarrollo — orden del Dashboard

- Selector de incorporaciones más nuevas o más antiguas en la tabla de administración; nuevas primero por defecto.
- Mismo orden y selector en el catálogo público, tanto en tarjetas como en lista, manteniendo búsqueda, filtros y paginación; la elección de orden se conserva en la URL.
- Cronología común de fechas reales de app/lotes de Sheets. Inicialización histórica separada y autorizada por año/quarter y filas, referencias estimadas marcadas con ≈ y auditoría; la fila de Sheets no cambia.
- Fecha de incorporación para nuevas importaciones y protección de fechas existentes al editar contenido o noticias.
- Pruebas de ordenación, fechas equivalentes, filas históricas y conservación del arreglo original; pruebas de catálogo real con búsqueda, paginación y recarga. Integración mediante pull request pendiente.

### Evolución previa — distribución horizontal de filtros

- Panel horizontal en lugar de barra lateral, con letras A–Z, iniciales no alfabéticas, tipo, género, año de estreno y estado de producción.
- Búsqueda y limpieza visibles; temporadas, visualización y rango de años agrupados en «Más filtros».
- Resultados a la izquierda y ordenación a la derecha, conservando los controles de categorías, seguimiento y vista.
- Distribución adaptable a móvil y pruebas de navegador de filtros, teclado y ordenación. No se añaden criterios de popularidad o puntuación sin datos adecuados.

### En desarrollo — catálogo móvil

- Dos tarjetas por fila en móvil, incluso por debajo de 420 px, con portada 2:3 y título legible debajo de la imagen.
- Opciones secundarias plegables mediante «Mostrar opciones»; iniciales y filtros principales siempre visibles.
- Barra de controles compacta junto a resultados y densidad de escritorio mediante selector 3/5/7; móvil mantiene dos columnas.
- Pruebas de navegador a 320, 360, 412, 600 y 768 px.

### Distribución vigente — menú lateral del catálogo

- Búsqueda, limpieza, filtros avanzados, categorías, seguimiento y controles de vista en la barra lateral izquierda fija original, siempre visible en escritorio, no en un diálogo.
- Letras, filtros principales, resultados y ordenación permanecen en el contenido central; en móvil la barra lateral se convierte en un bloque plegable sobre el catálogo.
- Contenido centrado en el espacio disponible a la derecha del sidebar, con márgenes equilibrados en pantallas amplias sin agrandar las tarjetas.
- Controles de la barra lateral separados verticalmente en tipo, estado de visualización (incluido «No visto»), presentación y cantidad por fila; selector con números 3/5/7.
- Selector numérico centrado, Favoritos centrado en la última fila, símbolos originales para tarjetas/lista y filtros avanzados visibles sin desplegable ni caja exterior.
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
