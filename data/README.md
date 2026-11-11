# Datos operativos privados

Las colecciones JSON son locales y no se versionan. No copiar cuentas, actividad,
sesiones, tokens ni el catálogo operativo a Git. La retirada del seguimiento no
borra los archivos de las instalaciones existentes.

Las pruebas generan sus propias cuentas y catálogos ficticios con tools/qa.py.
Para una instalación real, preparar los descriptores y restaurar los datos privados
mediante el procedimiento de recuperación aprobado. No reutilizar claves de ejemplo.
