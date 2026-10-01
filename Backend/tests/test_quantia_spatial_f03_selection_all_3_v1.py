from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.quantia_spatial.reconstruction_core import ProposalCReconstructionPipeline
from app.quantia_spatial.tests.quantia_case_loader import CASE_LOADERS, LoadedCase
from app.quantia_spatial.tests.test_quantia_spatial_context_classification_v6_2_standardized import (
    _run_level_probe,
)


PROBE_VERSION = "F03_SELECTION_ALL_3_V1"
BASELINE = "CANONICAL_METRIC_RASTER_V2_3_VALIDATED + CONTEXT_CLASSIFICATION_V6_2"
CASE_IDS = ("casa_viri", "miguel_h", "miguel_v")
TARGET_PX_PER_M = 90.0
TARGET_RELATIVE_TOLERANCE = 0.05

TESTS_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = TESTS_DIR / "output" / "f03_selection_v1"


def _run_case(case: LoadedCase) -> None:
    output_dir = OUTPUT_ROOT / case.case_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = ProposalCReconstructionPipeline()

    scale_inputs = []
    for loaded in case.levels:
        level_result = loaded.level_result
        perimeter = level_result.perimeter.editable_perimeter
        assert perimeter is not None, f"{loaded.level_name}: F02 no publicó perímetro."
        scale_inputs.append((level_result.level_view, perimeter))

    project_scale = pipeline.build_project_scale_context(levels=scale_inputs)
    assert project_scale.state == "RESOLVED", (
        f"{case.case_id}: la base V2.3 dejó de estar estable; "
        f"project_scale={project_scale.state}"
    )

    report = {
        "probe_version": PROBE_VERSION,
        "baseline": BASELINE,
        "case_id": case.case_id,
        "case": case.case_name,
        "gemini_calls_added": 0,
        "target_px_per_m": TARGET_PX_PER_M,
        "target_relative_tolerance": TARGET_RELATIVE_TOLERANCE,
        "project_scale": project_scale.model_dump(mode="json"),
        "levels": [],
    }

    failures: list[str] = []

    for loaded in case.levels:
        level_result = loaded.level_result
        scale_profile = project_scale.for_level(level_result.level_view.id)

        if scale_profile.state != "RESOLVED" or scale_profile.local_m_per_px is None:
            failures.append(f"{loaded.level_name}:SCALE_{scale_profile.state}")
            continue

        px_per_m = 1.0 / scale_profile.local_m_per_px
        relative_error = abs(px_per_m - TARGET_PX_PER_M) / TARGET_PX_PER_M
        if relative_error > TARGET_RELATIVE_TOLERANCE:
            failures.append(
                f"{loaded.level_name}:PX_PER_M_OUT_OF_TOLERANCE:{px_per_m:.6f}"
            )

        level_report = _run_level_probe(
            pipeline=pipeline,
            loaded=loaded,
            output_dir=output_dir,
            case_id=case.case_id,
            scale_profile=scale_profile,
        )
        level_report["canonical_metric_guard"] = {
            "state": scale_profile.state,
            "px_per_m": px_per_m,
            "relative_error_to_90": relative_error,
            "within_tolerance": relative_error <= TARGET_RELATIVE_TOLERANCE,
        }
        report["levels"].append(level_report)

        print("\n" + "=" * 104)
        print(f"F03 SELECTION ALL 3 V1 — {case.case_name} — {loaded.level_name}")
        print({
            "px_m": round(px_per_m, 3),
            "discovered": level_report["discovered_count"],
            "quarantine": level_report["quarantined_count"],
            "review": level_report["review_count"],
            "solver_candidates": level_report["solver_candidate_count"],
            "selected": level_report["selected_count"],
            "categories": level_report["category_counts"],
            "selected_context": level_report["selected_context_type_counts"],
            "surface_selected": level_report["surface_context_selected_count"],
            "visual": level_report["visual_file"],
        })

    report["failures"] = failures
    report["passed"] = not failures

    json_path = output_dir / f"{case.case_id}__f03_selection_all_3_v1.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    pngs = sorted(output_dir.glob("*.png"))
    assert len(pngs) == len(case.levels), (
        f"{case.case_id}: debe producir exactamente 1 PNG por LevelView; "
        f"levels={len(case.levels)} pngs={len(pngs)}"
    )

    print(f"\nJSON: {json_path}")
    print(f"Visuales: {len(pngs)} = 1 por LevelView")

    assert not failures, (
        f"{case.case_id}: la base métrica V2.3 dejó de estar estable durante "
        f"la prueba F03. failures={json.dumps(failures, ensure_ascii=False)}"
    )


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_f03_selection_all_3_v1(case_id: str) -> None:
    # Los tres casos recorren exactamente el mismo procedimiento. Solo cambia
    # la entrada resuelta por CASE_LOADERS; Miguel V conserva sus PDFs por planta.
    _run_case(CASE_LOADERS[case_id]())


if __name__ == "__main__":
    for _case_id in CASE_IDS:
        _run_case(CASE_LOADERS[_case_id]())
