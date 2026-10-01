import logging
import time
from typing import Callable, TypeVar

from fastapi import APIRouter, HTTPException, Query

from app.core.supabase_client import get_supabase_admin_client
from app.schemas.conceptos import CatalogConceptListResponse

router = APIRouter(prefix="/catalogos", tags=["catalogos"])
logger = logging.getLogger(__name__)
T = TypeVar("T")


MODULE_PARTIDAS: dict[str, list[str]] = {
    "preliminares": ["PRE"],
    "cimentacion": ["CIM"],
    "estructura": ["EST"],
    "albanileria": ["ALB"],
    "instalaciones": ["HID", "SAN", "PLU", "ELE", "GAS"],
    "acabados": ["ACA"],
    "complementarios_y_equipamiento": ["CAR", "CAN", "HER", "MSA", "COM"],
}


def safe_text(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def execute_catalog_query(
    query_builder: Callable[[object], T],
    *,
    operation: str,
    critical: bool,
    default: T | None = None,
    attempts: int = 3,
) -> T:
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            client = get_supabase_admin_client(force_refresh=attempt > 0)
            return query_builder(client)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.25 * (attempt + 1))

    if critical:
        raise RuntimeError(f"Fallo en {operation}: {last_error}") from last_error

    logger.warning("Consulta opcional fallida en %s: %s", operation, last_error)
    return default  # type: ignore[return-value]


