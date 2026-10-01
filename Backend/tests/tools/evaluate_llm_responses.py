from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.vector_store_service import LocalVectorStore


TESTS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = TESTS_DIR / "fixtures" / "rag_real"
EVIDENCE_DIR = TESTS_DIR / "evidence"
EVIDENCE_PATH = EVIDENCE_DIR / "task_8_3_llm_results.json"


def _tokens(value: str) -> set[str]:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return {token for token in re.findall(r"[a-z0-9]+", ascii_value.lower()) if token}


def _write_evidence(evidence: dict) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source_text = (FIXTURE_DIR / "documento_rag_control.txt").read_text(encoding="utf-8")
    expectations = json.loads((FIXTURE_DIR / "expectativas_rag.json").read_text(encoding="utf-8"))
    cases = [
        {**item, "kind": "answerable"} for item in expectations["preguntas"]
    ] + [
        {
            "pregunta": "¿Cuál es la marca de pintura autorizada?",
            "respuesta": None,
            "kind": "unanswerable",
        },
        {
            "pregunta": "¿Cuál es la fecha exacta de entrega de la vivienda?",
            "respuesta": None,
            "kind": "unanswerable",
        },
    ]

    llm_service = LLMService()
    health = llm_service.health()
    if not health.get("available") or not health.get("model_available"):
        raise RuntimeError(f"Ollama o el modelo no estan disponibles: {health}")

    service = RAGService(
        llm_service=llm_service,
        embedding_service=EmbeddingService(backend="hashing", dimension=384),
        vector_store=LocalVectorStore(),
    )
    indexed = service.index_document(source_text, document_id="control-llm")
    evidence = {
        "model": llm_service.model,
        "context_length": llm_service.context_length,
        "max_tokens": llm_service.max_tokens,
        "timeout_seconds": llm_service.timeout,
        "temperature": llm_service.temperature,
        "chunk_size": service.chunk_size,
        "overlap": service.overlap,
        "top_k": service.top_k,
        "chunk_count": indexed["chunk_count"],
        "results": [],
    }

    for index, item in enumerate(cases, start=1):
        started = time.perf_counter()
        try:
            result = service.answer_from_retrieval(
                item["pregunta"],
                document_id=indexed["document_id"],
                top_k=service.top_k,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            answer = result["answer"].strip()
            answer_tokens = _tokens(answer)
            expected_tokens = _tokens(item["respuesta"] or "")
            coverage = (
                round(len(answer_tokens & expected_tokens) / len(expected_tokens), 4)
                if expected_tokens
                else None
            )
            cited_ids = [
                match["chunk_id"] for match in result["matches"] if match["chunk_id"] in answer
            ]
            refusal_tokens = _tokens("No hay informacion suficiente en el documento")
            refusal_coverage = round(len(answer_tokens & refusal_tokens) / len(refusal_tokens), 4)
            passed = coverage is not None and coverage >= 0.8
            if item["kind"] == "unanswerable":
                passed = refusal_coverage >= 0.8
            record = {
                "index": index,
                "kind": item["kind"],
                "question": item["pregunta"],
                "expected": item["respuesta"],
                "answer": answer,
                "expected_token_coverage": coverage,
                "refusal_token_coverage": refusal_coverage if item["kind"] == "unanswerable" else None,
                "cited_chunk_ids": cited_ids,
                "citation_present": bool(cited_ids),
                "elapsed_ms": elapsed_ms,
                "passed": passed,
                "matches": [
                    {
                        "chunk_id": match["chunk_id"],
                        "score": round(match["score"], 6),
                    }
                    for match in result["matches"]
                ],
            }
        except Exception as exc:
            record = {
                "index": index,
                "kind": item["kind"],
                "question": item["pregunta"],
                "expected": item["respuesta"],
                "error": str(exc),
                "passed": False,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        evidence["results"].append(record)
        _write_evidence(evidence)
        print(
            f"[{index}/{len(cases)}] pass={record['passed']} "
            f"citation={record.get('citation_present', False)} ms={record['elapsed_ms']}"
        )
        if record.get("answer"):
            print(record["answer"])

    answerable = [item for item in evidence["results"] if item["kind"] == "answerable"]
    unanswerable = [item for item in evidence["results"] if item["kind"] == "unanswerable"]
    completed = [item for item in evidence["results"] if "error" not in item]
    evidence["summary"] = {
        "answerable_passed": sum(1 for item in answerable if item["passed"]),
        "answerable_total": len(answerable),
        "unanswerable_refused": sum(1 for item in unanswerable if item["passed"]),
        "unanswerable_total": len(unanswerable),
        "responses_with_citation": sum(1 for item in completed if item.get("citation_present")),
        "completed_total": len(completed),
        "average_latency_ms": round(
            sum(item["elapsed_ms"] for item in completed) / len(completed), 2
        ) if completed else None,
        "max_latency_ms": max((item["elapsed_ms"] for item in completed), default=None),
    }
    _write_evidence(evidence)
    print(json.dumps(evidence["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
