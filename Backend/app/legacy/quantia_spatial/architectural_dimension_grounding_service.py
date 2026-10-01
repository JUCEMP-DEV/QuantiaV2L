from __future__ import annotations

import math
import statistics
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
    RasterLineSegment,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    BoundaryCandidate,
    GeometryTextEvidence,
    PlanGeometryReconciliationResult,
    SpaceGeometryReconciliation,
)

# ============================================================
# EJE ARQUITECTÓNICO CANDIDATO
# ============================================================


@dataclass(slots=True)
class AxisAnchorCandidate:
    """
    Eje identificado mediante:

        etiqueta OCR/PyMuPDF
        +
        alineación con línea OpenCV

    Ejemplo:

        etiqueta C
            +
        línea vertical x=842
            ↓
        eje C candidato

    Todavía:

        confirmed = False
    """

    id: str

    label: str
    normalized_label: str

    orientation: str

    coordinate_px: float

    supporting_segment_ids: list[str] = field(default_factory=list)

    evidence_sources: list[str] = field(default_factory=list)

    evidence_bboxes: list[list[float]] = field(default_factory=list)

    confidence: float = 0.0

    ambiguous_orientation: bool = False

    confirmed: bool = False


# ============================================================
# COTA ASOCIADA A TRAMO ENTRE EJES
# ============================================================


@dataclass(slots=True)
class AxisDimensionEvidence:
    text: str

    value_m: float

    numeric_unit: str | None

    unit_explicit: bool

    source: str

    confidence: float

    x: float
    y: float

    bbox: list[float]


# ============================================================
# TRAMO ENTRE EJES
# ============================================================


@dataclass(slots=True)
class AxisSpanGrounding:
    """
    Tramo entre dos ejes consecutivos.

    Ejemplo:

        C ───── D
           2.60

    orientation:
        orientación de los ejes.

    measurement_direction:
        dirección de la dimensión medida.
    """

    id: str

    space_id: str
    level: str

    orientation: str
    measurement_direction: str

    start_axis_id: str
    start_axis_label: str
    start_coordinate_px: float

    end_axis_id: str
    end_axis_label: str
    end_coordinate_px: float

    pixel_span: float

    value_m: float | None

    pixels_per_meter: float | None

    dimension_evidence: list[AxisDimensionEvidence] = field(default_factory=list)

    distinct_values_m: list[float] = field(default_factory=list)

    unit_explicit: bool = False

    state: str = "NO_IDENTIFICADO"

    confirmed: bool = False


# ============================================================
# DIMENSIÓN RESUELTA DE ESPACIO
# ============================================================


@dataclass(slots=True)
class ResolvedSpaceDimension:
    """
    Dimensión espacial derivada de:

        límite geométrico
        +
        ejes
        +
        cotas

    No depende de que Gemini haya propuesto el mismo valor.

    dimension_axis:

        x → dimensión horizontal
        y → dimensión vertical
    """

    id: str

    space_id: str
    level: str
    space_name: str

    dimension_axis: str

    value_m: float

    pixel_span: float

    pixels_per_meter: float

    start_axis_label: str
    end_axis_label: str

    component_span_ids: list[str] = field(default_factory=list)

    evidence_sources: list[str] = field(default_factory=list)

    unit_explicit: bool = False

    model_values: list[float] = field(default_factory=list)

    matching_model_fields: list[str] = field(default_factory=list)

    conflicting_model_values: list[float] = field(default_factory=list)

    model_agreement: bool = False

    model_conflict: bool = False

    state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# ESPACIO NO RESUELTO
# ============================================================


@dataclass(slots=True)
class UnresolvedSpaceDimension:
    space_id: str

    level: str

    dimension_axis: str

    reason: str


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class ArchitecturalDimensionGroundingResult:
    page: int

    width_px: int
    height_px: int

    axis_anchors: list[AxisAnchorCandidate] = field(default_factory=list)

    axis_spans: list[AxisSpanGrounding] = field(default_factory=list)

    resolved_space_dimensions: list[ResolvedSpaceDimension] = field(
        default_factory=list
    )

    unresolved_space_dimensions: list[UnresolvedSpaceDimension] = field(
        default_factory=list
    )

    unresolved_axis_labels: list[dict[str, Any]] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# SERVICIO
# ============================================================


