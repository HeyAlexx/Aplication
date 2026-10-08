# Ruta de progreso de Altoidss

Plan de evolución de la aplicación. Cada etapa se implementará en una rama independiente, con validación y revisión antes de integrarse en `main`. El procedimiento está en [CONTRIBUTING.md](CONTRIBUTING.md).

**Estado:** alcance de las etapas definido; implementación pendiente. No hay fechas comprometidas. Las versiones futuras se asignarán al preparar cada lanzamiento, no por anticipado.

## Punto de partida

La aplicación cuenta con catálogo audiovisual, cuentas y perfiles, lista personal, seguimiento de visualización y herramientas de administración. El catálogo de anime dispone de importación desde Google Sheets o Excel, revisión de diferencias, consulta de metadatos por URL y devolución de correcciones aprobadas a Google Sheets mediante OAuth.

La guía de instalación y uso está en [README.md](README.md).

## Etapa 0 — Versionado y flujo de cambios

- Objetivo: identificar versiones y evitar que nuevas funciones se desarrollen directamente en `main`.
- Rama de preparación: `docs/roadmap-versioning`.
- Archivos: `VERSION`, `CHANGELOG.md`, guía de contribución y plantilla de pull request.
- Versión de desarrollo inicial: `0.1.0-dev`; no representa una versión publicada ni una etiqueta existente.
- Criterios: documentar ramas, revisión, pruebas, lanzamientos y recuperación; comprobar que el commit solo incluya archivos de esta etapa.
- Pendiente de configuración externa: proteger `main` en GitHub y separar el checkout de desarrollo de la instalación que atiende usuarios.
- Estado: documentación preparada; integración y lanzamiento pendientes.

## Etapa 1 — Página dinámica de contenido y capítulos

- Objetivo: una única página reutilizable que cargue anime, películas o series mediante un identificador, sin crear un HTML por título.
- Rama prevista: `feature/content-detail`.
- Pasos: revisar el modelo actual; definir la relación contenido–temporadas–episodios; agregar consultas necesarias; construir la ficha y navegación por temporadas; probar los tres tipos de contenido.
- Mostrar datos de la obra, temporadas y capítulos registrados. Para películas, representar el contenido principal sin inventar episodios.
- Distinguir un capítulo registrado de un archivo local disponible: los metadatos por sí solos no prueban que exista un vídeo reproducible.
- Criterios: abrir distintos títulos con la misma página; manejar identificadores inexistentes y obras sin capítulos; funcionar en móvil y escritorio; no duplicar ni perder registros existentes.
- Dependencias: inventario de los datos actuales y definición de identificadores estables.
- Estado: planificada, no implementada.

## Etapa 2 — Reproductor integrado de archivos locales

- Objetivo: reproducir vídeos seleccionados por el usuario desde su computadora, sin obligarlo a subirlos al servidor.
- Rama prevista: `feature/local-player`.
- Pasos: definir asociación archivo–capítulo; implementar selección explícita de archivos y reproducción con el navegador; conectar el reproductor con la ficha; gestionar errores y liberar recursos temporales.
- No explorar el disco sin permiso ni publicar rutas locales. Los formatos y códecs admitidos dependerán del navegador.
- Definir si las asociaciones sobreviven al cierre de la sesión; no prometer acceso persistente hasta validar permisos y compatibilidad.
- Criterios: reproducir un archivo compatible, pausar, buscar y ajustar volumen; mostrar un error claro ante un archivo incompatible o acceso revocado; mantener los archivos en el equipo; aislar las asociaciones entre usuarios.
- Fuera de alcance inicial: transcodificación, streaming remoto y descarga de contenido.
- Dependencias: etapa 1 y pruebas con navegadores y vídeos de ejemplo autorizados.
- Estado: planificada, no implementada.

## Etapa 3 — Mi lista con acordeones por usuario

- Objetivo: organizar el perfil con secciones colapsables de Favoritos, Por ver y Viendo.
- Rama prevista: `feature/my-list-accordions`.
- Pasos: revisar persistencia de favoritos y estados; definir transiciones; construir acordeones accesibles; conectar acciones con la API; probar aislamiento de cuentas.
- Favoritos es independiente del estado de visualización: una obra puede ser favorita y estar en Viendo.
- Revisar la compatibilidad de los estados existentes al incorporar Viendo; conservar Visto y no reinterpretar Ignorado silenciosamente.
- Criterios: desplegar y colapsar con teclado; mostrar cantidades y estados vacíos; guardar cambios tras recargar; evitar duplicados y conservar las listas existentes.
- Estado: planificada, no implementada.

