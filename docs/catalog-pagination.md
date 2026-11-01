# Conservacion de pagina al actualizar visualizacion

## Solicitud
Mantener la pagina del catalogo al cambiar el estado de visualizacion de una tarjeta.

## Implementacion
`js/catalogo.js`: `applyCurrentFilters` acepta `preservePage`, desactivado por defecto. El cambio de estado activa esta opcion cuando hay filtros de visualizacion. Cambiar los filtros sigue comenzando en la pagina 1.

`renderCatalogPage` limita la pagina al rango disponible. Si desaparece la ultima pagina al excluir una tarjeta, se muestra la ultima pagina valida. La URL recibe la pagina resultante.

`Html/catalogo.html`: se incrementa la version del JavaScript para solicitar el archivo actualizado al navegador.

## Alcance
Mismo ajuste en Desarrollo/Aplication y ProyectoFinal/Aplication. Sin cambios de iconos ni estilos. No se modifican datos del catalogo.

## Verificacion
Sintaxis JavaScript y funciones reales de filtrado y paginacion con datos aislados: conservar pagina 2, retroceder cuando desaparece la ultima pagina, manejar cero resultados y reiniciar al aplicar otro filtro.
La comprobacion aislada no sustituye una prueba interactiva con la sesion del usuario.
