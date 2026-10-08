# Altoidss

Altoidss nació como un proyecto universitario de Programación Internet. Desde entonces se ha ido transformando en una aplicación para organizar un catálogo audiovisual personal, con herramientas de administración, revisión de información y sincronización de anime. Su origen académico forma parte de su historia; hoy su desarrollo se centra en mejorar la aplicación y ampliar sus posibilidades de uso.

## ¿Qué es Altoidss?

Una aplicación web para consultar y administrar películas, series y anime, mantener una lista personal y registrar el estado de visualización. Funciona con PHP y archivos JSON, sin requerir MySQL. El catálogo de anime puede alimentarse desde Google Sheets o Excel y contrastarse con proveedores externos de metadatos.

Altoidss es un gestor de catálogo: no incluye un servicio de streaming ni descarga de episodios.

## Funciones

- Catálogo de películas, series y anime con búsqueda, filtros y fichas de detalle.
- Registro e inicio de sesión, perfiles y preferencias de usuario.
- Favoritos / Mi lista y seguimiento del estado de visualización.
- Dashboard con información del catálogo y herramientas según el rol de la cuenta.
- Administración de contenido y noticias; ocultamiento de registros sin eliminarlos físicamente del catálogo.
- Importación de anime desde Google Sheets o un archivo Excel `.xlsx`.
- Sincronización periódica, detección de diferencias y revisión de información antes de aprobar cambios que lo requieran.
- Editor de revisiones para comparar y corregir la versión final de un registro.
- Botón **Obtener datos desde URL** para consultar fuentes compatibles de MyAnimeList, AniList y Kitsu. Si no se encuentran datos compatibles, aparece el aviso **No hay datos compatibles**.
- Consulta de la API oficial de MyAnimeList en las revisiones por URL cuando existe un Client ID configurado, con Jikan como respaldo.
- Envío de correcciones aprobadas a Google Sheets mediante OAuth y una cola local de actualizaciones.
- Persistencia en JSON y respaldos automáticos de las escrituras de la API.

## Instalación y primer inicio

### Requisitos

- PHP 8.2 o superior, con cURL y mbstring para consultas y procesamiento de texto.
- Navegador actualizado y Git si deseas clonar el repositorio.
- Python 3 y `openpyxl` para utilizar la sincronización de anime.
- Acceso a Internet para Google Sheets y proveedores de metadatos.

### Ejecutar localmente

Desde una terminal:

```powershell
git clone https://github.com/HeyAlexx/Aplication.git
cd Aplication
php -S 127.0.0.1:8091 -t . server-router.php
```

