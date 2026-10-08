# Entorno de desarrollo aislado

## Distribución local actual

- Instalación existente: `G:\Coding Files\CodexProyects\Altoids\ProyectoFinal\Aplication`. Su lanzador protegido sigue apuntando allí, con el puerto 8091.
- Desarrollo: `G:\Coding Files\CodexProyects\Altoids\Desarrollo\Aplication`. Es un worktree Git separado creado desde el commit `0ab0850` integrado mediante el PR #1.
- Puerto de desarrollo: 8092, accesible solo en `127.0.0.1`.

Los dos directorios comparten el historial Git, pero no sus archivos de trabajo. No ejecutar tareas de desarrollo en la instalación existente ni cambiar allí de rama mientras atienda usuarios.

## Inicio

Desde la carpeta de desarrollo, ejecutar `Iniciar-Desarrollo.cmd`. Para comprobar que encuentra PHP y el router sin iniciar el servidor:

```powershell
.\Iniciar-Desarrollo.cmd --check
```

Abrir `http://127.0.0.1:8092/Html/index.html`. El lanzador no abre el navegador, no inicia Cloudflare ni el sincronizador y no busca otro puerto automáticamente si 8092 está ocupado. Detenerlo con Ctrl+C.

## Datos y servicios externos

El worktree contiene los archivos ya versionados en el repositorio, incluidos los datos y respaldos históricos que ya estaban allí. No es una base de prueba vacía ni un entorno anonimizado. Sus archivos están separados físicamente de los de la instalación existente.

No se copiaron desde la instalación los archivos locales ignorados de configuración de sincronización, OAuth, token de Google o Client ID de MyAnimeList. No copiar esas credenciales para probar nuevas funciones. Revisar también variables de entorno heredadas antes de ejecutar pruebas contra proveedores externos.

Para probar sincronización, preparar posteriormente una hoja de prueba y credenciales específicas, con autorización. No iniciar un segundo monitor contra la hoja real. No publicar datos personales o sesiones del entorno de prueba.

## Ramas y publicación

La rama `chore/dev-isolation` prepara este entorno. Las funciones posteriores comienzan en una rama nueva basada en `main` actualizado, siempre desde esta carpeta de desarrollo y con el checkout limpio.

Aplicar [CONTRIBUTING.md](../CONTRIBUTING.md): commit selectivo, pruebas y pull request. Un merge no copia archivos a la instalación existente ni cambia su lanzador. El despliegue y los respaldos siguen siendo pasos explícitos; aún no hay despliegue automático ni una release etiquetada.
