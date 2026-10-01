import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.services.motor_simulation_service import simulate_modulo, simulate_preliminares


logger = logging.getLogger("app.result_service")

EXTERIOR_NODE = "__EXTERIOR__"
RELATION_DIRECTIONS = ["norte", "sur", "este", "oeste"]
OPPOSITE_DIRECTION = {
    "norte": "sur",
    "sur": "norte",
    "este": "oeste",
    "oeste": "este",
}
LEVEL_LABELS = {
    "planta_baja": "Planta Baja",
    "segunda_planta": "Segunda Planta",
    "tercera_planta": "Tercera Planta",
    "planta_azotea": "Planta Azotea",
}
TYPE_LABELS = {
    "recamara_principal": "Recamara Principal",
    "recamara_2": "Recamara 2",
    "recamara_3": "Recamara 3",
    "recamara_4": "Recamara 4",
    "bano_1": "Bano 1",
    "bano_2": "Bano 2",
    "medio_bano": "Medio Bano",
    "sala": "Sala",
    "cocina": "Cocina",
    "comedor": "Comedor",
    "estancia": "Estancia",
    "estudio": "Estudio",
    "escalera_1": "Escalera 1",
    "escalera_2": "Escalera 2",
    "escalera_3": "Escalera 3",
    "terraza": "Terraza",
    "pasillo_interior": "Pasillo interior",
    "patio_servicio": "Patio Servicio",
    "patio_exterior": "Patio Exterior",
    "cochera": "Cochera",
    "jardin": "Jardin",
}
MODULE_ORDER = [
    "cimentacion",
    "estructura",
    "albanileria",
    "instalaciones",
    "acabados",
    "complementarios_y_equipamiento",
]
MODULE_KEY_ALIASES = {
    "cimentacion": "cimentacion",
    "estructura": "estructura",
    "albanileria": "albanileria",
    "instalaciones": "instalaciones",
    "acabados": "acabados",
    "complementarios": "complementarios_y_equipamiento",
    "complementarios_y_equipamiento": "complementarios_y_equipamiento",
}


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


def _round_optional(value: Any, decimals: int) -> float | None:
    parsed = _to_optional_number(value)
    if parsed is None:
        return None
    return _round_half_up(parsed, decimals)


def _round_half_up(value: float, decimals: int) -> float:
    quant = Decimal("1").scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def _to_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_group_key(label: str | None) -> str:
    text = str(label or "general").strip().lower()
    normalized = (
        text.replace("Ã¡", "a")
        .replace("Ã©", "e")
        .replace("Ã­", "i")
        .replace("Ã³", "o")
        .replace("Ãº", "u")
    )
    return "_".join(normalized.split())


def _normalize_module_key(value: Any) -> str:
    raw = str(value or "").strip().lower()
    normalized = raw.replace("-", "_").replace(" ", "_")
    return MODULE_KEY_ALIASES.get(normalized, "")


def _module_title(module_key: str) -> str:
    labels = {
        "cimentacion": "Cimentacion",
        "estructura": "Estructura",
        "albanileria": "Albanileria",
        "instalaciones": "Instalaciones",
        "acabados": "Acabados",
        "complementarios_y_equipamiento": "Complementarios y equipamiento",
    }
    return labels.get(str(module_key or "").strip(), "Modulo")


def _resolve_factor_ajuste(
    variables_entrada: dict[str, Any],
    datos_generales_obra: dict[str, Any],
) -> float:
    raw = _to_number((variables_entrada or {}).get("factorAjuste") or (datos_generales_obra or {}).get("factorAjuste"), 1.0)
    return _round_half_up(raw if raw > 0 else 1.0, 4)


