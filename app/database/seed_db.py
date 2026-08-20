import os
import pandas as pd
from app.database.connection import engine, Base, SessionLocal
from app.models.order import Order
from app.models.prediction_log import PredictionLog

def inicializar_y_poblar_bd():
    print(" Creando tablas en SQLite...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        conteo_actual = db.query(Order).count()
        if conteo_actual > 0:
            print(f"ℹ️ La base de datos ya contiene {conteo_actual} registros. Omitiendo importación.")
            return

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(BASE_DIR, "ml", "data", "pedidos.csv")
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encontró el dataset en: {csv_path}. Ejecuta primero ml/training/generate_dataset.py")

        print(f"📥 Cargando datos desde {csv_path}...")
        df = pd.read_csv(csv_path)

        pedidos = [
            Order(
                order_id=row['order_id'],
                fecha_pedido=str(row['fecha_pedido']),
                region=row['region'],
                tipo_envio=row['tipo_envio'],
                distancia_km=float(row['distancia_km']),
                tiempo_estimado_dias=int(row['tiempo_estimado_dias']),
                tiempo_preparacion_horas=float(row['tiempo_preparacion_horas']),
                cantidad_productos=int(row['cantidad_productos']),
                peso_kg=float(row['peso_kg']),
                prioridad=row['prioridad'],
                dia_semana=row['dia_semana'],
                carga_logistica=row['carga_logistica'],
                entrega_tardia=int(row['entrega_tardia'])
            )
            for _, row in df.iterrows()
        ]

        db.bulk_save_objects(pedidos)
        db.commit()
        print(f" Base de datos poblada exitosamente con {len(pedidos)} pedidos.")
    except Exception as e:
        db.rollback()
        print(f" Error durante la inicialización de la BD: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    inicializar_y_poblar_bd()