@router.get("/modulos/{module_key}/conceptos", response_model=CatalogConceptListResponse)
def get_catalog_concepts_by_module(
    module_key: str,
    limit: int = Query(default=250, ge=1, le=2000),
    source_name: str = Query(default="CONSTRUBASE_PU_48_CONSTRUCTOR"),
):
    normalized_module = safe_text(module_key).lower()
    partida_codes = MODULE_PARTIDAS.get(normalized_module)
    if not partida_codes:
        raise HTTPException(status_code=404, detail="Modulo no soportado para consulta de catalogo.")

    try:
        partidas_rows = execute_catalog_query(
            lambda client: (
                client.table("catalog_partidas")
                .select("id,code,name")
                .in_("code", partida_codes)
                .eq("is_active", True)
                .execute()
                .data
                or []
            ),
            operation="catalog_partidas",
            critical=True,
        )
        if not partidas_rows:
            return {
                "ok": True,
                "module_key": normalized_module,
                "source_name": source_name,
                "count": 0,
                "concepts": [],
            }

        partida_id_by_code = {safe_text(row.get("code")): safe_text(row.get("id")) for row in partidas_rows}
        partida_name_by_id = {safe_text(row.get("id")): safe_text(row.get("name")) for row in partidas_rows}
        partida_code_by_id = {safe_text(row.get("id")): safe_text(row.get("code")) for row in partidas_rows}
        partida_ids = [value for value in partida_id_by_code.values() if value]

        concepts_rows = execute_catalog_query(
            lambda client: (
                client.table("catalog_concepts")
                .select(
                    "id,code,technical_description,official_description,unit_id,partida_id,"
                    "default_formula_code,quantification_mode,is_active"
                )
                .in_("partida_id", partida_ids)
                .eq("is_active", True)
                .limit(limit)
                .execute()
                .data
                or []
            ),
            operation="catalog_concepts",
            critical=True,
        )
        if not concepts_rows:
            return {
                "ok": True,
                "module_key": normalized_module,
                "source_name": source_name,
                "count": 0,
                "concepts": [],
            }

        unit_ids = list(
            {
                safe_text(row.get("unit_id"))
                for row in concepts_rows
                if safe_text(row.get("unit_id"))
            }
        )
        concept_ids = [safe_text(row.get("id")) for row in concepts_rows if safe_text(row.get("id"))]

        units_map: dict[str, dict] = {}
        if unit_ids:
            units_rows = execute_catalog_query(
                lambda client: (
                    client.table("catalog_units").select("id,code,symbol").in_("id", unit_ids).execute().data or []
                ),
                operation="catalog_units",
                critical=False,
                default=[],
            )
            units_map = {safe_text(row.get("id")): row for row in units_rows}

        specs_by_concept_id: dict[str, dict] = {}
        spec_ids: list[str] = []
        if concept_ids:
            spec_rows = execute_catalog_query(
                lambda client: (
                    client.table("engine_concept_specs")
                    .select("id,concept_id,spec_code,is_active")
                    .in_("concept_id", concept_ids)
                    .eq("is_active", True)
                    .execute()
                    .data
                    or []
                ),
                operation="engine_concept_specs",
                critical=False,
                default=[],
            )
            for row in spec_rows:
                concept_id = safe_text(row.get("concept_id"))
                spec_id = safe_text(row.get("id"))
                if not concept_id or not spec_id:
                    continue
                previous = specs_by_concept_id.get(concept_id)
                if previous is None or safe_text(row.get("spec_code")) < safe_text(previous.get("spec_code"), "zzzz"):
                    specs_by_concept_id[concept_id] = row
                spec_ids.append(spec_id)

        prices_by_spec_id: dict[str, dict] = {}
        if spec_ids:
            price_rows = execute_catalog_query(
                lambda client: (
                    client.table("price_concept_bases")
                    .select("concept_spec_id,source_name,unit_price,is_active,updated_at")
                    .in_("concept_spec_id", list(set(spec_ids)))
                    .eq("is_active", True)
                    .execute()
                    .data
                    or []
                ),
                operation="price_concept_bases",
                critical=False,
                default=[],
            )

            for row in price_rows:
                spec_id = safe_text(row.get("concept_spec_id"))
                if not spec_id:
                    continue
                current = prices_by_spec_id.get(spec_id)
                row_source = safe_text(row.get("source_name"))

                if row_source == source_name:
                    prices_by_spec_id[spec_id] = row
                    continue

                if current is None:
                    prices_by_spec_id[spec_id] = row

        concepts_payload: list[dict] = []
        for row in concepts_rows:
            concept_id = safe_text(row.get("id"))
            unit = units_map.get(safe_text(row.get("unit_id")), {})
            spec = specs_by_concept_id.get(concept_id, {})
            price = prices_by_spec_id.get(safe_text(spec.get("id")), {})
            price_value = row.get("unit_price") if isinstance(row.get("unit_price"), (int, float)) else None
            if price_value is None:
                price_value = price.get("unit_price")

            concepts_payload.append(
                {
                    "code": safe_text(row.get("code")),
                    "technical_description": safe_text(row.get("technical_description")),
                    "official_description": safe_text(row.get("official_description")),
                    "unit_code": safe_text(unit.get("code"), "OTRO"),
                    "unit_symbol": safe_text(unit.get("symbol"), "u"),
                    "partida_code": partida_code_by_id.get(safe_text(row.get("partida_id")), ""),
                    "partida_name": partida_name_by_id.get(safe_text(row.get("partida_id")), ""),
                    "default_formula_code": safe_text(row.get("default_formula_code")) or None,
                    "quantification_mode": safe_text(row.get("quantification_mode")) or None,
                    "spec_code": safe_text(spec.get("spec_code")) or None,
                    "unit_price": float(price_value or 0),
                    "source_name": safe_text(price.get("source_name")) or None,
                }
            )

        concepts_payload.sort(key=lambda item: item.get("code") or "")

        return {
            "ok": True,
            "module_key": normalized_module,
            "source_name": source_name,
            "count": len(concepts_payload),
            "concepts": concepts_payload,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar a BD para catalogos: {exc}",
        ) from exc


@router.get("/reglas-catalogos")
def get_rules_catalogs():
    """Public catalog projection; credentials and user records stay server-side."""
    try:
        client = get_supabase_admin_client()
        rules = client.table("engine_activation_rules").select(
            "id,code,rule_name,activation_type,priority,is_active,type_intervention,scope"
        ).order("id").limit(200).execute()
        concepts = client.table("catalog_concepts").select(
            "id,code,technical_description,official_description,is_active,finish_level"
        ).order("id").limit(500).execute()
        return {"reglas": rules.data or [], "catalogos": concepts.data or [], "errors": []}
    except Exception:
        raise HTTPException(status_code=503, detail="No fue posible consultar reglas y catalogos.") from None
