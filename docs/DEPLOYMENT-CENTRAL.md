# Despliegue del código central y reversión

Preparación para revisión; este documento no despliega automáticamente ni cambia `main`.

1. Revisar el PR, sus pruebas y el diff sin credenciales/datos privados. Mantener Cloudflare Access. Resolver el estado del proveedor Jikan documentado en QA antes de declarar todas las APIs saludables.
2. Crear un snapshot verificado con `tools/preproduction-snapshot.ps1 -Phase before-approved-deploy`. Contiene configuración privada: nunca subirlo a GitHub. Guardar SHA del código instalado y del aprobado. No sustituye un respaldo completo de sesiones/dependencias/sistema.
3. Detener el monitor de producción y bloquear temporalmente escrituras administrativas durante la actualización. Guardar los cambios locales existentes en producción: no hacer `git reset --hard`, checkout forzado ni copiar todo desarrollo encima de producción.
4. Instalar solamente el código del commit aprobado en la instalación de producción; mantener su descriptor externo, catálogo, datos personales, secretos locales y OAuth. No trasladar `data`/colas/revisiones de desarrollo. No basta cambiar de rama si el checkout tiene modificaciones sin commit.
5. Iniciar PHP con `server-router.php` y comprobar descriptor `environment: produccion`, origen de datos y las rutas privadas (404). El servidor integrado es para la instalación local protegida; una publicación Apache/Nginx requiere enrutamiento y protección equivalentes, no sustituirlos por archivos estáticos.
6. **Google Sheets requiere autorización separada.** En la preparación actual debe permanecer apagado: existen cambios nuevos en la hoja que el usuario todavía no desea cargar. No usar el launcher raíz que arranca el monitor automáticamente. Solo después de esa autorización arrancar **un** monitor usando configuración Sheets/OAuth de producción, conservar todos los códigos y verificar reporte reciente, catálogo, pendientes, cola y lectura de confirmación. Un PID no prueba salud. No aprobar registros reales como prueba automática.
7. Hacer smoke test en móvil/escritorio, tomar snapshot `after-approved-deploy` y documentar SHA/fecha. Solo tras ello considerar producción desplegada. Etiquetas/versiones se acuerdan por separado.

## Reversión segura

1. Guardar un snapshot del fallo antes de cambiar nada. Detener monitor/escrituras. No borrar `.storage.lock`/`.watcher.lock` para intentar liberar procesos.
2. Si el problema es solo código/UI, volver al código compatible con catálogo central, conservando los datos actuales. No restaurar datos antiguos por un fallo de CSS.
3. Si el catálogo necesita restauración, comprobar hashes y ensayar primero con `tools/preproduction-restore-check.ps1 -Snapshot <ruta>`. Ese ensayo copia ocho JSON centrales a una carpeta aislada; no demuestra una recuperación completa ni modifica instalaciones.
4. Restaurar catálogo, cola y revisiones del **mismo entorno y fase** con escritores detenidos. Revisar cualquier `.transaction.json` antes de descartarlo. Los respaldos contienen datos privados y no deben difundirse.
5. Una escritura ya confirmada en Sheets no se revierte al recuperar JSON. Conciliar la fila y la cola antes de reactivar el monitor, para no devolver datos viejos accidentalmente. No copiar OAuth entre entornos.
6. Si se vuelve a código anterior al soporte central, tratarlo como una migración manual de almacenamiento. No arrancar automáticamente con los JSON versionados atrasados. Revalidar códigos, rutas privadas y Access después de cualquier reversión.

Diagrama de ramas/datos y flujo de redundancia: [CATALOG-STORAGE.md](CATALOG-STORAGE.md).
