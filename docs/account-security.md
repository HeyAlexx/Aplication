# Cuentas, sesiones y aprobación de títulos externos

Este lote amplía la seguridad del sistema PHP/JSON existente. No cambia la arquitectura cloud,
no aprueba cuentas del piloto y no modifica el formulario de contenido.

## Autenticación y sesiones

El backend admite cuentas con status Activo y roles admin/usuario. Conserva sus IDs.
La sesión guarda la versión de autenticación, una huella del hash de contraseña y tiempos del servidor;
esos datos internos no se devuelven al navegador. Las sesiones antiguas que carezcan de este estado
se invalidan y requieren iniciar sesión de nuevo.

Cada solicitud revalida la cuenta; las operaciones sensibles fuerzan una lectura actual.
Eliminar/desactivar la cuenta, cambiar su rol, incrementar authVersion o cambiar su hash invalida
su sesión anterior. Los cambios de rol requieren autenticarse de nuevo.
La inactividad máxima es 30 minutos y la duración absoluta ocho horas.
Se regeneran ID y CSRF al autenticar o invalidar. PHP usa solo cookies y modo estricto de sesión.

El login reserva de forma atómica intentos antes de verificar la contraseña.
Ventana fija de 15 minutos: cinco intentos por cuenta/origen, diez por cuenta y cien por origen.
Los rechazos no prolongan la ventana. Un login correcto reinicia los contadores de cuenta/par,
pero no el total de origen. Los registros vencidos se purgan y el almacén tiene tamaño limitado.
El origen es REMOTE_ADDR: no se confía en X-Forwarded-For ni en cabeceras de Cloudflare sin
una configuración de proxy verificada. Detrás de un túnel, varios usuarios pueden compartir
el límite de origen; la limitación por cuenta sigue activa. El estado se guarda bajo backups/security,
fuera de las rutas públicas y del paquete Git.

El navegador requiere autenticación del servidor. Ya no verifica ni guarda contraseñas en
localStorage cuando PHP no responde. Al cargar la versión nueva retira las antiguas claves
altoidss_auth_users y altoidss_auth_session; conserva las colecciones de perfiles y catálogo.
La previsualización estática sigue mostrando catálogo como visitante, sin cuentas locales.
Un fallo de red al cerrar sesión no se presenta como confirmación del cierre en el servidor.

## Restablecimiento local: AL-01

La publicación de código no rota las credenciales reales. AL-01 solo se cierra después
de una operación local comprobada para cada cuenta afectada.

El operador requiere una terminal interactiva. Recibe contraseña y confirmación con getpass;
no admite contraseñas en argv, chat o archivos de plan. Envía el secreto al proceso PHP por
un pipe anónimo y nunca devuelve el hash. El helper PHP solo funciona como CLI y ambos
operadores limitan las rutas operativas a las instalaciones previstas de C:. G: queda excluido.

Ejemplo de operador, después de instalar el release aprobado:

~~~powershell
python -B "C:\Users\Alvar\Projects\Altoids\ProyectoFinal\Aplication\tools\reset-account-password.py" --app "C:\Users\Alvar\Projects\Altoids\ProyectoFinal\Aplication"
~~~

Para revocar sesiones sin cambiar contraseña, agregar --revoke-only.
Elegir la cuenta en la terminal local. Cada contraseña nueva debe tener al menos 15 caracteres,
máximo 72 bytes UTF-8 y ser distinta de la anterior. No se truncan contraseñas para bcrypt.

La operación confirma usuarios.json en una transacción: mantiene ID, rol, estado y campos ajenos,
cambia el hash cuando corresponde, incrementa authVersion y fecha la revocación.
Conserva un respaldo mediante JsonStorage. No altera perfiles, historial, favoritos ni preferencias.
Antes de operar, comprobar respaldo privado y escritores detenidos; después comprobar acceso nuevo,
rechazo de la credencial anterior, revocación e integridad de relaciones.
Registrar solo resultado, IDs y versiones; nunca texto de contraseña.
Los hashes nuevos de producción no se agregan a Git: AL-02 (datos ya versionados e historial)
continúa siendo una tarea separada.

