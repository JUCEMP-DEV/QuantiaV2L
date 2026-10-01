from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

from shapely.geometry import (
    LineString,
    Point,
    Polygon,
    box,
)
from shapely.ops import (
    polygonize_full,
    unary_union,
)

from app.legacy.quantia_spatial.architectural_graph_builder import (
    ArchitecturalGraphEdge,
    ArchitecturalGraphResult,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    PlanGeometryReconciliationResult,
)
from app.legacy.quantia_spatial.wall_opening_topology_service import (
    WallOpeningTopologyResult,
)
import numpy as np

from scipy.optimize import linear_sum_assignment

# ============================================================
# ASOCIACIÓN SEMÁNTICA
# ============================================================


@dataclass(slots=True)
class FaceSemanticCandidate:
    """
    Posible correspondencia entre un polígono geométrico
    y un espacio identificado semánticamente.

    No confirma automáticamente la asociación.
    """

    space_id: str

    nivel: str

    nombre: str

    bbox_overlap_ratio: float

    face_overlap_ratio: float

    centroid_inside_localization: bool

    confirmed: bool = False


# ============================================================
# CARA / POLÍGONO
# ============================================================


@dataclass(slots=True)
class ArchitecturalFaceCandidate:
    """
    Polígono topológicamente cerrado.

    Estados:

        DETECTADO
            El polígono ya cerraba usando únicamente
            geometría detectada.

        INFERIDO
            El polígono solo cierra en el grafo aumentado,
            normalmente gracias a continuidad virtual
            de puerta/ventana.

        CANDIDATO
            Existe geométricamente, pero su procedencia
            no pudo clasificarse todavía.

    Ningún estado equivale a confirmed=True.
    """

    id: str

    vertices: list[
        tuple[
            float,
            float,
        ]
    ]

    area_px2: float

    perimeter_px: float

    centroid_x: float
    centroid_y: float

    bbox: list[float]

    shapely_valid: bool

    state: str

    detected_in_base_graph: bool

    uses_virtual_closure: bool

    virtual_edge_ids: list[str] = field(default_factory=list)

    opening_gap_ids: list[str] = field(default_factory=list)

    semantic_candidates: list[FaceSemanticCandidate] = field(default_factory=list)

    confirmed: bool = False


# ============================================================
# ADYACENCIA
# ============================================================


@dataclass(slots=True)
class FaceAdjacency:
    face_a: str

    face_b: str

    touches: bool

    shared_boundary_length_px: float


# ============================================================
# DIAGNÓSTICO DE POLYGONIZE
# ============================================================


@dataclass(slots=True)
class PolygonizationDiagnostics:
    """
    Diagnóstico Shapely de los dos grafos.

    Los dangles/cuts permiten detectar dónde sigue existiendo
    geometría abierta o incompleta.
    """

    base_polygon_count: int

    augmented_polygon_count: int

    base_dangles: int

    base_cuts: int

    base_invalid_rings: int

    augmented_dangles: int

    augmented_cuts: int

    augmented_invalid_rings: int


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class ShapelyPlanGeometryResult:
    page: int

    width_px: int
    height_px: int

    faces: list[ArchitecturalFaceCandidate] = field(default_factory=list)

    adjacencies: list[FaceAdjacency] = field(default_factory=list)

    diagnostics: PolygonizationDiagnostics | None = None

    open_graph: bool = False

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# RESULTADO INTERNO POLYGONIZE
# ============================================================


@dataclass(slots=True)
class _PolygonizeResult:
    polygons: list[Polygon]

    dangles: int

    cuts: int

    invalid_rings: int


# ============================================================
# SERVICIO
# ============================================================


