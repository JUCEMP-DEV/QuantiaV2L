from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.ocr_plan_text_service import (
    OCRPlanTextResult,
    OCRTextItem,
)
from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
    RasterLineSegment,
)
from app.legacy.quantia_spatial.pdf_quantia_grounding_service import (
    GroundedMetricCandidate,
    QuantiaGroundingResult,
)
from app.legacy.quantia_spatial.quantia_extraction_reconciler import (
    MetricCandidate,
)
from app.legacy.quantia_spatial.space_pdf_coordinate_mapper import (
    RasterBBox,
    SpacePDFCoordinateMapping,
)
from app.legacy.quantia_spatial.space_raster_coordinate_mapper import (
    SpaceRasterCoordinateMapping,
)
from app.legacy.quantia_spatial.space_vector_boundary_probe import (
    SpaceVectorBoundaryProbeResult,
    VectorSegmentCandidate,
)

MappingType = SpacePDFCoordinateMapping | SpaceRasterCoordinateMapping


# ============================================================
# TEXTO UNIFICADO
# ============================================================


@dataclass(slots=True)
class GeometryTextEvidence:
    kind: str

    text: str

    page: int

    x: float
    y: float

    bbox: list[float]

    numeric_value: float | None

    numeric_unit: str | None

    comparison_value: float | None

    source: str

    confidence: float


# ============================================================
# CANDIDATO A LÍMITE/MURO
# ============================================================


@dataclass(slots=True)
class BoundaryCandidate:
    """
    Línea candidata relacionada con un recinto.

    NO constituye todavía un muro Quantia.
    """

    side: str

    orientation: str

    x1: float
    y1: float
    x2: float
    y2: float

    length_px: float

    bbox_coverage_ratio: float

    distance_to_bbox_edge_px: float

    crosses_space_center: bool

    opencv_segment_id: str

    vector_support_indices: list[int] = field(default_factory=list)

    sources: list[str] = field(default_factory=list)

    support_count: int = 1

    confirmed: bool = False

    state: str = "CANDIDATO"


@dataclass(slots=True)
class DirectionalGeometryCandidates:
    left: list[BoundaryCandidate] = field(default_factory=list)

    right: list[BoundaryCandidate] = field(default_factory=list)

    top: list[BoundaryCandidate] = field(default_factory=list)

    bottom: list[BoundaryCandidate] = field(default_factory=list)


# ============================================================
# ASOCIACIÓN MÉTRICA
# ============================================================


@dataclass(slots=True)
class MetricSpatialCandidate:
    element_type: str

    element_id: str

    field: str

    value: float

    metric_kind: str

    evidence_source: str

    matched_text: str | None

    matched_text_source: str | None

    matched_value: float | None

    matched_bbox: list[float] | None

    distance_to_space_bbox_px: float | None

    inside_space_bbox: bool

    association_validated: bool = False


# ============================================================
# EVIDENCIA CERCA DE ESPACIO
# ============================================================


@dataclass(slots=True)
class NearbyTextEvidence:
    kind: str

    text: str

    source: str

    x: float
    y: float

    distance_to_space_bbox_px: float

    relative_position: str

    numeric_value: float | None = None


# ============================================================
# RESULTADO POR ESPACIO
# ============================================================


@dataclass(slots=True)
class SpaceGeometryReconciliation:
    nivel: str

    id_propuesto: str

    nombre: str

    localization_bbox: RasterBBox

    boundaries: DirectionalGeometryCandidates

    nearby_axes: list[NearbyTextEvidence] = field(default_factory=list)

    nearby_dimensions: list[NearbyTextEvidence] = field(default_factory=list)

    metric_associations: list[MetricSpatialCandidate] = field(default_factory=list)

    wall_geometry_confirmed: bool = False

    polygon_confirmed: bool = False


# ============================================================
# RESULTADO GENERAL
# ============================================================


@dataclass(slots=True)
class PlanGeometryReconciliationResult:
    page: int

    width_px: int
    height_px: int

    spaces: list[SpaceGeometryReconciliation] = field(default_factory=list)

    axis_evidence: list[GeometryTextEvidence] = field(default_factory=list)

    dimension_evidence: list[GeometryTextEvidence] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# RECONCILIADOR
