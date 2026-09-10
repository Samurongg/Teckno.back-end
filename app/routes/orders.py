from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
import math

from app.database.connection import get_db
from app.models.order import Order
from app.schemas.order import OrderSchema, OrderPaginatedResponse

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.get("", response_model=OrderPaginatedResponse)
def listar_pedidos(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=10000),
    search: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    departamento_destino: Optional[str] = Query(None),
    zona_logistica: Optional[str] = Query(None),
    tipo_envio: Optional[str] = Query(None),
    entrega_tardia: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Order)

    if search:
        patron = f"%{search}%"
        query = query.filter(
            or_(
                Order.order_id.ilike(patron),
                Order.departamento_destino.ilike(patron),
                Order.zona_logistica.ilike(patron),
            )
        )
    if region:
        query = query.filter(
            or_(
                Order.departamento_destino == region,
                Order.zona_logistica == region,
            )
        )
    if departamento_destino:
        query = query.filter(Order.departamento_destino == departamento_destino)
    if zona_logistica:
        query = query.filter(Order.zona_logistica == zona_logistica)
    if tipo_envio:
        query = query.filter(Order.tipo_envio == tipo_envio)
    if entrega_tardia is not None:
        query = query.filter(Order.entrega_tardia == entrega_tardia)

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    orders = query.offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "data": orders
    }

@router.get("/{order_id}", response_model=OrderSchema)
def obtener_pedido_por_id(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} no encontrado")
    return order
