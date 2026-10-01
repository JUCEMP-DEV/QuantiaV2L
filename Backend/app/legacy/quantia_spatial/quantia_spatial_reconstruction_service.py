from __future__ import annotations
from time import perf_counter


from app.schemas.quantia_extraction import (
    QuantiaExtractionSchema,
)

from dataclasses import (
    asdict,
    dataclass,
    field,
    fields,
)
from typing import (
    Any,
    Callable,
    Literal,
)

from app.schemas.quantia_spatial_contract import (
    QuantiaSpatialContract,
    SpatialBaseLayer,
)
from app.legacy.quantia_spatial.architectural_dimension_grounding_service import (
    ArchitecturalDimensionGroundingResult,
    ArchitecturalDimensionGroundingService,
)
from app.legacy.quantia_spatial.architectural_graph_builder import (
    ArchitecturalGraphBuilder,
    ArchitecturalGraphResult,
)
from app.legacy.quantia_spatial.architectural_wall_abstraction_service import (
    ArchitecturalWallAbstractionResult,
    ArchitecturalWallAbstractionService,
)
from app.services.gemini_vision_provider import (
    GeminiVisionProvider,
    get_gemini_vision_provider,
)
from app.services.ocr_plan_text_service import (
    OCRPlanTextResult,
    OCRPlanTextService,
)
from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
    OpenCVPlanGeometryService,
)
from app.legacy.quantia_spatial.pdf_plan_evidence_extractor import (
    PDFPlanEvidence,
    PDFPlanEvidenceExtractor,
)
from app.legacy.quantia_spatial.pdf_quantia_grounding_service import (
    PDFQuantiaGroundingService,
    QuantiaGroundingResult,
)
from app.services.plan_document_analyzer import (
    DocumentRasterPage,
    PlanDocumentAnalysis,
    PlanDocumentAnalyzer,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    PlanGeometryReconciler,
    PlanGeometryReconciliationResult,
)
from app.legacy.quantia_spatial.quantia_extraction_reconciler import (
    QuantiaReconciliationResult,
    reconcile_gemini_transport,
)
from app.legacy.quantia_spatial.quantia_spatial_contract_builder import (
    QuantiaSpatialContractBuilder,
)
from app.legacy.quantia_spatial.shapely_plan_geometry_service import (
    ShapelyPlanGeometryResult,
    ShapelyPlanGeometryService,
)
from app.legacy.quantia_spatial.space_geometry_resolver import (
    SpaceGeometryResolver,
    SpaceGeometryResolverResult,
)
from app.legacy.quantia_spatial.space_pdf_coordinate_mapper import (
    SpacePDFCoordinateMapper,
    SpacePDFCoordinateMapping,
)
from app.legacy.quantia_spatial.space_raster_coordinate_mapper import (
    SpaceRasterCoordinateMapper,
    SpaceRasterCoordinateMapping,
)
from app.legacy.quantia_spatial.space_vector_boundary_probe import (
    SpaceVectorBoundaryProbeResult,
    SpaceVectorBoundaryProbeService,
)
from app.legacy.quantia_spatial.wall_geometry_resolver import (
    WallGeometryResolver,
    WallGeometryResolverResult,
    WallThicknessEvidence,
)
from app.legacy.quantia_spatial.wall_opening_topology_service import (
    WallOpeningTopologyResult,
    WallOpeningTopologyService,
)

# ============================================================
# TIPOS
# ============================================================


CoordinateMapping = SpacePDFCoordinateMapping | SpaceRasterCoordinateMapping


OCRStrategy = Literal[
    "auto",
    "always",
]


LocalizationPromptBuilder = Callable[
    [
        QuantiaExtractionSchema,
    ],
    str,
]


# ============================================================
# DESCRIPTOR DE PLANO BASE
# ============================================================


@dataclass(
    slots=True,
    frozen=True,
)
class BaseLayerDescriptor:
    """
    Metadatos que el almacenamiento/frontend conoce y que
    este servicio NO debe inventar.

    anchoPx / altoPx / mimeType / pagina se obtienen del
    raster canónico y no se reciben aquí.
    """

    id: str

    nombre: str

    referencia: str | None

    visible: bool

    bloqueado: bool

    ocultable: bool

    bloqueable: bool


# ============================================================
# METADATOS GEMINI
# ============================================================


