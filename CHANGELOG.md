# Historial de cambios

Este archivo registra cambios relevantes para quien usa o mantiene Altoidss. Los commits anteriores al inicio del versionado se conservan en Git; no se les asignan versiones retrospectivamente.

## Sin publicar — 0.1.0-dev

### En desarrollo — orden del Dashboard

- Selector de incorporaciones más nuevas o más antiguas en la tabla de administración; nuevas primero por defecto.
- Mismo orden y selector en el catálogo público, tanto en tarjetas como en lista, manteniendo búsqueda, filtros y paginación; la elección de orden se conserva en la URL.
- Referencia histórica por fila de Google Sheets/Excel cuando no existe fecha exacta; sin fabricar fechas ni usar el año de estreno.
- Fecha de incorporación para nuevas importaciones y protección de fechas existentes al editar contenido o noticias.
- Pruebas de ordenación, fechas equivalentes, filas históricas y conservación del arreglo original. Pendiente de validación visual e integración mediante pull request.

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
