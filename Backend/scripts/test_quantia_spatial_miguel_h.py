from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import threading
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

# Permite ejecutar tanto ``python -m scripts...`` como el archivo
# directamente desde cualquier directorio de trabajo.
BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Windows puede iniciar Python con stdout cp1252. El diagnóstico usa
# caracteres Unicode y no debe fallar por la codificación de consola.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.prompts.quantia_extraction_prompt import (
    QUANTIA_EXTRACTION_PROMPT,
)
from app.prompts.quantia_space_localization_prompt import (
    build_quantia_space_localization_prompt,
)
from app.schemas.gemini_extraction_transport import (
    get_gemini_extraction_transport_schema,
)
from app.schemas.gemini_space_localization_transport import (
    get_gemini_space_localization_schema,
)
from app.services.gemini_vision_provider import (
    get_gemini_vision_provider,
)
from app.services.quantia_spatial_reconstruction_service import (
    BaseLayerDescriptor,
    QuantiaSpatialReconstructionService,
)
from app.services.vision_provider import (
    VisionResult,
)

# ============================================================
# BASELINE MIGUEL H
# ============================================================


MIGUEL_H_RENDER_SCALE = 0.7935

EXPECTED_LEVELS = {
    "planta baja",
    "planta alta",
}

EXPECTED_AXIS_LABELS = {
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "A",
    "J",
    "C",
    "D",
}

EXPECTED_CRITICAL_DIMENSIONS = {
    1.18,
    2.60,
    3.78,
    4.10,
}

EXPECTED_OPEN_AREA_ZONES = {
    "estancia",
    "comedor",
    "cocina",
}


# ============================================================
# GEMINI REPLAY CACHE
# ============================================================


REPLAY_CACHE_VERSION = 1

REPLAY_STAGE_FILES = {
    "extraction": "miguel_h_gemini_extraction_replay.json",
    "localization": "miguel_h_gemini_localization_replay.json",
}


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_json_hash(
    value: Any,
) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return sha256_bytes(serialized.encode("utf-8"))


def vision_call_signature(
    *,
    prompt: Any,
    media_bytes: Any,
    media_mime_type: Any,
    response_json_schema: Any,
) -> dict[str, Any]:
    if not isinstance(
        prompt,
        str,
    ):
        raise RuntimeError("La llamada vision no contiene prompt válido.")

    if not isinstance(
        media_bytes,
        (bytes, bytearray),
    ):
        raise RuntimeError("La llamada vision no contiene media_bytes válidos.")

    return {
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "media_sha256": sha256_bytes(bytes(media_bytes)),
        "media_mime_type": str(media_mime_type or "").strip().lower(),
        "response_schema_sha256": stable_json_hash(response_json_schema),
    }


def cache_path_for_stage(
    cache_dir: Path,
    stage_key: str,
) -> Path:
    filename = REPLAY_STAGE_FILES.get(stage_key)

    if filename is None:
        raise RuntimeError(f"Etapa Gemini no soportada por replay: {stage_key}")

    return cache_dir / filename


def write_vision_cache(
    *,
    path: Path,
    stage_key: str,
    signature: dict[str, Any],
    result: VisionResult,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "cache_version": REPLAY_CACHE_VERSION,
        "stage": stage_key,
        "signature": signature,
        "result": {
            "provider": result.provider,
            "model": result.model,
            "text": result.text,
            "data": result.data,
            "fallback_used": bool(result.fallback_used),
            "raw": result.raw,
        },
    }

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(path)


def load_vision_cache(
    *,
    path: Path,
    stage_key: str,
    expected_signature: dict[str, Any],
) -> VisionResult:
    if not path.is_file():
        raise RuntimeError(
            f"Replay solicitado pero no existe cache para {stage_key}: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(f"Cache replay inválido: {path}") from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(f"Cache replay no es un objeto JSON: {path}")

    if payload.get("cache_version") != REPLAY_CACHE_VERSION:
        raise RuntimeError(f"Versión de cache replay incompatible en {path}")

    if payload.get("stage") != stage_key:
        raise RuntimeError(f"El cache replay corresponde a otra etapa: {path}")

    actual_signature = payload.get("signature")

    if actual_signature != expected_signature:
        mismatches = []

        if isinstance(
            actual_signature,
            dict,
        ):
            for key, expected_value in expected_signature.items():
                actual_value = actual_signature.get(key)

                if actual_value != expected_value:
                    mismatches.append(key)
        else:
            mismatches.append("signature")

        raise RuntimeError(
            "El cache replay no corresponde exactamente "
            "a esta llamada. Diferencias: " + ", ".join(mismatches)
        )

    cached_result = payload.get("result")

    if not isinstance(
        cached_result,
        dict,
    ):
        raise RuntimeError(f"Cache replay sin result válido: {path}")

    provider = str(
        cached_result.get(
            "provider",
            "",
        )
    ).strip()

    model = str(
        cached_result.get(
            "model",
            "",
        )
    ).strip()

    text = cached_result.get("text")

    data = cached_result.get("data")

    raw = cached_result.get("raw")

    if not provider:
        raise RuntimeError(f"Cache replay sin provider: {path}")

    if not model:
        raise RuntimeError(f"Cache replay sin model: {path}")

    if not isinstance(
        text,
        str,
    ):
        raise RuntimeError(f"Cache replay sin text válido: {path}")

    if not isinstance(
        data,
        (dict, list),
    ):
        raise RuntimeError(f"Cache replay sin data estructurada válida: {path}")

    if not isinstance(
        raw,
        dict,
    ):
        raise RuntimeError(f"Cache replay sin raw válido: {path}")

    return VisionResult(
        provider=provider,
        model=model,
        text=text,
        data=data,
        fallback_used=bool(
            cached_result.get(
                "fallback_used",
                False,
            )
        ),
        raw=raw,
    )


def validate_replay_cache_presence(
    cache_dir: Path,
) -> list[Path]:
    missing: list[Path] = []

    for stage_key in (
        "extraction",
        "localization",
    ):
        path = cache_path_for_stage(
            cache_dir,
            stage_key,
        )

        if not path.is_file():
            missing.append(path)

    return missing


# ============================================================
# CHECK
# ============================================================


class Check:
    def __init__(
        self,
        name: str,
        status: str,
        detail: str,
    ) -> None:
        self.name = name
        self.status = status
        self.detail = detail

    def to_dict(
        self,
    ) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }


