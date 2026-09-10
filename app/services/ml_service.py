import os
import json
import joblib
import numpy as np
import pandas as pd
from app.domain.peru_logistics import obtener_zona_logistica
from app.schemas.prediction import PredictionInput

class MLService:
    def __init__(self):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.model_path = os.path.join(BASE_DIR, "ml", "models", "modelo_entrega.joblib")
        self.metadata_path = os.path.join(BASE_DIR, "ml", "models", "metadatos_modelo.json")
        self.pipeline = None
        self.decision_threshold = 0.50
        self._cargar_modelo()

    def _cargar_modelo(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modelo no encontrado en: {self.model_path}. Entrena el modelo con train_model.py")
        self.pipeline = joblib.load(self.model_path)
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                metadatos = json.load(f)
            umbral = float(metadatos.get("decision_threshold", 0.50))
            if not 0.0 < umbral < 1.0:
                raise ValueError("El umbral de decisión del modelo debe estar entre 0 y 1")
            self.decision_threshold = umbral

    def predecir_retraso(self, datos: PredictionInput) -> dict:
        pipeline = self.pipeline
        if pipeline is None:
            raise RuntimeError("El modelo no está cargado")

        # 1. Definir los datos en un diccionario
        zona_logistica = obtener_zona_logistica(datos.departamento_destino)
        datos_dict = {
            'departamento_destino': str(datos.departamento_destino),
            'zona_logistica': zona_logistica,
            'modo_transporte': str(datos.modo_transporte),
            'tipo_envio': str(datos.tipo_envio),
            'distancia_km': float(datos.distancia_km),
            'tiempo_estimado_dias': int(datos.tiempo_estimado_dias),
            'tiempo_preparacion_horas': float(datos.tiempo_preparacion_horas),
            'cantidad_productos': int(datos.cantidad_productos),
            'peso_kg': float(datos.peso_kg),
            'prioridad': str(datos.prioridad),
            'dia_semana': str(datos.dia_semana),
            'carga_logistica': str(datos.carga_logistica)
        }

        # 2. Construir el DataFrame
        df_input = pd.DataFrame([datos_dict])

        # 3. Alinear el orden de columnas con el que fue entrenado el modelo
        if hasattr(pipeline, "feature_names_in_"):
            columnas_esperadas = list(pipeline.feature_names_in_)
            df_input = df_input[columnas_esperadas]
        else:
            # Orden estándar de X en el dataset original
            columnas_ordenadas = [
                'zona_logistica', 'modo_transporte', 'tipo_envio',
                'distancia_km', 'tiempo_estimado_dias',
                'tiempo_preparacion_horas', 'cantidad_productos', 'peso_kg',
                'prioridad', 'dia_semana', 'carga_logistica'
            ]
            df_input = df_input[columnas_ordenadas]

        # 4. Inferencia probabilística
        probabilidades = pipeline.predict_proba(df_input)
        clases = list(pipeline.classes_)
        if 1 not in clases:
            raise ValueError("El modelo no contiene la clase esperada para entrega tardía (1)")
        indice_clase_retraso = clases.index(1)
        probabilidad = float(probabilidades[0][indice_clase_retraso])
        prediccion = int(probabilidad >= self.decision_threshold)

        # 5. Determinación de nivel de riesgo
        if probabilidad >= 0.70:
            nivel_riesgo = "ALTO"
        elif probabilidad >= 0.35:
            nivel_riesgo = "MEDIO"
        else:
            nivel_riesgo = "BAJO"

        return {
            "prediccion": prediccion,
            "resultado": "Entrega Tardía" if prediccion == 1 else "A Tiempo",
            "probabilidad_retraso": round(probabilidad * 100, 2),
            "nivel_riesgo": nivel_riesgo,
            "departamento_destino": datos.departamento_destino,
            "zona_logistica": zona_logistica,
            "modo_transporte": datos.modo_transporte,
        }

    def obtener_metadatos(self) -> dict:
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadatos no encontrados en: {self.metadata_path}")
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            metadatos = json.load(f)
        metadatos["feature_importance"] = self._obtener_importancia_variables()
        return metadatos

    def _obtener_importancia_variables(self) -> list[dict]:
        """Agrupa la importancia del clasificador por variable original."""
        if self.pipeline is None:
            return []
        preprocessor = self.pipeline.named_steps.get("preprocessor")
        classifier = self.pipeline.named_steps.get("classifier")
        if preprocessor is None or classifier is None:
            return []

        feature_names = preprocessor.get_feature_names_out()
        if hasattr(classifier, "feature_importances_"):
            importances = np.asarray(classifier.feature_importances_, dtype=float)
        elif hasattr(classifier, "coef_"):
            importances = np.abs(np.asarray(classifier.coef_, dtype=float)[0])
            suma = importances.sum()
            if suma > 0:
                importances = importances / suma
        else:
            return []
        variables = [
            "distancia_km", "tiempo_estimado_dias", "tiempo_preparacion_horas",
            "cantidad_productos", "peso_kg", "departamento_destino",
            "zona_logistica", "modo_transporte", "tipo_envio", "prioridad",
            "dia_semana", "carga_logistica",
        ]
        acumuladas = {variable: 0.0 for variable in variables}
        for nombre, importancia in zip(feature_names, importances):
            nombre_original = nombre.split("__", 1)[-1]
            variable = next((v for v in variables if nombre_original == v or nombre_original.startswith(f"{v}_")), None)
            if variable:
                acumuladas[variable] += float(importancia)

        etiquetas = {
            "distancia_km": "Distancia (km)",
            "tiempo_estimado_dias": "Tiempo estimado",
            "tiempo_preparacion_horas": "Tiempo preparación",
            "cantidad_productos": "Cantidad de productos",
            "peso_kg": "Peso del pedido",
            "departamento_destino": "Departamento de destino",
            "zona_logistica": "Zona logística",
            "modo_transporte": "Modo de transporte",
            "tipo_envio": "Tipo de envío",
            "prioridad": "Prioridad",
            "dia_semana": "Día de la semana",
            "carga_logistica": "Carga logística",
        }
        return [
            {"feature": etiquetas[variable], "importance": round(importancia * 100, 2)}
            for variable, importancia in sorted(acumuladas.items(), key=lambda item: item[1], reverse=True)
            if importancia > 0
        ]

# Instancia Singleton
ml_service = MLService()