class ArchitecturalDimensionGroundingService:
    """
    Grounding métrico mediante ejes y cotas.

    ==========================================================
    OBJETIVO
    ==========================================================

    Convertir:

        "2.60 existe"

    en:

        "C → D mide 2.60"

    y después, cuando los límites del espacio corresponden
    a esos ejes:

        "la dimensión X/Y del espacio es 2.60 m"

    ==========================================================
    PRIORIDAD
    ==========================================================

    La métrica se resuelve usando:

        geometría
        + ejes
        + cotas

    Gemini participa después como:

        acuerdo
        o
        conflicto

    Nunca como autoridad métrica primaria.

    ==========================================================
    REGLAS
    ==========================================================

    1. Una letra/número OCR no es eje automáticamente.

    2. Una etiqueta de eje debe tener soporte geométrico
       alineado en OpenCV.

    3. Dos ejes consecutivos forman un tramo candidato.

    4. Una cota solo pertenece al tramo cuando su posición
       se encuentra entre ambos ejes.

    5. Si distintas cotas asignables al mismo tramo muestran
       valores diferentes:

           CONFLICTO

    6. Un espacio solo obtiene dimensión resuelta si sus
       límites geométricos seleccionados corresponden a
       los ejes extremos de una cadena válida.

    7. Si Gemini contradice esa dimensión:

           la dimensión geométrica se conserva
           +
           state = CONFLICTO

    8. confirmed siempre permanece False.
    """

    NUMERIC_TOLERANCE = 1e-6

    # ========================================================
    # API
    # ========================================================

    def ground(
        self,
        *,
        reconciliation: PlanGeometryReconciliationResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> ArchitecturalDimensionGroundingResult:
        self._validate_inputs(
            reconciliation=reconciliation,
            opencv_geometry=opencv_geometry,
        )

        coordinate_tolerance = self._coordinate_tolerance(opencv_geometry)

        segment_lookup = self._segment_lookup(opencv_geometry)

        # ====================================================
        # EJES
        # ====================================================

        (
            axis_anchors,
            unresolved_axis_labels,
        ) = self._build_axis_anchors(
            evidence=reconciliation.axis_evidence,
            geometry=opencv_geometry,
            tolerance=coordinate_tolerance,
        )

        # ====================================================
        # EVITAR QUE ETIQUETAS DE EJE NUMÉRICAS SE UTILICEN
        # TAMBIÉN COMO COTAS
        # ====================================================

        dimension_evidence = self._remove_axis_labels_from_dimensions(
            dimensions=reconciliation.dimension_evidence,
            axes=reconciliation.axis_evidence,
            tolerance=coordinate_tolerance,
        )

        axis_spans: list[AxisSpanGrounding] = []

        resolved_dimensions: list[ResolvedSpaceDimension] = []

        unresolved_dimensions: list[UnresolvedSpaceDimension] = []

        span_counter = 0
        dimension_counter = 0

        # ====================================================
        # ESPACIOS
        # ====================================================

        for space in reconciliation.spaces:
            # ------------------------------------------------
            # DIMENSIÓN X
            # ------------------------------------------------

            (
                x_spans,
                x_dimension,
                x_reason,
            ) = self._resolve_space_axis_dimension(
                space=space,
                orientation="vertical",
                dimension_axis="x",
                axis_anchors=axis_anchors,
                dimension_evidence=dimension_evidence,
                segment_lookup=segment_lookup,
                tolerance=coordinate_tolerance,
                span_counter_start=span_counter,
            )

            span_counter += len(x_spans)

            axis_spans.extend(x_spans)

            if x_dimension is not None:
                dimension_counter += 1

                x_dimension.id = f"SPACE_DIM_{dimension_counter}"

                self._compare_with_model(
                    resolved=x_dimension,
                    space=space,
                )

                resolved_dimensions.append(x_dimension)

            else:
                unresolved_dimensions.append(
                    UnresolvedSpaceDimension(
                        space_id=space.id_propuesto,
                        level=space.nivel,
                        dimension_axis="x",
                        reason=x_reason,
                    )
                )

            # ------------------------------------------------
            # DIMENSIÓN Y
            # ------------------------------------------------

            (
                y_spans,
                y_dimension,
                y_reason,
            ) = self._resolve_space_axis_dimension(
                space=space,
                orientation="horizontal",
                dimension_axis="y",
                axis_anchors=axis_anchors,
                dimension_evidence=dimension_evidence,
                segment_lookup=segment_lookup,
                tolerance=coordinate_tolerance,
                span_counter_start=span_counter,
            )

            span_counter += len(y_spans)

            axis_spans.extend(y_spans)

            if y_dimension is not None:
                dimension_counter += 1

                y_dimension.id = f"SPACE_DIM_{dimension_counter}"

                self._compare_with_model(
                    resolved=y_dimension,
                    space=space,
                )

                resolved_dimensions.append(y_dimension)

            else:
                unresolved_dimensions.append(
                    UnresolvedSpaceDimension(
                        space_id=space.id_propuesto,
                        level=space.nivel,
                        dimension_axis="y",
                        reason=y_reason,
                    )
                )

        return ArchitecturalDimensionGroundingResult(
            page=reconciliation.page,
            width_px=reconciliation.width_px,
            height_px=reconciliation.height_px,
            axis_anchors=axis_anchors,
            axis_spans=axis_spans,
            resolved_space_dimensions=resolved_dimensions,
            unresolved_space_dimensions=unresolved_dimensions,
            unresolved_axis_labels=unresolved_axis_labels,
            notes=[
                (
                    "Los ejes requieren simultáneamente "
                    "etiqueta textual y soporte geométrico."
                ),
                (
                    "Las cotas fueron asociadas únicamente "
                    "a tramos entre ejes por posición."
                ),
                (
                    "Las cadenas dimensionales se construyen "
                    "sumando únicamente tramos consecutivos "
                    "sin conflicto."
                ),
                (
                    "Las dimensiones espaciales resueltas "
                    "proceden de límites + ejes + cotas."
                ),
                (
                    "Los valores Gemini se utilizaron "
                    "después para detectar acuerdo o conflicto."
                ),
                ("Ninguna dimensión tiene confirmed=true."),
            ],
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        reconciliation: PlanGeometryReconciliationResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> None:
        if reconciliation.page != opencv_geometry.page:
            raise ValueError(
                "Reconciliación y OpenCV pertenecen " "a páginas distintas."
            )

        if (
            reconciliation.width_px != opencv_geometry.width_px
            or reconciliation.height_px != opencv_geometry.height_px
        ):
            raise ValueError(
                "Reconciliación y OpenCV no utilizan " "el mismo raster canónico."
            )

    # ========================================================
    # TOLERANCIA
    # ========================================================

    @staticmethod
    def _coordinate_tolerance(
        geometry: OpenCVPlanGeometryResult,
    ) -> float:
        if geometry.diagnostics is not None:
            value = geometry.diagnostics.parameters.axis_tolerance_px

            if value > 0:
                return float(value)

        return 1.0

    # ========================================================
    # LOOKUP SEGMENTOS
    # ========================================================

    @staticmethod
    def _segment_lookup(
        geometry: OpenCVPlanGeometryResult,
    ) -> dict[
        str,
        RasterLineSegment,
    ]:
        result: dict[
            str,
            RasterLineSegment,
        ] = {}

        for segment in (
            geometry.horizontal_segments
            + geometry.vertical_segments
            + geometry.other_segments
        ):
            result[segment.id] = segment

        return result

    # ========================================================
    # CONSTRUIR EJES
    # ========================================================

    def _build_axis_anchors(
        self,
        *,
        evidence: list[GeometryTextEvidence],
        geometry: OpenCVPlanGeometryResult,
        tolerance: float,
    ) -> tuple[
        list[AxisAnchorCandidate],
        list[dict[str, Any]],
    ]:
        raw: list[AxisAnchorCandidate] = []

        unresolved: list[dict[str, Any]] = []

        counter = 0

        for item in evidence:
            label = str(item.text or "").strip()

            if not label:
                continue

            bbox_width = abs(item.bbox[2] - item.bbox[0])

            bbox_height = abs(item.bbox[3] - item.bbox[1])

            x_tolerance = max(
                tolerance,
                tolerance + bbox_width,
            )

            y_tolerance = max(
                tolerance,
                bbox_height / 2.0,
            )

            vertical_matches = self._aligned_vertical_segments(
                x=item.x,
                segments=geometry.vertical_segments,
                tolerance=x_tolerance,
            )

            horizontal_matches = self._aligned_horizontal_segments(
                y=item.y,
                segments=geometry.horizontal_segments,
                tolerance=y_tolerance,
            )

            if not vertical_matches and not horizontal_matches:
                unresolved.append(
                    {
                        "text": item.text,
                        "source": item.source,
                        "bbox": list(item.bbox),
                        "reason": (
                            "La etiqueta no pudo "
                            "alinearse con ninguna línea "
                            "horizontal o vertical OpenCV."
                        ),
                    }
                )

                continue

            ambiguous = bool(vertical_matches and horizontal_matches)

            if vertical_matches:
                selected = self._nearest_vertical_group(
                    item.x,
                    vertical_matches,
                    tolerance,
                )

                counter += 1

                raw.append(
                    AxisAnchorCandidate(
                        id=f"AXIS_RAW_{counter}",
                        label=label,
                        normalized_label=self._normalize_label(label),
                        orientation="vertical",
                        coordinate_px=statistics.median(
                            [segment.midpoint_x for segment in selected]
                        ),
                        supporting_segment_ids=[segment.id for segment in selected],
                        evidence_sources=[item.source],
                        evidence_bboxes=[list(item.bbox)],
                        confidence=item.confidence,
                        ambiguous_orientation=ambiguous,
                        confirmed=False,
                    )
                )

            if horizontal_matches:
                selected = self._nearest_horizontal_group(
                    item.y,
                    horizontal_matches,
                    tolerance,
                )

                counter += 1

                raw.append(
                    AxisAnchorCandidate(
                        id=f"AXIS_RAW_{counter}",
                        label=label,
                        normalized_label=self._normalize_label(label),
                        orientation="horizontal",
                        coordinate_px=statistics.median(
                            [segment.midpoint_y for segment in selected]
                        ),
                        supporting_segment_ids=[segment.id for segment in selected],
                        evidence_sources=[item.source],
                        evidence_bboxes=[list(item.bbox)],
                        confidence=item.confidence,
                        ambiguous_orientation=ambiguous,
                        confirmed=False,
                    )
                )

        return (
            self._merge_axis_anchors(
                raw,
                tolerance=tolerance,
            ),
            unresolved,
        )

    # ========================================================
    # SEGMENTOS ALINEADOS
    # ========================================================

    @staticmethod
    def _aligned_vertical_segments(
        *,
        x: float,
        segments: list[RasterLineSegment],
        tolerance: float,
    ) -> list[RasterLineSegment]:
        return [
            segment for segment in segments if abs(segment.midpoint_x - x) <= tolerance
        ]

    @staticmethod
    def _aligned_horizontal_segments(
        *,
        y: float,
        segments: list[RasterLineSegment],
        tolerance: float,
    ) -> list[RasterLineSegment]:
        return [
            segment for segment in segments if abs(segment.midpoint_y - y) <= tolerance
        ]

    # ========================================================
    # GRUPO MÁS CERCANO
    # ========================================================

    @staticmethod
    def _nearest_vertical_group(
        x: float,
        segments: list[RasterLineSegment],
        tolerance: float,
    ) -> list[RasterLineSegment]:
        minimum = min(abs(segment.midpoint_x - x) for segment in segments)

        return [
            segment
            for segment in segments
            if abs(segment.midpoint_x - x) <= minimum + tolerance
        ]

    @staticmethod
    def _nearest_horizontal_group(
        y: float,
        segments: list[RasterLineSegment],
        tolerance: float,
    ) -> list[RasterLineSegment]:
        minimum = min(abs(segment.midpoint_y - y) for segment in segments)

        return [
            segment
            for segment in segments
            if abs(segment.midpoint_y - y) <= minimum + tolerance
        ]

    # ========================================================
    # MERGE EJES DUPLICADOS
    # ========================================================

    def _merge_axis_anchors(
        self,
        anchors: list[AxisAnchorCandidate],
        *,
        tolerance: float,
    ) -> list[AxisAnchorCandidate]:
        result: list[AxisAnchorCandidate] = []

        for anchor in anchors:
            existing = None

            for candidate in result:
                if candidate.orientation != anchor.orientation:
                    continue

                if candidate.normalized_label != anchor.normalized_label:
                    continue

                if abs(candidate.coordinate_px - anchor.coordinate_px) > tolerance:
                    continue

                existing = candidate

                break

            if existing is None:
                result.append(anchor)

                continue

            coordinates = [
                existing.coordinate_px,
                anchor.coordinate_px,
            ]

            existing.coordinate_px = statistics.median(coordinates)

            for segment_id in anchor.supporting_segment_ids:
                if segment_id not in existing.supporting_segment_ids:
                    existing.supporting_segment_ids.append(segment_id)

            for source in anchor.evidence_sources:
                if source not in existing.evidence_sources:
                    existing.evidence_sources.append(source)

            existing.confidence = max(
                existing.confidence,
                anchor.confidence,
            )

            existing.ambiguous_orientation = (
                existing.ambiguous_orientation or anchor.ambiguous_orientation
            )

        for index, anchor in enumerate(
            result,
            start=1,
        ):
            anchor.id = f"AXIS_{index}"

            anchor.supporting_segment_ids.sort()

            anchor.evidence_sources.sort()

        return result

    # ========================================================
    # QUITAR LABELS DE EJE DE LAS COTAS
    # ========================================================

    def _remove_axis_labels_from_dimensions(
        self,
        *,
        dimensions: list[GeometryTextEvidence],
        axes: list[GeometryTextEvidence],
        tolerance: float,
    ) -> list[GeometryTextEvidence]:
        result: list[GeometryTextEvidence] = []

        for dimension in dimensions:
            duplicated_axis = False

            for axis in axes:
                if dimension.source != axis.source:
                    continue

                if self._normalize_label(dimension.text) != self._normalize_label(
                    axis.text
                ):
                    continue

                if (
                    math.hypot(
                        dimension.x - axis.x,
                        dimension.y - axis.y,
                    )
                    <= tolerance
                ):
                    duplicated_axis = True

                    break

            if not duplicated_axis:
                result.append(dimension)

        return result

    # ========================================================
    # RESOLVER DIMENSIÓN DEL ESPACIO
    # ========================================================

    def _resolve_space_axis_dimension(
        self,
        *,
        space: SpaceGeometryReconciliation,
        orientation: str,
        dimension_axis: str,
        axis_anchors: list[AxisAnchorCandidate],
        dimension_evidence: list[GeometryTextEvidence],
        segment_lookup: dict[str, RasterLineSegment],
        tolerance: float,
        span_counter_start: int,
    ) -> tuple[
        list[AxisSpanGrounding],
        ResolvedSpaceDimension | None,
        str,
    ]:
        orientation_axes = [
            axis
            for axis in axis_anchors
            if (
                axis.orientation == orientation
                and not axis.ambiguous_orientation
            )
        ]

        orientation_axes = self._axes_for_space_chain(
            axes=orientation_axes,
            space=space,
            orientation=orientation,
            tolerance=tolerance,
        )

        local_axes = [
            axis
            for axis in orientation_axes
            if self._axis_reaches_space(
                    axis=axis,
                    space=space,
                    segment_lookup=segment_lookup,
                    tolerance=tolerance,
                )
        ]

        local_axes.sort(key=lambda axis: axis.coordinate_px)

        if len(local_axes) < 2:
            return (
                [],
                None,
                (
                    "No existen al menos dos ejes "
                    "geométricamente asociados al espacio."
                ),
            )

        # ----------------------------------------------------
        # LÍMITES GEOMÉTRICOS PREFERENTES
        # ----------------------------------------------------

        first_boundary, second_boundary = self._space_boundary_pair(
            space=space,
            orientation=orientation,
        )

        if first_boundary is None or second_boundary is None:
            return (
                [],
                None,
                (
                    "No existen límites geométricos "
                    "opuestos suficientes para asociar "
                    "la dimensión a ejes."
                ),
            )

        first_coordinate = self._boundary_coordinate(
            first_boundary,
            orientation,
        )

        second_coordinate = self._boundary_coordinate(
            second_boundary,
            orientation,
        )

        start_axis = min(
            local_axes,
            key=lambda axis: abs(axis.coordinate_px - first_coordinate),
        )

        end_axis = min(
            local_axes,
            key=lambda axis: abs(axis.coordinate_px - second_coordinate),
        )

        if start_axis.id == end_axis.id:
            return (
                [],
                None,
                ("Ambos límites del espacio se " "asociaron al mismo eje."),
            )

        start_index = local_axes.index(start_axis)

        end_index = local_axes.index(end_axis)

        if start_index > end_index:
            start_index, end_index = (
                end_index,
                start_index,
            )

            start_axis, end_axis = (
                end_axis,
                start_axis,
            )

        if end_index - start_index < 1:
            return (
                [],
                None,
                ("No existe tramo dimensional " "entre los ejes asociados."),
            )

        # Una asociación semántica de una cota solo puede
        # resolver por sí sola el tamaño del recinto cuando
        # sus dos límites físicos corresponden a ese único
        # tramo. Si el recinto abarca varios tramos, se debe
        # conservar y sumar la cadena completa entre ejes.
        if end_index - start_index == 1:
            corroborated = self._resolve_corroborated_axis_span(
                space=space,
                local_axes=[start_axis, end_axis],
                orientation=orientation,
                dimension_axis=dimension_axis,
                dimension_evidence=dimension_evidence,
                tolerance=tolerance,
                span_counter_start=span_counter_start,
            )

            if corroborated is not None:
                return corroborated

        # ----------------------------------------------------
        # TRAMOS CONSECUTIVOS
        # ----------------------------------------------------

        spans: list[AxisSpanGrounding] = []

        for index in range(
            start_index,
            end_index,
        ):
            first_axis = local_axes[index]

            second_axis = local_axes[index + 1]

            span_id = f"AXIS_SPAN_" f"{span_counter_start + len(spans) + 1}"

            spans.append(
                self._ground_axis_span(
                    span_id=span_id,
                    space=space,
                    start_axis=first_axis,
                    end_axis=second_axis,
                    orientation=orientation,
                    dimension_evidence=dimension_evidence,
                    tolerance=tolerance,
                )
            )

        # ----------------------------------------------------
        # LA CADENA SOLO ES VÁLIDA SI TODOS LOS TRAMOS
        # ESTÁN RESUELTOS SIN CONFLICTO
        # ----------------------------------------------------

        invalid = [
            span for span in spans if span.state != "DETECTADO" or span.value_m is None
        ]

        if invalid:
            if any(span.state == "CONFLICTO" for span in invalid):
                reason = "La cadena entre ejes contiene " "cotas contradictorias."

            else:
                reason = (
                    "La cadena entre ejes contiene " "tramos sin cota identificable."
                )

            return (
                spans,
                None,
                reason,
            )

        total_value = sum(span.value_m for span in spans if span.value_m is not None)

        pixel_span = abs(end_axis.coordinate_px - start_axis.coordinate_px)

        if total_value <= 0 or pixel_span <= 0:
            return (
                spans,
                None,
                ("La cadena dimensional produjo " "una magnitud inválida."),
            )

        sources = sorted(
            {evidence.source for span in spans for evidence in span.dimension_evidence}
        )

        unit_explicit = all(span.unit_explicit for span in spans)

        resolved = ResolvedSpaceDimension(
            id="",
            space_id=space.id_propuesto,
            level=space.nivel,
            space_name=space.nombre,
            dimension_axis=dimension_axis,
            value_m=total_value,
            pixel_span=pixel_span,
            pixels_per_meter=(pixel_span / total_value),
            start_axis_label=start_axis.label,
            end_axis_label=end_axis.label,
            component_span_ids=[span.id for span in spans],
            evidence_sources=sources,
            unit_explicit=unit_explicit,
            state="DETECTADO",
            confirmed=False,
        )

        return (
            spans,
            resolved,
            "",
        )

    # ========================================================
    # TRAMO CORROBORADO POR EVIDENCIA EXPLICITA
    # ========================================================

    def _resolve_corroborated_axis_span(
        self,
        *,
        space: SpaceGeometryReconciliation,
        local_axes: list[AxisAnchorCandidate],
        orientation: str,
        dimension_axis: str,
        dimension_evidence: list[GeometryTextEvidence],
        tolerance: float,
        span_counter_start: int,
    ) -> tuple[
        list[AxisSpanGrounding],
        ResolvedSpaceDimension,
        str,
    ] | None:
        associations = sorted(
            (
                association
                for association in space.metric_associations
                if association.element_type == "espacio"
                and association.element_id == space.id_propuesto
                and association.metric_kind == "linear"
                and association.matched_text
                and association.matched_value is not None
                and association.matched_bbox
            ),
            key=lambda association: (
                float(association.distance_to_space_bbox_px)
                if association.distance_to_space_bbox_px is not None
                else float("inf")
            ),
        )

        for association in associations:
            matched_bbox = list(association.matched_bbox or [])

            for evidence in dimension_evidence:
                if evidence.comparison_value is None:
                    continue

                if not math.isclose(
                    float(evidence.comparison_value),
                    float(association.matched_value),
                    rel_tol=0.0,
                    abs_tol=self.NUMERIC_TOLERANCE,
                ):
                    continue

                if self._normalize_label(evidence.text) != self._normalize_label(
                    association.matched_text
                ):
                    continue

                evidence_bbox = list(evidence.bbox)

                if len(matched_bbox) < 4 or len(evidence_bbox) < 4:
                    continue

                if max(
                    abs(float(first) - float(second))
                    for first, second in zip(matched_bbox, evidence_bbox)
                ) > tolerance:
                    continue

                measurement_coordinate = (
                    evidence.x if orientation == "vertical" else evidence.y
                )

                for index in range(len(local_axes) - 1):
                    start_axis = local_axes[index]
                    end_axis = local_axes[index + 1]
                    start_coordinate = min(
                        start_axis.coordinate_px,
                        end_axis.coordinate_px,
                    )
                    end_coordinate = max(
                        start_axis.coordinate_px,
                        end_axis.coordinate_px,
                    )

                    if not (
                        start_coordinate - tolerance
                        <= measurement_coordinate
                        <= end_coordinate + tolerance
                    ):
                        continue

                    span = self._ground_axis_span(
                        span_id=f"AXIS_SPAN_{span_counter_start + 1}",
                        space=space,
                        start_axis=start_axis,
                        end_axis=end_axis,
                        orientation=orientation,
                        dimension_evidence=dimension_evidence,
                        tolerance=tolerance,
                    )

                    if span.state != "DETECTADO" or span.value_m is None:
                        continue

                    if not math.isclose(
                        span.value_m,
                        float(association.matched_value),
                        rel_tol=0.0,
                        abs_tol=self.NUMERIC_TOLERANCE,
                    ):
                        continue

                    resolved = ResolvedSpaceDimension(
                        id="",
                        space_id=space.id_propuesto,
                        level=space.nivel,
                        space_name=space.nombre,
                        dimension_axis=dimension_axis,
                        value_m=span.value_m,
                        pixel_span=span.pixel_span,
                        pixels_per_meter=(span.pixel_span / span.value_m),
                        start_axis_label=span.start_axis_label,
                        end_axis_label=span.end_axis_label,
                        component_span_ids=[span.id],
                        evidence_sources=sorted(
                            {item.source for item in span.dimension_evidence}
                        ),
                        unit_explicit=span.unit_explicit,
                        state="INFERIDO",
                        confirmed=False,
                    )

                    return [span], resolved, ""

        return None

    # ========================================================
    # GROUNDING DE TRAMO
    # ========================================================

    def _ground_axis_span(
        self,
        *,
        span_id: str,
        space: SpaceGeometryReconciliation,
        start_axis: AxisAnchorCandidate,
        end_axis: AxisAnchorCandidate,
        orientation: str,
        dimension_evidence: list[
            GeometryTextEvidence
        ],
        tolerance: float,
    ) -> AxisSpanGrounding:
        start_coordinate = min(
            start_axis.coordinate_px,
            end_axis.coordinate_px,
        )

        end_coordinate = max(
            start_axis.coordinate_px,
            end_axis.coordinate_px,
        )

        # ----------------------------------------------------
        # BANDA ORTOGONAL DEL ESPACIO
        # ----------------------------------------------------
        #
        # No basta con que una cifra esté entre dos ejes.
        # También debe pertenecer espacialmente a la banda
        # perpendicular del espacio que estamos resolviendo.
        #
        # Esto evita que cotas de otra cadena gráfica entren
        # en conflicto con el tramo actual.
        # ----------------------------------------------------

        orthogonal_start: float | None = None
        orthogonal_end: float | None = None
        label_intervals = self._axis_label_intervals(
            axes=[start_axis, end_axis],
            orientation=orientation,
        )

        if label_intervals:
            orthogonal_start = min(item[0] for item in label_intervals)
            orthogonal_end = max(item[1] for item in label_intervals)

        chain_tolerance = tolerance * 12.0

        evidence_items: list[
            AxisDimensionEvidence
        ] = []

        for evidence in dimension_evidence:
            if (
                evidence.comparison_value is None
                or evidence.comparison_value <= 0
            ):
                continue

            # ------------------------------------------------
            # COORDENADA PRINCIPAL DEL TRAMO
            # ------------------------------------------------

            if orientation == "vertical":
                measurement_coordinate = evidence.x
            else:
                measurement_coordinate = evidence.y

            if not (
                start_coordinate - self.NUMERIC_TOLERANCE
                <= measurement_coordinate
                <= end_coordinate + self.NUMERIC_TOLERANCE
            ):
                continue

            # ------------------------------------------------
            # FILTRO ORTOGONAL
            # ------------------------------------------------

            if (
                orthogonal_start is not None
                and orthogonal_end is not None
            ):
                bbox = list(
                    evidence.bbox
                )

                if len(bbox) >= 4:
                    if orientation == "vertical":
                        evidence_interval_start = min(
                            float(bbox[1]),
                            float(bbox[3]),
                        )

                        evidence_interval_end = max(
                            float(bbox[1]),
                            float(bbox[3]),
                        )

                    else:
                        evidence_interval_start = min(
                            float(bbox[0]),
                            float(bbox[2]),
                        )

                        evidence_interval_end = max(
                            float(bbox[0]),
                            float(bbox[2]),
                        )

                    orthogonal_distance = (
                        self._interval_distance(
                            orthogonal_start,
                            orthogonal_end,
                            evidence_interval_start,
                            evidence_interval_end,
                        )
                    )

                    if orthogonal_distance > chain_tolerance:
                        continue

            evidence_items.append(
                AxisDimensionEvidence(
                    text=evidence.text,
                    value_m=float(
                        evidence.comparison_value
                    ),
                    numeric_unit=evidence.numeric_unit,
                    unit_explicit=(
                        evidence.numeric_unit
                        is not None
                    ),
                    source=evidence.source,
                    confidence=evidence.confidence,
                    x=evidence.x,
                    y=evidence.y,
                    bbox=list(
                        evidence.bbox
                    ),
                )
            )

        if evidence_items:
            row_support = {
                id(item): self._dimension_row_support(
                    item=item,
                    all_evidence=dimension_evidence,
                    orientation=orientation,
                    tolerance=tolerance,
                )
                for item in evidence_items
            }
            maximum_support = max(row_support.values())
            evidence_items = [
                item
                for item in evidence_items
                if row_support[id(item)] == maximum_support
            ]

        distinct_values = (
            self._distinct_numeric_values(
                [
                    item.value_m
                    for item in evidence_items
                ]
            )
        )

        pixel_span = abs(
            end_axis.coordinate_px
            - start_axis.coordinate_px
        )

        measurement_direction = (
            "horizontal"
            if orientation == "vertical"
            else "vertical"
        )

        # ----------------------------------------------------
        # SIN EVIDENCIA
        # ----------------------------------------------------

        if not distinct_values:
            return AxisSpanGrounding(
                id=span_id,
                space_id=space.id_propuesto,
                level=space.nivel,
                orientation=orientation,
                measurement_direction=measurement_direction,
                start_axis_id=start_axis.id,
                start_axis_label=start_axis.label,
                start_coordinate_px=start_axis.coordinate_px,
                end_axis_id=end_axis.id,
                end_axis_label=end_axis.label,
                end_coordinate_px=end_axis.coordinate_px,
                pixel_span=pixel_span,
                value_m=None,
                pixels_per_meter=None,
                dimension_evidence=evidence_items,
                distinct_values_m=[],
                unit_explicit=False,
                state="NO_IDENTIFICADO",
                confirmed=False,
            )

        # ----------------------------------------------------
        # EVIDENCIA CONTRADICTORIA
        # ----------------------------------------------------

        if len(distinct_values) > 1:
            return AxisSpanGrounding(
                id=span_id,
                space_id=space.id_propuesto,
                level=space.nivel,
                orientation=orientation,
                measurement_direction=measurement_direction,
                start_axis_id=start_axis.id,
                start_axis_label=start_axis.label,
                start_coordinate_px=start_axis.coordinate_px,
                end_axis_id=end_axis.id,
                end_axis_label=end_axis.label,
                end_coordinate_px=end_axis.coordinate_px,
                pixel_span=pixel_span,
                value_m=None,
                pixels_per_meter=None,
                dimension_evidence=evidence_items,
                distinct_values_m=distinct_values,
                unit_explicit=False,
                state="CONFLICTO",
                confirmed=False,
            )

        # ----------------------------------------------------
        # TRAMO RESUELTO
        # ----------------------------------------------------

        value_m = distinct_values[0]

        unit_explicit = all(
            item.unit_explicit
            for item in evidence_items
            if math.isclose(
                item.value_m,
                value_m,
                rel_tol=0.0,
                abs_tol=self.NUMERIC_TOLERANCE,
            )
        )

        return AxisSpanGrounding(
            id=span_id,
            space_id=space.id_propuesto,
            level=space.nivel,
            orientation=orientation,
            measurement_direction=measurement_direction,
            start_axis_id=start_axis.id,
            start_axis_label=start_axis.label,
            start_coordinate_px=start_axis.coordinate_px,
            end_axis_id=end_axis.id,
            end_axis_label=end_axis.label,
            end_coordinate_px=end_axis.coordinate_px,
            pixel_span=pixel_span,
            value_m=value_m,
            pixels_per_meter=(
                pixel_span / value_m
            ),
            dimension_evidence=evidence_items,
            distinct_values_m=distinct_values,
            unit_explicit=unit_explicit,
            state="DETECTADO",
            confirmed=False,
        )
    # ========================================================
    # CADENA DE EJES DEL ESPACIO
    # ========================================================

    def _axes_for_space_chain(
        self,
        *,
        axes: list[AxisAnchorCandidate],
        space: SpaceGeometryReconciliation,
        orientation: str,
        tolerance: float,
    ) -> list[AxisAnchorCandidate]:
        if orientation != "vertical" or len(axes) < 2:
            return axes

        distances: dict[str, float] = {}

        for axis in axes:
            intervals = self._axis_label_intervals(
                axes=[axis],
                orientation=orientation,
            )

            if not intervals:
                continue

            distances[axis.id] = min(
                self._interval_distance(
                    interval_start,
                    interval_end,
                    space.localization_bbox.y_min,
                    space.localization_bbox.y_max,
                )
                for interval_start, interval_end in intervals
            )

        if not distances:
            return axes

        minimum_distance = min(distances.values())
        chain_margin = tolerance * 20.0

        return [
            axis
            for axis in axes
            if distances.get(axis.id, float("inf"))
            <= minimum_distance + chain_margin
        ]

    @staticmethod
    def _axis_label_intervals(
        *,
        axes: list[AxisAnchorCandidate],
        orientation: str,
    ) -> list[tuple[float, float]]:
        intervals: list[tuple[float, float]] = []

        for axis in axes:
            for bbox in axis.evidence_bboxes:
                if len(bbox) < 4:
                    continue

                if orientation == "vertical":
                    first = float(bbox[1])
                    second = float(bbox[3])
                else:
                    first = float(bbox[0])
                    second = float(bbox[2])

                intervals.append((min(first, second), max(first, second)))

        return intervals

    @staticmethod
    def _dimension_row_support(
        *,
        item: AxisDimensionEvidence,
        all_evidence: list[GeometryTextEvidence],
        orientation: str,
        tolerance: float,
    ) -> int:
        coordinate = item.y if orientation == "vertical" else item.x
        row_tolerance = tolerance * 2.0

        return sum(
            1
            for evidence in all_evidence
            if evidence.comparison_value is not None
            and evidence.comparison_value > 0
            and abs(
                (evidence.y if orientation == "vertical" else evidence.x)
                - coordinate
            )
            <= row_tolerance
        )

    # ========================================================
    # EJE ALCANZA ESPACIO
    # ========================================================

    def _axis_reaches_space(
        self,
        *,
        axis: AxisAnchorCandidate,
        space: SpaceGeometryReconciliation,
        segment_lookup: dict[str, RasterLineSegment],
        tolerance: float,
    ) -> bool:
        bbox = space.localization_bbox

        for segment_id in axis.supporting_segment_ids:
            segment = segment_lookup.get(segment_id)

            if segment is None:
                continue

            if axis.orientation == "vertical":
                segment_start = min(
                    segment.y1,
                    segment.y2,
                )

                segment_end = max(
                    segment.y1,
                    segment.y2,
                )

                if (
                    self._interval_distance(
                        segment_start,
                        segment_end,
                        bbox.y_min,
                        bbox.y_max,
                    )
                    <= tolerance
                ):
                    return True

            else:
                segment_start = min(
                    segment.x1,
                    segment.x2,
                )

                segment_end = max(
                    segment.x1,
                    segment.x2,
                )

                if (
                    self._interval_distance(
                        segment_start,
                        segment_end,
                        bbox.x_min,
                        bbox.x_max,
                    )
                    <= tolerance
                ):
                    return True

        coordinate_margin = tolerance * 4.0

        if axis.orientation == "vertical":
            return (
                bbox.x_min - coordinate_margin
                <= axis.coordinate_px
                <= bbox.x_max + coordinate_margin
            )

        return (
            bbox.y_min - coordinate_margin
            <= axis.coordinate_px
            <= bbox.y_max + coordinate_margin
        )

    # ========================================================
    # LÍMITES OPUESTOS DEL ESPACIO
    # ========================================================

    @staticmethod
    def _space_boundary_pair(
        *,
        space: SpaceGeometryReconciliation,
        orientation: str,
    ) -> tuple[
        BoundaryCandidate | None,
        BoundaryCandidate | None,
    ]:
        def preferred(
            candidates: list[BoundaryCandidate],
        ) -> BoundaryCandidate | None:
            if not candidates:
                return None

            return min(
                candidates,
                key=lambda candidate: (
                    candidate.distance_to_bbox_edge_px,
                    -candidate.support_count,
                    -candidate.length_px,
                ),
            )

        if orientation == "vertical":
            first = preferred(space.boundaries.left)
            second = preferred(space.boundaries.right)

        else:
            first = preferred(space.boundaries.top)
            second = preferred(space.boundaries.bottom)

        return (
            first,
            second,
        )

    # ========================================================
    # COORDENADA DEL LÍMITE
    # ========================================================

    @staticmethod
    def _boundary_coordinate(
        boundary: BoundaryCandidate,
        orientation: str,
    ) -> float:
        if orientation == "vertical":
            return (boundary.x1 + boundary.x2) / 2.0

        return (boundary.y1 + boundary.y2) / 2.0

    # ========================================================
    # COMPARAR CONTRA GEMINI
    # ========================================================

    def _compare_with_model(
        self,
        *,
        resolved: ResolvedSpaceDimension,
        space: SpaceGeometryReconciliation,
    ) -> None:
        model_entries: dict[
            tuple[
                str,
                float,
            ],
            None,
        ] = {}

        for association in space.metric_associations:
            if association.element_type != "espacio":
                continue

            if association.element_id != space.id_propuesto:
                continue

            if association.metric_kind != "linear":
                continue

            model_entries[
                (
                    association.field,
                    float(association.value),
                )
            ] = None

        model_values = sorted(
            {
                value
                for (
                    _field,
                    value,
                ) in model_entries.keys()
            }
        )

        resolved.model_values = model_values

        for (
            field_name,
            value,
        ) in model_entries.keys():
            if math.isclose(
                value,
                resolved.value_m,
                rel_tol=0.0,
                abs_tol=self.NUMERIC_TOLERANCE,
            ):
                resolved.model_agreement = True

                if field_name not in resolved.matching_model_fields:
                    resolved.matching_model_fields.append(field_name)

            else:
                if value not in resolved.conflicting_model_values:
                    resolved.conflicting_model_values.append(value)

        resolved.model_conflict = bool(
            resolved.conflicting_model_values and not resolved.model_agreement
        )

        if resolved.model_conflict:
            resolved.state = "CONFLICTO"

        resolved.matching_model_fields.sort()

        resolved.conflicting_model_values.sort()

    # ========================================================
    # DISTINTOS VALORES
    # ========================================================

    def _distinct_numeric_values(
        self,
        values: list[float],
    ) -> list[float]:
        result: list[float] = []

        for value in values:
            if any(
                math.isclose(
                    value,
                    existing,
                    rel_tol=0.0,
                    abs_tol=self.NUMERIC_TOLERANCE,
                )
                for existing in result
            ):
                continue

            result.append(float(value))

        result.sort()

        return result

    # ========================================================
    # DISTANCIA ENTRE INTERVALOS
    # ========================================================

    @staticmethod
    def _interval_distance(
        a0: float,
        a1: float,
        b0: float,
        b1: float,
    ) -> float:
        if a1 >= b0 and b1 >= a0:
            return 0.0

        if a1 < b0:
            return b0 - a1

        return a0 - b1

    # ========================================================
    # NORMALIZAR LABEL
    # ========================================================

    @staticmethod
    def _normalize_label(
        value: Any,
    ) -> str:
        text = str(value or "").strip().upper()

        decomposed = unicodedata.normalize(
            "NFD",
            text,
        )

        return "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )


# ============================================================
# FACTORY
# ============================================================


def get_architectural_dimension_grounding_service() -> (
    ArchitecturalDimensionGroundingService
):
    return ArchitecturalDimensionGroundingService()
