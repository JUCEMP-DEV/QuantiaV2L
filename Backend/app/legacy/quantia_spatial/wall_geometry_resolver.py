from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from shapely.geometry import LineString, Polygon

from app.legacy.quantia_spatial.architectural_dimension_grounding_service import (
    ArchitecturalDimensionGroundingResult,
)
from app.legacy.quantia_spatial.architectural_graph_builder import (
    ArchitecturalGraphEdge,
    ArchitecturalGraphNode,
)
from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
    RasterLineSegment,
)
from app.legacy.quantia_spatial.shapely_plan_geometry_service import (
    ArchitecturalFaceCandidate,
    ShapelyPlanGeometryResult,
)
from app.legacy.quantia_spatial.wall_opening_topology_service import (
    SemanticOpeningCandidate,
    WallGapCandidate,
    WallOpeningTopologyResult,
)


# ============================================================
# PRIORIDADES DE ESPESOR
# ============================================================


THICKNESS_PRIORITY_EXPLICIT_DIMENSION = 1
THICKNESS_PRIORITY_VECTOR_FACE = 2
THICKNESS_PRIORITY_RASTER_CALIBRATED = 3
THICKNESS_PRIORITY_DOMAIN_RULE = 4


# ============================================================
# SEMÁNTICA DE LADO
# ============================================================


@dataclass(slots=True)
class WallSideSemanticCandidate:
    space_id: str

    level: str

    name: str

    face_overlap_ratio: float

    bbox_overlap_ratio: float

    centroid_inside_localization: bool

    confirmed: bool = False


# ============================================================
# LADO DE MURO
# ============================================================


@dataclass(slots=True)
class WallSideReference:
    """
    Cara geométrica relacionada con uno de los lados del muro.

    En muro vertical:

        side_a = izquierda
        side_b = derecha

    En muro horizontal:

        side_a = superior
        side_b = inferior
    """

    face_id: str

    position: str

    shared_boundary_length_px: float

    semantic_candidates: list[
        WallSideSemanticCandidate
    ] = field(
        default_factory=list
    )

    primary_space_id: str | None = None

    primary_space_name: str | None = None

    primary_level: str | None = None

    confirmed: bool = False


# ============================================================
# EVIDENCIA EXTERNA DE ESPESOR
# ============================================================


@dataclass(slots=True)
class WallThicknessEvidence:
    """
    Evidencia ya asociada espacialmente a un muro.

    Permite incorporar en este resolver:

        prioridad 1:
            cota explícita de espesor.

        prioridad 2:
            separación vectorial entre caras.

    El servicio NO genera estas asociaciones por proximidad.

    Deben venir previamente grounded.
    """

    source: str

    priority: int

    thickness_m: float

    target_graph_edge_id: str | None = None

    target_continuity_group_id: str | None = None

    state: str = "DETECTADO"

    confidence: float | None = None

    evidence: list[str] = field(
        default_factory=list
    )


# ============================================================
# CANDIDATO DE ESPESOR
# ============================================================


@dataclass(slots=True)
class WallThicknessCandidate:
    source: str

    priority: int

    thickness_m: float | None

    thickness_px: float | None

    calibration_pixels_per_meter: float | None

    calibration_source_id: str | None

    supporting_segment_ids: list[
        str
    ] = field(
        default_factory=list
    )

    evidence: list[str] = field(
        default_factory=list
    )

    state: str = "CANDIDATO"

    promoted: bool = False


# ============================================================
# OPENING DE MURO
# ============================================================


@dataclass(slots=True)
class ResolvedWallOpeningReference:
    """
    Abertura semántica relacionada con un muro.

    La asociación sigue siendo candidata mientras no exista
    un anclaje geométrico inequívoco del vano.
    """

    opening_id: str

    opening_type: str

    space_id: str

    level: str

    semantic_location: str | None

    direction: str | None

    gap_id: str

    gap_length_px: float

    virtual_edge_id: str | None

    association_type: str

    state: str

    confirmed: bool = False


# ============================================================
# SEGMENTO DEL MURO
# ============================================================


@dataclass(slots=True)
class ResolvedWallSegment:
    graph_edge_id: str

    role: str

    x1: float
    y1: float

    x2: float
    y2: float

    length_px: float

    orientation: str

    side_a: WallSideReference | None

    side_b: WallSideReference | None

    side_a_candidates: list[
        WallSideReference
    ] = field(
        default_factory=list
    )

    side_b_candidates: list[
        WallSideReference
    ] = field(
        default_factory=list
    )

    openings: list[
        ResolvedWallOpeningReference
    ] = field(
        default_factory=list
    )

    evidence_sources: list[
        str
    ] = field(
        default_factory=list
    )

    side_conflict: bool = False

    state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# MURO RESUELTO
# ============================================================


