from __future__ import annotations

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

CONTEXT_CONDITIONS: dict[str, dict[str, Any]] = {
    "CIM-002": {
        "tipoCimentacion": "zapata_corrida",
    },
    "CIM-003": {
        "tipoCimentacion": "zapata_aislada_trabe_liga",
        "varianteZapata": "080",
    },
    "CIM-003A": {
        "tipoCimentacion": "zapata_aislada_trabe_liga",
        "varianteZapata": "100",
    },
    "CIM-004": {
        "tipoCimentacion": "zapata_aislada_trabe_liga",
    },
    # CIM-005 intencionalmente NO tiene context_conditions.
    "CIM-005A": {
        "tipoCimentacion": "zapata_corrida",
    },
    "CIM-006": {
        "tipoCimentacion": "mamposteria_corrida",
    },
}

REQUIRED_INPUTS: dict[str, list[str]] = {
    "CIM-002": ["tramos_zapata_corrida_confirmados"],
    "CIM-003": ["cantidad_zapatas_080_confirmada"],
    "CIM-003A": ["cantidad_zapatas_100_confirmada"],
    "CIM-004": ["cantidad_dados_confirmada"],
    "CIM-005": ["tramos_dala_desplante_confirmados"],
    "CIM-005A": ["tramos_contratrabe_20x30_confirmados"],
    "CIM-006": ["geometria_longitud_confirmada"],
}

STRATEGIES: dict[str, str] = {
    "CIM-002": "longitud_zapata_corrida",
    "CIM-003": "conteo_zapata_080",
    "CIM-003A": "conteo_zapata_100",
    "CIM-004": "conteo_dados_confirmados",
    "CIM-005": "longitud_dala_desplante",
    "CIM-005A": "longitud_contratrabe_20x30",
    "CIM-006": "longitud_muro_cimentacion",
}

UNITS: dict[str, str] = {
    "CIM-002": "ml",
    "CIM-003": "pza",
    "CIM-003A": "pza",
    "CIM-004": "pza",
    "CIM-005": "ml",
    "CIM-005A": "ml",
    "CIM-006": "ml",
}

FORMULAS: dict[str, str] = {
    "CIM-002": "F_ML_DIRECTA",
    "CIM-003": "F_PZA_DIRECTA",
    "CIM-003A": "F_PZA_DIRECTA",
    "CIM-004": "F_PZA_DIRECTA",
    "CIM-005": "F_ML_DIRECTA",
    "CIM-005A": "F_ML_DIRECTA",
    "CIM-006": "F_ML_DIRECTA",
}

WRITE_ENABLED = os.getenv("QUANTIA_RULES_CIM_V18_WRITE", "0") == "1"


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


def desired_payload(
    code: str,
    spec_id: str,
) -> dict[str, Any]:
    condition_json: dict[str, Any] = {
        "concept_active": True,
        "required_inputs": REQUIRED_INPUTS[code],
        "requires_project_definition": True,
    }

    context_conditions = CONTEXT_CONDITIONS.get(code)
    if context_conditions:
        condition_json["context_conditions"] = context_conditions

    return {
        "code": f"ACT_{code.replace('-', '_')}_V18",
        "concept_spec_id": spec_id,
        "rule_name": f"Activación V1.8 — {code}",
        "priority": 300,
        "activation_type": "condicional",
        "type_intervention": None,
        "scope": None,
        "trigger_json": {
            "sources": [
                "project_document_explicit",
                "ai_detected_geometry",
                "user_selection",
            ],
            "user_selectable": True,
        },
        "condition_json": condition_json,
        "derivation_json": {
            "strategy": STRATEGIES[code],
            "formula_code": FORMULAS[code],
            "unit": UNITS[code],
        },
        "invalidates_json": [
            "missing_required_input",
            "unit_or_code_mismatch",
            "duplicate_geometry",
            "missing_project_definition",
        ],
        "alerts_json": [
            {
                "code": "REQUIERE_DEFINICION_PROYECTO",
                "severity": "blocking",
            }
        ],
        "output_action_json": {
            "action": "propose_quantity",
            "status": "PROPOSED",
            "requires_user_confirmation": True,
            "persist_after_validation": True,
        },
        "stop_on_error": True,
        "is_active": True,
    }


