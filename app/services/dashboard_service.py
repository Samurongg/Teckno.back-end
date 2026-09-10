from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.order import Order
from app.models.prediction_log import PredictionLog

class DashboardService:
    @staticmethod
    def obtener_datos_dashboard(db: Session) -> dict:
        total_pedidos = db.query(Order).count()
        tardias = db.query(Order).filter(Order.entrega_tardia == 1).count()
        a_tiempo = total_pedidos - tardias
        tasa_retraso = round((tardias / total_pedidos * 100), 2) if total_pedidos > 0 else 0.0
        
        predicciones_totales = db.query(PredictionLog).count()

        # Nivel de riesgo general del negocio
        if tasa_retraso >= 25.0:
            riesgo_gral = "ALTO"
        elif tasa_retraso >= 15.0:
            riesgo_gral = "MEDIO"
        else:
            riesgo_gral = "BAJO"

        # Evolución mensual (agrupación por prefijo YYYY-MM de fecha_pedido)
        meses_query = (
            db.query(
                func.substr(Order.fecha_pedido, 1, 7).label("mes"),
                func.count(Order.order_id).label("total"),
                func.sum(Order.entrega_tardia).label("tardios")
            )
            .group_by("mes")
            .order_by("mes")
            .all()
        )

        evolucion = [
            {"mes": r.mes, "total": r.total, "tardios": int(r.tardios or 0)}
            for r in meses_query
        ]

        departamento_query = (
            db.query(
                Order.departamento_destino.label("departamento"),
                func.count(Order.order_id).label("total"),
                func.sum(Order.entrega_tardia).label("tardios")
            )
            .group_by(Order.departamento_destino)
            .all()
        )

        departamentos = [
            {
                "departamento": r.departamento,
                "total": r.total,
                "tardios": int(r.tardios or 0),
                "tasa_retraso": round(((r.tardios or 0) / r.total * 100), 2)
            }
            for r in departamento_query
        ]

        zona_query = (
            db.query(
                Order.zona_logistica.label("zona"),
                func.count(Order.order_id).label("total"),
                func.sum(Order.entrega_tardia).label("tardios"),
            )
            .group_by(Order.zona_logistica)
            .all()
        )
        zonas = [
            {
                "zona": r.zona,
                "total": r.total,
                "tardios": int(r.tardios or 0),
                "tasa_retraso": round(((r.tardios or 0) / r.total * 100), 2),
            }
            for r in zona_query
        ]

        tipo_envio_query = (
            db.query(
                Order.tipo_envio.label("tipo"),
                func.count(Order.order_id).label("total"),
                func.sum(Order.entrega_tardia).label("tardios"),
            )
            .group_by(Order.tipo_envio)
            .all()
        )
        tipos_envio = [
            {
                "tipo": r.tipo,
                "tasa_retraso": round(((r.tardios or 0) / r.total * 100), 2),
            }
            for r in tipo_envio_query
        ]

        return {
            "kpis": {
                "total_pedidos": total_pedidos,
                "entregas_a_tiempo": a_tiempo,
                "entregas_tardias": tardias,
                "tasa_retrasos": tasa_retraso,
                "predicciones_realizadas": predicciones_totales,
                "nivel_riesgo_general": riesgo_gral
            },
            "evolucion_mensual": evolucion,
            "pedidos_por_departamento": departamentos,
            "pedidos_por_zona": zonas,
            "pedidos_por_tipo_envio": tipos_envio,
        }

    @staticmethod
    def obtener_analitica_avanzada(db: Session) -> dict:
        def agrupar_por(columna):
            res = (
                db.query(
                    columna.label("categoria"),
                    func.count(Order.order_id).label("total"),
                    func.sum(Order.entrega_tardia).label("tardios")
                )
                .group_by(columna)
                .all()
            )
            return [
                {
                    "categoria": str(r.categoria),
                    "total_pedidos": r.total,
                    "entregas_tardias": int(r.tardios or 0),
                    "tasa_retraso": round(((r.tardios or 0) / r.total * 100), 2)
                }
                for r in res
            ]

        # Segmentación por rangos de distancia
        rangos_distancia = [
            ("0-200 km", Order.distancia_km <= 200),
            ("201-500 km", (Order.distancia_km > 200) & (Order.distancia_km <= 500)),
            ("501-900 km", (Order.distancia_km > 500) & (Order.distancia_km <= 900)),
            ("901-1300 km", (Order.distancia_km > 900) & (Order.distancia_km <= 1300)),
            ("> 1300 km", Order.distancia_km > 1300),
        ]
        distancias = [
            {
                "rango": rango,
                "total": db.query(Order).filter(filtro).count(),
                "tardios": db.query(Order)
                .filter(filtro, Order.entrega_tardia == 1)
                .count(),
            }
            for rango, filtro in rangos_distancia
        ]

        rangos_preparacion = [
            ("0-4 h", Order.tiempo_preparacion_horas <= 4),
            ("4-8 h", (Order.tiempo_preparacion_horas > 4) & (Order.tiempo_preparacion_horas <= 8)),
            ("8-12 h", (Order.tiempo_preparacion_horas > 8) & (Order.tiempo_preparacion_horas <= 12)),
            ("> 12 h", Order.tiempo_preparacion_horas > 12),
        ]
        tiempos_preparacion = [
            {
                "rango": rango,
                "total": db.query(Order).filter(filtro).count(),
                "tardios": db.query(Order).filter(filtro, Order.entrega_tardia == 1).count(),
            }
            for rango, filtro in rangos_preparacion
        ]

        meses_query = (
            db.query(
                func.substr(Order.fecha_pedido, 1, 7).label("mes"),
                func.count(Order.order_id).label("total"),
                func.sum(Order.entrega_tardia).label("tardios"),
            )
            .group_by("mes")
            .order_by("mes")
            .all()
        )
        tendencia_mensual = [
            {
                "mes": r.mes,
                "total": r.total,
                "tasa_retraso": round(((r.tardios or 0) / r.total * 100), 2),
            }
            for r in meses_query
        ]

        return {
            "por_departamento": agrupar_por(Order.departamento_destino),
            "por_zona_logistica": agrupar_por(Order.zona_logistica),
            "por_modo_transporte": agrupar_por(Order.modo_transporte),
            "por_tipo_envio": agrupar_por(Order.tipo_envio),
            "por_carga_logistica": agrupar_por(Order.carga_logistica),
            "por_prioridad": agrupar_por(Order.prioridad),
            "distribucion_distancias": distancias,
            "distribucion_tiempo_preparacion": tiempos_preparacion,
            "tendencia_mensual": tendencia_mensual,
        }
