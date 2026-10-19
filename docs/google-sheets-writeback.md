# Actualizar Google Sheets al aprobar una revisión

La importación puede leer la exportación XLSX o la API de Sheets según la configuración. Para devolver aprobaciones o ediciones de animes vinculados se usa OAuth y la API de Google Sheets. Las credenciales y el token permanecen locales y no se publican. Durante la revisión actual, no iniciar sincronización ni autorización nueva: el usuario mantiene en espera los cambios recientes de la hoja.

## Configuración única

1. En Google Cloud, crea o selecciona un proyecto y habilita **Google Sheets API**.
2. En **APIs y servicios > Credenciales**, crea un cliente OAuth de tipo **Aplicación de escritorio** y descarga su JSON.
3. Guarda ese archivo como `config/google-oauth-client.json` dentro de la aplicación. No lo subas ni lo compartas.
4. El bloque `googleSheets` ya está preparado en `config/anime-sync.json`. Solo verifica que el identificador de la hoja y el nombre de la pestaña sean correctos:

```json
"googleSheets": {
  "spreadsheetId": "ID_DE_LA_HOJA_DEL_ENTORNO",
  "sheetName": "Catalogo",
  "writeBackEnabled": false,
  "oauthClientSecrets": "config/google-oauth-client.json",
  "tokenFile": "runtime/anime-sync/google-token.json"
}
```

5. Ejecuta `Autorizar-Google-Sheets.cmd`, o desde la carpeta `Aplication` ejecuta:

```powershell
python tools/google_sheets_writeback.py --authorize
```

Se abrirá Google en el navegador. Inicia sesión con una cuenta que tenga permiso de edición sobre la hoja y acepta el permiso solicitado. Al completarse, Altoidss activa automáticamente `writeBackEnabled`.

## Funcionamiento

Al aprobar/guardar una revisión o editar campos compartidos de un anime vinculado, Altoidss actualiza catálogo y cola bajo una transacción recuperable. El monitor resuelve la fila actual por código único y devuelve los diez campos compartidos antes de la siguiente importación. Retira esa versión solo después de la confirmación de Google y una lectura de los mismos valores; una versión posterior encolada se conserva. Si no hay red o autorización, la cola permanece para reintentarla. Crear contenido local desde la página no agrega filas a Sheets. No confundir «Pendiente» con recepción por Google.
