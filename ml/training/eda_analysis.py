from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from app.domain.peru_logistics import (
    DEPARTAMENTOS_PERU,
    distancia_es_plausible,
    modos_permitidos,
)


RUTA_CSV = RAIZ_PROYECTO / "ml" / "data" / "pedidos.csv"
DIRECTORIO_FIGURAS = RAIZ_PROYECTO / "ml" / "reports" / "figures"

COLUMNAS_ESPERADAS = [
    "order_id",
    "fecha_pedido",
    "departamento_destino",
    "zona_logistica",
    "modo_transporte",
    "tipo_envio",
    "distancia_km",
    "tiempo_estimado_dias",
    "tiempo_preparacion_horas",
    "cantidad_productos",
    "peso_kg",
    "prioridad",
    "dia_semana",
    "carga_logistica",
    "entrega_tardia",
]

DIAS_SEMANA = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def _validar_dataset(df: pd.DataFrame) -> pd.Series:
    """Valida estructura, integridad y coherencia básica del conjunto."""
    columnas_faltantes = sorted(set(COLUMNAS_ESPERADAS) - set(df.columns))
    columnas_adicionales = sorted(set(df.columns) - set(COLUMNAS_ESPERADAS))
    if columnas_faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {columnas_faltantes}")
    if columnas_adicionales:
        raise ValueError(f"Hay columnas no esperadas: {columnas_adicionales}")

    fechas = pd.to_datetime(df["fecha_pedido"], errors="coerce")
    errores = []
    if df.isna().any().any():
        errores.append(f"valores nulos={int(df.isna().sum().sum())}")
    if fechas.isna().any():
        errores.append(f"fechas inválidas={int(fechas.isna().sum())}")
    if df["order_id"].duplicated().any():
        errores.append(f"order_id duplicados={int(df['order_id'].duplicated().sum())}")
    if not set(df["entrega_tardia"].unique()).issubset({0, 1}):
        errores.append("entrega_tardia contiene valores distintos de 0 y 1")

    columnas_positivas = [
        "distancia_km",
        "tiempo_estimado_dias",
        "tiempo_preparacion_horas",
        "cantidad_productos",
        "peso_kg",
    ]
    for columna in columnas_positivas:
        cantidad_invalidos = int((df[columna] <= 0).sum())
        if cantidad_invalidos:
            errores.append(f"{columna} no positivos={cantidad_invalidos}")

    dias_derivados = fechas.dt.dayofweek.map(DIAS_SEMANA)
    dias_inconsistentes = int((dias_derivados != df["dia_semana"]).sum())
    if dias_inconsistentes:
        errores.append(f"día/fecha inconsistentes={dias_inconsistentes}")

    departamentos_invalidos = sorted(
        set(df["departamento_destino"]) - set(DEPARTAMENTOS_PERU)
    )
    if departamentos_invalidos:
        errores.append(f"departamentos inválidos={departamentos_invalidos}")
    else:
        zonas_esperadas = df["departamento_destino"].map(
            lambda departamento: DEPARTAMENTOS_PERU[departamento].zona_logistica
        )
        zonas_inconsistentes = int(
            (zonas_esperadas != df["zona_logistica"]).sum()
        )
        if zonas_inconsistentes:
            errores.append(
                f"departamento/zona inconsistentes={zonas_inconsistentes}"
            )

        distancias_inconsistentes = sum(
            not distancia_es_plausible(departamento, distancia)
            for departamento, distancia in zip(
                df["departamento_destino"], df["distancia_km"]
            )
        )
        if distancias_inconsistentes:
            errores.append(
                f"departamento/distancia inconsistentes={distancias_inconsistentes}"
            )

        transportes_inconsistentes = sum(
            modo not in modos_permitidos(departamento)
            for departamento, modo in zip(
                df["departamento_destino"], df["modo_transporte"]
            )
        )
        if transportes_inconsistentes:
            errores.append(
                f"departamento/transporte inconsistentes={transportes_inconsistentes}"
            )

    if errores:
        raise ValueError("Dataset inválido: " + "; ".join(errores))
    return fechas


def _tabla_tasa(df: pd.DataFrame, columna: str) -> pd.DataFrame:
    tabla = df.groupby(columna, observed=False)["entrega_tardia"].agg(
        total="count", retrasos="sum", tasa_retraso="mean"
    )
    tabla["tasa_retraso"] = (tabla["tasa_retraso"] * 100).round(2)
    return tabla.sort_values("tasa_retraso", ascending=False)


