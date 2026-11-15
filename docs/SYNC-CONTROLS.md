# Control del sincronizador desde el acceso CMD

Al abrir Iniciar-Altoidss.cmd, la aplicación inicia con el flujo habitual y queda
un menú de control. Solo las opciones elegidas afectan al sincronizador.

~~~text
[R] Reiniciar sincronizador
[D] Detener sincronizador
[A] Reautorizar Google y reanudar
[S] Salir del menú
~~~

El estado se actualiza cada cinco segundos. PHP y Cloudflare conservan su estado.
Salir del menú deja los servicios activos. El sincronizador se ejecuta en segundo
plano; sus mensajes se añaden a runtime/anime-sync/watcher.log y watcher-error.log.

## Detener y reiniciar

D solicita una parada ordenada. Durante la espera entre ciclos responde en menos
de un segundo. Si está procesando, termina el ciclo antes de salir para conservar
las transacciones y la cola de Sheets. R espera esa parada y después inicia otro
proceso; no crea un segundo escritor mientras el anterior siga activo.

Tras 30 segundos, una operación larga se muestra como parada solicitada. No se
fuerza su terminación ni se inicia otro escritor. Repetir la acción cuando termine.
Un PID antiguo no autoriza a finalizar procesos: se usa el bloqueo del entorno
y una identidad de instancia. No se envían señales de terminación a otros Python.

Si queda un sincronizador anterior a este protocolo, el controlador solicita
cerrar su ventana una vez. No intenta adoptar ni finalizar ese proceso mediante
un PID potencialmente reutilizado. Los entornos y otros checkouts se distinguen.

## Error de autorización

Cuando Google devuelve invalid_grant, el watcher registra AUTHORIZATION_REQUIRED,
termina y libera sus bloqueos/PID. El menú muestra que hace falta autorizar.
Abrir de nuevo el lanzador o pulsar R no repite automáticamente esa credencial.

Los errores temporales mantienen los reintentos existentes cada cinco minutos.
Que el proceso esté activo no demuestra que la última sincronización fuera correcta.

A detiene primero el escritor, abre el consentimiento de Google en el navegador y
valida una lectura pequeña de la hoja antes de reanudar. Si se cancela, falla el
consentimiento o Google no permite leer la hoja, permanece detenido.
La validación de acceso no envía cambios; el watcher reanudado conserva su flujo
normal de cambios aprobados y sincronización.

El usuario introduce sus credenciales directamente en Google. No pegarlas en el
chat ni registrar cookies, códigos OAuth, tokens o client_secret. Reautorizar puede
actualizar el archivo privado del token y la configuración existente de Sheets;
no cambia código ni requiere reinstalar la aplicación.

## Accesos directos

Estas variantes abren solo los controles, sin iniciar PHP, Cloudflare ni navegador
de la aplicación:

~~~bat
Iniciar-Altoidss.cmd --sync-menu
Iniciar-Altoidss.cmd --stop-sync
Iniciar-Altoidss.cmd --restart-sync
Iniciar-Altoidss.cmd --authorize-sync
~~~

La última abre el navegador de consentimiento porque lo solicitó el usuario.
Requieren el Python declarado en runtime/toolchain.local.json y la configuración
del mismo entorno. --check-runtime continúa sin iniciar servicios; --check informa
de un estado degradado si falta autorización.

## Pruebas y despliegue

Las regresiones usan procesos desechables, bloqueos reales y Google simulado:
parada, reinicio, PID obsoleto, propietario ajeno, operación en curso, error OAuth,
cancelación, lectura denegada y reintentos temporales. Nunca usan la hoja real.

Los cambios se preparan en una rama aislada y siguen docs/CI-CD.md. La instalación
incluye código y plantilla CMD, además de actualizar el CMD real bajo su aprobación
final. No copiar la plantilla directamente a producción para saltar el pipeline.
G: y el protocolo AppAudit independiente permanecen fuera de este cambio.
