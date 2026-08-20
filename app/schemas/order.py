from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class OrderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    fecha_pedido: str
    region: str
    tipo_envio: str
    distancia_km: float
    tiempo_estimado_dias: int
    tiempo_preparacion_horas: float
    cantidad_productos: int
    peso_kg: float
    prioridad: str
    dia_semana: str
    carga_logistica: str
    entrega_tardia: int

class OrderPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[OrderSchema]