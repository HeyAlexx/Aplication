# Auditoria funcional de Altoidss

Fecha de revision: 24 de agosto de 2026

## 1. Alcance de la auditoria

La revision cubrio los flujos definidos en `docs/alcance_final.md` sin modificar la implementacion. Se probaron las paginas publicas, autenticacion, permisos, catalogo, favoritos, vistos, noticias, Dashboard y rutas principales de la API PHP.

## 2. Resumen

| Area | Estado | Resultado |
|---|---|---|
| Pagina de inicio | Correcto | Carrusel, noticias, enlaces e imagenes cargan sin errores visibles. |
| Navegacion | Correcto | Las paginas principales y categorias conservan rutas independientes. |
| Catalogo local | Correcto | Peliculas, series y anime cargan desde sus archivos JSON. |
| Filtros | Correcto | Busqueda, inicial, genero, tipo, temporadas, estado y anos responden. |
| Modos del catalogo | Correcto | Funcionan tarjetas, lista y seleccion de 3, 5 o 7 columnas. |
| Paginacion | Correcto | Se genera segun la cantidad de resultados. |
| Favoritos | Correcto | El cambio se guarda, aparece en Mi lista y puede revertirse. |
| Estado visto | Correcto | Se guarda y actualiza el icono y la etiqueta de la tarjeta. |
| Vistas de Mi lista | Correcto | Tarjetas, detallada y sencilla aplican clases visuales distintas. |
| Login de usuario | Correcto | La cuenta de prueba inicia sesion y abre el Dashboard. |
| Login de administrador | Correcto | La cuenta de prueba habilita las herramientas administrativas. |
| Cierre de sesion | Correcto | Regresa al inicio como visitante sin errores del Dashboard. |
| Registro | Correcto | Se creo una cuenta temporal, se confirmo su sesion y Dashboard, y se restauraron los datos originales. |
| Permisos | Correcto | Un usuario normal recibe HTTP 403 al intentar crear contenido. |
| CRUD | Correcto | Se probaron crear, actualizar y ocultar contenido y noticias; luego se restauraron los JSON originales. |
| Noticias | Correcto | La API y la pagina muestran cuatro publicaciones. |
| Busqueda externa | Correcto con respaldo | Watchmode, Jikan, AniList y Kitsu estan integrados; si un proveedor falla, el catalogo JSON permanece disponible. |
| Responsive | Correcto | Las seis paginas principales fueron verificadas a 320, 390, 768 y 1024 px sin desplazamiento horizontal. |

## 3. Evidencia de datos y API

- Salud de API: HTTP 200.
- PHP: version 8.2.12.
- Almacenamiento: JSON con permisos de escritura.
- Peliculas visibles: 12.
- Series visibles: 10.
- Anime visible: 738.
- Noticias visibles: 4.
- Login invalido: HTTP 401.
- Creacion de contenido como usuario: HTTP 403.
- Registro con correo duplicado: HTTP 409.
- Contenido invalido como administrador: HTTP 400.
- Logout de API: HTTP 200 y sesion de visitante confirmada.

## 4. Hallazgos que requieren correccion

### AF-01 - Error de JavaScript en Dashboard

Se ejecuta `syncActiveProfileButton()` desde el evento `altoidss-auth-change`, pero la funcion no existe. El error aparece al iniciar o cerrar sesion y al sincronizar el perfil.

Impacto: el flujo principal continua, pero quedan errores visibles en la consola y puede interrumpirse trabajo posterior dentro del mismo evento.

Prioridad: alta.

### AF-02 - Proveedores externos no disponibles

Las consultas de peliculas, series y anime devolvieron HTTP 502 con el mensaje `cURL 7`. El frontend conserva el catalogo local, por lo que la pagina no queda vacia.

Impacto: la busqueda local funciona, pero durante la presentacion no se puede garantizar la consulta de titulos externos.

Prioridad: alta.

### AF-03 - Metricas administrativas inconsistentes

El Dashboard administrativo muestra 12 peliculas, 10 series y 738 animes como vistos, mientras el grafico de progreso indica 0% visto.

Impacto: los numeros pueden resultar contradictorios durante la exposicion.

Prioridad: alta.

### AF-04 - Textos de etapa temporal desactualizados

El Dashboard todavia contiene expresiones como `CRUD temporal`, `antes de conectar PHP y MySQL` y `se retirara cuando exista backend final`. PHP y la persistencia JSON ya forman parte de la solucion final.

Impacto: la interfaz no representa el estado real del proyecto.

Prioridad: media.

### AF-05 - Validacion HTML de acceso mejorable

Los campos de login y registro dependen de la validacion JavaScript y del backend. No contienen atributos HTML como `required` o longitudes minimas.

Impacto: el backend protege los datos, pero se pierde una capa de ayuda inmediata para el usuario.

Prioridad: media.

### AF-06 - Registros de anime sin imagen

Los siete registros detectados recibieron imagen, enlace de fuente y metadatos mediante consultas controladas a AniList o Kitsu.

Impacto posterior: el archivo `anime.json` no contiene registros con imagen vacia.

Prioridad: media.

## 5. Observaciones positivas

