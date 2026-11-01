# Identidad visual del sitio

## Cambio aprobado
Sustituir las letras AL del encabezado por el logo existente de Altoidss y establecer el icono de pestana. Referencia visual: work/ui-proposals/altoidss-brand-preview/preview.svg, en la raiz del proyecto.

## Recursos
- img/Altoidss.png: logo transparente original, sin transformar.
- img/Altoidss.ico: icono existente, sin transformar.

## Integracion
Las seis paginas de Html declaran el icono de pestana y muestran el PNG junto al nombre Altoidss. El texto alternativo queda vacio porque el nombre ya forma parte del enlace.
La regla .brand-mark.brand-logo en css/site-shared.css elimina el fondo y el redondeo del distintivo anterior; ajusta la imagen dentro de las medidas existentes (34 px y 30 px en pantallas pequenas).
La version del CSS compartido pasa a 10; los nuevos recursos tienen version 1 para su cache.

## Alcance y comprobacion
Aplicado en desarrollo y en la aplicacion del lanzador. No modifica datos, navegacion ni servicios.
Verificacion estructural de las doce paginas, referencias locales, igualdad binaria de los recursos con los originales y reglas de dimension responsiva. Esta verificacion no confirma el refresco de cache de una sesion de navegador ya abierta.
