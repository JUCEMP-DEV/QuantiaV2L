from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from shapely.geometry import Polygon, box

from app.legacy.quantia_spatial.architectural_dimension_grounding_service import (
    ArchitecturalDimensionGroundingResult,
    ResolvedSpaceDimension,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    PlanGeometryReconciliationResult,
    SpaceGeometryReconciliation,
)
from app.legacy.quantia_spatial.shapely_plan_geometry_service import (
    ArchitecturalFaceCandidate,
    FaceAdjacency,
    FaceSemanticCandidate,
    ShapelyPlanGeometryResult,
)
from app.legacy.quantia_spatial.wall_geometry_resolver import (
    ResolvedWallGeometry,
    ResolvedWallOpeningReference,
    WallGeometryResolverResult,
)


# ============================================================
# DIMENSIÓN DEL ESPACIO
# ============================================================


@dataclass(slots=True)
class SpaceDimensionReference:
    dimension_id: str

    dimension_axis: str

    value_m: float

    pixel_span: float

    pixels_per_meter: float

    start_axis_label: str

    end_axis_label: str

    component_span_ids: list[
        str
    ] = field(
        default_factory=list
    )

    evidence_sources: list[
        str
    ] = field(
        default_factory=list
    )

    state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# MURO DEL ESPACIO
# ============================================================


@dataclass(slots=True)
class SpaceWallReference:
    wall_id: str

    continuity_group_id: str

    orientation: str

    positions: list[
        str
    ] = field(
        default_factory=list
    )

    shared_boundary_length_px: float = 0.0

    source_segment_ids: list[
        str
    ] = field(
        default_factory=list
    )

    association_conflict: bool = False

    wall_state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# OPENING DEL ESPACIO
# ============================================================


@dataclass(slots=True)
class SpaceOpeningReference:
    opening_id: str

    opening_type: str

    wall_id: str

    gap_id: str

    level: str

    semantic_location: str | None

    direction: str | None

    association_type: str

    state: str

    confirmed: bool = False


# ============================================================
# ZONA SEMÁNTICA
# ============================================================


@dataclass(slots=True)
class ResolvedSemanticZone:
    """
    Zona funcional dentro de una face geométrica.

    Ejemplo:

        FACE_1
        ├── Estancia
        ├── Comedor
        └── Cocina

    La geometría de la zona se obtiene únicamente como
    intersección aproximada:

        bbox Gemini ∩ face Shapely

    No representa un recinto independiente.
    """

    id: str

    source_space_id: str

    level: str

    name: str

    bbox_overlap_ratio: float

    face_overlap_ratio: float

    centroid_inside_localization: bool

    area_px2: float

    bbox: list[
        float
    ]

    polygons: list[
        list[
            tuple[
                float,
                float,
            ]
        ]
    ] = field(
        default_factory=list
    )

    dimension_candidates: list[
        SpaceDimensionReference
    ] = field(
        default_factory=list
    )

    geometry_source: str = (
        "gemini_bbox_intersection"
    )

    state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# CANDIDATO SEMÁNTICO
# ============================================================


@dataclass(slots=True)
class SpaceSemanticReference:
    space_id: str

    level: str

    name: str

    bbox_overlap_ratio: float

    face_overlap_ratio: float

    centroid_inside_localization: bool

    confirmed: bool = False


# ============================================================
# ESPACIO GEOMÉTRICO
# ============================================================


@dataclass(slots=True)
class ResolvedSpaceGeometry:
    """
    Espacio geométrico editable.

    Una face Shapely produce UNA entidad geométrica.

    Puede tener:

        - una identidad semántica única;
        - varias zonas semánticas;
        - ninguna identidad reconocida.
    """

    id: str

    face_id: str

    level: str | None

    name: str | None

    semantic_mode: str

    semantic_state: str

    geometry_state: str

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

    bbox: list[
        float
    ]

    uses_virtual_closure: bool

    virtual_edge_ids: list[
        str
    ] = field(
        default_factory=list
    )

    opening_gap_ids: list[
        str
    ] = field(
        default_factory=list
    )

    semantic_candidates: list[
        SpaceSemanticReference
    ] = field(
        default_factory=list
    )

    semantic_zones: list[
        ResolvedSemanticZone
    ] = field(
        default_factory=list
    )

    dimensions: list[
        SpaceDimensionReference
    ] = field(
        default_factory=list
    )

    walls: list[
        SpaceWallReference
    ] = field(
        default_factory=list
    )

    openings: list[
        SpaceOpeningReference
    ] = field(
        default_factory=list
    )

    adjacent_face_ids: list[
        str
    ] = field(
        default_factory=list
    )

    metric_area_m2: float | None = None

    state: str = "DETECTADO"

    confirmed: bool = False