- No se detecto desplazamiento horizontal en las paginas revisadas en escritorio.
- Las imagenes visibles de Inicio, Noticias y la primera pagina del Catalogo cargaron correctamente.
- La busqueda global abre el Catalogo y conserva el termino en la URL.
- Buscar `Dune` produjo dos resultados locales.
- Favoritos y vistos se reflejan inmediatamente en la interfaz y en el backend.
- Los controles administrativos no aparecen para el usuario normal y la API aplica autorizacion adicional.
- El cierre de sesion devuelve al visitante a la pagina inicial.
- Los archivos PHP y JavaScript no presentan errores de sintaxis.

## 6. Recomendacion para el siguiente cambio

Antes de agregar multimedia o modificar el diseno, conviene realizar una reparacion funcional corta con este orden:

1. Eliminar la llamada inexistente del Dashboard o implementar su comportamiento correcto.
2. Corregir el calculo de metricas administrativas.
3. Diagnosticar la conexion cURL de los proveedores externos y conservar el respaldo JSON.
4. Actualizar los textos temporales del Dashboard.
5. Agregar validacion HTML basica a login y registro.

Estas correcciones requieren aprobacion antes de modificar el codigo.

## 7. Estado de las correcciones aprobadas

| Hallazgo | Estado posterior | Verificacion |
|---|---|---|
| AF-01 | Corregido | Se elimino la llamada inexistente y se probaron login y logout sin errores de consola. |
| AF-02 | Diagnosticado y reforzado | La computadora alcanza los proveedores externos; el bloqueo observado provenia del servidor ejecutado en el entorno restringido. Se conservaron el respaldo JSON y los encabezados seguros de las solicitudes. |
| AF-03 | Corregido | Las metricas administrativas usan el historial real del perfil y el porcentaje evita mostrar 0% cuando existe actividad. |
| AF-04 | Corregido | El Dashboard describe PHP y JSON como arquitectura vigente, sin referencias a una futura migracion a MySQL. |
| AF-05 | Corregido | Login y registro incluyen campos obligatorios, autocompletado y longitud minima de contrasena. |
| AF-06 | Corregido | Los siete registros pendientes tienen imagen y fuente; la comprobacion final encontro cero URL vacias. |
| AF-07 | Corregido | La lista detallada mejora el espaciado, limita descripciones extensas y ofrece `Ver mas` para abrir el detalle enfocado en Catalogo. |
| AF-08 | Corregido | Los filtros rapidos de Mi lista clasifican favoritos por peliculas, series y anime. |
| AF-09 | Corregido | El Dashboard solicita un resumen actualizado al backend y muestra 22 favoritos: 9 peliculas, 7 series y 6 animes para el perfil administrador auditado. |

## 8. Paso 4 - Compatibilidad responsive

Se verificaron Inicio, Catalogo, Mi lista, Noticias, Dashboard y Login en anchos de 320, 390, 768 y 1024 pixeles.

- No se detecto desplazamiento horizontal en las paginas revisadas.
- La navegacion principal se convierte en menu plegable por debajo de 1200 pixeles.
- El sidebar permanece unicamente en Catalogo.
- Los filtros del Catalogo se presentan plegados en movil y se cierran automaticamente despues de aplicarlos.
- Catalogo y Favoritos distribuyen sus tarjetas en dos columnas para telefono y tres para tablet pequena.
- Login, Dashboard, Noticias y los modos detallado y sencillo de Mi lista mantienen una sola columna legible en movil.
- Se agrego `tests/responsive-harness.html` para repetir las comprobaciones con anchos controlados.

## 9. Paso 5 - Cierre funcional y de datos

- El Dashboard vuelve a consultar sus metricas al abrirse, recuperar el foco o cambiar la sesion.
- Las tarjetas superiores conservan el conteo de contenido visto y el grafico de coleccion distribuye los favoritos por peliculas, series y anime.
- Se completo la metadata visual de los siete animes pendientes mediante un proceso por lotes con respaldo automatico.
- El registro se verifico creando una cuenta temporal autenticada y consultando su Dashboard.
- El CRUD se verifico creando, actualizando y ocultando un contenido y una noticia.
- Las pruebas de registro y CRUD fueron reversibles; los JSON originales se restauraron y no conservan registros temporales.

## 10. Paso 6 - Multimedia editorial

- La sección Noticias incorpora tráileres oficiales como parte del detalle de cada publicación.
- Las cuadrículas conservan imágenes ligeras y un indicador de video; el reproductor solo se carga al abrir la noticia.
- El detalle utiliza un reproductor adaptable de YouTube con enlace alternativo a la fuente oficial.
- El CRUD de noticias permite guardar y editar la URL del tráiler, mientras PHP valida el proveedor antes de persistirla en JSON.

## 11. Paso 7 - Coherencia documental

- El README principal establece PHP 8.2 y JSON como arquitectura final portable.
- La documentación de la API describe en presente las integraciones externas ya implementadas.
- El alcance final registra los tráileres como funcionalidad completada.
- Se sustituyó el diagrama temporal basado en `localStorage` por el modelo real de persistencia PHP y JSON.
- Los textos de respaldo en Inicio y Noticias ya no anuncian una futura conexión con MySQL.
