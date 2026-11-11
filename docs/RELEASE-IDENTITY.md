# Identidad del código instalado por alcance

El HEAD del checkout productivo puede conservar una rama antigua por diseño.
No identifica por sí solo las rutas instaladas mediante el proceso CI/CD.
Tampoco es correcto declarar todo el árbol igual al último SHA cuando se preservan
modificaciones y ausencias ajenas al alcance.

Al terminar una instalación correcta, el instalador escribe atómicamente el comprobante
privado runtime/deployed-release.local.json. No se versiona ni entra al paquete; el router
no sirve runtime. El comprobante contiene:

- SHA aprobado y base revisada del alcance, junto con el HEAD conservado.
- Rutas del alcance y hashes del paquete.
- Estados/hash preservados fuera del alcance, incluidas ausencias previstas.
- Identificadores del plan/operación, fecha y hash del comprobante anterior, si existe.

No contiene cuentas, contraseñas, tokens ni datos de catálogo. No certifica archivos raíz
del workspace, configuración operativa, runtime efectivo ni integraciones externas: esos
elementos se verifican en sus diarios propios. Es evidencia local de despliegue, no una
firma criptográfica o una prueba frente a un operador que pueda modificar el disco.

## Consultar y detectar drift

~~~powershell
python -B tools/release_status.py --app RUTA_APLICACION
~~~

La consulta lee el comprobante y calcula hashes sin invocar Git ni abrir sesiones.
VERIFIED_SCOPED_RELEASE significa que las rutas instaladas y los estados preservados
siguen como se registraron. fullPackageMatches solo es true cuando todo el paquete coincide.
DRIFT separa cambios dentro del alcance de cambios en los estados preservados.
UNRECORDED indica ausencia de comprobante: consultar el diario previo, sin inventar
una versión desde HEAD. INVALID_RECEIPT exige revisión. La consulta nunca corrige archivos.

Códigos de salida: 0 verificado, 1 drift/comprobante inválido, 3 sin comprobante.

## Transacción y recuperación

El preparador registra el hash previo del comprobante. Si cambia antes de instalar,
el instalador rechaza el plan antes de escribir código. El comprobante anterior se retiene
en el diario y el nuevo solo se escribe después de validar el código y los datos protegidos.
Un fallo recupera código y comprobante anteriores con control de drift; una adición se
retiene de forma recuperable. Un cambio ajeno impide sobrescribir durante recuperación.

La escritura del comprobante debe figurar en el candidato presentado para aprobación de
producción. No generar un comprobante retrospectivo para lotes antiguos sin verificar
su alcance y diario. La primera publicación con este soporte creará la evidencia nueva.

El cierre del despliegue requiere además HTTP, navegador, regresiones aisladas y comprobación
del runtime real según CI-CD.md. El estado local de código no sustituye esas pruebas.
