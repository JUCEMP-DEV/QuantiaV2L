from __future__ import annotations

import json
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from app.services.ocr_service import OCRService


TESTS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = TESTS_DIR / "fixtures" / "ocr_real"
EVIDENCE_DIR = TESTS_DIR / "evidence"


def _normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value).strip().lower()


def main() -> None:
    source_lines = (FIXTURE_DIR / "documento_control.txt").read_text(encoding="utf-8").splitlines()
    expectations = json.loads((FIXTURE_DIR / "expectativas.json").read_text(encoding="utf-8"))
    all_expected_data = expectations["datos_esperados"]
    cases = {
        "documento_control.txt": ("\n".join(source_lines), all_expected_data),
        "documento_texto_embebido.pdf": ("\n".join(source_lines), all_expected_data),
        "imagen_escaneada.png": ("\n".join(source_lines[:7]), all_expected_data[:5]),
        "documento_escaneado.pdf": ("\n".join(source_lines), all_expected_data),
    }

    service = OCRService()
    results = []
    for file_name, (expected_text, expected_data) in cases.items():
        started = time.perf_counter()
        result = service.process_document(FIXTURE_DIR / file_name)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        extracted = result["text"]
        normalized_extracted = _normalize(extracted)
        hits = [value for value in expected_data if _normalize(value) in normalized_extracted]
        similarity = round(SequenceMatcher(None, _normalize(expected_text), normalized_extracted).ratio(), 4)
        results.append(
            {
                "file": file_name,
                "extension": Path(file_name).suffix.lower(),
                "page_count": result["metadata"]["page_count"],
                "elapsed_ms": elapsed_ms,
                "similarity": similarity,
                "expected_data_count": len(expected_data),
                "matched_data_count": len(hits),
                "matched_data": hits,
                "extracted_text": extracted,
            }
        )

    evidence = {
        "ocr_engine": service.engine,
        "results": results,
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / "task_8_1_ocr_results.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
