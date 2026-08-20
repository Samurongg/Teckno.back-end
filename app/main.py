from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import orders, predict, dashboard, analytics, model_info
from app.database.connection import Base, engine

# Asegurar la creación de tablas al inicio
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TecnoMarket Analytics API",
    description="API REST de Analítica Logística y Predicción de Entregas Tardías con ML",
    version="2.4.1"
)

# Configuración de CORS para desarrollo con React / Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
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