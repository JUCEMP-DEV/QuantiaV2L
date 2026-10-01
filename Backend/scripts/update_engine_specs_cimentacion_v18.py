from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1.endpoints.catalogos import execute_catalog_query


TARGET_CODES = [
    "CIM-002",
    "CIM-003",
    "CIM-003A",
    "CIM-004",
    "CIM-005",
    "CIM-005A",
    "CIM-006",
]

EXPECTED_CIM003A_ID = "c1497b86-9857-4170-b01b-f47b7fab5b56"

FORMULA_CODES = {
    "ml": "F_ML_DIRECTA",
    "pza": "F_PZA_DIRECTA",
}

EXPECTED_FORMULA_IDS = {
    "F_ML_DIRECTA": "8d2c5aa0-a209-44d4-9c00-c6b09ca0e158",
    "F_PZA_DIRECTA": "869938d1-db60-4413-aac7-d5c3e1b3c1ba",
}

UNIT_BY_CODE = {
    "CIM-002": "ml",
    "CIM-003": "pza",
    "CIM-003A": "pza",
    "CIM-004": "pza",
    "CIM-005": "ml",
    "CIM-005A": "ml",
    "CIM-006": "ml",
}

STRATEGY_BY_CODE = {
    "CIM-002": "longitud_zapata_corrida",
    "CIM-003": "conteo_zapata_080",
    "CIM-003A": "conteo_zapata_100",
    "CIM-004": "conteo_dados_confirmados",
    "CIM-005": "longitud_dala_desplante",
    "CIM-005A": "longitud_contratrabe_20x30",
    "CIM-006": "longitud_muro_cimentacion",
}

DEPENDENCIES_BY_CODE = {
    "CIM-002": ["PRE-003", "CIM-001"],
    "CIM-003": ["PRE-003", "CIM-001"],
    "CIM-003A": ["PRE-003", "CIM-001"],
    "CIM-004": ["CIM-003|CIM-003A"],
    "CIM-005": ["PRE-003"],
    "CIM-005A": ["CIM-002"],
    "CIM-006": ["PRE-003", "CIM-001"],
}

EXCLUSIONS_BY_CODE = {
    "CIM-002": [],
    "CIM-003": [],
    "CIM-003A": [],
    "CIM-004": [],
    "CIM-005": [],
    "CIM-005A": ["CIM-005", "CIM-002"],
    "CIM-006": [],
}

TECHNICAL_SCOPE_BY_CODE = {
    "CIM-002": (
        "Zapata corrida de concreto reforzado. La cuantificación corresponde "
        "a la longitud confirmada de los tramos aplicables del proyecto."
    ),
    "CIM-003": (
        "Zapata aislada de concreto reforzado de 0.80 x 0.80 m. "
        "Se cuantifica por pieza confirmada. Profundidad máxima de excavación: 1.00 m."
    ),
    "CIM-003A": (
        "Zapata aislada de concreto reforzado de 1.00 x 1.00 m. "
        "Se cuantifica por pieza confirmada. Profundidad máxima de excavación: 1.00 m."
    ),
    "CIM-004": (
        "Dado asociado a zapata aislada. Se cuantifica por piezas confirmadas "
        "por proyecto."
    ),
    "CIM-005": (
        "Dala o cadena de desplante. Se cuantifica por longitud confirmada "
        "de los tramos aplicables."
    ),
    "CIM-005A": (
        "Contratrabe de 20 x 30 cm asociada a zapata corrida. "
        "Se cuantifica por longitud confirmada y evita duplicidad por tramo."
    ),
    "CIM-006": (
        "Muro de cimentación de mampostería. Se cuantifica por longitud "
        "geométrica confirmada."
    ),
}

WRITE_ENABLED = os.getenv("QUANTIA_SPECS_CIM_V18_WRITE", "0") == "1"


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


