from __future__ import annotations

import importlib
import inspect
import shutil
import sys
from dataclasses import dataclass, field
from typing import Any


# ============================================================
# RESULTADO
# ============================================================


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass
class PreflightResult:
    checks: list[CheckResult] = field(default_factory=list)

    def add(
        self,
        name: str,
        ok: bool,
        detail: str,
    ) -> None:
        self.checks.append(
            CheckResult(
                name=name,
                ok=ok,
                detail=detail,
            )
        )

    @property
    def passed(self) -> int:
        return sum(
            1
            for item in self.checks
            if item.ok
        )

    @property
    def failed(self) -> int:
        return sum(
            1
            for item in self.checks
            if not item.ok
        )


# ============================================================
# MÓDULOS OBLIGATORIOS
# ============================================================


REQUIRED_MODULES = [
    "app.services.plan_document_analyzer",
    "app.services.gemini_vision_provider",
    "app.services.opencv_plan_geometry_service",
    "app.services.ocr_plan_text_service",
    "app.services.pdf_plan_evidence_extractor",
    "app.services.pdf_quantia_grounding_service",
    "app.services.quantia_extraction_reconciler",
    "app.services.space_pdf_coordinate_mapper",
    "app.services.space_raster_coordinate_mapper",
    "app.services.space_vector_boundary_probe",
    "app.services.plan_geometry_reconciler",
    "app.services.architectural_graph_builder",
    "app.services.wall_opening_topology_service",
    "app.services.shapely_plan_geometry_service",
    "app.services.architectural_dimension_grounding_service",
    "app.services.wall_geometry_resolver",
    "app.services.space_geometry_resolver",
    "app.services.quantia_spatial_contract_builder",
    "app.services.quantia_spatial_reconstruction_service",
    "app.schemas.quantia_spatial_contract",
]


# ============================================================
# DEPENDENCIAS EXTERNAS
# ============================================================


EXTERNAL_MODULES = [
    "pymupdf",
    "PIL",
    "numpy",
    "cv2",
    "shapely",
    "pytesseract",
    "pydantic",
    "requests",
]


# ============================================================
# FIRMAS ESPERADAS
# ============================================================


EXPECTED_METHODS: list[
    tuple[
        str,
        str,
        str,
        set[str],
    ]
] = [
    (
        "app.services.plan_document_analyzer",
        "PlanDocumentAnalyzer",
        "analyze",
        {
            "document_bytes",
            "mime_type",
        },
    ),
    (
        "app.services.plan_document_analyzer",
        "PlanDocumentAnalyzer",
        "prepare_raster_pages",
        {
            "document_bytes",
            "mime_type",
            "render_scale",
        },
    ),
    (
        "app.services.gemini_vision_provider",
        "GeminiVisionProvider",
        "analyze",
        {
            "prompt",
            "media_bytes",
            "media_mime_type",
            "response_json_schema",
        },
    ),
    (
        "app.services.opencv_plan_geometry_service",
        "OpenCVPlanGeometryService",
        "analyze",
        {
            "raster",
        },
    ),
    (
        "app.services.ocr_plan_text_service",
        "OCRPlanTextService",
        "analyze",
        {
            "raster",
        },
    ),
    (
        "app.services.pdf_plan_evidence_extractor",
        "PDFPlanEvidenceExtractor",
        "extract",
        {
            "analysis",
        },
    ),
    (
        "app.services.pdf_quantia_grounding_service",
        "PDFQuantiaGroundingService",
        "ground",
        {
            "reconciliation",
            "pdf_evidence",
        },
    ),
    (
        "app.services.space_pdf_coordinate_mapper",
        "SpacePDFCoordinateMapper",
        "map",
        {
            "analysis",
            "localization_payload",
            "image_width_px",
            "image_height_px",
        },
    ),
    (
        "app.services.space_raster_coordinate_mapper",
        "SpaceRasterCoordinateMapper",
        "map",
        {
            "localization_payload",
            "image_width_px",
            "image_height_px",
        },
    ),
    (
        "app.services.space_vector_boundary_probe",
        "SpaceVectorBoundaryProbeService",
        "probe",
        {
            "analysis",
            "mapping",
        },
    ),
    (
        "app.services.plan_geometry_reconciler",
        "PlanGeometryReconciler",
        "reconcile",
        {
            "opencv_geometry",
            "mapping",
            "ocr",
            "pdf_grounding",
            "vector_probe",
            "metric_candidates",
        },
    ),
    (
        "app.services.architectural_graph_builder",
        "ArchitecturalGraphBuilder",
        "build",
        {
            "reconciliation",
            "opencv_geometry",
        },
    ),
    (
        "app.services.wall_opening_topology_service",
        "WallOpeningTopologyService",
        "analyze",
        {
            "graph",
            "reconciliation",
            "opencv_geometry",
        },
    ),
    (
        "app.services.shapely_plan_geometry_service",
        "ShapelyPlanGeometryService",
        "analyze",
        {
            "topology",
            "reconciliation",
        },
    ),
    (
        "app.services.architectural_dimension_grounding_service",
        "ArchitecturalDimensionGroundingService",
        "ground",
        {
            "reconciliation",
            "opencv_geometry",
        },
    ),
    (
        "app.services.wall_geometry_resolver",
        "WallGeometryResolver",
        "resolve",
        {
            "topology",
            "shapely_geometry",
            "dimension_grounding",
            "opencv_geometry",
            "thickness_evidence",
            "domain_rule_targets",
        },
    ),
    (
        "app.services.space_geometry_resolver",
        "SpaceGeometryResolver",
        "resolve",
        {
            "shapely_geometry",
            "reconciliation",
            "dimension_grounding",
            "wall_geometry",
        },
    ),
    (
        "app.services.quantia_spatial_contract_builder",
        "QuantiaSpatialContractBuilder",
        "build",
        {
            "base_layer",
            "reconciliation",
            "geometry_reconciliation",
            "dimension_grounding",
            "topology",
            "wall_geometry",
            "space_geometry",
        },
    ),
    (
        "app.services.quantia_spatial_reconstruction_service",
        "QuantiaSpatialReconstructionService",
        "reconstruct_page",
        {
            "document_bytes",
            "mime_type",
            "page_number",
            "base_layer",
            "pdf_render_scale",
            "ocr_strategy",
            "thickness_evidence",
            "domain_rule_targets",
        },
    ),
]


