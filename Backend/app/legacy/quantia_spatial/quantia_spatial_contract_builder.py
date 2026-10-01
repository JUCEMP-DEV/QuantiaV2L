from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.schemas.quantia_spatial_contract import (
    QuantiaSpatialContract,
    RasterGeometry,
    SpatialAxis,
    SpatialBBox,
    SpatialBaseLayer,
    SpatialDimension,
    SpatialDoor,
    SpatialEvidence,
    SpatialGeometry,
    SpatialGeometryMetadata,
    SpatialLevel,
    SpatialOrigin,
    SpatialPoint,
    SpatialSemanticZone,
    SpatialSpace,
    SpatialSpaceDimension,
    SpatialStair,
    SpatialWall,
    SpatialWallSegment,
    SpatialWallSide,
    SpatialWindow,
)
from app.legacy.quantia_spatial.architectural_wall_abstraction_service import (
    ArchitecturalWallAbstractionResult,
)
from app.legacy.quantia_spatial.architectural_dimension_grounding_service import (
    ArchitecturalDimensionGroundingResult,
    AxisSpanGrounding,
    ResolvedSpaceDimension,
)
from app.legacy.quantia_spatial.plan_geometry_reconciler import (
    GeometryTextEvidence,
    PlanGeometryReconciliationResult,
)
from app.legacy.quantia_spatial.quantia_extraction_reconciler import (
    QuantiaReconciliationResult,
)
from app.legacy.quantia_spatial.space_geometry_resolver import (
    ResolvedSemanticZone,
    ResolvedSpaceGeometry,
    SpaceGeometryResolverResult,
)
from app.legacy.quantia_spatial.wall_geometry_resolver import (
    ResolvedWallGeometry,
    WallGeometryResolverResult,
)
from app.legacy.quantia_spatial.wall_opening_topology_service import (
    WallGapCandidate,
    WallOpeningTopologyResult,
)

# ============================================================
# ESTADOS SOPORTADOS
# ============================================================


VALID_STATES = {
    "DETECTADO",
    "INFERIDO",
    "NO_IDENTIFICADO",
    "CONFLICTO",
    "CANDIDATO",
    "PENDIENTE",
}


@dataclass(slots=True)
class _ContractWallTrace:
    """Geometría arquitectónica estable que se publicará hacia 04."""

    id: str
    orientation: str
    x1: float
    y1: float
    x2: float
    y2: float
    length_px: float
    levels: list[str] = field(default_factory=list)
    space_ids: list[str] = field(default_factory=list)
    source_segment_ids: list[str] = field(default_factory=list)
    endpoint_support_ids: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    state: str = "CANDIDATO"
    thickness_px: float | None = None
    source_kind: str = "wall_run"


# ============================================================
# BUILDER
# ============================================================