def merge_json(existing: Any, updates: dict[str, Any]) -> dict[str, Any]:
    base = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    base.update(updates)
    return base


def build_desired_existing(
    code: str,
    current: dict[str, Any],
    formula_id: str,
) -> dict[str, Any]:
    unit = UNIT_BY_CODE[code]

    desired = copy.deepcopy(current)

    desired["formula_id"] = formula_id
    desired["requires_project_definition"] = True
    desired["allows_user_override"] = True
    desired["default_quantity_mode"] = unit
    desired["technical_scope_text"] = TECHNICAL_SCOPE_BY_CODE[code]
    desired["inference_strategy"] = STRATEGY_BY_CODE[code]
    desired["dependencies_json"] = DEPENDENCIES_BY_CODE[code]
    desired["exclusions_json"] = EXCLUSIONS_BY_CODE[code]
    desired["parameter_rules"] = merge_json(
        current.get("parameter_rules"),
        {
            "unit_code": unit.upper(),
            "catalog_version": "V1.8",
        },
    )
    desired["metadata_json"] = merge_json(
        current.get("metadata_json"),
        {
            "catalog_version": "V1.8",
            "inference_rules_version": "V1.8",
            "unit_code": unit.upper(),
        },
    )
    desired["notes"] = (
        f"Engine spec actualizado a Quantia V1.8 para {code}."
    )
    desired["is_active"] = True

    return desired


def build_cim003a(
    concept_id: str,
    template: dict[str, Any],
    formula_id: str,
) -> dict[str, Any]:
    desired = copy.deepcopy(template)

    desired.pop("id", None)
    desired.pop("created_at", None)
    desired.pop("updated_at", None)

    desired["concept_id"] = concept_id
    desired["formula_id"] = formula_id
    desired["spec_code"] = "CIM-003A-BASE-TXT"
    desired["spec_name"] = "Especificacion base V1.8 CIM-003A"
    desired["requires_project_definition"] = True
    desired["allows_user_override"] = True
    desired["default_quantity_mode"] = "pza"
    desired["technical_scope_text"] = TECHNICAL_SCOPE_BY_CODE["CIM-003A"]
    desired["inference_strategy"] = STRATEGY_BY_CODE["CIM-003A"]
    desired["dependencies_json"] = DEPENDENCIES_BY_CODE["CIM-003A"]
    desired["exclusions_json"] = EXCLUSIONS_BY_CODE["CIM-003A"]

    desired["parameter_rules"] = merge_json(
        template.get("parameter_rules"),
        {
            "unit_code": "PZA",
            "catalog_version": "V1.8",
            "variant": "1.00x1.00",
            "max_excavation_depth_m": 1.0,
        },
    )

    desired["validations_json"] = merge_json(
        template.get("validations_json"),
        {
            "min_quantity": 0,
            "allow_negative": False,
            "max_excavation_depth_m": 1.0,
        },
    )

    desired["metadata_json"] = merge_json(
        template.get("metadata_json"),
        {
            "catalog_version": "V1.8",
            "inference_rules_version": "V1.8",
            "unit_code": "PZA",
            "variant": "1.00x1.00",
            "max_excavation_depth_m": 1.0,
        },
    )

    desired["notes"] = (
        "Engine spec creado para CIM-003A en Quantia V1.8. "
        "Variante de zapata aislada 1.00 x 1.00 m."
    )
    desired["is_active"] = True

    return desired


def compare_fields(
    current: dict[str, Any],
    desired: dict[str, Any],
) -> list[str]:
    skip = {"id", "created_at", "updated_at"}
    changed: list[str] = []

    for key, desired_value in desired.items():
        if key in skip:
            continue
        if current.get(key) != desired_value:
            changed.append(key)

    return changed


