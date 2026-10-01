from __future__ import annotations

import unittest

from app.services.architectural_dimension_grounding_service import (
    ArchitecturalDimensionGroundingService,
    AxisAnchorCandidate,
)
from app.services.plan_geometry_reconciler import (
    BoundaryCandidate,
    DirectionalGeometryCandidates,
    GeometryTextEvidence,
    MetricSpatialCandidate,
    SpaceGeometryReconciliation,
)
from app.services.space_pdf_coordinate_mapper import RasterBBox


def axis(
    axis_id: str,
    label: str,
    coordinate: float,
    label_y: float,
) -> AxisAnchorCandidate:
    return AxisAnchorCandidate(
        id=axis_id,
        label=label,
        normalized_label=label,
        orientation="vertical",
        coordinate_px=coordinate,
        evidence_bboxes=[[coordinate - 4, label_y, coordinate + 4, label_y + 12]],
    )


def horizontal_axis(
    axis_id: str,
    label: str,
    coordinate: float,
) -> AxisAnchorCandidate:
    return AxisAnchorCandidate(
        id=axis_id,
        label=label,
        normalized_label=label,
        orientation="horizontal",
        coordinate_px=coordinate,
        evidence_bboxes=[[344, coordinate - 6, 353, coordinate + 6]],
    )


def horizontal_boundary(
    side: str,
    coordinate: float,
) -> BoundaryCandidate:
    return BoundaryCandidate(
        side=side,
        orientation="horizontal",
        x1=500,
        y1=coordinate,
        x2=835,
        y2=coordinate,
        length_px=335,
        bbox_coverage_ratio=1,
        distance_to_bbox_edge_px=0,
        crosses_space_center=True,
        opencv_segment_id=f"{side}_{coordinate}",
    )


def dimension(text: str, value: float, x: float, y: float) -> GeometryTextEvidence:
    return GeometryTextEvidence(
        kind="dimension_candidate",
        text=text,
        page=1,
        x=x,
        y=y,
        bbox=[x - 7, y - 4, x + 7, y + 4],
        numeric_value=value,
        numeric_unit=None,
        comparison_value=value,
        source="pymupdf_vector_text",
        confidence=1,
    )


class ArchitecturalDimensionGroundingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArchitecturalDimensionGroundingService()
        self.space = SpaceGeometryReconciliation(
            nivel="Planta Alta",
            id_propuesto="pa_recamara_1",
            nombre="Recámara 1",
            localization_bbox=RasterBBox(
                x_min=500,
                y_min=840,
                x_max=835,
                y_max=1160,
            ),
            boundaries=DirectionalGeometryCandidates(),
            metric_associations=[
                MetricSpatialCandidate(
                    element_type="espacio",
                    element_id="pa_recamara_1",
                    field="largo_m",
                    value=4.1,
                    metric_kind="linear",
                    evidence_source="gemini_vision",
                    matched_text="4.10",
                    matched_text_source="pymupdf_vector_text",
                    matched_value=4.1,
                    matched_bbox=[660, 740, 674, 748],
                    distance_to_space_bbox_px=100,
                    inside_space_bbox=False,
                )
            ],
        )

    def test_selects_the_nearest_level_axis_chain(self) -> None:
        axes = [
            axis("PB_1", "1", 500, 110),
            axis("PB_2", "2", 700, 110),
            axis("PA_7", "7", 500, 690),
            axis("PA_8", "8", 835, 690),
        ]

        selected = self.service._axes_for_space_chain(
            axes=axes,
            space=self.space,
            orientation="vertical",
            tolerance=3.5,
        )

        self.assertEqual([item.id for item in selected], ["PA_7", "PA_8"])

    def test_uses_segment_row_and_rejects_overall_dimension_row(self) -> None:
        axes = [
            axis("PA_7", "7", 500, 690),
            axis("PA_8", "8", 835, 690),
            axis("PA_9", "9", 1165, 690),
        ]
        evidence = [
            dimension("4.10", 4.1, 667, 744),
            dimension("4.10", 4.1, 998, 744),
            dimension("15.00", 15, 700, 724),
        ]

        result = self.service._resolve_corroborated_axis_span(
            space=self.space,
            local_axes=axes,
            orientation="vertical",
            dimension_axis="x",
            dimension_evidence=evidence,
            tolerance=3.5,
            span_counter_start=0,
        )

        self.assertIsNotNone(result)
        spans, resolved, reason = result
        self.assertEqual(reason, "")
        self.assertEqual(resolved.value_m, 4.1)
        self.assertEqual(resolved.start_axis_label, "7")
        self.assertEqual(resolved.end_axis_label, "8")
        self.assertEqual(spans[0].distinct_values_m, [4.1])

    def test_multispan_room_uses_full_axis_chain(self) -> None:
        self.space.boundaries = DirectionalGeometryCandidates(
            top=[horizontal_boundary("top", 864)],
            bottom=[horizontal_boundary("bottom", 1163)],
        )
        self.space.metric_associations.append(
            MetricSpatialCandidate(
                element_type="espacio",
                element_id="pa_recamara_1",
                field="ancho_m",
                value=2.6,
                metric_kind="linear",
                evidence_source="gemini_vision",
                matched_text="2.60",
                matched_text_source="pymupdf_vector_text",
                matched_value=2.6,
                matched_bbox=[389, 1051, 396, 1065],
                distance_to_space_bbox_px=109,
                inside_space_bbox=False,
            )
        )
        axes = [
            horizontal_axis("PA_J", "J", 864),
            horizontal_axis("PA_C", "C", 955),
            horizontal_axis("PA_D", "D", 1163),
        ]
        evidence = [
            dimension("1.18", 1.18, 393, 906),
            dimension("2.60", 2.6, 393, 1058),
        ]

        spans, resolved, reason = self.service._resolve_space_axis_dimension(
            space=self.space,
            orientation="horizontal",
            dimension_axis="y",
            axis_anchors=axes,
            dimension_evidence=evidence,
            segment_lookup={},
            tolerance=3.5,
            span_counter_start=0,
        )

        self.assertEqual(reason, "")
        self.assertIsNotNone(resolved)
        self.assertEqual([span.value_m for span in spans], [1.18, 2.6])
        self.assertAlmostEqual(resolved.value_m, 3.78)
        self.assertEqual(resolved.start_axis_label, "J")
        self.assertEqual(resolved.end_axis_label, "D")

    def test_prefers_boundary_closest_to_space_edge(self) -> None:
        farther = horizontal_boundary("bottom", 1056)
        farther.distance_to_bbox_edge_px = 99
        closer = horizontal_boundary("bottom", 1149)
        closer.distance_to_bbox_edge_px = 6
        self.space.boundaries = DirectionalGeometryCandidates(
            top=[horizontal_boundary("top", 851)],
            bottom=[farther, closer],
        )

        top, bottom = self.service._space_boundary_pair(
            space=self.space,
            orientation="horizontal",
        )

        self.assertEqual(top.y1, 851)
        self.assertEqual(bottom.y1, 1149)


if __name__ == "__main__":
    unittest.main()
