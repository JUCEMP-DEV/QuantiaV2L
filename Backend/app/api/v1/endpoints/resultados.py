from fastapi import APIRouter, HTTPException

from app.schemas.resultados import InferenciaRequest, InferenciaResponse
from app.services.result_service import run_motor_inferencia_v4


router = APIRouter(prefix="/resultados", tags=["resultados"])


@router.post("/inferir", response_model=InferenciaResponse)
def inferir_resultado(payload: InferenciaRequest):
    try:
        return run_motor_inferencia_v4(
            preliminares=payload.preliminares,
            modulos=payload.modulos,
            datos_generales_obra=payload.datos_generales_obra,
            variables_entrada=payload.variables_entrada,
            estructura_espacial=payload.estructura_espacial,
            colindancias_recorrido=payload.colindancias_recorrido,
            validacion_espacial=payload.validacion_espacial,
            required_module_keys=payload.required_module_keys,
            perfil=payload.perfil,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