class QuantiaSpatialContractBuilder:
    """
    Construye el contrato canónico:

        03.2
          ↓
        04 Diseño de la vivienda

    ==========================================================
    PRINCIPIOS
    ==========================================================

    1. El plano original llega desde el caller como
       SpatialBaseLayer.

       Este builder NO inventa:

           - URL;
           - storage path;
           - nombre;
           - MIME;
           - dimensiones.

    2. Toda geometría reconstruida actualmente permanece
       disponible en raster_px.

    3. Nunca copia vértices raster dentro de:

           geometria.vertices

       porque 04 interpreta esos vértices como geometría
       métrica.

    4. anchoM / largoM permanecen null mientras no exista
       una normalización explícita de esas magnitudes.

    5. areaM2 permanece null mientras no exista polígono
       métrico validado.

    6. Las dimensiones grounded sí se entregan como cotas y
       restricciones métricas.

    7. Un espacio abierto conserva:

           una geometría física
           +
           varias zonas semánticas.

    8. Todo elemento automático mantiene:

           confirmed = False.
    """

    # ========================================================
    # API
    # ========================================================

    def build(
        self,
        *,
        base_layer: SpatialBaseLayer,
        reconciliation: QuantiaReconciliationResult,
        geometry_reconciliation: PlanGeometryReconciliationResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        wall_abstraction: ArchitecturalWallAbstractionResult,
        topology: WallOpeningTopologyResult,
        wall_geometry: WallGeometryResolverResult,
        space_geometry: SpaceGeometryResolverResult,
    ) -> QuantiaSpatialContract:
        self._validate_inputs(
            base_layer=base_layer,
            geometry_reconciliation=geometry_reconciliation,
            dimension_grounding=dimension_grounding,
            wall_abstraction=wall_abstraction,
            topology=topology,
            wall_geometry=wall_geometry,
            space_geometry=space_geometry,
        )

        # ====================================================
        # METADATOS SEMÁNTICOS
        # ====================================================

        source_space_metadata = self._source_space_metadata(reconciliation)

        # ====================================================
        # MAPEO DE ESPACIOS
        # ====================================================

        (
            contract_space_ids,
            source_to_contract_space,
        ) = self._build_space_id_maps(space_geometry)

        # ====================================================
        # NIVELES
        # ====================================================

        levels = self._build_levels(
            reconciliation=reconciliation,
            base_layer=base_layer,
        )

        # ====================================================
        # EJES
        # ====================================================

        axes = self._build_axes(
            grounding=dimension_grounding,
            base_layer=base_layer,
        )

        # ====================================================
        # COTAS
        # ====================================================

        dimensions = self._build_dimensions(
            grounding=dimension_grounding,
            geometry_reconciliation=geometry_reconciliation,
            base_layer=base_layer,
        )

        # ====================================================
        # PUERTAS / VENTANAS
        # ====================================================

        (
            doors,
            windows,
        ) = self._build_openings(
            topology=topology,
            wall_geometry=wall_geometry,
            base_layer=base_layer,
            source_to_contract_space=source_to_contract_space,
        )

        # ====================================================
        # MUROS REPRESENTATIVOS PARA 04
        # ====================================================

        walls = self._build_walls(
            wall_abstraction=wall_abstraction,
            base_layer=base_layer,
            source_to_contract_space=source_to_contract_space,
        )

        # ====================================================
        # ESPACIOS
        # ====================================================

        spaces = self._build_spaces(
            space_geometry=space_geometry,
            contract_space_ids=contract_space_ids,
            source_to_contract_space=source_to_contract_space,
            source_space_metadata=source_space_metadata,
            walls=walls,
            doors=doors,
            windows=windows,
            base_layer=base_layer,
        )

        # ====================================================
        # ZONAS SEMÁNTICAS
        # ====================================================

        zones = self._build_semantic_zones(
            space_geometry=space_geometry,
            contract_space_ids=contract_space_ids,
            source_space_metadata=source_space_metadata,
            base_layer=base_layer,
        )

        # ====================================================
        # ESCALERAS
        # ====================================================

        stairs = self._build_stairs(
            reconciliation=reconciliation,
            base_layer=base_layer,
        )

        # ====================================================
        # ESTADO GLOBAL
        # ====================================================

        global_state = self._global_state(
            walls=walls,
            spaces=spaces,
            dimensions=dimensions,
        )

        metric_complete = self._metric_geometry_complete(spaces)

        # ====================================================
        # CONTRATO FINAL 03.2 → 04
        # ====================================================

        return QuantiaSpatialContract(
            planoBase=base_layer.model_copy(deep=True),
            niveles=levels,
            ejes=axes,
            muros=walls,
            espacios=spaces,
            zonasSemanticas=zones,
            puertas=doors,
            ventanas=windows,
            escaleras=stairs,
            cotas=dimensions,
            geometria=SpatialGeometryMetadata(
                anchoRasterPx=space_geometry.width_px,
                altoRasterPx=space_geometry.height_px,
                geometriaMetricaCompleta=metric_complete,
                notas=[
                    (
                        "La geometría raster se conserva "
                        "separada de la geometría métrica."
                    ),
                    ("Los vértices px no se entregan " "como vértices métricos a 04."),
                    (
                        "Las cotas grounded pueden estar "
                        "disponibles aunque la geometría "
                        "métrica completa aún no exista."
                    ),
                    (
                        "Los muros publicados en 04 "
                        "proceden de la abstracción "
                        "arquitectónica representativa."
                    ),
                    (
                        "La topología analítica utilizada "
                        "por Shapely permanece separada "
                        "de la representación visual."
                    ),
                    (
                        "areaM2 permanece null hasta "
                        "obtener un polígono métrico "
                        "validado."
                    ),
                ],
            ),
            origen=[],
            confianza=None,
            estado=global_state,
            confirmed=False,
        )

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    @staticmethod
    def _validate_inputs(
        *,
        base_layer: SpatialBaseLayer,
        geometry_reconciliation: PlanGeometryReconciliationResult,
        dimension_grounding: ArchitecturalDimensionGroundingResult,
        wall_abstraction: ArchitecturalWallAbstractionResult,
        topology: WallOpeningTopologyResult,
        wall_geometry: WallGeometryResolverResult,
        space_geometry: SpaceGeometryResolverResult,
    ) -> None:
        page = geometry_reconciliation.page

        width = geometry_reconciliation.width_px

        height = geometry_reconciliation.height_px

        services = [
            (
                dimension_grounding.page,
                dimension_grounding.width_px,
                dimension_grounding.height_px,
                "dimension_grounding",
            ),
            (
                wall_abstraction.page,
                wall_abstraction.width_px,
                wall_abstraction.height_px,
                "wall_abstraction",
            ),
            (
                topology.page,
                topology.width_px,
                topology.height_px,
                "topology",
            ),
            (
                wall_geometry.page,
                wall_geometry.width_px,
                wall_geometry.height_px,
                "wall_geometry",
            ),
            (
                space_geometry.page,
                space_geometry.width_px,
                space_geometry.height_px,
                "space_geometry",
            ),
        ]

        for (
            service_page,
            service_width,
            service_height,
            service_name,
        ) in services:
            if service_page != page:
                raise ValueError(f"{service_name} pertenece " "a una página diferente.")

            if service_width != width or service_height != height:
                raise ValueError(
                    f"{service_name} no utiliza " "el mismo raster canónico."
                )

        if base_layer.pagina != page:
            raise ValueError(
                "planoBase pertenece a una página " "diferente de la reconstrucción."
            )

        if base_layer.anchoPx != width or base_layer.altoPx != height:
            raise ValueError(
                "Las dimensiones de planoBase no " "coinciden con el raster canónico."
            )

    # ========================================================
    # METADATOS SEMÁNTICOS ORIGINALES
    # ========================================================

    def _source_space_metadata(
        self,
        reconciliation: QuantiaReconciliationResult,
    ) -> dict[
        str,
        dict[str, Any],
    ]:
        result: dict[
            str,
            dict[str, Any],
        ] = {}

        extraction = reconciliation.extraction

        for level in extraction.niveles:
            level_name = str(
                getattr(
                    level,
                    "nombre",
                    "",
                )
                or ""
            )

            for space in getattr(
                level,
                "espacios",
                [],
            ):
                space_id = str(
                    getattr(
                        space,
                        "id_propuesto",
                        "",
                    )
                    or ""
                ).strip()

                if not space_id:
                    continue

                result[space_id] = {
                    "nombre": self._nullable_text(
                        getattr(
                            space,
                            "nombre",
                            None,
                        )
                    ),
                    "tipo": self._nullable_text(
                        getattr(
                            space,
                            "tipo",
                            None,
                        )
                    ),
                    "nivel": level_name,
                    "confianza": self._nullable_confidence(
                        getattr(
                            space,
                            "confianza",
                            None,
                        )
                    ),
                    "estado": self._state(
                        getattr(
                            space,
                            "estado",
                            None,
                        ),
                        fallback="CANDIDATO",
                    ),
                    "doble_altura": bool(
                        getattr(
                            space,
                            "doble_altura",
                            False,
                        )
                    ),
                    "evidencia": list(
                        getattr(
                            space,
                            "evidencia",
                            [],
                        )
                        or []
                    ),
                }

        return result

    # ========================================================
    # IDS ESPACIOS FÍSICOS
    # ========================================================

    def _build_space_id_maps(
        self,
        space_geometry: SpaceGeometryResolverResult,
    ) -> tuple[
        dict[
            str,
            str,
        ],
        dict[
            str,
            str | None,
        ],
    ]:
        """
        ESPACIO_UNICO:

            conserva id semántico original.

        MULTIPLES_ZONAS:

            usa SPACE_GEOM_x como espacio físico.

        Esto evita convertir sala/comedor/cocina abiertos
        en tres habitaciones.
        """

        contract_by_face: dict[
            str,
            str,
        ] = {}

        source_targets: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for space in space_geometry.spaces:
            if (
                space.semantic_mode == "ESPACIO_UNICO"
                and len(space.semantic_candidates) == 1
            ):
                contract_id = space.semantic_candidates[0].space_id

            else:
                contract_id = space.id

            contract_by_face[space.face_id] = contract_id

            for candidate in space.semantic_candidates:
                source_targets[candidate.space_id].add(contract_id)

        source_to_contract: dict[
            str,
            str | None,
        ] = {}

        for (
            source_id,
            targets,
        ) in source_targets.items():
            if len(targets) == 1:
                source_to_contract[source_id] = next(iter(targets))

            else:
                # La misma identidad semántica aparece
                # asociada a más de una face.
                #
                # No elegir una arbitrariamente.
                source_to_contract[source_id] = None

        return (
            contract_by_face,
            source_to_contract,
        )

    # ========================================================
    # NIVELES
    # ========================================================

    def _build_levels(
        self,
        *,
        reconciliation: QuantiaReconciliationResult,
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialLevel]:
        result: list[SpatialLevel] = []

        for index, level in enumerate(
            reconciliation.extraction.niveles,
            start=1,
        ):
            level_name = str(
                getattr(
                    level,
                    "nombre",
                    "",
                )
                or ""
            ).strip()

            if not level_name:
                continue

            child_states = [
                self._state(
                    getattr(
                        space,
                        "estado",
                        None,
                    ),
                    fallback="CANDIDATO",
                )
                for space in getattr(
                    level,
                    "espacios",
                    [],
                )
            ]

            level_state = self._aggregate_states(
                child_states,
                fallback="DETECTADO",
            )

            result.append(
                SpatialLevel(
                    id=f"LEVEL_{index}",
                    nombre=level_name,
                    pagina=base_layer.pagina,
                    estado=level_state,
                    confianza=None,
                    confirmed=False,
                    origen=[
                        self._origin(
                            base_layer=base_layer,
                            source="gemini_vision",
                        )
                    ],
                )
            )

        return result

    # ========================================================
    # EJES
    # ========================================================

    def _build_axes(
        self,
        *,
        grounding: ArchitecturalDimensionGroundingResult,
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialAxis]:
        result: list[SpatialAxis] = []

        for axis in grounding.axis_anchors:
            state = "CONFLICTO" if axis.ambiguous_orientation else "DETECTADO"

            origins = [
                self._origin(
                    base_layer=base_layer,
                    source=source,
                )
                for source in sorted(set(axis.evidence_sources))
            ]

            evidence: list[SpatialEvidence] = []

            for index, bbox in enumerate(axis.evidence_bboxes):
                source = (
                    axis.evidence_sources[
                        min(
                            index,
                            len(axis.evidence_sources) - 1,
                        )
                    ]
                    if axis.evidence_sources
                    else None
                )

                if source is None:
                    continue

                evidence.append(
                    SpatialEvidence(
                        fuente=source,
                        descripcion=(
                            "Etiqueta de eje alineada " "con geometría raster."
                        ),
                        pagina=base_layer.pagina,
                        bboxRaster=self._bbox_from_list(bbox),
                        confianza=axis.confidence,
                    )
                )

            result.append(
                SpatialAxis(
                    id=axis.id,
                    etiqueta=axis.label,
                    orientacion=axis.orientation,
                    coordenadaPx=axis.coordinate_px,
                    coordenadaM=None,
                    segmentosSoporte=list(axis.supporting_segment_ids),
                    origen=origins,
                    evidencia=evidence,
                    confianza=axis.confidence,
                    estado=state,
                    confirmed=False,
                )
            )

        return result

    # ========================================================
    # COTAS
    # ========================================================

    def _build_dimensions(
        self,
        *,
        grounding: ArchitecturalDimensionGroundingResult,
        geometry_reconciliation: PlanGeometryReconciliationResult,
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialDimension]:
        result: list[SpatialDimension] = []

        used_evidence: set[tuple[Any, ...]] = set()

        # ====================================================
        # COTAS GROUNDED ENTRE EJES
        # ====================================================

        for span in grounding.axis_spans:
            for item in span.dimension_evidence:
                used_evidence.add(
                    self._dimension_evidence_key(
                        source=item.source,
                        text=item.text,
                        bbox=item.bbox,
                    )
                )

            result.append(
                self._axis_span_dimension(
                    span=span,
                    base_layer=base_layer,
                )
            )

        # ====================================================
        # COTAS RASTER/PDF TODAVÍA NO ASOCIADAS
        # ====================================================

        raw_counter = 0

        for item in geometry_reconciliation.dimension_evidence:
            key = self._dimension_evidence_key(
                source=item.source,
                text=item.text,
                bbox=item.bbox,
            )

            if key in used_evidence:
                continue

            raw_counter += 1

            result.append(
                SpatialDimension(
                    id=f"COTA_RAW_{raw_counter}",
                    nivel=None,
                    # El número existe, pero todavía no se
                    # promovió como dimensión espacial.
                    valorM=None,
                    valorOriginal=item.text,
                    unidadOriginal=item.numeric_unit,
                    direccion="desconocida",
                    ejeInicioId=None,
                    ejeFinId=None,
                    ejeInicioEtiqueta=None,
                    ejeFinEtiqueta=None,
                    longitudPx=None,
                    geometria=self._bbox_geometry(item.bbox),
                    origen=[
                        self._origin(
                            base_layer=base_layer,
                            source=item.source,
                        )
                    ],
                    evidencia=[
                        SpatialEvidence(
                            fuente=item.source,
                            descripcion=(
                                "Cota encontrada pero "
                                "sin asociación espacial "
                                "resuelta."
                            ),
                            pagina=item.page,
                            textoOriginal=item.text,
                            bboxRaster=self._bbox_from_list(item.bbox),
                            confianza=item.confidence,
                        )
                    ],
                    confianza=item.confidence,
                    estado="CANDIDATO",
                    confirmed=False,
                )
            )

        return result

    # ========================================================
    # AXIS SPAN → COTA
    # ========================================================

    def _axis_span_dimension(
        self,
        *,
        span: AxisSpanGrounding,
        base_layer: SpatialBaseLayer,
    ) -> SpatialDimension:
        evidence = [
            SpatialEvidence(
                fuente=item.source,
                descripcion=(
                    "Cota asociada espacialmente "
                    f"al tramo "
                    f"{span.start_axis_label}"
                    "→"
                    f"{span.end_axis_label}."
                ),
                pagina=base_layer.pagina,
                textoOriginal=item.text,
                bboxRaster=self._bbox_from_list(item.bbox),
                confianza=item.confidence,
            )
            for item in span.dimension_evidence
        ]

        texts = sorted({item.text for item in span.dimension_evidence if item.text})

        units = sorted(
            {item.numeric_unit for item in span.dimension_evidence if item.numeric_unit}
        )

        return SpatialDimension(
            id=span.id,
            nivel=span.level,
            valorM=(span.value_m if span.state == "DETECTADO" else None),
            valorOriginal=(texts[0] if len(texts) == 1 else None),
            unidadOriginal=(units[0] if len(units) == 1 else None),
            direccion=(
                span.measurement_direction
                if span.measurement_direction
                in {
                    "horizontal",
                    "vertical",
                }
                else "desconocida"
            ),
            ejeInicioId=span.start_axis_id,
            ejeFinId=span.end_axis_id,
            ejeInicioEtiqueta=span.start_axis_label,
            ejeFinEtiqueta=span.end_axis_label,
            longitudPx=span.pixel_span,
            geometria=None,
            origen=[
                self._origin(
                    base_layer=base_layer,
                    source=source,
                )
                for source in sorted({item.source for item in span.dimension_evidence})
            ],
            evidencia=evidence,
            confianza=None,
            estado=self._state(
                span.state,
                fallback="CANDIDATO",
            ),
            confirmed=False,
        )

    # ========================================================
    # OPENINGS
    # ========================================================

    def _build_openings(
        self,
        *,
        topology: WallOpeningTopologyResult,
        wall_geometry: WallGeometryResolverResult,
        base_layer: SpatialBaseLayer,
        source_to_contract_space: dict[
            str,
            str | None,
        ],
    ) -> tuple[
        list[SpatialDoor],
        list[SpatialWindow],
    ]:
        gap_lookup = {gap.id: gap for gap in topology.gap_candidates}

        semantic_lookup = {
            (
                opening.id,
                opening.opening_type,
            ): opening
            for opening in topology.openings
        }

        associations: dict[
            tuple[
                str,
                str,
            ],
            list[
                tuple[
                    str,
                    Any,
                ]
            ],
        ] = defaultdict(list)

        for wall in wall_geometry.walls:
            for opening in wall.openings:
                associations[
                    (
                        opening.opening_id,
                        opening.opening_type,
                    )
                ].append(
                    (
                        wall.id,
                        opening,
                    )
                )

        doors: list[SpatialDoor] = []

        windows: list[SpatialWindow] = []

        for (
            opening_id,
            opening_type,
        ), items in associations.items():
            wall_ids = sorted({wall_id for wall_id, _ in items})

            gap_ids = sorted({opening.gap_id for _, opening in items})

            source_space_ids = sorted(
                {opening.space_id for _, opening in items if opening.space_id}
            )

            semantic = semantic_lookup.get(
                (
                    opening_id,
                    opening_type,
                )
            )

            unique_gap = gap_lookup.get(gap_ids[0]) if len(gap_ids) == 1 else None

            unique_wall_id = wall_ids[0] if len(wall_ids) == 1 else None

            source_space_id = (
                source_space_ids[0] if len(source_space_ids) == 1 else None
            )

            contract_space_id = self._mapped_space_id(
                source_space_id,
                source_to_contract_space,
            )

            conflict = (
                len(wall_ids) > 1 or len(gap_ids) > 1 or len(source_space_ids) > 1
            )

            state = "CONFLICTO" if conflict else "CANDIDATO"

            geometry = (
                self._gap_geometry(unique_gap) if unique_gap is not None else None
            )

            evidence: list[SpatialEvidence] = []

            if wall_ids:
                evidence.append(
                    SpatialEvidence(
                        fuente="wall_opening_topology",
                        descripcion=("Muros candidatos: " + ", ".join(wall_ids)),
                        pagina=base_layer.pagina,
                    )
                )

            if gap_ids:
                evidence.append(
                    SpatialEvidence(
                        fuente="wall_opening_topology",
                        descripcion=("Gaps candidatos: " + ", ".join(gap_ids)),
                        pagina=base_layer.pagina,
                    )
                )

            confidence = semantic.confidence if semantic is not None else None

            common = {
                "id": opening_id,
                "nivel": (semantic.level if semantic is not None else None),
                # El muro analítico original se conserva
                # en evidence, pero no se publica como
                # muroId porque contract.muros utilizará
                # los WALL_RUN representativos.
                "muroId": None,
                "espacioId": contract_space_id,
                "posicionM": None,
                "anchoM": None,
                "altoM": None,
                "anchoPx": (
                    unique_gap.gap_length_px if unique_gap is not None else None
                ),
                "geometria": geometry,
                "origen": [
                    self._origin(
                        base_layer=base_layer,
                        source="gemini_semantic",
                    ),
                    self._origin(
                        base_layer=base_layer,
                        source="wall_opening_topology",
                    ),
                ],
                "evidencia": evidence,
                "confianza": confidence,
                "estado": state,
                "confirmed": False,
            }

            if opening_type == "puerta":
                doors.append(
                    SpatialDoor(
                        **common,
                        sentido=(semantic.direction if semantic is not None else None),
                    )
                )

            elif opening_type == "ventana":
                windows.append(
                    SpatialWindow(
                        **common,
                    )
                )

        return (
            doors,
            windows,
        )

    # ========================================================
    # MUROS
    # ========================================================

    # ========================================================
    # MUROS REPRESENTATIVOS PARA 04
    # ========================================================

    def _build_walls(
        self,
        *,
        wall_abstraction: ArchitecturalWallAbstractionResult,
        base_layer: SpatialBaseLayer,
        source_to_contract_space: dict[
            str,
            str | None,
        ],
    ) -> list[SpatialWall]:
        """
        Construye los muros representativos entregados a 04.

        Esta colección NO sustituye la geometría analítica
        utilizada internamente por:

            grafo
            topology
            Shapely
            WallGeometryResolver

        Los centerlines válidos sustituyen exclusivamente las
        caras gráficas que consumen. Los wall runs no consumidos
        permanecen como candidatos para evitar perder cobertura.

        No se inventa:

            - espesor métrico;
            - longitud métrica;
            - clasificación interior/exterior;
            - confirmación;
            - geometría métrica desde raster.
        """

        result: list[SpatialWall] = []

        for trace in self._contract_wall_traces(wall_abstraction):
            # =================================================
            # ESPACIOS ASOCIADOS
            # =================================================

            mapped_space_ids = sorted(
                {
                    (
                        self._mapped_space_id(
                            space_id,
                            source_to_contract_space,
                        )
                        or space_id
                    )
                    for space_id in trace.space_ids
                    if space_id
                }
            )

            # =================================================
            # NIVEL
            # =================================================

            levels = sorted({level for level in trace.levels if level})

            wall_level = levels[0] if len(levels) == 1 else None

            # =================================================
            # GEOMETRÍA RASTER
            # =================================================

            geometry = self._line_geometry(
                x1=trace.x1,
                y1=trace.y1,
                x2=trace.x2,
                y2=trace.y2,
            )

            # =================================================
            # ORIGEN
            # =================================================

            origin_sources = sorted(
                {
                    "architectural_wall_abstraction",
                    *trace.sources,
                }
            )

            if trace.source_kind == "centerline":
                origin_sources.append("architectural_wall_centerline")

            origin_sources = sorted(set(origin_sources))

            origins = [
                self._origin(
                    base_layer=base_layer,
                    source=source,
                )
                for source in origin_sources
            ]

            # =================================================
            # EVIDENCIA
            # =================================================

            evidence: list[SpatialEvidence] = [
                SpatialEvidence(
                    fuente=(
                        "architectural_wall_centerline"
                        if trace.source_kind == "centerline"
                        else "architectural_wall_abstraction"
                    ),
                    descripcion=(
                        "Centerline arquitectónico candidato generado "
                        "a partir de dos caras gráficas opuestas."
                        if trace.source_kind == "centerline"
                        else (
                            "Tramo arquitectónico candidato generado "
                            "a partir de evidencia geométrica reconciliada."
                        )
                    ),
                    pagina=base_layer.pagina,
                )
            ]

            for source in sorted(set(trace.sources)):
                evidence.append(
                    SpatialEvidence(
                        fuente=source,
                        descripcion=(
                            "Evidencia geométrica utilizada "
                            "por la abstracción del muro."
                        ),
                        pagina=base_layer.pagina,
                    )
                )

            if trace.source_segment_ids:
                evidence.append(
                    SpatialEvidence(
                        fuente="opencv",
                        descripcion=(
                            "Segmentos de cara conservados como evidencia: "
                            + ", ".join(sorted(trace.source_segment_ids))
                        ),
                        pagina=base_layer.pagina,
                    )
                )

            if trace.endpoint_support_ids:
                evidence.append(
                    SpatialEvidence(
                        fuente="opencv",
                        descripcion=(
                            "Segmentos ortogonales usados únicamente como "
                            "soporte de extremos: "
                            + ", ".join(sorted(trace.endpoint_support_ids))
                        ),
                        pagina=base_layer.pagina,
                    )
                )

            # =================================================
            # SEGMENTO REPRESENTATIVO
            # =================================================

            segment = SpatialWallSegment(
                id=f"{trace.id}_SEGMENT_1",
                rol="wall_trace",
                geometria=geometry,
                estado=self._state(
                    trace.state,
                    fallback="CANDIDATO",
                ),
                confirmed=False,
            )

            # =================================================
            # MURO CONTRACTUAL
            # =================================================

            result.append(
                SpatialWall(
                    id=trace.id,
                    nivel=wall_level,
                    grupoContinuidadId=trace.id,
                    orientacion=trace.orientation,
                    # La abstracción visual todavía no posee
                    # evidencia suficiente para decidir si el
                    # muro es interior o exterior.
                    tipo="incierto",
                    # CRÍTICO:
                    # ningún espesor gráfico de 04 se publica
                    # aquí como espesor constructivo.
                    espesorM=None,
                    espesorFuente=None,
                    espesorEstado="PENDIENTE",
                    espesorObservadoPx=trace.thickness_px,
                    espesorObservadoFuente=(
                        "opencv_raster_face_distance"
                        if trace.thickness_px is not None
                        else None
                    ),
                    ladoA=None,
                    ladoB=None,
                    segmentos=[segment],
                    # La asociación contractual entre los
                    # openings analíticos y WALL_RUN todavía
                    # no ha sido resuelta.
                    puertaIds=[],
                    ventanaIds=[],
                    espacioIds=mapped_space_ids,
                    longitudRealPx=trace.length_px,
                    longitudTopologicaPx=None,
                    geometria=geometry,
                    origen=origins,
                    evidencia=evidence,
                    confianza=None,
                    estado=self._state(
                        trace.state,
                        fallback="CANDIDATO",
                    ),
                    confirmed=False,
                )
            )

        return result

    @staticmethod
    def _contract_wall_traces(
        wall_abstraction: ArchitecturalWallAbstractionResult,
    ) -> list[_ContractWallTrace]:
        """Crea muros híbridos sin reutilizar IDs OpenCV como identidad."""

        wall_run_by_id = {
            wall_run.id: wall_run for wall_run in wall_abstraction.wall_runs
        }

        consumed_wall_run_ids: set[str] = set()
        traces: list[_ContractWallTrace] = []

        for centerline in wall_abstraction.centerlines:
            supporting_runs = [
                wall_run_by_id[wall_run_id]
                for wall_run_id in centerline.wall_run_ids
                if wall_run_id in wall_run_by_id
            ]

            if len(supporting_runs) < 2:
                continue

            consumed_wall_run_ids.update(centerline.wall_run_ids)

            face_segment_ids = set(centerline.face_segment_ids)

            if not face_segment_ids:
                face_segment_ids.update(
                    segment_id
                    for wall_run in supporting_runs
                    for segment_id in wall_run.face_segment_ids
                )

            traces.append(
                _ContractWallTrace(
                    id=centerline.id,
                    orientation=centerline.orientation,
                    x1=float(centerline.x1),
                    y1=float(centerline.y1),
                    x2=float(centerline.x2),
                    y2=float(centerline.y2),
                    length_px=float(centerline.length_px),
                    levels=sorted(set(centerline.levels)),
                    space_ids=sorted(set(centerline.space_ids)),
                    source_segment_ids=sorted(face_segment_ids),
                    endpoint_support_ids=sorted(
                        {
                            segment_id
                            for wall_run in supporting_runs
                            for segment_id in wall_run.endpoint_support_ids
                        }
                    ),
                    sources=sorted(
                        {
                            source
                            for wall_run in supporting_runs
                            for source in wall_run.sources
                        }
                    ),
                    state=centerline.state,
                    thickness_px=float(centerline.thickness_px),
                    source_kind="centerline",
                )
            )

        for wall_run in wall_abstraction.wall_runs:
            if wall_run.id in consumed_wall_run_ids:
                continue

            traces.append(
                _ContractWallTrace(
                    id=wall_run.id,
                    orientation=wall_run.orientation,
                    x1=float(wall_run.x1),
                    y1=float(wall_run.y1),
                    x2=float(wall_run.x2),
                    y2=float(wall_run.y2),
                    length_px=float(wall_run.length_px),
                    levels=list(wall_run.levels),
                    space_ids=list(wall_run.space_ids),
                    source_segment_ids=list(wall_run.face_segment_ids),
                    endpoint_support_ids=list(wall_run.endpoint_support_ids),
                    sources=list(wall_run.sources),
                    state=wall_run.state,
                    source_kind="wall_run",
                )
            )

        traces.sort(key=lambda trace: (trace.source_kind != "centerline", trace.id))

        return traces

    # ========================================================
    # LADO DE MURO
    # ========================================================

    def _wall_side_summary(
        self,
        *,
        wall: ResolvedWallGeometry,
        side_name: str,
        source_to_contract_space: dict[
            str,
            str | None,
        ],
    ) -> SpatialWallSide | None:
        references = []

        for segment in wall.segments:
            reference = getattr(
                segment,
                side_name,
                None,
            )

            if reference is not None:
                references.append(reference)

        unique = {}

        for reference in references:
            key = (
                reference.face_id,
                reference.primary_space_id,
                reference.position,
            )

            unique[key] = reference

        if len(unique) != 1:
            return None

        reference = next(iter(unique.values()))

        return SpatialWallSide(
            faceId=reference.face_id,
            espacioId=self._mapped_space_id(
                reference.primary_space_id,
                source_to_contract_space,
            ),
            espacioNombre=reference.primary_space_name,
            posicion=reference.position,
            confirmed=False,
        )

    # ========================================================
    # ESPACIOS
    # ========================================================

    def _build_spaces(
        self,
        *,
        space_geometry: SpaceGeometryResolverResult,
        contract_space_ids: dict[
            str,
            str,
        ],
        source_to_contract_space: dict[
            str,
            str | None,
        ],
        source_space_metadata: dict[
            str,
            dict[str, Any],
        ],
        walls: list[SpatialWall],
        doors: list[SpatialDoor],
        windows: list[SpatialWindow],
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialSpace]:
        result: list[SpatialSpace] = []

        # ====================================================
        # OPENINGS POR ESPACIO
        # ====================================================

        doors_by_space: dict[
            str,
            list[SpatialDoor],
        ] = defaultdict(list)

        windows_by_space: dict[
            str,
            list[SpatialWindow],
        ] = defaultdict(list)

        for door in doors:
            if door.espacioId:
                doors_by_space[door.espacioId].append(door)

        for window in windows:
            if window.espacioId:
                windows_by_space[window.espacioId].append(window)

        # ====================================================
        # MUROS REPRESENTATIVOS POR ESPACIO
        # ====================================================

        walls_by_space: dict[
            str,
            list[SpatialWall],
        ] = defaultdict(list)

        for wall in walls:
            for space_id in wall.espacioIds:
                if not space_id:
                    continue

                walls_by_space[space_id].append(wall)

        # ====================================================
        # ESPACIOS RESUELTOS
        # ====================================================

        for space in space_geometry.spaces:
            canvas_area = float(
                max(1, space_geometry.width_px * space_geometry.height_px)
            )

            if (
                space.semantic_mode == "SIN_SEMANTICA"
                and space.area_px2 < canvas_area * 0.002
            ):
                continue

            contract_id = contract_space_ids[space.face_id]
            is_semantic_fallback = space.face_id.startswith("SEMANTIC_BBOX_")

            semantic_ids = [
                candidate.space_id for candidate in space.semantic_candidates
            ]

            metadata_items = [
                source_space_metadata[semantic_id]
                for semantic_id in semantic_ids
                if semantic_id in source_space_metadata
            ]

            # =================================================
            # NOMBRE
            # =================================================

            if space.name:
                name = space.name

            else:
                names: list[str] = []

                for zone in space.semantic_zones:
                    if zone.name and zone.name not in names:
                        names.append(zone.name)

                if not names:
                    for candidate in space.semantic_candidates:
                        if candidate.name and candidate.name not in names:
                            names.append(candidate.name)

                name = " / ".join(names) if names else space.face_id

            # =================================================
            # TIPO
            # =================================================

            types = sorted(
                {str(item["tipo"]) for item in metadata_items if item.get("tipo")}
            )

            space_type = types[0] if len(types) == 1 else "NO_IDENTIFICADO"

            # =================================================
            # NIVEL
            # =================================================

            levels = sorted(
                {str(item["nivel"]) for item in metadata_items if item.get("nivel")}
            )

            level = space.level or (
                levels[0] if len(levels) == 1 else "NO_IDENTIFICADO"
            )

            # =================================================
            # CONFIANZA / DOBLE ALTURA
            # =================================================

            confidence = (
                metadata_items[0].get("confianza")
                if (space.semantic_mode == "ESPACIO_UNICO" and len(metadata_items) == 1)
                else None
            )

            double_height = (
                bool(
                    metadata_items[0].get(
                        "doble_altura",
                        False,
                    )
                )
                if (space.semantic_mode == "ESPACIO_UNICO" and len(metadata_items) == 1)
                else False
            )

            # =================================================
            # DIMENSIONES
            # =================================================

            dimensions = [
                SpatialSpaceDimension(
                    id=dimension.dimension_id,
                    eje=dimension.dimension_axis,
                    valorM=dimension.value_m,
                    ejeInicio=dimension.start_axis_label,
                    ejeFin=dimension.end_axis_label,
                    estado=self._state(
                        dimension.state,
                        fallback="CANDIDATO",
                    ),
                    confirmed=False,
                )
                for dimension in space.dimensions
            ]

            # No mapear automáticamente:
            #
            # x → ancho
            # y → largo
            #
            # porque esa convención todavía no está fijada.

            width_m = None

            length_m = None

            # =================================================
            # OPENINGS
            # =================================================

            space_doors = list(
                doors_by_space.get(
                    contract_id,
                    [],
                )
            )

            space_windows = list(
                windows_by_space.get(
                    contract_id,
                    [],
                )
            )

            # =================================================
            # MUROS REPRESENTATIVOS
            # =================================================

            space_walls = list(
                walls_by_space.get(
                    contract_id,
                    [],
                )
            )

            wall_ids = sorted({wall.id for wall in space_walls})

            # =================================================
            # GEOMETRÍA
            # =================================================

            geometry = self._space_geometry(space)

            # =================================================
            # CONTRATO ESPACIAL
            # =================================================

            result.append(
                SpatialSpace(
                    id=contract_id,
                    faceId=(None if is_semantic_fallback else space.face_id),
                    nombre=name,
                    tipo=space_type,
                    nivel=level,
                    anchoM=width_m,
                    largoM=length_m,
                    areaM2=None,
                    geometria=geometry,
                    dobleAltura=double_height,
                    semanticMode=space.semantic_mode,
                    zonaIds=[zone.id for zone in space.semantic_zones],
                    muroIds=wall_ids,
                    puertaIds=[door.id for door in space_doors],
                    ventanaIds=[window.id for window in space_windows],
                    dimensiones=dimensions,
                    puerta=(space_doors[0] if space_doors else None),
                    ventana=(space_windows[0] if space_windows else None),
                    puertas=space_doors,
                    ventanas=space_windows,
                    origen=[
                        self._origin(
                            base_layer=base_layer,
                            source=(
                                "gemini_localization_bbox"
                                if is_semantic_fallback
                                else "shapely_polygonize"
                            ),
                        ),
                        *(
                            [
                                self._origin(
                                    base_layer=base_layer,
                                    source="gemini_semantic",
                                )
                            ]
                            if semantic_ids
                            else []
                        ),
                    ],
                    evidencia=[
                        SpatialEvidence(
                            fuente=(
                                "gemini_localization_bbox"
                                if is_semantic_fallback
                                else "shapely_polygonize"
                            ),
                            descripcion=(
                                (
                                    "Geometría raster aproximada conservada desde "
                                    "la localización semántica; no existe una face "
                                    "Shapely arquitectónica válida."
                                )
                                if is_semantic_fallback
                                else (
                                    f"Face {space.face_id}; "
                                    f"geometry_state={space.geometry_state}; "
                                    f"semantic_mode={space.semantic_mode}."
                                )
                            ),
                            pagina=base_layer.pagina,
                        ),
                        *(
                            [
                                SpatialEvidence(
                                    fuente="wall_opening_topology",
                                    descripcion=(
                                        "El recinto utilizó "
                                        "continuidad virtual "
                                        "para openings."
                                    ),
                                    pagina=base_layer.pagina,
                                )
                            ]
                            if space.uses_virtual_closure
                            else []
                        ),
                        *(
                            [
                                SpatialEvidence(
                                    fuente="architectural_wall_abstraction",
                                    descripcion=(
                                        "El espacio referencia "
                                        "muros representativos "
                                        "publicados para revisión "
                                        "en 04."
                                    ),
                                    pagina=base_layer.pagina,
                                )
                            ]
                            if wall_ids
                            else []
                        ),
                    ],
                    confianzaIA=confidence,
                    estado=self._state(
                        space.state,
                        fallback="CANDIDATO",
                    ),
                    confirmed=False,
                )
            )

        return result

    # ========================================================
    # ZONAS SEMÁNTICAS
    # ========================================================

    def _build_semantic_zones(
        self,
        *,
        space_geometry: SpaceGeometryResolverResult,
        contract_space_ids: dict[
            str,
            str,
        ],
        source_space_metadata: dict[
            str,
            dict[str, Any],
        ],
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialSemanticZone]:
        result: list[SpatialSemanticZone] = []

        parent_by_zone: dict[
            str,
            str,
        ] = {}

        for space in space_geometry.spaces:
            parent_contract_id = contract_space_ids[space.face_id]

            for zone in space.semantic_zones:
                parent_by_zone[zone.id] = parent_contract_id

        for zone in space_geometry.semantic_zones:
            metadata = source_space_metadata.get(
                zone.source_space_id,
                {},
            )

            zone_type = metadata.get("tipo")

            confidence = metadata.get("confianza")
            is_shared_semantic_bbox = (
                zone.geometry_source == "compound_semantic_bbox_shared"
            )

            result.append(
                SpatialSemanticZone(
                    id=zone.id,
                    espacioGeometricoId=parent_by_zone.get(
                        zone.id,
                        zone.source_space_id,
                    ),
                    sourceSpaceId=zone.source_space_id,
                    nivel=zone.level,
                    nombre=zone.name,
                    tipo=zone_type,
                    geometria=self._zone_geometry(zone),
                    origen=[
                        self._origin(
                            base_layer=base_layer,
                            source="gemini_semantic",
                        ),
                        self._origin(
                            base_layer=base_layer,
                            source=(
                                "gemini_localization_bbox"
                                if is_shared_semantic_bbox
                                else "shapely_intersection"
                            ),
                        ),
                    ],
                    evidencia=[
                        SpatialEvidence(
                            fuente="gemini_semantic",
                            descripcion=(
                                "Zona funcional inferida desde un nombre compuesto; "
                                "comparte bbox con el área abierta y no implica "
                                "un límite independiente."
                                if is_shared_semantic_bbox
                                else (
                                    "Zona funcional dentro de una face geométrica; "
                                    "no implica muro."
                                )
                            ),
                            pagina=base_layer.pagina,
                            confianza=confidence,
                        )
                    ],
                    confianza=confidence,
                    estado=self._state(
                        zone.state,
                        fallback="CANDIDATO",
                    ),
                    confirmed=False,
                )
            )

        return result

    # ========================================================
    # ESCALERAS
    # ========================================================

    def _build_stairs(
        self,
        *,
        reconciliation: QuantiaReconciliationResult,
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialStair]:
        result: list[SpatialStair] = []

        special_elements = getattr(
            reconciliation.extraction,
            "elementos_especiales",
            None,
        )

        if special_elements is None:
            return result

        for stair in getattr(
            special_elements,
            "escaleras",
            [],
        ):
            stair_id = str(
                getattr(
                    stair,
                    "id_propuesto",
                    "",
                )
                or ""
            ).strip()

            if not stair_id:
                # No crear identificadores artificiales
                # para una entidad sin identidad.
                continue

            evidence = self._canonical_evidence(
                getattr(
                    stair,
                    "evidencia",
                    [],
                ),
                base_layer=base_layer,
            )

            sources = sorted({item.fuente for item in evidence})

            result.append(
                SpatialStair(
                    id=stair_id,
                    nivel=self._nullable_text(
                        getattr(
                            stair,
                            "nivel",
                            None,
                        )
                    ),
                    tipo=self._nullable_text(
                        getattr(
                            stair,
                            "tipo",
                            None,
                        )
                    ),
                    sentido=self._nullable_text(
                        getattr(
                            stair,
                            "sentido",
                            None,
                        )
                    ),
                    anchoM=self._nullable_number(
                        getattr(
                            stair,
                            "ancho_m",
                            None,
                        )
                    ),
                    largoM=self._nullable_number(
                        getattr(
                            stair,
                            "largo_m",
                            None,
                        )
                    ),
                    geometria=None,
                    origen=[
                        self._origin(
                            base_layer=base_layer,
                            source=source,
                        )
                        for source in sources
                    ],
                    evidencia=evidence,
                    confianza=self._nullable_confidence(
                        getattr(
                            stair,
                            "confianza",
                            None,
                        )
                    ),
                    estado=self._state(
                        getattr(
                            stair,
                            "estado",
                            None,
                        ),
                        fallback="CANDIDATO",
                    ),
                    confirmed=False,
                )
            )

        return result

    # ========================================================
    # GEOMETRÍA ESPACIO
    # ========================================================

    @staticmethod
    def _space_geometry(
        space: ResolvedSpaceGeometry,
    ) -> SpatialGeometry:
        return SpatialGeometry(
            tipo="poligono",
            # CRÍTICO:
            # no copiar vértices px aquí.
            vertices=[],
            areaM2=None,
            perimetroM=None,
            raster=RasterGeometry(
                tipo="poligono",
                vertices=[
                    SpatialPoint(
                        x=x,
                        y=y,
                    )
                    for x, y in space.vertices
                ],
                bbox=SpatialBBox(
                    xMin=space.bbox[0],
                    yMin=space.bbox[1],
                    xMax=space.bbox[2],
                    yMax=space.bbox[3],
                ),
                areaPx2=space.area_px2,
                perimetroPx=space.perimeter_px,
            ),
            metrica=None,
        )

    # ========================================================
    # GEOMETRÍA ZONA
    # ========================================================

    @staticmethod
    def _zone_geometry(
        zone: ResolvedSemanticZone,
    ) -> SpatialGeometry:
        if len(zone.polygons) == 1:
            polygon = zone.polygons[0]

            raster = RasterGeometry(
                tipo="poligono",
                vertices=[
                    SpatialPoint(
                        x=x,
                        y=y,
                    )
                    for x, y in polygon
                ],
                bbox=SpatialBBox(
                    xMin=zone.bbox[0],
                    yMin=zone.bbox[1],
                    xMax=zone.bbox[2],
                    yMax=zone.bbox[3],
                ),
                areaPx2=zone.area_px2,
                perimetroPx=None,
            )

        else:
            # Si la intersección produjo varias islas,
            # no seleccionar arbitrariamente una.
            #
            # Se conserva su bbox aproximado.
            raster = RasterGeometry(
                tipo="bbox",
                vertices=[],
                bbox=SpatialBBox(
                    xMin=zone.bbox[0],
                    yMin=zone.bbox[1],
                    xMax=zone.bbox[2],
                    yMax=zone.bbox[3],
                ),
                areaPx2=zone.area_px2,
                perimetroPx=None,
            )

        return SpatialGeometry(
            tipo=raster.tipo,
            vertices=[],
            areaM2=None,
            perimetroM=None,
            raster=raster,
            metrica=None,
        )

    # ========================================================
    # GAP GEOMETRY
    # ========================================================

    def _gap_geometry(
        self,
        gap: WallGapCandidate,
    ) -> SpatialGeometry:
        return self._line_geometry(
            x1=gap.x1,
            y1=gap.y1,
            x2=gap.x2,
            y2=gap.y2,
        )

    # ========================================================
    # LINE GEOMETRY
    # ========================================================

    @staticmethod
    def _line_geometry(
        *,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> SpatialGeometry:
        bbox = SpatialBBox(
            xMin=min(
                x1,
                x2,
            ),
            yMin=min(
                y1,
                y2,
            ),
            xMax=max(
                x1,
                x2,
            ),
            yMax=max(
                y1,
                y2,
            ),
        )

        return SpatialGeometry(
            tipo="linea",
            vertices=[],
            areaM2=None,
            perimetroM=None,
            raster=RasterGeometry(
                tipo="linea",
                vertices=[
                    SpatialPoint(
                        x=x1,
                        y=y1,
                    ),
                    SpatialPoint(
                        x=x2,
                        y=y2,
                    ),
                ],
                bbox=bbox,
                areaPx2=None,
                perimetroPx=None,
            ),
            metrica=None,
        )

    # ========================================================
    # BBOX GEOMETRY
    # ========================================================

    def _bbox_geometry(
        self,
        bbox: list[float],
    ) -> SpatialGeometry:
        return SpatialGeometry(
            tipo="bbox",
            vertices=[],
            areaM2=None,
            perimetroM=None,
            raster=RasterGeometry(
                tipo="bbox",
                vertices=[],
                bbox=self._bbox_from_list(bbox),
                areaPx2=None,
                perimetroPx=None,
            ),
            metrica=None,
        )

    # ========================================================
    # WALL BBOX
    # ========================================================

    @staticmethod
    def _wall_bbox(
        wall: ResolvedWallGeometry,
    ) -> SpatialBBox | None:
        points = [
            (
                x,
                y,
            )
            for segment in wall.segments
            for x, y in [
                (
                    segment.x1,
                    segment.y1,
                ),
                (
                    segment.x2,
                    segment.y2,
                ),
            ]
        ]

        if not points:
            return None

        xs = [item[0] for item in points]

        ys = [item[1] for item in points]

        return SpatialBBox(
            xMin=min(xs),
            yMin=min(ys),
            xMax=max(xs),
            yMax=max(ys),
        )

    # ========================================================
    # EVIDENCIA CANÓNICA
    # ========================================================

    def _canonical_evidence(
        self,
        items: Any,
        *,
        base_layer: SpatialBaseLayer,
    ) -> list[SpatialEvidence]:
        if not isinstance(
            items,
            list,
        ):
            return []

        result: list[SpatialEvidence] = []

        for item in items:
            source = self._nullable_text(
                getattr(
                    item,
                    "fuente",
                    None,
                )
            )

            if source is None:
                continue

            result.append(
                SpatialEvidence(
                    fuente=source,
                    descripcion=self._nullable_text(
                        getattr(
                            item,
                            "descripcion",
                            None,
                        )
                    ),
                    pagina=(
                        getattr(
                            item,
                            "pagina",
                            None,
                        )
                        or base_layer.pagina
                    ),
                    textoOriginal=self._nullable_text(
                        getattr(
                            item,
                            "texto_original",
                            None,
                        )
                    ),
                    # El schema de extracción puede guardar
                    # bbox PDF/normalizado. Sin una declaración
                    # explícita de sistema no se etiqueta como
                    # bboxRaster.
                    bboxRaster=None,
                    confianza=self._nullable_confidence(
                        getattr(
                            item,
                            "confianza",
                            None,
                        )
                    ),
                )
            )

        return result

    # ========================================================
    # ORIGIN
    # ========================================================

    @staticmethod
    def _origin(
        *,
        base_layer: SpatialBaseLayer,
        source: str,
    ) -> SpatialOrigin:
        return SpatialOrigin(
            documento=base_layer.nombre,
            pagina=base_layer.pagina,
            fuente=source,
            referencia=base_layer.referencia,
        )

    # ========================================================
    # MAP SOURCE SPACE ID
    # ========================================================

    @staticmethod
    def _mapped_space_id(
        source_space_id: str | None,
        mapping: dict[
            str,
            str | None,
        ],
    ) -> str | None:
        if source_space_id is None:
            return None

        mapped = mapping.get(source_space_id)

        # Si una identidad semántica quedó asociada a
        # múltiples faces, no seleccionar una arbitrariamente.
        #
        # Se conserva el ID semántico original.
        if mapped is None:
            return source_space_id

        return mapped

    # ========================================================
    # BBOX
    # ========================================================

    @staticmethod
    def _bbox_from_list(
        bbox: list[float],
    ) -> SpatialBBox:
        if len(bbox) != 4:
            raise ValueError("bbox raster inválido.")

        return SpatialBBox(
            xMin=float(bbox[0]),
            yMin=float(bbox[1]),
            xMax=float(bbox[2]),
            yMax=float(bbox[3]),
        )

    # ========================================================
    # DIMENSION EVIDENCE KEY
    # ========================================================

    @staticmethod
    def _dimension_evidence_key(
        *,
        source: str,
        text: str,
        bbox: list[float],
    ) -> tuple[
        Any,
        ...,
    ]:
        return (
            source,
            text,
            tuple(
                round(
                    float(value),
                    6,
                )
                for value in bbox
            ),
        )

    # ========================================================
    # GEOMETRÍA MÉTRICA COMPLETA
    # ========================================================

    @staticmethod
    def _metric_geometry_complete(
        spaces: list[SpatialSpace],
    ) -> bool:
        if not spaces:
            return False

        for space in spaces:
            metric = space.geometria.metrica

            if (
                metric is None
                or not metric.vertices
                or metric.areaM2 is None
                or metric.perimetroM is None
            ):
                return False

        return True

    # ========================================================
    # ESTADO GLOBAL
    # ========================================================

    def _global_state(
        self,
        *,
        walls: list[SpatialWall],
        spaces: list[SpatialSpace],
        dimensions: list[SpatialDimension],
    ) -> str:
        states = [
            item.estado for item in (list(walls) + list(spaces) + list(dimensions))
        ]

        return self._aggregate_states(
            states,
            fallback="NO_IDENTIFICADO",
        )

    # ========================================================
    # AGREGAR ESTADOS
    # ========================================================

    @staticmethod
    def _aggregate_states(
        states: list[str],
        *,
        fallback: str,
    ) -> str:
        if not states:
            return fallback

        if "CONFLICTO" in states:
            return "CONFLICTO"

        if "INFERIDO" in states:
            return "INFERIDO"

        if "DETECTADO" in states:
            return "DETECTADO"

        if "CANDIDATO" in states:
            return "CANDIDATO"

        if "PENDIENTE" in states:
            return "PENDIENTE"

        if "NO_IDENTIFICADO" in states:
            return "NO_IDENTIFICADO"

        return fallback

    # ========================================================
    # NORMALIZAR ESTADO
    # ========================================================

    @staticmethod
    def _state(
        value: Any,
        *,
        fallback: str,
    ) -> str:
        if value is None:
            return fallback

        enum_value = getattr(
            value,
            "value",
            None,
        )

        text = str(enum_value if enum_value is not None else value).strip().upper()

        if text in VALID_STATES:
            return text

        if text.startswith("INFERIDO"):
            return "INFERIDO"

        if "CONFLICT" in text:
            return "CONFLICTO"

        if "NO_IDENT" in text:
            return "NO_IDENTIFICADO"

        if "PEND" in text:
            return "PENDIENTE"

        if "CANDID" in text:
            return "CANDIDATO"

        if "DETECT" in text:
            return "DETECTADO"

        return fallback

    # ========================================================
    # NULLABLE TEXT
    # ========================================================

    @staticmethod
    def _nullable_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(value).strip()

        return text if text else None

    # ========================================================
    # NULLABLE NUMBER
    # ========================================================

    @staticmethod
    def _nullable_number(
        value: Any,
    ) -> float | None:
        if isinstance(
            value,
            bool,
        ):
            return None

        if not isinstance(
            value,
            (int, float),
        ):
            return None

        return float(value)

    # ========================================================
    # NULLABLE CONFIDENCE
    # ========================================================

    @staticmethod
    def _nullable_confidence(
        value: Any,
    ) -> float | None:
        if isinstance(
            value,
            bool,
        ):
            return None

        if not isinstance(
            value,
            (int, float),
        ):
            return None

        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )


# ============================================================
# FACTORY
# ============================================================


def get_quantia_spatial_contract_builder() -> QuantiaSpatialContractBuilder:
    return QuantiaSpatialContractBuilder()