def main() -> None:
    print("Migración engine_concept_specs — Cimentación V1.8")
    print("Modo:", "ESCRITURA" if WRITE_ENABLED else "DRY-RUN")

    concepts = fetch_rows(
        "catalog_concepts",
        "id,code,is_active,unit_id,quantification_mode,default_formula_code",
    )
    concept_by_code = {
        str(row["code"]): row
        for row in concepts
        if row.get("code") in TARGET_CODES
    }

    missing_concepts = [
        code for code in TARGET_CODES if code not in concept_by_code
    ]
    if missing_concepts:
        raise RuntimeError(
            "Faltan conceptos en catalog_concepts: "
            + ", ".join(missing_concepts)
        )

    if str(concept_by_code["CIM-003A"]["id"]) != EXPECTED_CIM003A_ID:
        raise RuntimeError(
            "CIM-003A no tiene el UUID definitivo esperado."
        )

    units = fetch_rows("catalog_units", "id,code,symbol,is_active")
    unit_by_id = {str(row["id"]): row for row in units}

    for code in TARGET_CODES:
        concept = concept_by_code[code]
        unit = unit_by_id.get(str(concept.get("unit_id")))
        actual_unit = str(unit.get("code", "")).lower() if unit else ""
        expected_unit = UNIT_BY_CODE[code]

        if actual_unit != expected_unit:
            raise RuntimeError(
                f"{code}: unidad de catálogo={actual_unit!r}; "
                f"esperada={expected_unit!r}"
            )

    formulas = fetch_rows(
        "engine_formulas",
        "id,code,name,result_unit_symbol",
    )
    formula_by_code = {str(row["code"]): row for row in formulas}

    for formula_code, expected_id in EXPECTED_FORMULA_IDS.items():
        row = formula_by_code.get(formula_code)
        if not row:
            raise RuntimeError(
                f"Falta formula {formula_code} en engine_formulas."
            )
        if str(row["id"]) != expected_id:
            raise RuntimeError(
                f"{formula_code}: UUID={row['id']} no coincide con "
                f"el UUID auditado={expected_id}"
            )

    specs = fetch_rows("engine_concept_specs", "*")

    target_concept_ids = {
        str(concept_by_code[code]["id"]) for code in TARGET_CODES
    }
    specs_by_concept_id = {
        str(row["concept_id"]): row
        for row in specs
        if str(row.get("concept_id")) in target_concept_ids
    }

    existing_codes: dict[str, dict[str, Any]] = {}
    for code in TARGET_CODES:
        concept_id = str(concept_by_code[code]["id"])
        spec = specs_by_concept_id.get(concept_id)
        if spec:
            existing_codes[code] = spec

    expected_existing = {
        "CIM-002",
        "CIM-003",
        "CIM-004",
        "CIM-005",
        "CIM-005A",
        "CIM-006",
    }

    missing_existing = sorted(expected_existing - set(existing_codes))
    if missing_existing:
        raise RuntimeError(
            "Faltan engine_concept_specs que ya debían existir: "
            + ", ".join(missing_existing)
        )

    template = existing_codes["CIM-003"]

    desired_by_code: dict[str, dict[str, Any]] = {}

    for code in sorted(expected_existing):
        unit = UNIT_BY_CODE[code]
        formula_code = FORMULA_CODES[unit]
        formula_id = str(formula_by_code[formula_code]["id"])

        desired_by_code[code] = build_desired_existing(
            code,
            existing_codes[code],
            formula_id,
        )

    cim003a_formula_id = str(
        formula_by_code["F_PZA_DIRECTA"]["id"]
    )

    if "CIM-003A" in existing_codes:
        desired_by_code["CIM-003A"] = build_desired_existing(
            "CIM-003A",
            existing_codes["CIM-003A"],
            cim003a_formula_id,
        )
    else:
        desired_by_code["CIM-003A"] = build_cim003a(
            str(concept_by_code["CIM-003A"]["id"]),
            template,
            cim003a_formula_id,
        )

    print("\n--- AUDITORÍA ---")
    print(f"Conceptos encontrados: {len(concept_by_code)}/7")
    print(f"Specs existentes:       {len(existing_codes)}/7")
    print(
        "CIM-003A:",
        "UPDATE" if "CIM-003A" in existing_codes else "INSERT",
    )

    print("\n--- PLAN ---")

    insert_codes: list[str] = []
    update_codes: list[str] = []

    for code in TARGET_CODES:
        desired = desired_by_code[code]
        current = existing_codes.get(code)

        if current is None:
            insert_codes.append(code)
            print(
                f"+ {code}: INSERT "
                f"strategy={desired['inference_strategy']} "
                f"mode={desired['default_quantity_mode']}"
            )
        else:
            fields = compare_fields(current, desired)
            if fields:
                update_codes.append(code)
                print(
                    f"~ {code}: UPDATE -> {', '.join(fields)}"
                )
            else:
                print(f"= {code}: sin cambios")

    if not WRITE_ENABLED:
        print("\nDRY-RUN correcto. No se modificó Supabase.")
        print(
            "Para escribir: "
            '$env:QUANTIA_SPECS_CIM_V18_WRITE="1"'
        )
        return

    print("\n--- ESCRITURA ---")

    for code in TARGET_CODES:
        desired = desired_by_code[code]
        current = existing_codes.get(code)

        if current is None:
            payload = {
                key: value
                for key, value in desired.items()
                if key not in {"id", "created_at", "updated_at"}
            }

            execute_catalog_query(
                lambda client, payload=payload: (
                    client.table("engine_concept_specs")
                    .insert(payload)
                    .execute()
                    .data
                    or []
                ),
                operation=f"insert_engine_spec_{code}",
                critical=True,
            )
            print(f"Creado: {code}")
        else:
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
                lambda client,
                spec_id=current["id"],
                payload=payload: (
                    client.table("engine_concept_specs")
                    .update(payload)
                    .eq("id", spec_id)
                    .execute()
                    .data
                    or []
                ),
                operation=f"update_engine_spec_{code}",
                critical=True,
            )
            print(f"Actualizado: {code}")

    # Verificación posterior
    specs_after = fetch_rows("engine_concept_specs", "*")
    by_concept_after = {
        str(row["concept_id"]): row
        for row in specs_after
        if str(row.get("concept_id")) in target_concept_ids
    }

    errors: list[str] = []

    for code in TARGET_CODES:
        concept_id = str(concept_by_code[code]["id"])
        row = by_concept_after.get(concept_id)

        if not row:
            errors.append(f"{code}: sin engine_concept_specs")
            continue

        expected_unit = UNIT_BY_CODE[code]
        expected_formula_code = FORMULA_CODES[expected_unit]
        expected_formula_id = str(
            formula_by_code[expected_formula_code]["id"]
        )

        checks = {
            "formula_id": expected_formula_id,
            "requires_project_definition": True,
            "allows_user_override": True,
            "default_quantity_mode": expected_unit,
            "inference_strategy": STRATEGY_BY_CODE[code],
            "dependencies_json": DEPENDENCIES_BY_CODE[code],
            "exclusions_json": EXCLUSIONS_BY_CODE[code],
            "is_active": True,
        }

        for field, expected in checks.items():
            if row.get(field) != expected:
                errors.append(
                    f"{code}: {field}={row.get(field)!r}; "
                    f"esperado={expected!r}"
                )

    if errors:
        raise RuntimeError(
            "Verificación posterior falló:\n- "
            + "\n- ".join(errors)
        )

    print("\n--- VERIFICACIÓN FINAL ---")
    print("Specs Cimentación: 7/7")
    print("CIM-003A: creado y activo")
    print("Fórmulas: ML/PZA correctas")
    print("Estrategias: 7/7")
    print("Dependencias: 7/7")
    print("Cimentación engine_concept_specs V1.8 correcta.")


if __name__ == "__main__":
    main()
