from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from shapely.geometry import LineString, Point, box

from app.services.plan_document_analyzer import (
    DocumentLine,
    PlanDocumentAnalysis,
)
from app.legacy.quantia_spatial.space_pdf_coordinate_mapper import (
    MappedSpaceLocalization,
    PDFBBox,
    SpacePDFCoordinateMapping,
)


# ============================================================
# SEGMENTO VECTORIAL
# ============================================================


@dataclass(slots=True)
class VectorSegmentCandidate:
    """
    Segmento vectorial PyMuPDF encontrado dentro de la región
    aproximada de un espacio.

    IMPORTANTE:

        segmento candidato != muro

    Este objeto únicamente conserva características geométricas
    para que etapas posteriores puedan reconciliar:

        líneas
        + ejes
        + cotas
        + OpenCV
        + semántica Gemini.
    """

    index: int

    x1: float
    y1: float
    x2: float
    y2: float

    midpoint_x: float
    midpoint_y: float

    length: float

    orientation: str

    distance_to_seed: float

    distance_to_bbox: float

    intersects_localization_bbox: bool

    clipped_length_in_bbox: float

    crosses_seed_x: bool
    crosses_seed_y: bool

    bbox_overlap_length: float

    bbox_coverage_ratio: float

    distance_to_left_edge: float
    distance_to_right_edge: float
    distance_to_top_edge: float
    distance_to_bottom_edge: float

    source: str = "pymupdf_vector"


# ============================================================
# CANDIDATOS DIRECCIONALES
# ============================================================


@dataclass(slots=True)
class DirectionalBoundaryCandidates:
    """
    Segmentos agrupados según su posición relativa a la región
    semántica del espacio.

    Ninguna lista representa todavía un muro confirmado.
    """

    left: list[
        VectorSegmentCandidate
    ] = field(
        default_factory=list
    )

    right: list[
        VectorSegmentCandidate
    ] = field(
        default_factory=list
    )

    top: list[
        VectorSegmentCandidate
    ] = field(
        default_factory=list
    )

    bottom: list[
        VectorSegmentCandidate
    ] = field(
        default_factory=list
    )


# ============================================================
# RESULTADO POR ESPACIO
# ============================================================


@dataclass(slots=True)
class SpaceVectorBoundaryProbe:
    nivel: str

    id_propuesto: str

    nombre: str

    seed_x: float

    seed_y: float

    localization_bbox: PDFBBox

    total_page_segments: int

    usable_page_segments: int

    segments_intersecting_bbox: int

    horizontal_segments_in_bbox: int

    vertical_segments_in_bbox: int

    other_segments_in_bbox: int

    boundaries: DirectionalBoundaryCandidates

    all_intersecting_segments: list[
        VectorSegmentCandidate
    ] = field(
        default_factory=list
    )

    semantic_validation_pending: bool = True

    geometry_validation_pending: bool = True


# ============================================================
# RESULTADO GLOBAL
# ============================================================


@dataclass(slots=True)
class SpaceVectorBoundaryProbeResult:
    page: int

    spaces: list[
        SpaceVectorBoundaryProbe
    ] = field(
        default_factory=list
    )

    notes: list[str] = field(
        default_factory=list
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


# ============================================================
# SERVICIO
# ============================================================


class SpaceVectorBoundaryProbeService:
    """
    Busca geometría vectorial PyMuPDF potencialmente relacionada
    con espacios localizados previamente por Gemini.

    ==========================================================
    PIPELINE
    ==========================================================

        Gemini
        ↓
    bbox aproximado
        ↓
    SpacePDFCoordinateMapper
        ↓
    región PDF
        ↓
    SpaceVectorBoundaryProbeService
        ↓
    segmentos vectoriales candidatos

    ==========================================================
    REGLAS
    ==========================================================

    1. El bbox Gemini es únicamente una ventana de búsqueda.

    2. Una línea PyMuPDF no equivale automáticamente a muro.

    3. Ya NO exigimos que una línea atraviese exactamente el
       centro del bbox para considerarla candidata lateral.

    4. Conservamos:

        - orientación;
        - longitud;
        - intersección con bbox;
        - cobertura del bbox;
        - distancia a cada borde;
        - distancia al centro semántico.

    5. Los candidatos se ordenan para facilitar el grounding,
       pero no se selecciona ninguno como muro.

    6. OpenCV todavía NO participa aquí.

    7. La selección final deberá combinar:

        PyMuPDF
        + OpenCV
        + ejes
        + cotas
        + relaciones espaciales
        + Gemini.
    """

    NUMERIC_TOLERANCE = 1e-6

    # ========================================================
    # API PÚBLICA
    # ========================================================

    def probe(
        self,
        *,
        analysis: PlanDocumentAnalysis,
        mapping: SpacePDFCoordinateMapping,
    ) -> SpaceVectorBoundaryProbeResult:
        if not analysis.pages:
            raise ValueError(
                "El análisis PDF no contiene páginas."
            )

        if (
            mapping.page < 1
            or mapping.page
            > len(
                analysis.pages
            )
        ):
            raise ValueError(
                "La página del mapeo no existe "
                "en el análisis PDF."
            )

        page = (
            analysis.pages[
                mapping.page - 1
            ]
        )

        results: list[
            SpaceVectorBoundaryProbe
        ] = []

        for space in mapping.spaces:
            if (
                not space.localizado
                or space.bbox_pdf is None
            ):
                continue

            results.append(
                self._probe_space(
                    space=
                        space,

                    lines=
                        page.lines,
                )
            )

        notes: list[str] = [
            (
                "Los bbox Gemini se utilizaron únicamente "
                "como regiones aproximadas de búsqueda."
            ),
            (
                "Los segmentos vectoriales se clasificaron "
                "por orientación, cobertura y relación con "
                "los bordes del bbox."
            ),
            (
                "Cruzar el centro del bbox ya no es requisito "
                "para que un segmento sea candidato a límite."
            ),
            (
                "No se aplicaron longitudes constructivas "
                "mínimas ni espesores arbitrarios."
            ),
            (
                "Ningún segmento fue promovido a muro."
            ),
            (
                "La validación final permanece pendiente de "
                "OpenCV, ejes, cotas, continuidad y semántica."
            ),
        ]

        return SpaceVectorBoundaryProbeResult(
            page=
                mapping.page,

            spaces=
                results,

            notes=
                notes,
        )

    # ========================================================
    # ESPACIO
    # ========================================================

    def _probe_space(
        self,
        *,
        space: MappedSpaceLocalization,
        lines: list[DocumentLine],
    ) -> SpaceVectorBoundaryProbe:
        bbox = (
            space.bbox_pdf
        )

        if bbox is None:
            raise ValueError(
                "El espacio no contiene bbox PDF."
            )

        seed_x = (
            bbox.center_x
        )

        seed_y = (
            bbox.center_y
        )

        seed = Point(
            seed_x,
            seed_y,
        )

        localization_box = box(
            bbox.x_min,
            bbox.y_min,
            bbox.x_max,
            bbox.y_max,
        )

        intersecting: list[
            VectorSegmentCandidate
        ] = []

        left: list[
            VectorSegmentCandidate
        ] = []

        right: list[
            VectorSegmentCandidate
        ] = []

        top: list[
            VectorSegmentCandidate
        ] = []

        bottom: list[
            VectorSegmentCandidate
        ] = []

        horizontal_count = 0
        vertical_count = 0
        other_count = 0

        usable_segments = 0

        # ====================================================
        # ANALIZAR SEGMENTOS
        # ====================================================

        for index, line in enumerate(
            lines
        ):
            candidate = (
                self._build_candidate(
                    index=
                        index,

                    line=
                        line,

                    seed=
                        seed,

                    localization_box=
                        localization_box,

                    bbox=
                        bbox,

                    seed_x=
                        seed_x,

                    seed_y=
                        seed_y,
                )
            )

            # Segmento degenerado.
            if candidate is None:
                continue

            usable_segments += 1

            if (
                not candidate
                .intersects_localization_bbox
            ):
                continue

            intersecting.append(
                candidate
            )

            # =================================================
            # ORIENTACIÓN
            # =================================================

            if (
                candidate.orientation
                == "horizontal"
            ):
                horizontal_count += 1

            elif (
                candidate.orientation
                == "vertical"
            ):
                vertical_count += 1

            else:
                other_count += 1

            # =================================================
            # IZQUIERDA / DERECHA
            # =================================================
            #
            # Ya NO exigimos crosses_seed_y.
            #
            # Un muro real puede estar dentro del bbox pero no
            # atravesar exactamente la coordenada Y del centro,
            # especialmente en:
            #
            # - recintos irregulares;
            # - escaleras;
            # - espacios abiertos;
            # - bbox Gemini aproximados.
            #
            # Para entrar como candidato lateral basta:
            #
            # - ser vertical;
            # - intersectar la región;
            # - poseer cobertura vertical positiva.
            # =================================================

            if (
                candidate.orientation
                == "vertical"
                and candidate
                .bbox_overlap_length
                > self.NUMERIC_TOLERANCE
            ):
                if (
                    candidate.midpoint_x
                    < seed_x
                ):
                    left.append(
                        candidate
                    )

                elif (
                    candidate.midpoint_x
                    > seed_x
                ):
                    right.append(
                        candidate
                    )

            # =================================================
            # SUPERIOR / INFERIOR
            # =================================================

            if (
                candidate.orientation
                == "horizontal"
                and candidate
                .bbox_overlap_length
                > self.NUMERIC_TOLERANCE
            ):
                if (
                    candidate.midpoint_y
                    < seed_y
                ):
                    top.append(
                        candidate
                    )

                elif (
                    candidate.midpoint_y
                    > seed_y
                ):
                    bottom.append(
                        candidate
                    )

        # ====================================================
        # ORDEN DE CANDIDATOS
        # ====================================================
        #
        # El orden sirve únicamente para análisis posterior.
        #
        # NO representa selección automática.
        #
        # Prioridad:
        #
        # 1. mayor cobertura;
        # 2. menor distancia al borde correspondiente;
        # 3. menor distancia a la semilla.
        # ====================================================

        left.sort(
            key=lambda item: (
                -item.bbox_coverage_ratio,
                item.distance_to_left_edge,
                item.distance_to_seed,
            )
        )

        right.sort(
            key=lambda item: (
                -item.bbox_coverage_ratio,
                item.distance_to_right_edge,
                item.distance_to_seed,
            )
        )

        top.sort(
            key=lambda item: (
                -item.bbox_coverage_ratio,
                item.distance_to_top_edge,
                item.distance_to_seed,
            )
        )

        bottom.sort(
            key=lambda item: (
                -item.bbox_coverage_ratio,
                item.distance_to_bottom_edge,
                item.distance_to_seed,
            )
        )

        # Mantener también todos los segmentos que realmente
        # intersectaron la región para fases posteriores.

        intersecting.sort(
            key=lambda item: (
                item.orientation,
                -item.bbox_coverage_ratio,
                item.distance_to_seed,
            )
        )

        return SpaceVectorBoundaryProbe(
            nivel=
                space.nivel,

            id_propuesto=
                space.id_propuesto,

            nombre=
                space.nombre,

            seed_x=
                seed_x,

            seed_y=
                seed_y,

            localization_bbox=
                bbox,

            total_page_segments=
                len(
                    lines
                ),

            usable_page_segments=
                usable_segments,

            segments_intersecting_bbox=
                len(
                    intersecting
                ),

            horizontal_segments_in_bbox=
                horizontal_count,

            vertical_segments_in_bbox=
                vertical_count,

            other_segments_in_bbox=
                other_count,

            boundaries=
                DirectionalBoundaryCandidates(
                    left=
                        left,

                    right=
                        right,

                    top=
                        top,

                    bottom=
                        bottom,
                ),

            all_intersecting_segments=
                intersecting,

            semantic_validation_pending=
                True,

            geometry_validation_pending=
                True,
        )

    # ========================================================
    # CONSTRUIR CANDIDATO
    # ========================================================

    def _build_candidate(
        self,
        *,
        index: int,
        line: DocumentLine,
        seed: Point,
        localization_box,
        bbox: PDFBBox,
        seed_x: float,
        seed_y: float,
    ) -> VectorSegmentCandidate | None:
        dx = (
            line.x2
            - line.x1
        )

        dy = (
            line.y2
            - line.y1
        )

        length = math.hypot(
            dx,
            dy,
        )

        # ----------------------------------------------------
        # DESCARTAR SEGMENTOS DEGENERADOS
        # ----------------------------------------------------

        if (
            length
            <= self.NUMERIC_TOLERANCE
        ):
            return None

        geometry = LineString(
            [
                (
                    line.x1,
                    line.y1,
                ),
                (
                    line.x2,
                    line.y2,
                ),
            ]
        )

        orientation = (
            self._orientation(
                dx=
                    dx,

                dy=
                    dy,
            )
        )

        min_x = min(
            line.x1,
            line.x2,
        )

        max_x = max(
            line.x1,
            line.x2,
        )

        min_y = min(
            line.y1,
            line.y2,
        )

        max_y = max(
            line.y1,
            line.y2,
        )

        midpoint_x = (
            line.x1
            + line.x2
        ) / 2.0

        midpoint_y = (
            line.y1
            + line.y2
        ) / 2.0

        # ====================================================
        # RELACIÓN CON SEMILLA
        # ====================================================

        crosses_seed_x = (
            min_x
            - self.NUMERIC_TOLERANCE
            <= seed_x
            <= max_x
            + self.NUMERIC_TOLERANCE
        )

        crosses_seed_y = (
            min_y
            - self.NUMERIC_TOLERANCE
            <= seed_y
            <= max_y
            + self.NUMERIC_TOLERANCE
        )

        # ====================================================
        # INTERSECCIÓN CON BBOX
        # ====================================================

        intersects_bbox = bool(
            geometry.intersects(
                localization_box
            )
        )

        distance_to_bbox = float(
            geometry.distance(
                localization_box
            )
        )

        clipped_length = 0.0

        if intersects_bbox:
            try:
                clipped_geometry = (
                    geometry.intersection(
                        localization_box
                    )
                )

                clipped_length = float(
                    clipped_geometry.length
                )

            except Exception:
                clipped_length = 0.0

        # ====================================================
        # COBERTURA DIRECCIONAL
        # ====================================================

        overlap_length = 0.0
        coverage_ratio = 0.0

        if (
            orientation
            == "vertical"
        ):
            overlap_start = max(
                min_y,
                bbox.y_min,
            )

            overlap_end = min(
                max_y,
                bbox.y_max,
            )

            overlap_length = max(
                0.0,
                overlap_end
                - overlap_start,
            )

            if (
                bbox.height
                > self.NUMERIC_TOLERANCE
            ):
                coverage_ratio = (
                    overlap_length
                    / bbox.height
                )

        elif (
            orientation
            == "horizontal"
        ):
            overlap_start = max(
                min_x,
                bbox.x_min,
            )

            overlap_end = min(
                max_x,
                bbox.x_max,
            )

            overlap_length = max(
                0.0,
                overlap_end
                - overlap_start,
            )

            if (
                bbox.width
                > self.NUMERIC_TOLERANCE
            ):
                coverage_ratio = (
                    overlap_length
                    / bbox.width
                )

        else:
            # Para líneas diagonales u otras geometrías
            # conservamos únicamente cuánto de la línea queda
            # realmente dentro del bbox.
            overlap_length = (
                clipped_length
            )

            if (
                length
                > self.NUMERIC_TOLERANCE
            ):
                coverage_ratio = (
                    clipped_length
                    / length
                )

        # ====================================================
        # DISTANCIA A BORDES DEL BBOX
        # ====================================================
        #
        # No deciden cuál línea es muro.
        #
        # Sirven para ordenar candidatos de manera espacial.
        # ====================================================

        distance_to_left_edge = abs(
            midpoint_x
            - bbox.x_min
        )

        distance_to_right_edge = abs(
            midpoint_x
            - bbox.x_max
        )

        distance_to_top_edge = abs(
            midpoint_y
            - bbox.y_min
        )

        distance_to_bottom_edge = abs(
            midpoint_y
            - bbox.y_max
        )

        return VectorSegmentCandidate(
            index=
                index,

            x1=
                line.x1,

            y1=
                line.y1,

            x2=
                line.x2,

            y2=
                line.y2,

            midpoint_x=
                midpoint_x,

            midpoint_y=
                midpoint_y,

            length=
                length,

            orientation=
                orientation,

            distance_to_seed=
                float(
                    seed.distance(
                        geometry
                    )
                ),

            distance_to_bbox=
                distance_to_bbox,

            intersects_localization_bbox=
                intersects_bbox,

            clipped_length_in_bbox=
                clipped_length,

            crosses_seed_x=
                crosses_seed_x,

            crosses_seed_y=
                crosses_seed_y,

            bbox_overlap_length=
                overlap_length,

            bbox_coverage_ratio=
                coverage_ratio,

            distance_to_left_edge=
                distance_to_left_edge,

            distance_to_right_edge=
                distance_to_right_edge,

            distance_to_top_edge=
                distance_to_top_edge,

            distance_to_bottom_edge=
                distance_to_bottom_edge,

            source=
                "pymupdf_vector",
        )

    # ========================================================
    # ORIENTACIÓN
    # ========================================================

    def _orientation(
        self,
        *,
        dx: float,
        dy: float,
    ) -> str:
        """
        Clasificación estrictamente geométrica.

        No imponemos tolerancias angulares arbitrarias.

        Una línea será horizontal/vertical únicamente cuando
        PyMuPDF realmente la represente así dentro de la
        tolerancia numérica mínima.
        """

        if math.isclose(
            dy,
            0.0,
            rel_tol=0.0,
            abs_tol=
                self.NUMERIC_TOLERANCE,
        ):
            return "horizontal"

        if math.isclose(
            dx,
            0.0,
            rel_tol=0.0,
            abs_tol=
                self.NUMERIC_TOLERANCE,
        ):
            return "vertical"

        return "other"


# ============================================================
# DEPENDENCY FACTORY
# ============================================================


def get_space_vector_boundary_probe_service(
) -> SpaceVectorBoundaryProbeService:
    return SpaceVectorBoundaryProbeService()