# Relación entre pedidos y predicciones

`orders.order_id` identifica el pedido histórico. `prediction_logs.order_id`
es una clave foránea opcional que permite guardar varias simulaciones de un
mismo pedido. Las simulaciones manuales y los registros anteriores conservan
`order_id = NULL`.

La asociación es una referencia: las características ingresadas en el formulario
se guardan como una instantánea de la simulación. No se copian automáticamente
del pedido ni se modifica el historial.

## Integridad y migración

- SQLite activa `PRAGMA foreign_keys = ON` en cada conexión de la aplicación.
- La FK aplica `ON DELETE SET NULL`: eliminar o sustituir pedidos durante una
  sincronización conserva las predicciones y sus características originales.
- `app/database/migrations.py` añade la columna y el índice cuando faltan.
  La inicialización ejecuta esta migración antes de sincronizar el dataset.
- Una columna existente sin la FK esperada produce un error explícito para
  evitar continuar con un esquema incompatible.

## Contrato de predicción

`POST /api/predict` admite `order_id` como cadena opcional de hasta 20 caracteres.
Un valor vacío se interpreta como una simulación sin pedido asociado. Un código
inexistente devuelve HTTP 404 antes de ejecutar el modelo. La respuesta incluye
`prediction_id` y `order_id`, además de los resultados anteriores.

El formulario permite ingresar el código opcional y muestra la vinculación en
el resultado. El código no es una variable predictora del modelo de aprendizaje
automático.

## Tablas auxiliares y archivos

`dataset_state` almacena el hash del CSV importado. Es una tabla técnica sin FK
con las entidades del negocio. El pipeline y sus metadatos permanecen en
archivos; no se añaden tablas de usuarios, productos o modelos que el sistema
todavía no administra.
