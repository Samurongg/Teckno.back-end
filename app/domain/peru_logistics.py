from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracionDepartamento:
    zona_logistica: str
    distancia_min_km: float
    distancia_max_km: float
    peso_demanda: float
    modos_transporte: tuple[tuple[str, float], ...]

    @property
    def distancia_referencia_km(self) -> float:
        return round((self.distancia_min_km + self.distancia_max_km) / 2.0, 1)


SOLO_TERRESTRE = (("Terrestre", 0.94), ("Aéreo", 0.06))
TRANSPORTE_LOCAL = (("Terrestre", 1.0),)
TERRESTRE_MULTIMODAL = (
    ("Terrestre", 0.78),
    ("Multimodal", 0.16),
    ("Aéreo", 0.06),
)


# Rangos logísticos aproximados desde el centro operativo de Lima. Representan
# recorrido operativo, no distancia en línea recta, y permiten variación local.
DEPARTAMENTOS_PERU: dict[str, ConfiguracionDepartamento] = {
    "Amazonas": ConfiguracionDepartamento("Selva Norte", 900, 1350, 0.010, TERRESTRE_MULTIMODAL),
    "Áncash": ConfiguracionDepartamento("Costa Norte", 300, 550, 0.035, SOLO_TERRESTRE),
    "Apurímac": ConfiguracionDepartamento("Sierra Sur", 700, 1050, 0.012, SOLO_TERRESTRE),
    "Arequipa": ConfiguracionDepartamento("Costa Sur", 900, 1150, 0.070, SOLO_TERRESTRE),
    "Ayacucho": ConfiguracionDepartamento("Sierra Sur", 500, 750, 0.020, SOLO_TERRESTRE),
    "Cajamarca": ConfiguracionDepartamento("Sierra Norte", 750, 1050, 0.030, SOLO_TERRESTRE),
    "Callao": ConfiguracionDepartamento("Lima y Callao", 5, 80, 0.060, TRANSPORTE_LOCAL),
    "Cusco": ConfiguracionDepartamento("Sierra Sur", 900, 1250, 0.045, SOLO_TERRESTRE),
    "Huancavelica": ConfiguracionDepartamento("Sierra Centro", 400, 650, 0.008, SOLO_TERRESTRE),
    "Huánuco": ConfiguracionDepartamento("Sierra Centro", 350, 600, 0.020, SOLO_TERRESTRE),
    "Ica": ConfiguracionDepartamento("Costa Sur", 220, 380, 0.035, SOLO_TERRESTRE),
    "Junín": ConfiguracionDepartamento("Sierra Centro", 250, 500, 0.040, SOLO_TERRESTRE),
    "La Libertad": ConfiguracionDepartamento("Costa Norte", 520, 720, 0.060, SOLO_TERRESTRE),
    "Lambayeque": ConfiguracionDepartamento("Costa Norte", 700, 880, 0.045, SOLO_TERRESTRE),
    "Lima": ConfiguracionDepartamento("Lima y Callao", 5, 180, 0.300, TRANSPORTE_LOCAL),
    "Loreto": ConfiguracionDepartamento(
        "Selva Norte",
        1000,
        1800,
        0.025,
        (("Aéreo", 0.68), ("Multimodal", 0.32)),
    ),
    "Madre de Dios": ConfiguracionDepartamento(
        "Selva Centro-Sur",
        1000,
        1500,
        0.010,
        (("Terrestre", 0.58), ("Aéreo", 0.32), ("Multimodal", 0.10)),
    ),
    "Moquegua": ConfiguracionDepartamento("Costa Sur", 1050, 1250, 0.010, SOLO_TERRESTRE),
    "Pasco": ConfiguracionDepartamento("Sierra Centro", 250, 450, 0.008, SOLO_TERRESTRE),
    "Piura": ConfiguracionDepartamento("Costa Norte", 850, 1100, 0.055, SOLO_TERRESTRE),
    "Puno": ConfiguracionDepartamento("Sierra Sur", 1200, 1550, 0.030, SOLO_TERRESTRE),
    "San Martín": ConfiguracionDepartamento("Selva Norte", 900, 1300, 0.025, TERRESTRE_MULTIMODAL),
    "Tacna": ConfiguracionDepartamento("Costa Sur", 1200, 1450, 0.015, SOLO_TERRESTRE),
    "Tumbes": ConfiguracionDepartamento("Costa Norte", 1150, 1400, 0.012, SOLO_TERRESTRE),
    "Ucayali": ConfiguracionDepartamento(
        "Selva Centro-Sur",
        700,
        1100,
        0.020,
        (("Terrestre", 0.55), ("Aéreo", 0.25), ("Multimodal", 0.20)),
    ),
}

ZONAS_LOGISTICAS = tuple(
    sorted({config.zona_logistica for config in DEPARTAMENTOS_PERU.values()})
)
MODOS_TRANSPORTE = ("Terrestre", "Aéreo", "Multimodal")


def obtener_configuracion(departamento: str) -> ConfiguracionDepartamento:
    try:
        return DEPARTAMENTOS_PERU[departamento]
    except KeyError as exc:
        raise ValueError(f"Departamento no reconocido: {departamento}") from exc


def obtener_zona_logistica(departamento: str) -> str:
    return obtener_configuracion(departamento).zona_logistica


def distancia_es_plausible(departamento: str, distancia_km: float) -> bool:
    config = obtener_configuracion(departamento)
    margen_inferior = max(1.0, config.distancia_min_km * 0.75)
    margen_superior = config.distancia_max_km * 1.25
    return margen_inferior <= distancia_km <= margen_superior


def modos_permitidos(departamento: str) -> tuple[str, ...]:
    return tuple(modo for modo, _ in obtener_configuracion(departamento).modos_transporte)
