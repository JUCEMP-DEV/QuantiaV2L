from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Any

from app.legacy.quantia_spatial.architectural_graph_builder import (
    ArchitecturalGraphEdge,
    ArchitecturalGraphNode,
    ArchitecturalGraphResult,
)
from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
)
from app.legacy.quantia_spatial.quantia_extraction_reconciler import (
    QuantiaReconciliationResult,
)

# ============================================================
# ABERTURA SEMÁNTICA
# ============================================================


@dataclass(slots=True)
class SemanticOpeningCandidate:
    """
    Puerta o ventana detectada semánticamente.

    Todavía NO conocemos necesariamente:

        - muro exacto;
        - posición métrica;
        - gap gráfico exacto.

    Por eso una abertura puede quedar relacionada con varios
    gaps candidatos hasta la reconciliación final.
    """

    id: str

    opening_type: str

    space_id: str

    level: str

    semantic_location: str | None

    direction: str | None

    state: str

    confidence: float

    candidate_gap_ids: list[str] = field(default_factory=list)

    confirmed: bool = False

    source: str = "gemini_semantic"


# ============================================================
# GAP TOPOLÓGICO
# ============================================================


@dataclass(slots=True)
class WallGapCandidate:
    """
    Interrupción entre dos tramos colineales.

    Puede representar:

        - puerta;
        - ventana;
        - interrupción gráfica;
        - ruido;
        - geometría incompleta.

    Nunca se asume automáticamente que sea una abertura.
    """

    id: str

    orientation: str

    axis_coordinate_px: float

    x1: float
    y1: float

    x2: float
    y2: float

    gap_length_px: float

    space_ids: list[str] = field(default_factory=list)

    supporting_edge_ids: list[str] = field(default_factory=list)

    semantic_opening_ids: list[str] = field(default_factory=list)

    possible_opening_types: list[str] = field(default_factory=list)

    semantic_support: bool = False

    topology_bridge_created: bool = False

    virtual_edge_id: str | None = None

    state: str = "PENDIENTE"

    confirmed: bool = False


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class WallOpeningTopologyResult:
    """
    Resultado de aplicar continuidad topológica sobre
    aberturas candidatas.

    base_graph:
        grafo recibido sin cambios.

    augmented_graph:
        copia del grafo que puede contener aristas virtuales.

    openings:
        puertas/ventanas semánticas.

    gap_candidates:
        interrupciones geométricas detectadas.
    """

    page: int

    width_px: int
    height_px: int

    base_graph: ArchitecturalGraphResult

    augmented_graph: ArchitecturalGraphResult

    openings: list[SemanticOpeningCandidate] = field(default_factory=list)

    gap_candidates: list[WallGapCandidate] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# RUN INTERNO
# ============================================================


@dataclass(slots=True)
class _WallRun:
    """
    Tramo continuo resultado de fusionar aristas adyacentes
    pertenecientes al mismo espacio y eje geométrico.
    """

    orientation: str

    axis: float

    start: float
    end: float

    edge_ids: set[str] = field(default_factory=set)


# ============================================================
# SERVICIO
# ============================================================


