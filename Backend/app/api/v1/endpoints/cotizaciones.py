from app.core.document_auth import DocumentPrincipal, get_document_principal
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.supabase_client import get_supabase_admin_client
from app.schemas.cotizacion import (
    CotizacionItem,
    CotizacionListResponse,
    CotizacionResponse,
    CotizacionUpsertRequest,
)

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


def resolve_user_id(email: str) -> str | None:
    client = get_supabase_admin_client()
    result = client.table("app_users").select("id").eq("email", email).limit(1).execute()
    if result.data:
        return str(result.data[0].get("id"))
    return None


def to_quote_item(row: dict) -> CotizacionItem:
    return CotizacionItem(
        id=str(row.get("id") or ""),
        user_id=row.get("user_id"),
        user_email=row.get("user_email") or "",
        status=row.get("status") or "draft",
        modulo=row.get("modulo") or "vivienda",
        subtipo=row.get("subtipo"),
        payload_json=row.get("payload_json") or {},
        resumen_json=row.get("resumen_json") or {},
        total=float(row.get("total") or 0),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.post("", response_model=CotizacionResponse)
def upsert_cotizacion(payload: CotizacionUpsertRequest, principal: DocumentPrincipal = Depends(get_document_principal)):
    client = get_supabase_admin_client()
    user_email = str(principal.email or "").strip().lower()
    if not user_email or str(payload.user_email).lower() != user_email:
        raise HTTPException(status_code=403, detail="La cotizacion debe pertenecer a tu sesion.")
    user_id = principal.user_id

    record = {
        "user_id": user_id,
        "user_email": user_email,
        "status": payload.status,
        "modulo": payload.modulo,
        "subtipo": payload.subtipo,
        "payload_json": payload.payload_json,
        "resumen_json": payload.resumen_json,
        "total": payload.total,
    }

    if payload.quote_id:
        updated = (
            client.table("app_cotizaciones")
            .update(record)
            .eq("id", payload.quote_id).eq("user_email", user_email)
            .execute()
        )
        if not updated.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontro la cotizacion para actualizar.",
            )

        refreshed = client.table("app_cotizaciones").select("*").eq("id", payload.quote_id).eq("user_email", user_email).limit(1).execute()
        if not refreshed.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La cotizacion se actualizo pero no se pudo recuperar.",
            )
        return {"ok": True, "quote": to_quote_item(refreshed.data[0])}

    created = client.table("app_cotizaciones").insert(record).execute()
    if not created.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar la cotizacion.",
        )

    quote_id = str(created.data[0].get("id") or "")
    if not quote_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La cotizacion se guardo sin identificador.",
        )

    refreshed = client.table("app_cotizaciones").select("*").eq("id", quote_id).eq("user_email", str(principal.email or "").lower()).limit(1).execute()
    if not refreshed.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La cotizacion se guardo pero no se pudo recuperar.",
        )
    return {"ok": True, "quote": to_quote_item(refreshed.data[0])}


@router.get("", response_model=CotizacionListResponse)
def list_cotizaciones(
    user_email: str | None = Query(default=None),
    principal: DocumentPrincipal = Depends(get_document_principal),
    limit: int = Query(default=20, ge=1, le=200),
):
    client = get_supabase_admin_client()
    normalized_email = str(principal.email or "").strip().lower()
    if not normalized_email or (user_email and user_email.strip().lower() != normalized_email):
        raise HTTPException(status_code=403, detail="Solo puedes consultar tus proyectos.")

    result = (
        client.table("app_cotizaciones")
        .select("*")
        .eq("user_email", normalized_email)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    return {"ok": True, "quotes": [to_quote_item(row) for row in rows]}


@router.get("/{quote_id}", response_model=CotizacionResponse)
def get_cotizacion(quote_id: str, principal: DocumentPrincipal = Depends(get_document_principal)):
    client = get_supabase_admin_client()
    result = client.table("app_cotizaciones").select("*").eq("id", quote_id).eq("user_email", str(principal.email or "").lower()).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotizacion no encontrada.")
    return {"ok": True, "quote": to_quote_item(result.data[0])}
