import argparse
import json
import sys
from pathlib import Path

from app.services.pdf_plan_evidence_extractor import (
    PDFPlanEvidenceExtractor,
)
from app.services.pdf_quantia_grounding_service import (
    PDFQuantiaGroundingService,
)
from app.services.plan_document_analyzer import (
    PlanDocumentAnalyzer,
)
from app.services.quantia_extraction_reconciler import (
    reconcile_gemini_transport,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba de grounding documental "
            "PyMuPDF + Gemini + Quantia."
        )
    )

    parser.add_argument(
        "pdf",
        help="Ruta al PDF vectorial original.",
    )

    parser.add_argument(
        "transport_json",
        help="Ruta al JSON Gemini transport.",
    )

    args = parser.parse_args()

    pdf_path = Path(
        args.pdf
    ).expanduser().resolve()

    transport_path = Path(
        args.transport_json
    ).expanduser().resolve()

    # =========================================================
    # VALIDACIÓN DE ARCHIVOS
    # =========================================================

    if not pdf_path.exists():
        print(
            "ERROR: no existe el PDF:"
        )
        print(
            pdf_path
        )
        return 1

    if not transport_path.exists():
        print(
            "ERROR: no existe el JSON:"
        )
        print(
            transport_path
        )
        return 1

    # =========================================================
    # CARGA GEMINI TRANSPORT
    # =========================================================

    try:
        transport_payload = json.loads(
            transport_path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        print(
            "ERROR: JSON Gemini inválido:"
        )
        print(
            exc
        )
        return 2

    except OSError as exc:
        print(
            "ERROR leyendo JSON Gemini:"
        )
        print(
            exc
        )
        return 2

    # =========================================================
    # RECONCILIACIÓN GEMINI -> QUANTIA
    # =========================================================

    try:
        reconciliation = (
            reconcile_gemini_transport(
                transport_payload
            )
        )

    except Exception as exc:
        print(
            "ERROR EN RECONCILIACIÓN:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 3

    # =========================================================
    # ANÁLISIS PDF
    # =========================================================

    try:
        pdf_bytes = (
            pdf_path.read_bytes()
        )

        analysis = (
            PlanDocumentAnalyzer()
            .analyze(
                document_bytes=pdf_bytes,
                mime_type="application/pdf",
            )
        )

    except Exception as exc:
        print(
            "ERROR ANALIZANDO PDF:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 4

    if (
        analysis.document_type
        != "pdf_vector_or_hybrid"
    ):
        print(
            "ERROR: el PDF no contiene "
            "evidencia vectorial utilizable."
        )
        print(
            f"Tipo detectado: "
            f"{analysis.document_type}"
        )
        return 5

    # =========================================================
    # EVIDENCIA VECTORIAL
    # =========================================================

    try:
        evidence = (
            PDFPlanEvidenceExtractor()
            .extract(
                analysis
            )
        )

    except Exception as exc:
        print(
            "ERROR EXTRAYENDO EVIDENCIA:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 6

    # =========================================================
    # GROUNDING
    # =========================================================

    try:
        grounding = (
            PDFQuantiaGroundingService()
            .ground(
                reconciliation=
                    reconciliation,

                pdf_evidence=
                    evidence,
            )
        )

    except Exception as exc:
        print(
            "ERROR EN GROUNDING:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 7

    # =========================================================
    # MÉTRICAS
    # =========================================================

    metrics_total = len(
        grounding.metric_candidates
    )

    metrics_with_pdf_value = [
        item
        for item
        in grounding.metric_candidates
        if item.value_present_in_pdf
    ]

    metrics_without_pdf_value = [
        item
        for item
        in grounding.metric_candidates
        if not item.value_present_in_pdf
    ]

    associations_validated = [
        item
        for item
        in grounding.metric_candidates
        if item.association_validated
    ]

    # =========================================================
    # DOCUMENTO
    # =========================================================

    grounded_document_fields = [
        item
        for item
        in grounding.document_fields
        if item.matched
    ]

    grounded_levels = [
        item
        for item
        in grounding.levels
        if item.matched
    ]

    # =========================================================
    # SALIDAS
    # =========================================================

    grounded_path = (
        transport_path.with_name(
            f"{transport_path.stem}"
            ".grounded.quantia.json"
        )
    )

    audit_path = (
        transport_path.with_name(
            f"{transport_path.stem}"
            ".grounding-audit.json"
        )
    )

    try:
        grounded_path.write_text(
            grounding.extraction.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        audit_path.write_text(
            json.dumps(
                grounding.audit_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        print(
            "ERROR GUARDANDO RESULTADOS:"
        )
        print(
            exc
        )
        return 8

    # =========================================================
    # REPORTE
    # =========================================================

    print()
    print(
        "========================================"
    )
    print(
        "QUANTIA V2 — PDF GROUNDING"
    )
    print(
        "========================================"
    )

    print(
        f"PDF type                   : "
        f"{analysis.document_type}"
    )

    print(
        f"Páginas                    : "
        f"{analysis.page_count}"
    )

    print(
        f"Spans vectoriales          : "
        f"{sum(len(p.text_spans) for p in analysis.pages)}"
    )

    print(
        f"Trazos vectoriales         : "
        f"{sum(len(p.lines) for p in analysis.pages)}"
    )

    print(
        f"Cotas PDF candidatas       : "
        f"{len(evidence.dimension_candidates)}"
    )

    print(
        f"Métricas Gemini            : "
        f"{metrics_total}"
    )

    print(
        f"Métricas con valor en PDF  : "
        f"{len(metrics_with_pdf_value)}"
    )

    print(
        f"Métricas sin valor en PDF  : "
        f"{len(metrics_without_pdf_value)}"
    )

    print(
        f"Asociaciones validadas     : "
        f"{len(associations_validated)}"
    )

    print(
        f"Campos documento grounded  : "
        f"{len(grounded_document_fields)}"
    )

    print(
        f"Niveles grounded           : "
        f"{len(grounded_levels)}"
    )

    print(
        f"Escaleras                  : "
        f"{len(grounding.stairs)}"
    )

    print(
        f"Evidencias estructurales   : "
        f"{len(grounding.structural_evidence)}"
    )

    print(
        f"Cotas PDF no usadas        : "
        f"{len(grounding.unmatched_pdf_dimensions)}"
    )

    print()

    # =========================================================
    # CAMPOS DOCUMENTALES
    # =========================================================

    print(
        "DOCUMENTO:"
    )

    for item in grounding.document_fields:
        print(
            f" - {item.field}: "
            f"{item.value!r} "
            f"=> {'MATCH' if item.matched else 'NO MATCH'}"
        )

    print()

    print(
        "NIVELES:"
    )

    for item in grounding.levels:
        print(
            f" - {item.value!r} "
            f"=> {'MATCH' if item.matched else 'NO MATCH'}"
        )

    print()

    # =========================================================
    # MÉTRICAS CON RESPALDO
    # =========================================================

    print(
        "MÉTRICAS CON VALOR PRESENTE EN PDF:"
    )

    for item in metrics_with_pdf_value:
        print(
            f" - {item.level or '-'} | "
            f"{item.element_id} | "
            f"{item.field}={item.value:g} | "
            f"matches={len(item.pdf_matches)} | "
            f"association="
            f"{item.association_validated}"
        )

    print()

    if metrics_without_pdf_value:
        print(
            "MÉTRICAS SIN RESPALDO NUMÉRICO PDF:"
        )

        for item in metrics_without_pdf_value:
            print(
                f" - {item.level or '-'} | "
                f"{item.element_id} | "
                f"{item.field}={item.value:g}"
            )

        print()

    # =========================================================
    # ESCALERAS
    # =========================================================

    print(
        "ESCALERAS:"
    )

    for stair in grounding.stairs:
        print(
            f" - {stair.nivel} | "
            f"{stair.sentido} | "
            f"source={stair.source}"
        )

    print()

    # =========================================================
    # NOTAS
    # =========================================================

    print(
        "NOTAS:"
    )

    for note in grounding.notes:
        print(
            f" - {note}"
        )

    print()

    print(
        "JSON grounded:"
    )
    print(
        grounded_path
    )

    print()

    print(
        "Auditoría grounding:"
    )
    print(
        audit_path
    )

    print()

    # =========================================================
    # CONTROL CRÍTICO
    # =========================================================

    if associations_validated:
        print(
            "ERROR: se validaron asociaciones "
            "geométricas antes de la etapa correspondiente."
        )
        return 9

    print(
        "CONTROL OK — ninguna asociación "
        "geométrica fue promovida."
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
    