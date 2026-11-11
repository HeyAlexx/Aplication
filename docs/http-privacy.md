# Privacidad HTTP y registros atomicos

El router del servidor PHP integrado entrega solo las seis paginas, recursos
estaticos permitidos, cuatro representaciones publicas de catalogo/noticias y la
entrada `api/index.php`. No delega una URL arbitraria al servidor estatico.

Se validan la ruta solicitada y su destino canonico. Variantes de mayusculas de
directorios privados, scripts PHP fuera de la entrada API, enlaces a archivos
privados, temporales, segmentos ocultos y streams NTFS no abren esos recursos.
Las reglas se prueban en Windows y Linux porque sus sistemas de archivos difieren.

Las cuatro URLs de `data/*.json` se conservan como contrato de lectura del
frontend, pero ya no entregan las colecciones operativas sin filtrar. Catalogo
oculto y noticias borrador/archivadas no forman parte de estas respuestas.
La API de noticias conserva la gestion editorial para administradores
autenticados; visitantes y usuarios normales reciben solo noticias publicadas.
Esto no implementa todavia el futuro catalogo privado con aprobacion de cuentas.

El registro calcula el hash fuera del bloqueo y comprueba la unicidad del correo
dentro de una transaccion que incluye cuenta, perfil y preferencias. La sesion
se inicia despues de confirmar el almacenamiento. No se mezclan colecciones
privadas y catalogo central en esa transaccion.

## Pruebas

```powershell
python -B -m unittest discover -s tests -p test_http_privacy.py -v
python -B -m unittest discover -s tests -p test_auth_transactions.py -v
```

Son fixtures temporales sin configuracion OAuth, cuentas reales ni consultas a
proveedores. `PHP_BIN` permite indicar el ejecutable; de otro modo se descubre
PHP en PATH o en la ubicacion XAMPP local. Las pruebas de enlaces se declaran
omitidas si el sistema no permite crearlos. Un PASS sin esa capacidad no acredita
ese caso particular.

CI ejecuta ambas suites en Windows y Linux con PHP 8.2, y staging depende de que
ambas plataformas pasen. Esto no actualiza PHP en una instalacion real.

## Launcher raiz

`tools/deployment/Iniciar-Catalogo-Central.ps1` es el candidato versionado para
la ubicacion raiz del workspace. Su direccion predeterminada es loopback.
No se debe ejecutar desde su carpeta de plantilla ni copiar directamente desde
un checkout sin revisar.

La instalacion de la plantilla en la raiz es una etapa manual del despliegue:
usar el archivo del artefacto aprobado, verificar su SHA-256, respaldar el
launcher vigente y comprobar su hash esperado antes de reemplazarlo. Registrar
ese archivo adicional en el alcance de la aprobacion y el diario operativo.
El instalador habitual copia el paquete dentro de `Aplication`; no instala por
si solo esta plantilla en la raiz. G: y las distribuciones historicas se conservan.

## Limites y publicacion

El servidor integrado sigue siendo una herramienta local o para entornos
controlados, no un servidor para exposicion publica directa. Apache u otro
servidor necesitan restricciones equivalentes propias.

Estos cambios no rotan credenciales, revocan sesiones, migran datos ni activan
Sheets. La politica de futuras incorporaciones externas requiere aprobacion del
administrador y se implementara en su lote de autorizacion. La comprobacion de
cookies mediante el proxy real sigue siendo una validacion separada.

La publicacion se realiza por [CI/CD](CI-CD.md), con SHA fijo, respaldo verificado,
ensayo y aprobacion final. Una reversion no debe reabrir acceso a archivos privados.
