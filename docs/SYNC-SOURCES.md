# Fuentes de sincronización y configuración local

La configuración operativa está en config/anime-sync.json y no pertenece al paquete
de código. No copiarla desde otro entorno ni distribuir identificadores o credenciales.

## Precedencia actual

1. googleSheets.writeBackEnabled=true selecciona OAuth. No consulta el Excel local
   ni cambia a otra fuente si falla Google. La opción describe el modo existente:
   una previsualización no procesa devoluciones pendientes a la hoja.
2. Sin ese modo, --url tiene prioridad sobre googleExportUrl. Si hay una URL,
   descarga y lee su XLSX temporal; lo retira después de la lectura. Un error de
   descarga no utiliza silenciosamente el archivo local.
3. Sin OAuth ni URL, --workbook tiene prioridad sobre workbook de la configuración.
   Es una fuente explícita, cuya actualización y vigencia controla el operador.
4. Sin fuente válida se informa que falta un Excel o una URL exportable. No se
   debe restaurar un origen histórico como mecanismo automático de recuperación.

Los argumentos de Excel/URL no desactivan OAuth cuando writeBackEnabled=true.
Una ruta relativa de Excel se interpreta desde el directorio de ejecución; usar
una ruta absoluta explícita para un uso manual desde otro directorio. El ejemplo
usa imports/catalogo.xlsx y no incluye un archivo operativo.

## Retirar una referencia obsoleta

Si la instalación usa OAuth y conserva una clave workbook antigua, su retirada
debe ser una operación de configuración revisada. No ejecutar una sustitución
global de rutas ni copiar el Excel histórico.

Antes de aplicar, guardar el archivo original de forma privada, fijar su SHA-256 y
preparar el candidato eliminando únicamente workbook. Comprobar igualdad de todas
las demás claves, especialmente googleSheets y googleExportUrl. Ensayar OAuth,
exportación, Excel explícito, errores sin fallback y ausencia de fuente con datos
ficticios; las pruebas no abren unidades históricas ni solicitan autorización real.

Aplicar solo con aprobación final, escritores detenidos y respaldo restaurado,
siguiendo docs/CI-CD.md. El instalador de código excluye configuraciones privadas;
la operación debe registrar por separado su único destino y el comprobante de código.
Una variación de hash exige repetir el inventario antes de reemplazar el archivo.

Conservar token, identificador de hoja, pestaña, clientes OAuth y datos. No iniciar
el watcher real como prueba de instalación. Si hay que recuperar la configuración,
verificar primero el hash instalado y no activar automáticamente el origen antiguo.

Las diez regresiones de test_sync_source_selection.py prueban el despacho real de
process_once sobre almacenamiento ficticio y proveedores simulados. La selección
por sí sola no certifica conectividad ni permisos actuales de Google.
