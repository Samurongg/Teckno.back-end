from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database.connection import Base

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    region = Column(String(20), nullable=False)
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