from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1.endpoints.catalogos import execute_catalog_query


WRITE_ENABLED = os.getenv("QUANTIA_ENGINE_V18_WRITE", "0") == "1"

EXPECTED_TOTAL = 101
EXPECTED_ACTIVE = 99
EXPECTED_INACTIVE = {"EST-008", "EST-010"}

# Condiciones ya cerradas en migraciones previas.
STRUCTURE_CONTEXT: dict[str, dict[str, Any]] = {
    "EST-001": {"sistemaEstructural": ["tradicional", "mixta"]},
    "EST-002": {"sistemaEstructural": ["tradicional", "mixta"]},
    "EST-003": {"sistemaEstructural": ["concreto_reforzado", "mixta"]},
    "EST-004": {"sistemaEstructural": ["concreto_reforzado", "mixta"]},
    "EST-005": {"tipoLosa": "maciza"},
    "EST-006": {"tipoLosa": "vigueta_bovedilla"},
    "EST-007": {"tipoLosa": "aligerada_caseton_nervaduras"},
}

FOUNDATION_CONTEXT: dict[str, dict[str, Any]] = {
    "CIM-002": {"tipoCimentacion": "zapata_corrida"},
    "CIM-003": {
        "tipoCimentacion": "zapata_aislada_trabe_liga",
        "varianteZapata": "080",
    },
    "CIM-003A": {
        "tipoCimentacion": "zapata_aislada_trabe_liga",
        "varianteZapata": "100",
    },
    "CIM-004": {"tipoCimentacion": "zapata_aislada_trabe_liga"},
    # CIM-005 intencionalmente sin context_conditions.
    "CIM-005A": {"tipoCimentacion": "zapata_corrida"},
    "CIM-006": {"tipoCimentacion": "mamposteria_corrida"},
}

# Se conserva como contrato declarativo dentro de condition_json.
# El backend seguirá usando el filtro temporal hasta soportar/validar esta
# condición en _evaluate_activation_rule.
INSTALLATION_SERVICE: dict[str, str] = {
    "HID": "agua",
    "ELE": "energia",
    "SAN": "drenaje",
    "PLU": "drenaje",
}


SPEC_DIRECT_FIELDS = {
    "spec_code",
    "spec_name",
    "application_mode",
    "output_mode",
    "applies_first_level_only",
    "requires_project_definition",
    "allows_user_override",
    "default_quantity_mode",
    "technical_scope_text",
    "inference_strategy",
    "parameter_defaults",
    "parameter_rules",
    "validations_json",
    "dependencies_json",
    "exclusions_json",
    "metadata_json",
    "quantity_multiplier",
    "notes",
    "execution_priority",
}

RULE_COMPARE_FIELDS = [
    "code",
    "concept_spec_id",
    "rule_name",
    "priority",
    "activation_type",
    "type_intervention",
    "scope",
    "trigger_json",
    "condition_json",
    "derivation_json",
    "invalidates_json",
    "alerts_json",
    "output_action_json",
    "stop_on_error",
    "is_active",
]


# ---------------------------------------------------------------------------
# Adaptador contrato lógico V1.8 -> esquema físico Supabase
# ---------------------------------------------------------------------------

ALLOWED_APPLICATION_MODES = {
    "automatico",
    "semi_automatico",
    "manual_controlado",
}
ALLOWED_OUTPUT_MODES = {"base", "tecnico", "oficial", "ambos"}
ALLOWED_QUANTITY_MODES = {"ml", "m2", "m3", "pza", "salida", "tramite", "otro"}
ALLOWED_ACTIVATION_TYPES = {
    "obligatoria",
    "derivada",
    "condicional",
    "manual_controlada",
}
ALLOWED_SCOPES = {"obra_negra", "obra_gris", "obra_blanca"}
ALLOWED_TYPE_INTERVENTIONS = {"obra_nueva", "remodelacion", "complementaria"}

