from pathlib import Path
import sys

import numpy as np
import pandas as pd

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from app.domain.peru_logistics import DEPARTAMENTOS_PERU


RUTA_DATASET = RAIZ_PROYECTO / "ml" / "data" / "pedidos.csv"
TASA_RETRASO_OBJETIVO = 0.175

DIAS_SEMANA = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def _sigmoide(valores: np.ndarray) -> np.ndarray:
    valores_limitados = np.clip(valores, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-valores_limitados))


def _calibrar_intercepto(score: np.ndarray, tasa_objetivo: float) -> float:
    """Ajusta la probabilidad media sin fijar la cantidad exacta de retrasos."""
    limite_inferior, limite_superior = -15.0, 15.0
    for _ in range(80):
        punto_medio = (limite_inferior + limite_superior) / 2.0
        if _sigmoide(score + punto_medio).mean() > tasa_objetivo:
            limite_superior = punto_medio
        else:
            limite_inferior = punto_medio
    return (limite_inferior + limite_superior) / 2.0


def _sortear_modo_transporte(
    rng: np.random.Generator,
    departamento: str,
    tipo_envio: str,
) -> str:
    configuracion = DEPARTAMENTOS_PERU[departamento]
    modos = [modo for modo, _ in configuracion.modos_transporte]
    pesos = np.array([peso for _, peso in configuracion.modos_transporte], dtype=float)

    if tipo_envio == "Express" and "Aéreo" in modos:
        pesos[modos.index("Aéreo")] *= 2.2
    if tipo_envio == "Mismo Día":
        return "Terrestre"

    pesos /= pesos.sum()
    return str(rng.choice(modos, p=pesos))


