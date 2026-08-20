import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generar_dataset_pedidos(n_muestras: int = 5000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    
    # 1. Identificadores únicos y fechas
    order_ids = [f"ORD-{10001 + i}" for i in range(n_muestras)]
    fecha_base = datetime(2025, 1, 1)
    fechas_dt = [fecha_base + timedelta(days=int(np.random.uniform(0, 365))) for _ in range(n_muestras)]
    fechas_str = [f.strftime('%Y-%m-%d') for f in fechas_dt]
    
    # Derivación estricta de dia_semana
    dias_map = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
    dias_semana = [dias_map[f.weekday()] for f in fechas_dt]
    
    # 2. Variables categóricas logísticas
    regiones = np.random.choice(
        ['Centro', 'Norte', 'Sur', 'Este', 'Oeste'], 
        size=n_muestras, 
        p=[0.35, 0.25, 0.20, 0.12, 0.08]
    )
    
    tipos_envio = np.random.choice(
        ['Estándar', 'Express', 'Mismo Día'], 
        size=n_muestras, 
        p=[0.55, 0.35, 0.10]
    )
    
    prioridades = np.random.choice(
        ['Baja', 'Media', 'Alta'], 
        size=n_muestras, 
        p=[0.30, 0.50, 0.20]
    )
    
    cargas_logisticas = np.random.choice(
        ['Baja', 'Media', 'Alta'], 
        size=n_muestras, 
        p=[0.25, 0.50, 0.25]
    )
    
    # 3. Tiempos estimados condicionados al tipo de envío
    tiempos_estimados = []
    for tipo in tipos_envio:
        if tipo == 'Mismo Día':
            tiempos_estimados.append(1)
        elif tipo == 'Express':
            tiempos_estimados.append(int(np.random.choice([1, 2], p=[0.30, 0.70])))
        else:  # Estándar
            tiempos_estimados.append(int(np.random.choice([3, 4, 5, 6], p=[0.20, 0.40, 0.30, 0.10])))
    tiempos_estimados = np.array(tiempos_estimados)
    
    # 4. Variables numéricas correlacionadas
    distancias_km = np.round(np.random.uniform(5.0, 450.0, size=n_muestras), 2)
    cantidades = np.random.randint(1, 13, size=n_muestras)
    
    # Peso correlacionado con cantidad + variación
    pesos_kg = np.round(cantidades * np.random.uniform(0.6, 2.5, size=n_muestras) + np.random.normal(0.4, 0.15, size=n_muestras), 2)
    pesos_kg = np.maximum(pesos_kg, 0.5)
    
    # Tiempo de preparación correlacionado con ítems y peso
    tiempos_prep = (0.70 * cantidades) + (0.30 * pesos_kg) + np.random.normal(1.5, 0.5, size=n_muestras)
    tiempos_prep = np.round(np.maximum(tiempos_prep, 0.5), 2)
    
    # 5. Cálculo probabilístico de riesgo latente
    norm_dist = distancias_km / 450.0
    norm_prep = tiempos_prep / np.max(tiempos_prep)
    norm_peso = pesos_kg / np.max(pesos_kg)
    
    score_base = (0.35 * norm_dist) + (0.30 * norm_prep) + (0.10 * norm_peso)
    
    penalizacion_carga = np.where(cargas_logisticas == 'Alta', 0.22, np.where(cargas_logisticas == 'Baja', -0.10, 0.0))
    penalizacion_mismo_dia = np.where((tipos_envio == 'Mismo Día') & (distancias_km > 75.0), 0.35, 0.0)
    penalizacion_express = np.where((tipos_envio == 'Express') & (distancias_km > 260.0), 0.20, 0.0)
    bonificacion_prioridad = np.where(prioridades == 'Alta', -0.12, 0.0)
    
    score_total = score_base + penalizacion_carga + penalizacion_mismo_dia + penalizacion_express + bonificacion_prioridad
    
    # Función sigmoide para scoring continuo
    prob_retraso = 1 / (1 + np.exp(-(score_total - 0.40) * 5.8))
    
    # Ruido gaussiano para evitar fronteras deterministas
    ruido = np.random.normal(0, 0.04, size=n_muestras)
    prob_final = np.clip(prob_retraso + ruido, 0.001, 0.999)
    
    # Asignación exacta de 875 tardías (1) y 4,125 a tiempo (0)
    k_tardios = 875
    indices_ordenados = np.argsort(-prob_final)
    
    entrega_tardia = np.zeros(n_muestras, dtype=int)
    entrega_tardia[indices_ordenados[:k_tardios]] = 1
    
    return pd.DataFrame({
        'order_id': order_ids,
        'fecha_pedido': fechas_str,
        'region': regiones,
        'tipo_envio': tipos_envio,
        'distancia_km': distancias_km,
        'tiempo_estimado_dias': tiempos_estimados,
        'tiempo_preparacion_horas': tiempos_prep,
        'cantidad_productos': cantidades,
        'peso_kg': pesos_kg,
        'prioridad': prioridades,
        'dia_semana': dias_semana,
        'carga_logistica': cargas_logisticas,
        'entrega_tardia': entrega_tardia
    })

if __name__ == '__main__':
    os.makedirs('ml/data', exist_ok=True)
    df = generar_dataset_pedidos()
    ruta_salida = 'ml/data/pedidos.csv'
    df.to_csv(ruta_salida, index=False)
    print(f"Dataset generado exitosamente en: {ruta_salida}")
    print(f"Dimensiones: {df.shape}")
    print(f"Distribución del target:\n{df['entrega_tardia'].value_counts(normalize=False)}")