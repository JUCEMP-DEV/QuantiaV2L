import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from app.services.quantia_extraction_reconciler import (
    reconcile_gemini_transport,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba del reconciliador determinístico "
            "Gemini -> Quantia."
        )
    )

    parser.add_argument(
        "input",
        help="Ruta del JSON generado por Gemini.",
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    ).expanduser().resolve()

    if not input_path.exists():
        print(
            f"ERROR: no existe el archivo:\n"
            f"{input_path}"
        )
        return 1

    if not input_path.is_file():
        print(
            f"ERROR: la ruta no es un archivo:\n"
            f"{input_path}"
        )
        return 1

    try:
        payload = json.loads(
            input_path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        print(
            "ERROR leyendo archivo:"
        )
        print(exc)
        return 2

    except json.JSONDecodeError as exc:
        print(
            "ERROR: el archivo no contiene JSON válido:"
        )
        print(exc)
        return 3

    try:
        result = reconcile_gemini_transport(
            payload
        )

    except Exception as exc:
        print(
            "ERROR DURANTE RECONCILIACIÓN:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 4

    extraction = result.extraction

    # =========================================================
    # CONTEOS
    # =========================================================

    total_spaces = sum(
        len(level.espacios)
        for level in extraction.niveles
    )

    total_dimensions = sum(
        len(level.cotas)
        for level in extraction.niveles
    )

    total_stairs = len(
        extraction.elementos_especiales.escaleras
    )

    total_doors = sum(
        len(space.puertas)
        for level in extraction.niveles
        for space in level.espacios
    )

    total_windows = sum(
        len(space.ventanas)
        for level in extraction.niveles
        for space in level.espacios
    )

    # =========================================================
    # VERIFICACIÓN DE MÉTRICAS
    # =========================================================

    promoted_space_metrics = []

    for level in extraction.niveles:
        for space in level.espacios:
            if (
                space.ancho_m is not None
                or space.largo_m is not None
                or space.area_m2 is not None
            ):
                promoted_space_metrics.append(
                    space.id_propuesto
                )

    # =========================================================
    # ARCHIVOS DE SALIDA
    # =========================================================

    canonical_path = input_path.with_name(
        f"{input_path.stem}"
        ".quantia-canonical.json"
    )

    audit_path = input_path.with_name(
        f"{input_path.stem}"
        ".quantia-audit.json"
    )

    canonical_payload = (
        extraction.model_dump(
            mode="json"
        )
    )

    audit_payload = {
        "metric_candidates": [
            asdict(item)
            for item
            in result.metric_candidates
        ],
        "discarded_model_confirmations":
            result.discarded_model_confirmations,
        "discarded_unidentified":
            result.discarded_unidentified,
        "unmapped_constructive_items":
            result.unmapped_constructive_items,
    }

    try:
        canonical_path.write_text(
            json.dumps(
                canonical_payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        audit_path.write_text(
            json.dumps(
                audit_payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        print(
            "ERROR guardando resultados:"
        )
        print(exc)
        return 5

    # =========================================================
    # RESULTADO
    # =========================================================

    print()
    print(
        "========================================"
    )
    print(
        "QUANTIA V2 — RECONCILIACIÓN"
    )
    print(
        "========================================"
    )

    print(
        f"Niveles                    : "
        f"{len(extraction.niveles)}"
    )

    print(
        f"Espacios                   : "
        f"{total_spaces}"
    )

    print(
        f"Escaleras                  : "
        f"{total_stairs}"
    )

    print(
        f"Puertas                    : "
        f"{total_doors}"
    )

    print(
        f"Ventanas                   : "
        f"{total_windows}"
    )

    print(
        f"Cotas observadas           : "
        f"{total_dimensions}"
    )

    print(
        f"Métricas candidatas        : "
        f"{len(result.metric_candidates)}"
    )

    print(
        f"Métricas promovidas        : "
        f"{len(promoted_space_metrics)}"
    )

    print(
        f"Conflictos                 : "
        f"{len(extraction.conflictos)}"
    )

    print(
        f"Confirmaciones Quantia     : "
        f"{len(extraction.confirmaciones_requeridas)}"
    )

    print(
        f"Confirmaciones descartadas : "
        f"{len(result.discarded_model_confirmations)}"
    )

    print(
        f"Datos no identificados     : "
        f"{len(extraction.datos_no_identificados)}"
    )

    print(
        f"No identificados descartados: "
        f"{len(result.discarded_unidentified)}"
    )

    print(
        f"Constructivos no mapeados  : "
        f"{len(result.unmapped_constructive_items)}"
    )

    print()

    # =========================================================
    # CONTROLES CRÍTICOS
    # =========================================================

    print(
        "CONTROLES:"
    )

    if promoted_space_metrics:
        print(
            "ERROR: se promovieron métricas "
            "de espacios sin validación:"
        )

        for space_id in promoted_space_metrics:
            print(
                f"  - {space_id}"
            )

        return 6

    print(
        "OK — ninguna métrica de espacio "
        "fue promovida."
    )

    if (
        extraction.confirmaciones_requeridas
        and not extraction.conflictos
    ):
        print(
            "ERROR: existen confirmaciones Quantia "
            "sin conflictos documentales."
        )
        return 7

    print(
        "OK — Gemini no controla las "
        "confirmaciones finales."
    )

    print()

    if result.discarded_model_confirmations:
        print(
            "CONFIRMACIONES GEMINI DESCARTADAS:"
        )

        for item in (
            result.discarded_model_confirmations
        ):
            print(
                " -",
                item.get(
                    "elemento",
                    "Sin elemento",
                ),
            )

        print()

    if result.discarded_unidentified:
        print(
            "DATOS DESCARTADOS:"
        )

        for item in (
            result.discarded_unidentified
        ):
            print(
                f" - {item}"
            )

        print()

    if result.unmapped_constructive_items:
        print(
            "CONSTRUCTIVOS CONSERVADOS "
            "PARA AUDITORÍA:"
        )

        for item in (
            result.unmapped_constructive_items
        ):
            print(
                " -",
                item.get(
                    "campo",
                    "Sin campo",
                ),
                "=>",
                item.get(
                    "valor",
                ),
            )

        print()

    print(
        "JSON canónico:"
    )
    print(
        canonical_path
    )

    print()

    print(
        "Auditoría:"
    )
    print(
        audit_path
    )

    print()

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )