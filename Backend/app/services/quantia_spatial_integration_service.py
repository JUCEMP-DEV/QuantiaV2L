from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Any

from app.quantia_spatialV1.engine import QuantiaSpatialEngine
from app.quantia_spatialV1.process_engine import QuantiaSpatialV1ProcessEngine
from app.quantia_spatialV1.reconstruction_core.level_scale_normalizer import (
    ProjectLevelScaleNormalizer,
)


class QuantiaSpatialIntegrationError(RuntimeError):
    """Error de integración QuantiaV2L -> QuantiaSpatialV1."""


class QuantiaSpatialIntegrationService:
    """
    Frontera productiva entre QuantiaV2L y QuantiaSpatialV1.

    Responsabilidades:
    - recibir bytes del documento;
    - resolver internamente el raster bootstrap;
    - ejecutar F01 -> F01.5 -> F02;
    - ejecutar reconstrucción posterior por LevelView;
    - publicar una entrega de revisión consumible por 04.

    NO:
    - recibe pdf_render_scale desde el frontend;
    - calcula un porcentaje global de éxito inventado;
    - confirma automáticamente geometría;
    - modifica QuantiaSpatialV1.
    """

    # Bootstrap técnico ya usado por el runner canónico del repositorio.
    # NO representa la escala arquitectónica final.
    PDF_BOOTSTRAP_RENDER_SCALE = 0.7935

    TARGET_GEOMETRY_PX_PER_M = 90.0

    def __init__(
        self,
        *,
        spatial_engine: QuantiaSpatialEngine | None = None,
        process_engine: QuantiaSpatialV1ProcessEngine | None = None,
        scale_normalizer: ProjectLevelScaleNormalizer | None = None,
    ) -> None:
        self.spatial_engine = spatial_engine or QuantiaSpatialEngine()
        self.process_engine = process_engine or QuantiaSpatialV1ProcessEngine()
        self.scale_normalizer = scale_normalizer or ProjectLevelScaleNormalizer()

    def analyze(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
        source_document_id: str,
        source_file_name: str,
        project_site_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not document_bytes:
            raise QuantiaSpatialIntegrationError(
                "El documento no contiene bytes para analizar."
            )

        normalized_mime = str(mime_type or "").strip().lower()
        if normalized_mime not in {
            "application/pdf",
            "image/jpeg",
            "image/png",
        }:
            raise QuantiaSpatialIntegrationError(
                "Quantia Spatial solo soporta PDF, JPG y PNG."
            )

        source_id = str(source_document_id or "").strip()
        if not source_id:
            raise QuantiaSpatialIntegrationError("source_document_id es obligatorio.")

        bootstrap_render_scale = (
            self.PDF_BOOTSTRAP_RENDER_SCALE
            if normalized_mime == "application/pdf"
            else None
        )

        engine_result = self.spatial_engine.run(
            document_bytes=document_bytes,
            media_mime_type=normalized_mime,
            source_document_id=source_id,
            render_scale=bootstrap_render_scale,
            project_site_context=project_site_context,
            enable_gemini_discovery=True,
            enable_gemini_extraction=True,
            enable_metric_raster_normalization=True,
            target_geometry_px_per_m=self.TARGET_GEOMETRY_PX_PER_M,
        )

        warnings = list(engine_result.warnings or [])

        reconstructable = [
            level
            for level in engine_result.levels
            if level.perimeter.editable_perimeter is not None
        ]

        if not engine_result.phase_01.level_views:
            return self._empty_delivery(
                source_document_id=source_id,
                source_file_name=source_file_name,
                warnings=[
                    *warnings,
                    "Spatial no produjo LevelViews utilizables.",
                ],
                status="FAILED",
            )

        if not reconstructable:
            return self._engine_only_delivery(
                engine_result=engine_result,
                source_file_name=source_file_name,
                warnings=[
                    *warnings,
                    "F02 no produjo un perímetro editable para reconstrucción.",
                ],
            )

        scale_context = self.scale_normalizer.build(
            levels=[
                (
                    item.level_view,
                    item.perimeter.editable_perimeter,
                )
                for item in reconstructable
            ]
        )

        process_results: dict[str, Any] = {}
        process_errors: dict[str, str] = {}

        for item in reconstructable:
            level_id = item.level_view.id

            try:
                process_results[level_id] = self.process_engine.run_level(
                    level_view=item.level_view,
                    perimeter=item.perimeter.editable_perimeter,
                    evidence=item.evidence.evidence,
                    scale_profile=scale_context.for_level(level_id),
                    call2_mode="AUTO",
                )
            except Exception as exc:  # noqa: BLE001
                message = f"{type(exc).__name__}: {exc}"
                process_errors[level_id] = message
                warnings.append(
                    f"{item.level_view.level_name or level_id}: "
                    f"reconstrucción posterior no completada. {message}"
                )

        return self._build_review_delivery(
            engine_result=engine_result,
            process_results=process_results,
            process_errors=process_errors,
            source_file_name=source_file_name,
            warnings=warnings,
        )

    def _build_review_delivery(
        self,
        *,
        engine_result: Any,
        process_results: dict[str, Any],
        process_errors: dict[str, str],
        source_file_name: str,
        warnings: list[str],
    ) -> dict[str, Any]:
        levels: list[dict[str, Any]] = []
        walls: list[dict[str, Any]] = []
        logical_gaps: list[dict[str, Any]] = []

        buckets = {
            "WALL": [],
            "ARCHITECTURAL_ELEMENT": [],
            "EXCLUDED_GRAPHIC": [],
            "UNRESOLVED": [],
        }

        call2_candidates: list[dict[str, Any]] = []
        call2_unresolved: list[dict[str, Any]] = []
        integrity_states: list[bool] = []
        interior_space_counts: dict[str, int] = {}

        level_by_id = {item.level_view.id: item for item in engine_result.levels}

        for level_view in engine_result.phase_01.level_views:
            levels.append(
                {
                    "id": level_view.id,
                    "key": level_view.id,
                    "name": level_view.level_name or level_view.id,
                    "confirmed": False,
                    "pageNumber": level_view.source_page_number,
                    "confidence": level_view.confidence,
                    "state": str(level_view.state),
                }
            )

        for level_id, result in process_results.items():
            item = level_by_id[level_id]
            view = item.level_view
            final_graph = result.final_wall_graph
            evidence_bundle = result.canonical.evidence_bundle

            px_per_m = float(final_graph.px_per_m)
            if not math.isfinite(px_per_m) or px_per_m <= 0:
                process_errors[level_id] = (
                    "WallGraph final no contiene px_per_m válido."
                )
                warnings.append(
                    f"{view.level_name or level_id}: "
                    "WallGraph final sin escala métrica válida."
                )
                continue

            integrity_states.append(bool(result.canonical.integrity.valid))
            interior_space_counts[level_id] = int(final_graph.interior_space_count)

            for wall in final_graph.walls:
                start = {
                    "x": float(wall.start_px[0]) / px_per_m,
                    "y": float(wall.start_px[1]) / px_per_m,
                }
                end = {
                    "x": float(wall.end_px[0]) / px_per_m,
                    "y": float(wall.end_px[1]) / px_per_m,
                }

                source_wall_ids = list(
                    evidence_bundle.final_source_mapping.get(
                        wall.id,
                        [],
                    )
                )

                walls.append(
                    {
                        **wall.model_dump(mode="json"),
                        "levelId": level_id,
                        "nivel": level_id,
                        "start": start,
                        "end": end,
                        "lengthM": (
                            math.dist(
                                wall.start_px,
                                wall.end_px,
                            )
                            / px_per_m
                        ),
                        "thicknessM": (float(wall.thickness_px) / px_per_m),
                        "heightM": None,
                        "confirmed": False,
                        "state": "REVIEW",
                        "sourceWallIds": source_wall_ids,
                        "segmentos": [
                            {
                                "geometria": {
                                    "raster": {
                                        "vertices": [
                                            {
                                                "x": float(wall.start_px[0]),
                                                "y": float(wall.start_px[1]),
                                            },
                                            {
                                                "x": float(wall.end_px[0]),
                                                "y": float(wall.end_px[1]),
                                            },
                                        ]
                                    }
                                }
                            }
                        ],
                    }
                )

                buckets["WALL"].append(wall.id)

            logical_gaps.extend(
                [
                    {
                        **gap.model_dump(mode="json"),
                        "levelViewId": level_id,
                    }
                    for gap in final_graph.logical_gaps
                ]
            )

            buckets["ARCHITECTURAL_ELEMENT"].extend(
                evidence_bundle.architectural_elements
            )
            buckets["EXCLUDED_GRAPHIC"].extend(evidence_bundle.excluded_graphics)
            buckets["UNRESOLVED"].extend(evidence_bundle.unresolved)

            if result.call2_validation is not None:
                call2_candidates.extend(
                    result.call2_validation.accepted_architectural_regions
                )
                call2_unresolved.extend(
                    result.call2_validation.accepted_unresolved_regions
                )

        first_view = (
            engine_result.phase_01.level_views[0]
            if engine_result.phase_01.level_views
            else None
        )

        plano_base = (
            self._base_layer_payload(
                level_view=first_view,
                source_file_name=source_file_name,
            )
            if first_view is not None
            else None
        )

        normalization = engine_result.raster_normalization
        normalization_state = (
            str(normalization.state) if normalization is not None else "UNRESOLVED"
        )

        quality = {
            "successPercent": None,
            "components": {
                "scale": {
                    "percent": None,
                    "status": self._scale_quality_status(normalization_state),
                    "detail": (f"Raster métrico canónico {normalization_state}."),
                },
                "perimeter": {
                    "percent": None,
                    "status": self._perimeter_quality_status(engine_result.levels),
                    "detail": "Estado consolidado de F02.",
                },
                "walls": {
                    "percent": None,
                    "status": self._wall_quality_status(
                        walls=walls,
                        integrity_states=integrity_states,
                        process_errors=process_errors,
                    ),
                    "detail": (
                        "WallGraph canónico generado para "
                        f"{len(process_results)} LevelView(s)."
                    ),
                },
                "spaces": {
                    "percent": None,
                    "status": (
                        "REVIEW"
                        if any(value > 0 for value in interior_space_counts.values())
                        else "UNRESOLVED"
                    ),
                    "detail": (
                        "Existe diagnóstico topológico de espacios, "
                        "pero el contrato de polígonos de espacio "
                        "todavía no está cerrado."
                    ),
                },
                "openings": {
                    "percent": None,
                    "status": "UNRESOLVED",
                    "detail": (
                        "El grounding productivo de puertas y ventanas "
                        "todavía no está cerrado."
                    ),
                },
                "correlation": {
                    "percent": None,
                    "status": "UNRESOLVED",
                    "detail": (
                        "SpatialCorrelationGraph / SpaceValidationGate "
                        "todavía no están cerrados."
                    ),
                },
            },
        }

        has_walls = bool(walls)
        status = "PARTIAL" if has_walls else "FAILED"
        spatial_status = "REVIEW" if has_walls else "UNRESOLVED"

        revision_payload = {
            "levels": levels,
            "wallIds": sorted(item["id"] for item in walls),
            "logicalGapIds": sorted(item["id"] for item in logical_gaps),
            "normalizationState": normalization_state,
        }
        revision = hashlib.sha256(
            json.dumps(
                revision_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        first_graph = (
            next(iter(process_results.values())).final_wall_graph
            if process_results
            else None
        )

        coordinate_system = (
            {
                "raster": "local_px_xy_down",
                "metric": "local_m_xy_down",
                "pxPerM": float(first_graph.px_per_m),
            }
            if first_graph is not None
            else None
        )

        source_document_id = (
            first_view.source_document_id
            if first_view is not None
            else engine_result.phase_01.source_document_id
        )

        source_page_number = (
            first_view.source_page_number if first_view is not None else 1
        )

        source_bbox = (
            first_view.source_bbox_px.model_dump(mode="json")
            if first_view is not None
            else None
        )

        return {
            "schemaVersion": "SPATIAL_INTERFACE04_REVIEW_V1",
            "revision": revision,
            "execution": {
                "status": status,
                "spatialStatus": spatial_status,
                "progressPercent": 100,
                "phaseLabel": "Reconstrucción Spatial finalizada",
                "warnings": self._dedupe(warnings),
                "errors": list(process_errors.values()),
            },
            "quality": quality,
            "coordinateSystem": coordinate_system,
            "planoBase": plano_base,
            "source": {
                "documentId": source_document_id,
                "fileName": source_file_name,
                "pageNumber": source_page_number,
                "bboxPx": source_bbox,
            },
            "niveles": levels,
            "muros": walls,
            "puertas": [],
            "ventanas": [],
            "espacios": [],
            "ejes": [],
            "cotas": [],
            "escaleras": [],
            "buckets": buckets,
            "call2Candidates": call2_candidates,
            "call2Unresolved": call2_unresolved,
            "logicalGaps": logical_gaps,
            "interiorSpaceCount": sum(interior_space_counts.values()),
            "interiorSpaceCountByLevel": interior_space_counts,
            "readiness": {
                "wallReview": has_walls,
                "workflowContinuation": False,
                "quantification": False,
                "missing": [
                    "validated openings with host/offset/width",
                    "space polygons and names",
                    "grounded axes and dimensions",
                    "wall and opening heights",
                    "global spatial correlation validation",
                ],
            },
            "metadata": {
                "sourceMode": "plan",
                "sourceDocumentId": source_document_id,
                "sourceFileName": source_file_name,
                "sourcePageNumber": source_page_number,
                "bootstrapRenderScale": (
                    self.PDF_BOOTSTRAP_RENDER_SCALE
                    if engine_result.phase_01.media_mime_type == "application/pdf"
                    else None
                ),
                "metricRasterState": normalization_state,
                "metricRasterVersion": (
                    normalization.version if normalization is not None else None
                ),
                "targetGeometryPxPerM": (
                    normalization.target_geometry_px_per_m
                    if normalization is not None
                    else None
                ),
            },
        }

    def _engine_only_delivery(
        self,
        *,
        engine_result: Any,
        source_file_name: str,
        warnings: list[str],
    ) -> dict[str, Any]:
        first_view = (
            engine_result.phase_01.level_views[0]
            if engine_result.phase_01.level_views
            else None
        )

        levels = [
            {
                "id": view.id,
                "key": view.id,
                "name": view.level_name or view.id,
                "confirmed": False,
                "pageNumber": view.source_page_number,
                "confidence": view.confidence,
                "state": str(view.state),
            }
            for view in engine_result.phase_01.level_views
        ]

        normalization = engine_result.raster_normalization
        normalization_state = (
            str(normalization.state) if normalization is not None else "UNRESOLVED"
        )

        return {
            "schemaVersion": "SPATIAL_INTERFACE04_REVIEW_V1",
            "revision": hashlib.sha256(
                json.dumps(
                    {
                        "levels": [item["id"] for item in levels],
                        "state": normalization_state,
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
            "execution": {
                "status": "PARTIAL",
                "spatialStatus": "UNRESOLVED",
                "progressPercent": 100,
                "phaseLabel": "F01/F02 finalizadas sin WallGraph publicable",
                "warnings": self._dedupe(warnings),
                "errors": [],
            },
            "quality": {
                "successPercent": None,
                "components": {
                    "scale": {
                        "percent": None,
                        "status": self._scale_quality_status(normalization_state),
                        "detail": (
                            f"Estado del raster métrico: {normalization_state}."
                        ),
                    },
                    "perimeter": {
                        "percent": None,
                        "status": self._perimeter_quality_status(engine_result.levels),
                        "detail": "Estado consolidado de F02.",
                    },
                    "walls": {
                        "percent": None,
                        "status": "UNRESOLVED",
                        "detail": "No existe WallGraph final publicable.",
                    },
                    "spaces": {
                        "percent": None,
                        "status": "UNRESOLVED",
                        "detail": "Sin polígonos de espacio publicados.",
                    },
                    "openings": {
                        "percent": None,
                        "status": "UNRESOLVED",
                        "detail": "Sin openings publicados.",
                    },
                    "correlation": {
                        "percent": None,
                        "status": "UNRESOLVED",
                        "detail": "Correlación global aún no ejecutada.",
                    },
                },
            },
            "coordinateSystem": None,
            "planoBase": (
                self._base_layer_payload(
                    level_view=first_view,
                    source_file_name=source_file_name,
                )
                if first_view is not None
                else None
            ),
            "source": {
                "documentId": engine_result.phase_01.source_document_id,
                "fileName": source_file_name,
                "pageNumber": (
                    first_view.source_page_number if first_view is not None else 1
                ),
                "bboxPx": (
                    first_view.source_bbox_px.model_dump(mode="json")
                    if first_view is not None
                    else None
                ),
            },
            "niveles": levels,
            "muros": [],
            "puertas": [],
            "ventanas": [],
            "espacios": [],
            "ejes": [],
            "cotas": [],
            "escaleras": [],
            "buckets": {
                "WALL": [],
                "ARCHITECTURAL_ELEMENT": [],
                "EXCLUDED_GRAPHIC": [],
                "UNRESOLVED": [],
            },
            "call2Candidates": [],
            "call2Unresolved": [],
            "logicalGaps": [],
            "interiorSpaceCount": 0,
            "readiness": {
                "wallReview": False,
                "workflowContinuation": False,
                "quantification": False,
                "missing": [
                    "WallGraph canónico",
                    "space polygons and names",
                    "validated openings",
                    "grounded axes and dimensions",
                ],
            },
            "metadata": {
                "sourceMode": "plan",
                "sourceDocumentId": engine_result.phase_01.source_document_id,
                "sourceFileName": source_file_name,
                "bootstrapRenderScale": (
                    self.PDF_BOOTSTRAP_RENDER_SCALE
                    if engine_result.phase_01.media_mime_type == "application/pdf"
                    else None
                ),
                "metricRasterState": normalization_state,
            },
        }

    def _empty_delivery(
        self,
        *,
        source_document_id: str,
        source_file_name: str,
        warnings: list[str],
        status: str,
    ) -> dict[str, Any]:
        revision = hashlib.sha256(
            f"{source_document_id}:{status}".encode("utf-8")
        ).hexdigest()

        return {
            "schemaVersion": "SPATIAL_INTERFACE04_REVIEW_V1",
            "revision": revision,
            "execution": {
                "status": status,
                "spatialStatus": "UNRESOLVED",
                "progressPercent": 100,
                "phaseLabel": "Spatial finalizó sin geometría publicable",
                "warnings": self._dedupe(warnings),
                "errors": [],
            },
            "quality": {
                "successPercent": None,
                "components": {},
            },
            "coordinateSystem": None,
            "planoBase": None,
            "source": {
                "documentId": source_document_id,
                "fileName": source_file_name,
                "pageNumber": 1,
                "bboxPx": None,
            },
            "niveles": [],
            "muros": [],
            "puertas": [],
            "ventanas": [],
            "espacios": [],
            "ejes": [],
            "cotas": [],
            "escaleras": [],
            "buckets": {
                "WALL": [],
                "ARCHITECTURAL_ELEMENT": [],
                "EXCLUDED_GRAPHIC": [],
                "UNRESOLVED": [],
            },
            "call2Candidates": [],
            "call2Unresolved": [],
            "logicalGaps": [],
            "interiorSpaceCount": 0,
            "readiness": {
                "wallReview": False,
                "workflowContinuation": False,
                "quantification": False,
                "missing": [
                    "Spatial no produjo geometría publicable.",
                ],
            },
            "metadata": {
                "sourceMode": "plan",
                "sourceDocumentId": source_document_id,
                "sourceFileName": source_file_name,
            },
        }

    @staticmethod
    def _base_layer_payload(
        *,
        level_view: Any,
        source_file_name: str,
    ) -> dict[str, Any]:
        mime = str(level_view.raster_mime_type or "image/png")
        encoded = base64.b64encode(level_view.raster_bytes).decode("ascii")

        return {
            "id": f"{level_view.id}__BASE",
            "nombre": source_file_name,
            "mimeType": mime,
            "pagina": level_view.source_page_number,
            "anchoPx": level_view.raster_width_px,
            "altoPx": level_view.raster_height_px,
            "referencia": f"data:{mime};base64,{encoded}",
            "visible": True,
            "bloqueado": True,
            "ocultable": True,
            "bloqueable": True,
            "sha256": hashlib.sha256(level_view.raster_bytes).hexdigest(),
        }

    @staticmethod
    def _scale_quality_status(state: str) -> str:
        normalized = str(state or "").upper()

        if normalized == "NORMALIZED":
            return "VALID"

        if normalized in {
            "PARTIAL",
            "REVIEW",
        }:
            return "REVIEW"

        return "UNRESOLVED"

    @staticmethod
    def _perimeter_quality_status(
        levels: list[Any],
    ) -> str:
        if not levels:
            return "UNRESOLVED"

        states = {str(item.perimeter.state).upper() for item in levels}

        if states == {"RESOLVED"}:
            return "VALID"

        if "RESOLVED" in states:
            return "REVIEW"

        return "UNRESOLVED"

    @staticmethod
    def _wall_quality_status(
        *,
        walls: list[dict[str, Any]],
        integrity_states: list[bool],
        process_errors: dict[str, str],
    ) -> str:
        if not walls:
            return "UNRESOLVED"

        if process_errors:
            return "REVIEW"

        if integrity_states and all(integrity_states):
            return "VALID"

        return "REVIEW"

    @staticmethod
    def _dedupe(
        values: list[str],
    ) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue

            seen.add(text)
            result.append(text)

        return result
