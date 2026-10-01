from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from app.legacy.quantia_spatial.architectural_wall_abstraction_service import (
    ArchitecturalWallAbstractionResult,
)
from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    BoundaryCandidate,
    PlanGeometryReconciliationResult,
)

# ============================================================
# NODOS
# ============================================================


@dataclass(slots=True)
class ArchitecturalGraphNode:
    id: str

    x: float
    y: float

    degree: int = 0

    source_segment_ids: list[str] = field(default_factory=list)

    source: str = "geometry_reconciliation"


# ============================================================
# ARISTAS
# ============================================================


@dataclass(slots=True)
class ArchitecturalGraphEdge:
    """
    Arista topológica candidata.

    IMPORTANTE:

        edge != muro confirmado

    Representa continuidad geométrica reconciliada.
    """

    id: str

    start_node_id: str
    end_node_id: str

    x1: float
    y1: float
    x2: float
    y2: float

    orientation: str

    length_px: float

    source_segment_ids: list[str] = field(default_factory=list)

    sources: list[str] = field(default_factory=list)

    space_ids: list[str] = field(default_factory=list)

    support_count: int = 1

    state: str = "CANDIDATO"

    confirmed: bool = False


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class ArchitecturalGraphResult:
    page: int

    width_px: int
    height_px: int

    nodes: list[ArchitecturalGraphNode] = field(default_factory=list)

    edges: list[ArchitecturalGraphEdge] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# SEGMENTO INTERNO
# ============================================================


@dataclass(slots=True)
class _CollectedSegment:
    segment_id: str

    x1: float
    y1: float
    x2: float
    y2: float

    orientation: str

    source_segment_ids: set[str] = field(default_factory=set)

    sources: set[str] = field(default_factory=set)

    space_ids: set[str] = field(default_factory=set)

    support_count: int = 1


# ============================================================
# BUILDER
# ============================================================


