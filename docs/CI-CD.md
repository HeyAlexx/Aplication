# CI/CD y publicacion controlada

## Regla obligatoria

Todo paso a produccion debe seguir este flujo. No editar directamente la instalacion
que sirve usuarios para implementar o probar un cambio. La aprobacion visual de la
marca y la autorizacion para trabajar no sustituyen las verificaciones del pipeline.

## Etapas y evidencia

1. Rama propia desde `main`, cambios acotados, comentarios y documentacion. Commit
   selectivo sin datos operativos, secretos, sesiones ni respaldos.
2. Push y pull request a `main`. `.github/workflows/ci.yml` ejecuta sintaxis,
   regresion de paginacion y orden, y pruebas del preparador/instalador de releases.
3. Build mediante `tools/ci_release.py build --output RUTA`: exporta blobs del SHA
   exacto usando la lista permitida del preparador existente. Genera `code.zip` y
   `manifest.json` con SHA del commit y huellas SHA-256. No compila el frontend:
   esta aplicacion sirve HTML/CSS/JavaScript y PHP directamente.
4. Entrega del artefacto al job de staging. `tools/ci_release.py smoke --package RUTA`
   verifica todos los hashes, inicia PHP temporal con un catalogo ficticio y
   comprueba paginas, JS, CSS, imagenes, lectura aislada y privacidad por HTTP.
   No consulta proveedores ni inicia Google Sheets. Los resumenes de Actions
   muestran los resultados del build y staging; el artefacto dura 14 dias.
5. Revisar el PR y los resultados del SHA que se va a integrar. Tras el merge,
   esperar tambien el CI del nuevo SHA de `main`: las pruebas de un SHA anterior
   no validan automaticamente el resultado del merge.
6. Preparar la publicacion local del SHA integrado con `prepare_code_release.py`,
   revisar el inventario de diferencias locales y ensayar el paquete. Su contenido
   debe coincidir con el artefacto de CI del mismo SHA. No copiar todo desarrollo.
   Elegir y registrar una base revisada para `--scope-from SHA_BASE`: el instalador
   verifica el paquete completo pero solo cambia las rutas modificadas desde esa
   base. Conserva y registra diferencias previas ajenas. No reutilizar la base de
   otra publicacion sin revisar el inventario. La base debe ser un SHA completo
   ancestro del candidato; una eliminacion de codigo se rechaza. No declara toda
   la instalacion identica al SHA.
7. Antes de produccion: mostrar al usuario PR/SHA, CI, staging, archivos afectados,
   respaldo y plan de recuperacion. Obtener su aprobacion final del candidato.
8. Con escritores detenidos y respaldo verificado, instalar mediante
   `install_prepared_release.py`, con SHA fijo y diario de recuperacion. Preservar
   datos, descriptor, secretos, OAuth, dependencias, rama y cambios locales ajenos.
   Reiniciar solo el servidor necesario; no activar ni reconfigurar Sheets.
9. Verificar en produccion las paginas/recursos, el flujo de usuario y las rutas
   privadas. Registrar por separado cualquier limitacion de acceso publico. Solo
   entonces declarar el despliegue completado; si falla, revertir solo el codigo.

## Limites actuales

CI, build, artefacto y staging HTTP estan automatizados en GitHub Actions. La
instalacion de produccion es local en Windows y se mantiene como etapa manual
controlada despues de la aprobacion. Este workflow no tiene acceso a la PC ni a
credenciales de produccion; no se ha configurado un runner de despliegue remoto.
No declarar un CD completamente automatico ni un bloqueo obligatorio de GitHub
si la configuracion del repositorio no lo demuestra.

El smoke de CI no sustituye las pruebas visuales en navegador ni comprueba OAuth,
proveedores o sincronizacion real. Pruebas locales adicionales deben registrarse
con el SHA y el entorno que verificaron.

## Ejecucion local

```powershell
node tests/catalog-pagination-state.cjs
node tests/content-order.cjs
python -m unittest discover -s tests -p test_code_release_preparation.py
python -m unittest discover -s tests -p test_release_installation.py
python tools/ci_release.py build --output RUTA_FUERA_DEL_CHECKOUT
python tools/ci_release.py smoke --package RUTA_FUERA_DEL_CHECKOUT --php C:\xampp\php\php.exe
```

Usar rutas de paquete independientes. El build empaqueta el commit, no los archivos
sin confirmar. Para inventario/instalacion, seguir tambien
[INSTALLATION-PLAN.md](INSTALLATION-PLAN.md) y
[DEPLOYMENT-CENTRAL.md](DEPLOYMENT-CENTRAL.md).

Referencias oficiales: [artefactos de Actions](https://github.com/actions/upload-artifact)
y [control de despliegues](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments).