def ejecutar_eda() -> None:
    if not RUTA_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_CSV}. Ejecuta generate_dataset.py primero."
        )

    df = pd.read_csv(RUTA_CSV)
    fechas = _validar_dataset(df)
    DIRECTORIO_FIGURAS.mkdir(parents=True, exist_ok=True)

    df_analisis = df.copy()
    df_analisis["mes"] = fechas.dt.month

    print("=" * 68)
    print("TECNOMARKET ANALYTICS - REPORTE EXPLORATORIO DE DATOS (EDA)")
    print("=" * 68)

    print("\n1. VALIDACIÓN DE CALIDAD:")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")
    print(f"Valores nulos: {int(df.isna().sum().sum())}")
    print(f"order_id duplicados: {int(df['order_id'].duplicated().sum())}")
    print("Coherencia fecha/día: correcta")
    print("Coherencia departamento/zona/distancia/transporte: correcta")
    print("Valores del target: 0 y 1")

    print("\n2. ESTRUCTURA Y TIPOS:")
    df.info()

    print("\n3. ESTADÍSTICAS DESCRIPTIVAS (NUMÉRICAS):")
    print(df.describe().round(2))

    conteo_target = df["entrega_tardia"].value_counts().reindex([0, 1], fill_value=0)
    print("\n4. DISTRIBUCIÓN DE LA VARIABLE OBJETIVO:")
    print(conteo_target.rename(index={0: "A tiempo", 1: "Tardío"}))
    print(f"Tasa global de retrasos: {df['entrega_tardia'].mean():.2%}")

    print("\n5. TASA DE RETRASOS POR CATEGORÍA:")
    for columna in [
        "departamento_destino",
        "zona_logistica",
        "modo_transporte",
        "tipo_envio",
        "carga_logistica",
        "prioridad",
        "dia_semana",
    ]:
        print(f"\n--- Desglose por {columna} (porcentaje) ---")
        print(_tabla_tasa(df, columna))

    print("\n6. EVOLUCIÓN MENSUAL:")
    tabla_mensual = _tabla_tasa(df_analisis, "mes").sort_index()
    print(tabla_mensual)

    plt.style.use(
        "seaborn-v0_8-whitegrid"
        if "seaborn-v0_8-whitegrid" in plt.style.available
        else "default"
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].pie(
        conteo_target.to_numpy(),
        labels=["A tiempo (0)", "Tardío (1)"],
        autopct="%1.1f%%",
        colors=["#10B981", "#EF4444"],
        startangle=90,
    )
    axes[0].set_title("Distribución de la variable objetivo")

    sns.boxplot(
        x="entrega_tardia",
        y="distancia_km",
        data=df,
        order=[0, 1],
        hue="entrega_tardia",
        palette={0: "#10B981", 1: "#EF4444"},
        legend=False,
        ax=axes[1],
    )
    axes[1].set_title("Distancia frente al estado de entrega")
    axes[1].set_xlabel("Estado de entrega")
    axes[1].set_ylabel("Distancia (km)")
    axes[1].set_xticks([0, 1], ["A tiempo (0)", "Tardío (1)"])
    fig.tight_layout()
    fig.savefig(DIRECTORIO_FIGURAS / "target_y_distancia.png", dpi=300)
    plt.close(fig)

    columnas_numericas = [
        "distancia_km",
        "tiempo_estimado_dias",
        "tiempo_preparacion_horas",
        "cantidad_productos",
        "peso_kg",
        "entrega_tardia",
    ]
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        df[columnas_numericas].corr(),
        annot=True,
        cmap="coolwarm",
        fmt=".2f",
        vmin=-1,
        vmax=1,
        ax=ax,
    )
    ax.set_title("Matriz de correlación numérica")
    fig.tight_layout()
    fig.savefig(DIRECTORIO_FIGURAS / "matriz_correlacion.png", dpi=300)
    plt.close(fig)

    tasas_mes = tabla_mensual["tasa_retraso"]
    tasas_carga = _tabla_tasa(df, "carga_logistica").reindex(
        ["Baja", "Media", "Alta"]
    )["tasa_retraso"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(tasas_mes.index, tasas_mes.values, marker="o", color="#2563EB")
    axes[0].set_title("Tasa mensual de retrasos")
    axes[0].set_xlabel("Mes")
    axes[0].set_ylabel("Retrasos (%)")
    axes[0].set_xticks(range(1, 13))

    axes[1].bar(tasas_carga.index, tasas_carga.values, color=["#10B981", "#F59E0B", "#EF4444"])
    axes[1].set_title("Tasa de retrasos por carga logística")
    axes[1].set_xlabel("Carga logística")
    axes[1].set_ylabel("Retrasos (%)")
    fig.tight_layout()
    fig.savefig(DIRECTORIO_FIGURAS / "tasa_mensual_y_carga.png", dpi=300)
    plt.close(fig)

    print(f"\nGráficos generados correctamente en: {DIRECTORIO_FIGURAS}")


if __name__ == "__main__":
    ejecutar_eda()
