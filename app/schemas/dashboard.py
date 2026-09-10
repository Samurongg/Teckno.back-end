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

class DepartmentBreakdown(BaseModel):
    departamento: str
    total: int
    tardios: int
    tasa_retraso: float

class ZoneBreakdown(BaseModel):
    zona: str
    total: int
    tardios: int
    tasa_retraso: float

class ShippingBreakdown(BaseModel):
    tipo: str
    tasa_retraso: float

class DashboardResponse(BaseModel):
    kpis: KPICards
    evolucion_mensual: List[MonthlyTrend]
    pedidos_por_departamento: List[DepartmentBreakdown]
    pedidos_por_zona: List[ZoneBreakdown]
    pedidos_por_tipo_envio: List[ShippingBreakdown]