@dataclass(slots=True)
class VisionExecutionMetadata:
    provider: str

    model: str

    fallback_used: bool


# ============================================================
# RESULTADO FINAL
# ============================================================


@dataclass(slots=True)
class QuantiaSpatialReconstructionResult:
    """
    Resultado completo de una página.

    raster_page contiene bytes y por ello NO se incluye
    automáticamente en audit_dict().
    """

    page: int

    contract: QuantiaSpatialContract

    document_analysis: PlanDocumentAnalysis

    raster_page: DocumentRasterPage

    semantic_reconciliation: QuantiaReconciliationResult

    localization_payload: dict[
        str,
        Any,
    ]

    coordinate_mapping: CoordinateMapping

    opencv_geometry: OpenCVPlanGeometryResult

    ocr_result: OCRPlanTextResult | None

    pdf_evidence: PDFPlanEvidence | None

    pdf_grounding: QuantiaGroundingResult | None

    vector_probe: SpaceVectorBoundaryProbeResult | None

    geometry_reconciliation: PlanGeometryReconciliationResult

    architectural_graph: ArchitecturalGraphResult

    opening_topology: WallOpeningTopologyResult

    shapely_geometry: ShapelyPlanGeometryResult

    dimension_grounding: ArchitecturalDimensionGroundingResult

    wall_abstraction: ArchitecturalWallAbstractionResult

    wall_geometry: WallGeometryResolverResult

    space_geometry: SpaceGeometryResolverResult

    extraction_vision: VisionExecutionMetadata

    localization_vision: VisionExecutionMetadata

    notes: list[str] = field(default_factory=list)

    def audit_dict(
        self,
    ) -> dict[str, Any]:
        """
        Auditoría serializable sin:

            - bytes del raster;
            - raw response Gemini;
            - base64;
            - payload HTTP.
        """

        return {
            "page": self.page,
            "document": {
                "mime_type": self.document_analysis.mime_type,
                "document_type": self.document_analysis.document_type,
                "page_count": self.document_analysis.page_count,
                "vector_text_available": self.document_analysis.vector_text_available,
                "vector_geometry_available": self.document_analysis.vector_geometry_available,
            },
            "raster": {
                "page": self.raster_page.page,
                "width_px": self.raster_page.width_px,
                "height_px": self.raster_page.height_px,
                "mime_type": self.raster_page.mime_type,
            },
            "vision": {
                "extraction": asdict(self.extraction_vision),
                "localization": asdict(self.localization_vision),
            },
            "routes": {
                "ocr_used": self.ocr_result is not None,
                "pdf_grounding_used": self.pdf_grounding is not None,
                "vector_probe_used": self.vector_probe is not None,
            },
            "counts": {
                "opencv_horizontal_segments": len(
                    self.opencv_geometry.horizontal_segments
                ),
                "opencv_vertical_segments": len(self.opencv_geometry.vertical_segments),
                "opencv_intersections": len(self.opencv_geometry.intersections),
                "localized_spaces": len(self.coordinate_mapping.spaces),
                "graph_nodes": len(self.architectural_graph.nodes),
                "graph_edges": len(self.architectural_graph.edges),
                "faces": len(self.shapely_geometry.faces),
                "wall_runs": len(self.wall_abstraction.wall_runs),
                "walls": len(self.wall_geometry.walls),
                "spaces": len(self.space_geometry.spaces),
                "space_candidates": len(self.space_geometry.spaces),
                "contract_spaces": len(self.contract.espacios),
                "semantic_fallback_spaces": sum(
                    1
                    for space in self.space_geometry.spaces
                    if space.face_id.startswith("SEMANTIC_BBOX_")
                ),
                "semantic_zones": len(self.space_geometry.semantic_zones),
            },
            "dimension_grounding": self.dimension_grounding.to_dict(),
            "wall_abstraction": self.wall_abstraction.to_dict(),
            "geometry_reconciliation": self.geometry_reconciliation.to_dict(),
            "shapely_geometry": self.shapely_geometry.to_dict(),
            "space_geometry": self.space_geometry.to_dict(),
            "contract": self.contract.model_dump(mode="json"),
            "notes": list(self.notes),
        }


# ============================================================
# SERVICIO
# ============================================================


