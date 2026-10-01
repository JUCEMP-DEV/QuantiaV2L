from __future__ import annotations

import unittest

from shapely.geometry import Polygon

from app.services.plan_geometry_reconciler import (
    DirectionalGeometryCandidates,
    PlanGeometryReconciliationResult,
    SpaceGeometryReconciliation,
)
from app.services.shapely_plan_geometry_service import (
    ArchitecturalFaceCandidate,
    ShapelyPlanGeometryService,
)
from app.services.space_geometry_resolver import SpaceGeometryResolver
from app.services.space_pdf_coordinate_mapper import RasterBBox


class SpaceSemanticZoneTests(unittest.TestCase):
    def test_splits_a_verified_compound_open_area_name(self) -> None:
        self.assertEqual(
            SpaceGeometryResolver._compound_zone_names(
                "Estancia Comedor Cocina"
            ),
            ["Estancia", "Comedor", "Cocina"],
        )

    def test_preserves_a_single_space_name(self) -> None:
        self.assertEqual(
            SpaceGeometryResolver._compound_zone_names("Recámara 1"),
            ["Recámara 1"],
        )

    def test_builds_an_inferred_semantic_fallback_without_a_face(self) -> None:
        source_space = SpaceGeometryReconciliation(
            nivel="Planta Alta",
            id_propuesto="pa_recamara_1",
            nombre="Recámara 1",
            localization_bbox=RasterBBox(100, 200, 400, 500),
            boundaries=DirectionalGeometryCandidates(),
        )

        fallback, zones = SpaceGeometryResolver()._semantic_fallback_space(
            source_space=source_space,
            dimensions=[],
        )

        self.assertEqual(fallback.face_id, "SEMANTIC_BBOX_pa_recamara_1")
        self.assertEqual(fallback.semantic_mode, "ESPACIO_UNICO")
        self.assertEqual(fallback.state, "INFERIDO")
        self.assertEqual(fallback.area_px2, 90000)
        self.assertEqual(zones, [])

    def test_rejects_a_tiny_furniture_face_as_a_room(self) -> None:
        source_space = SpaceGeometryReconciliation(
            nivel="Planta Baja",
            id_propuesto="pb_cochera",
            nombre="Cochera",
            localization_bbox=RasterBBox(0, 0, 500, 400),
            boundaries=DirectionalGeometryCandidates(),
        )
        reconciliation = PlanGeometryReconciliationResult(
            page=1,
            width_px=1000,
            height_px=800,
            spaces=[source_space],
        )
        polygon = Polygon([(10, 10), (30, 10), (30, 30), (10, 30)])
        face = ArchitecturalFaceCandidate(
            id="FACE_DETAIL",
            vertices=[(10, 10), (30, 10), (30, 30), (10, 30)],
            area_px2=400,
            perimeter_px=80,
            centroid_x=20,
            centroid_y=20,
            bbox=[10, 10, 30, 30],
            shapely_valid=True,
            state="DETECTADO",
            detected_in_base_graph=True,
            uses_virtual_closure=False,
        )

        associations = ShapelyPlanGeometryService()._associate_semantics(
            faces=[face],
            geometries={face.id: polygon},
            reconciliation=reconciliation,
        )

        self.assertEqual(associations[face.id], [])


if __name__ == "__main__":
    unittest.main()
