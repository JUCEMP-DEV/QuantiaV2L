from __future__ import annotations

import logging
import re
from typing import Any
from app.services.spatial_quantity_inputs import automatic_spatial_inputs
from app.services.spatial_consumption import build_consumption

from app.api.v1.endpoints.catalogos import MODULE_PARTIDAS, execute_catalog_query, safe_text
logger = logging.getLogger("app.motor_simulation_service")


def _to_number(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed


def _to_optional_number(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _collect_engine_inputs(
    *sources: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for source in sources:
        if not isinstance(source, dict):
            continue

        values = source.get("engineInputs")

        if not isinstance(values, dict):
            continue

        for key, value in values.items():
            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            result[str(key)] = value

    return result


def _collect_engine_inputs_by_concept(
    *sources: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        values = source.get("engineInputsByConcept")
        if not isinstance(values, dict):
            continue
        for raw_code, raw_inputs in values.items():
            code = _to_text(raw_code, "").upper()
            if not code or not isinstance(raw_inputs, dict):
                continue
            target = result.setdefault(code, {})
            for key, value in raw_inputs.items():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                target[str(key)] = value
    return result


def _normalize_foundation_type(value: Any) -> str:
    normalized = _to_text(value, "").lower()
    return {
        "mamposteria": "mamposteria_corrida",
        "zapata_aislada": "zapata_aislada_trabe_liga",
        "trabe_liga": "zapata_aislada_trabe_liga",
    }.get(normalized, normalized)


def _round(value: float, decimals: int = 2) -> float:
    return round(float(value or 0.0), decimals)


def _to_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _safe_area(row: dict[str, Any]) -> float:
    area = _to_number(row.get("areaM2") or 0)
    if area > 0:
        return area
    return max(_to_number(row.get("anchoM") or 0), 0.0) * max(_to_number(row.get("largoM") or 0), 0.0)


def _build_spatial_context(
    datos_generales_obra: dict[str, Any] | None = None,
    estructura_espacial: dict[str, Any] | None = None,
    preliminares: dict[str, Any] | None = None,
) -> dict[str, Any]:

    datos = (
        datos_generales_obra
        if isinstance(datos_generales_obra, dict)
        else {}
    )

    estructura = (
        estructura_espacial
        if isinstance(estructura_espacial, dict)
        else {}
    )

    prelim = (
        preliminares
        if isinstance(preliminares, dict)
        else {}
    )

    # -------------------------------------------------
    # 1. Espacios
    # -------------------------------------------------

    espacios = estructura.get("espacios")

    espacios = (
        espacios
        if isinstance(espacios, list)
        else []
    )

    # -------------------------------------------------
    # 2. Área de espacios
    #
    # Es una inferencia geométrica válida si
    # ancho/largo o areaM2 existen realmente.
    # -------------------------------------------------

    area_spaces = sum(
        _safe_area(
            item
            if isinstance(item, dict)
            else {}
        )
        for item in espacios
    )

    # -------------------------------------------------
    # 3. Área de construcción
    #
    # Primero dato explícito.
    # Si no existe, se permite suma geométrica
    # de espacios como inferencia.
    # -------------------------------------------------

    area_construccion_explicit = _to_optional_number(
        datos.get("areaConstruccionM2")
    )

    if (
        area_construccion_explicit is not None
        and area_construccion_explicit >= 0
    ):
        area_construccion = area_construccion_explicit
        area_construccion_source = "project_document_explicit"

    elif area_spaces > 0:
        area_construccion = area_spaces
        area_construccion_source = "ai_geometry_inference"

    else:
        area_construccion = None
        area_construccion_source = None

    # -------------------------------------------------
    # 4. Área de terreno
    #
    # NO asumir que es igual al área construida.
    # -------------------------------------------------

    area_terreno = _to_optional_number(
        datos.get("areaTerrenoM2")
    )

    # -------------------------------------------------
    # 5. Niveles
    # -------------------------------------------------

    levels_from_spaces = {
        _to_text(
            (
                item
                if isinstance(item, dict)
                else {}
            ).get("nivel"),
            "",
        )
        for item in espacios
        if _to_text(
            (
                item
                if isinstance(item, dict)
                else {}
            ).get("nivel"),
            "",
        )
    }

    niveles_explicit = _to_optional_number(
        datos.get("niveles")
    )

    if niveles_explicit is not None:
        levels_count = int(
            max(niveles_explicit, 0)
        )

    elif levels_from_spaces:
        levels_count = len(
            levels_from_spaces
        )

    else:
        levels_count = 0

    # -------------------------------------------------
    # 6. Conteo de espacios
    # -------------------------------------------------

    count_by_type: dict[str, int] = {}

    for item in espacios:
        row = (
            item
            if isinstance(item, dict)
            else {}
        )

        key = _to_text(
            row.get("tipo"),
            "",
        ).lower()

        if not key:
            continue

        count_by_type[key] = (
            count_by_type.get(key, 0)
            + 1
        )

    total_spaces = len(espacios)

    total_banos = (
        count_by_type.get("bano_1", 0)
        + count_by_type.get("bano_2", 0)
        + count_by_type.get(
            "medio_bano",
            0,
        )
    )

    total_recamaras = (
        count_by_type.get(
            "recamara_principal",
            0,
        )
        + count_by_type.get(
            "recamara_2",
            0,
        )
        + count_by_type.get(
            "recamara_3",
            0,
        )
        + count_by_type.get(
            "recamara_4",
            0,
        )
    )

    # -------------------------------------------------
    # 7. Longitud heredada de cimentación
    #
    # Se conserva SOLO por compatibilidad temporal.
    #
    # NO debe alimentar reglas V1.8 directamente
    # porque puede duplicar lados compartidos.
    # -------------------------------------------------

    legacy_linear_ml = 0.0

    for item in espacios:

        row = (
            item
            if isinstance(item, dict)
            else {}
        )

        width = max(
            _to_number(
                row.get("anchoM"),
                0,
            ),
            0,
        )

        length = max(
            _to_number(
                row.get("largoM"),
                0,
            ),
            0,
        )

        lados = (
            row.get("ladosCimentacion")
            if isinstance(
                row.get(
                    "ladosCimentacion"
                ),
                dict,
            )
            else {}
        )

        if lados.get("a1"):
            legacy_linear_ml += width

        if lados.get("a2"):
            legacy_linear_ml += width

        if lados.get("l1"):
            legacy_linear_ml += length

        if lados.get("l2"):
            legacy_linear_ml += length

    # -------------------------------------------------
    # 8. Altura
    #
    # Ya NO existe default 2.60 m.
    # -------------------------------------------------

    altura_promedio = _to_optional_number(
        datos.get("alturaPromedioM")
    )

    altura_nivel_1 = _to_optional_number(
        datos.get("alturaNivel1M")
    )

    if altura_promedio is not None:
        altura_confirmada = altura_promedio

    elif altura_nivel_1 is not None:
        altura_confirmada = altura_nivel_1

    else:
        altura_confirmada = None

    # -------------------------------------------------
    # 9. wallArea heredada
    #
    # Solo se calcula si existe altura explícita.
    # Sigue siendo compatibilidad temporal.
    # -------------------------------------------------

    if (
        legacy_linear_ml > 0
        and altura_confirmada is not None
        and altura_confirmada > 0
    ):
        legacy_wall_area = (
            legacy_linear_ml
            * altura_confirmada
        )
    else:
        legacy_wall_area = None

    # -------------------------------------------------
    # 10. Demolición
    # -------------------------------------------------

    dem = (
        prelim.get("demolicion")
        if isinstance(
            prelim.get("demolicion"),
            dict,
        )
        else {}
    )

    area_demolicion = _to_optional_number(
        dem.get("areaDemolicionM2")
    )

    if area_demolicion is None:
        area_demolicion = _to_optional_number(
            prelim.get(
                "areaDemolicionM2"
            )
        )

    # Solo calcular ancho × largo cuando
    # ambos fueron proporcionados.
    if area_demolicion is None:

        dem_width = _to_optional_number(
            dem.get("anchoDemolicionM")
        )

        dem_length = _to_optional_number(
            dem.get("largoDemolicionM")
        )

        if (
            dem_width is not None
            and dem_length is not None
        ):
            area_demolicion = (
                dem_width
                * dem_length
            )

    # -------------------------------------------------
    # 11. Topografía
    #
    # Ya NO inferimos profundidad por clasificación.
    # -------------------------------------------------

    topografia = _to_text(
        prelim.get("topografia"),
        "",
    ).lower()

    topografia_depth = _to_optional_number(
        prelim.get(
            "pendienteProfundidadM"
        )
    )

    # -------------------------------------------------
    # 12. Área preliminar explícita
    #
    # Ya NO usamos automáticamente
    # areaConstruccion como preliminares.
    # -------------------------------------------------

    area_preliminares = _to_optional_number(
        prelim.get(
            "areaPreliminares"
        )
    )

    if area_preliminares is None:
        area_preliminares = (
            _to_optional_number(
                prelim.get(
                    "superficiePreliminar"
                )
            )
        )

    # -------------------------------------------------
    # 13. Contexto base / compatibilidad
    # -------------------------------------------------

    context: dict[str, Any] = {

        "areaConstruccion": (
            _round(
                area_construccion,
                2,
            )
            if area_construccion
            is not None
            else None
        ),

        "areaConstruccionSource":
            area_construccion_source,

        "areaTerreno": (
            _round(
                area_terreno,
                2,
            )
            if area_terreno
            is not None
            else None
        ),

        "areaPreliminares": (
            _round(
                area_preliminares,
                2,
            )
            if area_preliminares
            is not None
            else None
        ),

        "levelsCount":
            levels_count,

        "totalSpaces":
            total_spaces,

        "totalBanos":
            total_banos,

        "totalRecamaras":
            total_recamaras,

        "countByType":
            count_by_type,

        # Compatibilidad temporal
        "totalLinearMl": (
            _round(
                legacy_linear_ml,
                2,
            )
            if legacy_linear_ml > 0
            else None
        ),

        "foundationLinearMl": (
            _round(
                legacy_linear_ml,
                2,
            )
            if legacy_linear_ml > 0
            else None
        ),

        "wallAreaM2": (
            _round(
                legacy_wall_area,
                2,
            )
            if legacy_wall_area
            is not None
            else None
        ),

        "alturaConfirmadaM":
            altura_confirmada,

        "topografia":
            topografia,

        "topografiaDepthM":
            topografia_depth,

        "areaDemolicionM2":
            area_demolicion,

        "tipoCimentacion":
            _normalize_foundation_type(
                datos.get("tipoCimentacion")
            ),

        "sistemaEstructural":
            _to_text(
                datos.get(
                    "sistemaEstructural"
                ),
                "",
            ).lower(),
    }

    # -------------------------------------------------
    # 14. Inputs canónicos del motor V1.8
    # -------------------------------------------------

    engine_inputs = _collect_engine_inputs(
        datos,
        estructura,
        prelim,
    )

    engine_inputs_by_concept = _collect_engine_inputs_by_concept(
        datos,
        estructura,
        prelim,
    )

    # -------------------------------------------------
    # 15. Compatibilidad directa segura
    #
    # Solo datos explícitos.
    # -------------------------------------------------

    if area_preliminares is not None:
        engine_inputs.setdefault(
            "area_intervenida_confirmada",
            _round(
                area_preliminares,
                4,
            ),
        )

    if area_demolicion is not None:
        engine_inputs.setdefault(
            "area_demolicion_confirmada",
            _round(
                area_demolicion,
                4,
            ),
        )

    # -------------------------------------------------
    # 16. Integrar inputs V1.8 al contexto
    #
    # _resolve_required_inputs() los encontrará
    # directamente mediante context.get(nombre).
    # -------------------------------------------------

    if area_preliminares is not None:
        engine_inputs.setdefault(
            "areas_intervenidas_confirmadas",
            [{
                "areaM2": _round(area_preliminares, 4),
                "scopeRef": "preliminares_area_confirmada",
            }],
        )

    tipo_cimentacion = _normalize_foundation_type(
        datos.get("tipoCimentacion")
    )
    if tipo_cimentacion:
        engine_inputs.setdefault(
            "tipo_cimentacion",
            tipo_cimentacion,
        )

    alturas_nivel: list[float] = []
    for key in ("alturaNivel1M", "alturaNivel2M", "alturaNivel3M"):
        height = _to_optional_number(datos.get(key))
        if height is not None and height >= 0:
            alturas_nivel.append(height)
    if alturas_nivel:
        engine_inputs.setdefault("alturas_nivel", alturas_nivel)

    # La demolición confirmada se limita a PRE-007.
    if area_demolicion is not None:
        engine_inputs_by_concept.setdefault(
            "PRE-007",
            {},
        ).setdefault(
            "geometria_area_confirmada",
            {
                "areaM2": _round(area_demolicion, 4),
                "scopeRef": "demolicion_confirmada",
            },
        )

    context.update(engine_inputs)
    # An assignment confirmed against old geometry must be reviewed again.
    entities = {
        str(item.get("id")): item
        for group in ("espacios", "muros")
        for item in (estructura_espacial or {}).get(group, [])
        if isinstance(item, dict)
    }
    for inputs in engine_inputs_by_concept.values():
        for name, values in list(inputs.items()):
            if not isinstance(values, list):
                continue
            for record in values:
                if not isinstance(record, dict) or record.get("source") != "EDITOR_ASSIGNMENT":
                    continue
                entity = entities.get(str(record.get("scopeRef")))
                snapshot = record.get("sourceSnapshot")
                if not entity or not snapshot or entity.get("confirmed") is not True or any(entity.get(key) != value for key, value in snapshot.items()):
                    inputs[name] = None
                    break
    context["_engineInputsByConcept"] = engine_inputs_by_concept

    # -------------------------------------------------
    # 17. Trazabilidad
    # -------------------------------------------------

    context["engineInputKeys"] = sorted(
        engine_inputs.keys()
    )
    context["engineInputConceptCodes"] = sorted(
        engine_inputs_by_concept.keys()
    )

    return context


def _get_context_value(
    context: dict[str, Any],
    path: str,
) -> Any:

    current: Any = context

    for part in path.split("."):

        if not isinstance(
            current,
            dict,
        ):
            return None

        if part not in current:
            return None

        current = current.get(
            part
        )

    return current


def _matches_activation_condition(
    actual: Any,
    expected: Any,
) -> bool:
    if isinstance(expected, list):
        if isinstance(actual, str):
            return actual.strip().lower() in {
                str(item).strip().lower()
                for item in expected
            }
        return actual in expected

    if isinstance(expected, bool):
        return isinstance(actual, bool) and actual is expected

    if isinstance(expected, str):
        return _to_text(actual, "").lower() == expected.strip().lower()

    return actual == expected




def _evaluate_context_conditions(
    condition: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:

    conditions = condition.get(
        "context_conditions"
    )

    if not isinstance(
        conditions,
        dict,
    ):
        return {
            "matches": True,
            "missing": [],
            "mismatched": [],
        }

    missing: list[str] = []
    mismatched: list[dict[str, Any]] = []

    for field, expected in (
        conditions.items()
    ):

        actual = _get_context_value(
            context,
            field,
        )

        # -------------------------------------
        # El frontend todavía no dio el dato
        # -------------------------------------

        if actual is None:

            missing.append(
                field
            )

            continue

        if (
            isinstance(actual, str)
            and not actual.strip()
        ):

            missing.append(
                field
            )

            continue

        # -------------------------------------
        # Existe dato pero no cumple condición
        # -------------------------------------

        if not _matches_activation_condition(
            actual,
            expected,
        ):

            mismatched.append(
                {
                    "field":
                        field,

                    "expected":
                        expected,

                    "actual":
                        actual,
                }
            )

    return {
        "matches":
            (
                not missing
                and not mismatched
            ),

        "missing":
            missing,

        "mismatched":
            mismatched,
    }


def _evaluate_service_requirement(
    condition: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Evalúa serviciosInstalaciones sin convertir ausencia en True."""
    requirement = (
        condition.get("service_requirement")
        if isinstance(condition.get("service_requirement"), dict)
        else {}
    )

    if not requirement:
        return {
            "active": True,
            "status": None,
            "alerts": [],
            "missingInputs": [],
        }

    container = _to_text(
        requirement.get("container"),
        "serviciosInstalaciones",
    )
    key = _to_text(requirement.get("key"), "")
    required_value = requirement.get("required_value", True)
    false_state = _to_text(
        requirement.get("false_state"),
        "NOT_APPLICABLE",
    ).upper()

    path = f"{container}.{key}" if key else container
    values = context.get(container)

    if (
        not key
        or not isinstance(values, dict)
        or key not in values
        or values.get(key) is None
    ):
        return {
            "active": False,
            "status": "BLOCKED_MISSING_INPUT",
            "alerts": [
                {
                    "code": "MISSING_SERVICE_CONTEXT",
                    "severity": "blocking",
                    "field": path,
                }
            ],
            "missingInputs": [path],
        }

    actual = values.get(key)

    # El contrato de servicios es tri-state real: True / False / unknown.
    if not isinstance(actual, bool):
        return {
            "active": False,
            "status": "BLOCKED_CONFLICT",
            "alerts": [
                {
                    "code": "INVALID_SERVICE_CONTEXT",
                    "severity": "blocking",
                    "field": path,
                    "actual": actual,
                }
            ],
            "missingInputs": [],
        }

    if actual != required_value:
        return {
            "active": False,
            "status": false_state,
            "alerts": [
                {
                    "code": "SERVICE_NOT_APPLICABLE",
                    "severity": "info",
                    "field": path,
                }
            ],
            "missingInputs": [],
        }

    return {
        "active": True,
        "status": None,
        "alerts": [],
        "missingInputs": [],
    }


def _evaluate_activation_rule(
    concept: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    activation = (
        concept.get("activation_rule")
        if isinstance(concept.get("activation_rule"), dict)
        else {}
    )

    spec = (
        concept.get("engine_spec")
        if isinstance(concept.get("engine_spec"), dict)
        else {}
    )

    if not activation:
        return {
            "active": False,
            "status": "BLOCKED_MISSING_INPUT",
            "alerts": [
                {
                    "code": "MISSING_ACTIVATION_RULE",
                    "severity": "blocking",
                }
            ],
        }

    if activation.get("is_active") is False:
        return {
            "active": False,
            "status": "INACTIVE",
            "alerts": [
                {
                    "code": "RULE_INACTIVE",
                    "severity": "blocking",
                }
            ],
        }

    condition = (
        activation.get("condition_json")
        if isinstance(
            activation.get("condition_json"),
            dict,
        )
        else {}
    )

    if condition.get("concept_active") is False:
        return {
            "active": False,
            "status": "INACTIVE",
            "alerts": [
                {
                    "code": "CONCEPT_INACTIVE",
                    "severity": "blocking",
                }
            ],
        }

    # -------------------------------------------------
    # Servicio de Instalaciones — tri-state V1.8
    # -------------------------------------------------

    service_evaluation = _evaluate_service_requirement(
        condition,
        context,
    )

    if not service_evaluation.get("active", True):
        return {
            "active": False,
            "status": service_evaluation.get(
                "status",
                "BLOCKED_MISSING_INPUT",
            ),
            "alerts": service_evaluation.get("alerts", []),
            "missingInputs": service_evaluation.get(
                "missingInputs",
                [],
            ),
            "requiresProjectDefinition": bool(
                condition.get(
                    "requires_project_definition",
                    spec.get(
                        "requires_project_definition",
                        False,
                    ),
                )
            ),
        }

    # -------------------------------------------------
    # Condiciones de parametrización / proyecto
    # -------------------------------------------------

    context_evaluation = (
        _evaluate_context_conditions(
            condition,
            context,
        )
    )

    # -------------------------------------------------
    # Falta un dato necesario para saber si aplica
    # -------------------------------------------------

    if context_evaluation.get(
        "missing"
    ):

        return {
            "active": False,

            "status":
                "BLOCKED_MISSING_INPUT",

            "alerts": [
                {
                    "code":
                        "MISSING_ACTIVATION_CONTEXT",

                    "severity":
                        "blocking",

                    "missingFields":
                        context_evaluation.get(
                            "missing",
                            [],
                        ),
                }
            ],
        }

    # -------------------------------------------------
    # Tenemos el dato y el concepto no corresponde
    # al proyecto.
    # Esto NO es error.
    # -------------------------------------------------

    if context_evaluation.get(
        "mismatched"
    ):

        return {
            "active": False,

            "status":
                "NOT_APPLICABLE",

            "alerts": [
                {
                    "code":
                        "ACTIVATION_CONDITION_NOT_MATCHED",

                    "severity":
                        "info",

                    "conditions":
                        context_evaluation.get(
                            "mismatched",
                            [],
                        ),
                }
            ],
        }



    requires_project_definition = bool(
        condition.get(
            "requires_project_definition",
            spec.get(
                "requires_project_definition",
                False,
            ),
        )
    )

    return {
        "active": True,
        "status": "PROPOSED",
        "requiresProjectDefinition":
            requires_project_definition,
        "alerts": [],
    }


def _resolve_required_inputs(
    concept: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    spec = (
        concept.get("engine_spec")
        if isinstance(concept.get("engine_spec"), dict)
        else {}
    )
    parameter_rules = (
        spec.get("parameter_rules")
        if isinstance(spec.get("parameter_rules"), dict)
        else {}
    )
    required_inputs = parameter_rules.get("required_inputs", [])
    if not isinstance(required_inputs, list):
        required_inputs = []

    code = _to_text(concept.get("code"), "").upper()
    by_concept = context.get("_engineInputsByConcept")
    by_concept = by_concept if isinstance(by_concept, dict) else {}
    concept_inputs = by_concept.get(code)
    concept_inputs = concept_inputs if isinstance(concept_inputs, dict) else {}

    missing_inputs: list[str] = []
    resolved_inputs: dict[str, Any] = {}

    for input_name in required_inputs:
        if input_name in concept_inputs:
            value = concept_inputs.get(input_name)
        elif input_name in context:
            value = context.get(input_name)
        else:
            missing_inputs.append(input_name)
            continue

        if value is None:
            missing_inputs.append(input_name)
            continue
        if isinstance(value, str) and not value.strip():
            missing_inputs.append(input_name)
            continue

        resolved_inputs[input_name] = value

    return {
        "requiredInputs": required_inputs,
        "resolvedInputs": resolved_inputs,
        "missingInputs": missing_inputs,
        "complete": not missing_inputs,
        "inputScope": "concept" if concept_inputs else "global",
    }



def _get_inference_strategy(
    concept: dict[str, Any],
) -> str:
    spec = (
        concept.get("engine_spec")
        if isinstance(concept.get("engine_spec"), dict)
        else {}
    )

    return _to_text(
        spec.get("inference_strategy"),
        "",
    ).lower()


def _positive_or_zero(
    value: Any,
) -> float | None:
    parsed = _to_optional_number(value)

    if parsed is None:
        return None

    if parsed < 0:
        return None

    return parsed


def _sum_confirmed_measure(
    value: Any,
    measure: str,
) -> float | None:
    """
    Convierte inputs explícitos del frontend en una medida total.

    Admite:
        número directo
        lista de números
        lista de objetos geométricos
        objeto geométrico individual

    NO asigna dimensiones por defecto.
    """

    if value is None:
        return None

    # ---------------------------------
    # Valor numérico directo
    # ---------------------------------

    if isinstance(
        value,
        (int, float),
    ):
        return (
            float(value)
            if float(value) >= 0
            else None
        )

    # ---------------------------------
    # Lista de elementos
    # ---------------------------------

    if isinstance(value, list):
        total = 0.0

        for item in value:
            measured = _sum_confirmed_measure(
                item,
                measure,
            )

            if measured is None:
                # Si existe un elemento sin información
                # suficiente, no ignorarlo silenciosamente.
                return None

            total += measured

        return total

    # ---------------------------------
    # Objeto
    # ---------------------------------

    if not isinstance(value, dict):
        return None

    # ---------------------------------
    # LONGITUD
    # ---------------------------------

    if measure == "length":

        for key in (
            "longitudM",
            "longitud",
            "lengthM",
            "length",
            "ml",
            "value",
        ):
            parsed = _positive_or_zero(
                value.get(key)
            )

            if parsed is not None:
                return parsed

        # Elemento repetido:
        # cantidad × altura.
        cantidad = _positive_or_zero(
            value.get("cantidad")
        )

        altura = _positive_or_zero(
            value.get("alturaM")
        )

        if (
            cantidad is not None
            and altura is not None
        ):
            return cantidad * altura

        return None

    # ---------------------------------
    # ÁREA
    # ---------------------------------

    if measure == "area":

        for key in (
            "areaM2",
            "area",
            "area_m2",
            "value",
        ):
            parsed = _positive_or_zero(
                value.get(key)
            )

            if parsed is not None:
                return parsed

        ancho = _positive_or_zero(
            value.get("anchoM")
        )

        largo = _positive_or_zero(
            value.get("largoM")
        )

        if (
            ancho is not None
            and largo is not None
        ):
            return ancho * largo

        longitud = _positive_or_zero(
            value.get("longitudM")
        )

        altura = _positive_or_zero(
            value.get("alturaM")
        )

        if (
            longitud is not None
            and altura is not None
        ):
            return longitud * altura

        return None

    # ---------------------------------
    # VOLUMEN
    # ---------------------------------

    if measure == "volume":

        for key in (
            "volumenM3",
            "volumen",
            "volumeM3",
            "volume",
            "value",
        ):
            parsed = _positive_or_zero(
                value.get(key)
            )

            if parsed is not None:
                return parsed

        largo = _positive_or_zero(
            value.get("largoM")
        )

        ancho = _positive_or_zero(
            value.get("anchoM")
        )

        profundidad = _positive_or_zero(
            value.get("profundidadM")
        )

        if (
            largo is not None
            and ancho is not None
            and profundidad is not None
        ):
            return (
                largo
                * ancho
                * profundidad
            )

        return None

    # ---------------------------------
    # PESO
    # ---------------------------------

    if measure == "weight":

        for key in (
            "pesoKg",
            "peso",
            "kg",
            "value",
        ):
            parsed = _positive_or_zero(
                value.get(key)
            )

            if parsed is not None:
                return parsed

        return None

    # ---------------------------------
    # CONTEO
    # ---------------------------------

    if measure == "count":

        for key in (
            "cantidad",
            "count",
            "piezas",
            "value",
        ):
            parsed = _positive_or_zero(
                value.get(key)
            )

            if parsed is not None:
                return parsed

        # Si el objeto representa una pieza
        # confirmada individual.
        return 1.0

    return None


def _calculate_vanos_aristas_length(
    value: Any,
) -> float | None:

    if isinstance(value, (int, float)):
        return _positive_or_zero(value)

    if not isinstance(value, list):
        return None

    total = 0.0

    for item in value:

        if not isinstance(item, dict):
            return None

        tipo = _to_text(
            item.get("tipo"),
            "",
        ).lower()

        if tipo == "ventana":

            ancho = _positive_or_zero(
                item.get("anchoM")
            )

            alto = _positive_or_zero(
                item.get("altoM")
            )

            if (
                ancho is None
                or alto is None
            ):
                return None

            total += (
                2 * ancho
                + 2 * alto
            )

        elif tipo == "puerta":

            ancho = _positive_or_zero(
                item.get("anchoM")
            )

            alto = _positive_or_zero(
                item.get("altoM")
            )

            if (
                ancho is None
                or alto is None
            ):
                return None

            total += (
                ancho
                + 2 * alto
            )

        elif tipo in {
            "pretil",
            "arista",
            "remate",
        }:

            longitud = _positive_or_zero(
                item.get("longitudM")
            )

            if longitud is None:
                return None

            total += longitud

        else:
            return None

    return total


def _calculate_wet_wall_area(
    walls: Any,
    height: Any,
    openings: Any,
) -> float | None:

    # Primero intentamos recibir ya
    # superficies explícitas.
    gross_area = _sum_confirmed_measure(
        walls,
        "area",
    )

    # Si se recibieron longitudes de muro,
    # necesitamos altura explícita.
    if gross_area is None:

        total_length = _sum_confirmed_measure(
            walls,
            "length",
        )

        wall_height = _positive_or_zero(
            height
        )

        if (
            total_length is None
            or wall_height is None
        ):
            return None

        gross_area = (
            total_length
            * wall_height
        )

    opening_area = _sum_confirmed_measure(
        openings,
        "area",
    )

    # Lista explícitamente vacía = cero vanos.
    if openings == []:
        opening_area = 0.0

    if opening_area is None:
        return None

    return max(
        gross_area - opening_area,
        0.0,
    )


def _calculate_net_wall_area(
    walls: Any,
    openings: Any,
    castillos: Any,
) -> float | None:

    wall_area = _sum_confirmed_measure(
        walls,
        "area",
    )

    if wall_area is None:
        return None

    opening_area = _sum_confirmed_measure(
        openings,
        "area",
    )

    if openings == []:
        opening_area = 0.0

    castillo_area = _sum_confirmed_measure(
        castillos,
        "area",
    )

    if castillos == []:
        castillo_area = 0.0

    if (
        opening_area is None
        or castillo_area is None
    ):
        return None

    return max(
        wall_area
        - opening_area
        - castillo_area,
        0.0,
    )


def _extract_level_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return _to_optional_number(value)
    if not isinstance(value, dict):
        return None
    for key in ("nivelM", "cotaM", "elevationM", "elevation", "nivel", "value"):
        parsed = _to_optional_number(value.get(key))
        if parsed is not None:
            return parsed
    return None


def _calculate_excavation_geometry_volume(
    geometry: Any,
    confirmed_depth: Any,
) -> float | None:
    depth = _positive_or_zero(confirmed_depth)
    if depth is None:
        return None

    if isinstance(geometry, list):
        total = 0.0
        for item in geometry:
            measured = _calculate_excavation_geometry_volume(item, depth)
            if measured is None:
                return None
            total += measured
        return total

    if not isinstance(geometry, dict):
        return None

    for key in ("volumenM3", "volumen", "volumeM3", "volume"):
        direct = _positive_or_zero(geometry.get(key))
        if direct is not None:
            return direct

    area = None
    for key in ("areaM2", "area", "area_m2"):
        area = _positive_or_zero(geometry.get(key))
        if area is not None:
            break

    if area is None:
        largo = _positive_or_zero(geometry.get("largoM"))
        ancho = _positive_or_zero(geometry.get("anchoM"))
        if largo is not None and ancho is not None:
            area = largo * ancho

    if area is None:
        longitud = _positive_or_zero(geometry.get("longitudM"))
        ancho = _positive_or_zero(geometry.get("anchoM"))
        if longitud is not None and ancho is not None:
            area = longitud * ancho

    if area is None:
        return None

    local_depth = _positive_or_zero(geometry.get("profundidadM"))
    if local_depth is None:
        local_depth = depth

    return area * local_depth


def _calculate_cut_volume_by_surfaces(
    existing_surface: Any,
    project_level: Any,
) -> float | None:
    project = _extract_level_value(project_level)
    if project is None:
        return None

    if isinstance(existing_surface, list):
        total = 0.0
        for zone in existing_surface:
            measured = _calculate_cut_volume_by_surfaces(zone, project)
            if measured is None:
                return None
            total += measured
        return total

    if not isinstance(existing_surface, dict):
        return None

    for key in ("volumenCorteM3", "volumenM3", "volumen"):
        direct = _positive_or_zero(existing_surface.get(key))
        if direct is not None:
            return direct

    area = None
    for key in ("areaM2", "area", "area_m2"):
        area = _positive_or_zero(existing_surface.get(key))
        if area is not None:
            break
    if area is None:
        return None

    # Simplificación permitida sólo con profundidad media explícita.
    for key in ("profundidadMediaM", "profundidad_media_m"):
        avg_depth = _positive_or_zero(existing_surface.get(key))
        if avg_depth is not None:
            return area * avg_depth

    existing_level = _extract_level_value(existing_surface)
    if existing_level is None:
        return None

    return area * max(existing_level - project, 0.0)


def _collect_scope_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key in ("scopeRef", "scope_ref"):
            ref = _to_text(value.get(key), "")
            if ref:
                refs.add(ref)
        for child in value.values():
            refs.update(_collect_scope_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_collect_scope_refs(child))
    return refs


def _execute_inference_strategy(
    concept: dict[str, Any],
    context: dict[str, Any],
    resolved_inputs: dict[str, Any],
) -> dict[str, Any]:

    strategy = _get_inference_strategy(
        concept
    )

    quantity: float | None = None

    evidence: list[dict[str, Any]] = []

    alerts: list[dict[str, Any]] = []

    scope_refs = sorted(
        _collect_scope_refs(resolved_inputs)
    )

    # =================================================
    # ESTRATEGIAS GENÉRICAS SEGURAS
    # =================================================

    if strategy in {
        "area_neta_confirmada",
        "area_firme_neta",
        "area_firme_reforzado",
        "area_andador",
    }:

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "geometria_area_confirmada"
            )
            if "geometria_area_confirmada"
            in resolved_inputs
            else resolved_inputs.get(
                "areas_andador_confirmadas"
            ),
            "area",
        )

    elif strategy in {
        "longitud_neta_confirmada",
        "longitud_muro_cimentacion",
        "longitud_guarnicion",
        "longitud_barandal",
    }:

        source = (
            resolved_inputs.get(
                "geometria_longitud_confirmada"
            )
            if "geometria_longitud_confirmada"
            in resolved_inputs
            else resolved_inputs.get(
                "tramos_guarnicion_confirmados"
            )
        )

        if source is None:
            source = resolved_inputs.get(
                "tramos_barandal_confirmados"
            )

        quantity = _sum_confirmed_measure(
            source,
            "length",
        )

    elif strategy in {
        "volumen_geometrico_confirmado",
        "volumen_directo_confirmado",
        "volumen_relleno_neto",
    }:

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "geometria_volumen_confirmada"
            ),
            "volume",
        )

    elif strategy in {
        "conteo_piezas_confirmadas",
        "conteo_por_mueble",
        "conteo_por_servicio",
        "conteo_bajantes_confirmados",
    }:

        source = resolved_inputs.get(
            "cantidad_piezas_confirmada"
        )

        if source is None:
            source = resolved_inputs.get(
                "cantidad_salidas_confirmada"
            )

        quantity = _sum_confirmed_measure(
            source,
            "count",
        )

    elif strategy in {
        "conteo_salidas_confirmadas",
        "conteo_electrico_plano_o_propuesta",
    }:

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "cantidad_salidas_confirmada"
            ),
            "count",
        )

    elif strategy == "conteo_tramites_confirmados":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "cantidad_tramites_confirmada"
            ),
            "count",
        )

    elif strategy == "cantidad_directa_confirmada":

        quantity = _positive_or_zero(
            resolved_inputs.get(
                "cantidad_confirmada"
            )
        )

    # =================================================
    # PRELIMINARES
    # =================================================

    elif strategy == "suma_areas_intervencion":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "areas_intervenidas_confirmadas"
            ),
            "area",
        )

    elif strategy == "area_por_espesor_despalme":

        area = _sum_confirmed_measure(
            resolved_inputs.get(
                "area_intervenida_confirmada"
            ),
            "area",
        )

        if area is not None:

            thickness = _positive_or_zero(
                resolved_inputs.get(
                    "espesor_despalme_confirmado"
                )
            )
            thickness_source = "user_confirmed"
            if thickness is None:
                thickness = 0.15
                thickness_source = "documentacion_v1_8"

            quantity = area * thickness

            evidence.append(
                {
                    "source":
                        thickness_source,
                    "parameter":
                        "despalme_thickness_m",
                    "value":
                        thickness,
                }
            )

    elif strategy == "excavacion_cimentacion_por_geometria":

        quantity = _calculate_excavation_geometry_volume(
            resolved_inputs.get("geometria_excavacion"),
            resolved_inputs.get("profundidad_confirmada"),
        )
        if quantity is not None:
            evidence.append(
                {
                    "source": "engine_input",
                    "parameter": "tipo_cimentacion",
                    "value": resolved_inputs.get("tipo_cimentacion"),
                }
            )

    elif strategy == "corte_topografico_por_superficies":

        quantity = _calculate_cut_volume_by_surfaces(
            resolved_inputs.get("superficie_existente"),
            resolved_inputs.get("nivel_proyecto"),
        )

    elif strategy == "balance_tierras_retiro":

        generated = _sum_confirmed_measure(
            resolved_inputs.get(
                "volumen_generado"
            ),
            "volume",
        )

        reused = _sum_confirmed_measure(
            resolved_inputs.get(
                "volumen_reutilizado"
            ),
            "volume",
        )

        if (
            generated is not None
            and reused is not None
        ):

            quantity = max(
                generated - reused,
                0.0,
            )

    elif strategy == "balance_tierras_relleno_reutilizable":

        required = _sum_confirmed_measure(
            resolved_inputs.get(
                "volumen_relleno_requerido"
            ),
            "volume",
        )

        reusable = _sum_confirmed_measure(
            resolved_inputs.get(
                "material_reutilizable_apto"
            ),
            "volume",
        )

        if (
            required is not None
            and reusable is not None
        ):

            # PRE-006 representa solamente
            # el relleno cubierto con material reutilizable.
            quantity = min(
                required,
                reusable,
            )

            faltante = max(
                required - reusable,
                0.0,
            )

            if faltante > 0:

                alerts.append(
                    {
                        "code":
                            "RELLENO_EXTERNO_REQUERIDO",
                        "severity":
                            "warning",
                        "faltanteM3":
                            _round(
                                faltante,
                                4,
                            ),
                    }
                )

    # =================================================
    # CIMENTACIÓN
    # =================================================

    elif strategy == "longitud_zapata_corrida":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "tramos_zapata_corrida_confirmados"
            ),
            "length",
        )

    elif strategy == "conteo_zapata_080":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "cantidad_zapatas_080_confirmada"
            ),
            "count",
        )

    elif strategy == "conteo_zapata_100":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "cantidad_zapatas_100_confirmada"
            ),
            "count",
        )

    elif strategy == "conteo_dados_confirmados":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "cantidad_dados_confirmada"
            ),
            "count",
        )

    elif strategy == "longitud_dala_desplante":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "tramos_dala_desplante_confirmados"
            ),
            "length",
        )

    elif strategy == "longitud_contratrabe_20x30":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "tramos_contratrabe_20x30_confirmados"
            ),
            "length",
        )

    # =================================================
    # ESTRUCTURA
    # =================================================

    elif strategy == "longitud_castillos_unicos":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "castillos_unicos_confirmados"
            ),
            "length",
        )

        # alturas_nivel se conserva como
        # dato de comprobación/evidencia.
        if quantity is not None:

            evidence.append(
                {
                    "source":
                        "engine_input",
                    "parameter":
                        "alturas_nivel",
                    "value":
                        resolved_inputs.get(
                            "alturas_nivel"
                        ),
                }
            )

    elif strategy == "longitud_cadenas_cerramiento":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "tramos_cadena_confirmados"
            ),
            "length",
        )

    elif strategy == "longitud_columnas_confirmadas":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "columnas_confirmadas"
            ),
            "length",
        )

    elif strategy == "longitud_trabes_confirmadas":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "trabes_confirmadas"
            ),
            "length",
        )

    elif strategy in {
        "area_neta_losa_maciza",
        "area_neta_losa_vigueta_bovedilla",
        "area_neta_losa_nervada",
    }:

        gross_area = _sum_confirmed_measure(
            resolved_inputs.get(
                "poligono_losa"
            ),
            "area",
        )

        openings = _sum_confirmed_measure(
            resolved_inputs.get(
                "huecos_no_losa"
            ),
            "area",
        )

        if resolved_inputs.get(
            "huecos_no_losa"
        ) == []:
            openings = 0.0

        if (
            gross_area is not None
            and openings is not None
        ):

            quantity = max(
                gross_area - openings,
                0.0,
            )

    elif strategy == "peso_acero_confirmado":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "despiece_o_peso_acero_confirmado"
            ),
            "weight",
        )

    # =================================================
    # ALBAÑILERÍA
    # =================================================

    elif strategy == "area_neta_muro_descuentos":

        quantity = _calculate_net_wall_area(
            resolved_inputs.get(
                "muros_sistema_confirmados"
            ),
            resolved_inputs.get(
                "vanos"
            ),
            resolved_inputs.get(
                "castillos"
            ),
        )

    elif strategy == "area_caras_confirmadas":

        # Las caras que llegan aquí deben estar
        # explícitamente confirmadas por usuario/IA.
        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "caras_a_aplanar_confirmadas"
            ),
            "area",
        )

    elif strategy == "perimetro_vanos_y_aristas":

        quantity = _calculate_vanos_aristas_length(
            resolved_inputs.get(
                "vanos_y_aristas_confirmados"
            )
        )

    # =================================================
    # ACABADOS
    # =================================================

    elif strategy == "area_neta_piso":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "geometria_area_confirmada"
            ),
            "area",
        )

    elif strategy == "perimetro_neto_zoclo":

        gross_perimeter = _sum_confirmed_measure(
            resolved_inputs.get(
                "perimetros"
            ),
            "length",
        )

        excluded_length = _sum_confirmed_measure(
            resolved_inputs.get(
                "puertas_y_tramos_excluidos"
            ),
            "length",
        )

        if resolved_inputs.get(
            "puertas_y_tramos_excluidos"
        ) == []:
            excluded_length = 0.0

        if (
            gross_perimeter is not None
            and excluded_length is not None
        ):
            quantity = max(
                gross_perimeter - excluded_length,
                0.0,
            )

            evidence.append(
                {
                    "source": "engine_input",
                    "parameter": "espacios_con_zoclo",
                    "value": resolved_inputs.get(
                        "espacios_con_zoclo"
                    ),
                }
            )

    elif strategy == "area_neta_muros_humedos":

        quantity = _calculate_wet_wall_area(
            resolved_inputs.get(
                "muros_humedos_confirmados"
            ),
            resolved_inputs.get(
                "altura_recubrimiento"
            ),
            resolved_inputs.get(
                "vanos"
            ),
        )

    elif strategy == "area_muros_mas_boquillas":

        wall_area = _sum_confirmed_measure(
            resolved_inputs.get(
                "area_muros_pintar"
            ),
            "area",
        )

        boquilla_length = _sum_confirmed_measure(
            resolved_inputs.get(
                "longitud_boquillas_si_aplica"
            ),
            "length",
        )

        if (
            wall_area is not None
            and boquilla_length is not None
        ):

            boquilla_width = 0.15

            quantity = (
                wall_area
                + (
                    boquilla_length
                    * boquilla_width
                )
            )

            evidence.append(
                {
                    "source":
                        "documentacion_v1_4",
                    "parameter":
                        "boquilla_width_m",
                    "value":
                        boquilla_width,
                }
            )

    # =================================================
    # CANCELERÍA
    # =================================================

    elif strategy == "area_real_canceleria":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "dimensiones_ventanas_confirmadas"
            ),
            "area",
        )

    # =================================================
    # OBRAS COMPLEMENTARIAS
    # =================================================

    elif strategy == "longitud_guarnicion":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "tramos_guarnicion_confirmados"
            ),
            "length",
        )

    elif strategy == "area_andador":

        quantity = _sum_confirmed_measure(
            resolved_inputs.get(
                "areas_andador_confirmadas"
            ),
            "area",
        )

    # =================================================
    # ESTRATEGIA NO IMPLEMENTADA
    # =================================================

    else:

        return {
            "quantity": None,

            "status":
                "BLOCKED_MISSING_INPUT",

            "evidence":
                evidence,

            "scopeRefs":
                scope_refs,

            "alerts": [
                {
                    "code":
                        "INFERENCE_STRATEGY_NOT_IMPLEMENTED",

                    "strategy":
                        strategy,

                    "severity":
                        "blocking",
                }
            ],
        }

    # =================================================
    # RESULTADO
    # =================================================

    if quantity is None:

        return {
            "quantity": None,

            "status":
                "BLOCKED_MISSING_INPUT",

            "evidence":
                evidence,

            "scopeRefs":
                scope_refs,

            "alerts":
                alerts
                + [
                    {
                        "code":
                            "INPUT_FORMAT_NOT_COMPUTABLE",

                        "strategy":
                            strategy,

                        "severity":
                            "blocking",
                    }
                ],
        }

    return {
        "quantity":
            _round(
                quantity,
                4,
            ),

        "status":
            "PROPOSED",

        "evidence":
            evidence,

        "scopeRefs":
            scope_refs,

        "alerts":
            alerts,
    }


def _validate_quantity(
    concept: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    quantity = result.get("quantity")

    alerts = list(
        result.get("alerts")
        if isinstance(
            result.get("alerts"),
            list,
        )
        else []
    )

    if quantity is None:
        return {
            **result,
            "status": "BLOCKED_MISSING_INPUT",
            "alerts": alerts,
        }

    if _to_number(quantity, -1) < 0:
        alerts.append(
            {
                "code": "NEGATIVE_QUANTITY",
                "severity": "blocking",
            }
        )

        return {
            **result,
            "quantity": None,
            "status": "BLOCKED_CONFLICT",
            "alerts": alerts,
        }

    unit_code = _to_text(
        concept.get("unit_code"),
        "",
    )

    if not unit_code:
        alerts.append(
            {
                "code": "MISSING_UNIT",
                "severity": "blocking",
            }
        )

        return {
            **result,
            "status": "BLOCKED_CONFLICT",
            "alerts": alerts,
        }

    return {
        **result,
        "status": "PROPOSED",
        "alerts": alerts,
    }


def _extract_scope_refs(
    result: dict[str, Any],
) -> set[str]:

    refs: set[str] = set()

    scope_refs = result.get(
        "scopeRefs"
    )

    if isinstance(scope_refs, list):

        for item in scope_refs:

            text = _to_text(
                item,
                "",
            )

            if text:
                refs.add(text)

    evidence = result.get(
        "evidence"
    )

    if isinstance(evidence, list):

        for item in evidence:

            if not isinstance(
                item,
                dict,
            ):
                continue

            scope_ref = _to_text(
                item.get("scopeRef"),
                "",
            )

            if scope_ref:
                refs.add(
                    scope_ref
                )

    return refs


def _apply_exclusions(
    concept: dict[str, Any],
    results_by_code: dict[str, dict[str, Any]],
    current_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = (
        concept.get("engine_spec")
        if isinstance(concept.get("engine_spec"), dict)
        else {}
    )
    exclusions = spec.get("exclusions_json", [])
    if not isinstance(exclusions, list):
        exclusions = []

    alerts: list[dict[str, Any]] = []
    blocking = False
    current_scope_refs = _extract_scope_refs(
        current_result if isinstance(current_result, dict) else {}
    )

    for exclusion in exclusions:
        if not isinstance(exclusion, dict):
            continue
        excluded_codes = exclusion.get("concepts", [])
        if not isinstance(excluded_codes, list):
            continue

        for excluded_code in excluded_codes:
            related_code = _to_text(excluded_code, "").upper()
            related = results_by_code.get(related_code)
            if not related:
                continue

            related_status = _to_text(
                related.get("status"), ""
            ).upper()
            if related_status not in {"PROPOSED", "CONFIRMED"}:
                continue

            related_scope_refs = _extract_scope_refs(related)
            same_scope = bool(
                current_scope_refs
                and related_scope_refs
                and (current_scope_refs & related_scope_refs)
            )

            if same_scope:
                blocking = True
                alert_code = "CONFIRMED_SCOPE_EXCLUSION"
                severity = "blocking"
            else:
                alert_code = "POTENTIAL_SCOPE_EXCLUSION"
                severity = "warning"

            alerts.append(
                {
                    "code": alert_code,
                    "relatedConcept": related_code,
                    "scope": exclusion.get("scope"),
                    "rule": exclusion.get("rule"),
                    "severity": severity,
                }
            )

    return {"blocking": blocking, "alerts": alerts}




def _run_declarative_validations(
    concept: dict[str, Any],
    context: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:

    spec = (
        concept.get("engine_spec")
        if isinstance(
            concept.get("engine_spec"),
            dict,
        )
        else {}
    )

    activation = (
        concept.get("activation_rule")
        if isinstance(
            concept.get("activation_rule"),
            dict,
        )
        else {}
    )

    validations = (
        spec.get("validations_json")
        if isinstance(
            spec.get("validations_json"),
            dict,
        )
        else {}
    )

    alerts: list[dict[str, Any]] = []

    blocking = False

    handled: set[str] = set()

    # ==========================================
    # 1. Identidad del concepto
    # ==========================================

    concept_id = _to_text(
        concept.get("concept_id"),
        "",
    )

    spec_concept_id = _to_text(
        spec.get("concept_id"),
        "",
    )

    if (
        concept_id
        and spec_concept_id
        and concept_id
        != spec_concept_id
    ):

        blocking = True

        alerts.append(
            {
                "code":
                    "CONCEPT_ID_MISMATCH",

                "severity":
                    "blocking",

                "catalogConceptId":
                    concept_id,

                "specConceptId":
                    spec_concept_id,
            }
        )

    # ==========================================
    # 2. Unidad
    # ==========================================

    derivation = (
        activation.get(
            "derivation_json"
        )
        if isinstance(
            activation.get(
                "derivation_json"
            ),
            dict,
        )
        else {}
    )

    derivation_unit = _to_text(
        derivation.get("unit"),
        "",
    ).lower()

    catalog_unit = _to_text(
        concept.get("unit_symbol"),
        _to_text(
            concept.get("unit_code"),
            "",
        ),
    ).lower()

    if (
        derivation_unit
        and catalog_unit
        and derivation_unit
        != catalog_unit
    ):

        blocking = True

        alerts.append(
            {
                "code":
                    "UNIT_MISMATCH",

                "severity":
                    "blocking",

                "catalogUnit":
                    catalog_unit,

                "ruleUnit":
                    derivation_unit,
            }
        )

    # ==========================================
    # 3. Profundidad máxima CIM-003/003A
    # ==========================================

    code = _to_text(
        concept.get("code"),
        "",
    ).upper()

    if code in {
        "CIM-003",
        "CIM-003A",
    }:

        depth = _to_optional_number(
            context.get(
                "profundidad_excavacion_confirmada"
            )
        )

        if depth is None:

            depth = _to_optional_number(
                context.get(
                    "excavation_depth_m"
                )
            )

        if (
            depth is not None
            and depth > 1.00
        ):

            blocking = True

            alerts.append(
                {
                    "code":
                        "MAX_EXCAVATION_DEPTH_EXCEEDED",

                    "severity":
                        "blocking",

                    "value":
                        depth,

                    "max":
                        1.00,
                }
            )

    # ==========================================
    # 4. EST-009
    # No duplicar acero
    # ==========================================

    if code == "EST-009":

        steel_integrated = context.get(
            "acero_integrado_en_tarjeta_estructural"
        )

        if steel_integrated is True:

            blocking = True

            alerts.append(
                {
                    "code":
                        "REINFORCEMENT_ALREADY_INCLUDED",

                    "severity":
                        "blocking",
                }
            )

    # ==========================================
    # 5. Mantener trazabilidad de validaciones
    # que todavía no tienen ejecutor específico.
    # ==========================================

    declared_specific = validations.get(
        "specific",
        [],
    )

    if not isinstance(
        declared_specific,
        list,
    ):
        declared_specific = []

    known_validations = {
        "block_if_required_project_definition_missing",
        "excavation_depth_m <= 1.00",
        "footing_variant_must_match_confirmed_design",
        "boquilla_area_m2 = boquilla_length_m * 0.15",
        "avoid_duplicate_wall_and_boquilla_surfaces",
        "retirement_volume_excludes_reused_material",
        "deduct_doors_windows_and_castillos",
        "do_not_multiply_faces_by_2_automatically",
        "manual_only_if_reinforcement_not_already_in_structural_card",
    }

    unhandled = [
        str(item)
        for item in declared_specific
        if str(item)
        not in known_validations
    ]

    return {
        "blocking":
            blocking,

        "alerts":
            alerts,

        "unhandledValidations":
            unhandled,
    }


def _get_stop_on_error(
    concept: dict[str, Any],
) -> bool:

    activation = (
        concept.get("activation_rule")
        if isinstance(
            concept.get("activation_rule"),
            dict,
        )
        else {}
    )

    return bool(
        activation.get(
            "stop_on_error",
            False,
        )
    )


_CONCEPT_CODE_PATTERN = re.compile(
    r"^[A-Z]{3}-\d{3}[A-Z]?$"
)

def _is_concept_code(
    value: Any,
) -> bool:

    text = _to_text(
        value,
        "",
    ).upper()

    return bool(
        _CONCEPT_CODE_PATTERN.fullmatch(
            text
        )
    )


def _get_external_results_by_code(
    context: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    raw = context.get(
        "confirmedConceptsByCode"
    )

    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}

    for key, value in raw.items():

        code = _to_text(
            key,
            "",
        ).upper()

        if not code:
            continue

        if isinstance(value, dict):
            result[code] = value

    return result


def _evaluate_dependencies(
    concept: dict[str, Any],
    context: dict[str, Any],
    results_by_code: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    spec = (
        concept.get("engine_spec")
        if isinstance(
            concept.get("engine_spec"),
            dict,
        )
        else {}
    )

    dependencies_json = (
        spec.get("dependencies_json")
        if isinstance(
            spec.get("dependencies_json"),
            dict,
        )
        else {}
    )

    dependencies = dependencies_json.get(
        "requires_or_derives_from",
        [],
    )

    if not isinstance(
        dependencies,
        list,
    ):
        dependencies = []

    alerts: list[dict[str, Any]] = []

    informational: list[str] = []

    blocking = False

    external_results = (
        _get_external_results_by_code(
            context
        )
    )

    for dependency_expression in dependencies:

        expression = _to_text(
            dependency_expression,
            "",
        )

        if not expression:
            continue

        alternatives = [
            item.strip().upper()
            for item in expression.split("|")
            if item.strip()
        ]

        concept_alternatives = [
            item
            for item in alternatives
            if _is_concept_code(item)
        ]

        # ------------------------------------------
        # Dependencia semántica
        #
        # Ejemplo:
        # muros
        # vanos
        # niveles
        #
        # required_inputs es quien debe controlar
        # esos datos. No bloqueamos aquí.
        # ------------------------------------------

        if not concept_alternatives:

            informational.append(
                expression
            )

            continue

        # ------------------------------------------
        # Buscar resultados disponibles
        # ------------------------------------------

        available_results: list[
            dict[str, Any]
        ] = []

        for dependency_code in (
            concept_alternatives
        ):

            result = results_by_code.get(
                dependency_code
            )

            if result is None:
                result = external_results.get(
                    dependency_code
                )

            if result is not None:
                available_results.append(
                    result
                )

        # ------------------------------------------
        # Ningún resultado disponible
        #
        # Puede tratarse de dependencia entre
        # módulos. No bloqueamos falsamente.
        # ------------------------------------------

        if not available_results:

            alerts.append(
                {
                    "code":
                        "DEPENDENCY_CONTEXT_NOT_AVAILABLE",

                    "dependency":
                        expression,

                    "severity":
                        "warning",
                }
            )

            continue

        # ------------------------------------------
        # OR lógico
        #
        # CIM-003 | CIM-003A
        # significa que basta uno.
        # ------------------------------------------

        satisfied = False

        for result in available_results:

            status = _to_text(
                result.get("status"),
                "",
            ).upper()

            quantity = result.get(
                "quantity"
            )

            if (
                status
                in {
                    "PROPOSED",
                    "CONFIRMED",
                }
                and quantity is not None
            ):
                satisfied = True
                break

        if not satisfied:

            blocking = True

            alerts.append(
                {
                    "code":
                        "DEPENDENCY_NOT_SATISFIED",

                    "dependency":
                        expression,

                    "severity":
                        "blocking",
                }
            )

    return {
        "blocking": blocking,
        "alerts": alerts,
        "informationalDependencies":
            informational,
    }


def _execute_concept_rule(
    concept: dict[str, Any],
    context: dict[str, Any],
    results_by_code: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    code = _to_text(
        concept.get("code"),
        "",
    ).upper()

    alerts: list[dict[str, Any]] = []

    # ==========================================
    # 1. Activación
    # ==========================================

    activation = _evaluate_activation_rule(
        concept,
        context,
    )

    alerts.extend(
        activation.get(
            "alerts",
            [],
        )
    )

    if not activation.get(
        "active"
    ):

        return {
            "code":
                code,

            "status":
                activation.get(
                    "status",
                    "INACTIVE",
                ),

            "quantity":
                None,

            "alerts":
                alerts,

            "evidence":
                [],

            "missingInputs":
                [],

            "strategy":
                _get_inference_strategy(
                    concept
                ),

            "requiresProjectDefinition":
                activation.get(
                    "requiresProjectDefinition",
                    False,
                ),
        }

    # ==========================================
    # 2. Inputs requeridos
    # ==========================================

    inputs = _resolve_required_inputs(
        concept,
        context,
    )

    if not inputs.get(
        "complete"
    ):

        alerts.append(
            {
                "code":
                    "MISSING_REQUIRED_INPUT",

                "severity":
                    "blocking",

                "missingInputs":
                    inputs.get(
                        "missingInputs",
                        [],
                    ),
            }
        )

        return {
            "code":
                code,

            "status":
                "BLOCKED_MISSING_INPUT",

            "quantity":
                None,

            "alerts":
                alerts,

            "evidence":
                [],

            "missingInputs":
                inputs.get(
                    "missingInputs",
                    [],
                ),

            "strategy":
                _get_inference_strategy(
                    concept
                ),

            "requiresProjectDefinition":
                activation.get(
                    "requiresProjectDefinition",
                    False,
                ),
        }

    # ==========================================
    # 3. Dependencias
    # ==========================================

    dependency_result = (
        _evaluate_dependencies(
            concept,
            context,
            results_by_code,
        )
    )

    alerts.extend(
        dependency_result.get(
            "alerts",
            [],
        )
    )

    if dependency_result.get(
        "blocking"
    ):

        return {
            "code":
                code,

            "status":
                "BLOCKED_CONFLICT",

            "quantity":
                None,

            "alerts":
                alerts,

            "evidence":
                [],

            "missingInputs":
                [],

            "strategy":
                _get_inference_strategy(
                    concept
                ),

            "requiresProjectDefinition":
                activation.get(
                    "requiresProjectDefinition",
                    False,
                ),

            "informationalDependencies":
                dependency_result.get(
                    "informationalDependencies",
                    [],
                ),
        }

    # ==========================================
    # 4. Ejecutar cálculo
    # ==========================================

    execution = (
        _execute_inference_strategy(
            concept,
            context,
            inputs.get(
                "resolvedInputs",
                {},
            ),
        )
    )

    alerts.extend(
        execution.get(
            "alerts",
            [],
        )
    )

    # ==========================================
    # 5. Validación básica de cantidad
    # ==========================================

    validated = _validate_quantity(
        concept,
        execution,
    )

    alerts = list(
        validated.get(
            "alerts",
            alerts,
        )
    )

    calculated_quantity = (
        validated.get(
            "quantity"
        )
    )

    # ==========================================
    # 6. Validaciones declarativas
    # ==========================================

    rule_validation = (
        _run_declarative_validations(
            concept,
            context,
            validated,
        )
    )

    alerts.extend(
        rule_validation.get(
            "alerts",
            [],
        )
    )

    # ==========================================
    # 7. Exclusiones
    # ==========================================

    exclusion_result = (
        _apply_exclusions(
            concept,
            results_by_code,
            current_result=validated,
        )
    )

    alerts.extend(
        exclusion_result.get(
            "alerts",
            [],
        )
    )

    # ==========================================
    # 8. Determinar conflicto final
    # ==========================================

    blocking_error = bool(
        rule_validation.get(
            "blocking"
        )
        or exclusion_result.get(
            "blocking"
        )
    )

    stop_on_error = (
        _get_stop_on_error(
            concept
        )
    )

    if blocking_error:

        return {
            "code":
                code,

            "status":
                "BLOCKED_CONFLICT",

            # No entra al presupuesto
            "quantity":
                None,

            # Conservamos lo calculado únicamente
            # para diagnóstico.
            "calculatedQuantity":
                calculated_quantity,

            "alerts":
                alerts,

            "evidence":
                validated.get(
                    "evidence",
                    [],
                ),

            "scopeRefs":
                validated.get(
                    "scopeRefs",
                    [],
                ),

            "missingInputs":
                [],

            "strategy":
                _get_inference_strategy(
                    concept
                ),

            "requiresProjectDefinition":
                activation.get(
                    "requiresProjectDefinition",
                    False,
                ),

            "stopOnError":
                stop_on_error,

            "informationalDependencies":
                dependency_result.get(
                    "informationalDependencies",
                    [],
                ),

            "unhandledValidations":
                rule_validation.get(
                    "unhandledValidations",
                    [],
                ),
        }

    # ==========================================
    # 9. Resultado correcto
    # ==========================================

    return {
        "code":
            code,

        "status":
            validated.get(
                "status",
                "PROPOSED",
            ),

        "quantity":
            calculated_quantity,

        "alerts":
            alerts,

        "evidence":
            validated.get(
                "evidence",
                [],
            ),

        "scopeRefs":
            validated.get(
                "scopeRefs",
                [],
            ),

        "missingInputs":
            [],

        "strategy":
            _get_inference_strategy(
                concept
            ),

        "requiresProjectDefinition":
            activation.get(
                "requiresProjectDefinition",
                False,
            ),

        "stopOnError":
            stop_on_error,

        "informationalDependencies":
            dependency_result.get(
                "informationalDependencies",
                [],
            ),

        "unhandledValidations":
            rule_validation.get(
                "unhandledValidations",
                [],
            ),
    }


def _group_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        partida = _to_text(row.get("partida"), "General")
        if partida not in grouped:
            grouped[partida] = {"partida": partida, "concepts": 0, "total": 0.0}
        grouped[partida]["concepts"] += 1
        grouped[partida]["total"] += _to_number(row.get("total"), 0)

    return [
        {
            "partida": item["partida"],
            "concepts": int(item["concepts"]),
            "total": _round(item["total"], 2),
        }
        for item in grouped.values()
    ]


def _fetch_catalog_concepts(module_key: str, source_name: str = "CONSTRUBASE_PU_48_CONSTRUCTOR", limit: int = 500) -> list[dict[str, Any]]:
    normalized_module = _to_text(module_key, "").lower()
    partida_codes = MODULE_PARTIDAS.get(normalized_module)
    if not partida_codes:
        return []

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
        return []

    partida_name_by_id = {safe_text(row.get("id")): safe_text(row.get("name")) for row in partidas_rows}
    partida_code_by_id = {safe_text(row.get("id")): safe_text(row.get("code")) for row in partidas_rows}
    partida_ids = [safe_text(row.get("id")) for row in partidas_rows if safe_text(row.get("id"))]

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
        return []

    unit_ids = list({safe_text(row.get("unit_id")) for row in concepts_rows if safe_text(row.get("unit_id"))})
    concept_ids = [safe_text(row.get("id")) for row in concepts_rows if safe_text(row.get("id"))]

    units_map: dict[str, dict[str, Any]] = {}
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

    specs_by_concept_id: dict[str, dict[str, Any]] = {}
    spec_ids: list[str] = []
    if concept_ids:
        spec_rows = execute_catalog_query(
            lambda client: (
                client.table("engine_concept_specs")
                .select(
                    "id,concept_id,spec_code,is_active,spec_profile_id,formula_id,"
                    "application_mode,requires_project_definition,default_quantity_mode,"
                    "technical_scope_text,inference_strategy,parameter_defaults,parameter_rules,"
                    "validations_json,dependencies_json,exclusions_json,quantity_multiplier,"
                    "execution_priority"
                )
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

    activation_by_spec_id: dict[str, dict[str, Any]] = {}

    if spec_ids:
        activation_rows = execute_catalog_query(
            lambda client: (
                client.table("engine_activation_rules")
                .select(
                    "id,"
                    "code,"
                    "concept_spec_id,"
                    "rule_name,"
                    "priority,"
                    "activation_type,"
                    "type_intervention,"
                    "scope,"
                    "trigger_json,"
                    "condition_json,"
                    "derivation_json,"
                    "invalidates_json,"
                    "alerts_json,"
                    "output_action_json,"
                    "stop_on_error,"
                    "is_active"
                )
                .in_("concept_spec_id", spec_ids)
                .eq("is_active", True)
                .execute()
                .data
                or []
            ),
            operation="engine_activation_rules",
            critical=False,
            default=[],
        )

        for row in activation_rows:
            spec_id = safe_text(row.get("concept_spec_id"))

            if not spec_id:
                continue

            activation_by_spec_id[spec_id] = row

    prices_by_concept_id: dict[str, dict[str, Any]] = {}

    if concept_ids:
        price_rows = execute_catalog_query(
            lambda client: (
                client.table("current_unit_prices")
                .select(
                    "external_concept_id,concept_code,price_version,"
                    "direct_cost,unit_price,region_code,base_date"
                )
                .in_("external_concept_id", concept_ids)
                .execute()
                .data
                or []
            ),
            operation="current_unit_prices",
            critical=False,
            default=[],
        )

        prices_by_concept_id = {
            safe_text(row.get("external_concept_id")): row
            for row in price_rows
            if safe_text(row.get("external_concept_id"))
        }
   


    payload: list[dict[str, Any]] = []
    for row in concepts_rows:
        concept_id = safe_text(row.get("id"))
        unit = units_map.get(safe_text(row.get("unit_id")), {})
        spec = specs_by_concept_id.get(concept_id, {})
        spec_id = safe_text(spec.get("id"))

        activation_rule = (
            activation_by_spec_id.get(spec_id, {})
            if spec_id
            else {}
        )

        price = prices_by_concept_id.get(concept_id, {})
        unit_price = price.get("unit_price")

        payload.append(
            {
                "unit_price": float(unit_price or 0),
                "source_name": "current_unit_prices",
                "code": safe_text(row.get("code")),
                "technical_description": safe_text(row.get("technical_description")),
                "official_description": safe_text(row.get("official_description")),
                "unit_code": safe_text(unit.get("code"), "OTRO"),
                "unit_symbol": safe_text(unit.get("symbol"), "u"),
                "partida_code": partida_code_by_id.get(safe_text(row.get("partida_id")), ""),
                "partida_name": partida_name_by_id.get(safe_text(row.get("partida_id")), ""),
                "default_formula_code": safe_text(row.get("default_formula_code")),
                "quantification_mode": safe_text(row.get("quantification_mode")),
                "unit_price": float(unit_price or 0),
                "source_name": safe_text(price.get("source_name")) or source_name,
                "engine_spec": spec,
                "activation_rule": activation_rule,
                "concept_id": concept_id,
            }
        )

    payload.sort(key=lambda item: item.get("code") or "")
    return payload




def _audit_module_activation_rules(
    concepts: list[dict[str, Any]],
    module_key: str,
) -> dict[str, Any]:
    missing_rules: list[str] = []
    missing_strategies: list[str] = []

    for concept in concepts:
        code = _to_text(concept.get("code"), "").upper()
        if not code:
            continue

        activation = (
            concept.get("activation_rule")
            if isinstance(concept.get("activation_rule"), dict)
            else {}
        )
        spec = (
            concept.get("engine_spec")
            if isinstance(concept.get("engine_spec"), dict)
            else {}
        )

        if not activation or activation.get("is_active") is False:
            missing_rules.append(code)

        if not _to_text(spec.get("inference_strategy"), ""):
            missing_strategies.append(code)

    return {
        "ready": bool(concepts) and not missing_rules and not missing_strategies,
        "module": module_key,
        "checkedConcepts": len(concepts),
        "missingRules": missing_rules,
        "missingStrategies": missing_strategies,
    }


def _activation_rule_has_context_condition(
    concept: dict[str, Any],
    field: str,
) -> bool:

    activation = (
        concept.get("activation_rule")
        if isinstance(
            concept.get("activation_rule"),
            dict,
        )
        else {}
    )

    condition = (
        activation.get("condition_json")
        if isinstance(
            activation.get("condition_json"),
            dict,
        )
        else {}
    )

    context_conditions = (
        condition.get(
            "context_conditions"
        )
        if isinstance(
            condition.get(
                "context_conditions"
            ),
            dict,
        )
        else {}
    )

    return (
        field
        in context_conditions
    )


def _audit_estructura_activation_rules(
    concepts: list[dict[str, Any]],
) -> dict[str, Any]:

    required_conditions = {
        "EST-001":
            "sistemaEstructural",

        "EST-002":
            "sistemaEstructural",

        "EST-003":
            "sistemaEstructural",

        "EST-004":
            "sistemaEstructural",

        "EST-005":
            "tipoLosa",

        "EST-006":
            "tipoLosa",

        "EST-007":
            "tipoLosa",
    }

    found_codes: set[str] = set()

    missing_conditions: list[
        dict[str, str]
    ] = []

    for concept in concepts:

        code = _to_text(
            concept.get("code"),
            "",
        ).upper()

        if code not in required_conditions:
            continue

        found_codes.add(
            code
        )

        required_field = (
            required_conditions[code]
        )

        if not _activation_rule_has_context_condition(
            concept,
            required_field,
        ):

            missing_conditions.append(
                {
                    "code":
                        code,

                    "field":
                        required_field,
                }
            )

    missing_concepts = [
        code
        for code
        in required_conditions
        if code not in found_codes
    ]

    ready = (
        not missing_conditions
        and not missing_concepts
    )

    return {
        "ready":
            ready,

        "missingConditions":
            missing_conditions,

        "missingConcepts":
            missing_concepts,

        "requiredConcepts":
            sorted(
                required_conditions.keys()
            ),
    }


def _audit_instalaciones_activation_rules(
    concepts: list[dict[str, Any]],
) -> dict[str, Any]:
    required_service_by_partida = {
        "HID": "agua",
        "ELE": "energia",
        "SAN": "drenaje",
        "PLU": "drenaje",
        "GAS": "gas",
    }

    checked = 0
    missing_conditions: list[dict[str, str]] = []

    for concept in concepts:
        partida_code = _to_text(
            concept.get("partida_code"),
            "",
        ).upper()

        expected_key = required_service_by_partida.get(
            partida_code
        )

        if not expected_key:
            continue

        checked += 1

        activation = (
            concept.get("activation_rule")
            if isinstance(concept.get("activation_rule"), dict)
            else {}
        )
        condition = (
            activation.get("condition_json")
            if isinstance(activation.get("condition_json"), dict)
            else {}
        )
        requirement = (
            condition.get("service_requirement")
            if isinstance(condition.get("service_requirement"), dict)
            else {}
        )

        valid = (
            requirement.get("container")
            == "serviciosInstalaciones"
            and requirement.get("key") == expected_key
            and requirement.get("required_value") is True
        )

        if not valid:
            missing_conditions.append(
                {
                    "code": _to_text(
                        concept.get("code"),
                        "",
                    ).upper(),
                    "partida": partida_code,
                    "field": (
                        "service_requirement:"
                        f"serviciosInstalaciones.{expected_key}"
                    ),
                }
            )

    return {
        "ready": checked > 0 and not missing_conditions,
        "checkedConcepts": checked,
        "missingConditions": missing_conditions,
    }




def _build_available_concepts(
    module_key: str,
    concepts: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    results_by_code: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    ordered_concepts = sorted(
        concepts,
        key=lambda item: (
            int(
                (
                    item.get("engine_spec")
                    if isinstance(
                        item.get("engine_spec"),
                        dict,
                    )
                    else {}
                ).get(
                    "execution_priority",
                    9999,
                )
                or 9999
            ),
            _to_text(
                item.get("code"),
                "",
            ),
        ),
    )

    for concept in ordered_concepts:
        code = _to_text(
            concept.get("code"),
            "",
        ).upper()

        if not code:
            continue

        # -------------------------------------------------
        # Ejecutar regla V1.8
        # -------------------------------------------------

        inference_result = _execute_concept_rule(
            concept=concept,
            context=context,
            results_by_code=results_by_code,
        )

        # Guardar resultado para dependencias/exclusiones
        results_by_code[code] = inference_result

        status = _to_text(
            inference_result.get("status"),
            "BLOCKED_MISSING_INPUT",
        )

        quantity_raw = inference_result.get(
            "quantity"
        )

        quantity = (
            _round(
                _to_number(quantity_raw, 0),
                4,
            )
            if quantity_raw is not None
            else None
        )

        # -------------------------------------------------
        # Precio
        #
        # El precio NO participa en la inferencia.
        # Solo se aplica después de obtener cantidad.
        # -------------------------------------------------

        unit_price = _round(
            _to_number(
                concept.get("unit_price"),
                0,
            ),
            2,
        )

        # Si la cantidad todavía está bloqueada,
        # no calculamos importe.
        if quantity is None:
            total = 0.0
        else:
            total = _round(
                quantity * unit_price,
                2,
            )

        # -------------------------------------------------
        # Datos de la especificación
        # -------------------------------------------------

        spec = (
            concept.get("engine_spec")
            if isinstance(
                concept.get("engine_spec"),
                dict,
            )
            else {}
        )

        activation_rule = (
            concept.get("activation_rule")
            if isinstance(
                concept.get("activation_rule"),
                dict,
            )
            else {}
        )

        # -------------------------------------------------
        # Resultado para frontend
        # -------------------------------------------------

        rows.append(
            {
                "key": code,

                "moduleKey": module_key,

                "partida": _to_text(
                    concept.get("partida_name"),
                    _to_text(
                        concept.get("partida_code"),
                        "General",
                    ),
                ),

                "title": _to_text(
                    concept.get(
                        "official_description"
                    ),
                    _to_text(
                        concept.get(
                            "technical_description"
                        ),
                        code,
                    ),
                ),

                "description": _to_text(
                    concept.get(
                        "technical_description"
                    ),
                    _to_text(
                        concept.get(
                            "official_description"
                        ),
                        "Concepto",
                    ),
                ),

                "unit": _to_text(
                    concept.get("unit_symbol"),
                    _to_text(
                        concept.get("unit_code"),
                        "u",
                    ),
                ).lower(),

                # -----------------------------------------
                # Resultado de inferencia V1.8
                # -----------------------------------------

                "quantity": quantity,

                "status": status,

                "calculatedQuantity":
                    inference_result.get(
                        "calculatedQuantity"
                    ),

                "strategy": _to_text(
                    inference_result.get(
                        "strategy"
                    ),
                    _to_text(
                        spec.get(
                            "inference_strategy"
                        ),
                        "",
                    ),
                ),

                "requiresProjectDefinition": bool(
                    inference_result.get(
                        "requiresProjectDefinition",
                        spec.get(
                            "requires_project_definition",
                            False,
                        ),
                    )
                ),

                "missingInputs": (
                    inference_result.get(
                        "missingInputs"
                    )
                    if isinstance(
                        inference_result.get(
                            "missingInputs"
                        ),
                        list,
                    )
                    else []
                ),

                "alerts": (
                    inference_result.get(
                        "alerts"
                    )
                    if isinstance(
                        inference_result.get(
                            "alerts"
                        ),
                        list,
                    )
                    else []
                ),

                "evidence": (
                    inference_result.get(
                        "evidence"
                    )
                    if isinstance(
                        inference_result.get(
                            "evidence"
                        ),
                        list,
                    )
                    else []
                ),

                # -----------------------------------------
                # Información económica
                # -----------------------------------------

                "unitPrice": unit_price,

                "total": total,

                # -----------------------------------------
                # Trazabilidad del motor
                # -----------------------------------------

                "formulaCode": _to_text(
                    concept.get(
                        "default_formula_code"
                    ),
                    "",
                ),

                "quantificationMode": _to_text(
                    concept.get(
                        "quantification_mode"
                    ),
                    _to_text(
                        spec.get(
                            "default_quantity_mode"
                        ),
                        "",
                    ),
                ),

                "specCode": _to_text(
                    spec.get("spec_code"),
                    "",
                ),

                "activationRuleCode": _to_text(
                    activation_rule.get("code"),
                    "",
                ),

                "sourceName": _to_text(
                    concept.get(
                        "source_name"
                    ),
                    "",
                ),
            }
        )

    return rows




def _pending_definitions() -> list[str]:
    return [
        "P-001 frontera exacta de obra_gris en obra_nueva",
        "P-002 catalogo oficial de nivel_acabado por modulo",
        "P-003 matriz tipo_intervencion -> alcance -> partidas activas",
        "P-004 taxonomia final de subalcances por partida",
        "P-005 compatibilidad formal cimentacion-estructura",
        "P-007 matriz de instalaciones por ambiente y numero de salidas",
    ]


def simulate_preliminares(
    *,
    preliminares: dict[str, Any] | None = None,
    datos_generales_obra: dict[str, Any] | None = None,
    estructura_espacial: dict[str, Any] | None = None,
    colindancias_recorrido: dict[str, Any] | None = None,
    source_name: str = "CONSTRUBASE_PU_48_CONSTRUCTOR",
) -> dict[str, Any]:
    _ = colindancias_recorrido
    prelim = preliminares or {}

    context = _build_spatial_context(
        datos_generales_obra,
        estructura_espacial,
        prelim,
    )
    catalog = _fetch_catalog_concepts(
        "preliminares",
        source_name=source_name,
    )
    activation_coverage = _audit_module_activation_rules(
        catalog,
        "preliminares",
    )
    available = _build_available_concepts(
        "preliminares",
        catalog,
        context,
    )

    def status_is(item: dict[str, Any], *values: str) -> bool:
        return _to_text(item.get("status"), "").upper() in set(values)

    proposed = [dict(x) for x in available if status_is(x, "PROPOSED")]
    confirmed = [dict(x) for x in available if status_is(x, "CONFIRMED")]
    blocked = [
        dict(x) for x in available
        if status_is(x, "BLOCKED_MISSING_INPUT", "BLOCKED_CONFLICT")
    ]
    not_applicable = [
        dict(x) for x in available if status_is(x, "NOT_APPLICABLE")
    ]
    inactive = [dict(x) for x in available if status_is(x, "INACTIVE")]
    active = proposed + confirmed

    technical = [
        {
            "key": item.get("key"),
            "sourceKey": item.get("key"),
            "group": item.get("partida") or "Preliminares",
            "title": item.get("title") or "Concepto preliminar",
            "description": item.get("description")
            or "Concepto generado desde motor backend.",
            "unit": item.get("unit") or "u",
            "quantity": _round(_to_number(item.get("quantity"), 0), 4),
            "unitPrice": _round(_to_number(item.get("unitPrice"), 0), 2),
            "total": _round(_to_number(item.get("total"), 0), 2),
            "status": item.get("status"),
            "strategy": item.get("strategy"),
            "alerts": item.get("alerts") or [],
            "evidence": item.get("evidence") or [],
        }
        for item in active
        if item.get("quantity") is not None
    ]

    official = [
        {
            "group": str(item.get("partida") or "general").lower().replace(" ", "_"),
            "title": item.get("partida") or "General",
            "description": (
                "Resumen de actividades del grupo "
                f"{item.get('partida') or 'General'}."
            ),
            "labor": "Cuadrilla de apoyo",
            "materials": "Material menor",
            "total": _round(_to_number(item.get("total"), 0), 2),
        }
        for item in _group_summary(technical)
    ]

    total = _round(
        sum(_to_number(item.get("total"), 0) for item in technical),
        2,
    )

    logger.info(
        "[TRACE][SIM][PRELIMINARES] available=%s proposed=%s blocked=%s total=%s source=%s",
        len(available),
        len(proposed),
        len(blocked),
        total,
        source_name,
    )

    return {
        "availableConcepts": available,
        "activeConcepts": active,
        "proposedConcepts": proposed,
        "confirmedConcepts": confirmed,
        "blockedConcepts": blocked,
        "notApplicableConcepts": not_applicable,
        "inactiveConcepts": inactive,
        "technicalConcepts": technical,
        "officialSummary": official,
        "costoEstimado": total,
        "sourceName": source_name,
        "contextSnapshot": context,
        "activationCoverage": activation_coverage,
        "pendingDefinitions": _pending_definitions(),
    }




def simulate_modulo(
    *,
    module_key: str,
    controles: dict[str, Any] | None = None,
    selected_concept_keys: list[str] | None = None,
    force_select_all: bool = False,
    preliminares: dict[str, Any] | None = None,
    datos_generales_obra: dict[str, Any] | None = None,
    estructura_espacial: dict[str, Any] | None = None,
    colindancias_recorrido: dict[str, Any] | None = None,
    source_name: str = "CONSTRUBASE_PU_48_CONSTRUCTOR",
) -> dict[str, Any]:
    controles_data = controles if isinstance(controles, dict) else {}

    context = _build_spatial_context(
        datos_generales_obra,
        estructura_espacial,
        preliminares,
    )

    sistema_estructural = _to_text(
        controles_data.get("sistemaEstructural"),
        context.get("sistemaEstructural", ""),
    ).lower()
    tipo_losa = _to_text(controles_data.get("tipoLosa"), "").lower()
    tipo_cimentacion = _normalize_foundation_type(
        controles_data.get(
            "tipoCimentacion",
            context.get("tipoCimentacion", ""),
        )
    )
    variante_zapata = _to_text(
        controles_data.get("varianteZapata"), ""
    ).lower()
    tipo_intervencion = _to_text(
        controles_data.get("tipoIntervencion"), ""
    ).lower()
    alcance_proyecto = _to_text(
        controles_data.get("alcanceProyecto"), ""
    ).lower()
    services = controles_data.get("serviciosInstalaciones")
    services = services if isinstance(services, dict) else {}

    context["parameterizationSnapshot"] = {
        "tipoIntervencion": tipo_intervencion,
        "alcanceProyecto": alcance_proyecto,
        "sistemaEstructural": sistema_estructural,
        "tipoCimentacion": tipo_cimentacion,
        "varianteZapata": variante_zapata,
        "tipoLosa": tipo_losa,
        "serviciosInstalaciones": services,
    }
    context.update(
        {
            "sistemaEstructural": sistema_estructural,
            "tipoLosa": tipo_losa,
            "tipoCimentacion": tipo_cimentacion,
            "tipo_cimentacion": tipo_cimentacion,
            "tipoIntervencion": tipo_intervencion,
            "alcanceProyecto": alcance_proyecto,
            "serviciosInstalaciones": services,
            "varianteZapata": variante_zapata,
        }
    )

    consumption = build_consumption(estructura_espacial, datos_generales_obra, context["parameterizationSnapshot"])
    automatic_inputs, geometry_audit = consumption['derivedInputsByConcept'], consumption['derivationTrace']
    context['consumption04'] = {key: consumption[key] for key in ('schemaVersion', 'modelSha256', 'issues', 'status')}
    by_concept = context.setdefault("_engineInputsByConcept", {})
    applied_geometry_inputs = set()
    for code, inputs in automatic_inputs.items():
        target = by_concept.setdefault(code, {})
        for name, value in inputs.items():
            if name not in target and name not in context:
                target[name] = value
                applied_geometry_inputs.add((code, name))
    context["geometryInference"] = [entry for entry in geometry_audit if (entry["concept"], entry["input"]) in applied_geometry_inputs]

    catalog = _fetch_catalog_concepts(
        module_key,
        source_name=source_name,
    )
    activation_coverage = _audit_module_activation_rules(
        catalog,
        module_key,
    )

    if module_key == "estructura":
        specialized = _audit_estructura_activation_rules(catalog)
        activation_coverage["specialized"] = specialized
        activation_coverage["ready"] = bool(
            activation_coverage.get("ready")
            and specialized.get("ready")
        )

    if module_key == "instalaciones":
        specialized = _audit_instalaciones_activation_rules(catalog)
        activation_coverage["specialized"] = specialized
        activation_coverage["ready"] = bool(
            activation_coverage.get("ready")
            and specialized.get("ready")
        )

    # V1.8 no vuelve a filtros heurísticos si falta cobertura.
    available = _build_available_concepts(
        module_key,
        catalog,
        context,
    )

    def status_is(item: dict[str, Any], *values: str) -> bool:
        return _to_text(item.get("status"), "").upper() in set(values)

    proposed = [dict(x) for x in available if status_is(x, "PROPOSED")]
    confirmed = [dict(x) for x in available if status_is(x, "CONFIRMED")]
    blocked = [
        dict(x) for x in available
        if status_is(x, "BLOCKED_MISSING_INPUT", "BLOCKED_CONFLICT")
    ]
    not_applicable = [
        dict(x) for x in available if status_is(x, "NOT_APPLICABLE")
    ]
    inactive = [dict(x) for x in available if status_is(x, "INACTIVE")]
    selectable = proposed + confirmed

    requested_keys = {
        str(item).strip().upper()
        for item in (selected_concept_keys or [])
        if str(item).strip()
    }

    if force_select_all:
        selected = [dict(item) for item in selectable]
    elif requested_keys:
        selected = [
            dict(item)
            for item in selectable
            if _to_text(item.get("key"), "").upper() in requested_keys
        ]
    else:
        selected = []

    selected_keys = [_to_text(item.get("key"), "") for item in selected]
    selectable_keys = {
        _to_text(item.get("key"), "").upper() for item in selectable
    }
    invalid_requested_keys = sorted(requested_keys - selectable_keys)

    summary = _group_summary(selected)
    costo_estimado = _round(
        sum(_to_number(item.get("total"), 0) for item in selected),
        2,
    )

    logger.info(
        "[TRACE][SIM][MODULO] key=%s available=%s proposed=%s blocked=%s selected=%s coverage=%s total=%s source=%s",
        module_key,
        len(available),
        len(proposed),
        len(blocked),
        len(selected),
        activation_coverage.get("ready"),
        costo_estimado,
        source_name,
    )

    return {
        "moduleKey": module_key,
        "availableConcepts": available,
        "proposedConcepts": proposed,
        "confirmedConcepts": confirmed,
        "blockedConcepts": blocked,
        "notApplicableConcepts": not_applicable,
        "inactiveConcepts": inactive,
        "selectedConcepts": selected,
        "selectedConceptKeys": selected_keys,
        "invalidRequestedKeys": invalid_requested_keys,
        "summaryByPartida": summary,
        "costoEstimado": costo_estimado,
        "sourceName": source_name,
        "contextSnapshot": context,
        "activationCoverage": activation_coverage,
    }


