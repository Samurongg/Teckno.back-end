from pydantic import BaseModel, Field
from typing import Literal

class PredictionInput(BaseModel):
    region: Literal['Centro', 'Norte', 'Sur', 'Este', 'Oeste']
    tipo_envio: Literal['Estándar', 'Express', 'Mismo Día']
    distancia_km: float = Field(..., gt=0, le=1000, description="Distancia en kilómetros")
    tiempo_estimado_dias: int = Field(..., ge=1, le=15, description="Días prometidos al cliente")
    tiempo_preparacion_horas: float = Field(..., ge=0.1, le=72, description="Horas de empaque")
    cantidad_productos: int = Field(..., ge=1, le=50, description="Cantidad de ítems")
    peso_kg: float = Field(..., ge=0.1, le=100, description="Peso del paquete")
    prioridad: Literal['Baja', 'Media', 'Alta']
    dia_semana: Literal['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    carga_logistica: Literal['Baja', 'Media', 'Alta']

class PredictionResponse(BaseModel):
    prediccion: int  # 0 = A tiempo, 1 = Tardía
    resultado: str  # "A Tiempo" o "Entrega Tardía"
    probabilidad_retraso: float  # Porcentaje (ej. 78.45)
    nivel_riesgo: str  # "BAJO", "MEDIO", "ALTO"