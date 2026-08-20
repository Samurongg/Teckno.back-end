from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.analytics import AnalyticsResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("", response_model=AnalyticsResponse)
def obtener_analitica(db: Session = Depends(get_db)):
    return DashboardService.obtener_analitica_avanzada(db)