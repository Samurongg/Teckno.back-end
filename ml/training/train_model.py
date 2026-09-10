import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
RUTA_DATASET = RAIZ_PROYECTO / "ml" / "data" / "pedidos.csv"
DIRECTORIO_MODELOS = RAIZ_PROYECTO / "ml" / "models"
RUTA_MODELO_ACTIVO = DIRECTORIO_MODELOS / "modelo_entrega.joblib"
RUTA_METADATA_ACTIVA = DIRECTORIO_MODELOS / "metadatos_modelo.json"
RUTA_REPORTE = RAIZ_PROYECTO / "ml" / "reports" / "comparacion_modelos.json"
DIRECTORIO_RESPALDOS = DIRECTORIO_MODELOS / "backups"
VERSION_MODELO = "v3.0.2"

COLUMNAS_NUMERICAS = [
    "distancia_km",
    "tiempo_estimado_dias",
    "tiempo_preparacion_horas",
    "cantidad_productos",
    "peso_kg",
]

COLUMNAS_CATEGORICAS = [
    "zona_logistica",
    "modo_transporte",
    "tipo_envio",
    "prioridad",
    "dia_semana",
    "carga_logistica",
]

COLUMNAS_MODELO = COLUMNAS_NUMERICAS + COLUMNAS_CATEGORICAS


def _crear_preprocesador() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), COLUMNAS_NUMERICAS),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                COLUMNAS_CATEGORICAS,
            ),
        ]
    )


def _crear_candidatos() -> dict[str, object]:
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=1500,
            random_state=42,
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=6,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=42,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            max_depth=10,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=400,
            max_depth=12,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    }


def _probabilidad_clase_positiva(modelo: object, datos: pd.DataFrame) -> np.ndarray:
    probabilidades = modelo.predict_proba(datos)
    clases = list(modelo.classes_)
    if 1 not in clases:
        raise ValueError("El modelo entrenado no contiene la clase positiva 1.")
    return probabilidades[:, clases.index(1)]


def _calcular_metricas(
    y_real: pd.Series,
    probabilidades: np.ndarray,
    umbral: float,
) -> dict[str, object]:
    predicciones = (probabilidades >= umbral).astype(int)
    return {
        "threshold": round(float(umbral), 4),
        "accuracy": round(float(accuracy_score(y_real, predicciones)), 4),
        "balanced_accuracy": round(
            float(balanced_accuracy_score(y_real, predicciones)), 4
        ),
        "precision": round(
            float(precision_score(y_real, predicciones, zero_division=0)), 4
        ),
        "recall": round(
            float(recall_score(y_real, predicciones, zero_division=0)), 4
        ),
        "f1_score": round(
            float(f1_score(y_real, predicciones, zero_division=0)), 4
        ),
        "f2_score": round(
            float(fbeta_score(y_real, predicciones, beta=2, zero_division=0)), 4
        ),
        "roc_auc": round(float(roc_auc_score(y_real, probabilidades)), 4),
        "average_precision": round(
            float(average_precision_score(y_real, probabilidades)), 4
        ),
        "brier_score": round(float(brier_score_loss(y_real, probabilidades)), 4),
        "predicted_positive_rate": round(float(predicciones.mean()), 4),
        "confusion_matrix": confusion_matrix(
            y_real, predicciones, labels=[0, 1]
        ).tolist(),
    }


def _seleccionar_umbral(
    y_validacion: pd.Series,
    probabilidades: np.ndarray,
) -> tuple[float, dict[str, object]]:
    """Equilibra precisión y detección manteniendo un recall mínimo de 50 %."""
    resultados = []
    for umbral in np.linspace(0.10, 0.80, 71):
        metricas = _calcular_metricas(y_validacion, probabilidades, umbral)
        resultados.append(metricas)

    resultados_admisibles = [
        metricas for metricas in resultados if metricas["recall"] >= 0.50
    ]
    if not resultados_admisibles:
        resultados_admisibles = resultados

    mejor = max(
        resultados_admisibles,
        key=lambda item: (
            item["f1_score"],
            item["balanced_accuracy"],
            item["precision"],
        ),
    )
    return float(mejor["threshold"]), mejor