class ArchitecturalGraphBuilder:
    """
    Construye el grafo geométrico candidato de la vivienda.

    Entrada:

        PlanGeometryReconciliationResult
        +
        OpenCVPlanGeometryResult

    Proceso:

        límites candidatos
            ↓
        deduplicación por segmento OpenCV
            ↓
        intersecciones
            ↓
        división de segmentos
            ↓
        nodos
            ↓
        aristas
            ↓
        grafo topológico

    Todavía NO:

        - confirma muros;
        - cierra recintos semánticamente;
        - crea espacios definitivos;
        - convierte píxeles a metros;
        - aplica espesores.
    """

    NUMERIC_TOLERANCE = 1e-6

    # ========================================================
    # API
    # ========================================================

    def build(
        self,
        *,
        reconciliation: PlanGeometryReconciliationResult,
        opencv_geometry: OpenCVPlanGeometryResult,
        wall_abstraction: ArchitecturalWallAbstractionResult | None = None,
    ) -> ArchitecturalGraphResult:
        self._validate_inputs(
            reconciliation=reconciliation,
            opencv_geometry=opencv_geometry,
        )

        tolerance = self._coordinate_tolerance(opencv_geometry)

        graph_source = "reconciliation"

        if wall_abstraction is not None:
            if wall_abstraction.centerlines:
                collected = self._collect_centerlines(wall_abstraction)
                graph_source = "centerlines"
            else:
                collected = self._collect_wall_runs(wall_abstraction)
                graph_source = "wall_runs"
        else:
            collected = self._collect_segments(reconciliation)

        # Las intersecciones OpenCV solamente pertenecen
        # directamente a segmentos OpenCV originales.
        #
        # Centerlines y wall runs tienen identidad
        # arquitectónica propia y no deben buscar sus IDs
        # dentro del mapa de intersecciones OpenCV.
        if graph_source == "reconciliation":
            intersection_map = self._build_intersection_map(
                opencv_geometry,
                allowed_segment_ids=set(collected.keys()),
            )
        else:
            intersection_map = {}

        nodes: list[ArchitecturalGraphNode] = []

        edges: list[ArchitecturalGraphEdge] = []

        edge_registry: dict[
            tuple[str, str],
            ArchitecturalGraphEdge,
        ] = {}

        node_counter = 0
        edge_counter = 0

        for segment in collected.values():
            split_points = [
                (
                    segment.x1,
                    segment.y1,
                ),
                (
                    segment.x2,
                    segment.y2,
                ),
            ]

            for point in intersection_map.get(
                segment.segment_id,
                [],
            ):
                split_points.append(point)

            split_points = self._sort_and_deduplicate_points(
                split_points,
                orientation=segment.orientation,
                tolerance=tolerance,
            )

            if len(split_points) < 2:
                continue

            for index in range(len(split_points) - 1):
                x1, y1 = split_points[index]

                x2, y2 = split_points[index + 1]

                length = math.hypot(
                    x2 - x1,
                    y2 - y1,
                )

                if length <= tolerance:
                    continue

                start_node, created = self._get_or_create_node(
                    nodes=nodes,
                    x=x1,
                    y=y1,
                    tolerance=tolerance,
                    source_segment_id=(segment.segment_id),
                    next_id=(node_counter + 1),
                )

                if created:
                    node_counter += 1

                end_node, created = self._get_or_create_node(
                    nodes=nodes,
                    x=x2,
                    y=y2,
                    tolerance=tolerance,
                    source_segment_id=(segment.segment_id),
                    next_id=(node_counter + 1),
                )

                if created:
                    node_counter += 1

                if start_node.id == end_node.id:
                    continue

                key = tuple(
                    sorted(
                        (
                            start_node.id,
                            end_node.id,
                        )
                    )
                )

                existing = edge_registry.get(key)

                if existing is not None:
                    self._merge_edge_metadata(
                        existing=existing,
                        segment=segment,
                    )

                    continue

                edge_counter += 1

                edge = ArchitecturalGraphEdge(
                    id=f"AG_E_{edge_counter}",
                    start_node_id=(start_node.id),
                    end_node_id=(end_node.id),
                    x1=start_node.x,
                    y1=start_node.y,
                    x2=end_node.x,
                    y2=end_node.y,
                    orientation=(segment.orientation),
                    length_px=length,
                    source_segment_ids=sorted(segment.source_segment_ids),
                    sources=sorted(segment.sources),
                    space_ids=sorted(segment.space_ids),
                    support_count=(segment.support_count),
                    state="CANDIDATO",
                    confirmed=False,
                )

                edge_registry[key] = edge

                edges.append(edge)

        self._calculate_node_degrees(
            nodes=nodes,
            edges=edges,
        )

        notes: list[str] = [
            ("La geometría seleccionada fue convertida en un grafo topológico."),
            (f"Fuente geométrica del grafo: {graph_source}."),
            (
                "Aristas compartidas por varios espacios "
                "conservan sus referencias semánticas."
            ),
            ("Ninguna arista fue confirmada como muro."),
            ("No se realizó conversión de píxeles a unidades métricas."),
        ]

        if graph_source == "reconciliation":
            notes.append(
                (
                    "Los segmentos OpenCV originales fueron "
                    "divididos usando intersecciones OpenCV."
                )
            )

        elif graph_source == "centerlines":
            notes.append(
                (
                    "Los centerlines arquitectónicos conservan "
                    "su identidad propia y no reutilizan "
                    "intersecciones por ID de segmentos OpenCV."
                )
            )

        return ArchitecturalGraphResult(
            page=reconciliation.page,
            width_px=(reconciliation.width_px),
            height_px=(reconciliation.height_px),
            nodes=nodes,
            edges=edges,
            notes=notes,
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
            raise ValueError("Reconciliación y OpenCV pertenecen a páginas distintas.")

        if (
            reconciliation.width_px != opencv_geometry.width_px
            or reconciliation.height_px != opencv_geometry.height_px
        ):
            raise ValueError(
                "Reconciliación y OpenCV no utilizan el mismo raster canónico."
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
    # RECOLECTAR SEGMENTOS
    # ========================================================
    def _collect_segments(
        self,
        reconciliation: PlanGeometryReconciliationResult,
    ) -> dict[str, _CollectedSegment]:
        result: dict[str, _CollectedSegment] = {}

        for space in reconciliation.spaces:
            for side in (
                "left",
                "right",
                "top",
                "bottom",
            ):
                candidates: list[BoundaryCandidate] = getattr(
                    space.boundaries,
                    side,
                )

                for candidate in candidates:
                    segment_id = candidate.opencv_segment_id

                    existing = result.get(segment_id)

                    if existing is None:
                        existing = _CollectedSegment(
                            segment_id=segment_id,
                            x1=float(candidate.x1),
                            y1=float(candidate.y1),
                            x2=float(candidate.x2),
                            y2=float(candidate.y2),
                            orientation=(candidate.orientation),
                            source_segment_ids={segment_id},
                            sources=set(candidate.sources),
                            space_ids={space.id_propuesto},
                            support_count=(candidate.support_count),
                        )

                        result[segment_id] = existing

                    else:
                        existing.source_segment_ids.add(segment_id)

                        existing.sources.update(candidate.sources)

                        existing.space_ids.add(space.id_propuesto)

                        existing.support_count = max(
                            existing.support_count,
                            candidate.support_count,
                        )

        return result

    # ========================================================
    # RECOLECTAR WALL RUNS ARQUITECTÓNICOS
    # ========================================================
    @staticmethod
    def _collect_wall_runs(
        abstraction: ArchitecturalWallAbstractionResult,
    ) -> dict[str, _CollectedSegment]:
        result: dict[
            str,
            _CollectedSegment,
        ] = {}

        for wall_run in abstraction.wall_runs:
            segment_id = wall_run.id

            result[segment_id] = _CollectedSegment(
                segment_id=segment_id,
                x1=float(wall_run.x1),
                y1=float(wall_run.y1),
                x2=float(wall_run.x2),
                y2=float(wall_run.y2),
                orientation=wall_run.orientation,
                source_segment_ids=set(wall_run.source_segment_ids),
                sources=set(wall_run.sources),
                space_ids=set(wall_run.space_ids),
                support_count=(wall_run.support_count),
            )

        return result

    # ========================================================
    # MAPA DE INTERSECCIONES
    # ========================================================

    @staticmethod
    def _collect_centerlines(
        abstraction: ArchitecturalWallAbstractionResult,
    ) -> dict[str, _CollectedSegment]:
        result: dict[
            str,
            _CollectedSegment,
        ] = {}

        wall_run_by_id = {wall_run.id: wall_run for wall_run in abstraction.wall_runs}

        for centerline in abstraction.centerlines:
            supporting_runs = [
                wall_run_by_id[wall_run_id]
                for wall_run_id in centerline.wall_run_ids
                if wall_run_id in wall_run_by_id
            ]

            sources = {
                source for wall_run in supporting_runs for source in wall_run.sources
            }

            source_segment_ids = set(centerline.face_segment_ids)

            if not source_segment_ids:
                source_segment_ids = {
                    segment_id
                    for wall_run in supporting_runs
                    for segment_id in wall_run.face_segment_ids
                }

            support_count = max(
                (wall_run.support_count for wall_run in supporting_runs),
                default=1,
            )

            result[centerline.id] = _CollectedSegment(
                segment_id=centerline.id,
                x1=float(centerline.x1),
                y1=float(centerline.y1),
                x2=float(centerline.x2),
                y2=float(centerline.y2),
                orientation=(centerline.orientation),
                source_segment_ids=(source_segment_ids),
                sources=sources,
                space_ids=set(centerline.space_ids),
                support_count=(support_count),
            )

        return result

    def _collect_hybrid_segments(
        self,
        *,
        reconciliation: PlanGeometryReconciliationResult,
        abstraction: ArchitecturalWallAbstractionResult,
    ) -> dict[str, _CollectedSegment]:
        result = self._collect_segments(reconciliation)

        centerline_segments = self._collect_centerlines(abstraction)

        wall_run_by_id = {wall_run.id: wall_run for wall_run in abstraction.wall_runs}

        consumed_source_segment_ids: set[str] = set()

        for centerline in abstraction.centerlines:
            face_segment_ids = set(centerline.face_segment_ids)

            if not face_segment_ids:
                for wall_run_id in centerline.wall_run_ids:
                    wall_run = wall_run_by_id.get(wall_run_id)

                    if wall_run is None:
                        continue

                    face_segment_ids.update(wall_run.face_segment_ids)

            consumed_source_segment_ids.update(face_segment_ids)

        for source_segment_id in consumed_source_segment_ids:
            result.pop(
                source_segment_id,
                None,
            )

        result.update(centerline_segments)

        return result

    @staticmethod
    def _build_intersection_map(
        geometry: OpenCVPlanGeometryResult,
        *,
        allowed_segment_ids: set[str] | None = None,
    ) -> dict[
        str,
        list[
            tuple[
                float,
                float,
            ]
        ],
    ]:
        result: dict[
            str,
            list[
                tuple[
                    float,
                    float,
                ]
            ],
        ] = {}

        for intersection in geometry.intersections:
            if allowed_segment_ids is not None:
                if (
                    intersection.horizontal_segment_id not in allowed_segment_ids
                    or intersection.vertical_segment_id not in allowed_segment_ids
                ):
                    continue

            point = (
                intersection.x,
                intersection.y,
            )

            result.setdefault(
                intersection.horizontal_segment_id,
                [],
            ).append(point)

            result.setdefault(
                intersection.vertical_segment_id,
                [],
            ).append(point)

        return result

    @staticmethod
    def _build_centerline_intersection_map(
        *,
        abstraction: ArchitecturalWallAbstractionResult,
        collected: dict[str, _CollectedSegment],
        opencv_geometry: OpenCVPlanGeometryResult,
        tolerance: float,
    ) -> dict[
        str,
        list[
            tuple[
                float,
                float,
            ]
        ],
    ]:
        result: dict[
            str,
            list[
                tuple[
                    float,
                    float,
                ]
            ],
        ] = {}

        wall_run_by_id = {wall_run.id: wall_run for wall_run in abstraction.wall_runs}

        centerline_by_id = {
            centerline.id: centerline for centerline in abstraction.centerlines
        }

        face_to_centerline_ids: dict[
            str,
            set[str],
        ] = {}

        for centerline in abstraction.centerlines:
            face_segment_ids = set(centerline.face_segment_ids)

            if not face_segment_ids:
                for wall_run_id in centerline.wall_run_ids:
                    wall_run = wall_run_by_id.get(wall_run_id)

                    if wall_run is None:
                        continue

                    face_segment_ids.update(wall_run.face_segment_ids)

            for face_segment_id in face_segment_ids:
                face_to_centerline_ids.setdefault(
                    face_segment_id,
                    set(),
                ).add(centerline.id)

        for intersection in opencv_geometry.intersections:
            segment_pairs = (
                (
                    intersection.horizontal_segment_id,
                    intersection.vertical_segment_id,
                ),
                (
                    intersection.vertical_segment_id,
                    intersection.horizontal_segment_id,
                ),
            )

            for (
                face_segment_id,
                other_segment_id,
            ) in segment_pairs:
                centerline_ids = face_to_centerline_ids.get(face_segment_id)

                if not centerline_ids:
                    continue

                other_segment = collected.get(other_segment_id)

                if other_segment is None:
                    continue

                for centerline_id in centerline_ids:
                    centerline = centerline_by_id.get(centerline_id)

                    if centerline is None:
                        continue

                    if centerline_id not in collected:
                        continue

                    if centerline.orientation == "vertical":
                        x = (float(centerline.x1) + float(centerline.x2)) / 2.0

                        y = float(intersection.y)

                        lower = min(
                            centerline.y1,
                            centerline.y2,
                        )

                        upper = max(
                            centerline.y1,
                            centerline.y2,
                        )

                        if y < lower - tolerance or y > upper + tolerance:
                            continue

                    elif centerline.orientation == "horizontal":
                        x = float(intersection.x)

                        y = (float(centerline.y1) + float(centerline.y2)) / 2.0

                        lower = min(
                            centerline.x1,
                            centerline.x2,
                        )

                        upper = max(
                            centerline.x1,
                            centerline.x2,
                        )

                        if x < lower - tolerance or x > upper + tolerance:
                            continue

                    else:
                        continue

                    if other_segment.orientation == "horizontal":
                        other_y = (other_segment.y1 + other_segment.y2) / 2.0

                        if abs(y - other_y) > tolerance:
                            continue

                        other_lower = min(
                            other_segment.x1,
                            other_segment.x2,
                        )

                        other_upper = max(
                            other_segment.x1,
                            other_segment.x2,
                        )

                        if x < other_lower - tolerance or x > other_upper + tolerance:
                            continue

                    elif other_segment.orientation == "vertical":
                        other_x = (other_segment.x1 + other_segment.x2) / 2.0

                        if abs(x - other_x) > tolerance:
                            continue

                        other_lower = min(
                            other_segment.y1,
                            other_segment.y2,
                        )

                        other_upper = max(
                            other_segment.y1,
                            other_segment.y2,
                        )

                        if y < other_lower - tolerance or y > other_upper + tolerance:
                            continue

                    else:
                        continue

                    point = (
                        x,
                        y,
                    )

                    result.setdefault(
                        centerline_id,
                        [],
                    ).append(point)

                    result.setdefault(
                        other_segment_id,
                        [],
                    ).append(point)

        return result

    # ========================================================
    # ORDENAR / DEDUPLICAR PUNTOS
    # ========================================================

    @staticmethod
    def _sort_and_deduplicate_points(
        points: list[
            tuple[
                float,
                float,
            ]
        ],
        *,
        orientation: str,
        tolerance: float,
    ) -> list[
        tuple[
            float,
            float,
        ]
    ]:
        if orientation == "vertical":
            ordered = sorted(
                points,
                key=lambda item: item[1],
            )

        else:
            ordered = sorted(
                points,
                key=lambda item: item[0],
            )

        result: list[
            tuple[
                float,
                float,
            ]
        ] = []

        for point in ordered:
            if not result:
                result.append(point)
                continue

            previous = result[-1]

            distance = math.hypot(
                point[0] - previous[0],
                point[1] - previous[1],
            )

            if distance <= tolerance:
                continue

            result.append(point)

        return result

    # ========================================================
    # NODOS
    # ========================================================

    @staticmethod
    def _get_or_create_node(
        *,
        nodes: list[ArchitecturalGraphNode],
        x: float,
        y: float,
        tolerance: float,
        source_segment_id: str,
        next_id: int,
    ) -> tuple[
        ArchitecturalGraphNode,
        bool,
    ]:
        for node in nodes:
            if (
                math.hypot(
                    node.x - x,
                    node.y - y,
                )
                <= tolerance
            ):
                if source_segment_id not in node.source_segment_ids:
                    node.source_segment_ids.append(source_segment_id)

                return (
                    node,
                    False,
                )

        node = ArchitecturalGraphNode(
            id=f"AG_N_{next_id}",
            x=float(x),
            y=float(y),
            source_segment_ids=[source_segment_id],
        )

        nodes.append(node)

        return (
            node,
            True,
        )

    # ========================================================
    # MERGE METADATA
    # ========================================================

    @staticmethod
    def _merge_edge_metadata(
        *,
        existing: ArchitecturalGraphEdge,
        segment: _CollectedSegment,
    ) -> None:
        for source in segment.sources:
            if source not in existing.sources:
                existing.sources.append(source)

        for space_id in segment.space_ids:
            if space_id not in existing.space_ids:
                existing.space_ids.append(space_id)

        for source_segment_id in segment.source_segment_ids:
            if source_segment_id not in existing.source_segment_ids:
                existing.source_segment_ids.append(source_segment_id)

        existing.support_count = max(
            existing.support_count,
            segment.support_count,
            len(existing.sources),
        )

        existing.sources.sort()
        existing.space_ids.sort()
        existing.source_segment_ids.sort()

    # ========================================================
    # GRADO
    # ========================================================

    @staticmethod
    def _calculate_node_degrees(
        *,
        nodes: list[ArchitecturalGraphNode],
        edges: list[ArchitecturalGraphEdge],
    ) -> None:
        counts: dict[
            str,
            int,
        ] = {node.id: 0 for node in nodes}

        for edge in edges:
            counts[edge.start_node_id] = (
                counts.get(
                    edge.start_node_id,
                    0,
                )
                + 1
            )

            counts[edge.end_node_id] = (
                counts.get(
                    edge.end_node_id,
                    0,
                )
                + 1
            )

        for node in nodes:
            node.degree = counts.get(
                node.id,
                0,
            )


# ============================================================
# FACTORY
# ============================================================


def get_architectural_graph_builder() -> ArchitecturalGraphBuilder:
    return ArchitecturalGraphBuilder()