# ============================================================
# NORMALIZACIÓN
# ============================================================


def normalize_text(
    value: Any,
) -> str:
    text = str(value or "").strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    return "".join(
        character for character in text if not unicodedata.combining(character)
    )


def is_bedroom_contract_space(
    space: Any,
) -> bool:
    semantic_text = normalize_text(
        " ".join(
            str(value or "")
            for value in (
                getattr(space, "nombre", None),
                getattr(space, "tipo", None),
            )
        )
    )

    return any(
        term in semantic_text
        for term in (
            "recamara",
            "dormitorio",
            "habitacion",
        )
    )


def close_to(
    value: float,
    expected: float,
    tolerance: float = 0.01,
) -> bool:
    return math.isclose(
        value,
        expected,
        rel_tol=0.0,
        abs_tol=tolerance,
    )


# ============================================================
# CONFIRMED
# ============================================================


def find_confirmed_true(
    value: Any,
    path: str = "contract",
) -> list[str]:
    result: list[str] = []

    if isinstance(
        value,
        dict,
    ):
        if value.get("confirmed") is True:
            result.append(path)

        for key, child in value.items():
            result.extend(
                find_confirmed_true(
                    child,
                    f"{path}.{key}",
                )
            )

    elif isinstance(
        value,
        list,
    ):
        for index, child in enumerate(value):
            result.extend(
                find_confirmed_true(
                    child,
                    f"{path}[{index}]",
                )
            )

    return result


# ============================================================
# NIVELES
# ============================================================


def extraction_level_names(
    result: Any,
) -> set[str]:
    names: set[str] = set()

    for level in result.semantic_reconciliation.extraction.niveles:
        name = normalize_text(
            getattr(
                level,
                "nombre",
                "",
            )
        )

        if name:
            names.add(name)

    return names


# ============================================================
# DIMENSIONES GROUNDED
# ============================================================


def grounded_values(
    result: Any,
) -> list[float]:
    values: list[float] = []

    for span in result.dimension_grounding.axis_spans:
        value = getattr(
            span,
            "value_m",
            None,
        )

        if isinstance(
            value,
            (int, float),
        ):
            values.append(float(value))

    for dimension in result.dimension_grounding.resolved_space_dimensions:
        value = getattr(
            dimension,
            "value_m",
            None,
        )

        if isinstance(
            value,
            (int, float),
        ):
            values.append(float(value))

    return values


# ============================================================
# RECÁMARAS
# ============================================================


def bedroom_dimension_groups(
    result: Any,
) -> dict[
    str,
    list[float],
]:
    groups: dict[
        str,
        list[float],
    ] = defaultdict(list)

    for dimension in result.dimension_grounding.resolved_space_dimensions:
        name = normalize_text(
            getattr(
                dimension,
                "space_name",
                "",
            )
        )

        if "recamara" not in name and "dormitorio" not in name:
            continue

        value = getattr(
            dimension,
            "value_m",
            None,
        )

        if not isinstance(
            value,
            (int, float),
        ):
            continue

        space_id = str(
            getattr(
                dimension,
                "space_id",
                "",
            )
            or name
        )

        groups[space_id].append(float(value))

    return groups


# ============================================================
# CHECKS
# ============================================================


