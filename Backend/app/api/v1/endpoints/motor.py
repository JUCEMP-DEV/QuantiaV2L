from fastapi import APIRouter, HTTPException

from app.schemas.resultados import (
    Consumo04Response,
    SimulacionModuloRequest,
    SimulacionModuloResponse,
    SimulacionPreliminaresRequest,
    SimulacionPreliminaresResponse,
)
from app.services.motor_simulation_service import simulate_modulo, simulate_preliminares
from app.services.spatial_consumption import build_consumption


router = APIRouter(prefix="/motor", tags=["motor"])


@router.post("/consumo-04", response_model=Consumo04Response)
def consumo_04(payload: SimulacionModuloRequest):
    """Export the same deterministic model/derivations used in simulation."""
    return build_consumption(payload.estructura_espacial, payload.datos_generales_obra, payload.controles)


@router.post("/preliminares/simular", response_model=SimulacionPreliminaresResponse)
def simular_preliminares(payload: SimulacionPreliminaresRequest):
    try:
        return simulate_preliminares(
            preliminares=payload.preliminares,
            datos_generales_obra=payload.datos_generales_obra,
            estructura_espacial=payload.estructura_espacial,
            colindancias_recorrido=payload.colindancias_recorrido,
            source_name=payload.source_name,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"No se pudo simular preliminares: {exc}") from exc


@router.post("/modulos/{module_key}/simular", response_model=SimulacionModuloResponse)
def simular_modulo(module_key: str, payload: SimulacionModuloRequest):
    try:
        return simulate_modulo(
            module_key=module_key,
            controles=payload.controles,
            selected_concept_keys=payload.selected_concept_keys,
            force_select_all=payload.force_select_all,
            preliminares=payload.preliminares,
            datos_generales_obra=payload.datos_generales_obra,
            estructura_espacial=payload.estructura_espacial,
            colindancias_recorrido=payload.colindancias_recorrido,
            source_name=payload.source_name,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"No se pudo simular modulo '{module_key}': {exc}") from exc