def _separar_cronologicamente(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fechas = pd.to_datetime(df["fecha_pedido"], errors="raise")
    datos = (
        df.assign(_fecha_orden=fechas)
        .sort_values(["_fecha_orden", "order_id"])
        .drop(columns="_fecha_orden")
        .reset_index(drop=True)
    )

    fin_entrenamiento = int(len(datos) * 0.70)
    fin_validacion = int(len(datos) * 0.85)
    entrenamiento = datos.iloc[:fin_entrenamiento].copy()
    validacion = datos.iloc[fin_entrenamiento:fin_validacion].copy()
    prueba = datos.iloc[fin_validacion:].copy()

    for nombre, particion in [
        ("entrenamiento", entrenamiento),
        ("validación", validacion),
        ("prueba", prueba),
    ]:
        if particion.empty or particion["entrega_tardia"].nunique() < 2:
            raise ValueError(f"La partición de {nombre} no contiene ambas clases.")

    return entrenamiento, validacion, prueba


def _datos_modelo(
    particion: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    return particion[COLUMNAS_MODELO], particion["entrega_tardia"]


def _leer_json(ruta: Path) -> dict[str, object]:
    if not ruta.exists():
        return {}
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _guardar_json_atomico(datos: dict[str, object], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, nombre_temporal = tempfile.mkstemp(
        prefix=f".{ruta.stem}_", suffix=".tmp", dir=ruta.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=4, ensure_ascii=False)
            archivo.write("\n")
        os.replace(nombre_temporal, ruta)
    except Exception:
        if os.path.exists(nombre_temporal):
            os.unlink(nombre_temporal)
        raise


def _activar_modelo(
    pipeline: Pipeline,
    metadatos: dict[str, object],
) -> list[str]:
    DIRECTORIO_MODELOS.mkdir(parents=True, exist_ok=True)
    DIRECTORIO_RESPALDOS.mkdir(parents=True, exist_ok=True)
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    rutas_respaldo = []

    if RUTA_MODELO_ACTIVO.exists():
        respaldo_modelo = (
            DIRECTORIO_RESPALDOS / f"modelo_entrega_{marca_tiempo}.joblib"
        )
        shutil.copy2(RUTA_MODELO_ACTIVO, respaldo_modelo)
        rutas_respaldo.append(
            respaldo_modelo.relative_to(RAIZ_PROYECTO).as_posix()
        )
    if RUTA_METADATA_ACTIVA.exists():
        respaldo_metadata = (
            DIRECTORIO_RESPALDOS / f"metadatos_modelo_{marca_tiempo}.json"
        )
        shutil.copy2(RUTA_METADATA_ACTIVA, respaldo_metadata)
        rutas_respaldo.append(
            respaldo_metadata.relative_to(RAIZ_PROYECTO).as_posix()
        )

    descriptor, nombre_temporal = tempfile.mkstemp(
        prefix=".modelo_entrega_", suffix=".joblib", dir=DIRECTORIO_MODELOS
    )
    os.close(descriptor)
    try:
        joblib.dump(pipeline, nombre_temporal)
        os.replace(nombre_temporal, RUTA_MODELO_ACTIVO)
        _guardar_json_atomico(metadatos, RUTA_METADATA_ACTIVA)
    except Exception:
        if os.path.exists(nombre_temporal):
            os.unlink(nombre_temporal)
        raise

    return rutas_respaldo


def entrenar_y_evaluar(activar_si_mejora: bool = False) -> dict[str, object]:
    if not RUTA_DATASET.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {RUTA_DATASET}")

    df = pd.read_csv(RUTA_DATASET)
    hash_dataset_actual = hashlib.sha256(RUTA_DATASET.read_bytes()).hexdigest()
    columnas_requeridas = {
        "order_id",
        "fecha_pedido",
        "entrega_tardia",
        *COLUMNAS_MODELO,
    }
    faltantes = sorted(columnas_requeridas - set(df.columns))
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {faltantes}")

    entrenamiento, validacion, prueba = _separar_cronologicamente(df)
    X_train, y_train = _datos_modelo(entrenamiento)
    X_val, y_val = _datos_modelo(validacion)
    X_test, y_test = _datos_modelo(prueba)

    print("\n" + "=" * 72)
    print("EVALUACIÓN TEMPORAL DE MODELOS - TECNOMARKET ANALYTICS")
    print("=" * 72)
    for nombre, particion in [
        ("Entrenamiento", entrenamiento),
        ("Validación", validacion),
        ("Prueba final", prueba),
    ]:
        print(
            f"{nombre}: {len(particion):,} filas | "
            f"{particion['fecha_pedido'].min()} a {particion['fecha_pedido'].max()} | "
            f"retrasos={particion['entrega_tardia'].mean():.2%}"
        )

    comparacion_validacion = {}
    pipelines = {}
    for nombre, clasificador in _crear_candidatos().items():
        pipeline = Pipeline(
            steps=[
                ("preprocessor", _crear_preprocesador()),
                ("classifier", clasificador),
            ]
        )
        pipeline.fit(X_train, y_train)
        probabilidades_val = _probabilidad_clase_positiva(pipeline, X_val)
        umbral, metricas_val = _seleccionar_umbral(y_val, probabilidades_val)
        metricas_val["selection_score"] = round(
            0.55 * metricas_val["roc_auc"] + 0.45 * metricas_val["f1_score"],
            4,
        )
        comparacion_validacion[nombre] = metricas_val
        pipelines[nombre] = pipeline

        print(
            f"\n{nombre}: AUC={metricas_val['roc_auc']:.4f} | "
            f"F1={metricas_val['f1_score']:.4f} | "
            f"F2={metricas_val['f2_score']:.4f} | "
            f"Recall={metricas_val['recall']:.4f} | "
            f"Umbral={umbral:.2f}"
        )

    mejor_nombre = max(
        comparacion_validacion,
        key=lambda nombre: comparacion_validacion[nombre]["selection_score"],
    )
    mejor_pipeline = pipelines[mejor_nombre]
    mejor_umbral = float(comparacion_validacion[mejor_nombre]["threshold"])

    probabilidades_test = _probabilidad_clase_positiva(mejor_pipeline, X_test)
    metricas_test = _calcular_metricas(y_test, probabilidades_test, mejor_umbral)

    metadata_anterior = _leer_json(RUTA_METADATA_ACTIVA)
    dataset_modelo_activo_distinto = (
        metadata_anterior.get("dataset_sha256") != hash_dataset_actual
    )
    metricas_modelo_activo = None
    error_modelo_activo = None
    if RUTA_MODELO_ACTIVO.exists():
        try:
            modelo_activo = joblib.load(RUTA_MODELO_ACTIVO)
            umbral_activo = float(metadata_anterior.get("decision_threshold", 0.50))
            probabilidades_activas = _probabilidad_clase_positiva(
                modelo_activo, X_test
            )
            metricas_modelo_activo = _calcular_metricas(
                y_test, probabilidades_activas, umbral_activo
            )
        except Exception as exc:
            error_modelo_activo = str(exc)

    minimos = {
        "roc_auc": 0.70,
        "recall": 0.55,
        "precision": 0.35,
        "f1_score": 0.40,
        "accuracy": 0.65,
    }
    cumple_minimos = all(
        metricas_test[metrica] >= minimo for metrica, minimo in minimos.items()
    )
    cumple_volumen_alertas = metricas_test["predicted_positive_rate"] <= 0.50
    cumple_minimos = bool(cumple_minimos and cumple_volumen_alertas)
    if metricas_modelo_activo is None:
        mejora_clasificacion = True
        mejora_calibracion = True
        simplificacion_no_inferior = True
        supera_modelo_activo = True
    else:
        mejora_clasificacion = (
            metricas_test["roc_auc"]
            >= metricas_modelo_activo["roc_auc"] + 0.02
            and metricas_test["f1_score"]
            >= metricas_modelo_activo["f1_score"] + 0.05
        )
        mejora_calibracion = (
            metricas_test["brier_score"]
            <= metricas_modelo_activo["brier_score"] - 0.03
            and metricas_test["roc_auc"]
            >= metricas_modelo_activo["roc_auc"] - 0.005
            and metricas_test["f1_score"]
            >= metricas_modelo_activo["f1_score"] - 0.01
        )
        features_anteriores = metadata_anterior.get("features", {})
        cantidad_features_anteriores = len(
            features_anteriores.get("numerical", [])
        ) + len(features_anteriores.get("categorical", []))
        simplificacion_no_inferior = (
            len(COLUMNAS_MODELO) < cantidad_features_anteriores
            and metricas_test["roc_auc"]
            >= metricas_modelo_activo["roc_auc"] - 0.005
            and metricas_test["f1_score"]
            >= metricas_modelo_activo["f1_score"] - 0.01
        )
        supera_modelo_activo = (
            mejora_clasificacion
            or mejora_calibracion
            or simplificacion_no_inferior
            or dataset_modelo_activo_distinto
        )

    aprobado = bool(cumple_minimos and supera_modelo_activo)
    activado = bool(activar_si_mejora and aprobado)
    fecha_entrenamiento = datetime.now().astimezone().isoformat(timespec="seconds")

    metadatos = {
        "model_name": mejor_nombre,
        "model_version": VERSION_MODELO,
        "trained_at": fecha_entrenamiento,
        "total_samples": len(df),
        "train_samples": len(entrenamiento),
        "validation_samples": len(validacion),
        "test_samples": len(prueba),
        "target_distribution": {
            "ontime_0": int((df["entrega_tardia"] == 0).sum()),
            "delayed_1": int((df["entrega_tardia"] == 1).sum()),
        },
        "features": {
            "numerical": COLUMNAS_NUMERICAS,
            "categorical": COLUMNAS_CATEGORICAS,
        },
        "decision_threshold": mejor_umbral,
        "best_model_metrics": metricas_test,
        "comparison": comparacion_validacion,
        "active_model_comparison": {
            "previous_model_name": metadata_anterior.get("model_name"),
            "previous_model_version": metadata_anterior.get("model_version"),
            "test_metrics": metricas_modelo_activo,
            "evaluation_error": error_modelo_activo,
        },
        "historical_baseline": metadata_anterior.get(
            "historical_baseline",
            metadata_anterior.get("active_model_comparison"),
        ),
        "validation_strategy": {
            "type": "chronological_holdout",
            "selection_metric": "0.55 * ROC-AUC + 0.45 * F1",
            "threshold_metric": "maximum F1 with recall >= 0.50",
            "train_period": [
                entrenamiento["fecha_pedido"].min(),
                entrenamiento["fecha_pedido"].max(),
            ],
            "validation_period": [
                validacion["fecha_pedido"].min(),
                validacion["fecha_pedido"].max(),
            ],
            "test_period": [
                prueba["fecha_pedido"].min(),
                prueba["fecha_pedido"].max(),
            ],
        },
        "quality_gate": {
            "minimum_metrics": minimos,
            "maximum_predicted_positive_rate": 0.50,
            "requires_active_auc_improvement": 0.02,
            "requires_active_f1_improvement": 0.05,
            "allows_brier_improvement": 0.03,
            "active_dataset_mismatch": dataset_modelo_activo_distinto,
            "classification_improved": mejora_clasificacion,
            "calibration_improved": mejora_calibracion,
            "simpler_non_inferior_model": simplificacion_no_inferior,
            "meets_minimum_metrics": cumple_minimos,
            "beats_active_model": supera_modelo_activo,
            "approved": aprobado,
            "activated": activado,
        },
        "dataset_sha256": hash_dataset_actual,
        "runtime_versions": {
            "python": os.sys.version.split()[0],
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }

    respaldos = []
    if activado:
        respaldos = _activar_modelo(mejor_pipeline, metadatos)

    reporte = {
        **metadatos,
        "activation_requested": activar_si_mejora,
        "backup_paths": respaldos,
    }
    _guardar_json_atomico(reporte, RUTA_REPORTE)

    print("\n" + "=" * 72)
    print(f"MODELO SELECCIONADO: {mejor_nombre}")
    print(
        f"Prueba final: AUC={metricas_test['roc_auc']:.4f} | "
        f"F1={metricas_test['f1_score']:.4f} | "
        f"Recall={metricas_test['recall']:.4f} | "
        f"Precision={metricas_test['precision']:.4f}"
    )
    if metricas_modelo_activo:
        print(
            f"Modelo anterior: AUC={metricas_modelo_activo['roc_auc']:.4f} | "
            f"F1={metricas_modelo_activo['f1_score']:.4f} | "
            f"Recall={metricas_modelo_activo['recall']:.4f}"
        )
    print(f"Control de calidad aprobado: {'SÍ' if aprobado else 'NO'}")
    print(f"Modelo activado: {'SÍ' if activado else 'NO'}")
    print(f"Reporte guardado en: {RUTA_REPORTE}")
    print("=" * 72)

    return reporte


def _leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Entrena, valida y compara modelos de retraso de entregas."
    )
    parser.add_argument(
        "--activate-if-better",
        action="store_true",
        help="Activa el candidato solo si supera los controles de calidad.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    argumentos = _leer_argumentos()
    entrenar_y_evaluar(activar_si_mejora=argumentos.activate_if_better)