def comparable_fields() -> list[str]:
    return [
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


def changed_fields(
    current: dict[str, Any],
    desired: dict[str, Any],
) -> list[str]:
    changed: list[str] = []
    for field in comparable_fields():
        if current.get(field) != desired.get(field):
            changed.append(field)
    return changed


def main() -> None:
    print("Actualización de reglas de activación — Cimentación V1.8")
    print("Modo:", "ESCRITURA" if WRITE_ENABLED else "DRY-RUN")

    concepts = fetch_rows(
        "catalog_concepts",
        "id,code,is_active",
    )
    concept_by_code = {
        str(row["code"]): row
        for row in concepts
        if row.get("code") in TARGET_CODES
    }

    missing_concepts = [
        code for code in TARGET_CODES
        if code not in concept_by_code
    ]
    if missing_concepts:
        raise RuntimeError(
            "Faltan conceptos en catalog_concepts: "
            + ", ".join(missing_concepts)
        )

    specs = fetch_rows(
        "engine_concept_specs",
        "id,concept_id,spec_code,inference_strategy,"
        "requires_project_definition,is_active",
    )

    spec_by_concept_id = {
        str(row["concept_id"]): row
        for row in specs
    }

    spec_by_code: dict[str, dict[str, Any]] = {}

    for code in TARGET_CODES:
        concept_id = str(concept_by_code[code]["id"])
        spec = spec_by_concept_id.get(concept_id)

        if not spec:
            raise RuntimeError(
                f"{code}: no tiene engine_concept_specs."
            )

        if not spec.get("is_active"):
            raise RuntimeError(
                f"{code}: engine_concept_specs está inactivo."
            )

        if spec.get("inference_strategy") != STRATEGIES[code]:
            raise RuntimeError(
                f"{code}: inference_strategy="
                f"{spec.get('inference_strategy')!r}; "
                f"esperada={STRATEGIES[code]!r}"
            )

        if spec.get("requires_project_definition") is not True:
            raise RuntimeError(
                f"{code}: requires_project_definition no es true."
            )

        spec_by_code[code] = spec

    print(f"\nConceptos encontrados: {len(concept_by_code)}/7")
    print(f"Specs activos V1.8:    {len(spec_by_code)}/7")

    rules = fetch_rows("engine_activation_rules", "*")

    target_spec_ids = {
        str(spec_by_code[code]["id"])
        for code in TARGET_CODES
    }

    rules_by_spec_id: dict[str, list[dict[str, Any]]] = {}

    for rule in rules:
        spec_id = str(rule.get("concept_spec_id"))
        if spec_id in target_spec_ids:
            rules_by_spec_id.setdefault(spec_id, []).append(rule)

    duplicates = {
        spec_id: rows
        for spec_id, rows in rules_by_spec_id.items()
        if len(rows) > 1
    }

    if duplicates:
        detail = []
        for spec_id, rows in duplicates.items():
            detail.append(
                f"{spec_id}: "
                + ", ".join(str(row.get("code")) for row in rows)
            )
        raise RuntimeError(
            "Hay más de una activation_rule para un spec objetivo:\n- "
            + "\n- ".join(detail)
        )

    desired_by_code: dict[str, dict[str, Any]] = {}
    existing_by_code: dict[str, dict[str, Any]] = {}

    for code in TARGET_CODES:
        spec_id = str(spec_by_code[code]["id"])
        desired = desired_payload(code, spec_id)
        desired_by_code[code] = desired

        rows = rules_by_spec_id.get(spec_id, [])
        if rows:
            existing_by_code[code] = rows[0]

    print("\n--- PLAN ---")

    inserts = 0
    updates = 0
    unchanged = 0

    for code in TARGET_CODES:
        current = existing_by_code.get(code)
        desired = desired_by_code[code]

        if current is None:
            inserts += 1
            print(
                f"+ {code}: INSERT "
                f"{desired['code']}"
            )
            continue

        fields = changed_fields(current, desired)
        if fields:
            updates += 1
            print(
                f"~ {code}: UPDATE -> "
                + ", ".join(fields)
            )
        else:
            unchanged += 1
            print(f"= {code}: sin cambios")

    print(
        f"\nINSERT={inserts} UPDATE={updates} "
        f"SIN_CAMBIOS={unchanged}"
    )

    print("\nContext conditions esperadas:")
    for code in TARGET_CODES:
        context = CONTEXT_CONDITIONS.get(code)
        print(
            f"  {code}: "
            f"{context if context else 'SIN context_conditions'}"
        )

    if not WRITE_ENABLED:
        print("\nDRY-RUN correcto. No se modificó Supabase.")
        print(
            "Para escribir: "
            '$env:QUANTIA_RULES_CIM_V18_WRITE="1"'
        )
        return

    print("\n--- ESCRITURA ---")

    for code in TARGET_CODES:
        current = existing_by_code.get(code)
        payload = desired_by_code[code]

        if current is None:
            execute_catalog_query(
                lambda client, payload=payload: (
                    client.table("engine_activation_rules")
                    .insert(payload)
                    .execute()
                    .data
                    or []
                ),
                operation=f"insert_activation_{code}",
                critical=True,
            )
            print(f"Creada: {code}")
        else:
            rule_id = current["id"]

            execute_catalog_query(
                lambda client,
                rule_id=rule_id,
                payload=payload: (
                    client.table("engine_activation_rules")
                    .update(payload)
                    .eq("id", rule_id)
                    .execute()
                    .data
                    or []
                ),
                operation=f"update_activation_{code}",
                critical=True,
            )
            print(f"Actualizada: {code}")

    # Verificación final.
    after = fetch_rows("engine_activation_rules", "*")

    after_by_spec: dict[str, list[dict[str, Any]]] = {}
    for rule in after:
        spec_id = str(rule.get("concept_spec_id"))
        if spec_id in target_spec_ids:
            after_by_spec.setdefault(spec_id, []).append(rule)

    errors: list[str] = []
    context_count = 0

    for code in TARGET_CODES:
        spec_id = str(spec_by_code[code]["id"])
        rows = after_by_spec.get(spec_id, [])

        if len(rows) != 1:
            errors.append(
                f"{code}: reglas encontradas={len(rows)}; esperada=1"
            )
            continue

        actual = rows[0]
        desired = desired_by_code[code]

        fields = changed_fields(actual, desired)
        if fields:
            errors.append(
                f"{code}: difiere en {', '.join(fields)}"
            )

        context_conditions = (
            actual.get("condition_json") or {}
        ).get("context_conditions")

        if context_conditions:
            context_count += 1

        if code == "CIM-005" and context_conditions:
            errors.append(
                "CIM-005 no debe tener context_conditions."
            )

        if code != "CIM-005" and not context_conditions:
            errors.append(
                f"{code}: falta context_conditions."
            )

    if context_count != 6:
        errors.append(
            f"context_conditions={context_count}/7; "
            "esperado 6/7."
        )

    if errors:
        raise RuntimeError(
            "Verificación final falló:\n- "
            + "\n- ".join(errors)
        )

    print("\n--- VERIFICACIÓN FINAL ---")
    print("Reglas Cimentación: 7/7")
    print("Reglas con context_conditions: 6/7")
    print("CIM-005 sin context_conditions: correcto")
    print("stop_on_error: 7/7")
    print("activation_type=condicional: 7/7")
    print("Cimentación engine_activation_rules V1.8 correcta.")


if __name__ == "__main__":
    main()
