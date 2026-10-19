# Respaldo coordinado y reanudación tras un reinicio

## Punto de control actual

Paso 5 completado el 2026-10-19, 10:58 (Costa Rica); los pasos 3 y 4 solo preparan/ensayan. No integrar, desplegar,
inicializar el histórico de producción ni arrancar Google Sheets sin autorización.
El proyecto operativo está en `C:\Users\Alvar\Projects\Altoids`, no en el disco G:.

Después del BSOD del 2026-10-19 se comprobaron JSON, hashes y objetos Git antes
de reanudar los servidores. Las capturas interrumpidas se conservan, pero ninguna
con estado `INCOMPLETE`, sin manifiesto o con `.incomplete` es restaurable.
El evento Kernel-Power registra `0x124` con primer parámetro `0x10`; no identifica
el dispositivo responsable. No hay minidump nuevo disponible. No se repararon
discos ni cambiaron controladores o configuración del sistema.

Repetición satisfactoria: `F:\Altoidss-Backups\20261019-104819-739-step5`,
19.072 archivos, 3.114.526.734 bytes. ZIP `VERIFIED` y operador
`BACKUP_AND_RECOVERY_VERIFIED`. Ensayo completo:
`work/recovery-drills/coordinated-20261019-105306-379273/report.json`, `PASSED`.
Se verificaron nueve colecciones centrales y cinco privadas por entorno,
cuatro JSON de estado de producción, 809 contenidos por entorno y objetos Git.
No se escribieron datos vivos ni se consultó Google. Los servidores estuvieron
pausados 10:48:28–10:53:03 y después respondieron HTTP 200; Access mantuvo 302.
Las 59 pruebas Python pasaron, incluidas corrupción, rutas largas e interrupción
simulada. El backup precede al commit de documentación de cierre: regenerar el
paquete y revisar frescura del respaldo al autorizar una instalación posterior.

## Secuencia numerada

1. Verificar procesos, puertos, JSON y ausencia de diarios de transacción tanto
   centrales como privados. No ejecutar el launcher raíz: inicia Sheets.
2. Con autorización de pausa, ejecutar desde el checkout de desarrollo:
   `./tools/coordinated-backup.ps1 -PauseAndResume` en PowerShell. Requiere PHP,
   Python y permisos sobre C:/F: y procesos. El script comprueba que F: es NTFS,
   figura saludable y está en otro disco físico distinto de C:/G:. Esto no es una
   prueba completa de salud del hardware.
3. Detener exclusivamente los dos PHP identificados y registrar la pausa.
   Capturar directamente a `F:\Altoidss-Backups\<fecha>-step5\project.zip.incomplete`.
   Se evita otra copia completa intermedia en el SSD. Los checkpoints de avance
   siguen siendo `INCOMPLETE`: no autorizan restauración parcial.
4. Verificar inventario y hashes de origen durante la pausa, CRC del ZIP y SHA-256.
   Solo entonces promover a `project.zip` y `status.json: VERIFIED`. El bloque
   `finally` intenta reanudar ambos PHP incluso ante un error normal; no puede
   ejecutarse durante un BSOD o corte eléctrico. Tras un reinicio, revisar y
   reanudar explícitamente, sin reutilizar PIDs antiguos.
5. Con los servidores nuevamente activos, restaurar **todos** los archivos desde
   F: en una carpeta nueva `work/recovery-drills/coordinated-*/workspace` en C:.
   Comprobar cada SHA-256, lecturas PHP CLI de ambos entornos con descriptores
   aislados y `git fsck` del almacén de objetos copiado. No ejecutar launchers,
   descriptores operativos ni worktrees copiados con rutas absolutas antiguas.
6. Revalidar todos los archivos restaurados. Exigir `recovery-report.json: PASSED`
   y `operator.json: BACKUP_AND_RECOVERY_VERIFIED` antes de cerrar el paso 5.
   Una copia `VERIFIED` sin ensayo aprobado todavía no completa este paso.

Si una ejecución se interrumpe, conservar su carpeta para diagnóstico y generar
un destino nuevo; no sobrescribirla ni completar manualmente su estado. Nunca
restaurar una copia encima de los datos vivos como reacción automática al BSOD.

## Alcance y límites

Incluye código de ambos checkouts, objetos/refs/índices Git y archivos locales,
catálogo/estado central, datos privados, configuraciones y evidencias anteriores.
El ZIP contiene secretos y **no está cifrado**: se restringe su carpeta NTFS al
usuario actual, SYSTEM y Administradores. No adjuntarlo al PR ni publicarlo.
F: es una unidad física independiente, pero interna: no sustituye una copia
externa/offline ni protege por sí sola frente a robo o ransomware.

No se siguen junctions/reparse points; sus referencias quedan documentadas.
Se excluyen logs, cachés Python, bloqueos temporales, PID de watcher y árboles de
ensayos/capturas derivados para evitar copias recursivas. No es una imagen de
Windows ni instala PHP/Python/Node. No copia configuración externa del túnel ni
reactiva sesiones PHP, OAuth o sincronización; no prueba escritura real en Sheets.
Los permisos NTFS originales por archivo no se reconstruyen como imagen de disco.

La escritura atómica y los diarios de JSON ayudan frente a interrupciones, pero
no garantizan supervivencia ante un fallo físico ni reemplazan este respaldo.
El ensayo prueba recuperación aislada; una recuperación operativa real exige
revisar rutas, permisos, secretos y autorización antes de reabrir escritores.

El código de parada y el parámetro se interpretan según [Microsoft: bug check
0x124](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x124---whea-uncorrectable-error).
No atribuir el fallo a un disco concreto sin evidencia adicional ni dar por
resuelta la estabilidad del equipo porque el ensayo haya pasado.