def _sanitize_preliminares_capture(
    preliminares: dict[str, Any],
) -> dict[str, Any]:
    row = preliminares if isinstance(preliminares, dict) else {}
    dem_raw = row.get("demolicion")
    dem = dem_raw if isinstance(dem_raw, dict) else {}

    engine_inputs = (
        row.get("engineInputs")
        if isinstance(row.get("engineInputs"), dict)
        else {}
    )
    engine_inputs_by_concept = (
        row.get("engineInputsByConcept")
        if isinstance(row.get("engineInputsByConcept"), dict)
        else {}
    )

    area_pre_raw = row.get("areaPreliminares")
    if area_pre_raw is None or (isinstance(area_pre_raw, str) and not area_pre_raw.strip()):
        area_pre_raw = row.get("superficiePreliminar")

    superficie_raw = row.get("superficiePreliminar")
    if superficie_raw is None or (isinstance(superficie_raw, str) and not superficie_raw.strip()):
        superficie_raw = row.get("areaPreliminares")

    return {
        "tipoIntervencion": _to_text(row.get("tipoIntervencion"), ""),
        "alcanceSeleccionado": _to_text(row.get("alcanceSeleccionado"), ""),
        "areaPreliminares": _round_optional(area_pre_raw, 2),
        "superficiePreliminar": _round_optional(superficie_raw, 2),
        "tipoAcceso": _to_text(row.get("tipoAcceso"), ""),
        "condicionTerreno": _to_text(row.get("condicionTerreno"), ""),
        "topografia": _to_text(row.get("topografia"), ""),
        "pendienteProfundidadM": _round_optional(
            row.get("pendienteProfundidadM"),
            4,
        ),
        "demolicion": {
            "tipoDemolicion": _to_text(dem.get("tipoDemolicion"), ""),
            "tipoEstructuraExistente": _to_text(
                dem.get("tipoEstructuraExistente"),
                "",
            ),
            "nivelesExistentes": _round_optional(
                dem.get("nivelesExistentes"),
                2,
            ),
            "anchoDemolicionM": _round_optional(
                dem.get("anchoDemolicionM"),
                2,
            ),
            "largoDemolicionM": _round_optional(
                dem.get("largoDemolicionM"),
                2,
            ),
            "areaDemolicionM2": _round_optional(
                dem.get("areaDemolicionM2"),
                2,
            ),
            "volumenDemolicion": _round_optional(
                dem.get("volumenDemolicion"),
                2,
            ),
        },
        "observaciones": _to_text(row.get("observaciones"), ""),
        "engineInputs": engine_inputs,
        "engineInputsByConcept": engine_inputs_by_concept,
    }



