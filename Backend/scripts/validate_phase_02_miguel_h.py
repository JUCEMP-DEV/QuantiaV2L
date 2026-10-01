from __future__ import annotations

import argparse
import json
import math
import mimetypes
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from app.quantia_spatial.models.evidence import RawEvidence
from app.quantia_spatial.phase_01_level.level_identification_service import (
    LevelIdentificationService,
)
from app.quantia_spatial.phase_015_evidence.evidence_pipeline import EvidencePipeline
from app.quantia_spatial.phase_015_evidence.gemini_evidence_adapter import (
    GeminiEvidenceAdapter,
)
from app.quantia_spatial.phase_015_evidence.gemini_semantic_history import (
    GeminiSemanticHistory,
)
from app.quantia_spatial.phase_02_boundaries.perimeter_wall_pipeline import (
    PerimeterWallPipeline,
)


EXPECTED_PAGE_NUMBER = 1
EXPECTED_SOURCE_DOCUMENT_ID = "MIGUEL_H_PHASE_02"

_GENERAL_SPAN_VALUES = {"GENERAL", "TOTAL", "OVERALL"}
_HORIZONTAL_VALUES = {"HORIZONTAL", "H", "X"}
_VERTICAL_VALUES = {"VERTICAL", "V", "Y"}
_LENGTH_UNITS = {"M", "CM", "MM"}


# ============================================================================
# UTILIDADES DE ENTRADA
# ============================================================================


def load_localization_replay(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("El replay de localización debe contener un objeto JSON.")

    result = data.get("result")
    if not isinstance(result, dict):
        raise ValueError("El replay de localización no contiene result.")

    payload = result.get("data")
    if not isinstance(payload, dict):
        raise ValueError("El replay de localización no contiene result.data.")

    if payload.get("pagina") != EXPECTED_PAGE_NUMBER:
        raise ValueError(
            "El replay de localización no corresponde a la página canónica esperada."
        )

    levels = payload.get("niveles")
    if not isinstance(levels, list) or not levels:
        raise ValueError("El replay de localización no contiene niveles.")

    return payload


def infer_media_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"

    guessed, _ = mimetypes.guess_type(path.name)
    if guessed in {"application/pdf", "image/png", "image/jpeg"}:
        return guessed

    raise ValueError(f"No se pudo determinar un MIME soportado para: {path}")


def expected_levels_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in payload["niveles"]
        if (
            isinstance(item, dict)
            and item.get("localizado") is True
            and isinstance(item.get("bbox_normalizado"), dict)
        )
    ]


# ============================================================================
# HISTÓRICO SEMÁNTICO GEMINI
# ============================================================================


def load_success_history_event(*, history_path: Path, call_id: str) -> dict[str, Any]:
    if not history_path.is_file():
        raise ValueError(f"No existe semantic history: {history_path}")

    matched: list[dict[str, Any]] = []

    for raw_line in history_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(item, dict):
            continue

        if item.get("call_id") == call_id and item.get("event") == "SUCCEEDED":
            matched.append(item)

    if not matched:
        raise ValueError(
            f"No existe evento SUCCEEDED para semantic_call_id={call_id}."
        )

    return matched[-1]


# ============================================================================
# NORMALIZACIÓN SEMÁNTICA
# ============================================================================


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().upper().split())


def normalize_orientation(value: object) -> str | None:
    text = normalize_text(value)
    if text in _HORIZONTAL_VALUES:
        return "HORIZONTAL"
    if text in _VERTICAL_VALUES:
        return "VERTICAL"
    return None


def measurement_to_meters(measurement: dict[str, Any]) -> float | None:
    unit = normalize_text(measurement.get("unit"))
    if unit not in _LENGTH_UNITS:
        return None

    value = measurement.get("value")
    if isinstance(value, bool):
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if parsed <= 0.0:
        return None

    if unit == "M":
        return parsed
    if unit == "CM":
        return parsed / 100.0
    return parsed / 1000.0


def gemini_evidence(evidence: list[RawEvidence]) -> list[RawEvidence]:
    return [
        item
        for item in evidence
        if item.kind == "GEMINI_OBSERVATION" and item.source == "GEMINI"
    ]


def semantic_category(item: RawEvidence) -> str:
    return normalize_text(item.metadata.get("semantic_category")) or "OTHER"


def semantic_category_counts(evidence: list[RawEvidence]) -> dict[str, int]:
    counter = Counter(semantic_category(item) for item in gemini_evidence(evidence))
    return dict(sorted(counter.items()))


def relevant_general_dimensions(evidence: list[RawEvidence]) -> list[dict[str, Any]]:
    """
    Extrae exclusivamente cotas longitudinales GENERAL/TOTAL/OVERALL H/V.

    Estas son las observaciones que la implementación actual de F02 puede
    asociar de forma demostrable al span completo del perímetro sin inventar
    correspondencias locales.
    """

    result: list[dict[str, Any]] = []

    for item in gemini_evidence(evidence):
        if semantic_category(item) != "DIMENSION":
            continue

        metadata = item.metadata
        raw_observation = metadata.get("raw_observation")
        raw_observation = raw_observation if isinstance(raw_observation, dict) else {}

        default_orientation = normalize_orientation(
            metadata.get("orientation") or raw_observation.get("orientation")
        )
        default_span = normalize_text(
            metadata.get("span_type") or raw_observation.get("span_type")
        )

        measurements = metadata.get("measurements")
        if not isinstance(measurements, list):
            continue

        for index, measurement in enumerate(measurements):
            if not isinstance(measurement, dict):
                continue

            value_m = measurement_to_meters(measurement)
            if value_m is None:
                continue

            orientation = normalize_orientation(
                measurement.get("orientation") or default_orientation
            )
            span_type = normalize_text(
                measurement.get("span_type") or default_span
            )

            if orientation is None or span_type not in _GENERAL_SPAN_VALUES:
                continue

            result.append(
                {
                    "evidence_id": item.id,
                    "measurement_index": index,
                    "visible_text": measurement.get("text") or item.text,
                    "value_m": value_m,
                    "orientation": orientation,
                    "span_type": span_type,
                    "reference_start": (
                        measurement.get("reference_start")
                        or metadata.get("reference_start")
                    ),
                    "reference_end": (
                        measurement.get("reference_end")
                        or metadata.get("reference_end")
                    ),
                }
            )

    return result


# ============================================================================
# COMPARACIÓN F02 ↔ GEMINI F01.5
# ============================================================================