# ============================================================


class PlanGeometryReconciler:
    """
    Primera fusión geométrica real de Quantia.

    Combina:

        OpenCV
        + localización Gemini
        + OCR/Tesseract
        + PyMuPDF cuando existe
        + grounding PDF
        + geometría vectorial cuando existe.

    Todavía NO realiza polygonización final.

    Tampoco confirma muros.

    Su salida alimentará:

        grafo arquitectónico
        ↓
        Shapely
        ↓
        reglas Quantia.
    """

    def reconcile(
        self,
        *,
        opencv_geometry: OpenCVPlanGeometryResult,
        mapping: MappingType,
        ocr: OCRPlanTextResult | None = None,
        pdf_grounding: QuantiaGroundingResult | None = None,
        vector_probe: SpaceVectorBoundaryProbeResult | None = None,
        metric_candidates: list[MetricCandidate] | None = None,
    ) -> PlanGeometryReconciliationResult:
        self._validate_inputs(
            opencv_geometry=opencv_geometry,
            mapping=mapping,
            ocr=ocr,
        )

        axis_evidence = self._collect_axis_evidence(
            mapping=mapping,
            ocr=ocr,
            pdf_grounding=pdf_grounding,
        )

        dimension_evidence = self._collect_dimension_evidence(
            mapping=mapping,
            ocr=ocr,
            pdf_grounding=pdf_grounding,
        )

        metrics = self._collect_metrics(
            pdf_grounding=pdf_grounding,
            metric_candidates=metric_candidates,
        )

        result_spaces: list[SpaceGeometryReconciliation] = []

        for space in mapping.spaces:
            if not space.localizado or space.bbox_raster is None:
                continue

            vector_space_probe = self._find_vector_probe(
                vector_probe,
                space.id_propuesto,
            )

            boundaries = self._build_boundaries(
                bbox=space.bbox_raster,
                opencv_geometry=opencv_geometry,
                vector_probe=vector_space_probe,
                mapping=mapping,
            )

            nearby_axes = self._nearby_text(
                axis_evidence,
                space.bbox_raster,
            )

            nearby_dimensions = self._nearby_text(
                dimension_evidence,
                space.bbox_raster,
            )

            associations = self._metric_associations(
                metrics=metrics,
                space_id=space.id_propuesto,
                bbox=space.bbox_raster,
                dimension_evidence=dimension_evidence,
            )

            result_spaces.append(
                SpaceGeometryReconciliation(
                    nivel=space.nivel,
                    id_propuesto=space.id_propuesto,
                    nombre=space.nombre,
                    localization_bbox=space.bbox_raster,
                    boundaries=boundaries,
                    nearby_axes=nearby_axes,
                    nearby_dimensions=nearby_dimensions,
                    metric_associations=associations,
                    wall_geometry_confirmed=False,
                    polygon_confirmed=False,
                )
            )

        return PlanGeometryReconciliationResult(
            page=mapping.page,
            width_px=opencv_geometry.width_px,
            height_px=opencv_geometry.height_px,
            spaces=result_spaces,
            axis_evidence=axis_evidence,
            dimension_evidence=dimension_evidence,
            notes=[
                (
                    "OpenCV, Gemini, OCR y PyMuPDF "
                    "fueron llevados al mismo sistema "
                    "raster cuando estuvieron disponibles."
                ),
                (
                    "Una coincidencia numérica continúa "
                    "sin equivaler a una asociación espacial."
                ),
                (
                    "Los candidatos con soporte OpenCV "
                    "y PyMuPDF conservan ambas fuentes, "
                    "pero todavía no son muros confirmados."
                ),
                (
                    "Los ejes y cotas permanecen como "
                    "restricciones/evidencias para construir "
                    "el grafo arquitectónico."
                ),
                ("La polygonización y validación Shapely siguen pendientes."),
            ],
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        opencv_geometry: OpenCVPlanGeometryResult,
        mapping: MappingType,
        ocr: OCRPlanTextResult | None,
    ) -> None:
        if mapping.page != opencv_geometry.page:
            raise ValueError("Mapping y OpenCV pertenecen a páginas distintas.")

        if (
            mapping.image_width_px != opencv_geometry.width_px
            or mapping.image_height_px != opencv_geometry.height_px
        ):
            raise ValueError("Mapping y OpenCV no utilizan el mismo raster canónico.")

        if (
            opencv_geometry.diagnostics
            and opencv_geometry.diagnostics.parameters.deskew_applied
        ):
            raise ValueError(
                "OpenCV aplicó deskew sin restaurar "
                "las coordenadas al raster canónico. "
                "No es seguro reconciliar."
            )

        if ocr is not None:
            if (
                ocr.page != mapping.page
                or ocr.width_px != mapping.image_width_px
                or ocr.height_px != mapping.image_height_px
            ):
                raise ValueError("OCR no corresponde al mismo raster canónico.")

    # ========================================================
    # EVIDENCIA DE EJES
    # ========================================================

    def _collect_axis_evidence(
        self,
        *,
        mapping: MappingType,
        ocr: OCRPlanTextResult | None,
        pdf_grounding: QuantiaGroundingResult | None,
    ) -> list[GeometryTextEvidence]:
        result: list[GeometryTextEvidence] = []

        if ocr is not None:
            for item in ocr.axis_candidates:
                result.append(
                    self._ocr_to_evidence(
                        item,
                        kind="axis_candidate",
                    )
                )

        if pdf_grounding is not None and isinstance(
            mapping,
            SpacePDFCoordinateMapping,
        ):
            for item in pdf_grounding.axis_evidence:
                converted = self._pdf_dict_to_raster_evidence(
                    item,
                    mapping,
                    kind="axis_candidate",
                )

                if converted is not None:
                    result.append(converted)

        return result

    # ========================================================
    # EVIDENCIA DE COTAS
    # ========================================================

    def _collect_dimension_evidence(
        self,
        *,
        mapping: MappingType,
        ocr: OCRPlanTextResult | None,
        pdf_grounding: QuantiaGroundingResult | None,
    ) -> list[GeometryTextEvidence]:
        result: list[GeometryTextEvidence] = []

        if ocr is not None:
            for item in ocr.dimension_candidates:
                result.append(
                    self._ocr_to_evidence(
                        item,
                        kind="dimension_candidate",
                    )
                )

        if pdf_grounding is not None and isinstance(
            mapping,
            SpacePDFCoordinateMapping,
        ):
            for item in pdf_grounding.dimension_evidence:
                converted = self._pdf_dict_to_raster_evidence(
                    item,
                    mapping,
                    kind="dimension_candidate",
                )

                if converted is not None:
                    result.append(converted)

        return result

    # ========================================================
    # OCR → EVIDENCIA
    # ========================================================

    @staticmethod
    def _ocr_to_evidence(
        item: OCRTextItem,
        *,
        kind: str,
    ) -> GeometryTextEvidence:
        comparison_value = PlanGeometryReconciler._convert_to_meters(
            item.numeric_value,
            item.numeric_unit,
        )

        return GeometryTextEvidence(
            kind=kind,
            text=item.text,
            page=item.page,
            x=item.center_x,
            y=item.center_y,
            bbox=[
                item.x0,
                item.y0,
                item.x1,
                item.y1,
            ],
            numeric_value=item.numeric_value,
            numeric_unit=item.numeric_unit,
            comparison_value=comparison_value,
            source=item.source,
            confidence=item.confidence,
        )

    # ========================================================
    # PDF → RASTER
    # ========================================================

    @staticmethod
    def _pdf_dict_to_raster_evidence(
        item: dict[str, Any],
        mapping: SpacePDFCoordinateMapping,
        *,
        kind: str,
    ) -> GeometryTextEvidence | None:
        bbox = item.get("bbox")

        if (
            not isinstance(
                bbox,
                list,
            )
            or len(bbox) != 4
        ):
            return None

        try:
            x0 = float(bbox[0]) * mapping.diagnostics.px_per_pdf_x

            y0 = float(bbox[1]) * mapping.diagnostics.px_per_pdf_y

            x1 = float(bbox[2]) * mapping.diagnostics.px_per_pdf_x

            y1 = float(bbox[3]) * mapping.diagnostics.px_per_pdf_y

        except (
            TypeError,
            ValueError,
        ):
            return None

        return GeometryTextEvidence(
            kind=kind,
            text=str(
                item.get(
                    "text",
                    "",
                )
            ),
            page=int(
                item.get(
                    "page",
                    mapping.page,
                )
            ),
            x=(x0 + x1) / 2.0,
            y=(y0 + y1) / 2.0,
            bbox=[
                x0,
                y0,
                x1,
                y1,
            ],
            numeric_value=item.get("numeric_value"),
            numeric_unit=item.get("numeric_unit"),
            comparison_value=item.get("comparison_value"),
            source=str(
                item.get(
                    "source",
                    "pymupdf",
                )
            ),
            confidence=float(
                item.get(
                    "confidence",
                    1.0,
                )
            ),
        )

    # ========================================================
    # MÉTRICAS
    # ========================================================

    @staticmethod
    def _collect_metrics(
        *,
        pdf_grounding: QuantiaGroundingResult | None,
        metric_candidates: list[MetricCandidate] | None,
    ) -> list[GroundedMetricCandidate | MetricCandidate]:
        if pdf_grounding is not None:
            return list(pdf_grounding.metric_candidates)

        return list(metric_candidates or [])

    # ========================================================
    # BOUNDARIES
    # ========================================================

    def _build_boundaries(
        self,
        *,
        bbox: RasterBBox,
        opencv_geometry: OpenCVPlanGeometryResult,
        vector_probe: Any,
        mapping: MappingType,
    ) -> DirectionalGeometryCandidates:
        result = DirectionalGeometryCandidates()

        tolerance = 1.0

        if opencv_geometry.diagnostics is not None:
            tolerance = opencv_geometry.diagnostics.parameters.axis_tolerance_px

        for segment in opencv_geometry.vertical_segments:
            overlap = self._vertical_overlap(
                segment,
                bbox,
            )

            if overlap <= 0:
                continue

            side = "left" if segment.midpoint_x < bbox.center_x else "right"

            candidate = self._boundary_candidate(
                segment=segment,
                bbox=bbox,
                side=side,
                overlap=overlap,
                vector_probe=vector_probe,
                mapping=mapping,
                tolerance=tolerance,
            )

            getattr(
                result,
                side,
            ).append(candidate)

        for segment in opencv_geometry.horizontal_segments:
            overlap = self._horizontal_overlap(
                segment,
                bbox,
            )

            if overlap <= 0:
                continue

            side = "top" if segment.midpoint_y < bbox.center_y else "bottom"

            candidate = self._boundary_candidate(
                segment=segment,
                bbox=bbox,
                side=side,
                overlap=overlap,
                vector_probe=vector_probe,
                mapping=mapping,
                tolerance=tolerance,
            )

            getattr(
                result,
                side,
            ).append(candidate)

        for side in (
            "left",
            "right",
            "top",
            "bottom",
        ):
            items = getattr(
                result,
                side,
            )

            items.sort(
                key=lambda item: (
                    -item.support_count,
                    -item.bbox_coverage_ratio,
                    item.distance_to_bbox_edge_px,
                )
            )

        return result  # ========================================================

    # FILTRAR BANDA DE LÍMITE
    # ========================================================

    @staticmethod
    def _select_boundary_band(
        candidates: list[BoundaryCandidate],
        *,
        tolerance: float,
    ) -> list[BoundaryCandidate]:
        """
        Conserva únicamente la banda geométrica más cercana
        al borde del bbox del espacio.

        Esto evita que líneas interiores de mobiliario,
        símbolos o detalles gráficos entren automáticamente
        al grafo arquitectónico.

        No confirma muros.
        No convierte píxeles a metros.
        """

        if not candidates:
            return []

        ordered = sorted(
            candidates,
            key=lambda item: (
                item.distance_to_bbox_edge_px,
                -item.support_count,
                -item.bbox_coverage_ratio,
            ),
        )

        nearest_distance = ordered[0].distance_to_bbox_edge_px

        effective_tolerance = max(
            float(tolerance),
            0.0,
        )

        selected = [
            item
            for item in ordered
            if (item.distance_to_bbox_edge_px <= nearest_distance + effective_tolerance)
        ]

        selected.sort(
            key=lambda item: (
                -item.support_count,
                -item.bbox_coverage_ratio,
                item.distance_to_bbox_edge_px,
            )
        )

        return selected

    # ========================================================
    # CANDIDATO BOUNDARY
    # ========================================================

    def _boundary_candidate(
        self,
        *,
        segment: RasterLineSegment,
        bbox: RasterBBox,
        side: str,
        overlap: float,
        vector_probe: Any,
        mapping: MappingType,
        tolerance: float,
    ) -> BoundaryCandidate:
        if segment.orientation == "vertical":
            coverage = overlap / bbox.height if bbox.height > 0 else 0.0

            edge = bbox.x_min if side == "left" else bbox.x_max

            axis = segment.midpoint_x

            crosses_center = (
                min(
                    segment.y1,
                    segment.y2,
                )
                <= bbox.center_y
                <= max(
                    segment.y1,
                    segment.y2,
                )
            )

        else:
            coverage = overlap / bbox.width if bbox.width > 0 else 0.0

            edge = bbox.y_min if side == "top" else bbox.y_max

            axis = segment.midpoint_y

            crosses_center = (
                min(
                    segment.x1,
                    segment.x2,
                )
                <= bbox.center_x
                <= max(
                    segment.x1,
                    segment.x2,
                )
            )

        vector_matches = self._vector_support(
            segment=segment,
            vector_probe=vector_probe,
            mapping=mapping,
            tolerance=tolerance,
        )

        sources = [
            "opencv",
        ]

        if vector_matches:
            sources.append("pymupdf_vector")

        return BoundaryCandidate(
            side=side,
            orientation=segment.orientation,
            x1=segment.x1,
            y1=segment.y1,
            x2=segment.x2,
            y2=segment.y2,
            length_px=segment.length_px,
            bbox_coverage_ratio=coverage,
            distance_to_bbox_edge_px=abs(axis - edge),
            crosses_space_center=crosses_center,
            opencv_segment_id=segment.id,
            vector_support_indices=vector_matches,
            sources=sources,
            support_count=len(sources),
            confirmed=False,
        )

    # ========================================================
    # SOPORTE VECTORIAL
    # ========================================================

    def _vector_support(
        self,
        *,
        segment: RasterLineSegment,
        vector_probe: Any,
        mapping: MappingType,
        tolerance: float,
    ) -> list[int]:
        if vector_probe is None or not isinstance(
            mapping,
            SpacePDFCoordinateMapping,
        ):
            return []

        matches: list[int] = []

        for vector in vector_probe.all_intersecting_segments:
            transformed = self._vector_to_raster(
                vector,
                mapping,
            )

            if transformed is None:
                continue

            (
                orientation,
                x1,
                y1,
                x2,
                y2,
            ) = transformed

            if orientation != segment.orientation:
                continue

            if orientation == "vertical":
                vector_axis = (x1 + x2) / 2.0

                if abs(vector_axis - segment.midpoint_x) > tolerance:
                    continue

                if (
                    self._interval_overlap(
                        min(
                            y1,
                            y2,
                        ),
                        max(
                            y1,
                            y2,
                        ),
                        min(
                            segment.y1,
                            segment.y2,
                        ),
                        max(
                            segment.y1,
                            segment.y2,
                        ),
                    )
                    <= 0
                ):
                    continue

            else:
                vector_axis = (y1 + y2) / 2.0

                if abs(vector_axis - segment.midpoint_y) > tolerance:
                    continue

                if (
                    self._interval_overlap(
                        min(
                            x1,
                            x2,
                        ),
                        max(
                            x1,
                            x2,
                        ),
                        min(
                            segment.x1,
                            segment.x2,
                        ),
                        max(
                            segment.x1,
                            segment.x2,
                        ),
                    )
                    <= 0
                ):
                    continue

            matches.append(vector.index)

        return matches

    # ========================================================
    # VECTOR PDF → RASTER
    # ========================================================

    @staticmethod
    def _vector_to_raster(
        vector: VectorSegmentCandidate,
        mapping: SpacePDFCoordinateMapping,
    ) -> (
        tuple[
            str,
            float,
            float,
            float,
            float,
        ]
        | None
    ):
        if vector.orientation not in {
            "horizontal",
            "vertical",
        }:
            return None

        return (
            vector.orientation,
            vector.x1 * mapping.diagnostics.px_per_pdf_x,
            vector.y1 * mapping.diagnostics.px_per_pdf_y,
            vector.x2 * mapping.diagnostics.px_per_pdf_x,
            vector.y2 * mapping.diagnostics.px_per_pdf_y,
        )

    # ========================================================
    # VECTOR PROBE POR ESPACIO
    # ========================================================

    @staticmethod
    def _find_vector_probe(
        result: SpaceVectorBoundaryProbeResult | None,
        space_id: str,
    ) -> Any:
        if result is None:
            return None

        for item in result.spaces:
            if item.id_propuesto == space_id:
                return item

        return None

    # ========================================================
    # TEXTO CERCANO
    # ========================================================

    def _nearby_text(
        self,
        evidence: list[GeometryTextEvidence],
        bbox: RasterBBox,
    ) -> list[NearbyTextEvidence]:
        result: list[NearbyTextEvidence] = []

        for item in evidence:
            distance = self._point_bbox_distance(
                item.x,
                item.y,
                bbox,
            )

            result.append(
                NearbyTextEvidence(
                    kind=item.kind,
                    text=item.text,
                    source=item.source,
                    x=item.x,
                    y=item.y,
                    distance_to_space_bbox_px=distance,
                    relative_position=self._relative_position(
                        item.x,
                        item.y,
                        bbox,
                    ),
                    numeric_value=item.comparison_value,
                )
            )

        result.sort(key=lambda item: item.distance_to_space_bbox_px)

        return result

    # ========================================================
    # ASOCIACIONES MÉTRICAS
    # ========================================================

    def _metric_associations(
        self,
        *,
        metrics: list[Any],
        space_id: str,
        bbox: RasterBBox,
        dimension_evidence: list[GeometryTextEvidence],
    ) -> list[MetricSpatialCandidate]:
        result: list[MetricSpatialCandidate] = []

        for metric in metrics:
            if not self._belongs_to_space(
                metric.element_id,
                space_id,
            ):
                continue

            field = str(metric.field)

            metric_kind = getattr(
                metric,
                "metric_kind",
                self._metric_kind(field),
            )

            source = getattr(
                metric,
                "model_source",
                getattr(
                    metric,
                    "source",
                    "gemini_vision",
                ),
            )

            if metric_kind != "linear":
                result.append(
                    MetricSpatialCandidate(
                        element_type=metric.element_type,
                        element_id=metric.element_id,
                        field=field,
                        value=metric.value,
                        metric_kind=metric_kind,
                        evidence_source=source,
                        matched_text=None,
                        matched_text_source=None,
                        matched_value=None,
                        matched_bbox=None,
                        distance_to_space_bbox_px=None,
                        inside_space_bbox=False,
                        association_validated=False,
                    )
                )

                continue

            matches = [
                evidence
                for evidence in dimension_evidence
                if (
                    evidence.comparison_value is not None
                    and math.isclose(
                        evidence.comparison_value,
                        float(metric.value),
                        rel_tol=0.0,
                        abs_tol=1e-6,
                    )
                )
            ]

            if not matches:
                result.append(
                    MetricSpatialCandidate(
                        element_type=metric.element_type,
                        element_id=metric.element_id,
                        field=field,
                        value=metric.value,
                        metric_kind=metric_kind,
                        evidence_source=source,
                        matched_text=None,
                        matched_text_source=None,
                        matched_value=None,
                        matched_bbox=None,
                        distance_to_space_bbox_px=None,
                        inside_space_bbox=False,
                        association_validated=False,
                    )
                )

                continue

            for evidence in matches:
                distance = self._point_bbox_distance(
                    evidence.x,
                    evidence.y,
                    bbox,
                )

                result.append(
                    MetricSpatialCandidate(
                        element_type=metric.element_type,
                        element_id=metric.element_id,
                        field=field,
                        value=metric.value,
                        metric_kind=metric_kind,
                        evidence_source=source,
                        matched_text=evidence.text,
                        matched_text_source=evidence.source,
                        matched_value=evidence.comparison_value,
                        matched_bbox=evidence.bbox,
                        distance_to_space_bbox_px=distance,
                        inside_space_bbox=distance == 0.0,
                        association_validated=False,
                    )
                )

        result.sort(
            key=lambda item: (
                item.distance_to_space_bbox_px
                if item.distance_to_space_bbox_px is not None
                else float("inf")
            )
        )

        return result

    # ========================================================
    # HELPERS GEOMÉTRICOS
    # ========================================================

    @staticmethod
    def _vertical_overlap(
        segment: RasterLineSegment,
        bbox: RasterBBox,
    ) -> float:
        x = segment.midpoint_x

        if not (bbox.x_min <= x <= bbox.x_max):
            return 0.0

        return PlanGeometryReconciler._interval_overlap(
            min(
                segment.y1,
                segment.y2,
            ),
            max(
                segment.y1,
                segment.y2,
            ),
            bbox.y_min,
            bbox.y_max,
        )

    @staticmethod
    def _horizontal_overlap(
        segment: RasterLineSegment,
        bbox: RasterBBox,
    ) -> float:
        y = segment.midpoint_y

        if not (bbox.y_min <= y <= bbox.y_max):
            return 0.0

        return PlanGeometryReconciler._interval_overlap(
            min(
                segment.x1,
                segment.x2,
            ),
            max(
                segment.x1,
                segment.x2,
            ),
            bbox.x_min,
            bbox.x_max,
        )

    @staticmethod
    def _interval_overlap(
        a0: float,
        a1: float,
        b0: float,
        b1: float,
    ) -> float:
        return max(
            0.0,
            min(
                a1,
                b1,
            )
            - max(
                a0,
                b0,
            ),
        )

    @staticmethod
    def _point_bbox_distance(
        x: float,
        y: float,
        bbox: RasterBBox,
    ) -> float:
        dx = max(
            bbox.x_min - x,
            0.0,
            x - bbox.x_max,
        )

        dy = max(
            bbox.y_min - y,
            0.0,
            y - bbox.y_max,
        )

        return math.hypot(
            dx,
            dy,
        )

    @staticmethod
    def _relative_position(
        x: float,
        y: float,
        bbox: RasterBBox,
    ) -> str:
        if bbox.x_min <= x <= bbox.x_max and bbox.y_min <= y <= bbox.y_max:
            return "inside"

        candidates = {
            "left": abs(x - bbox.x_min),
            "right": abs(x - bbox.x_max),
            "top": abs(y - bbox.y_min),
            "bottom": abs(y - bbox.y_max),
        }

        return min(
            candidates,
            key=candidates.get,
        )

    @staticmethod
    def _belongs_to_space(
        element_id: str,
        space_id: str,
    ) -> bool:
        element = str(element_id)

        return element == space_id or element.startswith(f"{space_id}_")

    @staticmethod
    def _metric_kind(
        field: str,
    ) -> str:
        normalized = str(field or "").lower()

        if normalized.endswith("_m2"):
            return "area"

        if normalized.endswith("_m"):
            return "linear"

        return "unknown"

    @staticmethod
    def _convert_to_meters(
        value: float | None,
        unit: str | None,
    ) -> float | None:
        if value is None:
            return None

        if unit is None:
            return float(value)

        normalized = str(unit).lower()

        if normalized == "m":
            return float(value)

        if normalized == "cm":
            return float(value) / 100.0

        if normalized == "mm":
            return float(value) / 1000.0

        return None


# ============================================================
# FACTORY
# ============================================================


def get_plan_geometry_reconciler() -> PlanGeometryReconciler:
    return PlanGeometryReconciler()
