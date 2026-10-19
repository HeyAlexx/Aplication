# Paso 3 — preparación de instalación, sin desplegar

Fecha: 2026-10-19. Código ensayado: `71d96c14eb6072471d915ff167fb11e3949f2270`, PR #3 en borrador. Producción conserva su rama `chore/dev-isolation` y HEAD `0337dd83d25f84df29dc7d88aed38e621ceeebab`, con sus cambios locales intactos. El HEAD de Git no representa por sí solo todo el código instalado cuando hay modificaciones locales.

Este paso prepara y ensaya, no autoriza merge, instalación, reinicios, migración de datos ni arranque de Sheets. Tampoco implementa un instalador automático.

## 3.1 Inventario y paquete aislado

`tools/prepare_code_release.py` exporta una lista permitida de archivos del SHA indicado, nunca del directorio de desarrollo sucio. El paquete ensayado contiene 112 archivos de código/recursos/pruebas/documentación. Quedan fuera `data`, `config`, `runtime`, `backups`, `outputs`, dependencias, archivos locales de credenciales y launchers `.cmd`.

Salida privada: `work/installation-plans/<fecha>-<sha>/`. Contiene `code/`, copias exactas del código local en `production-local/` y `manifest.json` con hashes y condiciones previas. No publicar el inventario ni las copias. El paquete de código no contiene los JSON operativos de desarrollo.

El preparador no modifica producción, no inicia procesos de sincronización, no cambia ramas y no planifica eliminaciones. Si detecta un cambio de datos/código durante la lectura, rechaza validar el plan. Si cambian el SHA o los archivos reales después, hay que regenerarlo; no es una autorización permanente.

## 3.2 Revisión de las modificaciones locales

El inventario registró 546 entradas de estado Git. Se excluyen de la instalación 532 diferencias de dependencias/generados, incluido un archivo compilado Python. No se borran, restablecen ni trasladan a la rama de desarrollo.

Los otros 14 archivos se preservaron y revisaron:

| Grupo | Archivos | Decisión preparada, no aplicada |
| --- | --- | --- |
| Solo finales de línea respecto al HEAD de producción | `CHANGELOG.md`, `CONTRIBUTING.md`, `Iniciar-Desarrollo.cmd`, `docs/development-environment.md` | Conservar originales en respaldo; actualizar documentación desde el código aprobado. El launcher queda fuera del paquete y permanece intacto. |
| Ya coinciden con el candidato, ignorando CRLF | `ROADMAP.md`, `api/config/catalog-storage.php` | No requieren combinación funcional. |
| Soporte central previo ampliado por el PR | `api/core/JsonStorage.php` | Conservar la selección de catálogo externo; el candidato añade bloqueo/diario recuperable. No volver al almacenamiento versionado antiguo. |
| Router central previo ampliado | `server-router.php` | El candidato mantiene catálogo central y privacidad; cambia lectura directa por `JsonStorage` con recuperación/bloqueo. |
| Sincronizador central/completitud previo ampliado | `tools/anime_sync_pipeline.py` | El candidato conserva centralización, espejo y reparación de códigos; añade protección concurrente e incorporación por lotes. Instalar código no autoriza ejecutarlo. |
| Utilidades antiguas | `tools/apply_anime_review.py`, `tools/enrich_anime_metadata.py`, `tools/import_anime_excel.py`, `tools/sync_anime_workbook.py` | Mantener sus rutas centrales; la versión del PR impide escrituras masivas que eludan aprobación/cola. |
| Módulo local aún sin seguimiento en producción | `tools/catalog_storage.py` | Mantener el resolutor externo; el candidato incorpora además `guard_legacy_write`. Respaldar el original, no descartarlo por ser untracked. |

La clasificación automática marcó siete solapamientos y una colisión con archivo no seguido; no significa que el PR tenga conflictos con `main`. La revisión de sus diferencias confirma que las funciones locales de centralización/completitud están incorporadas o ampliadas por el candidato. No se aplicó una mezcla automática ni se reinterpretaron cambios del usuario.

## 3.3 Ensayo de compatibilidad

Se construyó otra carpeta de ensayo desde el paquete; solo se copiaron nueve colecciones del catálogo de producción, nunca sus cuentas, secretos, OAuth o configuración de sincronización. Se creó un descriptor exclusivamente aislado y un usuario ficticio. PHP CLI leyó las colecciones con el código candidato, sin abrir un servidor ni consultar red/proveedores.

Resultado: 784 animes, 15 películas, 10 series, cuatro noticias, 781 filas del espejo, una revisión y cero devoluciones pendientes; todos los códigos del espejo están en el catálogo. Total visible: 809 contenidos. Los JSON de ensayo no cambiaron. Las 31 huellas protegidas de producción (catálogo, estado, datos personales, descriptor y configuración local existente) permanecieron iguales.

Producción registra cero inicializaciones históricas: el candidato es compatible con ese estado anterior y no lo migra al leer. Las fechas/orden definitivos requieren el paso 4. Este ensayo no sustituye las pruebas HTTP, de concurrencia o de navegador, ni el ensayo de recuperación coordinada del paso 5.

Comandos reproducibles desde desarrollo:

```powershell
python -m unittest discover -s tests -p test_code_release_preparation.py
python tools/prepare_code_release.py --commit SHA_COMPLETO_DEL_COMMIT_REVISADO --php 'C:\xampp\php\php.exe'
```

El SHA debe tener 40 caracteres; no se acepta una rama móvil como `HEAD`. En otra distribución indicar `--workspace` y `--source`. No usar un checkout de producción como fuente. El informe privado está en `rehearsal/report.json`; el propio arnés PHP rechaza la instalación real y exige descriptor aislado.

## 3.4 Condiciones para la instalación futura

1. Completar la vista previa/migración propia de producción del paso 4 y la recuperación/copia independiente del paso 5. Resolver o aceptar expresamente la salvedad de Jikan.
2. Obtener aprobación explícita para merge y despliegue; registrar el SHA finalmente autorizado. Regenerar paquete/inventario con ese SHA y con el estado real del momento. Un squash/merge puede cambiarlo respecto al ensayado aquí.
3. Con autorización, detener escrituras y el PHP de producción para no servir una mezcla de archivos viejos/nuevos. Mantener Access; no hacer pública la aplicación ni modificar el túnel para eludirlo. Sheets ya debe estar apagado y seguirá apagado.
4. Crear respaldo consistente y verificar los hashes esperados de todos los destinos, archivos locales y datos protegidos. Ante cualquier divergencia, detener la instalación y revisar; no forzar reemplazos.
5. Reemplazar únicamente las rutas de código revisadas del manifiesto, con copias de los originales para rollback. Preservar `.git`, datos personales, catálogo central, descriptor, configuración, OAuth, sesiones, dependencias y launchers. No copiar carpetas completas de desarrollo ni borrar archivos ausentes del paquete.
6. Registrar el SHA realmente instalado fuera de Git y las diferencias locales conservadas. No fingir que cambiar de rama o `git pull` actualiza esta instalación sucia de forma segura.
7. Arrancar PHP con el router y el descriptor de producción, sin iniciar el launcher raíz ni ningún monitor. Comprobar catálogo, autenticación, privacidad, Access y móvil/escritorio. Solo entonces registrar el paso 6 como desplegado.

Para un fallo solo de código, restaurar los archivos de código de la fase previa con el servidor detenido, sin devolver datos antiguos. Un rollback que cruce formatos de datos requiere un plan compatible y la conciliación de cola/revisiones. Ver [despliegue y reversión](DEPLOYMENT-CENTRAL.md).