# ============================================================
# CONFLICTO SEMÁNTICO
# ============================================================


@dataclass(slots=True)
class SpaceSemanticConflict:
    face_id: str

    space_ids: list[
        str
    ]

    levels: list[
        str
    ]

    reason: str


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class SpaceGeometryResolverResult:
    page: int

    width_px: int
    height_px: int

    spaces: list[
        ResolvedSpaceGeometry
    ] = field(
        default_factory=list
    )

    semantic_zones: list[
        ResolvedSemanticZone
    ] = field(
        default_factory=list
    )

    semantic_conflicts: list[
        SpaceSemanticConflict
    ] = field(
        default_factory=list
    )

    unidentified_face_ids: list[
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
# SERVICIO
# ============================================================


class SpaceGeometryResolver:
    """
    Resuelve faces geométricas contra semántica, muros,
    dimensiones y adyacencias.

    ==========================================================
    PRINCIPIO FUNDAMENTAL
    ==========================================================

    Face geométrica != función arquitectónica.

    Ejemplo:

        ┌─────────────────────────────┐
        │ ESTANCIA   COMEDOR   COCINA │
        └─────────────────────────────┘

    Si no existen muros físicos entre las tres funciones:

        1 face geométrica
        +
        3 zonas semánticas

    NO:

        3 habitaciones inventadas.

    ==========================================================
    REGLAS
    ==========================================================

    1. Cada face Shapely genera un espacio geométrico.

    2. Una sola correspondencia semántica:

           semantic_mode = ESPACIO_UNICO

    3. Varias correspondencias del mismo nivel:

           semantic_mode = MULTIPLES_ZONAS

    4. Varias correspondencias de niveles distintos:

           semantic_state = CONFLICTO

    5. Sin semántica:

           semantic_state = NO_IDENTIFICADO

    6. Las dimensiones grounded solo se promocionan al espacio
       físico cuando existe una identidad semántica única.

    7. En MULTIPLES_ZONAS, las dimensiones permanecen dentro
       de cada zona como candidatas.

    8. area_px2 nunca se convierte automáticamente a m².

    9. confirmed siempre permanece False.
    """

    # ========================================================
    # API
    # ========================================================

    def resolve(
        self,
        *,
        shapely_geometry: ShapelyPlanGeometryResult,
        reconciliation: PlanGeometryReconciliationResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        wall_geometry: WallGeometryResolverResult,
    ) -> SpaceGeometryResolverResult:
        self._validate_inputs(
            shapely_geometry=
                shapely_geometry,

            reconciliation=
                reconciliation,

            dimension_grounding=
                dimension_grounding,

            wall_geometry=
                wall_geometry,
        )

        reconciliation_lookup = {
            space.id_propuesto:
                space
            for space
            in reconciliation.spaces
        }

        dimensions_by_space = (
            self._dimensions_by_space(
                dimension_grounding
            )
        )

        adjacency_lookup = (
            self._adjacency_lookup(
                shapely_geometry.adjacencies
            )
        )

        spaces: list[
            ResolvedSpaceGeometry
        ] = []

        all_zones: list[
            ResolvedSemanticZone
        ] = []

        conflicts: list[
            SpaceSemanticConflict
        ] = []

        unidentified_faces: list[
            str
        ] = []

        for index, face in enumerate(
            shapely_geometry.faces,
            start=1,
        ):
            semantic_candidates = [
                self._semantic_reference(
                    candidate
                )
                for candidate
                in face.semantic_candidates
            ]

            levels = sorted(
                {
                    candidate.level
                    for candidate
                    in semantic_candidates
                    if candidate.level
                }
            )

            compound_zone_names = (
                self._compound_zone_names(semantic_candidates[0].name)
                if len(semantic_candidates) == 1
                else []
            )

            # =================================================
            # ESTADO SEMÁNTICO
            # =================================================

            if not semantic_candidates:
                semantic_mode = (
                    "SIN_SEMANTICA"
                )

                semantic_state = (
                    "NO_IDENTIFICADO"
                )

                level = (
                    None
                )

                name = (
                    None
                )

                unidentified_faces.append(
                    face.id
                )

            elif len(
                levels
            ) > 1:
                semantic_mode = (
                    "MULTIPLES_CANDIDATOS"
                )

                semantic_state = (
                    "CONFLICTO"
                )

                level = (
                    None
                )

                name = (
                    None
                )

                conflicts.append(
                    SpaceSemanticConflict(
                        face_id=
                            face.id,

                        space_ids=[
                            candidate.space_id
                            for candidate
                            in semantic_candidates
                        ],

                        levels=
                            levels,

                        reason=(
                            "Una misma face recibió "
                            "candidatos semánticos de "
                            "niveles diferentes."
                        ),
                    )
                )

            elif (
                len(semantic_candidates) == 1
                and len(compound_zone_names) > 1
            ):
                semantic_mode = "MULTIPLES_ZONAS"
                semantic_state = "INFERIDO"
                level = semantic_candidates[0].level
                name = None

            elif len(
                semantic_candidates
            ) == 1:
                semantic_mode = (
                    "ESPACIO_UNICO"
                )

                semantic_state = (
                    "DETECTADO"
                )

                level = (
                    semantic_candidates[
                        0
                    ].level
                )

                name = (
                    semantic_candidates[
                        0
                    ].name
                )

            else:
                # Varias funciones dentro de una misma
                # geometría física.
                semantic_mode = (
                    "MULTIPLES_ZONAS"
                )

                semantic_state = (
                    "DETECTADO"
                )

                level = (
                    levels[
                        0
                    ]
                    if len(
                        levels
                    )
                    == 1
                    else None
                )

                name = (
                    None
                )

            # =================================================
            # ZONAS SEMÁNTICAS
            # =================================================

            zones: list[
                ResolvedSemanticZone
            ] = []

            for zone_index, candidate in enumerate(
                face.semantic_candidates,
                start=1,
            ):
                if semantic_mode != "MULTIPLES_ZONAS":
                    continue

                source_space = (
                    reconciliation_lookup.get(
                        candidate.space_id
                    )
                )

                if source_space is None:
                    continue

                zone_names = self._compound_zone_names(candidate.nombre)

                for derived_index, zone_name in enumerate(zone_names, start=1):
                    is_compound = len(zone_names) > 1
                    zone = self._build_semantic_zone(
                        zone_id=(
                            f"ZONE_{index}_{zone_index}_{derived_index}"
                            if is_compound
                            else f"ZONE_{index}_{zone_index}"
                        ),
                        face=face,
                        candidate=candidate,
                        source_space=source_space,
                        dimensions=dimensions_by_space.get(candidate.space_id, []),
                        zone_name=zone_name,
                        inferred_from_compound_name=is_compound,
                    )

                    if zone is None:
                        continue

                    zones.append(zone)
                    all_zones.append(zone)

            # =================================================
            # DIMENSIONES DEL ESPACIO FÍSICO
            # =================================================

            physical_dimensions: list[
                SpaceDimensionReference
            ] = []

            if (
                semantic_mode
                == "ESPACIO_UNICO"
            ):
                unique_space_id = (
                    semantic_candidates[
                        0
                    ].space_id
                )

                physical_dimensions = [
                    self._dimension_reference(
                        dimension
                    )
                    for dimension
                    in dimensions_by_space.get(
                        unique_space_id,
                        [],
                    )
                ]

            # =================================================
            # MUROS
            # =================================================

            wall_refs = (
                self._walls_for_face(
                    face_id=
                        face.id,

                    walls=
                        wall_geometry.walls,
                )
            )

            # =================================================
            # OPENINGS
            # =================================================

            semantic_space_ids = {
                candidate.space_id
                for candidate
                in semantic_candidates
            }

            opening_refs = (
                self._openings_for_space(
                    walls=
                        wall_geometry.walls,

                    wall_refs=
                        wall_refs,

                    semantic_space_ids=
                        semantic_space_ids,
                )
            )

            # =================================================
            # ESTADO GENERAL
            # =================================================

            if (
                face.state
                == "INFERIDO"
            ):
                state = (
                    "INFERIDO"
                )

            elif (
                semantic_state
                == "CONFLICTO"
            ):
                state = (
                    "CONFLICTO"
                )

            elif (
                face.state
                == "DETECTADO"
            ):
                state = (
                    "DETECTADO"
                )

            else:
                state = (
                    "CANDIDATO"
                )

            spaces.append(
                ResolvedSpaceGeometry(
                    id=
                        f"SPACE_GEOM_{index}",

                    face_id=
                        face.id,

                    level=
                        level,

                    name=
                        name,

                    semantic_mode=
                        semantic_mode,

                    semantic_state=
                        semantic_state,

                    geometry_state=
                        face.state,

                    vertices=
                        list(
                            face.vertices
                        ),

                    area_px2=
                        face.area_px2,

                    perimeter_px=
                        face.perimeter_px,

                    centroid_x=
                        face.centroid_x,

                    centroid_y=
                        face.centroid_y,

                    bbox=
                        list(
                            face.bbox
                        ),

                    uses_virtual_closure=
                        face.uses_virtual_closure,

                    virtual_edge_ids=
                        list(
                            face.virtual_edge_ids
                        ),

                    opening_gap_ids=
                        list(
                            face.opening_gap_ids
                        ),

                    semantic_candidates=
                        semantic_candidates,

                    semantic_zones=
                        zones,

                    dimensions=
                        physical_dimensions,

                    walls=
                        wall_refs,

                    openings=
                        opening_refs,

                    adjacent_face_ids=
                        adjacency_lookup.get(
                            face.id,
                            [],
                        ),

                    metric_area_m2=
                        None,

                    state=
                        state,

                    confirmed=
                        False,
                )
            )

        assigned_source_space_ids = {
            candidate.space_id
            for space in spaces
            for candidate in space.semantic_candidates
        }

        for source_space in reconciliation.spaces:
            if source_space.id_propuesto in assigned_source_space_ids:
                continue

            fallback_space, fallback_zones = self._semantic_fallback_space(
                source_space=source_space,
                dimensions=dimensions_by_space.get(source_space.id_propuesto, []),
            )
            spaces.append(fallback_space)
            all_zones.extend(fallback_zones)

        return SpaceGeometryResolverResult(
            page=
                shapely_geometry.page,

            width_px=
                shapely_geometry.width_px,

            height_px=
                shapely_geometry.height_px,

            spaces=
                spaces,

            semantic_zones=
                all_zones,

            semantic_conflicts=
                conflicts,

            unidentified_face_ids=
                unidentified_faces,

            notes=[
                (
                    "Cada face Shapely se conservó como "
                    "una única geometría física."
                ),
                (
                    "Varias funciones semánticas dentro "
                    "de una misma face se representaron "
                    "como zonas y no como habitaciones "
                    "independientes."
                ),
                (
                    "Las dimensiones grounded solo se "
                    "asignaron directamente a faces con "
                    "una identidad semántica única."
                ),
                (
                    "En espacios abiertos, las dimensiones "
                    "permanecen asociadas a cada zona como "
                    "candidatas."
                ),
                (
                    "Los muros se relacionaron mediante "
                    "las faces Shapely que tienen a cada "
                    "lado."
                ),
                (
                    "No se calculó área métrica a partir "
                    "de área raster."
                ),
                (
                    "Todo elemento generado mantiene "
                    "confirmed=false."
                ),
            ],
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    def _semantic_fallback_space(
        self,
        *,
        source_space: SpaceGeometryReconciliation,
        dimensions: list[ResolvedSpaceDimension],
    ) -> tuple[ResolvedSpaceGeometry, list[ResolvedSemanticZone]]:
        bbox = source_space.localization_bbox
        vertices = [
            (bbox.x_min, bbox.y_min),
            (bbox.x_max, bbox.y_min),
            (bbox.x_max, bbox.y_max),
            (bbox.x_min, bbox.y_max),
        ]
        area_px2 = bbox.width * bbox.height
        perimeter_px = 2.0 * (bbox.width + bbox.height)
        zone_names = self._compound_zone_names(source_space.nombre)
        is_compound = len(zone_names) > 1
        semantic_mode = "MULTIPLES_ZONAS" if is_compound else "ESPACIO_UNICO"
        face_id = f"SEMANTIC_BBOX_{source_space.id_propuesto}"
        semantic_reference = SpaceSemanticReference(
            space_id=source_space.id_propuesto,
            level=source_space.nivel,
            name=source_space.nombre,
            bbox_overlap_ratio=1.0,
            face_overlap_ratio=1.0,
            centroid_inside_localization=True,
            confirmed=False,
        )
        dimension_references = [
            self._dimension_reference(dimension) for dimension in dimensions
        ]
        zones: list[ResolvedSemanticZone] = []

        if is_compound:
            for index, zone_name in enumerate(zone_names, start=1):
                zones.append(
                    ResolvedSemanticZone(
                        id=f"ZONE_FALLBACK_{source_space.id_propuesto}_{index}",
                        source_space_id=source_space.id_propuesto,
                        level=source_space.nivel,
                        name=zone_name,
                        bbox_overlap_ratio=1.0,
                        face_overlap_ratio=1.0,
                        centroid_inside_localization=True,
                        area_px2=area_px2,
                        bbox=[bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max],
                        polygons=[list(vertices)],
                        dimension_candidates=list(dimension_references),
                        geometry_source="compound_semantic_bbox_shared",
                        state="INFERIDO",
                        confirmed=False,
                    )
                )

        return (
            ResolvedSpaceGeometry(
                id=f"SPACE_FALLBACK_{source_space.id_propuesto}",
                face_id=face_id,
                level=source_space.nivel,
                name=None if is_compound else source_space.nombre,
                semantic_mode=semantic_mode,
                semantic_state="INFERIDO",
                geometry_state="INFERIDO",
                vertices=vertices,
                area_px2=area_px2,
                perimeter_px=perimeter_px,
                centroid_x=bbox.center_x,
                centroid_y=bbox.center_y,
                bbox=[bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max],
                uses_virtual_closure=False,
                semantic_candidates=[semantic_reference],
                semantic_zones=zones,
                dimensions=([] if is_compound else dimension_references),
                metric_area_m2=None,
                state="INFERIDO",
                confirmed=False,
            ),
            zones,
        )

    @staticmethod
    def _validate_inputs(
        *,
        shapely_geometry: ShapelyPlanGeometryResult,
        reconciliation: PlanGeometryReconciliationResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        wall_geometry: WallGeometryResolverResult,
    ) -> None:
        page = (
            shapely_geometry.page
        )

        if (
            reconciliation.page
            != page
            or dimension_grounding.page
            != page
            or wall_geometry.page
            != page
        ):
            raise ValueError(
                "Los servicios espaciales pertenecen "
                "a páginas distintas."
            )

        width = (
            shapely_geometry.width_px
        )

        height = (
            shapely_geometry.height_px
        )

        if (
            reconciliation.width_px
            != width
            or reconciliation.height_px
            != height
            or dimension_grounding.width_px
            != width
            or dimension_grounding.height_px
            != height
            or wall_geometry.width_px
            != width
            or wall_geometry.height_px
            != height
        ):
            raise ValueError(
                "Los servicios espaciales no utilizan "
                "el mismo raster canónico."
            )

    # ========================================================
    # SEMÁNTICA
    # ========================================================

    @staticmethod
    def _semantic_reference(
        candidate: FaceSemanticCandidate,
    ) -> SpaceSemanticReference:
        return SpaceSemanticReference(
            space_id=
                candidate.space_id,

            level=
                candidate.nivel,

            name=
                candidate.nombre,

            bbox_overlap_ratio=
                candidate
                .bbox_overlap_ratio,

            face_overlap_ratio=
                candidate
                .face_overlap_ratio,

            centroid_inside_localization=
                candidate
                .centroid_inside_localization,

            confirmed=
                False,
        )

    # ========================================================
    # DIMENSIONES POR ESPACIO
    # ========================================================

    @staticmethod
    def _dimensions_by_space(
        grounding: ArchitecturalDimensionGroundingResult,
    ) -> dict[
        str,
        list[
            ResolvedSpaceDimension
        ],
    ]:
        result: dict[
            str,
            list[
                ResolvedSpaceDimension
            ],
        ] = {}

        for dimension in (
            grounding
            .resolved_space_dimensions
        ):
            result.setdefault(
                dimension.space_id,
                [],
            ).append(
                dimension
            )

        return result

    # ========================================================
    # DIMENSION REFERENCE
    # ========================================================

    @staticmethod
    def _dimension_reference(
        dimension: ResolvedSpaceDimension,
    ) -> SpaceDimensionReference:
        return SpaceDimensionReference(
            dimension_id=
                dimension.id,

            dimension_axis=
                dimension.dimension_axis,

            value_m=
                dimension.value_m,

            pixel_span=
                dimension.pixel_span,

            pixels_per_meter=
                dimension
                .pixels_per_meter,

            start_axis_label=
                dimension
                .start_axis_label,

            end_axis_label=
                dimension
                .end_axis_label,

            component_span_ids=
                list(
                    dimension
                    .component_span_ids
                ),

            evidence_sources=
                list(
                    dimension
                    .evidence_sources
                ),

            state=
                dimension.state,

            confirmed=
                False,
        )

    # ========================================================
    # ZONA SEMÁNTICA
    # ========================================================

    def _build_semantic_zone(
        self,
        *,
        zone_id: str,
        face: ArchitecturalFaceCandidate,
        candidate: FaceSemanticCandidate,
        source_space: SpaceGeometryReconciliation,
        dimensions: list[
            ResolvedSpaceDimension
        ],
        zone_name: str,
        inferred_from_compound_name: bool,
    ) -> ResolvedSemanticZone | None:
        face_polygon = (
            self._face_polygon(
                face
            )
        )

        if face_polygon is None:
            return None

        localization = (
            source_space
            .localization_bbox
        )

        semantic_bbox = box(
            localization.x_min,
            localization.y_min,
            localization.x_max,
            localization.y_max,
        )

        intersection = (
            face_polygon.intersection(
                semantic_bbox
            )
        )

        if intersection.is_empty:
            return None

        polygons = (
            self._geometry_polygons(
                intersection
            )
        )

        min_x, min_y, max_x, max_y = (
            intersection.bounds
        )

        return ResolvedSemanticZone(
            id=
                zone_id,

            source_space_id=
                candidate.space_id,

            level=
                candidate.nivel,

            name=
                zone_name,

            bbox_overlap_ratio=
                candidate
                .bbox_overlap_ratio,

            face_overlap_ratio=
                candidate
                .face_overlap_ratio,

            centroid_inside_localization=
                candidate
                .centroid_inside_localization,

            area_px2=
                float(
                    intersection.area
                ),

            bbox=[
                float(
                    min_x
                ),
                float(
                    min_y
                ),
                float(
                    max_x
                ),
                float(
                    max_y
                ),
            ],

            polygons=
                polygons,

            dimension_candidates=[
                self._dimension_reference(
                    dimension
                )
                for dimension
                in dimensions
            ],

            geometry_source=(
                "compound_semantic_bbox_shared"
                if inferred_from_compound_name
                else "gemini_bbox_intersection"
            ),

            state=(
                "INFERIDO"
                if inferred_from_compound_name
                else "DETECTADO"
            ),

            confirmed=
                False,
        )

    @staticmethod
    def _compound_zone_names(value: str) -> list[str]:
        normalized = str(value or "").casefold()
        known_zones = (
            ("estancia", "Estancia"),
            ("comedor", "Comedor"),
            ("cocina", "Cocina"),
        )
        detected = [
            display_name
            for token, display_name in known_zones
            if token in normalized
        ]

        return detected if len(detected) > 1 else [str(value)]

    # ========================================================
    # FACE POLYGON
    # ========================================================

    @staticmethod
    def _face_polygon(
        face: ArchitecturalFaceCandidate,
    ) -> Polygon | None:
        if (
            len(
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
    # INTERSECTION → POLYGONS
    # ========================================================

    @staticmethod
    def _geometry_polygons(
        geometry: Any,
    ) -> list[
        list[
            tuple[
                float,
                float,
            ]
        ]
    ]:
        result: list[
            list[
                tuple[
                    float,
                    float,
                ]
            ]
        ] = []

        geometries = getattr(
            geometry,
            "geoms",
            None,
        )

        items = (
            list(
                geometries
            )
            if geometries is not None
            else [
                geometry
            ]
        )

        for item in items:
            if not isinstance(
                item,
                Polygon,
            ):
                continue

            coordinates = list(
                item.exterior.coords
            )

            if (
                len(
                    coordinates
                )
                > 1
                and coordinates[0]
                == coordinates[-1]
            ):
                coordinates = (
                    coordinates[:-1]
                )

            result.append(
                [
                    (
                        float(
                            x
                        ),
                        float(
                            y
                        ),
                    )
                    for x, y
                    in coordinates
                ]
            )

        return result

    # ========================================================
    # WALLS POR FACE
    # ========================================================

    def _walls_for_face(
        self,
        *,
        face_id: str,
        walls: list[
            ResolvedWallGeometry
        ],
    ) -> list[
        SpaceWallReference
    ]:
        result: list[
            SpaceWallReference
        ] = []

        for wall in walls:
            positions: set[str] = set()

            segment_ids: set[str] = set()

            shared_length = 0.0

            conflict = False

            for segment in wall.segments:
                matched = False

                for reference in (
                    segment
                    .side_a_candidates
                    + segment
                    .side_b_candidates
                ):
                    if (
                        reference.face_id
                        != face_id
                    ):
                        continue

                    matched = True

                    positions.add(
                        reference.position
                    )

                    shared_length += (
                        reference
                        .shared_boundary_length_px
                    )

                if matched:
                    segment_ids.add(
                        segment
                        .graph_edge_id
                    )

                    conflict = (
                        conflict
                        or segment
                        .side_conflict
                    )

            if not segment_ids:
                continue

            result.append(
                SpaceWallReference(
                    wall_id=
                        wall.id,

                    continuity_group_id=
                        wall
                        .continuity_group_id,

                    orientation=
                        wall.orientation,

                    positions=
                        sorted(
                            positions
                        ),

                    shared_boundary_length_px=
                        shared_length,

                    source_segment_ids=
                        sorted(
                            segment_ids
                        ),

                    association_conflict=
                        conflict,

                    wall_state=
                        wall.state,

                    confirmed=
                        False,
                )
            )

        result.sort(
            key=lambda item:
                -item
                .shared_boundary_length_px
        )

        return result

    # ========================================================
    # OPENINGS
    # ========================================================

    @staticmethod
    def _openings_for_space(
        *,
        walls: list[
            ResolvedWallGeometry
        ],
        wall_refs: list[
            SpaceWallReference
        ],
        semantic_space_ids: set[str],
    ) -> list[
        SpaceOpeningReference
    ]:
        if not semantic_space_ids:
            return []

        wall_ids = {
            reference.wall_id
            for reference
            in wall_refs
        }

        result: list[
            SpaceOpeningReference
        ] = []

        seen: set[
            tuple[
                str,
                str,
            ]
        ] = set()

        for wall in walls:
            if wall.id not in wall_ids:
                continue

            for opening in wall.openings:
                if (
                    opening.space_id
                    not in semantic_space_ids
                ):
                    continue

                key = (
                    opening.opening_id,
                    wall.id,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                result.append(
                    SpaceOpeningReference(
                        opening_id=
                            opening.opening_id,

                        opening_type=
                            opening.opening_type,

                        wall_id=
                            wall.id,

                        gap_id=
                            opening.gap_id,

                        level=
                            opening.level,

                        semantic_location=
                            opening
                            .semantic_location,

                        direction=
                            opening.direction,

                        association_type=
                            opening
                            .association_type,

                        state=
                            opening.state,

                        confirmed=
                            False,
                    )
                )

        return result

    # ========================================================
    # ADYACENCIAS
    # ========================================================

    @staticmethod
    def _adjacency_lookup(
        adjacencies: list[
            FaceAdjacency
        ],
    ) -> dict[
        str,
        list[str],
    ]:
        result: dict[
            str,
            list[str],
        ] = {}

        for adjacency in adjacencies:
            result.setdefault(
                adjacency.face_a,
                [],
            ).append(
                adjacency.face_b
            )

            result.setdefault(
                adjacency.face_b,
                [],
            ).append(
                adjacency.face_a
            )

        for face_id in result:
            result[
                face_id
            ] = sorted(
                set(
                    result[
                        face_id
                    ]
                )
            )

        return result


# ============================================================
# FACTORY
# ============================================================


def get_space_geometry_resolver(
) -> SpaceGeometryResolver:
    return SpaceGeometryResolver()
