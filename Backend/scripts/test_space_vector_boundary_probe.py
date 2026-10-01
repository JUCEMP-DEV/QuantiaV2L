import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from app.services.plan_document_analyzer import (
    PlanDocumentAnalyzer,
)
from app.services.space_pdf_coordinate_mapper import (
    SpacePDFCoordinateMapper,
)
from app.services.space_vector_boundary_probe import (
    SpaceVectorBoundaryProbeService,
)


def format_candidate(
    candidate,
) -> str:
    return (
        f"idx={candidate.index} | "
        f"({candidate.x1:.2f},{candidate.y1:.2f}) "
        f"→ "
        f"({candidate.x2:.2f},{candidate.y2:.2f}) | "
        f"len={candidate.length:.2f} | "
        f"dist={candidate.distance_to_seed:.2f}"
    )


def print_direction(
    label: str,
    candidates,
) -> None:
    print(
        f"  {label}: "
        f"{len(candidates)} candidatos"
    )

    if not candidates:
        print(
            "     más cercano: ninguno"
        )
        return

    print(
        "     más cercano:",
        format_candidate(
            candidates[0]
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnóstico de segmentos vectoriales "
            "alrededor de espacios Quantia."
        )
    )

    parser.add_argument(
        "pdf",
        help="Ruta al PDF vectorial original.",
    )

    parser.add_argument(
        "image",
        help="Ruta a la imagen renderizada del PDF.",
    )

    parser.add_argument(
        "localization_json",
        help=(
            "Ruta al JSON de localización "
            "espacial generado por Gemini."
        ),
    )

    args = parser.parse_args()

    pdf_path = Path(
        args.pdf
    ).expanduser().resolve()

    image_path = Path(
        args.image
    ).expanduser().resolve()

    localization_path = Path(
        args.localization_json
    ).expanduser().resolve()

    # =========================================================
    # VALIDACIÓN
    # =========================================================

    for path, label in (
        (
            pdf_path,
            "PDF",
        ),
        (
            image_path,
            "imagen",
        ),
        (
            localization_path,
            "JSON de localización",
        ),
    ):
        if not path.exists():
            print(
                f"ERROR: no existe {label}:"
            )
            print(
                path
            )
            return 1

    # =========================================================
    # CARGA LOCALIZACIÓN
    # =========================================================

    try:
        localization_payload = json.loads(
            localization_path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        print(
            "ERROR: JSON de localización inválido:"
        )
        print(
            exc
        )
        return 2

    except OSError as exc:
        print(
            "ERROR leyendo localización:"
        )
        print(
            exc
        )
        return 2

    # =========================================================
    # PDF
    # =========================================================

    try:
        analysis = (
            PlanDocumentAnalyzer()
            .analyze(
                document_bytes=
                    pdf_path.read_bytes(),

                mime_type=
                    "application/pdf",
            )
        )

    except Exception as exc:
        print(
            "ERROR analizando PDF:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 3

    if (
        analysis.document_type
        != "pdf_vector_or_hybrid"
    ):
        print(
            "ERROR: el PDF no contiene "
            "geometría vectorial utilizable."
        )
        return 4

    # =========================================================
    # IMAGEN
    # =========================================================

    try:
        with Image.open(
            image_path
        ) as image:
            image_width, image_height = (
                image.size
            )

    except Exception as exc:
        print(
            "ERROR abriendo imagen:"
        )
        print(
            exc
        )
        return 5

    # =========================================================
    # MAPEO GEMINI → PDF
    # =========================================================

    try:
        mapping = (
            SpacePDFCoordinateMapper()
            .map(
                analysis=analysis,

                localization_payload=
                    localization_payload,

                image_width_px=
                    image_width,

                image_height_px=
                    image_height,
            )
        )

    except Exception as exc:
        print(
            "ERROR mapeando coordenadas:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 6

    # =========================================================
    # PROBE VECTORIAL
    # =========================================================

    try:
        result = (
            SpaceVectorBoundaryProbeService()
            .probe(
                analysis=analysis,
                mapping=mapping,
            )
        )

    except Exception as exc:
        print(
            "ERROR durante probe vectorial:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 7

    # =========================================================
    # REPORTE
    # =========================================================

    page = analysis.pages[
        result.page - 1
    ]

    print()
    print(
        "========================================"
    )
    print(
        "QUANTIA V2 — VECTOR BOUNDARY PROBE"
    )
    print(
        "========================================"
    )

    print(
        f"Página                    : "
        f"{result.page}"
    )

    print(
        f"Trazos vectoriales página : "
        f"{len(page.lines)}"
    )

    print(
        f"Espacios analizados       : "
        f"{len(result.spaces)}"
    )

    print()

    # =========================================================
    # ESPACIOS
    # =========================================================

    for space in result.spaces:
        print(
            "----------------------------------------"
        )

        print(
            f"{space.nivel} | "
            f"{space.id_propuesto}"
        )

        print(
            f"Nombre : {space.nombre}"
        )

        print(
            f"Seed   : "
            f"({space.seed_x:.2f}, "
            f"{space.seed_y:.2f})"
        )

        bbox = space.localization_bbox

        print(
            "BBox   : "
            f"({bbox.x_min:.2f}, "
            f"{bbox.y_min:.2f}) "
            f"→ "
            f"({bbox.x_max:.2f}, "
            f"{bbox.y_max:.2f})"
        )

        print(
            f"Segmentos dentro bbox : "
            f"{space.segments_intersecting_bbox}"
        )

        print(
            f"  horizontales        : "
            f"{space.horizontal_segments_in_bbox}"
        )

        print(
            f"  verticales          : "
            f"{space.vertical_segments_in_bbox}"
        )

        print(
            f"  otros               : "
            f"{space.other_segments_in_bbox}"
        )

        print()

        print(
            "CANDIDATOS DIRECCIONALES:"
        )

        print_direction(
            "IZQUIERDA",
            space.boundaries.left,
        )

        print_direction(
            "DERECHA",
            space.boundaries.right,
        )

        print_direction(
            "SUPERIOR",
            space.boundaries.top,
        )

        print_direction(
            "INFERIOR",
            space.boundaries.bottom,
        )

        print()

    # =========================================================
    # RESUMEN
    # =========================================================

    without_left = sum(
        1
        for space in result.spaces
        if not space.boundaries.left
    )

    without_right = sum(
        1
        for space in result.spaces
        if not space.boundaries.right
    )

    without_top = sum(
        1
        for space in result.spaces
        if not space.boundaries.top
    )

    without_bottom = sum(
        1
        for space in result.spaces
        if not space.boundaries.bottom
    )

    print(
        "========================================"
    )
    print(
        "RESUMEN"
    )
    print(
        "========================================"
    )

    print(
        f"Sin candidato izquierda : "
        f"{without_left}"
    )

    print(
        f"Sin candidato derecha   : "
        f"{without_right}"
    )

    print(
        f"Sin candidato superior  : "
        f"{without_top}"
    )

    print(
        f"Sin candidato inferior  : "
        f"{without_bottom}"
    )

    print()

    print(
        "NOTAS:"
    )

    for note in result.notes:
        print(
            f" - {note}"
        )

    print()

    print(
        "CONTROL OK — ningún segmento "
        "fue promovido a muro."
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )