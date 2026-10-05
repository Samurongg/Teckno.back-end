from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.prediction_log import PredictionLog
from app.models.order import Order
from app.schemas.prediction import PredictionInput, PredictionResponse
from app.services.ml_service import ml_service

router = APIRouter(prefix="/api/predict", tags=["Prediction"])

@router.post("", response_model=PredictionResponse)
def predecir_entrega(datos: PredictionInput, db: Session = Depends(get_db)):
    if datos.order_id is not None and db.get(Order, datos.order_id) is None:
        raise HTTPException(
            status_code=404,
            detail="El pedido de referencia no existe en el historial.",
        )

    resultado = ml_service.predecir_retraso(datos)

    # Persistencia de log de auditoría
    log = PredictionLog(
        order_id=datos.order_id,
        region=resultado["zona_logistica"],
        departamento_destino=datos.departamento_destino,
        zona_logistica=resultado["zona_logistica"],
        modo_transporte=datos.modo_transporte,
        tipo_envio=datos.tipo_envio,
        distancia_km=datos.distancia_km,
        tiempo_estimado_dias=datos.tiempo_estimado_dias,
        tiempo_preparacion_horas=datos.tiempo_preparacion_horas,
        cantidad_productos=datos.cantidad_productos,
        peso_kg=datos.peso_kg,
        prioridad=datos.prioridad,
        dia_semana=datos.dia_semana,
        carga_logistica=datos.carga_logistica,
        prediccion=resultado["prediccion"],
        probabilidad=resultado["probabilidad_retraso"],
        nivel_riesgo=resultado["nivel_riesgo"]
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo guardar la predicción. Revisa el pedido de referencia.",
        ) from exc
    db.refresh(log)

    return {**resultado, "prediction_id": log.id, "order_id": log.order_id}
