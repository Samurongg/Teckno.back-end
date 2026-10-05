"""Migraciones incrementales del esquema SQLite, sin reemplazar registros."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def migrar_vinculo_predicciones(motor: Engine) -> None:
    """Permite asociar una simulación a un pedido histórico existente."""
    with motor.begin() as conexion:
        inspector = inspect(conexion)
        columnas = {
            columna["name"] for columna in inspector.get_columns("prediction_logs")
        }
        if "order_id" not in columnas:
            # El valor inicial NULL conserva las simulaciones anteriores sin
            # inventar una correspondencia con pedidos del dataset.
            conexion.execute(
                text(
                    "ALTER TABLE prediction_logs ADD COLUMN order_id VARCHAR(20) "
                    "CONSTRAINT fk_prediction_logs_order_id_orders "
                    "REFERENCES orders(order_id) ON DELETE SET NULL"
                )
            )
        # PRAGMA refleja también ON DELETE en claves añadidas con ALTER TABLE;
        # el inspector genérico puede omitir esa opción en restricciones inline.
        claves = conexion.exec_driver_sql(
            "PRAGMA foreign_key_list(prediction_logs)"
        ).mappings().all()
        vinculo_valido = any(
            clave["from"] == "order_id"
            and clave["table"] == "orders"
            and clave["to"] == "order_id"
            and clave["on_delete"].upper() == "SET NULL"
            for clave in claves
        )
        if not vinculo_valido:
            raise RuntimeError(
                "prediction_logs.order_id ya existe sin la FK esperada. "
                "Revisa el esquema antes de continuar; no se han reemplazado datos."
            )

        conexion.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_prediction_logs_order_id "
                "ON prediction_logs (order_id)"
            )
        )
