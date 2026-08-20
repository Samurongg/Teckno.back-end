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

        # Pedidos por región
        region_query = (
            db.query(
                Order.region,
                func.count(Order.order_id).label("total"),
                func.sum(Order.entrega_tardia).label("tardios")
            )
            .group_by(Order.region)
            .all()
        )

        regiones = [
            {
                "region": r.region,
                "total": r.total,
                "tardios": int(r.tardios or 0),
                "tasa_retraso": round(((r.tardios or 0) / r.total * 100), 2)
            }
            for r in region_query
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
            "pedidos_por_region": regiones
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
        distancias = [
            {"rango": "0-100 km", "total": db.query(Order).filter(Order.distancia_km <= 100).count(), "tardios": db.query(Order).filter(Order.distancia_km <= 100, Order.entrega_tardia == 1).count()},
            {"rango": "101-250 km", "total": db.query(Order).filter(Order.distancia_km > 100, Order.distancia_km <= 250).count(), "tardios": db.query(Order).filter(Order.distancia_km > 100, Order.distancia_km <= 250, Order.entrega_tardia == 1).count()},
            {"rango": "251-450 km", "total": db.query(Order).filter(Order.distancia_km > 250).count(), "tardios": db.query(Order).filter(Order.distancia_km > 250, Order.entrega_tardia == 1).count()}
        ]

        return {
            "por_region": agrupar_por(Order.region),
            "por_tipo_envio": agrupar_por(Order.tipo_envio),
            "por_carga_logistica": agrupar_por(Order.carga_logistica),
            "por_prioridad": agrupar_por(Order.prioridad),
            "distribucion_distancias": distancias
        }