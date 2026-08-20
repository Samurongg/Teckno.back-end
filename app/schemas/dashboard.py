from pydantic import BaseModel
from typing import List, Dict, Any

class KPICards(BaseModel):
    total_pedidos: int
    entregas_a_tiempo: int
    entregas_tardias: int
    tasa_retrasos: float
    predicciones_realizadas: int
    nivel_riesgo_general: str

class MonthlyTrend(BaseModel):
    mes: str
    total: int
    tardios: int

class RegionBreakdown(BaseModel):
    region: str
    total: int
    tardios: int
    tasa_retraso: float

class DashboardResponse(BaseModel):
    kpis: KPICards
    evolucion_mensual: List[MonthlyTrend]
    pedidos_por_region: List[RegionBreakdown]