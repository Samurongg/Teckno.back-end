from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.peru_logistics import (
    DEPARTAMENTOS_PERU,
    distancia_es_plausible,
    modos_permitidos,
    obtener_configuracion,
)


class PredictionInput(BaseModel):
    departamento_destino: str = Field(
        ..., description="Departamento de destino del pedido enviado desde Lima"
    )
    modo_transporte: Literal["Terrestre", "Aéreo", "Multimodal"]
    tipo_envio: Literal["Estándar", "Express", "Mismo Día"]
    distancia_km: float = Field(
        ..., gt=0, le=2500, description="Distancia logística aproximada desde Lima"
    )
    tiempo_estimado_dias: int = Field(
        ..., ge=1, le=15, description="Días prometidos al cliente"
    )
    tiempo_preparacion_horas: float = Field(
        ..., ge=0.1, le=72, description="Horas de preparación"
    )
    cantidad_productos: int = Field(..., ge=1, le=50)
    peso_kg: float = Field(..., ge=0.1, le=100)
    prioridad: Literal["Baja", "Media", "Alta"]
    dia_semana: Literal[
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    carga_logistica: Literal["Baja", "Media", "Alta"]

    @field_validator("departamento_destino")
    @classmethod
    def validar_departamento(cls, valor: str) -> str:
        if valor not in DEPARTAMENTOS_PERU:
            opciones = ", ".join(DEPARTAMENTOS_PERU)
            raise ValueError(f"Departamento no reconocido. Valores válidos: {opciones}")
        return valor

    @model_validator(mode="after")
    def validar_ruta_logistica(self):
        config = obtener_configuracion(self.departamento_destino)
        if not distancia_es_plausible(
            self.departamento_destino, self.distancia_km
        ):
            raise ValueError(
                "La distancia no es coherente con el departamento seleccionado. "
                f"Rango de referencia: {config.distancia_min_km:.0f}-"
                f"{config.distancia_max_km:.0f} km."
            )
        if self.modo_transporte not in modos_permitidos(
            self.departamento_destino
        ):
            modos = ", ".join(modos_permitidos(self.departamento_destino))
            raise ValueError(
                f"Transporte no disponible para {self.departamento_destino}. "
                f"Opciones: {modos}."
            )
        if self.tipo_envio == "Mismo Día" and (
            self.distancia_km > 180 or self.modo_transporte != "Terrestre"
        ):
            raise ValueError(
                "Mismo Día solo está disponible por vía terrestre hasta 180 km."
            )
        return self


class PredictionResponse(BaseModel):
    prediccion: int
    resultado: str
    probabilidad_retraso: float
    nivel_riesgo: str
    departamento_destino: str
    zona_logistica: str
    modo_transporte: str