## Solicitudes de catálogo: AL-04

Guardar un título existente modifica solo los favoritos del usuario en una transacción privada.
Un ID externo desconocido se valida por proveedor y número. El servidor obtiene los metadatos
desde sus adaptadores con URLs construidas por él; título, imagen, URLs y campos de auditoría
del cliente no son autoridad para publicar.

El favorito y su solicitud se guardan juntos en datos privados, sin tocar el catálogo compartido.
El usuario conserva el favorito pendiente o rechazado y ve su estado.
Un título oculto no reaparece desde una copia privada. Eliminar un favorito cancela su solicitud
pendiente. Reagregar una cancelada respeta el límite de pendientes; una rechazada no se reabre
automáticamente.

Límites: 20 solicitudes pendientes por usuario, 10.000 solicitudes conservadas por instalación,
20 resoluciones externas por usuario y 200 por instalación en 15 minutos.
La reserva de consultas ocurre antes de I/O y persiste aunque el proveedor falle.
Un favorito repetido reutiliza su candidato verificado sin consumir otra consulta.
Estos límites no sustituyen las cuotas del proveedor ni implican contratar un plan.

El administrador revisa las solicitudes desde Perfil → Revisión → Solicitudes de títulos externos.
Solo admin puede consultar la cola y aprobar/rechazar; las mutaciones requieren CSRF.

- GET /catalog/requests: cola privada del administrador.
- POST /catalog/requests/{id}, decision approve/reject: decisión.
- GET/POST/DELETE /favorites conserva el contrato existente.

La aprobación vuelve a consultar al proveedor fuera del bloqueo y comprueba otra vez cuenta,
rol y claim al confirmar el catálogo. No se publica el snapshot recibido del cliente.
Las URLs de datos privados de solicitudes no se sirven por HTTP.
Los registros provienen de Jikan, AniList, Kitsu o Watchmode. Watchmode conserva su alias de búsqueda
de anime; el administrador revisa esa clasificación antes de publicarla.

## Recuperación de aprobaciones

No se agrupan escrituras del catálogo central y de datos privados en una misma transacción.
Se utiliza una secuencia idempotente:

1. Reclamar la solicitud en privado como approving, con token y vencimiento de cinco minutos.
2. Obtener metadatos actuales fuera del bloqueo.
3. Revalidar administrador y claim dentro de la transacción que incorpora el título.
4. Finalizar en privado como approved y registrar administrador/fecha.

Un mismo administrador puede reanudar su operación; otro puede reclamarla tras vencer el claim.
Una petición antigua no publica después de perder su claim.
Si falla antes de publicar, vuelve a pending. Si ya se confirmó el catálogo pero no la finalización
privada, el reintento reutiliza el mismo ID y no duplica el título. No borrar manualmente la cola
para resolver ese estado. No se generan vínculos ni filas de Sheets para estas altas.

## Pruebas y publicación

Las regresiones usan cuentas ficticias, almacenes privados/centrales distintos y proveedores locales.
Cubren revocación, estado/rol, expiración, contraseña nueva y anterior, límites, acceso por rol/CSRF,
metadatos manipulados, favoritos privados, aprobación/rechazo, concurrencia y recuperación.
La integración de navegador usa API real de fixture; la matriz administrativa general conserva
sus simulaciones declaradas. Los proveedores vivos y el proxy real quedan fuera de estas pruebas.

Aplicar CI/CD con SHA fijo, paquete, staging y plan revisados. Separar la instalación del código
de la rotación operativa, que necesita entrada protegida del usuario.
Una reversión no debe restaurar credenciales publicadas ni reactivar sesiones anteriores.
G: y las distribuciones históricas se conservan.

Referencias primarias:
[OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
[OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[OpenAPI oficial de Watchmode](https://api.watchmode.com/openapi.json).

