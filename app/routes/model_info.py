from fastapi import APIRouter
from app.services.ml_service import ml_service

router = APIRouter(prefix="/api/model", tags=["Model Information"])

@router.get("/info")
def obtener_informacion_modelo():
    return ml_service.obtener_metadatos()