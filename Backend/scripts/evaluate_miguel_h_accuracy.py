from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_AUDIT = Path(
    "tests/output/miguel_h/miguel_h_pipeline_audit.json"
)
DEFAULT_CONTRACT = Path(
    "tests/output/miguel_h/miguel_h_contract_03_2_to_04.json"
)
DEFAULT_REGRESSION = Path(
    "tests/output/miguel_h/miguel_h_regression_summary.json"
)
DEFAULT_OUTPUT = Path(
    "tests/output/miguel_h/miguel_h_accuracy_report.json"
)

NUMERIC_TOLERANCE = 1e-6

# ============================================================
# BASELINE CANÓNICO MIGUEL H
# ============================================================
#
# Recuperado de la reconstrucción image-only validada:
# - 2 niveles
# - 21 referencias de eje por nivel
# - 17 tramos dimensionales
# - 8 espacios
# - 3 zonas semánticas abiertas
# - 3 escaleras
#
# No se puntúan muros / puertas / ventanas porque el baseline
# image-only recuperado no los enumera exhaustivamente.
# ============================================================

MIGUEL_H_BASELINE: dict[str, Any] = {
    "levels": [
        "Planta Baja",
        "Planta Alta",
    ],
    "plants": [
        {
            "name": "Planta Baja",
            "axis_x": {
                "labels": [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                ],
                "segments_m": [
                    1.85,
                    0.85,
                    2.00,
                    5.25,
                    5.05,
                ],
            },
            "axis_y": {
                "labels": [
                    "A",
                    "J",
                    "C",
                    "D",
                ],
                "segments_m": [
                    1.55,
                    0.85,
                    2.60,
                ],
            },
            "spaces": [
                "Cochera y acceso frontal",
                "Medio baño",
                "Patio de servicio / jardín posterior",
                "Área común",
            ],
            "semantic_zones": [
                "Estancia",
                "Comedor",
                "Cocina",
            ],
            "stairs": 1,
        },
        {
            "name": "Planta Alta",
            "axis_x": {
                "labels": [
                    "1",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "6",
                ],
                "segments_m": [
                    1.15,
                    4.10,
                    4.10,
                    2.00,
                    1.10,
                    2.55,
                ],
            },
            "axis_y": {
                "labels": [
                    "A",
                    "J",
                    "C",
                    "D",
                ],
                "segments_m": [
                    1.22,
                    1.18,
                    2.60,
                ],
            },
            "spaces": [
                "Recámara 1",
                "Recámara 2",
                "Recinto sin función identificable",
                "Distribución / circulación",
            ],
            "semantic_zones": [],
            "stairs": 2,
        },
    ],
}


# ============================================================
# UTILIDADES
# ============================================================


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo requerido: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def normalize_text(value: Any) -> str:
    text = str(
        value or ""
    ).strip().lower()

    decomposed = unicodedata.normalize(
        "NFD",
        text,
    )

    text = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def normalize_level(value: Any) -> str:
    text = normalize_text(
        value
    )

    aliases = {
        "pb": "planta baja",
        "pa": "planta alta",
        "planta baja": "planta baja",
        "planta alta": "planta alta",
    }

    return aliases.get(
        text,
        text,
    )


def numeric_value(value: Any) -> float | None:
    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        (int, float),
    ):
        result = float(
            value
        )

        return (
            result
            if math.isfinite(
                result
            )
            else None
        )

    text = str(
        value or ""
    ).strip().replace(
        ",",
        ".",
    )

    match = re.search(
        r"[-+]?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        result = float(
            match.group(0)
        )
    except ValueError:
        return None

    return (
        result
        if math.isfinite(
            result
        )
        else None
    )


def same_number(
    first: float | None,
    second: float | None,
) -> bool:
    if (
        first is None
        or second is None
    ):
        return False

    return math.isclose(
        first,
        second,
        rel_tol=0.0,
        abs_tol=NUMERIC_TOLERANCE,
    )


def first_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> Any:
    for key in keys:
        if key in payload:
            return payload[
                key
            ]

    return None


def walk_dicts(
    value: Any,
):
    if isinstance(
        value,
        dict,
    ):
        yield value

        for child in value.values():
            yield from walk_dicts(
                child
            )

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            yield from walk_dicts(
                child
            )