## Etapa 4 — Orden cronológico del Dashboard

- Objetivo: mostrar recientemente agregados por defecto y permitir elegir más nuevos o más antiguos.
- Rama prevista: `feature/dashboard-date-order`.
- Pasos: revisar fechas disponibles; definir una fecha estable de incorporación; resolver registros antiguos sin fecha sin inventar su antigüedad; agregar selector y orden estable.
- Ordenar por fecha de incorporación a Altoidss, no por año de estreno ni por fecha de modificación.
- Criterios: nuevos primero al entrar; alternar ambos sentidos sin perder filtros ni paginación; mantener el orden ante empates; documentar el tratamiento de registros sin fecha.
- Estado: planificada, no implementada.

## Etapa 5 — Evaluación de Vite o Next.js

- Objetivo: estudiar la evolución del frontend después de estabilizar los flujos anteriores.
- Rama de investigación prevista: `research/frontend-migration`.
- Pasos: inventariar páginas y API; comparar alternativas según ejecución local, autenticación, despliegue y mantenimiento; elaborar una decisión técnica; probar una pantalla representativa en un prototipo aislado.
- Vite y Next.js son alternativas a evaluar, no una migración aprobada. Evaluar por separado requisitos de instalación como aplicación web/PWA si se desean.
- Criterios: documentar ventajas, costos, compatibilidad y plan incremental con recuperación; no reemplazar la aplicación existente durante la investigación.
- Estado: investigación futura.

## Etapa 6 — Evaluación de SQLite y Supabase

- Objetivo: valorar persistencia futura para catálogo, cuentas, listas y revisiones sin elegir todavía una base de datos.
- Rama de investigación prevista: `research/database-options`.
- Pasos: definir necesidades de uso local/remoto y concurrencia; inventariar JSON y relaciones; comparar SQLite y Supabase en operación, acceso, seguridad, respaldo y costos; probar importación sobre copias de datos.
- Revisar autenticación, autorización por usuario y migración de credenciales. No cargar datos personales en servicios externos durante una prueba sin autorización.
- Criterios: decisión técnica documentada, prueba reproducible, verificación de integridad y plan de retorno; ningún cambio a los datos reales en esta etapa.
- Dependencias: requisitos de despliegue y modelo de contenido ya definidos. La decisión debe coordinarse con la etapa 5, sin obligar a migrar frontend y datos al mismo tiempo.
- Estado: investigación futura.

## Ideas para evaluar

Estas mejoras adicionales se mantienen para evaluación y no sustituyen las etapas anteriores. Su orden no implica prioridad.

| Área | Propuesta | Resultado esperado | Estado |
| --- | --- | --- | --- |
| Sincronización | Resolver la fila de Google Sheets por código estable antes de escribir. | Reducir el riesgo si cambia el orden de la hoja. | Por evaluar |
| Revisiones | Ampliar el historial de decisiones y versiones. | Distinguir cambios nuevos de correcciones ya aprobadas. | Por evaluar |
| Excel | Evaluar exportación o devolución de correcciones al libro local. | Evitar actualizar manualmente la fuente Excel. | Por evaluar |
| Diagnóstico | Mejorar la visibilidad de errores, reintentos y pendientes. | Saber qué ocurrió y qué intervención se necesita. | Por evaluar |
| Configuración | Simplificar la preparación de fuentes y proveedores. | Reducir pasos manuales en la primera instalación. | Por evaluar |

## Ficha de una mejora

Copia esta ficha cuando una propuesta pase a planificación:

- Nombre:
- Problema que resuelve:
- Prioridad:
- Versión objetivo:
- Cambios incluidos:
- Dependencias y riesgos:
- Criterios de aceptación:
- Pruebas:
- Estado:

Estados sugeridos: **por evaluar → planificada → en desarrollo → en validación → completada**. Una mejora puede quedar aplazada si cambian las prioridades.

## Checklist antes de publicar

- [ ] Confirmar alcance y criterios de aceptación.
- [ ] Implementar sin perder datos existentes.
- [ ] Ejecutar las comprobaciones correspondientes.
- [ ] Validar el flujo de uso afectado.
- [ ] Actualizar documentación y registrar limitaciones.
- [ ] Revisar que no se incluyan credenciales ni datos personales.
- [ ] Publicar los cambios y registrar la actualización.

## Registro de futuras actualizaciones

| Versión / fecha | Cambios principales | Validación | Limitaciones |
| --- | --- | --- | --- |
| Sin publicar | Preparación del roadmap y flujo de ramas. | Comprobaciones de documentación; no implementación funcional. | Protección remota y aislamiento del despliegue pendientes. |