APPLICATION_MODE_MAP = {
    # Contrato lógico V1.8
    "automatico": "automatico",
    "asistido": "semi_automatico",
    # Valores físicos aceptados (idempotencia)
    "semi_automatico": "semi_automatico",
    "manual_controlado": "manual_controlado",
    # Alias defensivos
    "manual": "manual_controlado",
    "manual_controlada": "manual_controlado",

    # Estado lógico exclusivo de registros históricos inactivos.
    # Supabase no dispone de "bloqueado" como enum físico; se conserva
    # la semántica con is_active=False y se usa manual_controlado como
    # representación física no automática.
    "bloqueado": "manual_controlado",
}

FORMULA_TO_PHYSICAL_QUANTITY_MODE = {
    "F_ML_DIRECTA": "ml",
    "F_M2_DIRECTA": "m2",
    "F_M3_DIRECTA": "m3",
    "F_PZA_DIRECTA": "pza",
    "F_SALIDA_DIRECTA": "salida",
    "F_TRAMITE_DIRECTA": "tramite",
    "F_OTRO_DIRECTA": "otro",
}

# Estos campos son contrato V1.8; NO deben mezclarse con residuos BASE-TXT.
CONTRACT_JSON_DEFAULTS = {
    "parameter_defaults": {},
    "parameter_rules": {},
    "validations_json": {},
    "dependencies_json": {},
    "exclusions_json": [],
    "metadata_json": {},
}


def map_application_mode(value: Any, *, code: str) -> str:
    logical = str(value or "").strip().lower()
    physical = APPLICATION_MODE_MAP.get(logical)
    if physical not in ALLOWED_APPLICATION_MODES:
        raise RuntimeError(
            f"{code}: application_mode lógico {value!r} no tiene mapeo físico válido."
        )
    return physical


def map_output_mode(value: Any, *, code: str) -> str:
    physical = str(value or "").strip().lower()
    if physical not in ALLOWED_OUTPUT_MODES:
        raise RuntimeError(
            f"{code}: output_mode {value!r} no está permitido por Supabase."
        )
    return physical


def map_quantity_mode_from_formula(formula_code: str, *, code: str) -> str:
    physical = FORMULA_TO_PHYSICAL_QUANTITY_MODE.get(formula_code)
    if physical not in ALLOWED_QUANTITY_MODES:
        raise RuntimeError(
            f"{code}: fórmula {formula_code!r} no tiene default_quantity_mode físico."
        )
    return physical


def validate_physical_payloads(
    desired_specs: dict[str, dict[str, Any]],
    desired_rules: dict[str, dict[str, Any] | None],
) -> None:
    """Preflight completo: ninguna escritura comienza si algún CHECK fallaría."""
    errors: list[str] = []

    for code, spec in desired_specs.items():
        application_mode = spec.get("application_mode")
        output_mode = spec.get("output_mode")
        quantity_mode = spec.get("default_quantity_mode")

        if application_mode not in ALLOWED_APPLICATION_MODES:
            errors.append(f"{code}: application_mode={application_mode!r}")
        if output_mode not in ALLOWED_OUTPUT_MODES:
            errors.append(f"{code}: output_mode={output_mode!r}")
        if quantity_mode not in ALLOWED_QUANTITY_MODES:
            errors.append(f"{code}: default_quantity_mode={quantity_mode!r}")

        parameter_rules = spec.get("parameter_rules")
        if isinstance(parameter_rules, dict) and "unit_code" in parameter_rules:
            errors.append(
                f"{code}: parameter_rules conserva unit_code heredado BASE-TXT="
                f"{parameter_rules.get('unit_code')!r}"
            )

    for code, rule in desired_rules.items():
        if rule is None:
            continue
        activation_type = rule.get("activation_type")
        scope = rule.get("scope")
        type_intervention = rule.get("type_intervention")

        if activation_type not in ALLOWED_ACTIVATION_TYPES:
            errors.append(f"{code}: activation_type={activation_type!r}")
        if scope is not None and scope not in ALLOWED_SCOPES:
            errors.append(f"{code}: scope={scope!r}")
        if (
            type_intervention is not None
            and type_intervention not in ALLOWED_TYPE_INTERVENTIONS
        ):
            errors.append(f"{code}: type_intervention={type_intervention!r}")

    if errors:
        raise RuntimeError(
            "Preflight físico Supabase falló; NO se permite escribir:\n- "
            + "\n- ".join(errors[:80])
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migración global declarativa Quantia V1.8 (DRY-RUN por defecto)."
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        help="Ruta al JSON definitivo de reglas V1.8.",
    )
    return parser.parse_args()


