# Entorno de desarrollo aislado

## Distribución local actual

Desde el traslado verificado del 2026-10-19, el proyecto opera en el SSD C:. La copia antigua de G: se conserva, pero no debe usarse para ejecutar ni modificar la aplicación.

- Producción: `Altoids/ProyectoFinal/Aplication`, PHP en `127.0.0.1:8091`, acceso externo mediante Cloudflare Access.
- Desarrollo: `Altoids/Desarrollo/Aplication`, worktree separado; puerto 8092. Para revisión física se abrió en `0.0.0.0` dentro de una LAN de confianza.
- Catálogos y estado: `Altoids/datos/{produccion|desarrollo}`, fuera de los checkouts.

Los worktrees comparten historial Git, no archivos de trabajo. Las ramas compatibles de desarrollo pueden compartir el catálogo central del entorno mediante descriptor externo. No cambiar la rama de la instalación que atiende usuarios ni copiar datos de desarrollo sobre producción.

## Inicio sin sincronización

Desde la carpeta de desarrollo:

```powershell
.\tools\start-central.ps1 -Environment desarrollo -Port 8092
```

Para teléfono, añadir `-BindAddress 0.0.0.0` únicamente en una LAN de confianza; usar la IP local de la PC. No abrir ese puerto a Internet. El launcher inicia PHP, no Cloudflare ni Sheets cuando se omite `-Sync`. No inicia otro servidor si el puerto está ocupado. PHP debe estar en PATH o indicarse con `-PhpBin`. Detener con Ctrl+C.

Abrir `http://127.0.0.1:8092/Html/catalogo.html` y `/Html/dashboard.html?tab=table`. Actualmente Sheets sigue apagado por instrucción del usuario; no ejecutar el launcher raíz que arranca el monitor ni añadir `-Sync`.

## Datos y servicios externos

La copia de desarrollo no está anonimizada: contiene datos de catálogo y estado personal local. Nunca publicar usuarios, preferencias, sesiones, colas, revisiones operativas, OAuth o respaldos.

Los datos de prueba se refrescan desde una instantánea validada de producción solo mediante una operación explícita y respaldada. No hacerlo durante una revisión: puede sustituir pruebas y referencias históricas de desarrollo. Git no actualiza los datos operativos; sus antiguos JSON no sustituyen el catálogo central.

Sheets de desarrollo tiene configuración/OAuth propios y nunca debe apuntar a la hoja real. Las claves de lectura MAL/Watchmode se reutilizaron localmente con autorización del usuario; no copiarlas a Git ni trasladar credenciales de Google entre entornos. Las consultas externas y pruebas live son opt-in y pueden consumir cuotas.

## Ramas, publicación y estado actual

La rama de preparación es `fix/admin-mobile-mockup`. Producción permanece en `chore/dev-isolation` con cambios locales que deben conservarse. Crear próximas ramas desde código compatible y configurar su descriptor antes de arrancar; ver [diagramas y almacenamiento](CATALOG-STORAGE.md).

Aplicar [CONTRIBUTING.md](../CONTRIBUTING.md): commits selectivos, revisión y PR. Push, merge y despliegue son operaciones distintas. No hay despliegue automático ni release estable creada por esta preparación. Continuar según [avance numerado](RELEASE-PROGRESS.md).
