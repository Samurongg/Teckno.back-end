import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def ejecutar_eda():
    ruta_csv = 'ml/data/pedidos.csv'
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No se encontró {ruta_csv}. Ejecuta generate_dataset.py primero.")
        
    df = pd.read_csv(ruta_csv)
    os.makedirs('ml/reports/figures', exist_ok=True)
    
    print("=" * 60)
    print("TECNOMARKET ANALYTICS - REPORTE EXPLORATORIO DE DATOS (EDA)")
    print("=" * 60)
    
    # 1. Estructura y tipos
    print("\n1. INFORMACIÓN GENERAL DEL DATASET:")
    print(df.info())
    
    # 2. Resumen estadístico de variables numéricas
    print("\n2. ESTADÍSTICAS DESCRIPTIVAS (NUMÉRICAS):")
    print(df.describe().round(2))
    
    # 3. Tasa de retraso por categoría
    print("\n3. TASA DE RETRASOS POR CATEGORÍA:")
    for col in ['region', 'tipo_envio', 'carga_logistica', 'prioridad']:
        tasa = df.groupby(col)['entrega_tardia'].agg(total='count', tasa_retraso='mean')
        tasa['tasa_retraso'] = (tasa['tasa_retraso'] * 100).round(2).astype(str) + '%'
        print(f"\n--- Desglose por {col} ---")
        print(tasa)
        
    # 4. Generación de Gráficos Diagnósticos
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Gráfico A: Distribución del Target
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    target_counts = df['entrega_tardia'].value_counts()
    axes[0].pie(target_counts, labels=['A Tiempo (0)', 'Tardío (1)'], autopct='%1.1f%%', colors=['#10B981', '#EF4444'], startangle=90)
    axes[0].set_title('Distribución de Variable Objetivo (Target)')
    
    # Gráfico B: Distancia vs Retraso
    sns.boxplot(x='entrega_tardia', y='distancia_km', data=df, ax=axes[1], palette=['#10B981', '#EF4444'])
    axes[1].set_title('Distancia (km) vs Estado de Entrega')
    axes[1].set_xticklabels(['A Tiempo (0)', 'Tardío (1)'])
    plt.tight_layout()
    plt.savefig('ml/reports/figures/target_y_distancia.png', dpi=300)
    plt.close()
    
    # Gráfico C: Heatmap de Correlación Numérica
    plt.figure(figsize=(8, 6))
    cols_num = ['distancia_km', 'tiempo_estimado_dias', 'tiempo_preparacion_horas', 'cantidad_productos', 'peso_kg', 'entrega_tardia']
    sns.heatmap(df[cols_num].corr(), annot=True, cmap='coolwarm', fmt='.2f', vmin=-1, vmax=1)
    plt.title('Matriz de Correlación Numérica')
    plt.tight_layout()
    plt.savefig('ml/reports/figures/matriz_correlacion.png', dpi=300)
    plt.close()
    
    print("\n Gráficos generados exitosamente en: ml/reports/figures/")

if __name__ == '__main__':
    ejecutar_eda()