class WallOpeningTopologyService:
    """
    Reconstruye continuidad topológica alrededor de
    puertas y ventanas candidatas.

    ==========================================================
    PRINCIPIO
    ==========================================================

    En un plano una puerta puede producir visualmente:

        muro ─────      ───── muro
                    ↑
                  puerta

    Geométricamente existen dos segmentos.

    Topológicamente sigue existiendo una frontera continua
    entre espacios.

    Quantia representa esto como:

        segmento real
        +
        abertura
        +
        continuidad virtual
        +
        segmento real

    ==========================================================
    REGLAS
    ==========================================================

    1. No se unen gaps indiscriminadamente.

    2. Los dos tramos deben ser colineales.

    3. Deben estar relacionados con el mismo espacio.

    4. Debe existir evidencia semántica de puerta o ventana
       en ese espacio para crear una continuidad virtual.

    5. La continuidad virtual:

           confirmed = False

    6. La abertura permanece como entidad independiente.

    7. No se convierte el ancho del gap de píxeles a metros.

    8. La asociación exacta abertura ↔ gap permanece pendiente
       hasta integrar evidencia específica del vano.
    """

    NUMERIC_TOLERANCE = 1e-6

    # ========================================================
    # API
    # ========================================================

    def analyze(
        self,
        *,
        graph: ArchitecturalGraphResult,
        reconciliation: QuantiaReconciliationResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> WallOpeningTopologyResult:
        self._validate_inputs(
            graph=graph,
            opencv_geometry=opencv_geometry,
        )

        base_graph = copy.deepcopy(graph)

        augmented_graph = copy.deepcopy(graph)

        axis_tolerance = self._axis_tolerance(opencv_geometry)

        openings = self._collect_openings(reconciliation)

        opening_by_space = self._opening_index_by_space(openings)

        raw_gaps: list[WallGapCandidate] = []

        # ====================================================
        # BUSCAR GAPS POR ESPACIO
        # ====================================================

        space_ids = sorted(
            {space_id for edge in graph.edges for space_id in edge.space_ids}
        )

        gap_counter = 0

        for space_id in space_ids:
            related_edges = [edge for edge in graph.edges if space_id in edge.space_ids]

            for orientation in (
                "horizontal",
                "vertical",
            ):
                orientation_edges = [
                    edge for edge in related_edges if edge.orientation == orientation
                ]

                clusters = self._cluster_by_axis(
                    orientation_edges,
                    orientation=orientation,
                    tolerance=axis_tolerance,
                )

                for cluster in clusters:
                    runs = self._build_runs(
                        cluster,
                        orientation=orientation,
                        tolerance=axis_tolerance,
                    )

                    if len(runs) < 2:
                        continue

                    for index in range(len(runs) - 1):
                        first = runs[index]

                        second = runs[index + 1]

                        gap_length = second.start - first.end

                        if gap_length <= axis_tolerance:
                            continue

                        gap_counter += 1

                        candidate = self._build_gap(
                            gap_id=(f"WALL_GAP_" f"{gap_counter}"),
                            space_id=space_id,
                            first=first,
                            second=second,
                            opening_candidates=opening_by_space.get(
                                space_id,
                                [],
                            ),
                        )

                        raw_gaps.append(candidate)

        # ====================================================
        # DEDUPLICAR GAPS FÍSICOS
        # ====================================================
        #
        # El mismo muro puede aparecer asociado a dos espacios.
        #
        # El gap físico debe existir una sola vez.
        # ====================================================

        gaps = self._deduplicate_gaps(
            raw_gaps,
            tolerance=axis_tolerance,
        )

        # ====================================================
        # RELACIONAR ABERTURAS ↔ GAPS
        # ====================================================

        opening_index = {opening.id: opening for opening in openings}

        for gap in gaps:
            for opening_id in gap.semantic_opening_ids:
                opening = opening_index.get(opening_id)

                if opening is None:
                    continue

                if gap.id not in opening.candidate_gap_ids:
                    opening.candidate_gap_ids.append(gap.id)

        # ====================================================
        # CREAR CONTINUIDADES VIRTUALES
        # ====================================================

        existing_pairs = {
            tuple(
                sorted(
                    (
                        edge.start_node_id,
                        edge.end_node_id,
                    )
                )
            )
            for edge in augmented_graph.edges
        }

        next_edge_number = len(augmented_graph.edges) + 1

        for gap in gaps:
            if not gap.semantic_support:
                gap.state = "GAP_SIN_ABERTURA_SEMANTICA"

                continue

            start_node = self._find_node(
                augmented_graph.nodes,
                x=gap.x1,
                y=gap.y1,
                tolerance=axis_tolerance,
            )

            end_node = self._find_node(
                augmented_graph.nodes,
                x=gap.x2,
                y=gap.y2,
                tolerance=axis_tolerance,
            )

            if start_node is None or end_node is None:
                gap.state = "ABERTURA_SIN_NODOS_TOPOLOGICOS"

                continue

            if start_node.id == end_node.id:
                gap.state = "GAP_DEGENERADO"

                continue

            pair = tuple(
                sorted(
                    (
                        start_node.id,
                        end_node.id,
                    )
                )
            )

            if pair in existing_pairs:
                gap.state = "CONTINUIDAD_YA_EXISTENTE"

                continue

            virtual_edge_id = f"AG_VIRTUAL_E_" f"{next_edge_number}"

            next_edge_number += 1

            virtual_edge = ArchitecturalGraphEdge(
                id=virtual_edge_id,
                start_node_id=start_node.id,
                end_node_id=end_node.id,
                x1=start_node.x,
                y1=start_node.y,
                x2=end_node.x,
                y2=end_node.y,
                orientation=gap.orientation,
                length_px=gap.gap_length_px,
                source_segment_ids=[f"virtual:{gap.id}"],
                sources=[
                    "topology_virtual",
                    "opening_semantic",
                ],
                space_ids=list(gap.space_ids),
                support_count=2,
                state="INFERIDO_APERTURA",
                confirmed=False,
            )

            augmented_graph.edges.append(virtual_edge)

            existing_pairs.add(pair)

            gap.topology_bridge_created = True

            gap.virtual_edge_id = virtual_edge_id

            gap.state = "CONTINUIDAD_VIRTUAL_CANDIDATA"

        # ====================================================
        # ACTUALIZAR GRADOS
        # ====================================================

        self._recalculate_degrees(augmented_graph)

        return WallOpeningTopologyResult(
            page=graph.page,
            width_px=graph.width_px,
            height_px=graph.height_px,
            base_graph=base_graph,
            augmented_graph=augmented_graph,
            openings=openings,
            gap_candidates=gaps,
            notes=[
                ("Las puertas y ventanas permanecen " "como entidades independientes."),
                ("Los gaps geométricos no fueron " "cerrados automáticamente."),
                (
                    "Solo los gaps colineales con soporte "
                    "semántico de abertura recibieron una "
                    "continuidad virtual candidata."
                ),
                ("Las aristas virtuales tienen " "confirmed=false."),
                (
                    "No se interpretó la longitud del gap "
                    "en píxeles como ancho métrico "
                    "de puerta o ventana."
                ),
                ("La asociación exacta abertura-gap " "permanece pendiente."),
            ],
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        graph: ArchitecturalGraphResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> None:
        if graph.page != opencv_geometry.page:
            raise ValueError("Grafo y OpenCV pertenecen " "a páginas distintas.")

        if (
            graph.width_px != opencv_geometry.width_px
            or graph.height_px != opencv_geometry.height_px
        ):
            raise ValueError("Grafo y OpenCV no utilizan " "el mismo raster.")

    # ========================================================
    # TOLERANCIA
    # ========================================================

    @staticmethod
    def _axis_tolerance(
        geometry: OpenCVPlanGeometryResult,
    ) -> float:
        if geometry.diagnostics is not None:
            value = geometry.diagnostics.parameters.axis_tolerance_px

            if value > 0:
                return float(value)

        return 1.0

    # ========================================================
    # ABERTURAS SEMÁNTICAS
    # ========================================================

    def _collect_openings(
        self,
        reconciliation: QuantiaReconciliationResult,
    ) -> list[SemanticOpeningCandidate]:
        result: list[SemanticOpeningCandidate] = []

        extraction = reconciliation.extraction

        for level in extraction.niveles:
            level_name = str(level.nombre)

            for space in level.espacios:
                space_id = str(space.id_propuesto)

                # --------------------------------------------
                # PUERTAS
                # --------------------------------------------

                for door in space.puertas:
                    result.append(
                        SemanticOpeningCandidate(
                            id=str(door.id_propuesto),
                            opening_type="puerta",
                            space_id=space_id,
                            level=level_name,
                            semantic_location=self._nullable_text(
                                getattr(
                                    door,
                                    "ubicacion",
                                    None,
                                )
                            ),
                            direction=self._nullable_text(
                                getattr(
                                    door,
                                    "hacia",
                                    None,
                                )
                            ),
                            state=self._state_value(
                                getattr(
                                    door,
                                    "estado",
                                    None,
                                )
                            ),
                            confidence=self._confidence(
                                getattr(
                                    door,
                                    "confianza",
                                    0.0,
                                )
                            ),
                            confirmed=False,
                        )
                    )

                # --------------------------------------------
                # VENTANAS
                # --------------------------------------------

                for window in space.ventanas:
                    result.append(
                        SemanticOpeningCandidate(
                            id=str(window.id_propuesto),
                            opening_type="ventana",
                            space_id=space_id,
                            level=level_name,
                            semantic_location=self._nullable_text(
                                getattr(
                                    window,
                                    "ubicacion",
                                    None,
                                )
                            ),
                            direction=None,
                            state=self._state_value(
                                getattr(
                                    window,
                                    "estado",
                                    None,
                                )
                            ),
                            confidence=self._confidence(
                                getattr(
                                    window,
                                    "confianza",
                                    0.0,
                                )
                            ),
                            confirmed=False,
                        )
                    )

        return result

    # ========================================================
    # ÍNDICE POR ESPACIO
    # ========================================================

    @staticmethod
    def _opening_index_by_space(
        openings: list[SemanticOpeningCandidate],
    ) -> dict[
        str,
        list[SemanticOpeningCandidate],
    ]:
        result: dict[
            str,
            list[SemanticOpeningCandidate],
        ] = {}

        for opening in openings:
            result.setdefault(
                opening.space_id,
                [],
            ).append(opening)

        return result

    # ========================================================
    # CLUSTER POR EJE
    # ========================================================

    def _cluster_by_axis(
        self,
        edges: list[ArchitecturalGraphEdge],
        *,
        orientation: str,
        tolerance: float,
    ) -> list[list[ArchitecturalGraphEdge]]:
        if not edges:
            return []

        ordered = sorted(
            edges,
            key=lambda edge: self._edge_axis(
                edge,
                orientation,
            ),
        )

        clusters: list[list[ArchitecturalGraphEdge]] = []

        for edge in ordered:
            axis = self._edge_axis(
                edge,
                orientation,
            )

            assigned = False

            for cluster in clusters:
                reference_axis = sum(
                    self._edge_axis(
                        item,
                        orientation,
                    )
                    for item in cluster
                ) / len(cluster)

                if abs(axis - reference_axis) <= tolerance:
                    cluster.append(edge)

                    assigned = True

                    break

            if not assigned:
                clusters.append([edge])

        return clusters

    # ========================================================
    # CREAR RUNS
    # ========================================================

    def _build_runs(
        self,
        edges: list[ArchitecturalGraphEdge],
        *,
        orientation: str,
        tolerance: float,
    ) -> list[_WallRun]:
        intervals: list[
            tuple[
                float,
                float,
                float,
                str,
            ]
        ] = []

        for edge in edges:
            axis = self._edge_axis(
                edge,
                orientation,
            )

            start, end = self._edge_interval(
                edge,
                orientation,
            )

            intervals.append(
                (
                    start,
                    end,
                    axis,
                    edge.id,
                )
            )

        intervals.sort(key=lambda item: item[0])

        runs: list[_WallRun] = []

        for (
            start,
            end,
            axis,
            edge_id,
        ) in intervals:
            if not runs:
                runs.append(
                    _WallRun(
                        orientation=orientation,
                        axis=axis,
                        start=start,
                        end=end,
                        edge_ids={edge_id},
                    )
                )

                continue

            current = runs[-1]

            if start <= current.end + tolerance:
                current.end = max(
                    current.end,
                    end,
                )

                current.edge_ids.add(edge_id)

                current.axis = (current.axis + axis) / 2.0

            else:
                runs.append(
                    _WallRun(
                        orientation=orientation,
                        axis=axis,
                        start=start,
                        end=end,
                        edge_ids={edge_id},
                    )
                )

        return runs

    # ========================================================
    # GAP
    # ========================================================

    @staticmethod
    def _build_gap(
        *,
        gap_id: str,
        space_id: str,
        first: _WallRun,
        second: _WallRun,
        opening_candidates: list[SemanticOpeningCandidate],
    ) -> WallGapCandidate:
        axis = (first.axis + second.axis) / 2.0

        if first.orientation == "horizontal":
            x1 = first.end

            y1 = axis

            x2 = second.start

            y2 = axis

        else:
            x1 = axis

            y1 = first.end

            x2 = axis

            y2 = second.start

        opening_ids = [opening.id for opening in opening_candidates]

        opening_types = sorted({opening.opening_type for opening in opening_candidates})

        semantic_support = bool(opening_ids)

        return WallGapCandidate(
            id=gap_id,
            orientation=first.orientation,
            axis_coordinate_px=axis,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            gap_length_px=math.hypot(
                x2 - x1,
                y2 - y1,
            ),
            space_ids=[space_id],
            supporting_edge_ids=sorted(first.edge_ids | second.edge_ids),
            semantic_opening_ids=opening_ids,
            possible_opening_types=opening_types,
            semantic_support=semantic_support,
            topology_bridge_created=False,
            virtual_edge_id=None,
            state=("ABERTURA_COMPATIBLE" if semantic_support else "PENDIENTE"),
            confirmed=False,
        )

    # ========================================================
    # DEDUPLICAR GAPS
    # ========================================================

    def _deduplicate_gaps(
        self,
        gaps: list[WallGapCandidate],
        *,
        tolerance: float,
    ) -> list[WallGapCandidate]:
        result: list[WallGapCandidate] = []

        for gap in gaps:
            existing = None

            for item in result:
                if item.orientation != gap.orientation:
                    continue

                if self._same_gap_geometry(
                    item,
                    gap,
                    tolerance=tolerance,
                ):
                    existing = item

                    break

            if existing is None:
                result.append(gap)

                continue

            for space_id in gap.space_ids:
                if space_id not in existing.space_ids:
                    existing.space_ids.append(space_id)

            for edge_id in gap.supporting_edge_ids:
                if edge_id not in existing.supporting_edge_ids:
                    existing.supporting_edge_ids.append(edge_id)

            for opening_id in gap.semantic_opening_ids:
                if opening_id not in existing.semantic_opening_ids:
                    existing.semantic_opening_ids.append(opening_id)

            for opening_type in gap.possible_opening_types:
                if opening_type not in existing.possible_opening_types:
                    existing.possible_opening_types.append(opening_type)

            existing.semantic_support = (
                existing.semantic_support or gap.semantic_support
            )

        for index, gap in enumerate(
            result,
            start=1,
        ):
            gap.id = f"WALL_GAP_{index}"

            gap.space_ids.sort()

            gap.supporting_edge_ids.sort()

            gap.semantic_opening_ids.sort()

            gap.possible_opening_types.sort()

        return result

    # ========================================================
    # MISMO GAP
    # ========================================================

    @staticmethod
    def _same_gap_geometry(
        first: WallGapCandidate,
        second: WallGapCandidate,
        *,
        tolerance: float,
    ) -> bool:
        return (
            abs(first.x1 - second.x1) <= tolerance
            and abs(first.y1 - second.y1) <= tolerance
            and abs(first.x2 - second.x2) <= tolerance
            and abs(first.y2 - second.y2) <= tolerance
        )

    # ========================================================
    # EJE DE EDGE
    # ========================================================

    @staticmethod
    def _edge_axis(
        edge: ArchitecturalGraphEdge,
        orientation: str,
    ) -> float:
        if orientation == "horizontal":
            return (edge.y1 + edge.y2) / 2.0

        return (edge.x1 + edge.x2) / 2.0

    # ========================================================
    # INTERVALO
    # ========================================================

    @staticmethod
    def _edge_interval(
        edge: ArchitecturalGraphEdge,
        orientation: str,
    ) -> tuple[
        float,
        float,
    ]:
        if orientation == "horizontal":
            return (
                min(
                    edge.x1,
                    edge.x2,
                ),
                max(
                    edge.x1,
                    edge.x2,
                ),
            )

        return (
            min(
                edge.y1,
                edge.y2,
            ),
            max(
                edge.y1,
                edge.y2,
            ),
        )

    # ========================================================
    # ENCONTRAR NODO
    # ========================================================

    @staticmethod
    def _find_node(
        nodes: list[ArchitecturalGraphNode],
        *,
        x: float,
        y: float,
        tolerance: float,
    ) -> ArchitecturalGraphNode | None:
        best = None
        best_distance = None

        for node in nodes:
            distance = math.hypot(
                node.x - x,
                node.y - y,
            )

            if distance > tolerance:
                continue

            if best_distance is None or distance < best_distance:
                best = node

                best_distance = distance

        return best

    # ========================================================
    # RECALCULAR GRADOS
    # ========================================================

    @staticmethod
    def _recalculate_degrees(
        graph: ArchitecturalGraphResult,
    ) -> None:
        counts = {node.id: 0 for node in graph.nodes}

        for edge in graph.edges:
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

        for node in graph.nodes:
            node.degree = counts.get(
                node.id,
                0,
            )

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _nullable_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(value).strip()

        return text if text else None

    @staticmethod
    def _confidence(
        value: Any,
    ) -> float:
        if isinstance(
            value,
            bool,
        ):
            return 0.0

        if not isinstance(
            value,
            (int, float),
        ):
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    @staticmethod
    def _state_value(
        value: Any,
    ) -> str:
        if value is None:
            return "NO_IDENTIFICADO"

        enum_value = getattr(
            value,
            "value",
            None,
        )

        if enum_value is not None:
            return str(enum_value)

        return str(value)


# ============================================================
# FACTORY
# ============================================================


def get_wall_opening_topology_service() -> WallOpeningTopologyService:
    return WallOpeningTopologyService()
