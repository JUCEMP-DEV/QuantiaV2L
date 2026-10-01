from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
    field,
)
from typing import Any

from app.legacy.quantia_spatial.architectural_dimension_grounding_service import (
    ArchitecturalDimensionGroundingResult,
    AxisAnchorCandidate,
)
from app.legacy.quantia_spatial.opencv_plan_geometry_service import (
    OpenCVPlanGeometryResult,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    BoundaryCandidate,
    PlanGeometryReconciliationResult,
)

# ============================================================
# TRAMO ARQUITECTÓNICO REPRESENTATIVO
# ============================================================


@dataclass(slots=True)
class ArchitecturalWallRun:
    id: str

    orientation: str

    x1: float
    y1: float
    x2: float
    y2: float

    length_px: float

    source_segment_ids: list[str] = field(default_factory=list)

    face_segment_ids: list[str] = field(default_factory=list)

    endpoint_support_ids: list[str] = field(default_factory=list)

    space_ids: list[str] = field(default_factory=list)

    space_sides: dict[str, str] = field(default_factory=dict)

    levels: list[str] = field(default_factory=list)

    axis_ids: list[str] = field(default_factory=list)

    sources: list[str] = field(default_factory=list)

    support_count: int = 1

    state: str = "CANDIDATO"

    confirmed: bool = False


# ============================================================
# CENTERLINE ARQUITECTÓNICO CANDIDATO
# ============================================================


@dataclass(slots=True)
class ArchitecturalWallCenterline:
    id: str

    orientation: str

    x1: float
    y1: float
    x2: float
    y2: float

    length_px: float

    thickness_px: float

    overlap_px: float
    overlap_ratio: float

    pairing_distance_limit_px: float

    wall_run_ids: list[str] = field(default_factory=list)

    face_segment_ids: list[str] = field(default_factory=list)

    space_ids: list[str] = field(default_factory=list)

    levels: list[str] = field(default_factory=list)

    state: str = "CANDIDATO"

    confirmed: bool = False


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class ArchitecturalWallAbstractionResult:
    page: int

    width_px: int
    height_px: int

    wall_runs: list[ArchitecturalWallRun] = field(default_factory=list)

    centerlines: list[ArchitecturalWallCenterline] = field(default_factory=list)

    discarded_boundary_count: int = 0

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# SERVICIO
# ============================================================


