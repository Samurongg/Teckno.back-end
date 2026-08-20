from sqlalchemy import Column, Integer, String, Float
from app.database.connection import Base

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(20), primary_key=True, index=True)
    fecha_pedido = Column(String(10), index=True, nullable=False)
    region = Column(String(20), nullable=False, index=True)
    tipo_envio = Column(String(20), nullable=False)
    distancia_km = Column(Float, nullable=False)
    tiempo_estimado_dias = Column(Integer, nullable=False)
    tiempo_preparacion_horas = Column(Float, nullable=False)
    cantidad_productos = Column(Integer, nullable=False)
    peso_kg = Column(Float, nullable=False)
    prioridad = Column(String(10), nullable=False)
    dia_semana = Column(String(15), nullable=False)
    carga_logistica = Column(String(10), nullable=False)
    entrega_tardia = Column(Integer, nullable=False)  # 0 = A tiempo, 1 = Tardía