def generar_dataset_pedidos(
    n_muestras: int = 5000,
    seed: int = 42,
    tasa_retraso_objetivo: float = TASA_RETRASO_OBJETIVO,
) -> pd.DataFrame:
    """Genera pedidos nacionales tomando Lima como centro operativo."""
    if n_muestras < 100:
        raise ValueError("n_muestras debe ser igual o mayor que 100.")
    if not 0.01 <= tasa_retraso_objetivo <= 0.99:
        raise ValueError("tasa_retraso_objetivo debe estar entre 0.01 y 0.99.")

    rng = np.random.default_rng(seed)

    order_ids = [f"ORD-{10001 + indice}" for indice in range(n_muestras)]
    fechas = pd.Timestamp("2025-01-01") + pd.to_timedelta(
        rng.integers(0, 365, size=n_muestras), unit="D"
    )
    meses = fechas.month.to_numpy()
    numeros_dia = fechas.dayofweek.to_numpy()
    es_fin_semana = numeros_dia >= 5
    es_temporada_alta = np.isin(meses, [7, 11, 12])

    nombres_departamentos = np.array(list(DEPARTAMENTOS_PERU))
    pesos_demanda = np.array(
        [DEPARTAMENTOS_PERU[nombre].peso_demanda for nombre in nombres_departamentos]
    )
    pesos_demanda /= pesos_demanda.sum()
    departamentos = rng.choice(
        nombres_departamentos, size=n_muestras, p=pesos_demanda
    )
    configuraciones = [DEPARTAMENTOS_PERU[nombre] for nombre in departamentos]
    zonas_logisticas = np.array(
        [config.zona_logistica for config in configuraciones]
    )

    minimos_distancia = np.array(
        [config.distancia_min_km for config in configuraciones], dtype=float
    )
    maximos_distancia = np.array(
        [config.distancia_max_km for config in configuraciones], dtype=float
    )
    modas_distancia = minimos_distancia + 0.42 * (
        maximos_distancia - minimos_distancia
    )
    distancias_km = rng.triangular(
        minimos_distancia, modas_distancia, maximos_distancia
    )
    distancias_km = np.round(distancias_km, 2)

    prioridades = rng.choice(
        ["Baja", "Media", "Alta"],
        size=n_muestras,
        p=[0.30, 0.50, 0.20],
    )

    score_carga = (
        rng.normal(0.0, 1.0, size=n_muestras)
        + 0.85 * es_temporada_alta
        + 0.20 * es_fin_semana
    )
    cargas_logisticas = np.select(
        [score_carga < -0.65, score_carga > 0.75],
        ["Baja", "Alta"],
        default="Media",
    )

    prob_mismo_dia = np.select(
        [distancias_km <= 80.0, distancias_km <= 180.0],
        [0.22, 0.06],
        default=0.0,
    )
    prob_express = np.select(
        [distancias_km <= 180.0, distancias_km <= 700.0],
        [0.42, 0.34],
        default=0.28,
    )
    sorteo_envio = rng.random(n_muestras)
    tipos_envio = np.where(
        sorteo_envio < prob_mismo_dia,
        "Mismo Día",
        np.where(
            sorteo_envio < prob_mismo_dia + prob_express,
            "Express",
            "Estándar",
        ),
    )

    modos_transporte = np.array(
        [
            _sortear_modo_transporte(rng, departamento, tipo_envio)
            for departamento, tipo_envio in zip(departamentos, tipos_envio)
        ]
    )

    tiempos_estimados = np.empty(n_muestras, dtype=int)
    mascara_mismo_dia = tipos_envio == "Mismo Día"
    mascara_express = tipos_envio == "Express"
    mascara_estandar = tipos_envio == "Estándar"
    mascara_multimodal = modos_transporte == "Multimodal"

    tiempos_estimados[mascara_mismo_dia] = 1
    base_express = np.ceil(distancias_km / 550.0).astype(int) + 1
    base_express += mascara_multimodal.astype(int)
    tiempos_estimados[mascara_express] = np.clip(
        base_express[mascara_express], 1, 6
    )
    base_estandar = np.ceil(distancias_km / 320.0).astype(int) + 2
    base_estandar += mascara_multimodal.astype(int)
    variacion_estandar = rng.choice(
        [-1, 0, 1], size=n_muestras, p=[0.10, 0.70, 0.20]
    )
    tiempos_estimados[mascara_estandar] = np.clip(
        base_estandar[mascara_estandar] + variacion_estandar[mascara_estandar],
        2,
        10,
    )

    cantidades = np.clip(rng.poisson(3.8, size=n_muestras) + 1, 1, 12)
    peso_unitario = rng.lognormal(mean=np.log(1.15), sigma=0.45, size=n_muestras)
    pesos_kg = cantidades * peso_unitario + rng.normal(0.35, 0.20, n_muestras)
    pesos_kg = np.round(np.clip(pesos_kg, 0.5, 40.0), 2)

    efecto_carga_preparacion = np.select(
        [cargas_logisticas == "Alta", cargas_logisticas == "Baja"],
        [1.8, -0.45],
        default=0.45,
    )
    tiempos_prep = (
        0.58 * cantidades
        + 0.24 * pesos_kg
        + efecto_carga_preparacion
        + 0.65 * es_temporada_alta
        + rng.normal(1.25, 0.85, size=n_muestras)
    )
    tiempos_prep = np.round(np.clip(tiempos_prep, 0.5, 30.0), 2)

    riesgo_zona = np.select(
        [
            zonas_logisticas == "Lima y Callao",
            np.char.startswith(zonas_logisticas, "Selva"),
            np.char.startswith(zonas_logisticas, "Sierra"),
        ],
        [-0.35, 0.45, 0.24],
        default=0.0,
    )
    riesgo_transporte = np.select(
        [modos_transporte == "Multimodal", modos_transporte == "Aéreo"],
        [0.50, -0.10],
        default=0.05,
    )
    score_riesgo = (
        0.52 * ((distancias_km - 500.0) / 400.0)
        + 0.72 * ((tiempos_prep - 5.5) / 3.0)
        + 0.14 * ((pesos_kg - 6.0) / 5.0)
        + riesgo_zona
        + riesgo_transporte
        + np.where(cargas_logisticas == "Alta", 0.95, 0.0)
        + np.where(cargas_logisticas == "Media", 0.25, 0.0)
        + np.where(
            mascara_mismo_dia,
            0.45 + 0.60 * np.maximum((distancias_km - 70.0) / 100.0, 0.0),
            0.0,
        )
        + np.where(
            mascara_express,
            0.18 * np.maximum((distancias_km - 700.0) / 500.0, 0.0),
            0.0,
        )
        - 0.10 * np.maximum(tiempos_estimados - 3, 0)
        - np.where(prioridades == "Alta", 0.38, 0.0)
        + np.where(prioridades == "Baja", 0.12, 0.0)
        + 0.22 * es_fin_semana
        + 0.28 * es_temporada_alta
        + rng.normal(0.0, 0.70, size=n_muestras)
    )

    intercepto = _calibrar_intercepto(score_riesgo, tasa_retraso_objetivo)
    prob_retraso = _sigmoide(score_riesgo + intercepto)
    entrega_tardia = rng.binomial(1, prob_retraso, size=n_muestras)

    return pd.DataFrame(
        {
            "order_id": order_ids,
            "fecha_pedido": fechas.strftime("%Y-%m-%d"),
            "departamento_destino": departamentos,
            "zona_logistica": zonas_logisticas,
            "modo_transporte": modos_transporte,
            "tipo_envio": tipos_envio,
            "distancia_km": distancias_km,
            "tiempo_estimado_dias": tiempos_estimados,
            "tiempo_preparacion_horas": tiempos_prep,
            "cantidad_productos": cantidades,
            "peso_kg": pesos_kg,
            "prioridad": prioridades,
            "dia_semana": [DIAS_SEMANA[dia] for dia in numeros_dia],
            "carga_logistica": cargas_logisticas,
            "entrega_tardia": entrega_tardia,
        }
    )


if __name__ == "__main__":
    RUTA_DATASET.parent.mkdir(parents=True, exist_ok=True)
    dataset = generar_dataset_pedidos()
    dataset.to_csv(RUTA_DATASET, index=False)
    print(f"Dataset generado exitosamente en: {RUTA_DATASET}")
    print(f"Dimensiones: {dataset.shape}")
    print(f"Tasa objetivo aproximada: {TASA_RETRASO_OBJETIVO:.2%}")
    print(f"Tasa observada: {dataset['entrega_tardia'].mean():.2%}")
    print("Distribución del target:")
    print(dataset["entrega_tardia"].value_counts().sort_index())