class QuantiaSpatialReconstructionService:
    """
    Orquestador de producción de 03.2.

    ==========================================================
    PDF VECTORIAL / HÍBRIDO
    ==========================================================

        PDF
         │
         ├─ PyMuPDF
         │   ├─ texto
         │   ├─ cotas/ejes
         │   └─ geometría vectorial
         │
         ├─ render canónico
         │   ├─ Gemini
         │   ├─ OpenCV
         │   └─ OCR si corresponde
         │
         ↓
        reconciliación
         ↓
        grafo
         ↓
        openings
         ↓
        Shapely
         ↓
        dimensiones
         ↓
        muros
         ↓
        espacios
         ↓
        contrato 04


    ==========================================================
    JPG / PNG / CROQUIS
    ==========================================================

        raster canónico
         │
         ├─ Gemini
         ├─ OpenCV
         └─ Tesseract
         │
         ↓
        misma cadena Quantia


    ==========================================================
    ALCANCE
    ==========================================================

    Este servicio procesa UNA página.

    No inventa todavía un merge entre páginas, porque no
    existe un contrato verificado de fusión multipágina.

    RAG tampoco se ejecuta aquí:

        RAG = contexto documental paralelo
        RAG != geometría
    """

    PDF_MIME_TYPE = "application/pdf"

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        *,
        extraction_prompt: str,
        extraction_response_json_schema: dict[
            str,
            Any,
        ],
        localization_prompt_builder: LocalizationPromptBuilder,
        localization_response_json_schema: dict[
            str,
            Any,
        ],
        vision_provider: GeminiVisionProvider | None = None,
        document_analyzer: PlanDocumentAnalyzer | None = None,
        opencv_service: OpenCVPlanGeometryService | None = None,
        ocr_service: OCRPlanTextService | None = None,
        pdf_evidence_extractor: PDFPlanEvidenceExtractor | None = None,
        pdf_grounding_service: PDFQuantiaGroundingService | None = None,
        pdf_coordinate_mapper: SpacePDFCoordinateMapper | None = None,
        raster_coordinate_mapper: SpaceRasterCoordinateMapper | None = None,
        vector_probe_service: SpaceVectorBoundaryProbeService | None = None,
        geometry_reconciler: PlanGeometryReconciler | None = None,
        graph_builder: ArchitecturalGraphBuilder | None = None,
        opening_topology_service: WallOpeningTopologyService | None = None,
        shapely_service: ShapelyPlanGeometryService | None = None,
        dimension_grounding_service: (
            ArchitecturalDimensionGroundingService | None
        ) = None,
        wall_abstraction_service: ArchitecturalWallAbstractionService | None = None,
        wall_geometry_resolver: WallGeometryResolver | None = None,
        space_geometry_resolver: SpaceGeometryResolver | None = None,
        contract_builder: QuantiaSpatialContractBuilder | None = None,
    ) -> None:
        self.extraction_prompt = self._required_prompt(
            extraction_prompt,
            "extraction_prompt",
        )

        self.extraction_response_json_schema = self._required_schema(
            extraction_response_json_schema,
            "extraction_response_json_schema",
        )

        if not callable(localization_prompt_builder):
            raise ValueError("localization_prompt_builder " "debe ser callable.")

        self.localization_prompt_builder = localization_prompt_builder

        self.localization_response_json_schema = self._required_schema(
            localization_response_json_schema,
            "localization_response_json_schema",
        )

        self.vision_provider = vision_provider or get_gemini_vision_provider()

        self.document_analyzer = document_analyzer or PlanDocumentAnalyzer()

        self.opencv_service = opencv_service or OpenCVPlanGeometryService()

        self.ocr_service = ocr_service or OCRPlanTextService()

        self.pdf_evidence_extractor = (
            pdf_evidence_extractor or PDFPlanEvidenceExtractor()
        )

        self.pdf_grounding_service = (
            pdf_grounding_service or PDFQuantiaGroundingService()
        )

        self.pdf_coordinate_mapper = pdf_coordinate_mapper or SpacePDFCoordinateMapper()

        self.raster_coordinate_mapper = (
            raster_coordinate_mapper or SpaceRasterCoordinateMapper()
        )

        self.vector_probe_service = (
            vector_probe_service or SpaceVectorBoundaryProbeService()
        )

        self.geometry_reconciler = geometry_reconciler or PlanGeometryReconciler()

        self.graph_builder = graph_builder or ArchitecturalGraphBuilder()

        self.opening_topology_service = (
            opening_topology_service or WallOpeningTopologyService()
        )

        self.shapely_service = shapely_service or ShapelyPlanGeometryService()

        self.dimension_grounding_service = (
            dimension_grounding_service or ArchitecturalDimensionGroundingService()
        )

        self.wall_abstraction_service = (
            wall_abstraction_service or ArchitecturalWallAbstractionService()
        )

        self.wall_geometry_resolver = wall_geometry_resolver or WallGeometryResolver()

        self.space_geometry_resolver = (
            space_geometry_resolver or SpaceGeometryResolver()
        )

        self.contract_builder = contract_builder or QuantiaSpatialContractBuilder()

    # ========================================================
    # API
    # ========================================================

    def reconstruct_page(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
        page_number: int,
        base_layer: BaseLayerDescriptor,
        pdf_render_scale: float | None = None,
        ocr_strategy: OCRStrategy = "auto",
        thickness_evidence: list[WallThicknessEvidence] | None = None,
        domain_rule_targets: set[str] | None = None,
    ) -> QuantiaSpatialReconstructionResult:
        normalized_mime = self._normalize_mime(mime_type)

        self._validate_page_request(
            document_bytes=document_bytes,
            mime_type=normalized_mime,
            page_number=page_number,
            pdf_render_scale=pdf_render_scale,
            ocr_strategy=ocr_strategy,
            base_layer=base_layer,
        )

        pipeline_started = perf_counter()

        def trace(message: str) -> None:
            elapsed = perf_counter() - pipeline_started
            print(
                f"[03.2 +{elapsed:7.2f}s] {message}",
                flush=True,
            )

        trace("PIPELINE START")

        self._validate_page_request(
            document_bytes=document_bytes,
            mime_type=normalized_mime,
            page_number=page_number,
            pdf_render_scale=pdf_render_scale,
            ocr_strategy=ocr_strategy,
            base_layer=base_layer,
        )
        pipeline_started = perf_counter()

        def trace(message: str) -> None:
            elapsed = perf_counter() - pipeline_started
            print(
                f"[03.2 +{elapsed:7.2f}s] {message}",
                flush=True,
            )

        # ====================================================
        # 1. ANÁLISIS DOCUMENTAL
        # ====================================================
        trace("Document analysis ........ START")
        analysis = self.document_analyzer.analyze(
            document_bytes=document_bytes,
            mime_type=normalized_mime,
        )

        if page_number < 1 or page_number > analysis.page_count:
            raise ValueError("La página solicitada no existe " "en el documento.")
        trace("Document analysis ........ OK")
        # ====================================================
        # 2. RASTER CANÓNICO
        # ====================================================
        trace("Raster preparation ....... START")
        if normalized_mime == self.PDF_MIME_TYPE:
            if pdf_render_scale is None:
                raise ValueError(
                    "pdf_render_scale es obligatorio " "para documentos PDF."
                )

            effective_render_scale = pdf_render_scale

        else:
            # El analyzer ignora render_scale para imágenes.
            #
            # No existe resize ni calibración asociada a este
            # valor en JPG/PNG.
            effective_render_scale = 1.0

        raster_pages = self.document_analyzer.prepare_raster_pages(
            document_bytes=document_bytes,
            mime_type=normalized_mime,
            render_scale=effective_render_scale,
        )

        raster = self._select_raster_page(
            raster_pages=raster_pages,
            page_number=page_number,
        )
        trace("Raster preparation ....... OK")
        # ====================================================
        # 3. OPENCV
        # ====================================================
        trace("OpenCV geometry .......... START")
        opencv_geometry = self.opencv_service.analyze(raster=raster)
        trace("OpenCV geometry .......... OK")
        # ====================================================
        # 4. GEMINI — EXTRACCIÓN SEMÁNTICA
        # ====================================================
        trace("Gemini extraction ........ START")
        extraction_vision = self.vision_provider.analyze(
            prompt=self.extraction_prompt,
            media_bytes=raster.image_bytes,
            media_mime_type=raster.mime_type,
            response_json_schema=self.extraction_response_json_schema,
        )

        extraction_payload = self._vision_dict(
            extraction_vision.data,
            stage="extracción",
        )

        semantic_reconciliation = reconcile_gemini_transport(extraction_payload)
        trace("Gemini extraction ........ OK")
        # ====================================================
        # 5. PYMUPDF — EVIDENCIA / GROUNDING
        # ====================================================

        pdf_evidence: PDFPlanEvidence | None = None

        pdf_grounding: QuantiaGroundingResult | None = None

        page_has_vector_text = False

        page_has_vector_geometry = False

        if normalized_mime == self.PDF_MIME_TYPE:
            page_has_vector_text = self._page_has_vector_text(
                analysis=analysis,
                page_number=page_number,
            )

            page_has_vector_geometry = self._page_has_vector_geometry(
                analysis=analysis,
                page_number=page_number,
            )

            full_pdf_evidence = self.pdf_evidence_extractor.extract(analysis)

            pdf_evidence = self._filter_pdf_evidence_page(
                evidence=full_pdf_evidence,
                page_number=page_number,
            )

            if page_has_vector_text:
                pdf_grounding = self.pdf_grounding_service.ground(
                    reconciliation=semantic_reconciliation,
                    pdf_evidence=pdf_evidence,
                )

        # ====================================================
        # 6. RECONCILIACIÓN SEMÁNTICA EFECTIVA
        # ====================================================

        effective_reconciliation = self._effective_reconciliation(
            semantic=semantic_reconciliation,
            grounding=pdf_grounding,
        )

        # ====================================================
        # 7. GEMINI — LOCALIZACIÓN
        # ====================================================
        trace("Gemini localization ...... START")
        localization_prompt = self.localization_prompt_builder(
            effective_reconciliation.extraction
        )

        localization_prompt = self._required_prompt(
            localization_prompt,
            "localization_prompt",
        )

        localization_vision = self.vision_provider.analyze(
            prompt=localization_prompt,
            media_bytes=raster.image_bytes,
            media_mime_type=raster.mime_type,
            response_json_schema=self.localization_response_json_schema,
        )

        localization_payload = self._vision_dict(
            localization_vision.data,
            stage="localización",
        )

        self._validate_localization_page(
            payload=localization_payload,
            expected_page=page_number,
        )
        trace("Gemini localization ...... OK")
        # ====================================================
        # 8. COORDENADAS
        # ====================================================

        if normalized_mime == self.PDF_MIME_TYPE:
            coordinate_mapping = self.pdf_coordinate_mapper.map(
                analysis=analysis,
                localization_payload=localization_payload,
                image_width_px=raster.width_px,
                image_height_px=raster.height_px,
            )

        else:
            coordinate_mapping = self.raster_coordinate_mapper.map(
                localization_payload=localization_payload,
                image_width_px=raster.width_px,
                image_height_px=raster.height_px,
            )

        # ====================================================
        # 9. OCR / TESSERACT
        # ====================================================

        use_ocr = self._should_use_ocr(
            mime_type=normalized_mime,
            page_has_vector_text=page_has_vector_text,
            strategy=ocr_strategy,
        )

        ocr_result: OCRPlanTextResult | None = None

        if use_ocr:
            ocr_result = self.ocr_service.analyze(raster=raster)

        # ====================================================
        # 10. PROBE VECTORIAL PDF
        # ====================================================

        vector_probe: SpaceVectorBoundaryProbeResult | None = None

        if (
            normalized_mime == self.PDF_MIME_TYPE
            and page_has_vector_geometry
            and isinstance(
                coordinate_mapping,
                SpacePDFCoordinateMapping,
            )
        ):
            vector_probe = self.vector_probe_service.probe(
                analysis=analysis,
                mapping=coordinate_mapping,
            )

        # ====================================================
        # 11. RECONCILIACIÓN GEOMÉTRICA
        # ====================================================

        geometry_reconciliation = self.geometry_reconciler.reconcile(
            opencv_geometry=opencv_geometry,
            mapping=coordinate_mapping,
            ocr=ocr_result,
            pdf_grounding=pdf_grounding,
            vector_probe=vector_probe,
            metric_candidates=effective_reconciliation.metric_candidates,
        )

        # ====================================================
        # 12. EJES + COTAS + DIMENSIONES
        # ====================================================

        dimension_grounding = self.dimension_grounding_service.ground(
            reconciliation=geometry_reconciliation,
            opencv_geometry=opencv_geometry,
        )

        # ====================================================
        # 13. ABSTRACCIÓN DE MUROS
        # ====================================================

        wall_abstraction = self.wall_abstraction_service.abstract(
            reconciliation=geometry_reconciliation,
            dimension_grounding=dimension_grounding,
            opencv_geometry=opencv_geometry,
        )

        # ====================================================
        # 14. GRAFO ARQUITECTÓNICO
        # ====================================================

        architectural_graph = self.graph_builder.build(
            reconciliation=geometry_reconciliation,
            opencv_geometry=opencv_geometry,
        )

        # ====================================================
        # 15. OPENINGS / CONTINUIDAD TOPOLOGÍA
        # ====================================================

        opening_topology = self.opening_topology_service.analyze(
            graph=architectural_graph,
            reconciliation=effective_reconciliation,
            opencv_geometry=opencv_geometry,
        )

        # ====================================================
        # 16. SHAPELY
        # ====================================================

        shapely_geometry = self.shapely_service.analyze(
            topology=opening_topology,
            reconciliation=geometry_reconciliation,
        )

        # ====================================================
        # 17. MUROS
        # ====================================================

        wall_geometry = self.wall_geometry_resolver.resolve(
            topology=opening_topology,
            shapely_geometry=shapely_geometry,
            dimension_grounding=dimension_grounding,
            opencv_geometry=opencv_geometry,
            thickness_evidence=thickness_evidence,
            domain_rule_targets=domain_rule_targets,
        )

        # ====================================================
        # 18. ESPACIOS / ZONAS
        # ====================================================

        space_geometry = self.space_geometry_resolver.resolve(
            shapely_geometry=shapely_geometry,
            reconciliation=geometry_reconciliation,
            dimension_grounding=dimension_grounding,
            wall_geometry=wall_geometry,
        )

        # ====================================================
        # 19. BASE LAYER CANÓNICO
        # ====================================================

        spatial_base_layer = SpatialBaseLayer(
            id=base_layer.id,
            nombre=base_layer.nombre,
            mimeType=raster.mime_type,
            pagina=raster.page,
            anchoPx=raster.width_px,
            altoPx=raster.height_px,
            referencia=base_layer.referencia,
            visible=base_layer.visible,
            bloqueado=base_layer.bloqueado,
            ocultable=base_layer.ocultable,
            bloqueable=base_layer.bloqueable,
        )

        # ====================================================
        # 20. CONTRATO 03.2 → 04
        # ====================================================

        contract = self.contract_builder.build(
            base_layer=
                spatial_base_layer,

            reconciliation=
                effective_reconciliation,

            geometry_reconciliation=
                geometry_reconciliation,

            dimension_grounding=
                dimension_grounding,

            wall_abstraction=
                wall_abstraction,

            topology=
                opening_topology,

            wall_geometry=
                wall_geometry,

            space_geometry=
                space_geometry,
        )

        # ====================================================
        # 21. RESULTADO
        # ====================================================
        trace("Result assembly ........... START")

        result = QuantiaSpatialReconstructionResult(
            page=page_number,
            contract=contract,
            document_analysis=analysis,
            raster_page=raster,
            semantic_reconciliation=effective_reconciliation,
            localization_payload=localization_payload,
            coordinate_mapping=coordinate_mapping,
            opencv_geometry=opencv_geometry,
            ocr_result=ocr_result,
            pdf_evidence=pdf_evidence,
            pdf_grounding=pdf_grounding,
            vector_probe=vector_probe,
            geometry_reconciliation=geometry_reconciliation,
            architectural_graph=architectural_graph,
            opening_topology=opening_topology,
            shapely_geometry=shapely_geometry,
            dimension_grounding=dimension_grounding,
            wall_abstraction=wall_abstraction,
            wall_geometry=wall_geometry,
            space_geometry=space_geometry,
            extraction_vision=VisionExecutionMetadata(
                provider=extraction_vision.provider,
                model=extraction_vision.model,
                fallback_used=extraction_vision.fallback_used,
            ),
            localization_vision=VisionExecutionMetadata(
                provider=localization_vision.provider,
                model=localization_vision.model,
                fallback_used=localization_vision.fallback_used,
            ),
            notes=[
                (
                    "03.2 completó la reconstrucción "
                    "de una página hasta el contrato "
                    "editable de 04."
                ),
                ("Gemini aportó semántica y " "localización aproximada."),
                ("OpenCV aportó evidencia geométrica " "raster."),
                ("PyMuPDF aportó evidencia vectorial " "cuando estuvo disponible."),
                (
                    "Tesseract se utilizó para raster "
                    "y para PDF cuando la estrategia "
                    "determinó que era necesario."
                ),
                (
                    "Las métricas no se promovieron "
                    "por coincidencia numérica aislada."
                ),
                ("Las continuidades virtuales de " "openings permanecen trazables."),
                ("RAG permanece fuera de esta " "cadena geométrica."),
                ("Todo elemento automático llega " "a 04 con confirmed=false."),
            ],
        )
        trace("Result assembly ........... OK")
        trace("PIPELINE OK")
        return result

    # ========================================================
    # RECONCILIACIÓN EFECTIVA
    # ========================================================

    @staticmethod
    def _effective_reconciliation(
        *,
        semantic: QuantiaReconciliationResult,
        grounding: QuantiaGroundingResult | None,
    ) -> QuantiaReconciliationResult:
        """
        Si existe grounding PDF usamos su copia del schema
        canónico, porque puede contener evidencia documental
        adicional.

        Las métricas propuestas y los descartes siguen siendo
        los originales del reconciliador Gemini.
        """

        if grounding is None:
            return semantic

        return QuantiaReconciliationResult(
            extraction=grounding.extraction,
            metric_candidates=list(semantic.metric_candidates),
            discarded_model_confirmations=list(semantic.discarded_model_confirmations),
            discarded_unidentified=list(semantic.discarded_unidentified),
            unmapped_constructive_items=list(semantic.unmapped_constructive_items),
        )

    # ========================================================
    # OCR
    # ========================================================

    def _should_use_ocr(
        self,
        *,
        mime_type: str,
        page_has_vector_text: bool,
        strategy: OCRStrategy,
    ) -> bool:
        # JPG / PNG:
        #
        # OCR forma parte de la ruta canónica.
        if mime_type != self.PDF_MIME_TYPE:
            return True

        # PDF:
        #
        # always:
        #     usa OCR aunque exista texto vectorial.
        #
        # auto:
        #     solo cuando esa página no contiene texto
        #     vectorial aprovechable.
        if strategy == "always":
            return True

        return not page_has_vector_text

    # ========================================================
    # PÁGINA CON TEXTO VECTORIAL
    # ========================================================

    @staticmethod
    def _page_has_vector_text(
        *,
        analysis: PlanDocumentAnalysis,
        page_number: int,
    ) -> bool:
        page = analysis.pages[page_number - 1]

        return any(str(span.text or "").strip() for span in page.text_spans)

    # ========================================================
    # PÁGINA CON GEOMETRÍA VECTORIAL
    # ========================================================

    @staticmethod
    def _page_has_vector_geometry(
        *,
        analysis: PlanDocumentAnalysis,
        page_number: int,
    ) -> bool:
        page = analysis.pages[page_number - 1]

        return bool(page.lines)

    # ========================================================
    # FILTRAR EVIDENCIA PDF POR PÁGINA
    # ========================================================

    @staticmethod
    def _filter_pdf_evidence_page(
        *,
        evidence: PDFPlanEvidence,
        page_number: int,
    ) -> PDFPlanEvidence:
        """
        No codifica manualmente la lista de campos del
        dataclass PDFPlanEvidence.

        Esto permite conservar nuevas colecciones futuras
        sin romper el orquestador.
        """

        payload: dict[
            str,
            Any,
        ] = {}

        for definition in fields(PDFPlanEvidence):
            value = getattr(
                evidence,
                definition.name,
            )

            if isinstance(
                value,
                list,
            ):
                payload[definition.name] = [
                    item
                    for item in value
                    if (
                        getattr(
                            item,
                            "page",
                            page_number,
                        )
                        == page_number
                    )
                ]

            else:
                payload[definition.name] = value

        return PDFPlanEvidence(**payload)

    # ========================================================
    # SELECCIONAR RASTER
    # ========================================================

    @staticmethod
    def _select_raster_page(
        *,
        raster_pages: list[DocumentRasterPage],
        page_number: int,
    ) -> DocumentRasterPage:
        for raster in raster_pages:
            if raster.page == page_number:
                return raster

        raise ValueError("No se generó raster canónico " "para la página solicitada.")

    # ========================================================
    # RESPONSE GEMINI → DICT
    # ========================================================

    @staticmethod
    def _vision_dict(
        value: Any,
        *,
        stage: str,
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "Gemini no devolvió un objeto JSON " f"válido durante {stage}."
            )

        return value

    # ========================================================
    # VALIDAR PÁGINA LOCALIZACIÓN
    # ========================================================

    @staticmethod
    def _validate_localization_page(
        *,
        payload: dict[
            str,
            Any,
        ],
        expected_page: int,
    ) -> None:
        if "pagina" not in payload:
            raise ValueError(
                "La respuesta de localización no " "contiene el campo pagina."
            )

        value = payload.get("pagina")

        if isinstance(
            value,
            bool,
        ):
            raise ValueError("La página de localización es inválida.")

        try:
            page = int(value)

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError("La página de localización es inválida.") from exc

        if page != expected_page:
            raise ValueError("Gemini localizó una página diferente " "a la solicitada.")

    # ========================================================
    # VALIDACIÓN SOLICITUD
    # ========================================================

    def _validate_page_request(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
        page_number: int,
        pdf_render_scale: float | None,
        ocr_strategy: str,
        base_layer: BaseLayerDescriptor,
    ) -> None:
        if not document_bytes:
            raise ValueError("El documento está vacío.")

        if mime_type not in {
            "application/pdf",
            "image/jpeg",
            "image/png",
        }:
            raise ValueError(
                "Tipo de documento no soportado: " f"{mime_type or 'desconocido'}"
            )

        if (
            isinstance(
                page_number,
                bool,
            )
            or not isinstance(
                page_number,
                int,
            )
            or page_number <= 0
        ):
            raise ValueError("page_number inválido.")

        if mime_type != self.PDF_MIME_TYPE and page_number != 1:
            raise ValueError("Las imágenes raster solo contienen " "la página 1.")

        if mime_type == self.PDF_MIME_TYPE:
            if pdf_render_scale is None:
                raise ValueError("pdf_render_scale es obligatorio " "para PDF.")

            if (
                isinstance(
                    pdf_render_scale,
                    bool,
                )
                or not isinstance(
                    pdf_render_scale,
                    (int, float),
                )
                or float(pdf_render_scale) <= 0
            ):
                raise ValueError("pdf_render_scale inválido.")

        if ocr_strategy not in {
            "auto",
            "always",
        }:
            raise ValueError("ocr_strategy debe ser " "'auto' o 'always'.")

        if not str(base_layer.id or "").strip():
            raise ValueError("base_layer.id es obligatorio.")

        if not str(base_layer.nombre or "").strip():
            raise ValueError("base_layer.nombre es obligatorio.")

    # ========================================================
    # PROMPT
    # ========================================================

    @staticmethod
    def _required_prompt(
        value: Any,
        name: str,
    ) -> str:
        if (
            not isinstance(
                value,
                str,
            )
            or not value.strip()
        ):
            raise ValueError(f"{name} está vacío.")

        return value.strip()

    # ========================================================
    # SCHEMA
    # ========================================================

    @staticmethod
    def _required_schema(
        value: Any,
        name: str,
    ) -> dict[
        str,
        Any,
    ]:
        if (
            not isinstance(
                value,
                dict,
            )
            or not value
        ):
            raise ValueError(f"{name} debe ser un JSON Schema " "no vacío.")

        return value

    # ========================================================
    # MIME
    # ========================================================

    @staticmethod
    def _normalize_mime(
        value: Any,
    ) -> str:
        return str(value or "").strip().lower()


# ============================================================
# FACTORY
# ============================================================


def get_quantia_spatial_reconstruction_service(
    *,
    extraction_prompt: str,
    extraction_response_json_schema: dict[
        str,
        Any,
    ],
    localization_prompt_builder: LocalizationPromptBuilder,
    localization_response_json_schema: dict[
        str,
        Any,
    ],
) -> QuantiaSpatialReconstructionService:
    return QuantiaSpatialReconstructionService(
        extraction_prompt=extraction_prompt,
        extraction_response_json_schema=extraction_response_json_schema,
        localization_prompt_builder=localization_prompt_builder,
        localization_response_json_schema=localization_response_json_schema,
    )