class ArchitecturalWallAbstractionService:
    """
    Convierte límites geométricos reconciliados en una
    representación arquitectónica simplificada.

    Entrada:

        PlanGeometryReconciliationResult
        +
        ArchitecturalDimensionGroundingResult
        +
        OpenCVPlanGeometryResult

    Estrategia:

        boundary candidates
            ↓
        mejor candidato por lado del espacio
            ↓
        coordenada representativa del límite
            ↓
        cruce con límites ortogonales
            ↓
        wall runs continuos
            ↓
        deduplicación geométrica por nivel

    IMPORTANTE:

        - OpenCV sigue siendo evidencia;
        - los extremos crudos de OpenCV no definen
          automáticamente la longitud visual;
        - un wall run NO es muro confirmado;
        - un eje suma evidencia pero no es obligatorio;
        - no se inventan métricas;
        - confirmed siempre permanece False.
    """

    # ========================================================
    # API
    # ========================================================
    def abstract(
        self,
        *,
        reconciliation: PlanGeometryReconciliationResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> ArchitecturalWallAbstractionResult:
        self._validate_inputs(
            reconciliation=reconciliation,
            dimension_grounding=dimension_grounding,
            opencv_geometry=opencv_geometry,
        )

        tolerance = self._coordinate_tolerance(opencv_geometry)

        registry: dict[
            tuple[
                str,
                str,
                int,
                int,
                int,
                int,
            ],
            ArchitecturalWallRun,
        ] = {}

        total_candidates = 0
        selected_candidates = 0
        counter = 0

        for space in reconciliation.spaces:
            selected_by_side: dict[
                str,
                BoundaryCandidate,
            ] = {}

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

                total_candidates += len(candidates)

                selected = self._select_candidate(
                    candidates=candidates,
                    axes=dimension_grounding.axis_anchors,
                    tolerance=tolerance,
                )

                if selected is None:
                    continue

                selected_by_side[side] = selected

            for side in (
                "left",
                "right",
                "top",
                "bottom",
            ):
                selected = selected_by_side.get(side)

                if selected is None:
                    continue

                coordinates = self._representative_run_coordinates(
                    side=side,
                    selected_by_side=selected_by_side,
                )

                if coordinates is None:
                    continue

                (
                    x1,
                    y1,
                    x2,
                    y2,
                ) = coordinates

                if selected.orientation == "vertical":
                    length_px = abs(y2 - y1)

                elif selected.orientation == "horizontal":
                    length_px = abs(x2 - x1)

                else:
                    continue

                if length_px <= 0:
                    continue

                selected_candidates += 1

                matched_axes = self._matching_axes(
                    candidate=selected,
                    axes=dimension_grounding.axis_anchors,
                    tolerance=tolerance,
                )

                evidence_candidates = self._run_evidence_candidates(
                    side=side,
                    selected_by_side=selected_by_side,
                )

                face_segment_ids = self._face_segment_group(
                    selected=selected,
                    opencv_geometry=opencv_geometry,
                )

                if selected.opencv_segment_id not in face_segment_ids:
                    face_segment_ids.append(selected.opencv_segment_id)

                face_segment_ids = sorted(set(face_segment_ids))

                endpoint_support_ids = sorted(
                    {
                        candidate.opencv_segment_id
                        for candidate in evidence_candidates
                        if (candidate.opencv_segment_id != selected.opencv_segment_id)
                    }
                )

                source_segment_ids = sorted(
                    set(face_segment_ids + endpoint_support_ids)
                )

                sources = sorted(
                    {
                        source
                        for candidate in evidence_candidates
                        for source in candidate.sources
                    }
                )

                support_count = max(
                    (candidate.support_count for candidate in evidence_candidates),
                    default=selected.support_count,
                )

                key = self._wall_run_key(
                    level=space.nivel,
                    orientation=selected.orientation,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    tolerance=tolerance,
                )

                existing = registry.get(key)

                if existing is not None:
                    self._merge_metadata(
                        wall_run=existing,
                        space_id=space.id_propuesto,
                        side=side,
                        level=space.nivel,
                        axis_ids=[axis.id for axis in matched_axes],
                        source_segment_ids=(source_segment_ids),
                        face_segment_ids=(face_segment_ids),
                        endpoint_support_ids=(endpoint_support_ids),
                        sources=sources,
                        support_count=support_count,
                    )

                    continue

                counter += 1

                wall_run = ArchitecturalWallRun(
                    id=f"WALL_RUN_{counter}",
                    orientation=(selected.orientation),
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    length_px=float(length_px),
                    source_segment_ids=(source_segment_ids),
                    face_segment_ids=(face_segment_ids),
                    endpoint_support_ids=(endpoint_support_ids),
                    space_ids=[space.id_propuesto],
                    space_sides={space.id_propuesto: side},
                    levels=[space.nivel],
                    axis_ids=[axis.id for axis in matched_axes],
                    sources=sources,
                    support_count=(support_count),
                    state="CANDIDATO",
                    confirmed=False,
                )

                registry[key] = wall_run

        wall_runs = list(registry.values())

        wall_runs.sort(
            key=lambda item: int(
                item.id.rsplit(
                    "_",
                    1,
                )[-1]
            )
        )

        centerlines = self.build_centerline_candidates(
            wall_runs=wall_runs,
            opencv_geometry=opencv_geometry,
        )

        return ArchitecturalWallAbstractionResult(
            page=reconciliation.page,
            width_px=reconciliation.width_px,
            height_px=reconciliation.height_px,
            wall_runs=wall_runs,
            centerlines=centerlines,
            discarded_boundary_count=max(
                0,
                total_candidates - selected_candidates,
            ),
            notes=[
                (
                    "Se seleccionó un límite representativo "
                    "por lado de cada espacio reconciliado."
                ),
                (
                    "Los fragmentos OpenCV compatibles con "
                    "la cara seleccionada se conservaron como "
                    "evidencia agrupada de esa cara."
                ),
                (
                    "La agrupación usa exclusivamente "
                    "tolerancias derivadas de los parámetros "
                    "reales del detector OpenCV."
                ),
                (
                    "Los segmentos ortogonales utilizados "
                    "para determinar extremos permanecen "
                    "separados de los segmentos de cara."
                ),
                ("Cada wall run conserva el lado del espacio del que fue obtenido."),
                (
                    "Las caras opuestas compatibles pueden "
                    "producir centerlines candidatos."
                ),
                (
                    "El espesor registrado en centerlines "
                    "permanece únicamente en píxeles raster "
                    "observados."
                ),
                (
                    "source_segment_ids conserva la unión "
                    "para compatibilidad con consumidores "
                    "existentes."
                ),
                ("No se realizó conversión de píxeles a metros."),
                ("Ningún wall run ni centerline fue confirmado automáticamente."),
            ],
        )

    # ========================================================
    # COORDENADAS REPRESENTATIVAS DEL WALL RUN
    # ========================================================

    @classmethod
    def _representative_run_coordinates(
        cls,
        *,
        side: str,
        selected_by_side: dict[
            str,
            BoundaryCandidate,
        ],
    ) -> (
        tuple[
            float,
            float,
            float,
            float,
        ]
        | None
    ):
        selected = selected_by_side.get(side)

        if selected is None:
            return None

        # ====================================================
        # MURO VERTICAL
        # ====================================================

        if side in (
            "left",
            "right",
        ):
            top = selected_by_side.get("top")

            bottom = selected_by_side.get("bottom")

            if top is None or bottom is None:
                return None

            x = cls._boundary_coordinate(selected)

            y_top = cls._boundary_coordinate(top)

            y_bottom = cls._boundary_coordinate(bottom)

            y1 = min(
                y_top,
                y_bottom,
            )

            y2 = max(
                y_top,
                y_bottom,
            )

            return (
                x,
                y1,
                x,
                y2,
            )

        # ====================================================
        # MURO HORIZONTAL
        # ====================================================

        if side in (
            "top",
            "bottom",
        ):
            left = selected_by_side.get("left")

            right = selected_by_side.get("right")

            if left is None or right is None:
                return None

            y = cls._boundary_coordinate(selected)

            x_left = cls._boundary_coordinate(left)

            x_right = cls._boundary_coordinate(right)

            x1 = min(
                x_left,
                x_right,
            )

            x2 = max(
                x_left,
                x_right,
            )

            return (
                x1,
                y,
                x2,
                y,
            )

        return None

    # ========================================================
    # COORDENADA ARQUITECTÓNICA DEL LÍMITE
    # ========================================================

    @staticmethod
    def _boundary_coordinate(
        boundary: BoundaryCandidate,
    ) -> float:
        if boundary.orientation == "vertical":
            return float((boundary.x1 + boundary.x2) / 2.0)

        if boundary.orientation == "horizontal":
            return float((boundary.y1 + boundary.y2) / 2.0)

        raise ValueError("BoundaryCandidate sin orientación arquitectónica soportada.")

    # ========================================================
    # EVIDENCIA GEOMÉTRICA DEL WALL RUN
    # ========================================================

    @staticmethod
    def _run_evidence_candidates(
        *,
        side: str,
        selected_by_side: dict[
            str,
            BoundaryCandidate,
        ],
    ) -> list[BoundaryCandidate]:
        if side in (
            "left",
            "right",
        ):
            evidence_sides = (
                side,
                "top",
                "bottom",
            )

        elif side in (
            "top",
            "bottom",
        ):
            evidence_sides = (
                side,
                "left",
                "right",
            )

        else:
            return []

        result: list[BoundaryCandidate] = []

        seen: set[str] = set()

        for evidence_side in evidence_sides:
            candidate = selected_by_side.get(evidence_side)

            if candidate is None:
                continue

            if candidate.opencv_segment_id in seen:
                continue

            seen.add(candidate.opencv_segment_id)

            result.append(candidate)

        return result

        # ========================================================

    # CENTERLINES ARQUITECTÓNICOS CANDIDATOS
    # ========================================================

    def build_centerline_candidates(
        self,
        *,
        wall_runs: list[ArchitecturalWallRun],
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> list[ArchitecturalWallCenterline]:
        """
        Construye candidatos de centerline a partir de pares
        de caras arquitectónicas opuestas.

        Esta función:

        - NO modifica wall_runs;
        - NO modifica ArchitecturalGraph;
        - NO modifica Shapely;
        - NO convierte píxeles a metros;
        - NO confirma muros automáticamente.

        La distancia máxima de emparejamiento se deriva
        exclusivamente de parámetros reales del detector
        OpenCV de la ejecución actual.
        """

        diagnostics = opencv_geometry.diagnostics

        axis_tolerance = 1.0
        merge_gap = 1.0

        if diagnostics is not None:
            parameters = diagnostics.parameters

            if parameters.axis_tolerance_px > 0:
                axis_tolerance = float(parameters.axis_tolerance_px)

            if parameters.merge_gap_px > 0:
                merge_gap = float(parameters.merge_gap_px)

        pairing_distance_limit = (2.0 * merge_gap) + axis_tolerance

        face_geometry: dict[
            str,
            dict[str, float],
        ] = {}

        for wall_run in wall_runs:
            geometry = self._reconstructed_face_geometry(
                wall_run=wall_run,
                opencv_geometry=opencv_geometry,
            )

            if geometry is None:
                continue

            face_geometry[wall_run.id] = geometry

        candidates: list[ArchitecturalWallCenterline] = []

        counter = 0

        for index, first in enumerate(wall_runs):
            first_geometry = face_geometry.get(first.id)

            if first_geometry is None:
                continue

            for second in wall_runs[index + 1 :]:
                second_geometry = face_geometry.get(second.id)

                if second_geometry is None:
                    continue

                if first.orientation != second.orientation:
                    continue

                shared_levels = sorted(set(first.levels) & set(second.levels))

                if not shared_levels:
                    continue

                if set(first.space_ids) & set(second.space_ids):
                    continue

                first_sides = set(first.space_sides.values())

                second_sides = set(second.space_sides.values())

                first_coordinate = first_geometry["coordinate"]

                second_coordinate = second_geometry["coordinate"]

                if first.orientation == "vertical":
                    faces_each_other = (
                        "right" in first_sides
                        and "left" in second_sides
                        and first_coordinate < second_coordinate
                    ) or (
                        "left" in first_sides
                        and "right" in second_sides
                        and second_coordinate < first_coordinate
                    )

                elif first.orientation == "horizontal":
                    faces_each_other = (
                        "bottom" in first_sides
                        and "top" in second_sides
                        and first_coordinate < second_coordinate
                    ) or (
                        "top" in first_sides
                        and "bottom" in second_sides
                        and second_coordinate < first_coordinate
                    )

                else:
                    continue

                if not faces_each_other:
                    continue

                distance = abs(first_coordinate - second_coordinate)

                if distance > pairing_distance_limit:
                    continue

                overlap_start = max(
                    first_geometry["start"],
                    second_geometry["start"],
                )

                overlap_end = min(
                    first_geometry["end"],
                    second_geometry["end"],
                )

                overlap = overlap_end - overlap_start

                if overlap <= 0:
                    continue

                first_length = first_geometry["end"] - first_geometry["start"]

                second_length = second_geometry["end"] - second_geometry["start"]

                shorter_length = min(
                    first_length,
                    second_length,
                )

                overlap_ratio = overlap / shorter_length if shorter_length > 0 else 0.0

                center_coordinate = (first_coordinate + second_coordinate) / 2.0

                if first.orientation == "vertical":
                    x1 = center_coordinate
                    y1 = overlap_start
                    x2 = center_coordinate
                    y2 = overlap_end

                else:
                    x1 = overlap_start
                    y1 = center_coordinate
                    x2 = overlap_end
                    y2 = center_coordinate

                counter += 1

                candidates.append(
                    ArchitecturalWallCenterline(
                        id=f"CENTERLINE_{counter}",
                        orientation=first.orientation,
                        x1=float(x1),
                        y1=float(y1),
                        x2=float(x2),
                        y2=float(y2),
                        length_px=float(overlap),
                        thickness_px=float(distance),
                        overlap_px=float(overlap),
                        overlap_ratio=float(overlap_ratio),
                        pairing_distance_limit_px=float(pairing_distance_limit),
                        wall_run_ids=[
                            first.id,
                            second.id,
                        ],
                        face_segment_ids=sorted(
                            set(first.face_segment_ids + second.face_segment_ids)
                        ),
                        space_ids=sorted(set(first.space_ids + second.space_ids)),
                        levels=shared_levels,
                        state="CANDIDATO",
                        confirmed=False,
                    )
                )

        return candidates

    def _reconstructed_face_geometry(
        self,
        *,
        wall_run: ArchitecturalWallRun,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> dict[str, float] | None:
        """
        Obtiene la geometría representativa de una cara
        reconstruida usando sus face_segment_ids.

        La coordenada transversal se calcula como promedio
        ponderado por longitud de los fragmentos observados.
        """

        if not wall_run.face_segment_ids:
            return None

        if wall_run.orientation == "vertical":
            segments = [
                segment
                for segment in opencv_geometry.vertical_segments
                if str(segment.id) in wall_run.face_segment_ids
            ]

            if not segments:
                return None

            total_weight = sum(
                max(
                    float(segment.length_px),
                    0.0,
                )
                for segment in segments
            )

            if total_weight <= 0:
                return None

            coordinate = (
                sum(
                    float(segment.midpoint_x) * float(segment.length_px)
                    for segment in segments
                )
                / total_weight
            )

            start = min(
                min(
                    float(segment.y1),
                    float(segment.y2),
                )
                for segment in segments
            )

            end = max(
                max(
                    float(segment.y1),
                    float(segment.y2),
                )
                for segment in segments
            )

        elif wall_run.orientation == "horizontal":
            segments = [
                segment
                for segment in opencv_geometry.horizontal_segments
                if str(segment.id) in wall_run.face_segment_ids
            ]

            if not segments:
                return None

            total_weight = sum(
                max(
                    float(segment.length_px),
                    0.0,
                )
                for segment in segments
            )

            if total_weight <= 0:
                return None

            coordinate = (
                sum(
                    float(segment.midpoint_y) * float(segment.length_px)
                    for segment in segments
                )
                / total_weight
            )

            start = min(
                min(
                    float(segment.x1),
                    float(segment.x2),
                )
                for segment in segments
            )

            end = max(
                max(
                    float(segment.x1),
                    float(segment.x2),
                )
                for segment in segments
            )

        else:
            return None

        if end <= start:
            return None

        return {
            "coordinate": float(coordinate),
            "start": float(start),
            "end": float(end),
        }

    def _face_segment_group(
        self,
        *,
        selected: BoundaryCandidate,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> list[str]:
        """
        Recupera fragmentos OpenCV que pueden pertenecer
        a la misma cara gráfica que el segmento seleccionado.

        No crea todavía una geometría nueva.
        """

        diagnostics = opencv_geometry.diagnostics

        axis_tolerance = 1.0
        merge_gap = 1.0

        if diagnostics is not None:
            parameters = diagnostics.parameters

            if parameters.axis_tolerance_px > 0:
                axis_tolerance = float(parameters.axis_tolerance_px)

            if parameters.merge_gap_px > 0:
                merge_gap = float(parameters.merge_gap_px)

        coordinate_tolerance = merge_gap

        longitudinal_gap_tolerance = merge_gap + axis_tolerance

        if selected.orientation == "vertical":
            segments = list(opencv_geometry.vertical_segments)

            seed_coordinate = (selected.x1 + selected.x2) / 2.0

            def coordinate(
                segment: Any,
            ) -> float:
                return float(segment.midpoint_x)

            def interval(
                segment: Any,
            ) -> tuple[float, float]:
                return (
                    min(
                        float(segment.y1),
                        float(segment.y2),
                    ),
                    max(
                        float(segment.y1),
                        float(segment.y2),
                    ),
                )

        elif selected.orientation == "horizontal":
            segments = list(opencv_geometry.horizontal_segments)

            seed_coordinate = (selected.y1 + selected.y2) / 2.0

            def coordinate(
                segment: Any,
            ) -> float:
                return float(segment.midpoint_y)

            def interval(
                segment: Any,
            ) -> tuple[float, float]:
                return (
                    min(
                        float(segment.x1),
                        float(segment.x2),
                    ),
                    max(
                        float(segment.x1),
                        float(segment.x2),
                    ),
                )

        else:
            return [selected.opencv_segment_id]

        segment_by_id = {str(segment.id): segment for segment in segments}

        seed = segment_by_id.get(selected.opencv_segment_id)

        if seed is None:
            return [selected.opencv_segment_id]

        compatible = [
            segment
            for segment in segments
            if (abs(coordinate(segment) - seed_coordinate) <= coordinate_tolerance)
        ]

        grouped_ids: set[str] = {str(seed.id)}

        changed = True

        while changed:
            changed = False

            grouped_segments = [
                segment_by_id[segment_id]
                for segment_id in grouped_ids
                if segment_id in segment_by_id
            ]

            for candidate in compatible:
                candidate_id = str(candidate.id)

                if candidate_id in grouped_ids:
                    continue

                candidate_start, candidate_end = interval(candidate)

                for grouped in grouped_segments:
                    grouped_start, grouped_end = interval(grouped)

                    gap = self._interval_gap(
                        first_start=grouped_start,
                        first_end=grouped_end,
                        second_start=candidate_start,
                        second_end=candidate_end,
                    )

                    if gap <= longitudinal_gap_tolerance:
                        grouped_ids.add(candidate_id)

                        changed = True
                        break

        return sorted(grouped_ids)

    # ========================================================
    # DISTANCIA ENTRE INTERVALOS
    # ========================================================

    @staticmethod
    def _interval_gap(
        *,
        first_start: float,
        first_end: float,
        second_start: float,
        second_end: float,
    ) -> float:
        first_min = min(
            first_start,
            first_end,
        )

        first_max = max(
            first_start,
            first_end,
        )

        second_min = min(
            second_start,
            second_end,
        )

        second_max = max(
            second_start,
            second_end,
        )

        if first_max >= second_min and second_max >= first_min:
            return 0.0

        if first_max < second_min:
            return float(second_min - first_max)

        return float(first_min - second_max)

    # ========================================================
    # CLAVE GEOMÉTRICA PARA DEDUPLICACIÓN
    # ========================================================

    @staticmethod
    def _wall_run_key(
        *,
        level: str,
        orientation: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        tolerance: float,
    ) -> tuple[
        str,
        str,
        int,
        int,
        int,
        int,
    ]:
        safe_tolerance = tolerance if tolerance > 0 else 1.0

        return (
            str(level or ""),
            orientation,
            round(x1 / safe_tolerance),
            round(y1 / safe_tolerance),
            round(x2 / safe_tolerance),
            round(y2 / safe_tolerance),
        )

    # ========================================================
    # SELECCIÓN DE CANDIDATO
    # ========================================================

    def _select_candidate(
        self,
        *,
        candidates: list[BoundaryCandidate],
        axes: list[AxisAnchorCandidate],
        tolerance: float,
    ) -> BoundaryCandidate | None:
        if not candidates:
            return None

        # ====================================================
        # BANDA ARQUITECTÓNICA MÁS PRÓXIMA AL BORDE DEL ESPACIO
        # ====================================================
        #
        # reconciliation conserva TODOS los candidatos porque
        # DimensionGrounding puede necesitarlos.
        #
        # La abstracción de muros, en cambio, trabaja únicamente
        # con la banda geométrica más próxima al límite estimado
        # del espacio para reducir mobiliario, sanitarios,
        # símbolos y detalles interiores.
        #
        # Esto todavía:
        #
        #   - no confirma muros;
        #   - no empareja caras paralelas;
        #   - no crea centerlines.
        # ====================================================

        nearest_distance = min(
            candidate.distance_to_bbox_edge_px for candidate in candidates
        )

        effective_tolerance = max(
            float(tolerance),
            0.0,
        )

        boundary_band = [
            candidate
            for candidate in candidates
            if (
                candidate.distance_to_bbox_edge_px
                <= nearest_distance + effective_tolerance
            )
        ]

        if not boundary_band:
            return None

        def ranking(
            candidate: BoundaryCandidate,
        ) -> tuple[
            int,
            int,
            int,
            float,
            float,
        ]:
            axis_support = bool(
                self._matching_axes(
                    candidate=candidate,
                    axes=axes,
                    tolerance=tolerance,
                )
            )

            vector_support = bool(candidate.vector_support_indices)

            return (
                (1 if axis_support else 0),
                (1 if vector_support else 0),
                (1 if candidate.crosses_space_center else 0),
                float(candidate.bbox_coverage_ratio),
                -float(candidate.distance_to_bbox_edge_px),
            )

        return max(
            boundary_band,
            key=ranking,
        )

    # ========================================================
    # EJES COMPATIBLES
    # ========================================================

    @staticmethod
    def _matching_axes(
        *,
        candidate: BoundaryCandidate,
        axes: list[AxisAnchorCandidate],
        tolerance: float,
    ) -> list[AxisAnchorCandidate]:
        if candidate.orientation == "vertical":
            coordinate = (candidate.x1 + candidate.x2) / 2.0

        elif candidate.orientation == "horizontal":
            coordinate = (candidate.y1 + candidate.y2) / 2.0

        else:
            return []

        return [
            axis
            for axis in axes
            if (
                axis.orientation == candidate.orientation
                and abs(axis.coordinate_px - coordinate) <= tolerance
            )
        ]

    # ========================================================
    # MERGE METADATA
    # ========================================================
    @staticmethod
    def _merge_metadata(
        *,
        wall_run: ArchitecturalWallRun,
        space_id: str,
        side: str,
        level: str,
        axis_ids: list[str],
        source_segment_ids: list[str],
        face_segment_ids: list[str],
        endpoint_support_ids: list[str],
        sources: list[str],
        support_count: int,
    ) -> None:
        if space_id not in wall_run.space_ids:
            wall_run.space_ids.append(space_id)

        if space_id:
            wall_run.space_sides[space_id] = side

        if level and level not in wall_run.levels:
            wall_run.levels.append(level)

        for axis_id in axis_ids:
            if axis_id not in wall_run.axis_ids:
                wall_run.axis_ids.append(axis_id)

        for segment_id in face_segment_ids:
            if segment_id not in wall_run.face_segment_ids:
                wall_run.face_segment_ids.append(segment_id)

        for segment_id in endpoint_support_ids:
            if segment_id not in wall_run.endpoint_support_ids:
                wall_run.endpoint_support_ids.append(segment_id)

        for segment_id in source_segment_ids:
            if segment_id not in wall_run.source_segment_ids:
                wall_run.source_segment_ids.append(segment_id)

        for source in sources:
            if source not in wall_run.sources:
                wall_run.sources.append(source)

        wall_run.support_count = max(
            wall_run.support_count,
            support_count,
        )

        wall_run.space_ids.sort()
        wall_run.levels.sort()
        wall_run.axis_ids.sort()
        wall_run.face_segment_ids.sort()
        wall_run.endpoint_support_ids.sort()
        wall_run.source_segment_ids.sort()
        wall_run.sources.sort()

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
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        reconciliation: PlanGeometryReconciliationResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        opencv_geometry: OpenCVPlanGeometryResult,
    ) -> None:
        pages = {
            reconciliation.page,
            dimension_grounding.page,
            opencv_geometry.page,
        }

        if len(pages) != 1:
            raise ValueError(
                "Reconciliación, grounding y OpenCV pertenecen a páginas distintas."
            )

        if (
            reconciliation.width_px != opencv_geometry.width_px
            or reconciliation.height_px != opencv_geometry.height_px
            or dimension_grounding.width_px != opencv_geometry.width_px
            or dimension_grounding.height_px != opencv_geometry.height_px
        ):
            raise ValueError(
                "Reconciliación, grounding y OpenCV "
                "no utilizan el mismo raster canónico."
            )


# ============================================================
# FACTORY
# ============================================================


def get_architectural_wall_abstraction_service() -> ArchitecturalWallAbstractionService:
    return ArchitecturalWallAbstractionService()
