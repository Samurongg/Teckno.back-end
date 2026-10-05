from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order_id = Column(
        String(20),
        ForeignKey(
            "orders.order_id",
            name="fk_prediction_logs_order_id_orders",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    region = Column(String(20), nullable=False)
    departamento_destino = Column(String(30), nullable=True)
    zona_logistica = Column(String(30), nullable=True)
    modo_transporte = Column(String(20), nullable=True)
    tipo_envio = Column(String(20), nullable=False)
    distancia_km = Column(Float, nullable=False)
    tiempo_estimado_dias = Column(Integer, nullable=False)
    tiempo_preparacion_horas = Column(Float, nullable=False)
    cantidad_productos = Column(Integer, nullable=False)
    peso_kg = Column(Float, nullable=False)
    prioridad = Column(String(10), nullable=False)
    dia_semana = Column(String(15), nullable=False)
    carga_logistica = Column(String(10), nullable=False)
    prediccion = Column(Integer, nullable=False)
    probabilidad = Column(Float, nullable=False)
    nivel_riesgo = Column(String(10), nullable=False)

    order = relationship("Order", back_populates="predictions")
