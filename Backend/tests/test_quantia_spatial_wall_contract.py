from __future__ import annotations

import unittest

from app.schemas.quantia_spatial_contract import SpatialBaseLayer
from app.services.architectural_wall_abstraction_service import (
    ArchitecturalWallAbstractionResult,
    ArchitecturalWallCenterline,
    ArchitecturalWallRun,
)
from app.services.quantia_spatial_contract_builder import (
    QuantiaSpatialContractBuilder,
)


class QuantiaSpatialWallContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.wall_abstraction = ArchitecturalWallAbstractionResult(
            page=1,
            width_px=1000,
            height_px=800,
            wall_runs=[
                ArchitecturalWallRun(
                    id="WALL_RUN_1",
                    orientation="horizontal",
                    x1=10,
                    y1=100,
                    x2=300,
                    y2=100,
                    length_px=290,
                    source_segment_ids=["CV_V_ENDPOINT", "CV_H_FACE_1"],
                    face_segment_ids=["CV_H_FACE_1"],
                    endpoint_support_ids=["CV_V_ENDPOINT"],
                    space_ids=["SOURCE_SPACE_1"],
                    levels=["NIVEL_1"],
                    sources=["opencv", "gemini"],
                ),
                ArchitecturalWallRun(
                    id="WALL_RUN_2",
                    orientation="horizontal",
                    x1=10,
                    y1=120,
                    x2=300,
                    y2=120,
                    length_px=290,
                    face_segment_ids=["CV_H_FACE_2"],
                    endpoint_support_ids=["CV_V_ENDPOINT_2"],
                    space_ids=["SOURCE_SPACE_2"],
                    levels=["NIVEL_1"],
                    sources=["opencv"],
                ),
                ArchitecturalWallRun(
                    id="WALL_RUN_3",
                    orientation="vertical",
                    x1=400,
                    y1=50,
                    x2=400,
                    y2=350,
                    length_px=300,
                    source_segment_ids=["CV_H_ENDPOINT", "CV_V_FACE_3"],
                    face_segment_ids=["CV_V_FACE_3"],
                    endpoint_support_ids=["CV_H_ENDPOINT"],
                    space_ids=["SOURCE_SPACE_3"],
                    levels=["NIVEL_1"],
                    sources=["opencv"],
                ),
            ],
            centerlines=[
                ArchitecturalWallCenterline(
                    id="CENTERLINE_1",
                    orientation="horizontal",
                    x1=10,
                    y1=110,
                    x2=300,
                    y2=110,
                    length_px=290,
                    thickness_px=20,
                    overlap_px=290,
                    overlap_ratio=1,
                    pairing_distance_limit_px=40,
                    wall_run_ids=["WALL_RUN_1", "WALL_RUN_2"],
                    face_segment_ids=["CV_H_FACE_1", "CV_H_FACE_2"],
                    space_ids=["SOURCE_SPACE_1", "SOURCE_SPACE_2"],
                    levels=["NIVEL_1"],
                )
            ],
        )
        self.base_layer = SpatialBaseLayer(
            id="BASE_1",
            nombre="plano.png",
            mimeType="image/png",
            pagina=1,
            anchoPx=1000,
            altoPx=800,
            referencia="fixture://plano.png",
            visible=True,
            bloqueado=True,
            ocultable=True,
            bloqueable=True,
        )

    def test_centerline_replaces_only_its_supporting_wall_runs(self) -> None:
        traces = QuantiaSpatialContractBuilder._contract_wall_traces(
            self.wall_abstraction
        )

        self.assertEqual(
            [trace.id for trace in traces],
            ["CENTERLINE_1", "WALL_RUN_3"],
        )
        self.assertEqual(
            traces[0].source_segment_ids,
            ["CV_H_FACE_1", "CV_H_FACE_2"],
        )
        self.assertEqual(
            traces[0].endpoint_support_ids,
            ["CV_V_ENDPOINT", "CV_V_ENDPOINT_2"],
        )

    def test_contract_uses_architectural_ids_and_observed_pixel_thickness(self) -> None:
        walls = QuantiaSpatialContractBuilder()._build_walls(
            wall_abstraction=self.wall_abstraction,
            base_layer=self.base_layer,
            source_to_contract_space={
                "SOURCE_SPACE_1": "SPACE_1",
                "SOURCE_SPACE_2": "SPACE_2",
                "SOURCE_SPACE_3": "SPACE_3",
            },
        )

        self.assertEqual([wall.id for wall in walls], ["CENTERLINE_1", "WALL_RUN_3"])
        self.assertEqual(
            [wall.segmentos[0].id for wall in walls],
            ["CENTERLINE_1_SEGMENT_1", "WALL_RUN_3_SEGMENT_1"],
        )
        self.assertEqual(walls[0].espesorObservadoPx, 20)
        self.assertEqual(walls[0].espesorEstado, "PENDIENTE")
        self.assertIsNone(walls[0].espesorM)
        self.assertEqual(walls[1].orientacion, "vertical")
        self.assertEqual(
            [point.x for point in walls[1].segmentos[0].geometria.raster.vertices],
            [400, 400],
        )


if __name__ == "__main__":
    unittest.main()
