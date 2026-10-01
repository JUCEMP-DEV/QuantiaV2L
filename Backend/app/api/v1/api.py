from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.catalogos import router as catalogos_router
from app.api.v1.endpoints.cotizaciones import router as cotizaciones_router
from app.api.v1.endpoints.documentos import router as documentos_router
from app.api.v1.endpoints.motor import router as motor_router
from app.api.v1.endpoints.resultados import router as resultados_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(cotizaciones_router)
api_router.include_router(catalogos_router)
api_router.include_router(documentos_router)
api_router.include_router(motor_router)
api_router.include_router(resultados_router)
