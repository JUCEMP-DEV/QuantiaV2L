from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1.endpoints.catalogos import (
    execute_catalog_query,
    safe_text,
)


# =========================================================
# CONFIGURACIÓN V1.8
# =========================================================

STRUCTURE_CONTEXT_CONDITIONS: dict[str, dict[str, Any]] = {
    # ---------------------------------------------
    # Sistema tradicional / mampostería
    # ---------------------------------------------

    "EST-001": {
        "sistemaEstructural": [
            "tradicional",
            "mixta",
        ]
    },

    "EST-002": {
        "sistemaEstructural": [
            "tradicional",
            "mixta",
        ]
    },

    # ---------------------------------------------
    # Concreto armado
    # ---------------------------------------------

    "EST-003": {
        "sistemaEstructural": [
            "concreto_reforzado",
            "mixta",
        ]
    },

    "EST-004": {
        "sistemaEstructural": [
            "concreto_reforzado",
            "mixta",
        ]
    },

    # ---------------------------------------------
    # Losas
    # ---------------------------------------------

    "EST-005": {
        "tipoLosa": "maciza"
    },

    "EST-006": {
        "tipoLosa":
            "vigueta_bovedilla"
    },

    "EST-007": {
        "tipoLosa":
            "aligerada_caseton_nervaduras"
    },
}


# =========================================================
# SEGURIDAD
#
# Por defecto NO escribe.
#
# Para escribir:
#
# $env:QUANTIA_RULES_WRITE="1"
# python .\scripts\update_engine_activation_structure_v18.py
# =========================================================

WRITE_ENABLED = (
    os.getenv(
        "QUANTIA_RULES_WRITE",
        "0",
    )
    == "1"
) 

STRUCTURE_REQUIRED_INPUTS: dict[str, list[str]] = {

    "EST-001": [
        "castillos_unicos_confirmados",
        "alturas_nivel",
    ],

    "EST-002": [
        "tramos_cadena_confirmados",
    ],

    "EST-003": [
        "columnas_confirmadas",
        "alturas_nivel",
    ],

    "EST-004": [
        "trabes_confirmadas",
        "longitudes",
    ],

    "EST-005": [
        "poligono_losa",
        "huecos_no_losa",
    ],

    "EST-006": [
        "poligono_losa",
        "huecos_no_losa",
        "sistema_confirmado",
    ],

    "EST-007": [
        "poligono_losa",
        "huecos_no_losa",
        "sistema_confirmado",
    ],
}

STRUCTURE_STRATEGIES: dict[str, str] = {

    "EST-001":
        "longitud_castillos_unicos",

    "EST-002":
        "longitud_cadenas_cerramiento",

    "EST-003":
        "longitud_columnas_confirmadas",

    "EST-004":
        "longitud_trabes_confirmadas",

    "EST-005":
        "area_neta_losa_maciza",

    "EST-006":
        "area_neta_losa_vigueta_bovedilla",

    "EST-007":
        "area_neta_losa_nervada",
}

STRUCTURE_UNITS: dict[str, str] = {

    "EST-001": "ml",
    "EST-002": "ml",
    "EST-003": "ml",
    "EST-004": "ml",

    "EST-005": "m2",
    "EST-006": "m2",
    "EST-007": "m2",
}

