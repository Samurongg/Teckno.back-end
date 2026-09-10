# TecnoMarket Analytics — Backend

## Descripción del trabajo

TecnoMarket Analytics es una plataforma de analítica logística y Machine Learning. Estudia pedidos históricos, identifica patrones de retraso y estima el riesgo de que una entrega llegue tarde.

No es una tienda virtual ni reemplaza el sistema donde se crean los pedidos. Los pedidos provienen de una fuente externa; este backend los centraliza para el dashboard, los reportes y las predicciones del frontend.

## Funcionalidades

- Consulta paginada y filtrable de pedidos históricos.
- Dashboard con indicadores, distribución geográfica y evolución mensual.
- Analítica nacional por departamento, zona logística, transporte, distancia y preparación.
- Predicción de retraso mediante un pipeline de Machine Learning.
- Registro de cada predicción para auditoría.
- Metadatos, métricas e importancia de variables del modelo.
- Carga automática del dataset inicial en SQLite cuando la base está vacía.

## Tecnologías

| Tecnología | Uso |
| --- | --- |
| Python | Lenguaje del servicio |
| FastAPI | API REST y documentación OpenAPI |
| SQLAlchemy | Acceso a datos |
| SQLite | Base local de desarrollo |
| Pandas / NumPy | Procesamiento de datos |
| scikit-learn | Entrenamiento e inferencia del modelo |
| Joblib | Persistencia del pipeline entrenado |

## Estructura

```text
app/
  routes/       Endpoints de la API
  schemas/      Validación y contratos de respuesta
  services/     Lógica de analítica y Machine Learning
  models/       Tablas SQLite
  database/     Conexión y carga inicial
ml/
  data/         Dataset de pedidos
  models/       Modelo y metadatos exportados
  training/     Generación, análisis y entrenamiento
```

## Instalación y ejecución

Requiere Python 3.11 o superior.

```powershell
cd C:\Users\adria\Desktop\TECKNOBACK\Teckno.back-end
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

La API se abrirá en `http://127.0.0.1:8000`. Consulta la documentación interactiva en `http://127.0.0.1:8000/docs`.

Al primer inicio se crean las tablas y se cargan los pedidos desde `ml/data/pedidos.csv`. Si la base ya contiene pedidos, no se duplican.

## Manual de uso

Este backend se usa normalmente desde el frontend. Para revisar o probar la API de forma directa, usa `/docs`.

| Acción | Endpoint | Método |
| --- | --- | --- |
| Confirmar que el servicio funciona | `/api/health` | GET |
| Ver indicadores del dashboard | `/api/dashboard` | GET |
| Consultar pedidos | `/api/orders?page=1&page_size=10` | GET |
| Ver detalle de un pedido | `/api/orders/{order_id}` | GET |
| Analizar retrasos | `/api/analytics` | GET |
| Consultar modelo y métricas | `/api/model/info` | GET |
| Calcular una predicción | `/api/predict` | POST |

### Ejemplo de predicción

En `/docs`, abre `POST /api/predict`, pulsa **Try it out** e ingresa:

```json
{
  "departamento_destino": "Arequipa",
  "modo_transporte": "Terrestre",
  "tipo_envio": "Estándar",
  "distancia_km": 1025,
  "tiempo_estimado_dias": 6,
  "tiempo_preparacion_horas": 8,
  "cantidad_productos": 4,
  "peso_kg": 6.5,
  "prioridad": "Media",
  "dia_semana": "Miércoles",
  "carga_logistica": "Alta"
}
```

La respuesta incluye la clasificación, la probabilidad de retraso y el nivel de riesgo.

El centro operativo se encuentra en Lima. Cada departamento pertenece a una zona logística y posee un rango aproximado de distancia operativa. La API rechaza combinaciones imposibles, como un envío nacional de larga distancia con servicio `Mismo Día`, y deriva la zona logística a partir del departamento para evitar inconsistencias.

## Entrenamiento y validación del modelo

El proyecto incluye un dataset sintético nacional para fines académicos y de demostración. Contiene departamento de destino, zona logística, modo de transporte y distancia aproximada desde Lima. Para regenerarlo, comprobar su calidad y comparar modelos sin modificar el modelo activo:

```powershell
python ml/training/generate_dataset.py
python ml/training/eda_analysis.py
python ml/training/train_model.py
```

El entrenamiento separa los pedidos cronológicamente en 70% para entrenamiento, 15% para validación y 15% para prueba final. La validación selecciona el algoritmo y el umbral; la prueba final se utiliza una sola vez para comprobar su generalización. El resultado completo se guarda en `ml/reports/comparacion_modelos.json`.

Para activar automáticamente el candidato únicamente cuando supere los mínimos de calidad y al modelo vigente:

```powershell
python ml/training/train_model.py --activate-if-better
```

Antes de reemplazarlo se crea un respaldo local en `ml/models/backups/`. El modelo activo y sus datos reproducibles quedan en `ml/models/modelo_entrega.joblib` y `ml/models/metadatos_modelo.json`. Después de activar un modelo, reinicia el backend para que vuelva a cargarlo.

Para un uso real, sustituye progresivamente el conjunto sintético por pedidos históricos anonimizados y conserva la misma evaluación temporal.

## Configuración CORS

`CORS_ALLOWED_ORIGINS` admite una lista de orígenes separada por comas. En desarrollo se permiten puertos locales; antes de desplegar, configura exclusivamente los dominios autorizados.