class ShapelyPlanGeometryService:
    """
    Polygonización y validación topológica de Quantia V2.

    ==========================================================
    ENTRADAS
    ==========================================================

    WallOpeningTopologyResult:

        base_graph
            geometría realmente detectada.

        augmented_graph
            base_graph
            +
            continuidades virtuales candidatas.

    PlanGeometryReconciliationResult:

        localizaciones semánticas Gemini.

    ==========================================================
    PROCESO
    ==========================================================

        base_graph
            ↓
        polygonize_full
            ↓
        polígonos detectados

        augmented_graph
            ↓
        polygonize_full
            ↓
        polígonos con continuidad topológica

        comparación
            ↓
        DETECTADO / INFERIDO

        +
        asociación semántica
        +
        adyacencias

    ==========================================================
    REGLAS
    ==========================================================

    1. Un polígono Shapely válido NO confirma habitación.

    2. Un polígono que necesita una arista virtual queda:

           state = INFERIDO
           confirmed = False

    3. Un polígono que ya existía en base_graph queda:

           state = DETECTADO
           confirmed = False

    4. No se convierten áreas px² a m².

    5. No se inventan cierres adicionales.

    6. Shapely valida topología; no decide semántica.
    """

    NUMERIC_TOLERANCE = 1e-6
    MIN_SEMANTIC_BBOX_COVERAGE = 0.05

    # ========================================================
    # API
    # ========================================================

    def analyze(
        self,
        *,
        topology: WallOpeningTopologyResult,
        reconciliation: PlanGeometryReconciliationResult,
    ) -> ShapelyPlanGeometryResult:
        self._validate_inputs(
            topology=topology,
            reconciliation=reconciliation,
        )

        # ====================================================
        # POLYGONIZE — GRAFO BASE
        # ====================================================

        base_result = self._polygonize_graph(topology.base_graph)

        # ====================================================
        # POLYGONIZE — GRAFO AUMENTADO
        # ====================================================

        augmented_result = self._polygonize_graph(topology.augmented_graph)

        # ====================================================
        # MAPA VIRTUAL EDGE → GAP
        # ====================================================

        virtual_edge_to_gap: dict[
            str,
            str,
        ] = {}

        for gap in topology.gap_candidates:
            if not gap.virtual_edge_id:
                continue

            virtual_edge_to_gap[gap.virtual_edge_id] = gap.id

        # ====================================================
        # CARAS FINALES
        # ====================================================

        faces: list[ArchitecturalFaceCandidate] = []

        face_geometries: dict[
            str,
            Polygon,
        ] = {}

        face_counter = 0

        for polygon in augmented_result.polygons:
            if polygon.is_empty or polygon.area <= 0:
                continue

            face_counter += 1

            face_id = f"FACE_{face_counter}"

            # ------------------------------------------------
            # ¿YA EXISTÍA SIN INFERENCIA?
            # ------------------------------------------------

            detected_in_base = any(
                self._same_polygon(
                    polygon,
                    base_polygon,
                )
                for base_polygon in base_result.polygons
            )

            # ------------------------------------------------
            # ¿QUÉ ARISTAS VIRTUALES PARTICIPAN?
            # ------------------------------------------------

            virtual_edge_ids = self._virtual_edges_on_boundary(
                polygon=polygon,
                edges=topology.augmented_graph.edges,
            )

            opening_gap_ids = [
                virtual_edge_to_gap[edge_id]
                for edge_id in virtual_edge_ids
                if edge_id in virtual_edge_to_gap
            ]

            uses_virtual_closure = bool(virtual_edge_ids)

            # ------------------------------------------------
            # ESTADO
            # ------------------------------------------------

            if detected_in_base:
                state = "DETECTADO"

            elif uses_virtual_closure:
                state = "INFERIDO"

            else:
                state = "CANDIDATO"

            # ------------------------------------------------
            # VÉRTICES
            # ------------------------------------------------

            coordinates = list(polygon.exterior.coords)

            if len(coordinates) > 1 and coordinates[0] == coordinates[-1]:
                coordinates = coordinates[:-1]

            centroid = polygon.centroid

            min_x, min_y, max_x, max_y = polygon.bounds

            # La asociación semántica se realiza después de
            # construir TODAS las faces. De esta forma cada
            # espacio localizado compite globalmente por una
            # única face y no se replica sobre cada polígono
            # que interseque su bbox aproximado.
            semantic_candidates: list[FaceSemanticCandidate] = []

            face = ArchitecturalFaceCandidate(
                id=face_id,
                vertices=[
                    (
                        float(x),
                        float(y),
                    )
                    for x, y in coordinates
                ],
                area_px2=float(polygon.area),
                perimeter_px=float(polygon.length),
                centroid_x=float(centroid.x),
                centroid_y=float(centroid.y),
                bbox=[
                    float(min_x),
                    float(min_y),
                    float(max_x),
                    float(max_y),
                ],
                shapely_valid=bool(polygon.is_valid),
                state=state,
                detected_in_base_graph=detected_in_base,
                uses_virtual_closure=uses_virtual_closure,
                virtual_edge_ids=sorted(virtual_edge_ids),
                opening_gap_ids=sorted(set(opening_gap_ids)),
                semantic_candidates=semantic_candidates,
                confirmed=False,
            )

            faces.append(face)

            face_geometries[face_id] = polygon

        # ====================================================
        # ASOCIACIÓN SEMÁNTICA GLOBAL
        # ====================================================
        #
        # Regla:
        #
        #   1 espacio semántico localizado
        #       -> como máximo 1 face geométrica.
        #
        # Varias zonas del MISMO nivel sí pueden terminar en
        # una misma face física (p. ej. estancia/comedor/cocina
        # en planta abierta).
        #
        # Si una misma face resulta ganadora para espacios de
        # niveles distintos, la semántica de esa face se deja
        # sin promover. Es preferible NO_IDENTIFICADO a mezclar
        # Planta Baja con Planta Alta.
        # ====================================================

        semantic_by_face = self._associate_semantics(
            faces=faces,
            geometries=face_geometries,
            reconciliation=reconciliation,
        )

        for face in faces:
            face.semantic_candidates = list(
                semantic_by_face.get(
                    face.id,
                    [],
                )
            )

        # ====================================================
        # ADYACENCIAS
        # ====================================================

        adjacencies = self._build_adjacencies(
            faces=faces,
            geometries=face_geometries,
        )

        # ====================================================
        # DIAGNÓSTICO
        # ====================================================

        diagnostics = PolygonizationDiagnostics(
            base_polygon_count=len(base_result.polygons),
            augmented_polygon_count=len(augmented_result.polygons),
            base_dangles=base_result.dangles,
            base_cuts=base_result.cuts,
            base_invalid_rings=base_result.invalid_rings,
            augmented_dangles=augmented_result.dangles,
            augmented_cuts=augmented_result.cuts,
            augmented_invalid_rings=augmented_result.invalid_rings,
        )

        open_graph = len(faces) == 0

        # ====================================================
        # NOTAS
        # ====================================================

        notes: list[str] = [
            (
                "Se polygonizó por separado el grafo "
                "detectado y el grafo con continuidad "
                "topológica."
            ),
            ("Los polígonos presentes en base_graph " "quedaron como DETECTADO."),
            (
                "Los polígonos que solo aparecen después "
                "de una continuidad virtual quedaron "
                "como INFERIDO."
            ),
            (
                "Las aristas virtuales utilizadas por cada "
                "polígono quedaron registradas."
            ),
            (
                "Las puertas/ventanas asociadas siguen "
                "siendo entidades independientes."
            ),
            (
                "Cada espacio localizado compitió "
                "globalmente por una única face geométrica."
            ),
            (
                "Una face puede conservar varias zonas "
                "semánticas únicamente cuando pertenecen "
                "al mismo nivel."
            ),
            (
                "Las asociaciones cruzadas entre niveles "
                "no se promueven; quedan sin semántica."
            ),
            ("Las áreas permanecen expresadas en px²."),
            ("Ningún polígono tiene confirmed=true."),
        ]

        if diagnostics.augmented_polygon_count > diagnostics.base_polygon_count:
            notes.append(
                "La continuidad topológica permitió " "cerrar recintos adicionales."
            )

        if diagnostics.augmented_dangles > 0:
            notes.append(
                "Persisten líneas abiertas después de "
                "aplicar continuidad topológica."
            )

        if open_graph:
            notes.append("No se obtuvo ningún recinto cerrado.")

        return ShapelyPlanGeometryResult(
            page=topology.page,
            width_px=topology.width_px,
            height_px=topology.height_px,
            faces=faces,
            adjacencies=adjacencies,
            diagnostics=diagnostics,
            open_graph=open_graph,
            notes=notes,
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        topology: WallOpeningTopologyResult,
        reconciliation: PlanGeometryReconciliationResult,
    ) -> None:
        if topology.page != reconciliation.page:
            raise ValueError(
                "Topología y reconciliación pertenecen " "a páginas distintas."
            )

        if (
            topology.width_px != reconciliation.width_px
            or topology.height_px != reconciliation.height_px
        ):
            raise ValueError(
                "Topología y reconciliación no utilizan " "el mismo raster canónico."
            )

    # ========================================================
    # POLYGONIZE
    # ========================================================

    def _polygonize_graph(
        self,
        graph: ArchitecturalGraphResult,
    ) -> _PolygonizeResult:
        lines: list[LineString] = []

        for edge in graph.edges:
            geometry = self._edge_geometry(edge)

            if geometry is None:
                continue

            lines.append(geometry)

        if not lines:
            return _PolygonizeResult(
                polygons=[],
                dangles=0,
                cuts=0,
                invalid_rings=0,
            )

        # ----------------------------------------------------
        # NODE / MERGE
        # ----------------------------------------------------

        merged = unary_union(lines)

        (
            polygons_geometry,
            cuts_geometry,
            dangles_geometry,
            invalid_geometry,
        ) = polygonize_full(merged)

        polygons = [
            geometry
            for geometry in self._geometry_collection_items(polygons_geometry)
            if isinstance(
                geometry,
                Polygon,
            )
            and not geometry.is_empty
            and geometry.area > 0
        ]

        return _PolygonizeResult(
            polygons=polygons,
            dangles=self._geometry_count(dangles_geometry),
            cuts=self._geometry_count(cuts_geometry),
            invalid_rings=self._geometry_count(invalid_geometry),
        )

    # ========================================================
    # EDGE → SHAPELY
    # ========================================================

    @staticmethod
    def _edge_geometry(
        edge: ArchitecturalGraphEdge,
    ) -> LineString | None:
        geometry = LineString(
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

        if geometry.is_empty or geometry.length <= 0:
            return None

        return geometry

    # ========================================================
    # COMPARAR POLÍGONOS
    # ========================================================

    def _same_polygon(
        self,
        first: Polygon,
        second: Polygon,
    ) -> bool:
        """
        Compara topología, no orden de vértices.
        """

        if first.equals(second):
            return True

        try:
            difference = first.symmetric_difference(second)

        except Exception:
            return False

        return difference.area <= self.NUMERIC_TOLERANCE

    # ========================================================
    # ARISTAS VIRTUALES EN LA FRONTERA
    # ========================================================

    def _virtual_edges_on_boundary(
        self,
        *,
        polygon: Polygon,
        edges: list[ArchitecturalGraphEdge],
    ) -> list[str]:
        result: list[str] = []

        polygon_boundary = polygon.boundary

        for edge in edges:
            if "topology_virtual" not in edge.sources:
                continue

            geometry = self._edge_geometry(edge)

            if geometry is None:
                continue

            intersection = polygon_boundary.intersection(geometry)

            if intersection.length > self.NUMERIC_TOLERANCE:
                result.append(edge.id)

        return result

    # ========================================================
    # ASOCIACIÓN SEMÁNTICA
    # ========================================================

    def _associate_semantics(
        self,
        *,
        faces: list[ArchitecturalFaceCandidate],
        geometries: dict[
            str,
            Polygon,
        ],
        reconciliation: PlanGeometryReconciliationResult,
    ) -> dict[
        str,
        list[FaceSemanticCandidate],
    ]:
        """
        Asocia globalmente espacios semánticos con faces
        geométricas usando asignación bipartita SciPy.

        Principios:

        1. Se conserva exactamente la evidencia geométrica
           que ya utilizaba Quantia:

               - centroide de face dentro del bbox;
               - cobertura del bbox por la face;
               - cobertura de la face por el bbox.

        2. No se introducen thresholds nuevos.

        3. Se conserva el orden de preferencia anterior para
           cada espacio y ese orden se convierte en ranking.

        4. SciPy resuelve después el conjunto completo para
           evitar que dos espacios físicos independientes
           ganen accidentalmente la misma face.

        5. Se agregan columnas dummy para permitir que un
           espacio quede sin face cuando exista conflicto.

        6. Las asociaciones siguen siendo candidatas:

               confirmed = False.

        7. No se inventan niveles, distancias ni métricas.
        """

        result: dict[
            str,
            list[FaceSemanticCandidate],
        ] = {face.id: [] for face in faces}

        if not faces or not reconciliation.spaces:
            return result

        # ====================================================
        # ÍNDICES DE FACES
        # ====================================================

        face_ids = [face.id for face in faces]

        face_index = {face_id: index for index, face_id in enumerate(face_ids)}

        # ====================================================
        # CANDIDATOS POR ESPACIO
        # ====================================================

        semantic_rows: list[
            tuple[
                str,
                list[
                    tuple[
                        FaceSemanticCandidate,
                        str,
                    ]
                ],
            ]
        ] = []

        for space in reconciliation.spaces:
            bbox = getattr(
                space,
                "localization_bbox",
                None,
            )

            if bbox is None:
                continue

            localization_geometry = box(
                bbox.x_min,
                bbox.y_min,
                bbox.x_max,
                bbox.y_max,
            )

            if (
                localization_geometry.is_empty
                or localization_geometry.area <= self.NUMERIC_TOLERANCE
            ):
                continue

            bbox_area = float(localization_geometry.area)

            matches: list[
                tuple[
                    FaceSemanticCandidate,
                    str,
                ]
            ] = []

            for face in faces:
                polygon = geometries.get(face.id)

                if polygon is None or polygon.is_empty or polygon.area <= 0:
                    continue

                centroid = polygon.centroid

                centroid_point = Point(
                    centroid.x,
                    centroid.y,
                )

                intersection = polygon.intersection(localization_geometry)

                intersection_area = float(intersection.area)

                face_area = float(polygon.area)

                bbox_overlap_ratio = (
                    intersection_area / bbox_area if bbox_area > 0 else 0.0
                )

                face_overlap_ratio = (
                    intersection_area / face_area if face_area > 0 else 0.0
                )

                centroid_inside = bool(
                    localization_geometry.contains(centroid_point)
                    or localization_geometry.touches(centroid_point)
                )

                # Se conserva exactamente la regla actual:
                # sin intersección ni centroide dentro,
                # no existe candidatura espacial.
                if intersection_area <= 0 and not centroid_inside:
                    continue

                # Una face diminuta dentro del bbox suele ser
                # mobiliario o detalle gráfico, no el recinto.
                # Debe cubrir una fracción material de la
                # localización semántica antes de competir por ella.
                if bbox_overlap_ratio < self.MIN_SEMANTIC_BBOX_COVERAGE:
                    continue

                matches.append(
                    (
                        FaceSemanticCandidate(
                            space_id=space.id_propuesto,
                            nivel=space.nivel,
                            nombre=space.nombre,
                            bbox_overlap_ratio=bbox_overlap_ratio,
                            face_overlap_ratio=face_overlap_ratio,
                            centroid_inside_localization=centroid_inside,
                            confirmed=False,
                        ),
                        face.id,
                    )
                )

            if not matches:
                continue

            # ====================================================
            # RANKING LOCAL EXISTENTE
            # ====================================================
            #
            # Importante:
            #
            # No inventamos pesos nuevos.
            #
            # Conservamos exactamente la prioridad anterior:
            #
            #   1. centroide dentro;
            #   2. mayor bbox overlap;
            #   3. mayor face overlap;
            #   4. face id como desempate estable.
            #
            # SciPy optimizará GLOBALMENTE estos rankings.
            # ====================================================

            matches.sort(
                key=lambda item: (
                    not item[0].centroid_inside_localization,
                    -item[0].bbox_overlap_ratio,
                    -item[0].face_overlap_ratio,
                    item[1],
                )
            )

            semantic_rows.append(
                (
                    space.id_propuesto,
                    matches,
                )
            )

        if not semantic_rows:
            return result

        # ====================================================
        # MATRIZ DE COSTO
        # ====================================================
        #
        # Columnas:
        #
        #   faces reales
        #   +
        #   una cantidad suficiente de columnas dummy.
        #
        # Las columnas dummy permiten que un espacio quede
        # sin asignar cuando las faces reales ya fueron tomadas.
        #
        # No existe threshold artificial:
        #
        #   cualquier candidato geométricamente válido
        #   sigue siendo preferible al unmatched.
        # ====================================================

        row_count = len(semantic_rows)

        face_count = len(face_ids)

        column_count = face_count + row_count

        invalid_cost = float(face_count + row_count + 1)

        cost_matrix = np.full(
            (
                row_count,
                column_count,
            ),
            invalid_cost,
            dtype=float,
        )

        candidate_lookup: dict[
            tuple[
                int,
                int,
            ],
            FaceSemanticCandidate,
        ] = {}

        for row_index, (
            _space_id,
            matches,
        ) in enumerate(semantic_rows):
            # ----------------------------------------------------
            # FACES REALES
            # ----------------------------------------------------

            for rank, (
                candidate,
                face_id,
            ) in enumerate(matches):
                column_index = face_index[face_id]

                # rank 0 = mejor candidato.
                cost_matrix[
                    row_index,
                    column_index,
                ] = float(rank)

                candidate_lookup[
                    (
                        row_index,
                        column_index,
                    )
                ] = candidate

            # ----------------------------------------------------
            # UNMATCHED
            # ----------------------------------------------------
            #
            # Queda después de todos los candidatos válidos
            # de este espacio.
            #
            # Esto conserva el comportamiento existente:
            # si existe una face válida, se intenta usarla.
            #
            # Pero si existe conflicto global por unicidad,
            # SciPy puede dejar este espacio sin face.
            # ----------------------------------------------------

            unmatched_cost = float(len(matches))

            for dummy_index in range(row_count):
                cost_matrix[
                    row_index,
                    face_count + dummy_index,
                ] = unmatched_cost

        # ====================================================
        # HUNGARIAN / LINEAR SUM ASSIGNMENT
        # ====================================================

        (
            assigned_rows,
            assigned_columns,
        ) = linear_sum_assignment(cost_matrix)

        # ====================================================
        # PROMOVER ASIGNACIONES GANADORAS
        # ====================================================

        for (
            row_index,
            column_index,
        ) in zip(
            assigned_rows.tolist(),
            assigned_columns.tolist(),
        ):
            # Columna dummy:
            # el espacio queda sin face.
            if column_index >= face_count:
                continue

            candidate = candidate_lookup.get(
                (
                    row_index,
                    column_index,
                )
            )

            # SciPy nunca debe promover una combinación que
            # no existía realmente en la matriz de candidatos.
            if candidate is None:
                continue

            face_id = face_ids[column_index]

            result[face_id].append(candidate)

        # ====================================================
        # VALIDACIÓN FINAL ENTRE NIVELES
        # ====================================================
        #
        # Con matching 1-a-1 normalmente cada face tendrá
        # como máximo un candidato.
        #
        # Conservamos esta protección porque mezclar plantas
        # nunca debe convertirse silenciosamente en semántica
        # válida si el algoritmo evoluciona posteriormente.
        # ====================================================

        for face_id, candidates in list(result.items()):
            levels = {
                str(candidate.nivel).strip()
                for candidate in candidates
                if str(candidate.nivel).strip()
            }

            if len(levels) > 1:
                result[face_id] = []

                continue

            candidates.sort(
                key=lambda item: (
                    not item.centroid_inside_localization,
                    -item.bbox_overlap_ratio,
                    -item.face_overlap_ratio,
                    item.space_id,
                )
            )

        return result

    # ========================================================
    # ADYACENCIAS
    # ========================================================

    @staticmethod
    def _build_adjacencies(
        *,
        faces: list[ArchitecturalFaceCandidate],
        geometries: dict[
            str,
            Polygon,
        ],
    ) -> list[FaceAdjacency]:
        result: list[FaceAdjacency] = []

        for first_index in range(len(faces)):
            first = faces[first_index]

            first_geometry = geometries[first.id]

            for second_index in range(
                first_index + 1,
                len(faces),
            ):
                second = faces[second_index]

                second_geometry = geometries[second.id]

                touches = bool(first_geometry.touches(second_geometry))

                shared = first_geometry.boundary.intersection(second_geometry.boundary)

                shared_length = float(shared.length)

                if not touches and shared_length <= 0:
                    continue

                result.append(
                    FaceAdjacency(
                        face_a=first.id,
                        face_b=second.id,
                        touches=touches,
                        shared_boundary_length_px=shared_length,
                    )
                )

        return result

    # ========================================================
    # GEOMETRY COLLECTION
    # ========================================================

    @staticmethod
    def _geometry_collection_items(
        geometry: Any,
    ) -> list[Any]:
        if geometry is None:
            return []

        if geometry.is_empty:
            return []

        geoms = getattr(
            geometry,
            "geoms",
            None,
        )

        if geoms is None:
            return [geometry]

        return list(geoms)

    # ========================================================
    # CONTADOR
    # ========================================================

    @classmethod
    def _geometry_count(
        cls,
        geometry: Any,
    ) -> int:
        return len(cls._geometry_collection_items(geometry))


# ============================================================
# FACTORY
# ============================================================


def get_shapely_plan_geometry_service() -> ShapelyPlanGeometryService:
    return ShapelyPlanGeometryService()