# ============================================================
# CLASES OBLIGATORIAS
# ============================================================


EXPECTED_CLASSES = [
    (
        "app.services.plan_document_analyzer",
        "DocumentRasterPage",
    ),
    (
        "app.services.plan_document_analyzer",
        "PlanDocumentAnalysis",
    ),
    (
        "app.services.space_pdf_coordinate_mapper",
        "NormalizedBBox",
    ),
    (
        "app.services.space_pdf_coordinate_mapper",
        "RasterBBox",
    ),
    (
        "app.services.space_pdf_coordinate_mapper",
        "PDFBBox",
    ),
    (
        "app.services.space_pdf_coordinate_mapper",
        "SpacePDFCoordinateMapping",
    ),
    (
        "app.schemas.quantia_spatial_contract",
        "QuantiaSpatialContract",
    ),
    (
        "app.schemas.quantia_spatial_contract",
        "SpatialBaseLayer",
    ),
    (
        "app.services.quantia_spatial_reconstruction_service",
        "QuantiaSpatialReconstructionService",
    ),
    (
        "app.services.quantia_spatial_reconstruction_service",
        "BaseLayerDescriptor",
    ),
]


# ============================================================
# HELPERS
# ============================================================


def import_module(
    module_name: str,
) -> tuple[Any | None, str | None]:
    try:
        return (
            importlib.import_module(
                module_name
            ),
            None,
        )

    except Exception as exc:
        return (
            None,
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def method_parameters(
    method: Any,
) -> set[str]:
    signature = inspect.signature(
        method
    )

    return {
        name
        for name
        in signature.parameters
        if name
        not in {
            "self",
            "cls",
        }
    }


# ============================================================
# PREFLIGHT
# ============================================================


def run_preflight() -> PreflightResult:
    result = PreflightResult()

    print()
    print(
        "=============================================="
    )
    print(
        " QUANTIA V2 — 03.2 SPATIAL PIPELINE PREFLIGHT"
    )
    print(
        "=============================================="
    )
    print()

    # ========================================================
    # PYTHON
    # ========================================================

    result.add(
        "Python",
        True,
        sys.version.split()[0],
    )

    # ========================================================
    # DEPENDENCIAS PYTHON
    # ========================================================

    for module_name in EXTERNAL_MODULES:
        module, error = (
            import_module(
                module_name
            )
        )

        if module is None:
            result.add(
                f"dependency:{module_name}",
                False,
                error
                or "No disponible",
            )

            continue

        version = getattr(
            module,
            "__version__",
            None,
        )

        result.add(
            f"dependency:{module_name}",
            True,
            str(
                version
                or "import OK"
            ),
        )

    # ========================================================
    # TESSERACT EJECUTABLE
    # ========================================================

    tesseract_path = (
        shutil.which(
            "tesseract"
        )
    )

    result.add(
        "tesseract executable",
        tesseract_path
        is not None,
        (
            tesseract_path
            or (
                "No encontrado en PATH. "
                "Puede configurarse mediante "
                "TESSERACT_CMD."
            )
        ),
    )

    # ========================================================
    # IMPORTS QUANTIA
    # ========================================================

    imported_modules: dict[
        str,
        Any,
    ] = {}

    for module_name in REQUIRED_MODULES:
        module, error = (
            import_module(
                module_name
            )
        )

        if module is None:
            result.add(
                f"import:{module_name}",
                False,
                error
                or "Import fallido",
            )

            continue

        imported_modules[
            module_name
        ] = module

        result.add(
            f"import:{module_name}",
            True,
            "OK",
        )

    # ========================================================
    # CLASES
    # ========================================================

    for (
        module_name,
        class_name,
    ) in EXPECTED_CLASSES:
        module = (
            imported_modules.get(
                module_name
            )
        )

        if module is None:
            result.add(
                f"class:{class_name}",
                False,
                (
                    "No se pudo validar porque "
                    "el módulo no importó."
                ),
            )

            continue

        value = getattr(
            module,
            class_name,
            None,
        )

        result.add(
            f"class:{class_name}",
            value is not None,
            (
                "OK"
                if value is not None
                else (
                    f"No existe {class_name} "
                    f"en {module_name}"
                )
            ),
        )

    # ========================================================
    # FIRMAS
    # ========================================================

    for (
        module_name,
        class_name,
        method_name,
        expected_parameters,
    ) in EXPECTED_METHODS:
        module = (
            imported_modules.get(
                module_name
            )
        )

        if module is None:
            result.add(
                (
                    f"signature:"
                    f"{class_name}."
                    f"{method_name}"
                ),
                False,
                "Módulo no importado.",
            )

            continue

        cls = getattr(
            module,
            class_name,
            None,
        )

        if cls is None:
            result.add(
                (
                    f"signature:"
                    f"{class_name}."
                    f"{method_name}"
                ),
                False,
                "Clase inexistente.",
            )

            continue

        method = getattr(
            cls,
            method_name,
            None,
        )

        if method is None:
            result.add(
                (
                    f"signature:"
                    f"{class_name}."
                    f"{method_name}"
                ),
                False,
                "Método inexistente.",
            )

            continue

        actual_parameters = (
            method_parameters(
                method
            )
        )

        missing = (
            expected_parameters
            - actual_parameters
        )

        if missing:
            result.add(
                (
                    f"signature:"
                    f"{class_name}."
                    f"{method_name}"
                ),
                False,
                (
                    "Faltan parámetros: "
                    + ", ".join(
                        sorted(
                            missing
                        )
                    )
                    + ". Actual: "
                    + ", ".join(
                        sorted(
                            actual_parameters
                        )
                    )
                ),
            )

        else:
            result.add(
                (
                    f"signature:"
                    f"{class_name}."
                    f"{method_name}"
                ),
                True,
                (
                    ", ".join(
                        sorted(
                            actual_parameters
                        )
                    )
                ),
            )

    # ========================================================
    # SCHEMA CONTRACT
    # ========================================================

    schema_module = (
        imported_modules.get(
            "app.schemas.quantia_spatial_contract"
        )
    )

    if schema_module is not None:
        contract_cls = getattr(
            schema_module,
            "QuantiaSpatialContract",
            None,
        )

        if contract_cls is not None:
            try:
                schema = (
                    contract_cls
                    .model_json_schema()
                )

                properties = set(
                    schema.get(
                        "properties",
                        {}
                    ).keys()
                )

                expected = {
                    "planoBase",
                    "niveles",
                    "ejes",
                    "muros",
                    "espacios",
                    "zonasSemanticas",
                    "puertas",
                    "ventanas",
                    "escaleras",
                    "cotas",
                    "geometria",
                    "origen",
                    "confianza",
                    "estado",
                    "confirmed",
                }

                missing = (
                    expected
                    - properties
                )

                result.add(
                    "contract:03.2→04",
                    not missing,
                    (
                        "OK"
                        if not missing
                        else (
                            "Faltan campos: "
                            + ", ".join(
                                sorted(
                                    missing
                                )
                            )
                        )
                    ),
                )

            except Exception as exc:
                result.add(
                    "contract:03.2→04",
                    False,
                    (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                )

    return result


# ============================================================
# OUTPUT
# ============================================================


def print_result(
    result: PreflightResult,
) -> None:
    print()

    for item in result.checks:
        marker = (
            "OK "
            if item.ok
            else "ERR"
        )

        print(
            f"[{marker}] "
            f"{item.name}"
        )

        if item.detail:
            print(
                f"      {item.detail}"
            )

    print()
    print(
        "----------------------------------------------"
    )

    print(
        f"PASSED: {result.passed}"
    )

    print(
        f"FAILED: {result.failed}"
    )

    print(
        "----------------------------------------------"
    )

    if result.failed:
        print()
        print(
            "PREFLIGHT = FAIL"
        )
        print(
            "No ejecutar todavía la prueba Gemini."
        )

    else:
        print()
        print(
            "PREFLIGHT = PASS"
        )
        print(
            "La cadena está lista para la prueba "
            "Miguel H."
        )


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    result = (
        run_preflight()
    )

    print_result(
        result
    )

    return (
        0
        if result.failed == 0
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )