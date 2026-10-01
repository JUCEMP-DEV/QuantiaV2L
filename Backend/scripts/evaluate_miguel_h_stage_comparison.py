from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT = Path("tests/output/miguel_h/miguel_h_contract_03_2_to_04.json")
DEFAULT_OUTPUT = Path("tests/output/miguel_h/miguel_h_stage_comparison.json")
TOL = 1e-6

BASELINE = {
    "levels": ["Planta Baja", "Planta Alta"],
    "axes": [
        # PB
        "1", "2", "3", "4", "5", "6", "A", "J", "C", "D",
        # PA
        "1", "7", "8", "9", "10", "11", "6", "A", "J", "C", "D",
    ],
    "dimensions": [
        # level, start, end, value_m
        ("Planta Baja", "1", "2", 1.85),
        ("Planta Baja", "2", "3", 0.85),
        ("Planta Baja", "3", "4", 2.00),
        ("Planta Baja", "4", "5", 5.25),
        ("Planta Baja", "5", "6", 5.05),
        ("Planta Baja", "A", "J", 1.55),
        ("Planta Baja", "J", "C", 0.85),
        ("Planta Baja", "C", "D", 2.60),
        ("Planta Alta", "1", "7", 1.15),
        ("Planta Alta", "7", "8", 4.10),
        ("Planta Alta", "8", "9", 4.10),
        ("Planta Alta", "9", "10", 2.00),
        ("Planta Alta", "10", "11", 1.10),
        ("Planta Alta", "11", "6", 2.55),
        ("Planta Alta", "A", "J", 1.22),
        ("Planta Alta", "J", "C", 1.18),
        ("Planta Alta", "C", "D", 2.60),
    ],
    "spaces": [
        "cochera",
        "medio_bano",
        "patio",
        "area_comun",
        "recamara_1",
        "recamara_2",
        "recinto_no_identificado",
        "circulacion",
    ],
    "semantic_zones": ["estancia", "comedor", "cocina"],
    "stairs": 3,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def norm_level(value: Any) -> str:
    text = norm(value)
    if text in {"pb", "planta baja"}:
        return "planta baja"
    if text in {"pa", "planta alta"}:
        return "planta alta"
    return text


def num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else None
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def same_num(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= TOL


def canonical_space_name(value: Any) -> str | None:
    text = norm(value)
    if not text:
        return None
    if "cochera" in text:
        return "cochera"
    if "medio bano" in text or ("bano" in text and "medio" in text):
        return "medio_bano"
    if "patio" in text or "jardin posterior" in text or "jardin interior" in text:
        return "patio"
    if "area comun" in text or all(token in text for token in ("estancia", "comedor", "cocina")):
        return "area_comun"
    if "recamara 1" in text:
        return "recamara_1"
    if "recamara 2" in text:
        return "recamara_2"
    if "sin funcion" in text or "no identific" in text:
        return "recinto_no_identificado"
    if "distribucion" in text or "circulacion" in text or "pasillo" in text:
        return "circulacion"
    return None


def multiset_match_numeric(expected: list[float], observed: list[float]) -> int:
    used = [False] * len(observed)
    matched = 0
    for exp in expected:
        for i, obs in enumerate(observed):
            if not used[i] and same_num(exp, obs):
                used[i] = True
                matched += 1
                break
    return matched


def evaluate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    # Levels
    expected_levels = Counter(norm_level(x) for x in BASELINE["levels"])
    observed_levels = Counter(
        norm_level(x.get("nombre")) for x in contract.get("niveles", [])
    )
    level_match = sum((expected_levels & observed_levels).values())

    # Axes: contract currently has no per-axis level, so use multiset of labels.
    expected_axes = Counter(str(x) for x in BASELINE["axes"])
    observed_axes = Counter(
        str(x.get("etiqueta"))
        for x in contract.get("ejes", [])
        if x.get("etiqueta") is not None
    )
    axis_match = sum((expected_axes & observed_axes).values())
    axis_missing = list((expected_axes - observed_axes).elements())
    axis_extra = list((observed_axes - expected_axes).elements())

    # Raw dimension value detection.
    raw_values: list[float] = []
    grounded = []
    for item in contract.get("cotas", []):
        item_id = str(item.get("id") or "")
        if item_id.startswith("COTA_RAW_"):
            value = num(item.get("valorOriginal"))
            if value is not None:
                raw_values.append(value)
        else:
            grounded.append(item)

    expected_dim_values = [float(x[3]) for x in BASELINE["dimensions"]]
    raw_dim_match = multiset_match_numeric(expected_dim_values, raw_values)

    # Exact grounded dimension association: level + axis pair + value.
    expected_dims = [
        (norm_level(level), str(start), str(end), float(value))
        for level, start, end, value in BASELINE["dimensions"]
    ]
    used_grounded = [False] * len(grounded)
    grounded_match = 0
    for exp_level, exp_start, exp_end, exp_value in expected_dims:
        for i, item in enumerate(grounded):
            if used_grounded[i]:
                continue
            value = num(item.get("valorM"))
            if value is None:
                continue
            level = norm_level(item.get("nivel"))
            start = str(item.get("ejeInicioEtiqueta") or "")
            end = str(item.get("ejeFinEtiqueta") or "")
            pair_ok = (start == exp_start and end == exp_end) or (start == exp_end and end == exp_start)
            if level == exp_level and pair_ok and same_num(value, exp_value):
                used_grounded[i] = True
                grounded_match += 1
                break

    wrong_grounded = 0
    for i, item in enumerate(grounded):
        value = num(item.get("valorM"))
        if value is not None and not used_grounded[i]:
            wrong_grounded += 1

    # Semantic spaces.
    observed_space_classes = [
        canonical_space_name(x.get("nombre"))
        for x in contract.get("espacios", [])
    ]
    observed_space_classes = [x for x in observed_space_classes if x]
    expected_space_counter = Counter(BASELINE["spaces"])
    observed_space_counter = Counter(observed_space_classes)
    space_match = sum((expected_space_counter & observed_space_counter).values())
    semantic_overflow = sum(
        max(0, count - expected_space_counter.get(key, 0))
        for key, count in observed_space_counter.items()
    )

    # Target semantic zones.
    zone_texts = [norm(x.get("nombre")) + " " + norm(x.get("tipo")) for x in contract.get("zonasSemanticas", [])]
    zone_match = sum(
        1 for target in BASELINE["semantic_zones"]
        if any(target in text for text in zone_texts)
    )

    stairs = len(contract.get("escaleras", []))
    stairs_match = min(stairs, BASELINE["stairs"])

    expected_units = (
        len(BASELINE["levels"])
        + len(BASELINE["axes"])
        + len(BASELINE["dimensions"])
        + len(BASELINE["spaces"])
        + len(BASELINE["semantic_zones"])
        + BASELINE["stairs"]
    )
    auto_ready = level_match + axis_match + grounded_match + space_match + zone_match + stairs_match
    review_units = expected_units - auto_ready

    return {
        "levels": {"matched": level_match, "expected": len(BASELINE["levels"])},
        "axes": {
            "matched": axis_match,
            "expected": len(BASELINE["axes"]),
            "missing": axis_missing,
            "extra": axis_extra,
        },
        "dimensions": {
            "raw_values_matched": raw_dim_match,
            "expected": len(BASELINE["dimensions"]),
            "grounded_exact": grounded_match,
            "wrong_auto_grounded": wrong_grounded,
        },
        "spaces": {
            "matched_unique_baseline": space_match,
            "expected": len(BASELINE["spaces"]),
            "contract_instances": len(contract.get("espacios", [])),
            "semantic_overflow_instances": semantic_overflow,
            "observed_classes": dict(observed_space_counter),
        },
        "semantic_zones": {"matched": zone_match, "expected": len(BASELINE["semantic_zones"])},
        "stairs": {"matched": stairs_match, "expected": BASELINE["stairs"], "observed": stairs},
        "manual_intervention": {
            "auto_ready_units": auto_ready,
            "expected_units": expected_units,
            "review_or_correction_units": review_units,
            "auto_ready_rate": auto_ready / expected_units,
            "review_or_correction_rate": review_units / expected_units,
            "note": "Las cotas COTA_RAW no cuentan como auto-ready hasta quedar grounded contra nivel+ejes.",
        },
    }


def print_report(metrics: dict[str, Any]) -> None:
    pct = lambda n, d: 0.0 if not d else 100.0 * n / d
    print("==============================================")
    print(" QUANTIA V2 — MIGUEL H STAGE COMPARISON")
    print("==============================================")
    print(f"Levels: {metrics['levels']['matched']}/{metrics['levels']['expected']} ({pct(metrics['levels']['matched'], metrics['levels']['expected']):.1f}%)")
    print(f"Axes: {metrics['axes']['matched']}/{metrics['axes']['expected']} ({pct(metrics['axes']['matched'], metrics['axes']['expected']):.1f}%)")
    print(f"  Missing: {metrics['axes']['missing']}")
    print(f"  Extra:   {metrics['axes']['extra']}")
    print(f"Raw dimension values: {metrics['dimensions']['raw_values_matched']}/{metrics['dimensions']['expected']} ({pct(metrics['dimensions']['raw_values_matched'], metrics['dimensions']['expected']):.1f}%)")
    print(f"Grounded exact dimensions: {metrics['dimensions']['grounded_exact']}/{metrics['dimensions']['expected']} ({pct(metrics['dimensions']['grounded_exact'], metrics['dimensions']['expected']):.1f}%)")
    print(f"Spaces: {metrics['spaces']['matched_unique_baseline']}/{metrics['spaces']['expected']} ({pct(metrics['spaces']['matched_unique_baseline'], metrics['spaces']['expected']):.1f}%)")
    print(f"  Contract instances: {metrics['spaces']['contract_instances']}")
    print(f"  Semantic overflow:  {metrics['spaces']['semantic_overflow_instances']}")
    print(f"Semantic zones: {metrics['semantic_zones']['matched']}/{metrics['semantic_zones']['expected']} ({pct(metrics['semantic_zones']['matched'], metrics['semantic_zones']['expected']):.1f}%)")
    print(f"Stairs: {metrics['stairs']['matched']}/{metrics['stairs']['expected']} ({pct(metrics['stairs']['matched'], metrics['stairs']['expected']):.1f}%)")
    manual = metrics["manual_intervention"]
    print("----------------------------------------------")
    print(f"Auto-ready: {manual['auto_ready_units']}/{manual['expected_units']} ({100*manual['auto_ready_rate']:.1f}%)")
    print(f"Review/correction: {manual['review_or_correction_units']}/{manual['expected_units']} ({100*manual['review_or_correction_rate']:.1f}%)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    contract = load_json(args.contract)
    metrics = evaluate_contract(contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print_report(metrics)
    print(f"\nReport: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
