from pydantic import BaseModel
from typing import List, Dict, Any

class CategoryDelayRate(BaseModel):
    categoria: str
    total_pedidos: int
    entregas_tardias: int
    tasa_retraso: float

class AnalyticsResponse(BaseModel):
    por_region: List[CategoryDelayRate]
    por_tipo_envio: List[CategoryDelayRate]
    por_carga_logistica: List[CategoryDelayRate]
    por_prioridad: List[CategoryDelayRate]
    distribucion_distancias: List[Dict[str, Any]]