Abre [Altoidss local](http://127.0.0.1:8091/Html/index.html) y deja esa terminal abierta mientras uses la aplicación. Si ya tienes una copia, inicia el servidor desde su carpeta `Aplication`; no necesitas clonarlo otra vez.

El servidor debe poder escribir en `data`, `backups` y, para la sincronización, `runtime`. No abras los HTML directamente: sesiones, persistencia y administración requieren el servidor PHP.

El servidor integrado de PHP es para uso local. Una publicación remota requiere un servidor adecuado, HTTPS, protección de archivos privados y control de acceso; no expongas este servidor directamente a Internet.

## Cómo usar la aplicación

1. Registra una cuenta o inicia sesión con una existente.
2. Explora el catálogo, utiliza sus filtros y abre una ficha para consultar sus detalles.
3. Agrega títulos a Mi lista y actualiza su estado de visualización.
4. Usa el Dashboard para consultar tu información y las herramientas disponibles.
5. Si tienes rol de administrador, administra contenido, noticias y revisiones pendientes.

El registro normal crea una cuenta de usuario, no de administrador. Las herramientas administrativas requieren una cuenta cuyo rol ya esté configurado como `admin` en la instalación. No compartas cuentas ni contraseñas de administración.

### Revisar información de anime

1. Entra con una cuenta administradora y abre una revisión pendiente desde el Dashboard.
2. Compara la información de la hoja con la propuesta de los proveedores.
3. Si necesitas otra fuente, agrega una URL compatible de MyAnimeList, AniList o Kitsu en la sección de fuente y pulsa **Obtener datos desde URL**.
4. Revisa los campos cargados y realiza las correcciones necesarias. Obtener datos no equivale a aprobarlos.
5. Guarda la versión final. Si Google Sheets está autorizado para edición, la actualización queda en cola para que el sincronizador la escriba en la hoja.

## Preparar la hoja de anime

La integración de hojas corresponde al catálogo de **anime**, no a películas o series. Puedes elegir Google Sheets o Excel como fuente de trabajo.

### Estructura obligatoria

Crea una pestaña llamada `Catalogo`, sin tilde. Usa la primera fila para encabezados y empieza los registros en la fila 2. Las columnas deben ocupar **A:J en este orden**; el importador interpreta su posición, no el nombre del encabezado.

| Columna | Encabezado sugerido | Contenido |
| --- | --- | --- |
| A | Código | Identificador único y estable. No lo reutilices para otro título. |
| B | Título | Nombre del anime; obligatorio. |
| C | Estado de producción | `Emision`, `Finalizado`, `Pausado`, `Próximamente`, `Cancelado` o `Pendiente`. |
| D | Formato | `Serie`, `Movie` (película), `OVA`, `ONA` o `Especial`. |
| E | Capítulos | Número entero no negativo. |
| F | Temporadas | Número entero no negativo. |
| G | Temporada activa | Código como `S01` o `S02`; para una película puede usarse `S00`. |
| H | Estado de visualización | `Visto`, `No visto`, `Por Ver` o `Ignorado`. |
| I | Año de emisión | Año entero, por ejemplo `2026`, no una fecha completa. |
| J | Trimestre | `1` = invierno, `2` = primavera, `3` = verano, `4` = otoño. |

Ejemplo para pegar en A1 (columnas separadas por tabulaciones; reemplaza la fila de ejemplo por tus datos):

```text
Código	Título	Estado de producción	Formato	Capítulos	Temporadas	Temporada activa	Estado de visualización	Año de emisión	Trimestre
1001	Ejemplo de anime	Finalizado	Serie	12	1	S01	Por Ver	2026	3
```

Mantén los códigos sin duplicados. Si contienen ceros iniciales, configura A como texto antes de escribirlos. Las filas sin código o sin título no se importan. Conserva una copia de seguridad de tu hoja antes de comenzar.

### Opción A: Google Sheets con lectura y edición autorizadas

1. Crea una hoja de cálculo en Google Sheets, por ejemplo **Altoidss - Catalogo**.
2. Renombra su pestaña a `Catalogo` y agrega las columnas y registros anteriores.
3. Copia el identificador de la hoja: el texto situado entre `/d/` y `/edit` en su URL.
4. Desde la carpeta de la aplicación, prepara la configuración local:

```powershell
python -m pip install openpyxl
Copy-Item config/anime-sync.example.json config/anime-sync.json
```

Si `config/anime-sync.json` ya existe, edítalo sin sobrescribir tu configuración. Para Google Sheets, utiliza esta estructura y reemplaza el identificador:

```json
{
  "workbook": "",
  "googleExportUrl": "",
  "googleSheets": {
    "spreadsheetId": "TU_SPREADSHEET_ID",
    "sheetName": "Catalogo",
    "writeBackEnabled": false,
    "oauthClientSecrets": "config/google-oauth-client.json",
    "tokenFile": "runtime/anime-sync/google-token.json"
  }
}
```

5. En Google Cloud, crea o selecciona un proyecto y habilita **Google Sheets API**. Configura la pantalla de consentimiento OAuth; si está en modo de prueba, agrega tu cuenta como usuario de prueba.
6. Crea un cliente OAuth de tipo **Aplicación de escritorio**, descarga su JSON y guárdalo como `config/google-oauth-client.json` dentro de la aplicación.
7. Ejecuta la autorización:

```powershell
python tools/google_sheets_writeback.py --authorize
```

También puedes ejecutar `Autorizar-Google-Sheets.cmd`. En el navegador, inicia sesión con una cuenta que tenga permiso de edición sobre la hoja y acepta el permiso solicitado. Al finalizar, la aplicación activa automáticamente `writeBackEnabled` y guarda el token localmente.

No necesitas publicar la hoja ni habilitar edición para cualquiera con el enlace. OAuth permite trabajar con una hoja privada a la que tu cuenta tenga acceso. Con este modo activo, la fuente se lee mediante la API de Google Sheets.

### Opción B: Excel local

1. Crea un libro con una pestaña `Catalogo` y la estructura A:J anterior.
2. Guarda el libro como `.xlsx`, por ejemplo `C:\Altoidss\Catalogo.xlsx`.
3. Instala `openpyxl` y copia la configuración de ejemplo como en la opción A.
4. En `config/anime-sync.json`, configura la ruta real del archivo:

```json
{
  "workbook": "C:\\Altoidss\\Catalogo.xlsx",
  "googleExportUrl": "",
  "googleSheets": {
    "writeBackEnabled": false
  }
}
```

Guarda los cambios en Excel antes de sincronizar. Actualmente esta opción **solo importa**: las correcciones aprobadas en Altoidss no se escriben automáticamente en el libro. Actualiza también tu Excel si deseas conservarlo como fuente de verdad.

### Iniciar la sincronización

Para ejecutar una importación:

```powershell
python tools/anime_sync_pipeline.py --config config/anime-sync.json --apply
```

Para revisar la fuente cada cinco minutos:

```powershell
python tools/anime_sync_pipeline.py --config config/anime-sync.json --apply --watch --interval 300
```

También puedes usar `iniciar-sincronizacion-anime.cmd`. Mantén el proceso activo; detén la vigilancia con `Ctrl+C`. El servidor web y el sincronizador son procesos separados.

El pipeline consulta AniList, Jikan y Kitsu para contrastar información. Las diferencias que necesitan intervención se revisan desde el Dashboard. La primera ejecución puede tardar más por las consultas a proveedores externos.

Con Google Sheets autorizado, el sincronizador procesa las correcciones aprobadas pendientes antes de la siguiente importación. Si falla la escritura, conserva la cola para reintentarla. **No ordenes, insertes ni elimines filas mientras haya correcciones pendientes de envío**: la escritura actual utiliza el número de fila registrado en la revisión.

Existe además una opción de lectura por exportación XLSX mediante `googleExportUrl`, sin devolución de correcciones. Cuando OAuth está desactivado, una URL de exportación no vacía tiene prioridad sobre `workbook`; déjala vacía para usar Excel local. Compartir un enlace con permiso de edición no sustituye OAuth.

## Configurar MyAnimeList

Para usar la API oficial en el botón de consulta por URL, registra una aplicación en [MyAnimeList API](https://myanimelist.net/apiconfig) y guarda **solo el Client ID** en `api/config/mal-client-id.local.txt`. También puedes utilizar la variable de entorno `MAL_CLIENT_ID`.

Las consultas públicas de metadatos de esta integración no requieren Client Secret ni autorización de listas personales. No se modifica tu lista de MyAnimeList. Este ajuste corresponde al editor de revisiones por URL; el pipeline Python conserva sus propios proveedores.

Consulta detalles y comandos de comprobación en [MyAnimeList API oficial](docs/myanimelist-api.md).

## Datos y seguridad

- El frontend consume la API PHP de `api/index.php`; los registros se almacenan en `data`.
- La API utiliza bloqueo de archivos y crea respaldos en `backups`; las sesiones se guardan en `backups/sessions`.
- La sincronización conserva estado e información de revisión en `runtime/anime-sync`.
- El router local restringe el acceso web a archivos internos y datos privados. Conserva estas protecciones al cambiar de servidor.
- No publiques credenciales OAuth, tokens, contraseñas ni copias de datos personales. Los archivos de configuración local y tokens previstos están excluidos de Git.
- Antes de actualizar o migrar, respalda los datos y la configuración local. Clonar el repositorio no sustituye una copia de seguridad de tu catálogo.

## Solución de problemas

- **`getaddrinfo failed` o error al descargar la hoja:** indica un problema al resolver el servidor remoto. Revisa conexión, DNS y acceso a Google desde la computadora que ejecuta el sincronizador.
- **La aprobación no aparece en Google Sheets:** confirma autorización, identificador, pestaña, permiso de edición y que el sincronizador esté activo para procesar la cola.
- **Vuelven a aparecer diferencias:** verifica que la fuente contenga la versión aprobada; con Excel hay que actualizarla manualmente. No borres el estado del sincronizador como primer intento de solución.
- **No hay datos compatibles desde una URL:** comprueba que sea una ficha de anime de un proveedor admitido. Un proveedor también puede estar temporalmente indisponible.
- **La aplicación no guarda cambios:** usa el servidor PHP, inicia sesión y comprueba permisos de escritura en datos y respaldos.

## Evolución de la aplicación

La planificación de próximas mejoras estará en [ROADMAP.md](ROADMAP.md). Es un borrador editable para definir prioridades, alcance y criterios de finalización; no representa fechas ni funciones prometidas.

La versión de desarrollo se identifica en `VERSION` y el historial en [CHANGELOG.md](CHANGELOG.md). Cada cambio se prepara en una rama independiente y se revisa antes de llegar a `main`, siguiendo [CONTRIBUTING.md](CONTRIBUTING.md). La integración del código no equivale a su despliegue; las protecciones remotas y la separación de instalaciones deben configurarse según esa guía.
