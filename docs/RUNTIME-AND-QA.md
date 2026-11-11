# Runtime independiente y pruebas reproducibles

Perfil revisado: PHP **8.4.27**, Python **3.13.12**, Node **22.22.0**.
PHP **8.2.35** se conserva como comparación de compatibilidad en QA. La rama 8.2
termina su soporte de seguridad el 31 de diciembre de 2026; 8.4 el 31 de diciembre de 2028.
Actualizar versiones y hashes del perfil requiere revisión y nuevas pruebas.

La aplicación sirve PHP, HTML, CSS y JavaScript directamente; no tiene una compilación frontend.
Node/Chromium son herramientas de pruebas. Python/openpyxl intervienen en las herramientas de hojas.
Los node_modules históricos se conservan para una intervención separada; QA usa exclusivamente `qa/node_modules`.

## Preparación en un checkout nuevo

Ejecutar desde la raíz del checkout con Python y Node de las versiones indicadas.
Usar carpetas nuevas: los preparadores rechazan destinos existentes y no modifican XAMPP,
el PATH global, servicios, cuentas ni descriptores operativos.

~~~powershell
python -B tools/setup_toolchain.py --destination runtime/qa-toolchain
npm --prefix qa ci --ignore-scripts --no-audit --no-fund
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) 'runtime/qa-browsers'
node qa/node_modules/playwright/cli.js install chromium
runtime/qa-toolchain/python/Scripts/python.exe -B tools/qa.py --php runtime/qa-toolchain/php-8.4.27/php.exe --suite all --output outputs/qa-primera-ejecucion
~~~

En Linux/CI se utiliza el PHP nativo de la misma versión, con curl, mbstring, openssl,
fileinfo, json, session y pdo_sqlite; el ZIP independiente corresponde a Windows x64 NTS.
Crear un venv e instalar `qa/requirements.txt` mediante pip `--require-hashes --only-binary=:all:`.
El CI fija Python/Node y ejecuta ambas versiones PHP en Windows y Linux.

`qa/requirements.txt` fija openpyxl 3.1.5 y et_xmlfile 2.0.0 con hashes de sus ruedas PyPI.
`qa/package-lock.json` fija Playwright 1.62.1, Bootstrap 5.3.8 y sus dependencias transitivas.
Instalar Chromium mediante ese Playwright fija también su revisión. No depende de Edge ni de NODE_PATH.
Para una comparación local opcional se admite `--browser-channel msedge`; debe registrarse como tal.

## Qué hace QA y dónde escribe

`tools/qa.py` verifica herramientas y SRI de Bootstrap, copia únicamente código permitido a
`SALIDA/fixture/app` y genera catálogo, noticias y colecciones privadas ficticios.
No copia data, secretos locales, OAuth, tokens, descriptores o dependencias históricas.
El entorno heredado de producción/proveedores y NODE_PATH se retira.
Los procesos de pruebas usan una carpeta temporal canónica dentro de la salida, evitando
alias 8.3 del perfil Windows sin relajar los controles de rutas de recuperación.

Ejecuta sintaxis Python/PHP/JS, regresiones Python y pruebas Node de paginación/orden/autenticación.
La integración de aprobación usa API PHP real de fixture y proveedores HTTP locales.
Después comprueba orden, móvil, 18 casos administrativos en nueve anchos y el flujo API.
La matriz administrativa declara su API simulada. Todos los servidores se vinculan a loopback y se cierran.
Bootstrap se sirve desde la dependencia bloqueada con el mismo SRI; el navegador bloquea las demás conexiones externas.
El backend no ejecuta sincronización ni consultas vivas a proveedores en estas pruebas.

La salida conserva logs, versiones, huellas del código probado, fixtures ficticias e informe JSON.
Una omisión, un fallo o un cambio del código fuente durante la ejecución impide declarar PASS.
Cada repetición usa una salida nueva. Los scripts históricos de capturas siguen siendo herramientas
manuales; el contrato de aceptación automático es `tools/qa.py --suite all`.

Comparación aislada de PHP 8.2:

~~~powershell
python -B tools/bootstrap_php.py --compatibility --destination runtime/qa-php-8.2.35
runtime/qa-toolchain/python/Scripts/python.exe -B tools/qa.py --php runtime/qa-php-8.2.35/php.exe --suite all --output outputs/qa-compatibilidad-82
~~~

## Runtime Windows y TLS

`tools/bootstrap_php.py` verifica el SHA-256 oficial del ZIP antes de extraer o ejecutar.
Rechaza rutas fuera del destino, enlaces, ADS, colisiones de mayúsculas, nombres reservados y sobrescrituras.
Prepara un php.ini desde la plantilla de producción del paquete, activa las extensiones declaradas,
fija America/Costa_Rica y configura una copia fechada y verificada del almacén CA publicado por curl.
TLS conserva sus verificaciones; no se deshabilita SSL para conseguir un PASS.
El manifiesto registra ejecutable, INI, CA y hashes de archivos. No mover el entorno ya generado:
sus rutas INI/venv son específicas del destino. Prepararlo de nuevo en el destino definitivo.

PHP 8.4 usa bcrypt con coste predeterminado 12. Los hashes previos siguen siendo verificables;
un login correcto puede actualizar su coste mediante el mecanismo transaccional existente.
La huella anterior de credencial deja entonces de autorizar sesiones previas.
No se cambian claves ni versiones de autenticación por instalar el runtime.

## Activación de la instalación C:

Preparar y probar el candidato, integrar por PR/CI y obtener aprobación final según `CI-CD.md`.
Antes de escribir en producción, revisar alcance, respaldo actual con credenciales ya rotadas y recuperación.
Instalar mediante el preparador/instalador previsto; no copiar todo desarrollo ni hacer checkout/reset de producción.

El toolchain definitivo se prepara en una carpeta nueva bajo `WORKSPACE/runtime/`.
La activación registra su `toolchain.local.json` como `WORKSPACE/runtime/toolchain.local.json`
mediante el diario aprobado y coloca las dos plantillas de `tools/deployment/` en la raíz.
El descriptor contiene rutas de herramientas y versiones, sin credenciales. No se versiona.

`Iniciar-Catalogo-Central.ps1` admite `-PhpExecutable`, `-PythonExecutable` y `-CheckRuntime`
para ensayos aislados. Verifica versión/extensiones o dependencias antes de iniciar.
`Iniciar-Altoidss.cmd --check-runtime` verifica el perfil sin iniciar servidor, Sheets ni túnel.
La ejecución normal del CMD conserva su comportamiento previo de iniciar servidor, sincronizador y túnel;
no utilizarla como smoke de publicación. El PS mantiene loopback y Sync requiere su opción explícita.

Las plantillas nuevas requieren el perfil aprobado; no recurren silenciosamente al XAMPP anterior.
Una recuperación conserva originales, rutas y hashes, y solo cambia el alcance aprobado.
Nunca restaurar usuarios.json anterior a la rotación ni reactivar sus sesiones.
G: y distribuciones históricas quedan fuera de estas operaciones.

Fuentes primarias: [soporte PHP](https://www.php.net/supported-versions.php),
[builds Windows y hashes](https://downloads.php.net/~windows/releases/releases.json),
[cambios PHP 8.4](https://www.php.net/manual/en/migration84.other-changes.php),
[certificados CA](https://curl.se/docs/caextract.html),
[navegadores Playwright](https://playwright.dev/docs/browsers).
