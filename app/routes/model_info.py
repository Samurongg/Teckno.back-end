from fastapi import APIRouter, HTTPException
from app.services.training_service import estado_entrenamiento, iniciar_entrenamiento
from app.services.ml_service import ml_service

router = APIRouter(prefix="/api/model", tags=["Model Information"])

@router.get("/info")
def obtener_informacion_modelo():
    return ml_service.obtener_metadatos()


@router.get("/training")
def consultar_entrenamiento():
    return estado_entrenamiento()


@router.post("/training", status_code=202)
def entrenar_modelo():
    try:
        return iniciar_entrenamiento()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
