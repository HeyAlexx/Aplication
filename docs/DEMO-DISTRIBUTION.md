# Distribución nueva de demostración — AL-15

La entrega histórica se conserva intacta. Esta herramienta crea otro paquete desde
un commit revisado; no cambia producción ni convierte la entrega antigua en segura.
El servidor soportado y probado es el PHP integrado con el router incluido.

## Construcción y prueba

Desde un checkout saneado y con los cambios ya comprometidos en Git:

```text
python -B tools/prepare_demo_distribution.py build --output RUTA_NUEVA_FUERA_DEL_CHECKOUT
python -B tools/prepare_demo_distribution.py smoke --archive RUTA/demo.zip --php RUTA_A_PHP
```

El constructor verifica la higiene del commit y exporta sus blobs con la lista
permitida existente. Ignora datos y código suelto del árbol de trabajo. Rechaza
repositorios con datos operativos versionados y salidas ya existentes; nunca copia
todo un checkout ni sobrescribe una entrega. `demo.zip` y `demo-distribution.json`
identifican el SHA y las huellas. Los ZIP usan inventario ordenado y fecha fija.

La aplicación incluida mantiene su código y recibe el catálogo ficticio de QA:
90 anime, 12 películas, 12 series y dos noticias. Usuarios, perfiles, configuración,
favoritos e historial empiezan vacíos. No se generan administradores, contraseñas
conocidas, OAuth, tokens, sesiones, respaldo operativo ni dependencias instaladas.
La actividad posterior se crea localmente en esa demostración.

El smoke extrae el mismo ZIP en una carpeta temporal, verifica rutas/CRC/hashes y
prueba recursos, doce rutas privadas/variantes, registro, login y logout reales con
una contraseña aleatoria efímera. Cierra PHP y elimina su extracción propia. No
consulta proveedores externos ni modifica archivos de otro entorno.

## Uso del ZIP

Extraer todo junto. Requiere Python 3.13 y uno de los PHP del perfil fijado en
[RUNTIME-AND-QA.md](RUNTIME-AND-QA.md). No instala herramientas automáticamente.

```text
Iniciar-Demo.cmd --php "RUTA_A_PHP_EXE" --check
Iniciar-Demo.cmd --php "RUTA_A_PHP_EXE"
```

En otros sistemas: `python3 -B Aplicacion/tools/run_demo.py --php /ruta/a/php`.
Abrir `http://127.0.0.1:8093/Html/index.html`. Ctrl+C detiene solo ese servidor.
`--port` permite otro puerto local. El chequeo no escribe ni inicia el servidor.
Para probar registro use cuentas ficticias con dominio `example.invalid`.

El launcher requiere el marcador del paquete y código igual al manifiesto. Rechaza
enlaces, hardlinks y configuración privada conocida de otros entornos; el marcador
es un control de integridad local, no una firma contra un atacante que cambie todo
el paquete. Regenera el descriptor para las carpetas propias y descarta variables
heredadas de almacenamiento/proveedores. PHP escucha únicamente en 127.0.0.1.

Es HTTP local: la cookie Secure no se activa y no sustituye el perfil HTTPS público.
No inicia Sheets, túneles ni navegador. Las búsquedas externas pueden contactar
proveedores si el usuario las elige; el smoke no las usa. No se certifica Apache:
los .htaccess adicionales solo actúan cuando el servidor los respeta. No publique
la carpeta con otro servidor sin una revisión específica.

## CI y conservación

La matriz Windows/Linux y PHP 8.2/8.4 ejecuta las regresiones del generador/launcher.
Build conserva `demo-SHA` además de `code-SHA` y los cuatro artefactos de QA.
Staging descarga y prueba ambos paquetes sin reconstruirlos. Así hay seis artefactos
por candidato, manteniendo siete jobs. No se publica una cuenta real para facilitar
una demostración ni se sobrescribe el ZIP histórico como parte del proceso.