def find_first_list(
    value: Any,
    keys: tuple[str, ...],
) -> list[Any]:
    if isinstance(
        value,
        dict,
    ):
        for key in keys:
            candidate = value.get(
                key
            )

            if isinstance(
                candidate,
                list,
            ):
                return candidate

        for child in value.values():
            result = find_first_list(
                child,
                keys,
            )

            if result:
                return result

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            result = find_first_list(
                child,
                keys,
            )

            if result:
                return result

    return []


def percent(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return (
        f"{value * 100.0:.1f}%"
    )


# ============================================================
# BASELINE → UNIDADES ESPERADAS
# ============================================================


def expected_levels() -> list[str]:
    return [
        normalize_level(
            level
        )
        for level in MIGUEL_H_BASELINE[
            "levels"
        ]
    ]


def expected_axes() -> list[
    dict[str, str]
]:
    result: list[
        dict[str, str]
    ] = []

    for plant in MIGUEL_H_BASELINE[
        "plants"
    ]:
        level = normalize_level(
            plant[
                "name"
            ]
        )

        for axis_group in (
            "axis_x",
            "axis_y",
        ):
            for label in plant[
                axis_group
            ][
                "labels"
            ]:
                result.append(
                    {
                        "level": level,
                        "label": str(
                            label
                        ).strip().upper(),
                    }
                )

    return result


def expected_dimensions() -> list[
    dict[str, Any]
]:
    result: list[
        dict[str, Any]
    ] = []

    for plant in MIGUEL_H_BASELINE[
        "plants"
    ]:
        level = normalize_level(
            plant[
                "name"
            ]
        )

        for axis_group in (
            "axis_x",
            "axis_y",
        ):
            axis = plant[
                axis_group
            ]

            labels = axis[
                "labels"
            ]

            segments = axis[
                "segments_m"
            ]

            if len(
                labels
            ) != len(
                segments
            ) + 1:
                raise ValueError(
                    "Baseline Miguel H inválido en "
                    f"{level}/{axis_group}."
                )

            for index, value_m in enumerate(
                segments
            ):
                result.append(
                    {
                        "level": level,
                        "axis_group": axis_group,
                        "start_label": str(
                            labels[
                                index
                            ]
                        ).strip().upper(),
                        "end_label": str(
                            labels[
                                index + 1
                            ]
                        ).strip().upper(),
                        "value_m": float(
                            value_m
                        ),
                    }
                )

    return result


def expected_named(
    field: str,
) -> list[
    dict[str, str]
]:
    result: list[
        dict[str, str]
    ] = []

    for plant in MIGUEL_H_BASELINE[
        "plants"
    ]:
        level = normalize_level(
            plant[
                "name"
            ]
        )

        for name in plant.get(
            field,
            [],
        ):
            result.append(
                {
                    "level": level,
                    "name": str(
                        name
                    ).strip(),
                }
            )

    return result


def expected_stairs() -> dict[
    str,
    int,
]:
    return {
        normalize_level(
            plant[
                "name"
            ]
        ): int(
            plant.get(
                "stairs",
                0,
            )
        )
        for plant in MIGUEL_H_BASELINE[
            "plants"
        ]
    }


# ============================================================
# LECTURA DEL CONTRATO ACTUAL
# ============================================================


def current_levels(
    contract: dict[str, Any],
) -> list[str]:
    items = find_first_list(
        contract,
        (
            "niveles",
            "levels",
        ),
    )

    result: list[str] = []

    for item in items:
        if isinstance(
            item,
            str,
        ):
            raw = item

        elif isinstance(
            item,
            dict,
        ):
            raw = first_value(
                item,
                (
                    "nombre",
                    "name",
                    "nivel",
                    "level",
                ),
            )

        else:
            continue

        level = normalize_level(
            raw
        )

        if (
            level
            and level not in result
        ):
            result.append(
                level
            )

    return result


def current_axes(
    contract: dict[str, Any],
) -> list[
    dict[str, str]
]:
    items = find_first_list(
        contract,
        (
            "ejes",
            "axes",
        ),
    )

    result: list[
        dict[str, str]
    ] = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        level = normalize_level(
            first_value(
                item,
                (
                    "nivel",
                    "level",
                    "nivelNombre",
                    "level_name",
                ),
            )
        )

        label = str(
            first_value(
                item,
                (
                    "etiqueta",
                    "label",
                    "nombre",
                    "name",
                ),
            )
            or ""
        ).strip().upper()

        if (
            level
            and label
        ):
            result.append(
                {
                    "level": level,
                    "label": label,
                }
            )

    return result


def current_named_entities(
    contract: dict[str, Any],
    *,
    list_keys: tuple[str, ...],
) -> list[
    dict[str, str]
]:
    items = find_first_list(
        contract,
        list_keys,
    )

    result: list[
        dict[str, str]
    ] = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        name = str(
            first_value(
                item,
                (
                    "nombre",
                    "name",
                    "tipo",
                    "type",
                ),
            )
            or ""
        ).strip()

        level = normalize_level(
            first_value(
                item,
                (
                    "nivel",
                    "level",
                    "nivelNombre",
                    "level_name",
                ),
            )
        )

        if name:
            result.append(
                {
                    "level": level,
                    "name": name,
                }
            )

    return result


def current_stairs(
    contract: dict[str, Any],
) -> dict[
    str,
    int,
]:
    items = find_first_list(
        contract,
        (
            "escaleras",
            "stairs",
        ),
    )

    result: dict[
        str,
        int,
    ] = defaultdict(
        int
    )

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        level = normalize_level(
            first_value(
                item,
                (
                    "nivel",
                    "level",
                    "nivelNombre",
                    "level_name",
                ),
            )
        )

        if level:
            result[
                level
            ] += 1

    return dict(
        result
    )


# ============================================================
# AUDIT → AXIS SPANS
# ============================================================


def collect_axis_spans(
    audit: dict[str, Any],
) -> list[
    dict[str, Any]
]:
    result: list[
        dict[str, Any]
    ] = []

    seen: set[
        tuple[Any, ...]
    ] = set()

    for item in walk_dicts(
        audit
    ):
        span_id = str(
            first_value(
                item,
                (
                    "id",
                    "span_id",
                ),
            )
            or ""
        )

        start_label = first_value(
            item,
            (
                "ejeInicioEtiqueta",
                "start_axis_label",
            ),
        )

        end_label = first_value(
            item,
            (
                "ejeFinEtiqueta",
                "end_axis_label",
            ),
        )

        if (
            not span_id.startswith(
                "AXIS_SPAN_"
            )
            and (
                start_label is None
                or end_label is None
            )
        ):
            continue

        level = normalize_level(
            first_value(
                item,
                (
                    "nivel",
                    "level",
                ),
            )
        )

        start_text = str(
            start_label or ""
        ).strip().upper()

        end_text = str(
            end_label or ""
        ).strip().upper()

        if (
            not level
            or not start_text
            or not end_text
        ):
            continue

        value_m = numeric_value(
            first_value(
                item,
                (
                    "valorM",
                    "value_m",
                ),
            )
        )

        state = str(
            first_value(
                item,
                (
                    "estado",
                    "state",
                ),
            )
            or ""
        ).strip().upper()

        evidence = first_value(
            item,
            (
                "evidencia",
                "dimension_evidence",
            ),
        )

        evidence_values: list[
            float
        ] = []

        if isinstance(
            evidence,
            list,
        ):
            for evidence_item in evidence:
                if not isinstance(
                    evidence_item,
                    dict,
                ):
                    continue

                evidence_value = numeric_value(
                    first_value(
                        evidence_item,
                        (
                            "textoOriginal",
                            "text",
                            "valorM",
                            "value_m",
                        ),
                    )
                )

                if evidence_value is not None:
                    evidence_values.append(
                        evidence_value
                    )

        identity = (
            span_id,
            level,
            start_text,
            end_text,
            value_m,
            state,
            tuple(
                evidence_values
            ),
        )

        if identity in seen:
            continue

        seen.add(
            identity
        )

        result.append(
            {
                "id": span_id,
                "level": level,
                "start_label": start_text,
                "end_label": end_text,
                "value_m": value_m,
                "state": state,
                "evidence_values_m": evidence_values,
            }
        )

    return result


# ============================================================
# EVALUADORES
# ============================================================


def pair_key(
    level: str,
    first: str,
    second: str,
) -> tuple[
    str,
    tuple[str, str],
]:
    return (
        normalize_level(
            level
        ),
        tuple(
            sorted(
                (
                    str(
                        first
                    ).strip().upper(),
                    str(
                        second
                    ).strip().upper(),
                )
            )
        ),
    )


def evaluate_levels(
    expected: list[str],
    current: list[str],
) -> dict[str, Any]:
    expected_set = set(
        expected
    )

    current_set = set(
        current
    )

    matched = sorted(
        expected_set
        & current_set
    )

    return {
        "expected": len(
            expected_set
        ),
        "matched": len(
            matched
        ),
        "missing": sorted(
            expected_set
            - current_set
        ),
        "extra_candidates": sorted(
            current_set
            - expected_set
        ),
    }


def evaluate_axes(
    expected: list[
        dict[str, str]
    ],
    current: list[
        dict[str, str]
    ],
) -> dict[str, Any]:
    expected_set = {
        (
            item[
                "level"
            ],
            item[
                "label"
            ],
        )
        for item in expected
    }

    current_set = {
        (
            item[
                "level"
            ],
            item[
                "label"
            ],
        )
        for item in current
    }

    missing = sorted(
        expected_set
        - current_set
    )

    extra = sorted(
        current_set
        - expected_set
    )

    return {
        "expected": len(
            expected_set
        ),
        "matched": len(
            expected_set
            & current_set
        ),
        "missing": [
            {
                "level": level,
                "label": label,
            }
            for level, label in missing
        ],
        "extra_candidates": [
            {
                "level": level,
                "label": label,
            }
            for level, label in extra
        ],
    }


def evaluate_dimensions(
    expected: list[
        dict[str, Any]
    ],
    spans: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    by_pair: dict[
        tuple[
            str,
            tuple[str, str],
        ],
        list[
            dict[str, Any]
        ],
    ] = defaultdict(
        list
    )

    for span in spans:
        by_pair[
            pair_key(
                span[
                    "level"
                ],
                span[
                    "start_label"
                ],
                span[
                    "end_label"
                ],
            )
        ].append(
            span
        )

    details: list[
        dict[str, Any]
    ] = []

    counts: dict[
        str,
        int,
    ] = defaultdict(
        int
    )

    automatic_decisions = 0
    automatic_wrong = 0
    expected_value_observed = 0

    for item in expected:
        candidates = by_pair.get(
            pair_key(
                item[
                    "level"
                ],
                item[
                    "start_label"
                ],
                item[
                    "end_label"
                ],
            ),
            [],
        )

        correct = [
            candidate
            for candidate in candidates
            if (
                candidate[
                    "value_m"
                ]
                is not None
                and same_number(
                    candidate[
                        "value_m"
                    ],
                    item[
                        "value_m"
                    ],
                )
            )
        ]

        wrong_auto = [
            candidate
            for candidate in candidates
            if (
                candidate[
                    "value_m"
                ]
                is not None
                and not same_number(
                    candidate[
                        "value_m"
                    ],
                    item[
                        "value_m"
                    ],
                )
                and candidate[
                    "state"
                ]
                in {
                    "DETECTADO",
                    "INFERIDO",
                }
            )
        ]

        evidence_has_expected = any(
            any(
                same_number(
                    evidence_value,
                    item[
                        "value_m"
                    ],
                )
                for evidence_value
                in candidate[
                    "evidence_values_m"
                ]
            )
            for candidate in candidates
        )

        if correct:
            status = (
                "CORRECTO_GROUNDED"
            )
            automatic_decisions += 1
            expected_value_observed += 1

        elif wrong_auto:
            status = (
                "ERROR_AUTOMATICO"
            )
            automatic_decisions += 1
            automatic_wrong += 1

            if evidence_has_expected:
                expected_value_observed += 1

        elif (
            candidates
            and any(
                candidate[
                    "state"
                ]
                == "CONFLICTO"
                for candidate in candidates
            )
        ):
            status = "CONFLICTO"

            if evidence_has_expected:
                expected_value_observed += 1

        elif evidence_has_expected:
            status = (
                "DETECTADO_NO_GROUNDED"
            )
            expected_value_observed += 1

        elif candidates:
            status = (
                "TRAMO_SIN_COTA_ESPERADA"
            )

        else:
            status = (
                "TRAMO_NO_RESUELTO"
            )

        counts[
            status
        ] += 1

        details.append(
            {
                **item,
                "status": status,
                "candidates": candidates,
            }
        )

    expected_count = len(
        expected
    )

    correct_count = counts[
        "CORRECTO_GROUNDED"
    ]

    return {
        "expected": expected_count,
        "correct_grounded": correct_count,
        "expected_value_observed": (
            expected_value_observed
        ),
        "conflicts": counts[
            "CONFLICTO"
        ],
        "detected_not_grounded": counts[
            "DETECTADO_NO_GROUNDED"
        ],
        "span_without_expected_value": counts[
            "TRAMO_SIN_COTA_ESPERADA"
        ],
        "unresolved_span": counts[
            "TRAMO_NO_RESUELTO"
        ],
        "automatic_wrong": automatic_wrong,
        "automatic_decisions": automatic_decisions,
        "grounding_accuracy": (
            correct_count
            / expected_count
            if expected_count
            else None
        ),
        "expected_value_observation_rate": (
            expected_value_observed
            / expected_count
            if expected_count
            else None
        ),
        "critical_auto_error_rate": (
            automatic_wrong
            / automatic_decisions
            if automatic_decisions
            else None
        ),
        "details": details,
    }


def name_match(
    expected_name: str,
    current_name: str,
) -> int:
    expected = normalize_text(
        expected_name
    )

    current = normalize_text(
        current_name
    )

    if (
        not expected
        or not current
    ):
        return 0

    if expected == current:
        return 3

    shorter = min(
        len(
            expected
        ),
        len(
            current
        ),
    )

    if (
        shorter >= 4
        and (
            expected in current
            or current in expected
        )
    ):
        return 2

    return 0


def evaluate_named_entities(
    expected: list[
        dict[str, str]
    ],
    current: list[
        dict[str, str]
    ],
) -> dict[str, Any]:
    used: set[int] = set()

    matches: list[
        dict[str, Any]
    ] = []

    missing: list[
        dict[str, str]
    ] = []

    for expected_item in expected:
        best_index: int | None = None
        best_score = 0

        for index, current_item in enumerate(
            current
        ):
            if index in used:
                continue

            if (
                expected_item[
                    "level"
                ]
                and current_item[
                    "level"
                ]
                and expected_item[
                    "level"
                ]
                != current_item[
                    "level"
                ]
            ):
                continue

            score = name_match(
                expected_item[
                    "name"
                ],
                current_item[
                    "name"
                ],
            )

            if score > best_score:
                best_score = score
                best_index = index

        if best_index is None:
            missing.append(
                expected_item
            )
            continue

        used.add(
            best_index
        )

        matches.append(
            {
                "expected": expected_item,
                "current": current[
                    best_index
                ],
                "match_type": (
                    "exact"
                    if best_score == 3
                    else "containment"
                ),
            }
        )

    extras = [
        item
        for index, item in enumerate(
            current
        )
        if index not in used
    ]

    return {
        "expected": len(
            expected
        ),
        "matched": len(
            matches
        ),
        "matches": matches,
        "missing": missing,
        "extra_candidates": extras,
        "note": (
            "Los extras se reportan para revisión, "
            "pero no se cuentan automáticamente como error."
        ),
    }


def evaluate_stairs(
    expected: dict[
        str,
        int,
    ],
    current: dict[
        str,
        int,
    ],
) -> dict[str, Any]:
    levels = sorted(
        set(
            expected
        )
        | set(
            current
        )
    )

    matched = 0
    missing = 0
    extra = 0
    details: list[
        dict[str, Any]
    ] = []

    for level in levels:
        expected_count = expected.get(
            level,
            0,
        )

        current_count = current.get(
            level,
            0,
        )

        level_matched = min(
            expected_count,
            current_count,
        )

        level_missing = max(
            0,
            expected_count
            - current_count,
        )

        level_extra = max(
            0,
            current_count
            - expected_count,
        )

        matched += level_matched
        missing += level_missing
        extra += level_extra

        details.append(
            {
                "level": level,
                "expected": expected_count,
                "current": current_count,
                "matched": level_matched,
                "missing": level_missing,
                "extra_candidates": level_extra,
            }
        )

    return {
        "expected": sum(
            expected.values()
        ),
        "matched": matched,
        "missing": missing,
        "extra_candidates": extra,
        "details": details,
    }


# ============================================================
# MARGEN DE INTERVENCIÓN MANUAL
# ============================================================


def manual_intervention_summary(
    *,
    levels: dict[str, Any],
    axes: dict[str, Any],
    dimensions: dict[str, Any],
    spaces: dict[str, Any],
    zones: dict[str, Any],
    stairs: dict[str, Any],
) -> dict[str, Any]:
    expected = {
        "levels": int(
            levels[
                "expected"
            ]
        ),
        "axes": int(
            axes[
                "expected"
            ]
        ),
        "dimensions": int(
            dimensions[
                "expected"
            ]
        ),
        "spaces": int(
            spaces[
                "expected"
            ]
        ),
        "semantic_zones": int(
            zones[
                "expected"
            ]
        ),
        "stairs": int(
            stairs[
                "expected"
            ]
        ),
    }

    correct = {
        "levels": int(
            levels[
                "matched"
            ]
        ),
        "axes": int(
            axes[
                "matched"
            ]
        ),
        "dimensions": int(
            dimensions[
                "correct_grounded"
            ]
        ),
        "spaces": int(
            spaces[
                "matched"
            ]
        ),
        "semantic_zones": int(
            zones[
                "matched"
            ]
        ),
        "stairs": int(
            stairs[
                "matched"
            ]
        ),
    }

    review = {
        category: max(
            0,
            expected[
                category
            ]
            - correct[
                category
            ],
        )
        for category in expected
    }

    total_expected = sum(
        expected.values()
    )

    total_review = sum(
        review.values()
    )

    return {
        "expected_units": total_expected,
        "correct_units": (
            total_expected
            - total_review
        ),
        "manual_intervention_units": total_review,
        "manual_intervention_rate": (
            total_review
            / total_expected
            if total_expected
            else None
        ),
        "review_units_by_category": review,
        "automatic_correction_required": int(
            dimensions.get(
                "automatic_wrong",
                0,
            )
        ),
        "critical_auto_error_rate_dimensions": (
            dimensions.get(
                "critical_auto_error_rate"
            )
        ),
        "interpretation": (
            "manual_intervention_rate mide unidades del "
            "baseline que todavía requieren revisión/corrección. "
            "No equivale a precisión estadística general."
        ),
    }


# ============================================================
# REGRESSION SNAPSHOT
# ============================================================


def regression_snapshot(
    regression: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(
        regression,
        dict,
    ):
        return None

    checks = regression.get(
        "checks",
        [],
    )

    if not isinstance(
        checks,
        list,
    ):
        return None

    counts: dict[
        str,
        int,
    ] = defaultdict(
        int
    )

    for check in checks:
        if not isinstance(
            check,
            dict,
        ):
            continue

        status = str(
            check.get(
                "status",
                "",
            )
        ).strip().upper()

        if status:
            counts[
                status
            ] += 1

    return {
        "status_counts": dict(
            counts
        ),
        "checks": checks,
    }


# ============================================================
# SALIDA
# ============================================================


def print_summary(
    report: dict[str, Any],
) -> None:
    metrics = report[
        "metrics"
    ]

    manual = report[
        "manual_intervention"
    ]

    print()
    print(
        "=============================================="
    )
    print(
        " QUANTIA V2 — MIGUEL H ACCURACY"
    )
    print(
        "=============================================="
    )

    print(
        "Levels: "
        f"{metrics['levels']['matched']}/"
        f"{metrics['levels']['expected']}"
    )

    print(
        "Axes: "
        f"{metrics['axes']['matched']}/"
        f"{metrics['axes']['expected']}"
    )

    print(
        "Dimensions grounded: "
        f"{metrics['dimensions']['correct_grounded']}/"
        f"{metrics['dimensions']['expected']} "
        f"({percent(metrics['dimensions']['grounding_accuracy'])})"
    )

    print(
        "Expected dimension values observed: "
        f"{metrics['dimensions']['expected_value_observed']}/"
        f"{metrics['dimensions']['expected']} "
        f"({percent(metrics['dimensions']['expected_value_observation_rate'])})"
    )

    print(
        "Critical auto-error dimensions: "
        f"{metrics['dimensions']['automatic_wrong']} "
        f"({percent(metrics['dimensions']['critical_auto_error_rate'])})"
    )

    print(
        "Spaces: "
        f"{metrics['spaces']['matched']}/"
        f"{metrics['spaces']['expected']}"
    )

    print(
        "Semantic zones: "
        f"{metrics['semantic_zones']['matched']}/"
        f"{metrics['semantic_zones']['expected']}"
    )

    print(
        "Stairs: "
        f"{metrics['stairs']['matched']}/"
        f"{metrics['stairs']['expected']}"
    )

    print(
        "----------------------------------------------"
    )

    print(
        "Manual intervention: "
        f"{manual['manual_intervention_units']}/"
        f"{manual['expected_units']} "
        f"({percent(manual['manual_intervention_rate'])})"
    )

    print(
        "Automatic corrections required: "
        f"{manual['automatic_correction_required']}"
    )

    print(
        "----------------------------------------------"
    )

    print(
        "No se puntúan muros, puertas ni ventanas "
        "sin baseline exhaustivo."
    )


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compara el pipeline actual de Miguel H "
            "contra el baseline image-only validado."
        )
    )

    parser.add_argument(
        "--audit",
        type=Path,
        default=DEFAULT_AUDIT,
    )

    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
    )

    parser.add_argument(
        "--regression",
        type=Path,
        default=DEFAULT_REGRESSION,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    audit = load_json(
        args.audit
    )

    contract = load_json(
        args.contract
    )

    regression = (
        load_json(
            args.regression
        )
        if args.regression.exists()
        else None
    )

    level_metrics = evaluate_levels(
        expected_levels(),
        current_levels(
            contract
        ),
    )

    axis_metrics = evaluate_axes(
        expected_axes(),
        current_axes(
            contract
        ),
    )

    dimension_metrics = evaluate_dimensions(
        expected_dimensions(),
        collect_axis_spans(
            audit
        ),
    )

    space_metrics = evaluate_named_entities(
        expected_named(
            "spaces"
        ),
        current_named_entities(
            contract,
            list_keys=(
                "espacios",
                "spaces",
            ),
        ),
    )

    zone_metrics = evaluate_named_entities(
        expected_named(
            "semantic_zones"
        ),
        current_named_entities(
            contract,
            list_keys=(
                "zonasSemanticas",
                "zonas_semanticas",
                "semanticZones",
                "semantic_zones",
            ),
        ),
    )

    stair_metrics = evaluate_stairs(
        expected_stairs(),
        current_stairs(
            contract
        ),
    )

    manual = manual_intervention_summary(
        levels=level_metrics,
        axes=axis_metrics,
        dimensions=dimension_metrics,
        spaces=space_metrics,
        zones=zone_metrics,
        stairs=stair_metrics,
    )

    report = {
        "sample": "Miguel H",
        "evaluation_type": (
            "image_only_baseline_vs_current_pipeline"
        ),
        "scope": {
            "scored": [
                "levels",
                "axes",
                "dimension_spans",
                "spaces",
                "semantic_zones",
                "stairs",
            ],
            "not_scored": [
                "walls",
                "doors",
                "windows",
            ],
            "warning": (
                "Este resultado mide el caso Miguel H. "
                "No debe interpretarse como precisión "
                "estadística general de Quantia."
            ),
        },
        "baseline_counts": {
            "levels": len(
                expected_levels()
            ),
            "axes": len(
                expected_axes()
            ),
            "dimension_spans": len(
                expected_dimensions()
            ),
            "spaces": len(
                expected_named(
                    "spaces"
                )
            ),
            "semantic_zones": len(
                expected_named(
                    "semantic_zones"
                )
            ),
            "stairs": sum(
                expected_stairs().values()
            ),
        },
        "metrics": {
            "levels": level_metrics,
            "axes": axis_metrics,
            "dimensions": dimension_metrics,
            "spaces": space_metrics,
            "semantic_zones": zone_metrics,
            "stairs": stair_metrics,
        },
        "manual_intervention": manual,
        "regression_snapshot": (
            regression_snapshot(
                regression
            )
        ),
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print_summary(
        report
    )

    print()
    print(
        "Reporte:"
    )
    print(
        f"  {args.output}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
