# Sesiones cuando HTTPS termina en un proxy

La cookie de sesión conserva HttpOnly, SameSite=Lax y Path=/. Secure se activa si
lo exige session.cookie_secure en la configuración del proceso PHP o si el SAPI
indica HTTPS nativo. Las cabeceras Forwarded/X-Forwarded-* de una petición no
deciden esta política. Un cliente no puede desactivar una exigencia del servidor.

Antes de este cambio bootstrap sustituía el valor de session.cookie_secure por
la detección HTTPS del origen. Un backend HTTP podía perder así la exigencia del
servidor aunque el navegador accediera mediante HTTPS a un proxy.

## Arranque público y desarrollo local

La plantilla Iniciar-Altoidss.cmd configura session.cookie_secure=1 al iniciar PHP
para el acceso público HTTPS. Antes de iniciar sincronización o túnel comprueba
por HTTP local los atributos de una cookie anónima y la salud del backend.
Si el servidor existente no cumple, aborta; no reinicia ni detiene procesos ajenos.
--check realiza esa comprobación cuando el backend ya responde. --check-runtime
solo comprueba herramientas y no inicia servicios.

Para iniciar únicamente un backend destinado al proxy desde la plantilla PS:

~~~powershell
./Iniciar-Catalogo-Central.ps1 -Environment produccion -Port 8091 -SecureCookies
~~~

La opción se aplica tanto al perfil de CheckRuntime como al proceso que sirve PHP.
No cambia el INI compartido. Es una opción de servidor, incompatible con Sync.
El PS sin SecureCookies conserva el modo HTTP local de desarrollo/pruebas; si su
INI ya exige Secure, se respeta esa exigencia. No retirar Secure para hacer funcionar
un acceso público por HTTP: usar el punto HTTPS previsto.

La configuración del proceso determina el modo; el nombre produccion no demuestra
por sí solo que exista TLS delante del backend. Un servidor iniciado manualmente
para acceso público también debe fijar session.cookie_secure=1. No publicar un
backend HTTP de pruebas mediante un túnel independiente que omita esta verificación.
El CMD no corrige un túnel ajeno que ya estuviera activo.

## Comprobación sin divulgar secretos

~~~powershell
python -B tools/check_session_cookie.py --url "http://127.0.0.1:8091/api/index.php?route=/health"
~~~

El comprobador solo acepta el health local; no sigue redirecciones ni envía cookies
previas o credenciales. Verifica Secure, HttpOnly, SameSite=Lax, Path=/ y cookie de
host. Emite atributos y estado, nunca valores de cookies o CSRF. Un fallo impide
continuar el arranque público. La petición crea una sesión anónima normal del backend.

PUBLIC_SESSION_COOKIE_VERIFIED verifica los atributos del origen; no certifica
el proxy ni el HTTPS público. Para cerrar AL-16 se debe comprobar la respuesta
recibida por el cliente HTTPS autorizado y su flujo de inicio/cierre de sesión.
Una redirección de Cloudflare Access solo confirma esa puerta de acceso.

## Pruebas y publicación

Las regresiones cubren HTTP local, política explícita del servidor, señal HTTPS
del SAPI, cabeceras falsificadas y login/logout. La prueba de integración añade un
frontal TLS local con backend HTTP y un certificado efímero generado mediante el
OpenSSL de PHP. El cliente confía exclusivamente en ese certificado, conserva
verificación TLS/hostname y usa cuentas ficticias; no cambia almacenes de certificados.
Claves, certificados, cookies y sesiones de esa fixture se eliminan con su temporal.

La instalación del código y las dos plantillas raíz sigue CI-CD.md, con respaldo,
plan, aprobación final y diario. Las pruebas de publicación usan el PS sin Sync y
fixtures; no ejecutar el CMD normal para comprobar únicamente el candidato.
Los originales históricos y G: quedan fuera de esta publicación.

Fuentes: [PHP: configuración de sesión](https://www.php.net/manual/en/session.configuration.php#ini.session.cookie-secure),
[PHP: parámetros de cookie](https://www.php.net/manual/en/function.session-set-cookie-params.php),
[OWASP: sesiones](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#secure-attribute).