def evaluate(
    result: Any,
) -> list[Check]:
    checks: list[Check] = []

    # --------------------------------------------------------
    # PDF VECTORIAL
    # --------------------------------------------------------

    if result.document_analysis.vector_text_available:
        checks.append(
            Check(
                "PDF vector text",
                "PASS",
                "PyMuPDF detectó texto vectorial.",
            )
        )

    else:
        checks.append(
            Check(
                "PDF vector text",
                "FAIL",
                "No se detectó texto vectorial.",
            )
        )

    if result.document_analysis.vector_geometry_available:
        checks.append(
            Check(
                "PDF vector geometry",
                "PASS",
                "PyMuPDF detectó geometría vectorial.",
            )
        )

    else:
        checks.append(
            Check(
                "PDF vector geometry",
                "FAIL",
                "No se detectó geometría vectorial.",
            )
        )

    # --------------------------------------------------------
    # NIVELES
    # --------------------------------------------------------

    actual_levels = extraction_level_names(result)

    missing_levels = EXPECTED_LEVELS - actual_levels

    if not missing_levels:
        checks.append(
            Check(
                "Levels PB/PA",
                "PASS",
                ("Detectados: " + ", ".join(sorted(actual_levels))),
            )
        )

    else:
        checks.append(
            Check(
                "Levels PB/PA",
                "FAIL",
                ("Faltan: " + ", ".join(sorted(missing_levels))),
            )
        )

    # --------------------------------------------------------
    # EJES
    # --------------------------------------------------------

    actual_axes = {
        str(axis.label).strip() for axis in result.dimension_grounding.axis_anchors
    }

    missing_axes = EXPECTED_AXIS_LABELS - actual_axes

    if not missing_axes:
        checks.append(
            Check(
                "Architectural axes",
                "PASS",
                "Todos los ejes baseline fueron encontrados.",
            )
        )

    else:
        checks.append(
            Check(
                "Architectural axes",
                "WARN",
                ("Ejes baseline aún no resueltos: " + ", ".join(sorted(missing_axes))),
            )
        )

    # --------------------------------------------------------
    # COTAS CRÍTICAS
    # --------------------------------------------------------

    values = grounded_values(result)

    missing_dimensions: list[float] = []

    for expected in EXPECTED_CRITICAL_DIMENSIONS:
        if not any(
            close_to(
                value,
                expected,
            )
            for value in values
        ):
            missing_dimensions.append(expected)

    if not missing_dimensions:
        checks.append(
            Check(
                "Critical dimensions 1.18 / 2.60 / 3.78 / 4.10",
                "PASS",
                "Los tramos y la dimensión compuesta aparecen en grounding.",
            )
        )

    else:
        checks.append(
            Check(
                "Critical dimensions 1.18 / 2.60 / 3.78 / 4.10",
                "FAIL",
                (
                    "No grounded: "
                    + ", ".join(f"{value:.2f}" for value in missing_dimensions)
                ),
            )
        )

    # --------------------------------------------------------
    # REGRESIÓN RECÁMARAS
    # --------------------------------------------------------

    bedroom_groups = bedroom_dimension_groups(result)

    if not bedroom_groups:
        checks.append(
            Check(
                "Bedroom 4.10 x 3.78 regression",
                "WARN",
                (
                    "Todavía no existen dimensiones "
                    "grounded asociadas semánticamente "
                    "a recámaras."
                ),
            )
        )

    else:
        regression_failed = False
        validated = 0

        details: list[str] = []

        for (
            space_id,
            space_values,
        ) in bedroom_groups.items():
            has_410 = any(
                close_to(
                    value,
                    4.10,
                )
                for value in space_values
            )

            has_378 = any(
                close_to(
                    value,
                    3.78,
                )
                for value in space_values
            )

            if has_410 and has_378:
                validated += 1

            details.append(
                (f"{space_id}=" + ", ".join(f"{value:.3f}" for value in space_values))
            )

        if regression_failed:
            status = "FAIL"

        elif validated:
            status = "PASS"

        else:
            status = "WARN"

        checks.append(
            Check(
                "Bedroom 4.10 x 3.78 regression",
                status,
                " | ".join(details),
            )
        )

    # --------------------------------------------------------
    # ZONAS ABIERTAS
    # --------------------------------------------------------

    zone_names = {
        normalize_text(zone.nombre) for zone in result.contract.zonasSemanticas
    }

    missing_zones = EXPECTED_OPEN_AREA_ZONES - zone_names

    if not missing_zones:
        checks.append(
            Check(
                "Open-area semantic zones",
                "PASS",
                ("Estancia, comedor y cocina se conservaron como zonas."),
            )
        )

    else:
        checks.append(
            Check(
                "Open-area semantic zones",
                "WARN",
                ("No aparecen todavía: " + ", ".join(sorted(missing_zones))),
            )
        )

    source_space_ids = {
        space.id_propuesto for space in result.geometry_reconciliation.spaces
    }
    published_source_ids = {space.id for space in result.contract.espacios}
    published_source_ids.update(
        zone.sourceSpaceId
        for zone in result.contract.zonasSemanticas
        if zone.sourceSpaceId
    )
    missing_contract_spaces = source_space_ids - published_source_ids

    checks.append(
        Check(
            "Contract semantic space coverage",
            "FAIL" if missing_contract_spaces else "PASS",
            (
                "No publicados: " + ", ".join(sorted(missing_contract_spaces))
                if missing_contract_spaces
                else f"Los {len(source_space_ids)} espacios semánticos llegan a 04."
            ),
        )
    )

    contract_bedrooms = [
        space
        for space in result.contract.espacios
        if is_bedroom_contract_space(space)
    ]
    contract_bedroom_failures: list[str] = []

    if len(contract_bedrooms) != 2:
        contract_bedroom_failures.append(
            f"cantidad de recámaras={len(contract_bedrooms)} (esperadas=2)"
        )

    for bedroom in contract_bedrooms:
        values = [dimension.valorM for dimension in bedroom.dimensiones]

        if not (
            any(close_to(value, 4.10) for value in values)
            and any(close_to(value, 3.78) for value in values)
        ):
            contract_bedroom_failures.append(bedroom.id)

    checks.append(
        Check(
            "Contract bedroom full dimensions",
            "FAIL" if contract_bedroom_failures else "PASS",
            (
                "Sin 4.10 x 3.78: " + ", ".join(contract_bedroom_failures)
                if contract_bedroom_failures
                else "Ambas recámaras publican 4.10 x 3.78 hacia 04."
            ),
        )
    )

    # --------------------------------------------------------
    # IDENTIDAD Y GEOMETRIA CONTRACTUAL DE MUROS
    # --------------------------------------------------------

    wall_run_ids = {
        wall_run.id for wall_run in result.wall_abstraction.wall_runs
    }
    eligible_centerlines = [
        centerline
        for centerline in result.wall_abstraction.centerlines
        if len(set(centerline.wall_run_ids) & wall_run_ids) >= 2
    ]
    consumed_wall_run_ids = {
        wall_run_id
        for centerline in eligible_centerlines
        for wall_run_id in centerline.wall_run_ids
        if wall_run_id in wall_run_ids
    }
    expected_wall_ids = (
        {centerline.id for centerline in eligible_centerlines}
        | (wall_run_ids - consumed_wall_run_ids)
    )
    actual_wall_ids = {wall.id for wall in result.contract.muros}

    invalid_segment_ids = [
        segment.id
        for wall in result.contract.muros
        for segment in wall.segmentos
        if not segment.id.startswith(f"{wall.id}_SEGMENT_")
    ]

    if actual_wall_ids == expected_wall_ids and not invalid_segment_ids:
        checks.append(
            Check(
                "Architectural wall contract identity",
                "PASS",
                (
                    f"{len(eligible_centerlines)} centerline(s) y "
                    f"{len(wall_run_ids - consumed_wall_run_ids)} wall run(s) "
                    "publicados con IDs estables."
                ),
            )
        )

    else:
        identity_details = []

        if actual_wall_ids != expected_wall_ids:
            identity_details.append(
                "faltan="
                + ",".join(sorted(expected_wall_ids - actual_wall_ids))
                + "; sobran="
                + ",".join(sorted(actual_wall_ids - expected_wall_ids))
            )

        if invalid_segment_ids:
            identity_details.append(
                "segmentos inestables=" + ",".join(sorted(invalid_segment_ids))
            )

        checks.append(
            Check(
                "Architectural wall contract identity",
                "FAIL",
                " | ".join(identity_details),
            )
        )

    invalid_wall_orientations: list[str] = []

    for wall in result.contract.muros:
        for segment in wall.segmentos:
            raster = segment.geometria.raster

            if raster is None or len(raster.vertices) != 2:
                invalid_wall_orientations.append(segment.id)
                continue

            first, second = raster.vertices
            is_horizontal = abs(first.y - second.y) <= 1e-6
            is_vertical = abs(first.x - second.x) <= 1e-6

            if (
                wall.orientacion == "horizontal" and not is_horizontal
            ) or (
                wall.orientacion == "vertical" and not is_vertical
            ):
                invalid_wall_orientations.append(segment.id)

    checks.append(
        Check(
            "Architectural wall segment orientation",
            "FAIL" if invalid_wall_orientations else "PASS",
            (
                "Segmentos incompatibles: "
                + ", ".join(sorted(invalid_wall_orientations))
                if invalid_wall_orientations
                else "Todos los segmentos coinciden con la orientación del muro."
            ),
        )
    )

    # --------------------------------------------------------
    # CONFIRMED
    # --------------------------------------------------------

    contract_dict = result.contract.model_dump(mode="json")

    confirmed_true = find_confirmed_true(contract_dict)

    if not confirmed_true:
        checks.append(
            Check(
                "confirmed=false invariant",
                "PASS",
                ("Ningún elemento automático llegó confirmado."),
            )
        )

    else:
        checks.append(
            Check(
                "confirmed=false invariant",
                "FAIL",
                ("Elementos confirmados automáticamente: " + ", ".join(confirmed_true)),
            )
        )

    # --------------------------------------------------------
    # PLANO BASE
    # --------------------------------------------------------

    if (
        result.contract.planoBase.anchoPx == result.raster_page.width_px
        and result.contract.planoBase.altoPx == result.raster_page.height_px
    ):
        checks.append(
            Check(
                "Canonical base layer",
                "PASS",
                (f"{result.raster_page.width_px}x{result.raster_page.height_px}"),
            )
        )

    else:
        checks.append(
            Check(
                "Canonical base layer",
                "FAIL",
                "El contrato no conserva el raster canónico.",
            )
        )

    # --------------------------------------------------------
    # MÉTRICA NO INVENTADA
    # --------------------------------------------------------

    invalid_metric_spaces = [
        space.id
        for space in result.contract.espacios
        if (
            space.geometria.metrica is None
            and (space.areaM2 is not None or space.geometria.vertices)
        )
    ]

    if not invalid_metric_spaces:
        checks.append(
            Check(
                "No px→m fabrication",
                "PASS",
                ("No se fabricó geometría métrica desde vértices raster."),
            )
        )

    else:
        checks.append(
            Check(
                "No px→m fabrication",
                "FAIL",
                ("Espacios contaminados: " + ", ".join(invalid_metric_spaces)),
            )
        )

    return checks


