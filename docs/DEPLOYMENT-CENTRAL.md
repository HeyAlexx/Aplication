# Despliegue del código central y reversión

Procedimiento operativo; este documento no despliega automáticamente ni cambia `main`.

Estado del 2026-10-19: pasos 1–6 completados, PR #3/#4 integrados, código
operativo `7af617fef113c1ac23a5732b2e28bc473e91e675`. Histórico delimitado
aplicado y sincronizador único de producción autorizado cada 300 s;
desarrollo sigue sin Google. Ver [cierre y límites](PRODUCTION-DEPLOYMENT-2026-10-19.md).

El paso 3 ya tiene [inventario, decisiones sobre cambios locales y ensayo aislado](INSTALLATION-PLAN.md). Usar ese procedimiento de preparación antes de cualquier reemplazo; no copiar indiscriminadamente el checkout de desarrollo.

El paso 4 tiene [propuesta, ensayo y aplicación delimitada](PRODUCTION-HISTORY-PLAN.md).
La CLI de desarrollo permanece bloqueada para producción; no eludirla.
Se aplicó el procedimiento específico autorizado, con respaldo coordinado y
código compatible, protegiendo altas posteriores.

El paso 5 ya cuenta con [copia independiente y restauración coordinada](COORDINATED-RECOVERY.md) verificadas. Tras el BSOD `0x124`, el origen del fallo del sistema sigue sin identificar; no confundir recuperación de archivos con estabilidad del hardware. Revisar este riesgo antes de autorizar el despliegue y renovar el respaldo si los datos cambiaron desde su captura.

1. Revisar el PR, sus pruebas y el diff sin credenciales/datos privados. Mantener Cloudflare Access. Resolver el estado del proveedor Jikan documentado en QA antes de declarar todas las APIs saludables.
2. Crear un snapshot verificado con `tools/preproduction-snapshot.ps1 -Phase before-approved-deploy`. Contiene configuración privada: nunca subirlo a GitHub. Guardar SHA del código instalado y del aprobado. No sustituye un respaldo completo de sesiones/dependencias/sistema.
3. Detener el monitor de producción y bloquear temporalmente escrituras administrativas durante la actualización. Guardar los cambios locales existentes en producción: no hacer `git reset --hard`, checkout forzado ni copiar todo desarrollo encima de producción.
4. Instalar solamente el código del commit aprobado en la instalación de producción; mantener su descriptor externo, catálogo, datos personales, secretos locales y OAuth. No trasladar `data`/colas/revisiones de desarrollo. No basta cambiar de rama si el checkout tiene modificaciones sin commit.
5. Iniciar PHP con `server-router.php` y comprobar descriptor `environment: produccion`, origen de datos y las rutas privadas (404). El servidor integrado es para la instalación local protegida; una publicación Apache/Nginx requiere enrutamiento y protección equivalentes, no sustituirlos por archivos estáticos.
6. **Google Sheets requiere autorización separada.** El 19 de octubre se autorizó primero la prueba real y después mantener **un** monitor de producción con `--apply --watch --interval 300`. Usar configuración Sheets/OAuth de producción, conservar todos los códigos y verificar reporte reciente, catálogo, pendientes, cola y lectura de confirmación. Un PID no prueba salud. No aprobar registros reales como prueba automática. Desarrollo sigue sin Google; no usar el launcher raíz para duplicar procesos. El intervalo es una espera tras cada ejecución; no se configuró arranque automático después de reiniciar Windows.
7. Hacer smoke test en móvil/escritorio, tomar snapshot `after-approved-deploy` y documentar SHA/fecha. Solo tras ello considerar producción desplegada. Etiquetas/versiones se acuerdan por separado.

## Reversión segura

1. Guardar un snapshot del fallo antes de cambiar nada. Detener monitor/escrituras. No borrar `.storage.lock`/`.watcher.lock` para intentar liberar procesos.
2. Si el problema es solo código/UI, volver al código compatible con catálogo central, conservando los datos actuales. No restaurar datos antiguos por un fallo de CSS.
3. Si el catálogo necesita restauración, comprobar hashes y ensayar primero con `tools/preproduction-restore-check.ps1 -Snapshot <ruta>`. Ese ensayo copia ocho JSON centrales a una carpeta aislada; no demuestra una recuperación completa ni modifica instalaciones.
4. Restaurar catálogo, cola y revisiones del **mismo entorno y fase** con escritores detenidos. Revisar cualquier `.transaction.json` antes de descartarlo. Los respaldos contienen datos privados y no deben difundirse.
5. Una escritura ya confirmada en Sheets no se revierte al recuperar JSON. Conciliar la fila y la cola antes de reactivar el monitor, para no devolver datos viejos accidentalmente. No copiar OAuth entre entornos.
6. Si se vuelve a código anterior al soporte central, tratarlo como una migración manual de almacenamiento. No arrancar automáticamente con los JSON versionados atrasados. Revalidar códigos, rutas privadas y Access después de cualquier reversión.

Diagrama de ramas/datos y flujo de redundancia: [CATALOG-STORAGE.md](CATALOG-STORAGE.md).