def _sanitize_modulos_capture(
    modulos: dict[str, Any],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key, value in (modulos or {}).items():
        normalized_key = _normalize_module_key(key)
        if not normalized_key:
            continue

        row = value if isinstance(value, dict) else {}
        controles = (
            row.get("controles")
            if isinstance(row.get("controles"), dict)
            else {}
        )

        selected_raw = row.get("selectedConceptKeys")
        selected_raw = selected_raw if isinstance(selected_raw, list) else []
        selected_keys = list(
            dict.fromkeys(
                str(item).strip().upper()
                for item in selected_raw
                if str(item).strip()
            )
        )

        normalized[normalized_key] = {
            "capturado": bool(row.get("capturado")),
            "noApplicable": bool(row.get("noApplicable")),
            "controles": controles,
            "selectedConceptKeys": selected_keys,
            "activationCoverage": (
                row.get("activationCoverage")
                if isinstance(row.get("activationCoverage"), dict)
                else {}
            ),
        }

    return normalized




def _normalize_required_modules(required_module_keys: list[str] | None, modulos: dict[str, Any]) -> list[str]:
    explicit: list[str] = []
    for raw in required_module_keys or []:
        key = _normalize_module_key(raw)
        if key and key not in explicit:
            explicit.append(key)
    if explicit:
        return [key for key in MODULE_ORDER if key in explicit]

    inferred = []
    for key in MODULE_ORDER:
        row = (modulos or {}).get(key) if isinstance(modulos, dict) else None
        if isinstance(row, dict) and bool(row.get("capturado")):
            inferred.append(key)
    return inferred


def _validate_preliminares_capture(preliminares: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    area = _to_number(preliminares.get("areaPreliminares") or preliminares.get("superficiePreliminar"), 0)
    if area <= 0:
        errors.append("Preliminares sin area valida.")
    if not _to_text(preliminares.get("tipoAcceso"), ""):
        errors.append("Preliminares sin tipoAcceso.")
    if not _to_text(preliminares.get("condicionTerreno"), ""):
        errors.append("Preliminares sin condicionTerreno.")
    topografia = _to_text(preliminares.get("topografia"), "")
    if not topografia:
        errors.append("Preliminares sin topografia.")
    if topografia == "con_pendiente" and _to_number(preliminares.get("pendienteProfundidadM"), 0) <= 0:
        errors.append("Preliminares con topografia con_pendiente sin pendienteProfundidadM.")
    return errors


def _validate_modulos_capture(
    modulos: dict[str, Any],
    required_modules: list[str],
    datos_generales_obra: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    tipo_cimentacion = _to_text(
        (datos_generales_obra or {}).get("tipoCimentacion"),
        "",
    ).lower()

    if tipo_cimentacion in {"zapata_aislada", "trabe_liga"}:
        tipo_cimentacion = "zapata_aislada_trabe_liga"
    elif tipo_cimentacion == "mamposteria":
        tipo_cimentacion = "mamposteria_corrida"

    for key in required_modules:
        row = (modulos or {}).get(key)
        if not isinstance(row, dict):
            errors.append(f"Modulo requerido '{key}' ausente en captura.")
            continue

        if not bool(row.get("capturado")):
            errors.append(f"Modulo requerido '{key}' no capturado.")
            continue

        if bool(row.get("noApplicable")):
            continue

        controles = (
            row.get("controles")
            if isinstance(row.get("controles"), dict)
            else {}
        )

        if (
            key == "cimentacion"
            and tipo_cimentacion == "zapata_aislada_trabe_liga"
            and not _to_text(controles.get("varianteZapata"), "")
        ):
            errors.append(
                "Modulo 'cimentacion' sin varianteZapata "
                "para zapata aislada."
            )

        if (
            key == "estructura"
            and not _to_text(controles.get("tipoLosa"), "")
        ):
            errors.append("Modulo 'estructura' sin control tipoLosa.")

        if (
            key == "acabados"
            and not _to_text(controles.get("nivelAcabado"), "")
        ):
            errors.append("Modulo 'acabados' sin control nivelAcabado.")

        if key == "instalaciones":
            services = (
                controles.get("serviciosInstalaciones")
                if isinstance(
                    controles.get("serviciosInstalaciones"),
                    dict,
                )
                else {}
            )
            for flag in ("agua", "energia", "drenaje"):
                if flag not in services or not isinstance(services.get(flag), bool):
                    errors.append(
                        "Modulo 'instalaciones' requiere definir "
                        f"serviciosInstalaciones.{flag} como si/no."
                    )

    return errors




def _validate_core_capture(
    preliminares: dict[str, Any],
    modulos: dict[str, Any],
    required_modules: list[str],
    datos_generales_obra: dict[str, Any],
    estructura_espacial: dict[str, Any],
    colindancias_recorrido: dict[str, Any],
    validacion_espacial: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    area_terreno = _to_number((datos_generales_obra or {}).get("areaTerrenoM2"), 0)
    area_construccion = _to_number((datos_generales_obra or {}).get("areaConstruccionM2"), 0)
    niveles = _to_number((datos_generales_obra or {}).get("niveles"), 0)
    sistema = _to_text((datos_generales_obra or {}).get("sistemaEstructural"), "")
    cimentacion = _to_text((datos_generales_obra or {}).get("tipoCimentacion"), "")
    if area_terreno <= 0 or area_construccion <= 0 or niveles <= 0 or not sistema or not cimentacion:
        errors.append("Datos generales de obra incompletos para inferencia.")

    spaces = (estructura_espacial or {}).get("espacios")
    spaces = spaces if isinstance(spaces, list) else []
    relations = (colindancias_recorrido or {}).get("relaciones")
    relations = relations if isinstance(relations, list) else []
    if not spaces:
        errors.append("Estructura espacial sin espacios validos.")
    if not relations:
        errors.append("Colindancias sin relaciones validas.")
    if not bool((validacion_espacial or {}).get("revisado")):
        errors.append("Validacion espacial no confirmada.")

    if not required_modules:
        errors.append("No hay modulos requeridos definidos para inferencia final.")

    errors.extend(_validate_preliminares_capture(preliminares))
    errors.extend(_validate_modulos_capture(modulos, required_modules, datos_generales_obra))
    return errors


def _build_official_summary(technical_concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in technical_concepts:
        group_name = str(item.get("group") or "General")
        group_key = _normalize_group_key(group_name)
        if group_key not in grouped:
            grouped[group_key] = {
                "group": group_key,
                "title": group_name,
                "description": f"Resumen de actividades del grupo {group_name}.",
                "labor": "Cuadrilla de apoyo",
                "materials": "Material menor",
                "total": 0.0,
            }
        grouped[group_key]["total"] = grouped[group_key]["total"] + _to_number(item.get("total") or 0)
    return [
        {
            **row,
            "total": _round_half_up(_to_number(row.get("total"), 0), 2),
        }
        for row in grouped.values()
    ]


def _direction_label(direction: str) -> str:
    mapping = {"norte": "Norte", "sur": "Sur", "este": "Este", "oeste": "Oeste"}
    return mapping.get(str(direction or "").strip(), str(direction or "").strip())


def _empty_relation_row(espacio_id: str) -> dict[str, str]:
    return {
        "espacioId": espacio_id,
        "norte": EXTERIOR_NODE,
        "sur": EXTERIOR_NODE,
        "este": EXTERIOR_NODE,
        "oeste": EXTERIOR_NODE,
    }


def _build_space_label_map(espacios: list[dict[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for index, item in enumerate(espacios):
        row = item if isinstance(item, dict) else {}
        space_id = str(row.get("id") or f"espacio-{index + 1}")
        space_type = TYPE_LABELS.get(str(row.get("tipo") or "").strip(), f"Espacio {index + 1}")
        level = LEVEL_LABELS.get(str(row.get("nivel") or "").strip(), "Nivel sin definir")
        labels[space_id] = f"{space_type} - {level}"
    return labels


def _normalize_spatial_relations(espacios: list[dict[str, Any]], relaciones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = relaciones if isinstance(relaciones, list) else []
    by_id = {
        str((item or {}).get("espacioId") or ""): item
        for item in rows
        if isinstance(item, dict)
    }
    normalized: list[dict[str, Any]] = []
    for espacio in espacios if isinstance(espacios, list) else []:
        espacio_row = espacio if isinstance(espacio, dict) else {}
        space_id = str(espacio_row.get("id") or "")
        base = _empty_relation_row(space_id)
        saved = by_id.get(space_id) or {}
        for direction in RELATION_DIRECTIONS:
            value = str((saved.get(direction) if isinstance(saved, dict) else "") or "").strip()
            base[direction] = value or EXTERIOR_NODE
        normalized.append(base)
    return normalized


def _validate_spatial_relations(
    espacios: list[dict[str, Any]],
    relaciones: list[dict[str, Any]],
) -> dict[str, Any]:
    issues: list[str] = []
    spaces = espacios if isinstance(espacios, list) else []
    relations = _normalize_spatial_relations(spaces, relaciones)
    label_map = _build_space_label_map(spaces)
    type_by_id = {
        str((item or {}).get("id") or ""): str((item or {}).get("tipo") or "").strip()
        for item in spaces
        if isinstance(item, dict)
    }
    valid_ids = {str((item or {}).get("id") or "") for item in spaces if isinstance(item, dict)}
    by_id = {str(item.get("espacioId") or ""): item for item in relations if isinstance(item, dict)}
    internal_links = 0
    reciprocal_links = 0

    for row in relations:
        from_id = str((row or {}).get("espacioId") or "")
        from_label = label_map.get(from_id) or from_id or "espacio_sin_id"
        if not from_id or from_id not in valid_ids:
            issues.append(f"Relacion sin espacio valido: {from_label}.")
            continue

        for direction in RELATION_DIRECTIONS:
            direction_label = _direction_label(direction)
            target_id = str((row or {}).get(direction) or "").strip()
            if not target_id:
                issues.append(f"Falta definir {direction_label} en {from_label}.")
                continue
            if target_id == EXTERIOR_NODE:
                continue

            target_label = label_map.get(target_id) or target_id
            if target_id not in valid_ids:
                issues.append(f"{from_label} apunta a {target_label} en {direction_label}, pero no existe.")
                continue
            if target_id == from_id:
                issues.append(f"{from_label} no puede colindar consigo mismo en {direction_label}.")
                continue

            internal_links += 1
            opposite = OPPOSITE_DIRECTION[direction]
            opposite_row = by_id.get(target_id, {})
            backward = str((opposite_row or {}).get(opposite) or "").strip()
            target_type = str(type_by_id.get(target_id) or "")
            has_any_backward_match = any(
                str((opposite_row or {}).get(check_direction) or "").strip() == from_id
                for check_direction in RELATION_DIRECTIONS
            )

            if backward == from_id or (target_type == "pasillo_interior" and has_any_backward_match):
                reciprocal_links += 1
            else:
                opposite_label = _direction_label(opposite)
                issues.append(
                    f"No hay reciprocidad: {from_label} al {direction_label} con {target_label}. "
                    f"Debe reflejarse {target_label} al {opposite_label} con {from_label}."
                )

    coverage_base = max(internal_links, 1)
    coverage_ratio = _round_half_up(reciprocal_links / coverage_base, 4)
    return {
        "valid": len(issues) == 0 and len(relations) == len(spaces),
        "issues": issues,
        "normalizedRelations": relations,
        "summary": {
            "spacesCount": len(spaces),
            "relationRowsCount": len(relations),
            "internalLinks": internal_links,
            "reciprocalLinks": reciprocal_links,
            "brokenLinks": max(internal_links - reciprocal_links, 0),
            "coverageRatio": coverage_ratio,
        },
    }


def _get_pendientes_definicion_v4() -> list[str]:
    return [
        "P-001 frontera exacta de obra_gris en obra_nueva",
        "P-002 catalogo oficial de nivel_acabado por modulo",
        "P-003 matriz tipo_intervencion -> alcance -> partidas activas",
        "P-004 taxonomia final de subalcances por partida",
        "P-005 compatibilidad formal cimentacion-estructura",
        "P-007 matriz de instalaciones por ambiente y numero de salidas",
    ]


def _build_technical_from_preliminares(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = simulation.get("technicalConcepts") if isinstance(simulation, dict) else []
    rows = rows if isinstance(rows, list) else []
    technical: list[dict[str, Any]] = []
    for index, item in enumerate(rows):
        row = item if isinstance(item, dict) else {}
        quantity = _round_half_up(_to_number(row.get("quantity"), 0), 4)
        unit_price = _round_half_up(_to_number(row.get("unitPrice"), 0), 2)
        total = _round_half_up(_to_number(row.get("total"), quantity * unit_price), 2)
        technical.append(
            {
                "key": _to_text(row.get("key"), f"PRE-{str(index + 1).zfill(3)}"),
                "sourceKey": _to_text(row.get("sourceKey"), "preliminares"),
                "group": _to_text(row.get("group"), "Preliminares"),
                "title": _to_text(row.get("title"), "Concepto preliminar"),
                "description": _to_text(row.get("description"), "Concepto generado desde preliminares."),
                "unit": _to_text(row.get("unit"), "u"),
                "quantity": quantity,
                "unitPrice": unit_price,
                "total": total,
            }
        )
    return technical


def _build_technical_from_modulo(module_key: str, simulation: dict[str, Any]) -> list[dict[str, Any]]:
    selected = simulation.get("selectedConcepts") if isinstance(simulation, dict) else []
    selected = selected if isinstance(selected, list) else []
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(selected):
        row = item if isinstance(item, dict) else {}
        quantity = _round_half_up(_to_number(row.get("quantity"), 0), 4)
        unit_price = _round_half_up(_to_number(row.get("unitPrice"), 0), 2)
        total = _round_half_up(_to_number(row.get("total"), quantity * unit_price), 2)
        rows.append(
            {
                "key": _to_text(row.get("key"), f"{str(module_key)[:3].upper()}-{str(index + 1).zfill(3)}"),
                "sourceKey": module_key,
                "group": _to_text(row.get("partida"), _module_title(module_key)),
                "title": _to_text(row.get("title"), "Concepto de modulo"),
                "description": _to_text(row.get("description"), f"Concepto derivado del modulo {module_key}."),
                "unit": _to_text(row.get("unit"), "u"),
                "quantity": quantity,
                "unitPrice": unit_price,
                "total": total,
            }
        )
    return rows


def run_motor_inferencia_v4(
    *,
    preliminares: dict[str, Any] | None = None,
    modulos: dict[str, Any] | None = None,
    datos_generales_obra: dict[str, Any] | None = None,
    variables_entrada: dict[str, Any] | None = None,
    estructura_espacial: dict[str, Any] | None = None,
    colindancias_recorrido: dict[str, Any] | None = None,
    validacion_espacial: dict[str, Any] | None = None,
    required_module_keys: list[str] | None = None,
    perfil: str = "oficial",
) -> dict[str, Any]:
    prelim_capture = _sanitize_preliminares_capture(preliminares or {})
    modulos_capture = _sanitize_modulos_capture(modulos or {})
    datos_generales_obra = datos_generales_obra or {}
    variables_entrada = variables_entrada or {}
    estructura_espacial = estructura_espacial or {}
    colindancias_recorrido = colindancias_recorrido or {}
    validacion_espacial = validacion_espacial or {}

    required_modules = _normalize_required_modules(required_module_keys, modulos_capture)

    spatial_audit = _validate_spatial_relations(
        espacios=estructura_espacial.get("espacios") or [],
        relaciones=colindancias_recorrido.get("relaciones") or [],
    )

    errors = _validate_core_capture(
        preliminares=prelim_capture,
        modulos=modulos_capture,
        required_modules=required_modules,
        datos_generales_obra=datos_generales_obra,
        estructura_espacial=estructura_espacial,
        colindancias_recorrido=colindancias_recorrido,
        validacion_espacial=validacion_espacial,
    )
    if errors:
        raise ValueError("Inferencia incompleta: " + " | ".join(errors))

    logger.info(
        "[TRACE][INFERENCIA][BACKEND_REQUEST] required=%s profile=%s spaces=%s",
        required_modules,
        perfil,
        len(estructura_espacial.get("espacios") or []),
    )

    prelim_simulation = simulate_preliminares(
        preliminares=prelim_capture,
        datos_generales_obra=datos_generales_obra,
        estructura_espacial=estructura_espacial,
        colindancias_recorrido=colindancias_recorrido,
    )
    prelim_technical = _build_technical_from_preliminares(prelim_simulation)
    logger.info(
        "[TRACE][INFERENCIA][BACKEND_PRELIMINARES] concepts=%s total=%s",
        len(prelim_technical),
        _round_half_up(_to_number(prelim_simulation.get("costoEstimado"), 0), 2),
    )

    module_errors: list[str] = []
    module_snapshots: dict[str, Any] = {}
    module_technical: list[dict[str, Any]] = []
    for module_key in required_modules:
        row = modulos_capture.get(module_key) or {}
        selected_keys = row.get("selectedConceptKeys") if isinstance(row.get("selectedConceptKeys"), list) else []
        controls = row.get("controles") if isinstance(row.get("controles"), dict) else {}
        simulation = simulate_modulo(
            module_key=module_key,
            controles=controls,
            selected_concept_keys=selected_keys,
            force_select_all=False,
            preliminares=prelim_capture,
            datos_generales_obra=datos_generales_obra,
            estructura_espacial=estructura_espacial,
            colindancias_recorrido=colindancias_recorrido,
        )
        selected = simulation.get("selectedConcepts") if isinstance(simulation, dict) else []
        selected = selected if isinstance(selected, list) else []
        module_total = _round_half_up(_to_number(simulation.get("costoEstimado"), 0), 2)
        logger.info(
            "[TRACE][INFERENCIA][BACKEND_MODULO] key=%s selected=%s total=%s",
            module_key,
            len(selected),
            module_total,
        )
        proposed = (
            simulation.get("proposedConcepts")
            if isinstance(simulation.get("proposedConcepts"), list)
            else []
        )
        blocked = (
            simulation.get("blockedConcepts")
            if isinstance(simulation.get("blockedConcepts"), list)
            else []
        )
        not_applicable = (
            simulation.get("notApplicableConcepts")
            if isinstance(simulation.get("notApplicableConcepts"), list)
            else []
        )
        invalid_requested = (
            simulation.get("invalidRequestedKeys")
            if isinstance(simulation.get("invalidRequestedKeys"), list)
            else []
        )

        if invalid_requested:
            module_errors.append(
                f"Modulo '{module_key}' solicito conceptos no seleccionables: "
                + ", ".join(str(x) for x in invalid_requested)
            )
            continue

        explicitly_not_applicable = bool(row.get("noApplicable"))
        if not selected and not explicitly_not_applicable:
            if blocked:
                blocked_codes = [
                    _to_text(item.get("key"), "")
                    for item in blocked[:8]
                ]
                module_errors.append(
                    f"Modulo '{module_key}' tiene conceptos bloqueados: "
                    + ", ".join(code for code in blocked_codes if code)
                )
            elif proposed:
                module_errors.append(
                    f"Modulo '{module_key}' tiene conceptos propuestos "
                    "pendientes de seleccion/confirmacion."
                )
            elif not_applicable:
                # Si todo el modulo quedó fuera por reglas, no es error.
                explicitly_not_applicable = True
            else:
                module_errors.append(
                    f"Modulo '{module_key}' no produjo conceptos evaluables."
                )
            if not explicitly_not_applicable:
                continue

        module_snapshots[module_key] = {
            "selectedConcepts": len(selected),
            "total": module_total,
            "noApplicable": explicitly_not_applicable,
            "activationCoverage": simulation.get("activationCoverage") or {},
            "blockedConcepts": len(blocked),
        }
        module_technical.extend(_build_technical_from_modulo(module_key, simulation))

    if module_errors:
        raise ValueError("Inferencia incompleta: " + " | ".join(module_errors))

    factor_final = _resolve_factor_ajuste(variables_entrada, datos_generales_obra)
    technical_concepts: list[dict[str, Any]] = []
    for item in prelim_technical + module_technical:
        quantity = _round_half_up(_to_number(item.get("quantity"), 0), 4)
        unit_price = _round_half_up(_to_number(item.get("unitPrice"), 0) * factor_final, 2)
        total = _round_half_up(_to_number(item.get("total"), quantity * unit_price) * factor_final, 2)
        technical_concepts.append(
            {
                **item,
                "quantity": quantity,
                "unitPrice": unit_price,
                "total": total,
            }
        )

    official_summary = _build_official_summary(technical_concepts)
    resultado_final = _round_half_up(sum(_to_number(item.get("total"), 0) for item in technical_concepts), 2)

    pending_definitions = list(_get_pendientes_definicion_v4())
    if not spatial_audit.get("valid"):
        pending_definitions.append(
            "P-ESP-001 Validar reciprocidad de colindancias entre espacios antes de cierre definitivo."
        )

    logger.info(
        "[TRACE][INFERENCIA][BACKEND_RESPONSE] technical=%s summary=%s total=%s factor=%s",
        len(technical_concepts),
        len(official_summary),
        resultado_final,
        factor_final,
    )

    return {
        "resultadoFinal": resultado_final,
        "desglose": {
            "technicalConcepts": technical_concepts,
            "officialSummary": official_summary,
        },
        "estadoResultado": "generado" if technical_concepts else "pendiente",
        "metadata": {
            "perfilSalida": perfil,
            "motorVersion": "v4-backend-autonomo",
            "factorAjusteAplicado": factor_final,
            "pendingDefinitions": pending_definitions,
            "contextSnapshot": {
                "espacios": len(estructura_espacial.get("espacios") or []),
                "relacionesInternas": ((spatial_audit.get("summary") or {}).get("internalLinks") or 0),
                "relacionesReciprocas": ((spatial_audit.get("summary") or {}).get("reciprocalLinks") or 0),
                "coberturaReciproca": ((spatial_audit.get("summary") or {}).get("coverageRatio") or 0),
                "validacionEspacialRevisada": bool(validacion_espacial.get("revisado")),
                "requiredModules": required_modules,
                "modules": module_snapshots,
            },
        },
    }