@dataclass(slots=True)
class ResolvedWallGeometry:
    """
    Muro candidato completo.

    Un muro puede contener varios segmentos porque:

        - existen intersecciones;
        - existen puertas/ventanas;
        - cambia el espacio que tiene a cada lado.

    La continuidad se conserva mediante continuity_group_id.
    """

    id: str

    continuity_group_id: str

    orientation: str

    segments: list[
        ResolvedWallSegment
    ] = field(
        default_factory=list
    )

    graph_edge_ids: list[
        str
    ] = field(
        default_factory=list
    )

    space_ids: list[
        str
    ] = field(
        default_factory=list
    )

    real_length_px: float = 0.0

    topological_length_px: float = 0.0

    virtual_opening_length_px: float = 0.0

    thickness_m: float | None = None

    thickness_state: str = "PENDIENTE"

    thickness_source: str | None = None

    thickness_candidates: list[
        WallThicknessCandidate
    ] = field(
        default_factory=list
    )

    openings: list[
        ResolvedWallOpeningReference
    ] = field(
        default_factory=list
    )

    evidence_sources: list[
        str
    ] = field(
        default_factory=list
    )

    confidence: float | None = None

    state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class WallGeometryResolverResult:
    page: int

    width_px: int
    height_px: int

    walls: list[
        ResolvedWallGeometry
    ] = field(
        default_factory=list
    )

    unresolved_thickness_wall_ids: list[
        str
    ] = field(
        default_factory=list
    )

    conflicting_wall_ids: list[
        str
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
# GRUPO INTERNO DE CONTINUIDAD
# ============================================================


@dataclass(slots=True)
class _ContinuityGroup:
    id: str

    orientation: str

    edge_ids: list[
        str
    ]

    edges: list[
        ArchitecturalGraphEdge
    ]


# ============================================================
# SERVICIO
# ============================================================


class WallGeometryResolver:
    """
    Convierte el grafo topológico en muros arquitectónicos
    candidatos.

    ==========================================================
    DEFINICIÓN DE MURO QUANTIA
    ==========================================================

        eje / centerline
        +
        continuidad topológica
        +
        lados A/B
        +
        espacios relacionados
        +
        espesor
        +
        openings
        +
        origen
        +
        estado
        +
        confirmed=false

    ==========================================================
    ESPESOR
    ==========================================================

    Prioridad:

        1. cota explícita;
        2. separación vectorial entre caras;
        3. separación raster calibrada;
        4. regla Quantia 0.15 m cuando aplique;
        5. null / pendiente.

    IMPORTANTE:

    La separación raster encontrada aquí permanece como
    CANDIDATO.

    Este servicio no promueve automáticamente dos líneas
    paralelas a caras de un mismo muro, porque podrían ser:

        - otro muro;
        - mobiliario;
        - línea de cota;
        - eje;
        - detalle constructivo.

    ==========================================================
    REGLA REGIONAL
    ==========================================================

    0.15 m NO se aplica globalmente.

    El llamador debe enviar explícitamente los IDs de muros
    o grupos donde la regla de dominio resulta aplicable.

    Cuando se utiliza:

        thickness_state = INFERIDO
        confirmed = False
    """

    NUMERIC_TOLERANCE = 1e-6

    DOMAIN_FINISHED_WALL_THICKNESS_M = 0.15

    # ========================================================
    # API
    # ========================================================

    def resolve(
        self,
        *,
        topology: WallOpeningTopologyResult,
        shapely_geometry: ShapelyPlanGeometryResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        opencv_geometry: OpenCVPlanGeometryResult,
        thickness_evidence: list[
            WallThicknessEvidence
        ] | None = None,
        domain_rule_targets: set[
            str
        ] | None = None,
    ) -> WallGeometryResolverResult:
        self._validate_inputs(
            topology=
                topology,

            shapely_geometry=
                shapely_geometry,

            dimension_grounding=
                dimension_grounding,

            opencv_geometry=
                opencv_geometry,
        )

        supplied_thickness = list(
            thickness_evidence
            or []
        )

        domain_targets = set(
            domain_rule_targets
            or set()
        )

        tolerance = (
            self._coordinate_tolerance(
                opencv_geometry
            )
        )

        graph = (
            topology.augmented_graph
        )

        groups = (
            self._build_continuity_groups(
                graph_edges=
                    graph.edges,

                graph_nodes=
                    graph.nodes,

                tolerance=
                    tolerance,
            )
        )

        opening_lookup = {
            opening.id:
                opening
            for opening
            in topology.openings
        }

        walls: list[
            ResolvedWallGeometry
        ] = []

        unresolved_thickness: list[
            str
        ] = []

        conflicting_walls: list[
            str
        ] = []

        wall_counter = 0

        for group in groups:
            wall_counter += 1

            wall_id = (
                f"WALL_{wall_counter}"
            )

            segments: list[
                ResolvedWallSegment
            ] = []

            wall_openings: list[
                ResolvedWallOpeningReference
            ] = []

            evidence_sources: set[str] = (
                set()
            )

            space_ids: set[str] = (
                set()
            )

            real_length = 0.0
            topological_length = 0.0
            virtual_length = 0.0

            wall_state = (
                "DETECTADO"
            )

            # =================================================
            # SEGMENTOS
            # =================================================

            for edge in (
                self._sort_group_edges(
                    group
                )
            ):
                is_virtual = (
                    "topology_virtual"
                    in edge.sources
                )

                role = (
                    "opening_bridge"
                    if is_virtual
                    else "wall_trace"
                )

                if is_virtual:
                    segment_state = (
                        "INFERIDO"
                    )

                    wall_state = (
                        "INFERIDO"
                        if wall_state
                        != "CONFLICTO"
                        else wall_state
                    )

                    virtual_length += (
                        edge.length_px
                    )

                else:
                    segment_state = (
                        "DETECTADO"
                    )

                    real_length += (
                        edge.length_px
                    )

                topological_length += (
                    edge.length_px
                )

                evidence_sources.update(
                    edge.sources
                )

                space_ids.update(
                    edge.space_ids
                )

                (
                    side_a,
                    side_b,
                    side_a_candidates,
                    side_b_candidates,
                    side_conflict,
                ) = self._resolve_edge_sides(
                    edge=
                        edge,

                    shapely_geometry=
                        shapely_geometry,
                )

                if side_conflict:
                    wall_state = (
                        "CONFLICTO"
                    )

                edge_openings = (
                    self._openings_for_edge(
                        edge=
                            edge,

                        gaps=
                            topology
                            .gap_candidates,

                        opening_lookup=
                            opening_lookup,
                    )
                )

                for opening in (
                    edge_openings
                ):
                    if not any(
                        existing.opening_id
                        == opening.opening_id
                        and existing.gap_id
                        == opening.gap_id
                        for existing
                        in wall_openings
                    ):
                        wall_openings.append(
                            opening
                        )

                segments.append(
                    ResolvedWallSegment(
                        graph_edge_id=
                            edge.id,

                        role=
                            role,

                        x1=
                            edge.x1,

                        y1=
                            edge.y1,

                        x2=
                            edge.x2,

                        y2=
                            edge.y2,

                        length_px=
                            edge.length_px,

                        orientation=
                            edge.orientation,

                        side_a=
                            side_a,

                        side_b=
                            side_b,

                        side_a_candidates=
                            side_a_candidates,

                        side_b_candidates=
                            side_b_candidates,

                        openings=
                            edge_openings,

                        evidence_sources=
                            sorted(
                                set(
                                    edge.sources
                                )
                            ),

                        side_conflict=
                            side_conflict,

                        state=
                            segment_state,

                        confirmed=
                            False,
                    )
                )

            # =================================================
            # ESPESOR — EVIDENCIA PROPORCIONADA
            # =================================================

            targeted_evidence = (
                self._targeted_thickness_evidence(
                    wall_id=
                        wall_id,

                    group=
                        group,

                    evidence=
                        supplied_thickness,
                )
            )

            thickness_candidates: list[
                WallThicknessCandidate
            ] = [
                WallThicknessCandidate(
                    source=
                        item.source,

                    priority=
                        item.priority,

                    thickness_m=
                        item.thickness_m,

                    thickness_px=
                        None,

                    calibration_pixels_per_meter=
                        None,

                    calibration_source_id=
                        None,

                    supporting_segment_ids=
                        [],

                    evidence=
                        list(
                            item.evidence
                        ),

                    state=
                        item.state,

                    promoted=
                        False,
                )
                for item
                in targeted_evidence
            ]

            # =================================================
            # ESPESOR — RASTER CALIBRADO CANDIDATO
            # =================================================

            raster_candidates = (
                self._raster_thickness_candidates(
                    group=
                        group,

                    wall_space_ids=
                        space_ids,

                    opencv_geometry=
                        opencv_geometry,

                    dimension_grounding=
                        dimension_grounding,
                )
            )

            thickness_candidates.extend(
                raster_candidates
            )

            # =================================================
            # RESOLVER PRIORIDADES 1/2 PROPORCIONADAS
            # =================================================

            (
                resolved_thickness,
                thickness_state,
                thickness_source,
                thickness_conflict,
            ) = self._resolve_supplied_thickness(
                candidates=
                    thickness_candidates,
            )

            # =================================================
            # REGLA DE DOMINIO
            # =================================================

            domain_applicable = (
                wall_id
                in domain_targets
                or group.id
                in domain_targets
                or any(
                    edge.id
                    in domain_targets
                    for edge
                    in group.edges
                )
            )

            if (
                resolved_thickness
                is None
                and not thickness_conflict
                and domain_applicable
            ):
                resolved_thickness = (
                    self
                    .DOMAIN_FINISHED_WALL_THICKNESS_M
                )

                thickness_state = (
                    "INFERIDO"
                )

                thickness_source = (
                    "quantia_domain_rule_finished_wall_minimum"
                )

                thickness_candidates.append(
                    WallThicknessCandidate(
                        source=
                            thickness_source,

                        priority=
                            THICKNESS_PRIORITY_DOMAIN_RULE,

                        thickness_m=
                            resolved_thickness,

                        thickness_px=
                            None,

                        calibration_pixels_per_meter=
                            None,

                        calibration_source_id=
                            None,

                        supporting_segment_ids=
                            [],

                        evidence=[
                            (
                                "Regla de dominio Quantia: "
                                "espesor terminado mínimo "
                                "0.15 m aplicado explícitamente "
                                "por contexto."
                            )
                        ],

                        state=
                            "INFERIDO",

                        promoted=
                            True,
                    )
                )

            # =================================================
            # MARCAR CANDIDATO PROMOVIDO
            # =================================================

            if (
                resolved_thickness
                is not None
                and thickness_source
                is not None
            ):
                for candidate in (
                    thickness_candidates
                ):
                    if (
                        candidate.source
                        == thickness_source
                        and candidate.thickness_m
                        is not None
                        and math.isclose(
                            candidate.thickness_m,
                            resolved_thickness,
                            rel_tol=0.0,
                            abs_tol=
                                self.NUMERIC_TOLERANCE,
                        )
                    ):
                        candidate.promoted = (
                            True
                        )

            if thickness_conflict:
                wall_state = (
                    "CONFLICTO"
                )

                conflicting_walls.append(
                    wall_id
                )

            if resolved_thickness is None:
                unresolved_thickness.append(
                    wall_id
                )

            # =================================================
            # RESULTADO MURO
            # =================================================

            walls.append(
                ResolvedWallGeometry(
                    id=
                        wall_id,

                    continuity_group_id=
                        group.id,

                    orientation=
                        group.orientation,

                    segments=
                        segments,

                    graph_edge_ids=[
                        edge.id
                        for edge
                        in group.edges
                    ],

                    space_ids=
                        sorted(
                            space_ids
                        ),

                    real_length_px=
                        real_length,

                    topological_length_px=
                        topological_length,

                    virtual_opening_length_px=
                        virtual_length,

                    thickness_m=
                        resolved_thickness,

                    thickness_state=
                        thickness_state,

                    thickness_source=
                        thickness_source,

                    thickness_candidates=
                        thickness_candidates,

                    openings=
                        wall_openings,

                    evidence_sources=
                        sorted(
                            evidence_sources
                        ),

                    confidence=
                        None,

                    state=
                        wall_state,

                    confirmed=
                        False,
                )
            )

        return WallGeometryResolverResult(
            page=
                topology.page,

            width_px=
                topology.width_px,

            height_px=
                topology.height_px,

            walls=
                walls,

            unresolved_thickness_wall_ids=
                unresolved_thickness,

            conflicting_wall_ids=
                sorted(
                    set(
                        conflicting_walls
                    )
                ),

            notes=[
                (
                    "Cada muro conserva su centerline como "
                    "grupo de continuidad topológica."
                ),
                (
                    "Los segmentos físicos y los bridges "
                    "virtuales de openings permanecen "
                    "diferenciados."
                ),
                (
                    "Los espacios a cada lado fueron "
                    "derivados de las faces Shapely y "
                    "permanecen sin confirmar."
                ),
                (
                    "Las asociaciones puerta/ventana ↔ muro "
                    "continúan como candidatas."
                ),
                (
                    "Las separaciones raster paralelas se "
                    "conservaron como candidatos de espesor "
                    "y no se promovieron automáticamente."
                ),
                (
                    "La regla de 0.15 m únicamente se aplica "
                    "a targets enviados explícitamente por "
                    "el contexto de dominio."
                ),
                (
                    "Todo elemento automático mantiene "
                    "confirmed=false."
                ),
            ],
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        topology: WallOpeningTopologyResult,
        shapely_geometry: ShapelyPlanGeometryResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> None:
        page = (
            topology.page
        )

        if (
            shapely_geometry.page
            != page
            or dimension_grounding.page
            != page
            or opencv_geometry.page
            != page
        ):
            raise ValueError(
                "Los servicios geométricos pertenecen "
                "a páginas distintas."
            )

        width = (
            topology.width_px
        )

        height = (
            topology.height_px
        )

        if (
            shapely_geometry.width_px
            != width
            or shapely_geometry.height_px
            != height
            or dimension_grounding.width_px
            != width
            or dimension_grounding.height_px
            != height
            or opencv_geometry.width_px
            != width
            or opencv_geometry.height_px
            != height
        ):
            raise ValueError(
                "Los servicios geométricos no utilizan "
                "el mismo raster canónico."
            )

    # ========================================================
    # TOLERANCIA
    # ========================================================

    @staticmethod
    def _coordinate_tolerance(
        geometry: OpenCVPlanGeometryResult,
    ) -> float:
        if (
            geometry.diagnostics
            is not None
        ):
            value = (
                geometry
                .diagnostics
                .parameters
                .axis_tolerance_px
            )

            if value > 0:
                return float(
                    value
                )

        return 1.0

    # ========================================================
    # GRUPOS DE CONTINUIDAD
    # ========================================================

    def _build_continuity_groups(
        self,
        *,
        graph_edges: list[
            ArchitecturalGraphEdge
        ],
        graph_nodes: list[
            ArchitecturalGraphNode
        ],
        tolerance: float,
    ) -> list[
        _ContinuityGroup
    ]:
        edge_lookup = {
            edge.id:
                edge
            for edge
            in graph_edges
        }

        node_edges: dict[
            str,
            list[str],
        ] = {}

        for edge in graph_edges:
            node_edges.setdefault(
                edge.start_node_id,
                [],
            ).append(
                edge.id
            )

            node_edges.setdefault(
                edge.end_node_id,
                [],
            ).append(
                edge.id
            )

        visited: set[str] = set()

        raw_groups: list[
            list[
                ArchitecturalGraphEdge
            ]
        ] = []

        for edge in graph_edges:
            if edge.id in visited:
                continue

            visited.add(
                edge.id
            )

            queue = [
                edge.id
            ]

            current_group: list[
                ArchitecturalGraphEdge
            ] = []

            while queue:
                current_id = (
                    queue.pop()
                )

                current = (
                    edge_lookup[
                        current_id
                    ]
                )

                current_group.append(
                    current
                )

                connected_ids = set(
                    node_edges.get(
                        current.start_node_id,
                        [],
                    )
                    + node_edges.get(
                        current.end_node_id,
                        [],
                    )
                )

                for neighbor_id in (
                    connected_ids
                ):
                    if neighbor_id in visited:
                        continue

                    neighbor = (
                        edge_lookup[
                            neighbor_id
                        ]
                    )

                    if not self._collinear_edges(
                        current,
                        neighbor,
                        tolerance=
                            tolerance,
                    ):
                        continue

                    visited.add(
                        neighbor_id
                    )

                    queue.append(
                        neighbor_id
                    )

            raw_groups.append(
                current_group
            )

        result: list[
            _ContinuityGroup
        ] = []

        for index, edges in enumerate(
            raw_groups,
            start=1,
        ):
            orientation = (
                edges[0].orientation
                if edges
                else "other"
            )

            result.append(
                _ContinuityGroup(
                    id=
                        f"WALL_GROUP_{index}",

                    orientation=
                        orientation,

                    edge_ids=[
                        edge.id
                        for edge
                        in edges
                    ],

                    edges=
                        edges,
                )
            )

        return result

    # ========================================================
    # COLINEALIDAD
    # ========================================================

    def _collinear_edges(
        self,
        first: ArchitecturalGraphEdge,
        second: ArchitecturalGraphEdge,
        *,
        tolerance: float,
    ) -> bool:
        if (
            first.orientation
            != second.orientation
        ):
            return False

        if first.orientation == "horizontal":
            first_axis = (
                first.y1
                + first.y2
            ) / 2.0

            second_axis = (
                second.y1
                + second.y2
            ) / 2.0

        elif first.orientation == "vertical":
            first_axis = (
                first.x1
                + first.x2
            ) / 2.0

            second_axis = (
                second.x1
                + second.x2
            ) / 2.0

        else:
            return False

        return (
            abs(
                first_axis
                - second_axis
            )
            <= tolerance
        )

    # ========================================================
    # ORDEN DE SEGMENTOS
    # ========================================================

    @staticmethod
    def _sort_group_edges(
        group: _ContinuityGroup,
    ) -> list[
        ArchitecturalGraphEdge
    ]:
        if (
            group.orientation
            == "vertical"
        ):
            return sorted(
                group.edges,
                key=lambda edge:
                    min(
                        edge.y1,
                        edge.y2,
                    ),
            )

        return sorted(
            group.edges,
            key=lambda edge:
                min(
                    edge.x1,
                    edge.x2,
                ),
        )

    # ========================================================
    # LADOS DEL MURO
    # ========================================================

    def _resolve_edge_sides(
        self,
        *,
        edge: ArchitecturalGraphEdge,
        shapely_geometry: ShapelyPlanGeometryResult,
    ) -> tuple[
        WallSideReference | None,
        WallSideReference | None,
        list[
            WallSideReference
        ],
        list[
            WallSideReference
        ],
        bool,
    ]:
        edge_geometry = LineString(
            [
                (
                    edge.x1,
                    edge.y1,
                ),
                (
                    edge.x2,
                    edge.y2,
                ),
            ]
        )

        side_a_candidates: list[
            WallSideReference
        ] = []

        side_b_candidates: list[
            WallSideReference
        ] = []

        for face in (
            shapely_geometry.faces
        ):
            polygon = (
                self._face_polygon(
                    face
                )
            )

            if polygon is None:
                continue

            shared = (
                polygon.boundary
                .intersection(
                    edge_geometry
                )
            )

            shared_length = float(
                shared.length
            )

            if (
                shared_length
                <= self.NUMERIC_TOLERANCE
            ):
                continue

            position = (
                self._face_position(
                    edge=
                        edge,

                    face=
                        face,
                )
            )

            semantics = [
                WallSideSemanticCandidate(
                    space_id=
                        candidate.space_id,

                    level=
                        candidate.nivel,

                    name=
                        candidate.nombre,

                    face_overlap_ratio=
                        candidate
                        .face_overlap_ratio,

                    bbox_overlap_ratio=
                        candidate
                        .bbox_overlap_ratio,

                    centroid_inside_localization=
                        candidate
                        .centroid_inside_localization,

                    confirmed=
                        False,
                )
                for candidate
                in face.semantic_candidates
            ]

            primary = (
                semantics[0]
                if semantics
                else None
            )

            reference = (
                WallSideReference(
                    face_id=
                        face.id,

                    position=
                        position,

                    shared_boundary_length_px=
                        shared_length,

                    semantic_candidates=
                        semantics,

                    primary_space_id=(
                        primary.space_id
                        if primary
                        else None
                    ),

                    primary_space_name=(
                        primary.name
                        if primary
                        else None
                    ),

                    primary_level=(
                        primary.level
                        if primary
                        else None
                    ),

                    confirmed=
                        False,
                )
            )

            if position in {
                "left",
                "top",
            }:
                side_a_candidates.append(
                    reference
                )

            else:
                side_b_candidates.append(
                    reference
                )

        side_a_candidates.sort(
            key=lambda item:
                -item.shared_boundary_length_px
        )

        side_b_candidates.sort(
            key=lambda item:
                -item.shared_boundary_length_px
        )

        side_a = (
            side_a_candidates[0]
            if len(
                side_a_candidates
            )
            == 1
            else None
        )

        side_b = (
            side_b_candidates[0]
            if len(
                side_b_candidates
            )
            == 1
            else None
        )

        side_conflict = (
            len(
                side_a_candidates
            )
            > 1
            or len(
                side_b_candidates
            )
            > 1
        )

        return (
            side_a,
            side_b,
            side_a_candidates,
            side_b_candidates,
            side_conflict,
        )

    # ========================================================
    # POLÍGONO FACE
    # ========================================================

    @staticmethod
    def _face_polygon(
        face: ArchitecturalFaceCandidate,
    ) -> Polygon | None:
        if (
            not face.shapely_valid
            or len(
                face.vertices
            )
            < 3
        ):
            return None

        polygon = Polygon(
            face.vertices
        )

        if (
            polygon.is_empty
            or not polygon.is_valid
            or polygon.area <= 0
        ):
            return None

        return polygon

    # ========================================================
    # POSICIÓN FACE RESPECTO A EDGE
    # ========================================================

    @staticmethod
    def _face_position(
        *,
        edge: ArchitecturalGraphEdge,
        face: ArchitecturalFaceCandidate,
    ) -> str:
        if (
            edge.orientation
            == "vertical"
        ):
            edge_x = (
                edge.x1
                + edge.x2
            ) / 2.0

            return (
                "left"
                if face.centroid_x
                < edge_x
                else "right"
            )

        edge_y = (
            edge.y1
            + edge.y2
        ) / 2.0

        return (
            "top"
            if face.centroid_y
            < edge_y
            else "bottom"
        )

    # ========================================================
    # OPENINGS POR EDGE
    # ========================================================

    def _openings_for_edge(
        self,
        *,
        edge: ArchitecturalGraphEdge,
        gaps: list[
            WallGapCandidate
        ],
        opening_lookup: dict[
            str,
            SemanticOpeningCandidate
        ],
    ) -> list[
        ResolvedWallOpeningReference
    ]:
        result: list[
            ResolvedWallOpeningReference
        ] = []

        for gap in gaps:
            supporting_edge = (
                edge.id
                in gap.supporting_edge_ids
            )

            virtual_bridge = (
                gap.virtual_edge_id
                == edge.id
            )

            if (
                not supporting_edge
                and not virtual_bridge
            ):
                continue

            association_type = (
                "virtual_gap_bridge"
                if virtual_bridge
                else "supporting_wall_segment"
            )

            for opening_id in (
                gap.semantic_opening_ids
            ):
                opening = (
                    opening_lookup.get(
                        opening_id
                    )
                )

                if opening is None:
                    continue

                result.append(
                    ResolvedWallOpeningReference(
                        opening_id=
                            opening.id,

                        opening_type=
                            opening.opening_type,

                        space_id=
                            opening.space_id,

                        level=
                            opening.level,

                        semantic_location=
                            opening.semantic_location,

                        direction=
                            opening.direction,

                        gap_id=
                            gap.id,

                        gap_length_px=
                            gap.gap_length_px,

                        virtual_edge_id=
                            gap.virtual_edge_id,

                        association_type=
                            association_type,

                        state=
                            "CANDIDATO",

                        confirmed=
                            False,
                    )
                )

        return result

    # ========================================================
    # EVIDENCIA DE ESPESOR DIRIGIDA
    # ========================================================

    @staticmethod
    def _targeted_thickness_evidence(
        *,
        wall_id: str,
        group: _ContinuityGroup,
        evidence: list[
            WallThicknessEvidence
        ],
    ) -> list[
        WallThicknessEvidence
    ]:
        result: list[
            WallThicknessEvidence
        ] = []

        edge_ids = {
            edge.id
            for edge
            in group.edges
        }

        for item in evidence:
            targets_group = (
                item.target_continuity_group_id
                == group.id
            )

            targets_edge = (
                item.target_graph_edge_id
                in edge_ids
            )

            # No aplicar evidencia sin target.
            if (
                not targets_group
                and not targets_edge
            ):
                continue

            if (
                item.thickness_m
                <= 0
            ):
                continue

            result.append(
                item
            )

        return result

    # ========================================================
    # RESOLVER EVIDENCIA DE ESPESOR
    # ========================================================

    def _resolve_supplied_thickness(
        self,
        *,
        candidates: list[
            WallThicknessCandidate
        ],
    ) -> tuple[
        float | None,
        str,
        str | None,
        bool,
    ]:
        promotable = [
            candidate
            for candidate
            in candidates
            if (
                candidate.thickness_m
                is not None
                and candidate.priority
                in {
                    THICKNESS_PRIORITY_EXPLICIT_DIMENSION,
                    THICKNESS_PRIORITY_VECTOR_FACE,
                }
            )
        ]

        if not promotable:
            return (
                None,
                "PENDIENTE",
                None,
                False,
            )

        best_priority = min(
            candidate.priority
            for candidate
            in promotable
        )

        preferred = [
            candidate
            for candidate
            in promotable
            if candidate.priority
            == best_priority
        ]

        values: list[float] = []

        for candidate in preferred:
            value = float(
                candidate.thickness_m
            )

            if any(
                math.isclose(
                    value,
                    existing,
                    rel_tol=0.0,
                    abs_tol=
                        self.NUMERIC_TOLERANCE,
                )
                for existing
                in values
            ):
                continue

            values.append(
                value
            )

        if len(values) > 1:
            return (
                None,
                "CONFLICTO",
                None,
                True,
            )

        value = (
            values[0]
        )

        matching = [
            candidate
            for candidate
            in preferred
            if (
                candidate.thickness_m
                is not None
                and math.isclose(
                    candidate.thickness_m,
                    value,
                    rel_tol=0.0,
                    abs_tol=
                        self.NUMERIC_TOLERANCE,
                )
            )
        ]

        sources = sorted(
            {
                candidate.source
                for candidate
                in matching
            }
        )

        for candidate in matching:
            candidate.promoted = (
                True
            )

        state = (
            "DETECTADO"
        )

        if any(
            candidate.state
            == "INFERIDO"
            for candidate
            in matching
        ):
            state = (
                "INFERIDO"
            )

        return (
            value,
            state,
            "+".join(
                sources
            ),
            False,
        )

    # ========================================================
    # CANDIDATOS DE ESPESOR RASTER
    # ========================================================

    def _raster_thickness_candidates(
        self,
        *,
        group: _ContinuityGroup,
        wall_space_ids: set[str],
        opencv_geometry: OpenCVPlanGeometryResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
    ) -> list[
        WallThicknessCandidate
    ]:
        result: list[
            WallThicknessCandidate
        ] = []

        calibrations = (
            self._wall_calibrations(
                orientation=
                    group.orientation,

                space_ids=
                    wall_space_ids,

                grounding=
                    dimension_grounding,
            )
        )

        if (
            group.orientation
            not in {
                "horizontal",
                "vertical",
            }
        ):
            return result

        source_segment_ids = {
            segment_id
            for edge
            in group.edges
            for segment_id
            in edge.source_segment_ids
            if not segment_id.startswith(
                "virtual:"
            )
        }

        reference_edges = [
            edge
            for edge
            in group.edges
            if (
                "topology_virtual"
                not in edge.sources
            )
        ]

        if not reference_edges:
            return result

        if group.orientation == "vertical":
            available_segments = (
                opencv_geometry
                .vertical_segments
            )

        else:
            available_segments = (
                opencv_geometry
                .horizontal_segments
            )

        seen_keys: set[
            tuple[
                str,
                str | None,
                int,
            ]
        ] = set()

        for edge in reference_edges:
            nearest = (
                self._nearest_parallel_segments(
                    edge=
                        edge,

                    segments=
                        available_segments,

                    excluded_ids=
                        source_segment_ids,
                )
            )

            for (
                side,
                parallel_segment,
                separation_px,
            ) in nearest:
                if calibrations:
                    for (
                        calibration_id,
                        pixels_per_meter,
                    ) in calibrations:
                        thickness_m = (
                            separation_px
                            / pixels_per_meter
                        )

                        key = (
                            parallel_segment.id,
                            calibration_id,
                            int(
                                round(
                                    separation_px
                                    * 1000
                                )
                            ),
                        )

                        if key in seen_keys:
                            continue

                        seen_keys.add(
                            key
                        )

                        result.append(
                            WallThicknessCandidate(
                                source=
                                    "raster_parallel_line",

                                priority=
                                    THICKNESS_PRIORITY_RASTER_CALIBRATED,

                                thickness_m=
                                    thickness_m,

                                thickness_px=
                                    separation_px,

                                calibration_pixels_per_meter=
                                    pixels_per_meter,

                                calibration_source_id=
                                    calibration_id,

                                supporting_segment_ids=[
                                    parallel_segment.id
                                ],

                                evidence=[
                                    (
                                        "Separación raster "
                                        f"{side} respecto al "
                                        "centerline candidato."
                                    )
                                ],

                                state=
                                    "CANDIDATO",

                                promoted=
                                    False,
                            )
                        )

                else:
                    key = (
                        parallel_segment.id,
                        None,
                        int(
                            round(
                                separation_px
                                * 1000
                            )
                        ),
                    )

                    if key in seen_keys:
                        continue

                    seen_keys.add(
                        key
                    )

                    result.append(
                        WallThicknessCandidate(
                            source=
                                "raster_parallel_line",

                            priority=
                                THICKNESS_PRIORITY_RASTER_CALIBRATED,

                            thickness_m=
                                None,

                            thickness_px=
                                separation_px,

                            calibration_pixels_per_meter=
                                None,

                            calibration_source_id=
                                None,

                            supporting_segment_ids=[
                                parallel_segment.id
                            ],

                            evidence=[
                                (
                                    "Separación raster "
                                    f"{side} sin calibración "
                                    "métrica disponible."
                                )
                            ],

                            state=
                                "CANDIDATO",

                            promoted=
                                False,
                        )
                    )

        return result

    # ========================================================
    # CALIBRACIONES DEL MURO
    # ========================================================

    @staticmethod
    def _wall_calibrations(
        *,
        orientation: str,
        space_ids: set[str],
        grounding: ArchitecturalDimensionGroundingResult,
    ) -> list[
        tuple[
            str,
            float,
        ]
    ]:
        # Espesor vertical se mide horizontalmente.
        # Espesor horizontal se mide verticalmente.

        if orientation == "vertical":
            required_axis = (
                "x"
            )

        elif orientation == "horizontal":
            required_axis = (
                "y"
            )

        else:
            return []

        result: list[
            tuple[
                str,
                float,
            ]
        ] = []

        for dimension in (
            grounding
            .resolved_space_dimensions
        ):
            if (
                dimension.space_id
                not in space_ids
            ):
                continue

            if (
                dimension.dimension_axis
                != required_axis
            ):
                continue

            if (
                dimension.pixels_per_meter
                <= 0
            ):
                continue

            result.append(
                (
                    dimension.id,
                    dimension
                    .pixels_per_meter,
                )
            )

        return result

    # ========================================================
    # PARALELAS MÁS CERCANAS
    # ========================================================

    def _nearest_parallel_segments(
        self,
        *,
        edge: ArchitecturalGraphEdge,
        segments: list[
            RasterLineSegment
        ],
        excluded_ids: set[str],
    ) -> list[
        tuple[
            str,
            RasterLineSegment,
            float,
        ]
    ]:
        negative: list[
            tuple[
                float,
                RasterLineSegment,
            ]
        ] = []

        positive: list[
            tuple[
                float,
                RasterLineSegment,
            ]
        ] = []

        if edge.orientation == "vertical":
            edge_axis = (
                edge.x1
                + edge.x2
            ) / 2.0

            edge_start = min(
                edge.y1,
                edge.y2,
            )

            edge_end = max(
                edge.y1,
                edge.y2,
            )

            for segment in segments:
                if segment.id in excluded_ids:
                    continue

                segment_start = min(
                    segment.y1,
                    segment.y2,
                )

                segment_end = max(
                    segment.y1,
                    segment.y2,
                )

                if (
                    self._interval_overlap(
                        edge_start,
                        edge_end,
                        segment_start,
                        segment_end,
                    )
                    <= 0
                ):
                    continue

                delta = (
                    segment.midpoint_x
                    - edge_axis
                )

                if (
                    abs(
                        delta
                    )
                    <= self.NUMERIC_TOLERANCE
                ):
                    continue

                if delta < 0:
                    negative.append(
                        (
                            abs(
                                delta
                            ),
                            segment,
                        )
                    )

                else:
                    positive.append(
                        (
                            abs(
                                delta
                            ),
                            segment,
                        )
                    )

        else:
            edge_axis = (
                edge.y1
                + edge.y2
            ) / 2.0

            edge_start = min(
                edge.x1,
                edge.x2,
            )

            edge_end = max(
                edge.x1,
                edge.x2,
            )

            for segment in segments:
                if segment.id in excluded_ids:
                    continue

                segment_start = min(
                    segment.x1,
                    segment.x2,
                )

                segment_end = max(
                    segment.x1,
                    segment.x2,
                )

                if (
                    self._interval_overlap(
                        edge_start,
                        edge_end,
                        segment_start,
                        segment_end,
                    )
                    <= 0
                ):
                    continue

                delta = (
                    segment.midpoint_y
                    - edge_axis
                )

                if (
                    abs(
                        delta
                    )
                    <= self.NUMERIC_TOLERANCE
                ):
                    continue

                if delta < 0:
                    negative.append(
                        (
                            abs(
                                delta
                            ),
                            segment,
                        )
                    )

                else:
                    positive.append(
                        (
                            abs(
                                delta
                            ),
                            segment,
                        )
                    )

        result: list[
            tuple[
                str,
                RasterLineSegment,
                float,
            ]
        ] = []

        if negative:
            distance, segment = min(
                negative,
                key=lambda item:
                    item[0],
            )

            result.append(
                (
                    "negative_side",
                    segment,
                    distance,
                )
            )

        if positive:
            distance, segment = min(
                positive,
                key=lambda item:
                    item[0],
            )

            result.append(
                (
                    "positive_side",
                    segment,
                    distance,
                )
            )

        return result

    # ========================================================
    # INTERVAL OVERLAP
    # ========================================================

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


# ============================================================
# FACTORY
# ============================================================


def get_wall_geometry_resolver(
) -> WallGeometryResolver:
    return WallGeometryResolver()