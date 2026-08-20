from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.prediction_log import PredictionLog
from app.schemas.prediction import PredictionInput, PredictionResponse
from app.services.ml_service import ml_service

router = APIRouter(prefix="/api/predict", tags=["Prediction"])

@router.post("", response_model=PredictionResponse)
def predecir_entrega(datos: PredictionInput, db: Session = Depends(get_db)):
    resultado = ml_service.predecir_retraso(datos)

    # Persistencia de log de auditoría
    log = PredictionLog(
        region=datos.region,
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
    db.commit()

    return resultado