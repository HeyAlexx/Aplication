# Árbol versionado y datos privados

El código, documentación, ejemplos sanitizados y manifiestos QA pertenecen a Git.
Las colecciones operativas, cuentas, actividad, sesiones, respaldos, tokens, runtime
instalado, outputs y node_modules permanecen locales. Las pruebas generan sus fixtures.

La retirada de seguimiento usa exclusivamente el índice de una rama aislada.
Los archivos locales se conservan y .gitignore evita su alta accidental futura.
No ejecutar git rm normal, git clean/reset ni una sincronización para replicar esta
retirada sobre una instalación. Producción y desarrollo conservan datos y dependencias.
La copia histórica G: queda fuera de acceso, limpieza, cambios de rama o sincronización.

Un commit normal solo sanea el árbol futuro. Los objetos anteriores, refs, PR, clones
y forks pueden conservar lo publicado. El saneamiento del historial requiere un
inventario, ensayo y aprobación específicos; este cambio no hace force-push ni purga.
Las credenciales expuestas necesitan su revocación/rotación propia.

## Control preventivo

Antes de crear el commit, desde la raíz de la rama aislada:

~~~powershell
python -B tools/repository_hygiene.py --index --output outputs/hygiene-index.json
~~~

Para revisar exactamente un commit:

~~~powershell
python -B tools/repository_hygiene.py --commit HEAD --output outputs/hygiene-commit.json
~~~

El control lee blobs del índice/commit, incluso si el archivo de trabajo cambió después.
Rechaza directorios operativos/generados, configuraciones locales y firmas de alta
confianza de claves privadas, hashes bcrypt y ciertas credenciales de proveedores.
Los ejemplos permitidos también pasan por el control de contenido. No imprime valores
coincidentes; la salida opcional contiene solo rutas/reglas y debe revisarse antes de compartirla.
El hash ficticio ya usado como igualador de tiempos tiene una excepción por digest exacto,
ruta y declaración DUMMY: cualquier otro valor, lugar o uso sigue rechazado.
Es una prevención acotada, no un escáner exhaustivo de datos personales, secretos o historia.

CI ejecuta este control sobre todo el árbol. Build y preparador revisan además cada payload
exportable; staging rechaza contenido prohibido aunque coincida con el manifiesto.
Las pruebas de rechazo utilizan sentinelas sintéticas, nunca credenciales operativas.

## Copias nuevas y producción existente

Un checkout nuevo no incluye cuentas ni catálogo operativo. Para QA, seguir RUNTIME-AND-QA.md:
la suite genera datos ficticios sin importar los privados. Para una instalación real, usar
descriptores y datos privados del proceso de recuperación aprobado; no crear cuentas demo
para sustituir las existentes. Mantener los IDs y relaciones.

El instalador de código sigue excluyendo datos, secretos y dependencias. Las retiradas de
seguimiento no se convierten en eliminaciones del disco productivo. Un scope revisado puede
contener retiradas no exportables; cualquier eliminación de código exportable se rechaza.

Fuente primaria: [GitHub: eliminación de datos sensibles](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
