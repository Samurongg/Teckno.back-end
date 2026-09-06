import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import orders, predict, dashboard, analytics, model_info
from app.database.connection import Base, engine
from app.database.seed_db import inicializar_y_poblar_bd

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    inicializar_y_poblar_bd()
    yield

allowed_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
).split(",")
local_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

app = FastAPI(
    title="TecnoMarket Analytics API",
    description="API REST de Analítica Logística y Predicción de Entregas Tardías con ML",
    version="2.4.1",
    lifespan=lifespan,
)

# Configuración de CORS para desarrollo con React / Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=local_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de routers
app.include_router(dashboard.router)
app.include_router(orders.router)
app.include_router(predict.router)
app.include_router(analytics.router)
app.include_router(model_info.router)

@app.get("/api/health", tags=["Health Check"])
def health_check():
    return {
        "status": "online",
        "service": "TecnoMarket Analytics API",
        "version": "2.4.1"
    }
