import hashlib
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text

from app.database.connection import Base, SessionLocal, engine
from app.models.order import Order
from app.models.prediction_log import PredictionLog


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
RUTA_DATASET = RAIZ_PROYECTO / "ml" / "data" / "pedidos.csv"
COLUMNAS_GEOGRAFICAS = {
    "departamento_destino",
    "zona_logistica",
    "modo_transporte",
}


def _migrar_esquema_geografico() -> None:
    inspector = inspect(engine)
    tablas = set(inspector.get_table_names())

    if "orders" in tablas:
        columnas_orders = {
            columna["name"] for columna in inspector.get_columns("orders")
        }
        if not COLUMNAS_GEOGRAFICAS.issubset(columnas_orders):
            print("Actualizando la tabla de pedidos al esquema geográfico nacional...")
            Order.__table__.drop(bind=engine, checkfirst=True)

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    columnas_logs = {
        columna["name"] for columna in inspector.get_columns("prediction_logs")
    }
    columnas_faltantes = COLUMNAS_GEOGRAFICAS - columnas_logs
    tipos_columnas = {
        "departamento_destino": "VARCHAR(30)",
        "zona_logistica": "VARCHAR(30)",
        "modo_transporte": "VARCHAR(20)",
    }
    if columnas_faltantes:
        with engine.begin() as conexion:
            for columna in sorted(columnas_faltantes):
                conexion.execute(
                    text(
                        f"ALTER TABLE prediction_logs ADD COLUMN {columna} "
                        f"{tipos_columnas[columna]}"
                    )
                )

    with engine.begin() as conexion:
        conexion.execute(
            text(
                "CREATE TABLE IF NOT EXISTS dataset_state ("
                "id INTEGER PRIMARY KEY, dataset_sha256 VARCHAR(64) NOT NULL)"
            )
        )


def _hash_dataset() -> str:
    return hashlib.sha256(RUTA_DATASET.read_bytes()).hexdigest()


def inicializar_y_poblar_bd() -> None:
    print("Preparando las tablas de SQLite...")
    _migrar_esquema_geografico()

    if not RUTA_DATASET.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset en: {RUTA_DATASET}. "
            "Ejecuta primero ml/training/generate_dataset.py"
        )

    hash_actual = _hash_dataset()
    db = SessionLocal()
    try:
        hash_importado = db.execute(
            text("SELECT dataset_sha256 FROM dataset_state WHERE id = 1")
        ).scalar_one_or_none()
        conteo_actual = db.query(Order).count()

        if hash_importado == hash_actual and conteo_actual > 0:
            print(
                f"La base contiene {conteo_actual} pedidos del dataset vigente."
            )
            return

        print(f"Sincronizando pedidos desde {RUTA_DATASET}...")
        df = pd.read_csv(RUTA_DATASET)
        faltantes = COLUMNAS_GEOGRAFICAS - set(df.columns)
        if faltantes:
            raise ValueError(
                f"El dataset no contiene las columnas geográficas: {sorted(faltantes)}"
            )

        db.query(Order).delete(synchronize_session=False)
        pedidos = [
            Order(
                order_id=row["order_id"],
                fecha_pedido=str(row["fecha_pedido"]),
                region=row["zona_logistica"],
                departamento_destino=row["departamento_destino"],
                zona_logistica=row["zona_logistica"],
                modo_transporte=row["modo_transporte"],
                tipo_envio=row["tipo_envio"],
                distancia_km=float(row["distancia_km"]),
                tiempo_estimado_dias=int(row["tiempo_estimado_dias"]),
                tiempo_preparacion_horas=float(
                    row["tiempo_preparacion_horas"]
                ),
                cantidad_productos=int(row["cantidad_productos"]),
                peso_kg=float(row["peso_kg"]),
                prioridad=row["prioridad"],
                dia_semana=row["dia_semana"],
                carga_logistica=row["carga_logistica"],
                entrega_tardia=int(row["entrega_tardia"]),
            )
            for _, row in df.iterrows()
        ]
        db.bulk_save_objects(pedidos)
        db.execute(
            text(
                "INSERT INTO dataset_state (id, dataset_sha256) VALUES (1, :hash) "
                "ON CONFLICT(id) DO UPDATE SET dataset_sha256 = excluded.dataset_sha256"
            ),
            {"hash": hash_actual},
        )
        db.commit()
        print(f"Base de datos sincronizada con {len(pedidos)} pedidos.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    inicializar_y_poblar_bd()
