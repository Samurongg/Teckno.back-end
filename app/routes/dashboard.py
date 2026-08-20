from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("", response_model=DashboardResponse)
def obtener_dashboard(db: Session = Depends(get_db)):
    return DashboardService.obtener_datos_dashboard(db)