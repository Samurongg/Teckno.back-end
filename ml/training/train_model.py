import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

def entrenar_y_evaluar():
    ruta_csv = 'ml/data/pedidos.csv'
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"Archivo {ruta_csv} no encontrado.")
        
    df = pd.read_csv(ruta_csv)
    
    # 1. Definición de variables
    # Excluimos order_id (ID) y fecha_pedido (conservada en BD para filtros temporales)
    y = df['entrega_tardia']
    X = df.drop(columns=['order_id', 'fecha_pedido', 'entrega_tardia'])
    
    columnas_numericas = [
        'distancia_km', 
        'tiempo_estimado_dias', 
        'tiempo_preparacion_horas', 
        'cantidad_productos', 
        'peso_kg'
    ]
    
    columnas_categoricas = [
        'region', 
        'tipo_envio', 
        'prioridad', 
        'dia_semana', 
        'carga_logistica'
    ]
    
    # 2. Preprocesador modular (Scikit-Learn ColumnTransformer)
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), columnas_numericas),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), columnas_categoricas)
        ]
    )
    
    # 3. Train/Test Split estratificado (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    # 4. Modelos a evaluar
    candidatos = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced'),
        'Decision Tree': DecisionTreeClassifier(max_depth=6, random_state=42, class_weight='balanced'),
        'Random Forest': RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42, class_weight='balanced')
    }
    
    metricas_modelos = {}
    pipelines_entrenados = {}
    
    print("\n" + "=" * 60)
    print("EVALUACIÓN COMPARATIVA DE MODELOS ML")
    print("=" * 60)
    
    for nombre, clasificador in candidatos.items():
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', clasificador)
        ])
        
        # Ajuste estricto sobre Train Set
        pipeline.fit(X_train, y_train)
        pipelines_entrenados[nombre] = pipeline
        
        # Predicción sobre Test Set
        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        cm = confusion_matrix(y_test, y_pred).tolist()
        
        metricas_modelos[nombre] = {
            'accuracy': round(float(acc), 4),
            'precision': round(float(prec), 4),
            'recall': round(float(rec), 4),
            'f1_score': round(float(f1), 4),
            'roc_auc': round(float(auc), 4),
            'confusion_matrix': cm
        }
        
        print(f"\nModelo: {nombre}")
        print(f" - ROC-AUC:   {auc:.4f}")
        print(f" - F1-Score:  {f1:.4f}")
        print(f" - Recall:    {rec:.4f}")
        print(f" - Precision: {prec:.4f}")
        print(f" - Accuracy:  {acc:.4f}")
        
    # 5. Selección del mejor modelo (criterio combinado ROC-AUC y F1-Score)
    mejor_nombre = max(metricas_modelos, key=lambda k: (metricas_modelos[k]['roc_auc'] + metricas_modelos[k]['f1_score']))
    mejor_pipeline = pipelines_entrenados[mejor_nombre]
    
    # 6. Exportar artefactos
    os.makedirs('ml/models', exist_ok=True)
    
    ruta_modelo = 'ml/models/modelo_entrega.joblib'
    joblib.dump(mejor_pipeline, ruta_modelo)
    
    metadatos = {
        'model_name': mejor_nombre,
        'model_version': 'v2.4.1',
        'trained_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_samples': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'target_distribution': {
            'ontime_0': int((df['entrega_tardia'] == 0).sum()),
            'delayed_1': int((df['entrega_tardia'] == 1).sum())
        },
        'features': {
            'numerical': columnas_numericas,
            'categorical': columnas_categoricas
        },
        'best_model_metrics': metricas_modelos[mejor_nombre],
        'comparison': metricas_modelos
    }
    
    ruta_metadatos = 'ml/models/metadatos_modelo.json'
    with open(ruta_metadatos, 'w', encoding='utf-8') as f:
        json.dump(metadatos, f, indent=4, ensure_ascii=False)
        
    print("\n" + "=" * 60)
    print(f"MODELO GANADOR: {mejor_nombre}")
    print(f"Pipeline exportado en: {ruta_modelo}")
    print(f"Metadatos guardados en: {ruta_metadatos}")
    print("=" * 60)

if __name__ == '__main__':
    entrenar_y_evaluar()