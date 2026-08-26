# Alcance final del proyecto Altoidss

## 1. Necesidad real

Las personas que consumen peliculas, series de television y anime suelen utilizar distintas plataformas y fuentes de informacion. Esto dificulta mantener en un solo lugar el contenido que desean ver, el que ya vieron y sus titulos favoritos.

Altoidss responde a esta necesidad mediante una aplicacion web que centraliza la consulta, organizacion y administracion de contenido audiovisual.

## 2. Publico objetivo

- Personas interesadas en peliculas, series de television y anime.
- Usuarios que desean organizar sus favoritos y contenidos vistos.
- Administradores responsables de mantener el catalogo y publicar noticias.

## 3. Objetivo general

Desarrollar una aplicacion web funcional que permita consultar y organizar contenido audiovisual, gestionar favoritos e historial de visualizacion y administrar el catalogo y las noticias mediante una interfaz clara, responsive y portable.

## 4. Funcionalidades incluidas

### Acceso publico

- Pagina de inicio con contenido destacado y noticias.
- Navegacion entre las paginas principales.
- Consulta del catalogo de peliculas, series y anime.
- Busqueda de contenido local y mediante proveedores externos.
- Filtros por inicial, genero, tipo, temporadas, estado y rango de anos.
- Vista del catalogo en tarjetas o lista.
- Paginacion y seleccion de cantidad de tarjetas por fila.

### Usuario registrado

- Registro, inicio y cierre de sesion.
- Consulta y edicion del perfil.
- Configuracion de preferencias visuales.
- Agregar y eliminar contenido de favoritos.
- Marcar contenido como visto o no visto.
- Consulta de datos personales y metricas en el Dashboard.

### Administrador

- Acceso a las funciones de usuario registrado.
- Creacion, consulta, actualizacion y ocultamiento logico de contenido.
- Gestion de publicaciones de noticias.
- Consulta de metricas generales en el Dashboard.

### Backend y persistencia

- API desarrollada con PHP 8.2.
- Persistencia portable mediante archivos JSON.
- Sesiones y autorizacion por roles.
- Validacion de solicitudes y proteccion CSRF.
- Bloqueo de archivos y respaldos automaticos.
- Integracion con Watchmode y proveedores especializados de anime.

## 5. Funcionalidades complementarias

- Temporadas y episodios forman parte del modelo preparado para anime y series.
- Su carga detallada es complementaria y no condiciona la demostracion principal.
- Las noticias pueden incorporar trailers oficiales mediante un reproductor adaptable y un enlace a la fuente.

## 6. Funcionalidades fuera del alcance

- Comentarios de usuarios.
- Reproduccion o alojamiento propio de peliculas, series o anime.
- Pagos, suscripciones o comercio electronico.
- Aplicacion movil nativa.
- Persistencia mediante MySQL u otro servidor de base de datos externo.
- Inicio de sesion real con Google o GitHub durante esta entrega.

## 7. Flujo principal de demostracion

1. Consultar la pagina de inicio y las noticias.
2. Registrarse o iniciar sesion.
3. Buscar y filtrar contenido en el catalogo.
4. Abrir el detalle de una pelicula, serie o anime.
5. Agregar el contenido a favoritos y marcarlo como visto.
6. Verificar los cambios en Mi lista y en el Dashboard.
7. Iniciar sesion como administrador.
8. Agregar o actualizar contenido y una noticia.
9. Cerrar sesion y regresar al modo visitante.

## 8. Criterio de finalizacion

El proyecto se considerara listo cuando el flujo principal funcione sin errores en escritorio y movil, la carpeta pueda ejecutarse con Apache y PHP sin instalar MySQL, y la documentacion describa fielmente la implementacion entregada.
