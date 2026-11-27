"""Un entrenamiento a la vez por proceso, con progreso consultable por la UI."""
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Any
from uuid import uuid4

from ml.training.train_model import entrenar_y_evaluar

_lock = Lock()
_estado: dict[str, Any] = {"status": "idle", "progress": 0, "events": [], "result": None}


def estado_entrenamiento() -> dict[str, Any]:
    with _lock:
        return deepcopy(_estado)


def iniciar_entrenamiento() -> dict[str, Any]:
    with _lock:
        if _estado["status"] == "running":
            raise RuntimeError("Ya hay un entrenamiento en curso.")
        _estado.clear()
        _estado.update(status="running", progress=0, events=[], result=None,
                       job_id=str(uuid4()), error=None)
        inicial = deepcopy(_estado)
    try:
        Thread(target=_ejecutar, daemon=True, name="ml-training").start()
    except Exception:
        with _lock:
            _estado.update(status="failed", error="No se pudo iniciar el entrenamiento.")
        raise
    return inicial


def _ejecutar() -> None:
    def progreso(mensaje: str, porcentaje: int) -> None:
        with _lock:
            _estado["progress"] = porcentaje
            _estado["events"].append({
                "message": mensaje,
                "time": datetime.now(timezone.utc).isoformat(),
            })
    try:
        # La interfaz evalúa candidatos; la activación sigue siendo una acción explícita.
        reporte = entrenar_y_evaluar(activar_si_mejora=False, progreso=progreso)
        with _lock:
            _estado.update(status="completed", progress=100, result={
                "model_name": reporte["model_name"],
                "metrics": reporte["best_model_metrics"],
                "comparison": reporte["comparison"],
                "approved": reporte["quality_gate"]["approved"],
                "activated": reporte["quality_gate"]["activated"],
            })
    except Exception as exc:
        with _lock:
            _estado.update(status="failed", error=f"No se pudo completar el entrenamiento: {exc}")