def compare_semantics(*, evidence: list[RawEvidence], phase_02_result: Any) -> dict[str, Any]:
    gemini = gemini_evidence(evidence)
    grounding = phase_02_result.grounding
    resolution = phase_02_result.resolution

    selected_semantic_ids: set[str] = set()
    candidate_semantic_ids: set[str] = set()

    if resolution.selected is not None:
        selected_semantic_ids.update(resolution.selected.semantic_evidence_ids)

    for candidate in resolution.candidates:
        candidate_semantic_ids.update(candidate.semantic_evidence_ids)

    dimension_refs_by_evidence: dict[str, list[Any]] = {}
    conflict_ids: set[str] = set()
    declared_scale_ids: set[str] = set()

    if grounding is not None:
        for ref in grounding.dimension_references:
            dimension_refs_by_evidence.setdefault(ref.evidence_id, []).append(ref)
        conflict_ids.update(grounding.conflict_evidence_ids)
        declared_scale_ids.update(grounding.declared_scale_evidence_ids)

    checks: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # BOUNDARY / WALL observations
    # ------------------------------------------------------------------
    boundary_wall = [
        item
        for item in gemini
        if semantic_category(item) in {"BOUNDARY_OBSERVATION", "WALL_OBSERVATION"}
    ]

    for item in boundary_wall:
        if item.id in selected_semantic_ids:
            status = "MATCH"
            detail = "La observación semántica respalda el candidato seleccionado."
        elif item.id in candidate_semantic_ids:
            status = "PARTIAL"
            detail = (
                "La observación se asoció a candidato(s), pero no al perímetro "
                "final seleccionado."
            )
        else:
            status = "UNRESOLVED"
            detail = "F02 no pudo asociar esta observación a un candidato perimetral."

        checks.append(
            {
                "type": "BOUNDARY_WALL",
                "evidence_id": item.id,
                "category": semantic_category(item),
                "text": item.text,
                "status": status,
                "detail": detail,
            }
        )

    # ------------------------------------------------------------------
    # GENERAL dimensions
    # ------------------------------------------------------------------
    for dimension in relevant_general_dimensions(evidence):
        evidence_id = str(dimension["evidence_id"])
        refs = dimension_refs_by_evidence.get(evidence_id, [])

        matching_refs = [
            ref
            for ref in refs
            if (
                ref.orientation == dimension["orientation"]
                and math.isclose(
                    float(ref.value_m),
                    float(dimension["value_m"]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )
        ]

        if evidence_id in conflict_ids or any(ref.state == "CONFLICT" for ref in refs):
            status = "CONFLICT"
            detail = "La cota participa en un conflicto dimensional dentro de F02."
        elif matching_refs and all(ref.state == "GROUNDED" for ref in matching_refs):
            status = "MATCH"
            detail = "La cota GENERAL fue asociada al span geométrico correspondiente."
        elif matching_refs:
            status = "PARTIAL"
            detail = "La cota fue reconocida por F02, pero su grounding no quedó completo."
        else:
            status = "UNRESOLVED"
            detail = "F02 no produjo una referencia de grounding para esta cota GENERAL."

        checks.append(
            {
                "type": "GENERAL_DIMENSION",
                **dimension,
                "status": status,
                "detail": detail,
                "f02_reference_ids": [ref.id for ref in matching_refs],
                "f02_meters_per_px": [ref.meters_per_px for ref in matching_refs],
            }
        )

    # ------------------------------------------------------------------
    # SCALE / DOCUMENT scale declaration
    # ------------------------------------------------------------------
    for item in gemini:
        category = semantic_category(item)
        if category not in {"SCALE", "DOCUMENT"}:
            continue

        raw_text = " ".join(
            str(value or "")
            for value in (
                item.text,
                item.metadata.get("raw_observation"),
            )
        )
        if ":" not in raw_text:
            continue

        if item.id in declared_scale_ids:
            status = "MATCH"
            detail = (
                "La escala declarada fue preservada por F02 como evidencia, "
                "pero no se usó por sí sola para imponer px→m."
            )
        else:
            status = "PARTIAL"
            detail = (
                "Existe observación de escala, pero F02 no la identificó como "
                "evidencia declarada utilizable."
            )

        checks.append(
            {
                "type": "DECLARED_SCALE",
                "evidence_id": item.id,
                "category": category,
                "text": item.text,
                "status": status,
                "detail": detail,
            }
        )

    status_counts = Counter(item["status"] for item in checks)

    if status_counts.get("CONFLICT", 0) > 0:
        overall = "CONFLICT"
    elif checks and status_counts.get("UNRESOLVED", 0) == 0 and status_counts.get(
        "PARTIAL", 0
    ) == 0:
        overall = "MATCH"
    elif checks and status_counts.get("MATCH", 0) > 0:
        overall = "PARTIAL"
    else:
        overall = "UNRESOLVED"

    return {
        "state": overall,
        "status_counts": dict(sorted(status_counts.items())),
        "checks": checks,
    }


# ============================================================================
# VERIFICACIÓN DE NO PÉRDIDA GEMINI -> RAWEVIDENCE
# ============================================================================


def compare_history_to_raw_evidence(
    *,
    history_event: dict[str, Any],
    evidence: list[RawEvidence],
    call_id: str,
) -> dict[str, Any]:
    payload = history_event.get("semantic_payload")
    payload = payload if isinstance(payload, dict) else {}
    observations = payload.get("observations")
    observations = observations if isinstance(observations, list) else []

    raw_for_call = [
        item
        for item in gemini_evidence(evidence)
        if str(item.metadata.get("semantic_call_id") or "") == call_id
    ]

    history_count = len(observations)
    raw_count = len(raw_for_call)

    return {
        "history_observation_count": history_count,
        "raw_evidence_count": raw_count,
        "same_count": history_count == raw_count,
        "semantic_contract_version": payload.get("semantic_contract_version"),
        "history_model": history_event.get("model"),
        "fallback_used": bool(history_event.get("fallback_used", False)),
        "conflicts": payload.get("conflicts") or [],
        "unidentified_relevant_data": payload.get("unidentified_relevant_data") or [],
    }


# ============================================================================
# OVERLAY
# ============================================================================


def write_overlay(*, level_view: Any, phase_02_result: Any, output_path: Path) -> None:
    if phase_02_result.wall_layer is None:
        return

    with Image.open(BytesIO(level_view.raster_bytes)) as source:
        image = source.convert("RGB")

    draw = ImageDraw.Draw(image)
    runs = sorted(
        phase_02_result.wall_layer.wall_runs,
        key=lambda item: item.sequence_index,
    )

    for run in runs:
        draw.line(
            [
                (run.start_px.x, run.start_px.y),
                (run.end_px.x, run.end_px.y),
            ],
            width=4,
        )
        midpoint = (
            (run.start_px.x + run.end_px.x) / 2.0,
            (run.start_px.y + run.end_px.y) / 2.0,
        )
        metric = f"{run.length_m:.3f}m" if run.length_m is not None else "?m"
        draw.text(midpoint, f"{run.sequence_index}:{metric}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")


# ============================================================================
# REPORTE
# ============================================================================


def level_report(
    *,
    level_view: Any,
    phase_015_result: Any,
    phase_02_result: Any,
    history_check: dict[str, Any],
    semantic_comparison: dict[str, Any],
) -> dict[str, Any]:
    wall_layer = phase_02_result.wall_layer
    grounding = phase_02_result.grounding

    runs: list[dict[str, Any]] = []
    if wall_layer is not None:
        for run in sorted(wall_layer.wall_runs, key=lambda item: item.sequence_index):
            runs.append(
                {
                    "id": run.id,
                    "sequence_index": run.sequence_index,
                    "start_px": [run.start_px.x, run.start_px.y],
                    "end_px": [run.end_px.x, run.end_px.y],
                    "drawing_orientation": run.drawing_orientation,
                    "drawing_side": run.drawing_side,
                    "cardinal_side": run.cardinal_side,
                    "length_px": run.length_px,
                    "length_m": run.length_m,
                    "metric_status": run.metric_status,
                    "geometry_source": run.geometry_source,
                    "evidence_ids": list(run.evidence_ids),
                    "dimensional_evidence_ids": list(run.dimensional_evidence_ids),
                    "confirmed": run.confirmed,
                }
            )

    return {
        "level_view_id": level_view.id,
        "level_name": level_view.level_name,
        "phase_015": {
            "total_evidence": phase_015_result.diagnostics.total_count,
            "kind_counts": phase_015_result.diagnostics.kind_counts,
            "source_diagnostics": {
                key: value.model_dump()
                for key, value in phase_015_result.diagnostics.source_diagnostics.items()
            },
            "gemini_call_id": phase_015_result.diagnostics.gemini_call_id,
            "gemini_semantic_history_path": (
                phase_015_result.diagnostics.gemini_semantic_history_path
            ),
            "gemini_category_counts": semantic_category_counts(
                phase_015_result.evidence
            ),
            "warnings": list(phase_015_result.warnings),
            "history_integrity": history_check,
        },
        "phase_02": {
            "state": phase_02_result.state,
            "resolution_state": phase_02_result.resolution.state,
            "candidate_count": len(phase_02_result.candidates),
            "selected_candidate_id": (
                phase_02_result.resolution.selected.id
                if phase_02_result.resolution.selected is not None
                else None
            ),
            "validation": phase_02_result.validation.model_dump(),
            "diagnostics": phase_02_result.diagnostics.model_dump(),
            "grounding": grounding.model_dump() if grounding is not None else None,
            "total_length_px": (
                wall_layer.total_length_px if wall_layer is not None else None
            ),
            "total_length_m": (
                wall_layer.total_length_m if wall_layer is not None else None
            ),
            "metric_status": (
                wall_layer.metric_status if wall_layer is not None else None
            ),
            "metric_scale_m_per_px": (
                wall_layer.metric_scale.meters_per_px
                if wall_layer is not None and wall_layer.metric_scale is not None
                else None
            ),
            "wall_runs": runs,
            "warnings": list(phase_02_result.warnings),
        },
        "semantic_cross_check": semantic_comparison,
    }


def classify_level_result(report: dict[str, Any]) -> str:
    phase_015 = report["phase_015"]
    phase_02 = report["phase_02"]
    semantic = report["semantic_cross_check"]

    gemini_diag = phase_015["source_diagnostics"].get("GEMINI", {})

    if gemini_diag.get("status") != "SUCCEEDED":
        return "FAIL"
    if not phase_015["history_integrity"].get("same_count", False):
        return "FAIL"
    if phase_02["state"] == "INVALID":
        return "FAIL"
    if semantic["state"] == "CONFLICT":
        return "FAIL"

    if phase_02["state"] == "VALID" and semantic["state"] == "MATCH":
        return "PASS"

    return "REVIEW"


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validación funcional Fase 02 Miguel H: ejecuta F01, F01.5 y F02 "
            "y compara la reconstrucción perimetral contra la semántica Gemini "
            "de la misma llamada F01.5."
        )
    )
    parser.add_argument(
        "--raster",
        required=True,
        type=Path,
        help="Raster canónico de la página Miguel H usado por F01.",
    )
    parser.add_argument(
        "--localization-replay",
        required=True,
        type=Path,
        help="miguel_h_gemini_localization_replay.json de F01.",
    )
    parser.add_argument(
        "--document",
        type=Path,
        default=None,
        help=(
            "PDF/imagen fuente para F01.5. Si se omite, F01.5 usa --raster y "
            "PyMuPDF queda NOT_APPLICABLE."
        ),
    )
    parser.add_argument(
        "--semantic-history",
        type=Path,
        default=Path(
            "Backend/tests/output/miguel_h/gemini_semantic/"
            "gemini_semantic_history.jsonl"
        ),
        help="JSONL append-only donde F01.5 registrará las llamadas Gemini.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Backend/tests/output/miguel_h/phase_02_validation.json"),
        help="Archivo JSON de auditoría generado por esta prueba.",
    )
    parser.add_argument(
        "--overlay-dir",
        type=Path,
        default=Path("Backend/tests/output/miguel_h/phase_02_overlays"),
        help="Directorio de overlays visuales por LevelView.",
    )

    args = parser.parse_args()

    if not args.raster.is_file():
        print(f"FAIL: raster inexistente: {args.raster}")
        return 2
    if not args.localization_replay.is_file():
        print(f"FAIL: replay inexistente: {args.localization_replay}")
        return 2
    if args.document is not None and not args.document.is_file():
        print(f"FAIL: documento inexistente: {args.document}")
        return 2

    payload = load_localization_replay(args.localization_replay)
    expected_levels = expected_levels_from_payload(payload)
    expected_names = [str(item["nombre"]) for item in expected_levels]

    raster_bytes = args.raster.read_bytes()
    with Image.open(BytesIO(raster_bytes)) as source:
        source.load()
        page_width_px, page_height_px = source.size

    print("=" * 76)
    print(" QUANTIA V2 — VALIDACION FUNCIONAL FASE 02 — MIGUEL H")
    print("=" * 76)
    print(f"Raster F01: {args.raster}")
    print(f"Raster origen: {page_width_px} x {page_height_px}")
    print(f"Niveles esperados: {len(expected_levels)}")
    print("Nombres: " + ", ".join(expected_names))

    # ------------------------------------------------------------------
    # F01 — localización/aislamiento de niveles
    # ------------------------------------------------------------------
    level_service = LevelIdentificationService()
    phase_01 = level_service.identify_page(
        source_raster_bytes=raster_bytes,
        source_page_number=EXPECTED_PAGE_NUMBER,
        source_document_id=EXPECTED_SOURCE_DOCUMENT_ID,
        known_level_names=expected_names,
        pdf_level_markers=[],
        gemini_payload=payload,
        single_level_isolated=False,
    )

    if phase_01.level_count != len(expected_levels):
        print(
            "FAIL F01: "
            f"LevelViews={phase_01.level_count}; esperados={len(expected_levels)}."
        )
        return 1
    if phase_01.unresolved_count != 0:
        print(f"FAIL F01: niveles sin resolver={phase_01.unresolved_count}.")
        return 1

    actual_names = [item.level_name for item in phase_01.level_views]
    if actual_names != expected_names:
        print(f"FAIL F01: nombres/orden={actual_names}; esperados={expected_names}.")
        return 1

    # ------------------------------------------------------------------
    # F01.5 — evidencia multimodal + Gemini semántico
    # ------------------------------------------------------------------
    input_document = args.document if args.document is not None else args.raster
    document_bytes = input_document.read_bytes()
    media_mime_type = infer_media_mime_type(input_document)

    semantic_history = GeminiSemanticHistory(history_path=args.semantic_history)
    gemini_adapter = GeminiEvidenceAdapter(semantic_history=semantic_history)
    evidence_pipeline = EvidencePipeline(gemini_adapter=gemini_adapter)
    perimeter_pipeline = PerimeterWallPipeline()

    reports: list[dict[str, Any]] = []

    for level_view in phase_01.level_views:
        print("\n" + "-" * 76)
        print(level_view.level_name)
        print("-" * 76)

        phase_015 = evidence_pipeline.run(
            document_bytes=document_bytes,
            media_mime_type=media_mime_type,
            level_view=level_view,
        )

        gemini_diag = phase_015.diagnostics.source_diagnostics.get("GEMINI")
        if gemini_diag is None or gemini_diag.status != "SUCCEEDED":
            print("  F01.5 Gemini: FAIL")
            if gemini_diag is not None and gemini_diag.error:
                print(f"    {gemini_diag.error}")
            history_check = {
                "history_observation_count": 0,
                "raw_evidence_count": 0,
                "same_count": False,
                "error": "Gemini no produjo una llamada SUCCEEDED.",
            }
        else:
            call_id = phase_015.diagnostics.gemini_call_id
            if not call_id:
                raise RuntimeError("F01.5 reportó Gemini SUCCEEDED sin gemini_call_id.")

            history_event = load_success_history_event(
                history_path=args.semantic_history,
                call_id=call_id,
            )
            history_check = compare_history_to_raw_evidence(
                history_event=history_event,
                evidence=phase_015.evidence,
                call_id=call_id,
            )

        # --------------------------------------------------------------
        # F02 — perímetro + wall_runs + grounding
        # --------------------------------------------------------------
        phase_02 = perimeter_pipeline.run(
            level_view=level_view,
            evidence=phase_015.evidence,
        )

        semantic_comparison = compare_semantics(
            evidence=phase_015.evidence,
            phase_02_result=phase_02,
        )

        report = level_report(
            level_view=level_view,
            phase_015_result=phase_015,
            phase_02_result=phase_02,
            history_check=history_check,
            semantic_comparison=semantic_comparison,
        )
        report["result"] = classify_level_result(report)
        reports.append(report)

        overlay_path = args.overlay_dir / f"{level_view.id}__phase_02.png"
        write_overlay(
            level_view=level_view,
            phase_02_result=phase_02,
            output_path=overlay_path,
        )

        print(f"  F01.5 evidencia: {phase_015.diagnostics.total_count}")
        print(f"  Gemini observations: {phase_015.diagnostics.gemini_count}")
        print(
            "  Gemini history -> RawEvidence: "
            f"{history_check.get('history_observation_count', 0)} -> "
            f"{history_check.get('raw_evidence_count', 0)} "
            f"({'OK' if history_check.get('same_count') else 'FAIL'})"
        )
        print(f"  F02 candidatos: {phase_02.diagnostics.candidate_count}")
        print(f"  F02 resolution: {phase_02.resolution.state}")
        print(f"  F02 validation: {phase_02.state}")

        if phase_02.wall_layer is not None:
            print(f"  Muros perimetrales: {len(phase_02.wall_layer.wall_runs)}")
            print(f"  Total px: {phase_02.wall_layer.total_length_px:.3f}")
            print(
                "  Total m: "
                + (
                    f"{phase_02.wall_layer.total_length_m:.3f}"
                    if phase_02.wall_layer.total_length_m is not None
                    else "UNRESOLVED"
                )
            )
            print(f"  Metric status: {phase_02.wall_layer.metric_status}")

        if phase_02.grounding is not None:
            print(f"  Grounding: {phase_02.grounding.status}")
            print(f"  Scale consistency: {phase_02.grounding.scale_consistency}")
            if phase_02.grounding.metric_scale is not None:
                print(
                    "  Escala validada: "
                    f"{phase_02.grounding.metric_scale.meters_per_px:.12f} m/px"
                )

        print(f"  Gemini cross-check: {semantic_comparison['state']}")
        for status, count in semantic_comparison["status_counts"].items():
            print(f"    {status}: {count}")
        print(f"  RESULTADO NIVEL: {report['result']}")

    # ------------------------------------------------------------------
    # Resultado global
    # ------------------------------------------------------------------
    level_results = [item["result"] for item in reports]
    if any(item == "FAIL" for item in level_results):
        overall = "FAIL"
        exit_code = 1
    elif reports and all(item == "PASS" for item in level_results):
        overall = "PASS"
        exit_code = 0
    else:
        overall = "REVIEW"
        exit_code = 0

    output = {
        "case": "MIGUEL_H",
        "source_document_id": EXPECTED_SOURCE_DOCUMENT_ID,
        "page_number": EXPECTED_PAGE_NUMBER,
        "raster": str(args.raster),
        "document": str(args.document) if args.document is not None else None,
        "media_mime_type": media_mime_type,
        "semantic_history": str(args.semantic_history),
        "overall_result": overall,
        "levels": reports,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 76)
    print(f"RESULTADO GLOBAL FASE 02: {overall}")
    print(f"Reporte: {args.output}")
    print(f"Semantic history: {args.semantic_history}")
    print(f"Overlays: {args.overlay_dir}")
    print("=" * 76)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