# ============================================================
# OUTPUT
# ============================================================


def write_outputs(
    *,
    result: Any,
    checks: list[Check],
    output_dir: Path,
    elapsed_seconds: float,
) -> None:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit_path = output_dir / "miguel_h_pipeline_audit.json"

    contract_path = output_dir / "miguel_h_contract_03_2_to_04.json"

    summary_path = output_dir / "miguel_h_regression_summary.json"

    raster_path = output_dir / "miguel_h_canonical_raster.png"

    audit_path.write_text(
        json.dumps(
            result.audit_dict(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    contract_path.write_text(
        json.dumps(
            result.contract.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    raster_path.write_bytes(result.raster_page.image_bytes)

    summary = {
        "execution_status": "PASS",
        "validation_status": (
            "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
        ),
        "elapsed_seconds": elapsed_seconds,
        "page": result.page,
        "raster": {
            "width_px": result.raster_page.width_px,
            "height_px": result.raster_page.height_px,
        },
        "gemini": {
            "extraction": {
                "model": result.extraction_vision.model,
                "fallback_used": result.extraction_vision.fallback_used,
            },
            "localization": {
                "model": result.localization_vision.model,
                "fallback_used": result.localization_vision.fallback_used,
            },
        },
        "counts": {
            "axes": len(result.dimension_grounding.axis_anchors),
            "axis_spans": len(result.dimension_grounding.axis_spans),
            "resolved_dimensions": len(
                result.dimension_grounding.resolved_space_dimensions
            ),
            "wall_runs": len(result.wall_abstraction.wall_runs),
            "centerlines": len(result.wall_abstraction.centerlines),
            "contract_walls": len(result.contract.muros),
            # Conservado por compatibilidad con consumidores anteriores.
            "walls": len(result.wall_geometry.walls),
            "faces": len(result.shapely_geometry.faces),
            "spaces": len(result.space_geometry.spaces),
            "space_candidates": len(result.space_geometry.spaces),
            "contract_spaces": len(result.contract.espacios),
            "semantic_fallback_spaces": sum(
                1
                for space in result.space_geometry.spaces
                if space.face_id.startswith("SEMANTIC_BBOX_")
            ),
            "semantic_zones": len(result.space_geometry.semantic_zones),
            "doors": len(result.contract.puertas),
            "windows": len(result.contract.ventanas),
            "stairs": len(result.contract.escaleras),
        },
        "checks": [check.to_dict() for check in checks],
    }

    summary_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Archivos generados:")
    print(f"  {audit_path}")
    print(f"  {contract_path}")
    print(f"  {summary_path}")
    print(f"  {raster_path}")


# ============================================================
# PRINT
# ============================================================


def print_checks(
    checks: list[Check],
) -> None:
    print()
    print("==============================================")
    print(" MIGUEL H — REGRESSION CHECKS")
    print("==============================================")
    print()

    for check in checks:
        print(f"[{check.status:<4}] {check.name}")

        print(f"       {check.detail}")

    failures = [item for item in checks if item.status == "FAIL"]

    warnings = [item for item in checks if item.status == "WARN"]

    print()
    print("----------------------------------------------")
    print(f"FAIL: {len(failures)}")
    print(f"WARN: {len(warnings)}")
    print("----------------------------------------------")


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Prueba funcional Quantia V2 03.2 sobre el plano Miguel H.")
    )

    parser.add_argument(
        "pdf",
        type=Path,
        help=("Ruta al archivo ARQUITECTONICO PB-PA MIGUE-H.pdf"),
    )

    parser.add_argument(
        "--render-scale",
        type=float,
        default=MIGUEL_H_RENDER_SCALE,
        help=("Factor de render PyMuPDF. Default Miguel H: 0.7935."),
    )

    parser.add_argument(
        "--ocr-strategy",
        choices=[
            "auto",
            "always",
        ],
        default="auto",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(Path("tests") / "output" / "miguel_h"),
    )

    parser.add_argument(
        "--replay",
        action="store_true",
        help=(
            "Reutiliza exactamente las respuestas Gemini "
            "guardadas y no realiza llamadas de red."
        ),
    )

    parser.add_argument(
        "--replay-cache-dir",
        type=Path,
        default=None,
        help=("Directorio del cache Gemini. Default: <output-dir>/gemini_replay."),
    )

    args = parser.parse_args()

    pdf_path = args.pdf.expanduser().resolve()

    if not pdf_path.is_file():
        print(f"ERROR: no existe el PDF: {pdf_path}")

        return 2

    if args.render_scale <= 0:
        print("ERROR: render-scale debe ser > 0.")

        return 2

    output_dir = args.output_dir.expanduser().resolve()

    replay_cache_dir = (
        args.replay_cache_dir.expanduser().resolve()
        if args.replay_cache_dir is not None
        else output_dir / "gemini_replay"
    )

    if args.replay:
        missing_cache_files = validate_replay_cache_presence(replay_cache_dir)

        if missing_cache_files:
            print("ERROR: --replay requiere cache Gemini completo.")

            for missing_path in missing_cache_files:
                print(f"  FALTA: {missing_path}")

            print("Ejecuta una corrida normal exitosa primero para generar el cache.")

            return 2

    # ========================================================
    # PROVIDER
    # ========================================================

    provider = get_gemini_vision_provider()

    if not args.replay and not provider.api_key:
        print("ERROR: GEMINI_API_KEY no está configurada.")

        return 2

    print()
    print("==============================================")
    print(" QUANTIA V2 — MIGUEL H FULL PIPELINE")
    print("==============================================")
    print()

    print(f"PDF: {pdf_path.name}")

    print(f"Render scale: {args.render_scale}")

    print("Gemini models: " + " → ".join(provider.models))

    print(f"OCR strategy: {args.ocr_strategy}")

    print(
        "Execution mode: "
        + (
            "REPLAY — cero llamadas Gemini"
            if args.replay
            else "NORMAL — Gemini activo + cache"
        )
    )

    print(f"Gemini replay cache: {replay_cache_dir}")

    # ========================================================
    # SERVICE
    # ========================================================

    service = QuantiaSpatialReconstructionService(
        extraction_prompt=QUANTIA_EXTRACTION_PROMPT,
        extraction_response_json_schema=get_gemini_extraction_transport_schema(),
        localization_prompt_builder=build_quantia_space_localization_prompt,
        localization_response_json_schema=get_gemini_space_localization_schema(),
        vision_provider=provider,
    )

    base_layer = BaseLayerDescriptor(
        id="QNT-03.2-001-PAGE-1",
        nombre=pdf_path.name,
        referencia=None,
        visible=True,
        bloqueado=True,
        ocultable=True,
        bloqueable=True,
    )

    # ========================================================
    # TEST OBSERVABILITY
    # ========================================================

    original_opencv_analyze = service.opencv_service.analyze

    def traced_opencv_analyze(
        *args,
        **kwargs,
    ):
        stage_started = time.perf_counter()

        print(
            "[03.2] OpenCV geometry ........ START",
            flush=True,
        )

        try:
            result = original_opencv_analyze(
                *args,
                **kwargs,
            )

        except Exception:
            elapsed = time.perf_counter() - stage_started

            print(
                f"[03.2] OpenCV geometry ........ FAIL ({elapsed:.2f}s)",
                flush=True,
            )

            raise

        elapsed = time.perf_counter() - stage_started

        print(
            f"[03.2] OpenCV geometry ........ OK ({elapsed:.2f}s)",
            flush=True,
        )

        return result

    service.opencv_service.analyze = traced_opencv_analyze

    original_vision_analyze = service.vision_provider.analyze

    gemini_call_number = 0

    def traced_vision_analyze(
        *vision_args,
        **kwargs,
    ):
        nonlocal gemini_call_number

        gemini_call_number += 1

        if gemini_call_number == 1:
            stage_key = "extraction"
            stage_name = "Gemini extraction"

        elif gemini_call_number == 2:
            stage_key = "localization"
            stage_name = "Gemini localization"

        else:
            stage_key = None
            stage_name = f"Gemini call {gemini_call_number}"

        stage_started = time.perf_counter()

        print(
            f"[03.2] {stage_name:<22} START",
            flush=True,
        )

        signature = vision_call_signature(
            prompt=kwargs.get("prompt"),
            media_bytes=kwargs.get("media_bytes"),
            media_mime_type=kwargs.get("media_mime_type"),
            response_json_schema=kwargs.get("response_json_schema"),
        )

        # ----------------------------------------------------
        # REPLAY
        # ----------------------------------------------------
        # En este modo no existe ninguna ruta silenciosa
        # hacia Gemini. Cache ausente/incompatible = FAIL.
        # ----------------------------------------------------

        if args.replay:
            if stage_key is None:
                raise RuntimeError(
                    "Replay recibió una llamada Gemini adicional "
                    "no contemplada por la prueba Miguel H."
                )

            try:
                result = load_vision_cache(
                    path=cache_path_for_stage(
                        replay_cache_dir,
                        stage_key,
                    ),
                    stage_key=stage_key,
                    expected_signature=signature,
                )

            except Exception:
                elapsed = time.perf_counter() - stage_started

                print(
                    f"[03.2] {stage_name:<22} FAIL ({elapsed:.2f}s) [REPLAY]",
                    flush=True,
                )

                raise

            elapsed = time.perf_counter() - stage_started

            print(
                f"[03.2] {stage_name:<22} OK ({elapsed:.2f}s) [REPLAY:{result.model}]",
                flush=True,
            )

            return result

        # ----------------------------------------------------
        # NORMAL
        # ----------------------------------------------------

        stop_heartbeat = threading.Event()

        def heartbeat() -> None:
            while not stop_heartbeat.wait(15):
                elapsed = time.perf_counter() - stage_started

                print(
                    f"       {stage_name} working... {elapsed:.0f}s",
                    flush=True,
                )

        heartbeat_thread = threading.Thread(
            target=heartbeat,
            daemon=True,
        )

        heartbeat_thread.start()

        try:
            result = original_vision_analyze(
                *vision_args,
                **kwargs,
            )

            if stage_key is not None:
                write_vision_cache(
                    path=cache_path_for_stage(
                        replay_cache_dir,
                        stage_key,
                    ),
                    stage_key=stage_key,
                    signature=signature,
                    result=result,
                )

        except Exception:
            elapsed = time.perf_counter() - stage_started

            print(
                f"[03.2] {stage_name:<22} FAIL ({elapsed:.2f}s)",
                flush=True,
            )

            raise

        finally:
            stop_heartbeat.set()

        elapsed = time.perf_counter() - stage_started

        model = getattr(
            result,
            "model",
            None,
        )

        print(
            f"[03.2] {stage_name:<22} OK "
            f"({elapsed:.2f}s)"
            + (f" [{model}]" if model else "")
            + (" [cache updated]" if stage_key is not None else ""),
            flush=True,
        )

        return result

    service.vision_provider.analyze = traced_vision_analyze

    # ========================================================
    # EXECUTION
    # ========================================================

    started = time.perf_counter()

    try:
        result = service.reconstruct_page(
            document_bytes=pdf_path.read_bytes(),
            mime_type="application/pdf",
            page_number=1,
            base_layer=base_layer,
            pdf_render_scale=args.render_scale,
            ocr_strategy=args.ocr_strategy,
            # Primera prueba:
            # no aplicar 0.15 m globalmente.
            thickness_evidence=None,
            domain_rule_targets=None,
        )

    except Exception as exc:
        print()
        print("PIPELINE = FAIL")

        print(f"{type(exc).__name__}: {exc}")

        raise

    elapsed = time.perf_counter() - started

    print("\n==============================================")
    print(" BOUNDARY CANDIDATES — MUROS DE CONTROL")
    print("==============================================")

    target_spaces = {
        "pa_recamara_1",
        "pa_recamara_2",
        "pa_pasillo_circulacion",
    }

    for space in result.geometry_reconciliation.spaces:
        if space.id_propuesto not in target_spaces:
            continue

        print(f"\nSPACE: {space.id_propuesto}")

        for side in (
            "left",
            "right",
            "top",
            "bottom",
        ):
            candidates = getattr(
                space.boundaries,
                side,
            )

            print(f"  {side.upper()}:")

            for candidate in candidates:
                coordinate = (
                    (candidate.x1 + candidate.x2) / 2.0
                    if candidate.orientation == "vertical"
                    else (candidate.y1 + candidate.y2) / 2.0
                )

                print(
                    f"    {candidate.opencv_segment_id}"
                    f" | coord={coordinate:.2f}"
                    f" | len={candidate.length_px:.2f}"
                    f" | coverage={candidate.bbox_coverage_ratio:.3f}"
                    f" | dist_bbox={candidate.distance_to_bbox_edge_px:.2f}"
                    f" | center={candidate.crosses_space_center}"
                    f" | vector={bool(candidate.vector_support_indices)}"
                    f" | sources={candidate.sources}"
                )

    print("\n==============================================")
    print(" OPENCV SEGMENTS — MUROS DE CONTROL")
    print("==============================================")

    target_ids = {
        "CV_V_38",
        "CV_V_39",
        "CV_V_41",
        "CV_V_42",
        "CV_V_43",
        "CV_V_7",
        "CV_V_9",
        "CV_V_60",
        "CV_V_75",
        "CV_V_76",
    }

    for segment in result.opencv_geometry.vertical_segments:
        if segment.id not in target_ids:
            continue

        print(
            f"{segment.id}"
            f" | x1={segment.x1:.2f}"
            f" | y1={segment.y1:.2f}"
            f" | x2={segment.x2:.2f}"
            f" | y2={segment.y2:.2f}"
            f" | len={segment.length_px:.2f}"
        )
    print("\n==============================================")
    print(" WALL RUN EVIDENCE — CONTROL")
    print("==============================================")

    for wall_run in result.wall_abstraction.wall_runs:
        if any(
            segment_id
            in {
                "CV_V_38",
                "CV_V_39",
                "CV_V_41",
                "CV_V_42",
            }
            for segment_id in wall_run.face_segment_ids
        ):
            print(
                f"{wall_run.id}"
                f" | orientation={wall_run.orientation}"
                f" | face={wall_run.face_segment_ids}"
                f" | endpoint={wall_run.endpoint_support_ids}"
                f" | spaces={wall_run.space_ids}"
                f" | sides={wall_run.space_sides}"
            )
    print("\n==============================================")
    print(" WALL FACE PAIRS — DIAGNOSTIC")
    print("==============================================")

    wall_runs = result.wall_abstraction.wall_runs

    pairs = []

    for index, first in enumerate(wall_runs):
        for second in wall_runs[index + 1 :]:
            if first.orientation != second.orientation:
                continue

            shared_levels = set(first.levels) & set(second.levels)

            if not shared_levels:
                continue

            first_sides = set(first.space_sides.values())

            second_sides = set(second.space_sides.values())

            if first.orientation == "vertical":
                opposite = ("right" in first_sides and "left" in second_sides) or (
                    "left" in first_sides and "right" in second_sides
                )

                if not opposite:
                    continue

                coordinate_distance = abs(float(first.x1) - float(second.x1))

                first_start = min(
                    float(first.y1),
                    float(first.y2),
                )

                first_end = max(
                    float(first.y1),
                    float(first.y2),
                )

                second_start = min(
                    float(second.y1),
                    float(second.y2),
                )

                second_end = max(
                    float(second.y1),
                    float(second.y2),
                )

            elif first.orientation == "horizontal":
                opposite = ("bottom" in first_sides and "top" in second_sides) or (
                    "top" in first_sides and "bottom" in second_sides
                )

                if not opposite:
                    continue

                coordinate_distance = abs(float(first.y1) - float(second.y1))

                first_start = min(
                    float(first.x1),
                    float(first.x2),
                )

                first_end = max(
                    float(first.x1),
                    float(first.x2),
                )

                second_start = min(
                    float(second.x1),
                    float(second.x2),
                )

                second_end = max(
                    float(second.x1),
                    float(second.x2),
                )

            else:
                continue

            overlap = max(
                0.0,
                min(
                    first_end,
                    second_end,
                )
                - max(
                    first_start,
                    second_start,
                ),
            )

            if overlap <= 0:
                continue

            shorter_length = min(
                first_end - first_start,
                second_end - second_start,
            )

            overlap_ratio = overlap / shorter_length if shorter_length > 0 else 0.0

            pairs.append(
                (
                    coordinate_distance,
                    -overlap_ratio,
                    first,
                    second,
                    overlap,
                    overlap_ratio,
                )
            )

    pairs.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    for (
        distance,
        _,
        first,
        second,
        overlap,
        overlap_ratio,
    ) in pairs:
        print(
            f"{first.id}"
            f" {first.space_sides}"
            f" <-> "
            f"{second.id}"
            f" {second.space_sides}"
            f" | orientation={first.orientation}"
            f" | distance={distance:.2f}px"
            f" | overlap={overlap:.2f}px"
            f" | overlap_ratio={overlap_ratio:.3f}"
        )
    print("\n==============================================")
    print(" CENTERLINES — WALL ABSTRACTION RESULT")
    print("==============================================")

    centerlines = result.wall_abstraction.centerlines

    print(f"Total centerlines almacenados: {len(centerlines)}")

    for centerline in centerlines:
        print(
            f"{centerline.id}"
            f" | walls={centerline.wall_run_ids}"
            f" | spaces={centerline.space_ids}"
            f" | orientation={centerline.orientation}"
            f" | x1={centerline.x1:.2f}"
            f" | y1={centerline.y1:.2f}"
            f" | x2={centerline.x2:.2f}"
            f" | y2={centerline.y2:.2f}"
            f" | length={centerline.length_px:.2f}px"
            f" | thickness={centerline.thickness_px:.2f}px"
            f" | overlap_ratio={centerline.overlap_ratio:.3f}"
            f" | confirmed={centerline.confirmed}"
        )
    print("\n==============================================")
    print(" GRAPH CENTERLINE COLLECTION — DIAGNOSTIC")
    print("==============================================")

    graph_centerlines = service.graph_builder._collect_centerlines(
        result.wall_abstraction
    )

    print(f"Total segmentos centerline recolectados: {len(graph_centerlines)}")

    for segment_id, segment in graph_centerlines.items():
        print(
            f"{segment_id}"
            f" | orientation={segment.orientation}"
            f" | x1={segment.x1:.2f}"
            f" | y1={segment.y1:.2f}"
            f" | x2={segment.x2:.2f}"
            f" | y2={segment.y2:.2f}"
            f" | sources={sorted(segment.sources)}"
            f" | source_segments={sorted(segment.source_segment_ids)}"
            f" | spaces={sorted(segment.space_ids)}"
            f" | support={segment.support_count}"
        )
    print("\n==============================================")
    print(" HYBRID GRAPH COLLECTION — DIAGNOSTIC")
    print("==============================================")

    hybrid_segments = service.graph_builder._collect_hybrid_segments(
        reconciliation=(result.geometry_reconciliation),
        abstraction=(result.wall_abstraction),
    )

    consumed_ids = {
        "CV_V_38",
        "CV_V_39",
        "CV_V_41",
        "CV_V_42",
    }

    print(f"Total segmentos híbridos: {len(hybrid_segments)}")

    print(f"CENTERLINE_1 presente: {'CENTERLINE_1' in hybrid_segments}")

    for segment_id in sorted(consumed_ids):
        print(f"{segment_id} presente: {segment_id in hybrid_segments}")

    centerline_segment = hybrid_segments.get("CENTERLINE_1")

    if centerline_segment is not None:
        print(
            "CENTERLINE_1"
            f" | x1={centerline_segment.x1:.2f}"
            f" | y1={centerline_segment.y1:.2f}"
            f" | x2={centerline_segment.x2:.2f}"
            f" | y2={centerline_segment.y2:.2f}"
            f" | source_segments="
            f"{sorted(centerline_segment.source_segment_ids)}"
            f" | spaces="
            f"{sorted(centerline_segment.space_ids)}"
        )
    print("\n==============================================")
    print(" CENTERLINE INTERSECTIONS — DIAGNOSTIC")
    print("==============================================")

    graph_tolerance = service.graph_builder._coordinate_tolerance(
        result.opencv_geometry
    )

    centerline_intersections = service.graph_builder._build_centerline_intersection_map(
        abstraction=(result.wall_abstraction),
        collected=hybrid_segments,
        opencv_geometry=(result.opencv_geometry),
        tolerance=graph_tolerance,
    )

    print(f"Tolerance: {graph_tolerance:.2f}px")

    centerline_points = centerline_intersections.get(
        "CENTERLINE_1",
        [],
    )

    print(f"CENTERLINE_1 intersection points: {len(centerline_points)}")

    for index, point in enumerate(
        centerline_points,
        start=1,
    ):
        print(f"P{index} | x={point[0]:.2f} | y={point[1]:.2f}")

    print(
        "IDs con intersecciones transferidas: "
        f"{sorted(centerline_intersections.keys())}"
    )

    print("\n==============================================")
    print(" CENTERLINE GRAPH — ISOLATED TEST")
    print("==============================================")

    centerline_graph = service.graph_builder.build(
        reconciliation=(result.geometry_reconciliation),
        opencv_geometry=(result.opencv_geometry),
        wall_abstraction=(result.wall_abstraction),
    )

    print(f"Nodes: {len(centerline_graph.nodes)}")

    print(f"Edges: {len(centerline_graph.edges)}")

    for note in centerline_graph.notes:
        print(f"NOTE: {note}")

    for node in centerline_graph.nodes:
        print(
            f"{node.id}"
            f" | x={node.x:.2f}"
            f" | y={node.y:.2f}"
            f" | degree={node.degree}"
            f" | source_segments={node.source_segment_ids}"
        )

    for edge in centerline_graph.edges:
        print(
            f"{edge.id}"
            f" | orientation={edge.orientation}"
            f" | x1={edge.x1:.2f}"
            f" | y1={edge.y1:.2f}"
            f" | x2={edge.x2:.2f}"
            f" | y2={edge.y2:.2f}"
            f" | length={edge.length_px:.2f}px"
            f" | source_segments={edge.source_segment_ids}"
            f" | spaces={edge.space_ids}"
            f" | confirmed={edge.confirmed}"
        )

    print("\n==============================================")
    print(" WALL FACE GROUPING — DIAGNOSTIC")
    print("==============================================")

    tolerance = result.opencv_geometry.diagnostics.parameters.axis_tolerance_px

    print(f"axis_tolerance_px={tolerance}")

    target_coordinates = {
        "FACE_A": 824.0,
        "FACE_B": 843.0,
    }

    for name, coordinate in target_coordinates.items():
        print(f"\n{name} x={coordinate:.2f}")

        for segment in result.opencv_geometry.vertical_segments:
            delta = abs(segment.midpoint_x - coordinate)

            if delta <= tolerance:
                print(
                    f"  {segment.id}"
                    f" | x={segment.midpoint_x:.2f}"
                    f" | y={min(segment.y1, segment.y2):.2f}"
                    f"→{max(segment.y1, segment.y2):.2f}"
                    f" | len={segment.length_px:.2f}"
                    f" | delta={delta:.2f}"
                )
    print("\n==============================================")
    print(" OPENCV PARAMETERS — DIAGNOSTIC")
    print("==============================================")

    parameters = result.opencv_geometry.diagnostics.parameters

    for name in dir(parameters):
        if name.startswith("_"):
            continue

        value = getattr(
            parameters,
            name,
        )

        if isinstance(
            value,
            (
                int,
                float,
                str,
                bool,
                type(None),
            ),
        ):
            print(f"{name}={value}")

    # ========================================================
    # RESULT
    # ========================================================

    print()
    print("PIPELINE EXECUTION = OK")

    print(f"Tiempo: {elapsed:.2f} s")

    print(
        "Gemini extracción: "
        f"{result.extraction_vision.model}"
        " | fallback="
        f"{result.extraction_vision.fallback_used}"
    )

    print(
        "Gemini localización: "
        f"{result.localization_vision.model}"
        " | fallback="
        f"{result.localization_vision.fallback_used}"
    )

    print(f"Raster: {result.raster_page.width_px}x{result.raster_page.height_px}")

    print(f"Espacios: {len(result.space_geometry.spaces)}")

    print(f"Muros: {len(result.wall_geometry.walls)}")

    print(f"Faces: {len(result.shapely_geometry.faces)}")

    print(f"Ejes: {len(result.dimension_grounding.axis_anchors)}")

    checks = evaluate(result)

    print_checks(checks)

    failures = [check for check in checks if check.status == "FAIL"]

    print(
        "PIPELINE VALIDATION = "
        + ("FAIL" if failures else "PASS")
    )

    write_outputs(
        result=result,
        checks=checks,
        output_dir=output_dir,
        elapsed_seconds=elapsed,
    )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