def main() -> None:

    target_codes = list(
        STRUCTURE_CONTEXT_CONDITIONS.keys()
    )

    print(
        "\n=== QUANTIA V1.8 ==="
    )

    print(
        "Actualización de condiciones "
        "de activación — Estructura"
    )

    print(
        f"Modo: "
        f"{'ESCRITURA' if WRITE_ENABLED else 'DRY-RUN'}"
    )

    # =====================================================
    # 1. BUSCAR CONCEPTOS
    # =====================================================

    concepts = execute_catalog_query(
        lambda client: (
            client.table(
                "catalog_concepts"
            )
            .select(
                "id,code,is_active"
            )
            .in_(
                "code",
                target_codes,
            )
            .execute()
            .data
            or []
        ),
        operation=
            "audit_structure_catalog_concepts",
        critical=True,
    )

    concepts_by_code = {
        safe_text(
            row.get("code")
        ).upper(): row
        for row in concepts
        if safe_text(
            row.get("code")
        )
    }

    missing_concepts = [
        code
        for code in target_codes
        if code
        not in concepts_by_code
    ]

    if missing_concepts:

        raise RuntimeError(
            "Faltan conceptos en "
            "catalog_concepts: "
            + ", ".join(
                missing_concepts
            )
        )

    print(
        f"Conceptos encontrados: "
        f"{len(concepts_by_code)}/7"
    )

    # =====================================================
    # 2. BUSCAR ENGINE SPECS
    # =====================================================

    concept_ids = [
        safe_text(
            row.get("id")
        )
        for row
        in concepts_by_code.values()
    ]

    specs = execute_catalog_query(
        lambda client: (
            client.table(
                "engine_concept_specs"
            )
            .select(
                "id,"
                "concept_id,"
                "spec_code,"
                "is_active"
            )
            .in_(
                "concept_id",
                concept_ids,
            )
            .eq(
                "is_active",
                True,
            )
            .execute()
            .data
            or []
        ),
        operation=
            "audit_structure_engine_specs",
        critical=True,
    )

    specs_by_concept_id: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in specs:

        concept_id = safe_text(
            row.get(
                "concept_id"
            )
        )

        if not concept_id:
            continue

        if concept_id in (
            specs_by_concept_id
        ):

            raise RuntimeError(
                "Más de un "
                "engine_concept_specs "
                "activo para concept_id="
                f"{concept_id}"
            )

        specs_by_concept_id[
            concept_id
        ] = row

    missing_specs: list[str] = []

    for code, concept in (
        concepts_by_code.items()
    ):

        concept_id = safe_text(
            concept.get("id")
        )

        if concept_id not in (
            specs_by_concept_id
        ):
            missing_specs.append(
                code
            )

    if missing_specs:

        raise RuntimeError(
            "Faltan especificaciones "
            "activas para: "
            + ", ".join(
                missing_specs
            )
        )

    print(
        f"Engine specs encontrados: "
        f"{len(specs_by_concept_id)}/7"
    )

    # =====================================================
    # 3. BUSCAR ACTIVATION RULES
    # =====================================================

    spec_ids = [
        safe_text(
            row.get("id")
        )
        for row
        in specs_by_concept_id.values()
    ]

    rules = execute_catalog_query(
        lambda client: (
            client.table(
                "engine_activation_rules"
            )
            .select(
                "id,"
                "code,"
                "concept_spec_id,"
                "condition_json,"
                "is_active"
            )
            .in_(
                "concept_spec_id",
                spec_ids,
            )
            .eq(
                "is_active",
                True,
            )
            .execute()
            .data
            or []
        ),
        operation=
            "audit_structure_activation_rules",
        critical=True,
    )

    rules_by_spec_id: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rules:

        spec_id = safe_text(
            row.get(
                "concept_spec_id"
            )
        )

        if not spec_id:
            continue

        if spec_id in rules_by_spec_id:

            raise RuntimeError(
                "Más de una regla "
                "de activación activa "
                "para concept_spec_id="
                f"{spec_id}"
            )

        rules_by_spec_id[
            spec_id
        ] = row

    # =====================================================
    # 4. CREAR PLAN DE ACTUALIZACIÓN
    # =====================================================

    update_plan: list[
        dict[str, Any]
    ] = []

    for code in target_codes:

        concept = (
            concepts_by_code[
                code
            ]
        )

        concept_id = safe_text(
            concept.get("id")
        )

        spec = (
            specs_by_concept_id[
                concept_id
            ]
        )

        spec_id = safe_text(
            spec.get("id")
        )

        rule = rules_by_spec_id.get(
            spec_id
        )

        # -------------------------------------------------
        # Si no existe regla, prepararla para INSERT.
        # Si existe, conservarla para UPDATE.
        # -------------------------------------------------

        if not rule:

            old_condition = {}

            new_condition = {
                "concept_active": True,
                "required_inputs":
                    STRUCTURE_REQUIRED_INPUTS[
                        code
                    ],
                "requires_project_definition": True,
                "context_conditions":
                    STRUCTURE_CONTEXT_CONDITIONS[
                        code
                    ],
            }

            update_plan.append(
                {
                    "action":
                        "UPDATE",

                    "code":
                        code,

                    "concept_id":
                        concept_id,

                    "spec_id":
                        spec_id,

                    "rule_id":
                        None,

                    "rule_code":
                        f"ACT_{code.replace('-', '_')}_V18",

                    "before":
                        {},

                    "after":
                        new_condition,
                }
            )

            continue 


      

        old_condition = (
            rule.get(
                "condition_json"
            )
            if isinstance(
                rule.get(
                    "condition_json"
                ),
                dict,
            )
            else {}
        )

        # ---------------------------------------------
        # IMPORTANTE:
        #
        # Preservar condition_json existente.
        # Solo agregar/reemplazar context_conditions.
        # ---------------------------------------------

        new_condition = dict(
            old_condition
        )

        new_condition[
            "context_conditions"
        ] = (
            STRUCTURE_CONTEXT_CONDITIONS[
                code
            ]
        )

        update_plan.append(
            {
                "code":
                    code,

                "concept_id":
                    concept_id,

                "spec_id":
                    spec_id,

                "rule_id":
                    safe_text(
                        rule.get(
                            "id"
                        )
                    ),

                "rule_code":
                    safe_text(
                        rule.get(
                            "code"
                        )
                    ),

                "before":
                    old_condition,

                "after":
                    new_condition,
            }
        )

    # =====================================================
    # 5. MOSTRAR PLAN
    # =====================================================

    print(
        "\n--- PLAN ---"
    )

    for item in update_plan:

        print(
            f"\n{item['code']}"
        )

        print(
            f"  concept_id: "
            f"{item['concept_id']}"
        )

        print(
            f"  spec_id: "
            f"{item['spec_id']}"
        )

        print(
            f"  rule_id: "
            f"{item['rule_id']}"
        )

        print(
            "  context_conditions:"
        )

        print(
            "   ",
            item["after"].get(
                "context_conditions"
            ),
        )

    # =====================================================
    # 6. DRY RUN
    # =====================================================

    if not WRITE_ENABLED:

        print(
            "\nDRY-RUN terminado."
        )

        print(
            "No se modificó Supabase."
        )

        print(
            "\nSi los 7 conceptos son "
            "correctos, ejecuta:"
        )

        print(
            '$env:QUANTIA_RULES_WRITE="1"'
        )

        print(
            "python "
            ".\\scripts\\"
            "update_engine_activation_"
            "structure_v18.py"
        )

        return

    # =====================================================
    # 7. ACTUALIZAR
    # =====================================================

    print(
    "\n--- ESCRITURA ---"
)

    for item in update_plan:

        code = item["code"]

        rule_id = item.get(
            "rule_id"
        )

        condition_json = item[
            "after"
        ]

        # =====================================================
        # INSERT
        #
        # Si no existe rule_id, la regla todavía no existe.
        # =====================================================

        if not rule_id:

            payload = {
                "code":
                    f"ACT_{code.replace('-', '_')}_V18",

                "concept_spec_id":
                    item["spec_id"],

                "rule_name":
                    f"Activación V1.8 — {code}",

                "priority":
                    300,

                "activation_type":
                    "condicional",

                "type_intervention":
                    None,

                "scope":
                    None,

                "trigger_json": {
                    "sources": [
                        "project_document_explicit",
                        "ai_detected_geometry",
                        "user_selection",
                    ],
                    "user_selectable":
                        True,
                },

                "condition_json":
                    condition_json,

                "derivation_json": {
                    "strategy":
                        STRUCTURE_STRATEGIES[
                            code
                        ],

                    "formula_code":
                        (
                            "F_M2_DIRECTA"
                            if STRUCTURE_UNITS[
                                code
                            ] == "m2"
                            else "F_ML_DIRECTA"
                        ),

                    "unit":
                        STRUCTURE_UNITS[
                            code
                        ],
                },

                "invalidates_json": [
                    "missing_required_input",
                    "unit_or_code_mismatch",
                    "duplicate_geometry",
                    "missing_project_definition",
                ],

                "alerts_json": [
                    {
                        "code":
                            "REQUIERE_DEFINICION_PROYECTO",

                        "severity":
                            "blocking",
                    }
                ],

                "output_action_json": {
                    "action":
                        "propose_quantity",

                    "status":
                        "PROPOSED",

                    "requires_user_confirmation":
                        True,

                    "persist_after_validation":
                        True,
                },

                "stop_on_error":
                    True,

                "is_active":
                    True,
            }

            inserted = execute_catalog_query(
                lambda client,
                payload=payload: (
                    client.table(
                        "engine_activation_rules"
                    )
                    .insert(
                        payload
                    )
                    .execute()
                    .data
                    or []
                ),
                operation=(
                    "insert_activation_"
                    f"{code}"
                ),
                critical=True,
            )

            print(
                f"Creada: {code}"
            )

            continue

        # =====================================================
        # UPDATE
        #
        # Solo llega aquí cuando rule_id realmente existe.
        # =====================================================

        execute_catalog_query(
            lambda client,
            rule_id=rule_id,
            condition_json=condition_json: (
                client.table(
                    "engine_activation_rules"
                )
                .update(
                    {
                        "condition_json":
                            condition_json
                    }
                )
                .eq(
                    "id",
                    rule_id,
                )
                .execute()
                .data
                or []
            ),
            operation=(
                "update_activation_"
                f"{code}"
            ),
            critical=True,
        )

        print(
            f"Actualizada: {code}"
        )


    # =====================================================
    # 8. VERIFICACIÓN POSTERIOR
    # =====================================================

    verification = execute_catalog_query(
        lambda client: (
            client.table(
                "engine_activation_rules"
            )
            .select(
                "id,"
                "code,"
                "concept_spec_id,"
                "condition_json,"
                "is_active"
            )
            .in_(
                "concept_spec_id",
                spec_ids,
            )
            .eq(
                "is_active",
                True,
            )
            .execute()
            .data
            or []
        ),
        operation=
            "verify_structure_activation_rules",
        critical=True,
    )

    verified = 0

    for rule in verification:

        condition = (
            rule.get(
                "condition_json"
            )
            if isinstance(
                rule.get(
                    "condition_json"
                ),
                dict,
            )
            else {}
        )

        context_conditions = (
            condition.get(
                "context_conditions"
            )
        )

        if isinstance(
            context_conditions,
            dict,
        ):
            verified += 1

    print(
        "\n--- VERIFICACIÓN ---"
    )

    print(
        f"Reglas con "
        f"context_conditions: "
        f"{verified}/7"
    )

    if verified != 7:

        raise RuntimeError(
            "La actualización no quedó "
            "completa: "
            f"{verified}/7"
        )

    print(
        "\nEstructura V1.8 "
        "actualizada correctamente."
    )


if __name__ == "__main__":
    main()