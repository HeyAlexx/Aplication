# Actualizar Google Sheets al aprobar una revisión

La importación usa la exportación XLSX de Google Sheets para leer la hoja. Para devolver una aprobación a la misma fila se usa OAuth y la API de Google Sheets. Las credenciales y el token permanecen locales y no se publican.

## Configuración única

1. En Google Cloud, crea o selecciona un proyecto y habilita **Google Sheets API**.
2. En **APIs y servicios > Credenciales**, crea un cliente OAuth de tipo **Aplicación de escritorio** y descarga su JSON.
3. Guarda ese archivo como `config/google-oauth-client.json` dentro de la aplicación. No lo subas ni lo compartas.
4. El bloque `googleSheets` ya está preparado en `config/anime-sync.json`. Solo verifica que el identificador de la hoja y el nombre de la pestaña sean correctos:

```json
"googleSheets": {
  "spreadsheetId": "1Hr-moj6tbq_LoNdas8RL4HziC631kjN65mKMwlKH9sM",
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

Al aprobar o guardar una revisión desde el Dashboard, Altoidss deja una actualización en una cola local. El monitor la escribe en la fila correspondiente de `Catalogo` antes de la siguiente importación y elimina la cola solo cuando Google confirma la escritura. Si no hay red o la autorización falla, la cola se conserva para reintentarla.
