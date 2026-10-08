# Flujo de desarrollo y versiones

## Regla principal

Cada función, corrección o cambio de documentación se trabaja en una rama propia y llega a `main` mediante un pull request revisado. No desarrollar directamente sobre `main` ni subir allí cambios sin validar. `main` es la referencia de código integrado; producción debe ejecutar una versión publicada desde una instalación separada.

Este documento establece el procedimiento, pero no activa por sí mismo restricciones en GitHub ni automatiza despliegues. Esa configuración sigue pendiente.

## 1. Revisar el estado antes de empezar

Desde la carpeta `Aplication`:

```powershell
git status --short
git branch --show-current
git diff --cached --name-only
```

Si hay cambios pendientes, identificar a qué tarea pertenecen. No descartarlos ni mezclarlos con la nueva tarea. Confirmarlos en su rama cuando estén listos o trabajar en un checkout separado. Evitar guardar en Git datos personales, sesiones, tokens y archivos generados.

Los cambios sin commit pueden acompañar un cambio de rama: cambiar de rama no los aísla. No usar `git add .` para preparar una publicación.

## 2. Crear una rama por cambio

Con el checkout limpio y sin estar sirviendo producción desde él:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/nombre-del-cambio
```

Prefijos: `feature/` para funciones, `fix/` para correcciones, `docs/` para documentación, `research/` para prototipos y `release/` para preparar un lanzamiento. Los nombres del roadmap son propuestas; las ramas se crean al comenzar cada tarea.

Una investigación no autoriza migraciones ni cambios de datos reales. Mantener sus prototipos separados del funcionamiento actual.

## 3. Implementar y validar

1. Definir alcance y criterios de aceptación en el roadmap o en el pull request.
2. Revisar el modelo y respaldar datos antes de cualquier migración.
3. Implementar en pasos pequeños y explicar los cambios.
4. Ejecutar comprobaciones proporcionales al área afectada y probar el flujo de usuario.
5. Registrar el resultado, las limitaciones y lo que no pudo verificarse.
6. Actualizar README y la sección sin publicar del changelog cuando corresponda.

Ejemplos de comprobaciones existentes, según el área modificada:

```powershell
git diff --check
php tests/anime-review-service.php
php tests/myanimelist-service.php
php tests/review-source-probe.php
```

No ejecutar pruebas `--live` o el sincronizador contra fuentes reales como una comprobación inocua: requieren conexión, configuración y revisión de sus efectos. No afirmar que una prueba está automatizada si solo se ejecutó manualmente.

## 4. Preparar commit y pull request

Agregar únicamente rutas relacionadas con la tarea; inspeccionar `git diff --cached` antes del commit. Ejemplo para un cambio exclusivamente documental:

```powershell
git add -- ROADMAP.md CHANGELOG.md
git diff --cached --check
git diff --cached
git commit -m "docs: describe next development stages"
git push -u origin docs/nombre-del-cambio
```

La rama del último comando debe ser la rama actual de la tarea; los comandos son ejemplos, no un script para ejecutar completo. Abrir el pull request hacia `main` y completar la plantilla: alcance, pruebas, riesgos y recuperación. No incluir secretos en diffs, capturas ni descripciones.

Revisar el diff, resolver observaciones y validar antes de integrar. Preferir squash merge para que cada tarea integrada deje un commit reconocible. No hacer force-push sobre `main`.

## 5. Proteger main en GitHub

Configuración administrativa pendiente: crear una regla para `main` que requiera pull request, resolución de conversaciones y bloquee force-push y eliminación. Acordar quién podrá integrar y si habrá revisión por otra persona; un autor único no puede aprobar su propio pull request.

Exigir checks de CI solo después de que existan y se hayan verificado. Actualmente esta preparación no instala un workflow de pruebas ni configura reglas remotas. Hasta activarlas, el procedimiento depende de respetar esta guía.

## 6. Asignar una versión

`VERSION` es la referencia de versión del código. Durante desarrollo se usa un sufijo como `0.1.0-dev`; no es una versión publicada. No se agrega por esta etapa un indicador de versión en la interfaz.

- `0.MINOR.PATCH`: fase de evolución previa a 1.0.
- Incrementar MINOR para una función nueva o un cambio incompatible durante esta fase; documentar las incompatibilidades.
- Incrementar PATCH para correcciones compatibles y ajustes pequeños de mantenimiento/documentación publicados.
- El paso a `1.0.0` requiere acordar estabilidad y alcance; no ocurre automáticamente.

Antes del lanzamiento, crear `release/numero-de-version`, cambiar `VERSION` al número elegido sin `-dev`, cerrar la sección correspondiente del changelog con la fecha real y validar. Integrar esa preparación mediante pull request. No aumentar la versión por cada commit ni etiquetar código todavía pendiente de integración.

Sobre el commit ya integrado y validado, crear una etiqueta anotada y publicarla. Ejemplo, solo cuando se apruebe realmente `0.1.0`:

```powershell
git tag -a v0.1.0 -m "Altoidss 0.1.0"
git push origin v0.1.0
```

Comprobar el commit antes de etiquetar. La etiqueta identifica código, no una copia de datos; una release de GitHub y su despliegue son pasos posteriores. No mover etiquetas ya publicadas.

## 7. Separar desarrollo y publicación

El lanzador local actual utiliza `ProyectoFinal/Aplication`. Si esa carpeta también atiende usuarios, las ediciones y cambios de rama pueden afectar lo que sirve aun sin merge. No considerar el aislamiento resuelto solo por crear ramas.

Antes de iniciar funciones, preparar una instalación de ejecución separada, con datos y credenciales propios, y otra de desarrollo con copias de prueba. Definir rutas, puertos y procesos antes de cambiar el lanzador. Mantener Cloudflare Access y las protecciones de archivos privados; no hacer pública la aplicación como parte de este flujo.

Se preparó un worktree local de desarrollo separado de la instalación existente. Sus rutas, limitaciones de datos e inicio sin sincronización se describen en [Entorno de desarrollo aislado](docs/development-environment.md). El lanzador de la instalación existente no se modifica.

Para publicar: respaldar datos, registrar la versión anterior, desplegar la etiqueta aprobada en la instalación de ejecución y verificar autenticación, catálogo, archivos privados y sincronización. No asumir que un push despliega la aplicación; no se ha configurado despliegue automático aquí.

## 8. Recuperación y cierre

Si un lanzamiento falla, volver a la versión anterior en la instalación de ejecución siguiendo un procedimiento probado. Si hubo migración de datos, restaurar también un respaldo compatible: volver al código anterior no revierte los datos.

Registrar resultado de publicación y limitaciones. Cerrar la tarea solo después de su validación; no marcar funciones futuras como terminadas porque su documentación se integró.
