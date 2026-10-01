from __future__ import annotations

import argparse
import json
import math
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from app.quantia_spatial.models.level_view import PixelPoint
from app.quantia_spatial.phase_01_level.level_identification_service import (
    LevelIdentificationService,
)
from PIL import Image

EXPECTED_PAGE_NUMBER = 1
EXPECTED_SOURCE_DOCUMENT_ID = "MIGUEL_H_PHASE_01"


def load_replay_payload(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("El replay debe contener un objeto JSON.")

    result = data.get("result")

    if not isinstance(result, dict):
        raise ValueError("El replay no contiene result.")

    payload = result.get("data")

    if not isinstance(payload, dict):
        raise ValueError("El replay no contiene result.data.")

    if payload.get("pagina") != EXPECTED_PAGE_NUMBER:
        raise ValueError("El replay no corresponde a la página canónica esperada.")

    niveles = payload.get("niveles")

    if not isinstance(niveles, list) or not niveles:
        raise ValueError("El replay no contiene niveles localizados.")

    return payload


def expected_bbox_px(
    *,
    normalized: dict[str, Any],
    page_width_px: int,
    page_height_px: int,
) -> tuple[int, int, int, int]:
    x_min = max(
        0,
        min(
            page_width_px - 1,
            math.floor(float(normalized["x_min"]) * page_width_px),
        ),
    )
    y_min = max(
        0,
        min(
            page_height_px - 1,
            math.floor(float(normalized["y_min"]) * page_height_px),
        ),
    )
    x_max = max(
        1,
        min(
            page_width_px,
            math.ceil(float(normalized["x_max"]) * page_width_px),
        ),
    )
    y_max = max(
        1,
        min(
            page_height_px,
            math.ceil(float(normalized["y_max"]) * page_height_px),
        ),
    )

    return x_min, y_min, x_max, y_max


def check(
    condition: bool,
    message: str,
    failures: list[str],
) -> None:
    if not condition:
        failures.append(message)


def validate_level_view(
    *,
    level_view,
    expected_level: dict[str, Any],
    page_width_px: int,
    page_height_px: int,
    failures: list[str],
) -> None:
    name = str(expected_level["nombre"])
    normalized_bbox = expected_level.get("bbox_normalizado")

    if not isinstance(normalized_bbox, dict):
        failures.append(f"{name}: replay sin bbox_normalizado.")
        return

    expected_bbox = expected_bbox_px(
        normalized=normalized_bbox,
        page_width_px=page_width_px,
        page_height_px=page_height_px,
    )

    actual_bbox = (
        level_view.source_bbox_px.x_min,
        level_view.source_bbox_px.y_min,
        level_view.source_bbox_px.x_max,
        level_view.source_bbox_px.y_max,
    )

    expected_width = expected_bbox[2] - expected_bbox[0]
    expected_height = expected_bbox[3] - expected_bbox[1]

    check(
        level_view.level_name == name,
        f"{name}: nombre obtenido={level_view.level_name!r}.",
        failures,
    )
    check(
        level_view.source_page_number == EXPECTED_PAGE_NUMBER,
        f"{name}: página origen incorrecta.",
        failures,
    )
    check(
        actual_bbox == expected_bbox,
        f"{name}: bbox obtenido={actual_bbox}, esperado={expected_bbox}.",
        failures,
    )
    check(
        level_view.raster_width_px == expected_width,
        f"{name}: ancho LevelView incorrecto.",
        failures,
    )
    check(
        level_view.raster_height_px == expected_height,
        f"{name}: alto LevelView incorrecto.",
        failures,
    )
    check(
        bool(level_view.raster_bytes),
        f"{name}: raster_bytes vacío.",
        failures,
    )
    check(
        level_view.raster_mime_type == "image/png",
        f"{name}: raster_mime_type={level_view.raster_mime_type!r}.",
        failures,
    )
    check(
        level_view.state == "DETECTADO",
        f"{name}: state={level_view.state!r}; se esperaba DETECTADO.",
        failures,
    )
    check(
        level_view.confirmed is False,
        f"{name}: confirmed debe permanecer False.",
        failures,
    )
    check(
        level_view.source_document_id == EXPECTED_SOURCE_DOCUMENT_ID,
        f"{name}: source_document_id no fue preservado.",
        failures,
    )

    expected_confidence = expected_level.get("confianza")

    check(
        level_view.confidence == expected_confidence,
        (
            f"{name}: confidence={level_view.confidence!r}, "
            f"esperada={expected_confidence!r}."
        ),
        failures,
    )

    transform = level_view.transform

    check(
        transform.offset_x_px == expected_bbox[0],
        f"{name}: offset_x_px incorrecto.",
        failures,
    )
    check(
        transform.offset_y_px == expected_bbox[1],
        f"{name}: offset_y_px incorrecto.",
        failures,
    )
    check(
        transform.source_page_width_px == page_width_px,
        f"{name}: source_page_width_px incorrecto.",
        failures,
    )
    check(
        transform.source_page_height_px == page_height_px,
        f"{name}: source_page_height_px incorrecto.",
        failures,
    )
    check(
        transform.local_width_px == expected_width,
        f"{name}: local_width_px incorrecto.",
        failures,
    )
    check(
        transform.local_height_px == expected_height,
        f"{name}: local_height_px incorrecto.",
        failures,
    )

    local_origin = PixelPoint(x=0, y=0)
    page_origin = transform.local_to_page(local_origin)

    check(
        (page_origin.x, page_origin.y) == (expected_bbox[0], expected_bbox[1]),
        f"{name}: local_to_page(0,0) incorrecto.",
        failures,
    )

    roundtrip = transform.page_to_local(page_origin)

    check(
        (roundtrip.x, roundtrip.y) == (0, 0),
        f"{name}: transformación local↔página no es reversible.",
        failures,
    )

    try:
        with Image.open(BytesIO(level_view.raster_bytes)) as image:
            image.load()
            encoded_size = image.size
    except Exception as exc:
        failures.append(f"{name}: raster generado no puede abrirse: {exc}")
        encoded_size = None

    check(
        encoded_size == (expected_width, expected_height),
        (
            f"{name}: tamaño PNG real={encoded_size}, "
            f"esperado={(expected_width, expected_height)}."
        ),
        failures,
    )

    print(f"\n{name}")
    print(f"  id: {level_view.id}")
    print(f"  pagina: {level_view.source_page_number}")
    print(f"  bbox_px: {actual_bbox}")
    print(f"  raster: {level_view.raster_width_px} x {level_view.raster_height_px}")
    print(f"  offset: ({transform.offset_x_px}, {transform.offset_y_px})")
    print(f"  state: {level_view.state}")
    print(f"  confidence: {level_view.confidence}")
    print(f"  confirmed: {level_view.confirmed}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validación funcional de Fase 01 usando "
            "Miguel H + replay de localización Gemini."
        )
    )
    parser.add_argument(
        "--raster",
        required=True,
        type=Path,
        help="Raster canónico Miguel H (PNG/JPG).",
    )
    parser.add_argument(
        "--replay",
        required=True,
        type=Path,
        help="miguel_h_gemini_localization_replay.json",
    )

    args = parser.parse_args()

    if not args.raster.is_file():
        print(f"FAIL: raster inexistente: {args.raster}")
        return 2

    if not args.replay.is_file():
        print(f"FAIL: replay inexistente: {args.replay}")
        return 2

    payload = load_replay_payload(args.replay)
    raster_bytes = args.raster.read_bytes()

    with Image.open(BytesIO(raster_bytes)) as image:
        image.load()
        page_width_px, page_height_px = image.size

    expected_levels = [
        level
        for level in payload["niveles"]
        if (
            isinstance(level, dict)
            and level.get("localizado") is True
            and isinstance(level.get("bbox_normalizado"), dict)
        )
    ]

    expected_names = [str(level["nombre"]) for level in expected_levels]

    print("=" * 68)
    print(" QUANTIA V2 — VALIDACION FUNCIONAL FASE 01 — MIGUEL H")
    print("=" * 68)
    print(f"Raster origen: {page_width_px} x {page_height_px}")
    print(f"Niveles esperados por replay: {len(expected_levels)}")
    print("Nombres esperados: " + ", ".join(expected_names))

    service = LevelIdentificationService()

    result = service.identify_page(
        source_raster_bytes=raster_bytes,
        source_page_number=EXPECTED_PAGE_NUMBER,
        source_document_id=EXPECTED_SOURCE_DOCUMENT_ID,
        known_level_names=expected_names,
        pdf_level_markers=[],
        gemini_payload=payload,
        single_level_isolated=False,
    )

    failures: list[str] = []

    check(
        result.source_page_width_px == page_width_px,
        "El ancho reportado por Fase 01 no coincide con el raster.",
        failures,
    )
    check(
        result.source_page_height_px == page_height_px,
        "El alto reportado por Fase 01 no coincide con el raster.",
        failures,
    )
    check(
        result.level_count == len(expected_levels),
        (
            f"LevelViews obtenidos={result.level_count}; "
            f"esperados={len(expected_levels)}."
        ),
        failures,
    )
    check(
        result.unresolved_count == 0,
        f"Fase 01 dejó {result.unresolved_count} nivel(es) sin resolver.",
        failures,
    )

    actual_names = [item.level_name for item in result.level_views]

    check(
        actual_names == expected_names,
        (f"Orden/nombres obtenidos={actual_names}; esperados={expected_names}."),
        failures,
    )

    ids = [item.id for item in result.level_views]

    check(
        len(ids) == len(set(ids)),
        "Fase 01 produjo LevelView.id duplicados.",
        failures,
    )

    by_name = {item.level_name: item for item in result.level_views}

    for expected_level in expected_levels:
        name = str(expected_level["nombre"])
        level_view = by_name.get(name)

        if level_view is None:
            failures.append(f"No se produjo LevelView para {name}.")
            continue

        validate_level_view(
            level_view=level_view,
            expected_level=expected_level,
            page_width_px=page_width_px,
            page_height_px=page_height_px,
            failures=failures,
        )

    print("\n" + "-" * 68)
    print(f"Warnings: {len(result.warnings)}")
    for warning in result.warnings:
        print(f"  - {warning}")

    print("-" * 68)

    if failures:
        print("RESULTADO FASE 01: FAIL")
        for failure in failures:
            print(f"  [FAIL] {failure}")
        return 1

    print("RESULTADO FASE 01: PASS")
    print(
        "La fase identifico, aislo y transformo correctamente "
        "los niveles del caso canonico."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
