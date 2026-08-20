import os
import json
import joblib
import pandas as pd
from app.schemas.prediction import PredictionInput

class MLService:
    def __init__(self):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.model_path = os.path.join(BASE_DIR, "ml", "models", "modelo_entrega.joblib")
        self.metadata_path = os.path.join(BASE_DIR, "ml", "models", "metadatos_modelo.json")
        self.pipeline = None
        self._cargar_modelo()

    def _cargar_modelo(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Modelo no encontrado en: {self.model_path}. Entrena el modelo con train_model.py")
        self.pipeline = joblib.load(self.model_path)

    def predecir_retraso(self, datos: PredictionInput) -> dict:
        pipeline = self.pipeline
        if pipeline is None:
            raise RuntimeError("El modelo no está cargado")

        # 1. Definir los datos en un diccionario
        datos_dict = {
            'region': str(datos.region),
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
                'region', 'tipo_envio', 'distancia_km', 'tiempo_estimado_dias',
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
        prediccion = int(probabilidad >= 0.50)

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
            "nivel_riesgo": nivel_riesgo
        }

    def obtener_metadatos(self) -> dict:
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadatos no encontrados en: {self.metadata_path}")
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)

# Instancia Singleton
ml_service = MLService()