def resolve_rules_path(explicit: Path | None) -> Path:
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.extend(
        [
            BACKEND_ROOT / "data" / "engine" / "Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json",
            BACKEND_ROOT / "data" / "Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json",
            BACKEND_ROOT / "Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json",
            Path.cwd() / "Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json",
        ]
    )
    for path in candidates:
        path = path.expanduser().resolve()
        if path.exists():
            return path
    raise FileNotFoundError(
        "No se encontró Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json. "
        "Use --rules RUTA."
    )


def extract_rule_items(document: Any) -> list[dict[str, Any]]:
    """Extrae de forma tolerante objetos {concept_id, code, spec, activation_rule}."""
    found: dict[str, dict[str, Any]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if {
                "concept_id",
                "code",
                "spec",
            }.issubset(node.keys()) and isinstance(node.get("spec"), dict):
                code = str(node.get("code") or "").strip().upper()
                if code:
                    if code in found and found[code] != node:
                        raise RuntimeError(f"Regla duplicada distinta para {code} en JSON.")
                    found[code] = node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    return [found[key] for key in sorted(found)]


def fetch_rows(table: str, select_fields: str = "*") -> list[dict[str, Any]]:
    return execute_catalog_query(
        lambda client: (
            client.table(table)
            .select(select_fields)
            .execute()
            .data
            or []
        ),
        operation=f"fetch_{table}",
        critical=True,
    )


def deep_merge(base: Any, overlay: Any) -> Any:
    """Conserva extras existentes y da prioridad al contrato V1.8."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        result = copy.deepcopy(base)
        for key, value in overlay.items():
            result[key] = deep_merge(result.get(key), value)
        return result
    return copy.deepcopy(overlay)


def changed_fields(
    current: dict[str, Any],
    desired: dict[str, Any],
    fields: list[str] | set[str],
) -> list[str]:
    return [
        field
        for field in fields
        if current.get(field) != desired.get(field)
    ]


def normalize_unit(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "m²": "m2",
        "m³": "m3",
        "salida": "sal",
        "sal": "sal",
        "pieza": "pza",
        "pza": "pza",
        "ml": "ml",
        "m2": "m2",
        "m3": "m3",
        "kg": "kg",
        "tramite": "tramite",
        "trámite": "tramite",
        "otro": "otro",
    }
    return aliases.get(text, text)


def expected_context_conditions(code: str) -> dict[str, Any] | None:
    if code in STRUCTURE_CONTEXT:
        return STRUCTURE_CONTEXT[code]
    if code in FOUNDATION_CONTEXT:
        return FOUNDATION_CONTEXT[code]
    return None


def build_spec_payload(
    *,
    item: dict[str, Any],
    current: dict[str, Any],
    formula_by_code: dict[str, dict[str, Any]],
    profile_by_code: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source = item["spec"]
    code = str(item["code"]).upper()
    formula_code = str(source.get("formula_code") or "").strip()
    profile_code = str(source.get("spec_profile_code") or "").strip()

    if formula_code not in formula_by_code:
        raise RuntimeError(
            f"{code}: fórmula {formula_code!r} no existe en engine_formulas."
        )
    if profile_code not in profile_by_code:
        raise RuntimeError(
            f"{code}: perfil {profile_code!r} no existe en engine_spec_profiles."
        )

    # Partimos de la fila actual para conservar columnas que no forman parte
    # del contrato V1.8 (FK técnicas, timestamps, etc.), pero los campos del
    # contrato se reemplazan de forma explícita. No se hace deep_merge con
    # BASE-TXT para evitar residuos como parameter_rules.unit_code.
    desired = copy.deepcopy(current)

    for field in SPEC_DIRECT_FIELDS:
        if field in CONTRACT_JSON_DEFAULTS:
            desired[field] = copy.deepcopy(
                source.get(field, CONTRACT_JSON_DEFAULTS[field])
            )
            continue
        if field in source:
            desired[field] = copy.deepcopy(source[field])

    # Adaptación de enums lógicos del JSON a los CHECK físicos de Supabase.
    desired["application_mode"] = map_application_mode(
        source.get("application_mode"),
        code=code,
    )
    desired["output_mode"] = map_output_mode(
        source.get("output_mode"),
        code=code,
    )
    desired["default_quantity_mode"] = map_quantity_mode_from_formula(
        formula_code,
        code=code,
    )

    # Trazabilidad: conservar el modo lógico del contrato sin forzarlo en la
    # columna física default_quantity_mode.
    metadata = copy.deepcopy(desired.get("metadata_json") or {})
    metadata["logical_default_quantity_mode"] = source.get(
        "default_quantity_mode"
    )
    metadata["physical_default_quantity_mode"] = desired[
        "default_quantity_mode"
    ]
    metadata["logical_application_mode"] = source.get("application_mode")
    metadata["physical_application_mode"] = desired["application_mode"]

    if source.get("application_mode") == "bloqueado":
        metadata["inactive_blocked_contract"] = True

    desired["metadata_json"] = metadata

    desired["formula_id"] = str(formula_by_code[formula_code]["id"])
    desired["spec_profile_id"] = str(profile_by_code[profile_code]["id"])
    desired["is_active"] = bool(item.get("is_active"))

    return desired

def build_rule_payload(
    *,
    item: dict[str, Any],
    spec_id: str,
    current: dict[str, Any] | None,
) -> dict[str, Any] | None:
    code = str(item["code"]).upper()
    if not bool(item.get("is_active")):
        return None

    source = item.get("activation_rule")
    if not isinstance(source, dict):
        raise RuntimeError(f"{code}: falta activation_rule en contrato V1.8.")

    condition = copy.deepcopy(source.get("condition_json") or {})

    # No perder condiciones que ya quedaron cerradas en Estructura/Cimentación.
    current_context = (
        ((current or {}).get("condition_json") or {}).get("context_conditions")
    )
    known_context = expected_context_conditions(code)
    if current_context:
        condition["context_conditions"] = copy.deepcopy(current_context)
    elif known_context:
        condition["context_conditions"] = copy.deepcopy(known_context)

    # Contrato tri-state de Instalaciones. No activa por ausencia:
    # la semántica se implementará/validará en el motor antes de retirar
    # _filter_instalaciones_by_services.
    family = code.split("-", 1)[0]
    if family in INSTALLATION_SERVICE:
        condition["service_requirement"] = {
            "container": "serviciosInstalaciones",
            "key": INSTALLATION_SERVICE[family],
            "required_value": True,
            "missing_state": "unknown",
            "false_state": "NOT_APPLICABLE",
        }

    desired = {
        "code": str(source.get("code") or f"ACT_{code.replace('-', '_')}_V18"),
        "concept_spec_id": spec_id,
        "rule_name": str(source.get("rule_name") or f"Activación V1.8 — {code}"),
        "priority": source.get("priority"),
        # Mapeo físico válido para el CHECK de Supabase.
        "activation_type": "condicional",
        # Los valores lógicos 'vivienda'/'project' del contrato no pertenecen
        # a los enums físicos auditados de estas columnas.
        "type_intervention": None,
        "scope": None,
        "trigger_json": copy.deepcopy(source.get("trigger_json") or {}),
        "condition_json": condition,
        "derivation_json": copy.deepcopy(source.get("derivation_json") or {}),
        "invalidates_json": copy.deepcopy(source.get("invalidates_json") or []),
        "alerts_json": copy.deepcopy(source.get("alerts_json") or []),
        "output_action_json": copy.deepcopy(source.get("output_action_json") or {}),
        "stop_on_error": bool(source.get("stop_on_error")),
        "is_active": True,
    }
    return desired


def validate_contract(
    *,
    items: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    units: list[dict[str, Any]],
    formulas: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> None:
    if len(items) != EXPECTED_TOTAL:
        raise RuntimeError(
            f"JSON definitivo contiene {len(items)} reglas; esperadas {EXPECTED_TOTAL}."
        )

    if len(concepts) != EXPECTED_TOTAL:
        raise RuntimeError(
            f"catalog_concepts contiene {len(concepts)} filas; esperadas {EXPECTED_TOTAL}."
        )

    json_by_code = {str(x["code"]).upper(): x for x in items}
    db_by_code = {str(x["code"]).upper(): x for x in concepts}

    if len(json_by_code) != EXPECTED_TOTAL:
        raise RuntimeError("JSON contiene claves duplicadas.")
    if len(db_by_code) != EXPECTED_TOTAL:
        raise RuntimeError("catalog_concepts contiene claves duplicadas.")

    if set(json_by_code) != set(db_by_code):
        missing_json = sorted(set(db_by_code) - set(json_by_code))
        extra_json = sorted(set(json_by_code) - set(db_by_code))
        raise RuntimeError(
            f"Claves JSON/BD no coinciden. Faltan JSON={missing_json}; extras JSON={extra_json}"
        )

    inactive_db = {
        code for code, row in db_by_code.items() if not bool(row.get("is_active"))
    }
    inactive_json = {
        code for code, row in json_by_code.items() if not bool(row.get("is_active"))
    }
    if inactive_db != EXPECTED_INACTIVE or inactive_json != EXPECTED_INACTIVE:
        raise RuntimeError(
            f"Inactivos no coinciden. BD={sorted(inactive_db)}, JSON={sorted(inactive_json)}"
        )

    active_count = sum(bool(row.get("is_active")) for row in concepts)
    if active_count != EXPECTED_ACTIVE:
        raise RuntimeError(
            f"Activos BD={active_count}; esperados {EXPECTED_ACTIVE}."
        )

    unit_by_id = {str(row["id"]): row for row in units}
    formula_codes = {str(row.get("code")) for row in formulas}
    profile_codes = {str(row.get("code")) for row in profiles}

    errors: list[str] = []
    for code in sorted(db_by_code):
        db = db_by_code[code]
        rule = json_by_code[code]
        if str(db["id"]) != str(rule["concept_id"]):
            errors.append(
                f"{code}: concept_id JSON={rule['concept_id']} BD={db['id']}"
            )

        spec = rule["spec"]
        formula_code = str(spec.get("formula_code") or "")
        profile_code = str(spec.get("spec_profile_code") or "")
        if formula_code not in formula_codes:
            errors.append(f"{code}: falta fórmula {formula_code}")
        if profile_code not in profile_codes:
            errors.append(f"{code}: falta perfil {profile_code}")

        if str(db.get("default_formula_code") or "") != formula_code:
            errors.append(
                f"{code}: default_formula_code BD={db.get('default_formula_code')!r} "
                f"JSON={formula_code!r}"
            )

        json_mode = str(spec.get("default_quantity_mode") or "")
        db_mode = str(db.get("quantification_mode") or "")
        if json_mode != db_mode:
            errors.append(
                f"{code}: quantification_mode BD={db_mode!r} JSON={json_mode!r}"
            )

        unit = unit_by_id.get(str(db.get("unit_id")), {})
        catalog_unit = normalize_unit(unit.get("code") or unit.get("symbol"))
        derivation = (rule.get("activation_rule") or {}).get("derivation_json") or {}
        json_unit = normalize_unit(derivation.get("unit"))
        if json_unit and catalog_unit and json_unit != catalog_unit:
            errors.append(
                f"{code}: unidad catálogo={catalog_unit!r}, contrato={json_unit!r}"
            )

    if errors:
        preview = "\n- ".join(errors[:30])
        suffix = "" if len(errors) <= 30 else f"\n... y {len(errors)-30} errores más."
        raise RuntimeError(
            "Contrato V1.8 no coincide con catálogo actual:\n- "
            + preview
            + suffix
        )


def main() -> None:
    args = parse_args()
    rules_path = resolve_rules_path(args.rules)

    print("Migración global del motor Quantia V1.8")
    print("Modo:", "ESCRITURA" if WRITE_ENABLED else "DRY-RUN")
    print("Contrato:", rules_path)

    with rules_path.open("r", encoding="utf-8-sig") as fh:
        document = json.load(fh)
    items = extract_rule_items(document)

    concepts = fetch_rows(
        "catalog_concepts",
        "id,code,is_active,unit_id,quantification_mode,default_formula_code",
    )
    units = fetch_rows("catalog_units", "id,code,symbol,is_active")
    formulas = fetch_rows("engine_formulas", "*")
    profiles = fetch_rows("engine_spec_profiles", "*")
    specs = fetch_rows("engine_concept_specs", "*")
    rules = fetch_rows("engine_activation_rules", "*")

    validate_contract(
        items=items,
        concepts=concepts,
        units=units,
        formulas=formulas,
        profiles=profiles,
    )

    concept_by_code = {str(x["code"]).upper(): x for x in concepts}
    formula_by_code = {str(x["code"]): x for x in formulas}
    profile_by_code = {str(x["code"]): x for x in profiles}

    specs_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in specs:
        specs_by_concept[str(row.get("concept_id"))].append(row)

    spec_errors = []
    current_spec_by_code: dict[str, dict[str, Any]] = {}
    for code, concept in concept_by_code.items():
        rows = specs_by_concept.get(str(concept["id"]), [])
        if len(rows) != 1:
            spec_errors.append(f"{code}: specs={len(rows)}; esperado=1")
        elif rows:
            current_spec_by_code[code] = rows[0]
    if spec_errors:
        raise RuntimeError(
            "No se puede migrar con specs faltantes/duplicados:\n- "
            + "\n- ".join(spec_errors)
        )

    rules_by_spec: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rules:
        rules_by_spec[str(row.get("concept_spec_id"))].append(row)

    duplicate_rules = {
        spec_id: rows
        for spec_id, rows in rules_by_spec.items()
        if len(rows) > 1
    }
    if duplicate_rules:
        details = []
        for spec_id, rows in duplicate_rules.items():
            details.append(
                f"{spec_id}: " + ", ".join(str(x.get("code")) for x in rows)
            )
        raise RuntimeError(
            "Hay specs con más de una activation_rule. Resolver antes de migrar:\n- "
            + "\n- ".join(details)
        )

    items_by_code = {str(x["code"]).upper(): x for x in items}

    desired_specs: dict[str, dict[str, Any]] = {}
    desired_rules: dict[str, dict[str, Any] | None] = {}
    current_rules: dict[str, dict[str, Any] | None] = {}

    for code in sorted(items_by_code):
        item = items_by_code[code]
        current_spec = current_spec_by_code[code]
        desired_spec = build_spec_payload(
            item=item,
            current=current_spec,
            formula_by_code=formula_by_code,
            profile_by_code=profile_by_code,
        )
        desired_specs[code] = desired_spec

        spec_id = str(current_spec["id"])
        existing_rule_rows = rules_by_spec.get(spec_id, [])
        current_rule = existing_rule_rows[0] if existing_rule_rows else None
        current_rules[code] = current_rule

        desired_rules[code] = build_rule_payload(
            item=item,
            spec_id=spec_id,
            current=current_rule,
        )

    # Preflight contra todos los CHECK constraints auditados.
    # Si algo no es físicamente válido, aborta antes del primer UPDATE/INSERT.
    validate_physical_payloads(desired_specs, desired_rules)

    print("\n--- AUDITORÍA GLOBAL ---")
    print("Preflight CHECK constraints: OK")
    print(f"Contrato JSON:        {len(items)}/{EXPECTED_TOTAL}")
    print(f"Catálogo Supabase:    {len(concepts)}/{EXPECTED_TOTAL}")
    print(f"Specs existentes:     {len(current_spec_by_code)}/{EXPECTED_TOTAL}")
    print(f"Conceptos activos:    {EXPECTED_ACTIVE}/{EXPECTED_ACTIVE}")
    print(f"Inactivos:            {', '.join(sorted(EXPECTED_INACTIVE))}")

    spec_updates: list[str] = []
    spec_unchanged: list[str] = []
    rule_inserts: list[str] = []
    rule_updates: list[str] = []
    rule_unchanged: list[str] = []
    rule_inactive_updates: list[str] = []

    changed_counter: Counter[str] = Counter()

    print("\n--- DELTA SPECS ---")
    for code in sorted(items_by_code):
        current = current_spec_by_code[code]
        desired = desired_specs[code]
        fields = changed_fields(
            current,
            desired,
            list(SPEC_DIRECT_FIELDS) + [
                "formula_id",
                "spec_profile_id",
                "is_active",
            ],
        )
        if fields:
            spec_updates.append(code)
            for field in fields:
                changed_counter[field] += 1
            print(f"~ {code}: {', '.join(fields)}")
        else:
            spec_unchanged.append(code)

    print("\n--- DELTA ACTIVATION RULES ---")
    for code in sorted(items_by_code):
        current = current_rules[code]
        desired = desired_rules[code]

        if desired is None:
            if current and bool(current.get("is_active")):
                rule_inactive_updates.append(code)
                print(f"~ {code}: desactivar regla existente")
            continue

        if current is None:
            rule_inserts.append(code)
            print(f"+ {code}: INSERT {desired['code']}")
            continue

        fields = changed_fields(current, desired, RULE_COMPARE_FIELDS)
        if fields:
            rule_updates.append(code)
            print(f"~ {code}: UPDATE -> {', '.join(fields)}")
        else:
            rule_unchanged.append(code)

    print("\n--- RESUMEN DEL DRY-RUN ---")
    print(f"Specs a actualizar:       {len(spec_updates)}")
    print(f"Specs sin cambios:        {len(spec_unchanged)}")
    print(f"Rules a insertar:         {len(rule_inserts)}")
    print(f"Rules a actualizar:       {len(rule_updates)}")
    print(f"Rules sin cambios:        {len(rule_unchanged)}")
    print(f"Rules a desactivar:       {len(rule_inactive_updates)}")
    if changed_counter:
        print("Campos spec más afectados:")
        for field, count in changed_counter.most_common():
            print(f"  {field}: {count}")

    if not WRITE_ENABLED:
        print("\nDRY-RUN correcto. No se modificó Supabase.")
        print("Revisar este resumen antes de habilitar escritura.")
        print('Para escribir: $env:QUANTIA_ENGINE_V18_WRITE="1"')
        return

    print("\n--- ESCRITURA CONTROLADA ---")

    for code in spec_updates:
        current = current_spec_by_code[code]
        desired = desired_specs[code]
        payload = {
            key: value
            for key, value in desired.items()
            if key not in {
                "id",
                "concept_id",
                "created_at",
                "updated_at",
            }
        }
        execute_catalog_query(
            lambda client, spec_id=current["id"], payload=payload: (
                client.table("engine_concept_specs")
                .update(payload)
                .eq("id", spec_id)
                .execute()
                .data
                or []
            ),
            operation=f"update_engine_spec_global_{code}",
            critical=True,
        )

    for code in rule_inserts:
        payload = desired_rules[code]
        assert payload is not None
        execute_catalog_query(
            lambda client, payload=payload: (
                client.table("engine_activation_rules")
                .insert(payload)
                .execute()
                .data
                or []
            ),
            operation=f"insert_activation_global_{code}",
            critical=True,
        )

    for code in rule_updates:
        current = current_rules[code]
        payload = desired_rules[code]
        assert current is not None and payload is not None
        execute_catalog_query(
            lambda client, rule_id=current["id"], payload=payload: (
                client.table("engine_activation_rules")
                .update(payload)
                .eq("id", rule_id)
                .execute()
                .data
                or []
            ),
            operation=f"update_activation_global_{code}",
            critical=True,
        )

    for code in rule_inactive_updates:
        current = current_rules[code]
        assert current is not None
        execute_catalog_query(
            lambda client, rule_id=current["id"]: (
                client.table("engine_activation_rules")
                .update({"is_active": False})
                .eq("id", rule_id)
                .execute()
                .data
                or []
            ),
            operation=f"deactivate_activation_global_{code}",
            critical=True,
        )

    print("\n--- VERIFICACIÓN POSTERIOR ---")
    specs_after = fetch_rows("engine_concept_specs", "*")
    rules_after = fetch_rows("engine_activation_rules", "*")

    after_specs_by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in specs_after:
        after_specs_by_concept[str(row.get("concept_id"))].append(row)

    active_rules_by_spec: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rules_after:
        if bool(row.get("is_active")):
            active_rules_by_spec[str(row.get("concept_spec_id"))].append(row)

    errors: list[str] = []
    active_strategy_count = 0
    active_rule_count = 0

    for code in sorted(items_by_code):
        concept = concept_by_code[code]
        rows = after_specs_by_concept.get(str(concept["id"]), [])
        if len(rows) != 1:
            errors.append(f"{code}: specs después={len(rows)}")
            continue

        spec = rows[0]
        expected = desired_specs[code]
        fields = changed_fields(
            spec,
            expected,
            list(SPEC_DIRECT_FIELDS) + [
                "formula_id",
                "spec_profile_id",
                "is_active",
            ],
        )
        if fields:
            errors.append(f"{code}: spec difiere en {', '.join(fields)}")

        if bool(concept.get("is_active")):
            if not spec.get("inference_strategy"):
                errors.append(f"{code}: inference_strategy vacío")
            else:
                active_strategy_count += 1

            active_rule_rows = active_rules_by_spec.get(str(spec["id"]), [])
            if len(active_rule_rows) != 1:
                errors.append(
                    f"{code}: activation rules activas={len(active_rule_rows)}"
                )
            else:
                active_rule_count += 1
                desired_rule = desired_rules[code]
                assert desired_rule is not None
                fields = changed_fields(
                    active_rule_rows[0],
                    desired_rule,
                    RULE_COMPARE_FIELDS,
                )
                if fields:
                    errors.append(
                        f"{code}: activation_rule difiere en {', '.join(fields)}"
                    )
        else:
            if bool(spec.get("is_active")):
                errors.append(f"{code}: spec debe quedar inactivo")
            if active_rules_by_spec.get(str(spec["id"])):
                errors.append(f"{code}: no debe tener activation_rule activa")

    if active_strategy_count != EXPECTED_ACTIVE:
        errors.append(
            f"Estrategias activas={active_strategy_count}; esperadas={EXPECTED_ACTIVE}"
        )
    if active_rule_count != EXPECTED_ACTIVE:
        errors.append(
            f"Activation rules activas={active_rule_count}; esperadas={EXPECTED_ACTIVE}"
        )

    if errors:
        raise RuntimeError(
            "Verificación posterior falló:\n- " + "\n- ".join(errors[:60])
        )

    print("Specs V1.8:                 101/101")
    print("Estrategias conceptos activos: 99/99")
    print("Activation rules activas:      99/99")
    print("Inactivos sin ejecución:       EST-008, EST-010")
    print("UUID de specs existentes:      conservados")
    print("Migración global V1.8 correcta.")


if __name__ == "__main__":
    main()
