from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.services.vector_store_service import LocalVectorStore


TESTS_DIR = Path(__file__).resolve().parents[1]
FIXTURE_DIR = TESTS_DIR / "fixtures" / "rag_real"
EVIDENCE_DIR = TESTS_DIR / "evidence"


def _normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value).strip().lower()


def main() -> None:
    source_text = (FIXTURE_DIR / "documento_rag_control.txt").read_text(encoding="utf-8")
    expectations = json.loads((FIXTURE_DIR / "expectativas_rag.json").read_text(encoding="utf-8"))
    questions = expectations["preguntas"]
    results = []

    for chunk_size in (80, 150, 250, 700):
        overlap = max(2, chunk_size // 5)
        for top_k in (1, 2, 3):
            vector_store = LocalVectorStore()
            service = RAGService(
                chunk_size=chunk_size,
                overlap=overlap,
                embedding_service=EmbeddingService(backend="hashing", dimension=384),
                vector_store=vector_store,
                top_k=top_k,
            )
            indexed = service.index_document(source_text, document_id=f"control-{chunk_size}")
            query_results = []
            for item in questions:
                started = time.perf_counter()
                matches = service.retrieve_chunks(
                    item["pregunta"],
                    document_id=indexed["document_id"],
                    top_k=top_k,
                )
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                expected = _normalize(item["respuesta"])
                relevant_rank = next(
                    (
                        rank
                        for rank, match in enumerate(matches, start=1)
                        if expected in _normalize(match["content"])
                    ),
                    None,
                )
                query_results.append(
                    {
                        "question": item["pregunta"],
                        "expected": item["respuesta"],
                        "relevant_rank": relevant_rank,
                        "retrieved": relevant_rank is not None,
                        "elapsed_ms": elapsed_ms,
                        "context_word_count": sum(len(match["content"].split()) for match in matches),
                        "matches": [
                            {
                                "chunk_id": match["chunk_id"],
                                "score": round(match["score"], 6),
                                "content": match["content"],
                            }
                            for match in matches
                        ],
                    }
                )

            hits = sum(1 for item in query_results if item["retrieved"])
            reciprocal_ranks = [
                1 / item["relevant_rank"] if item["relevant_rank"] is not None else 0 for item in query_results
            ]
            results.append(
                {
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "top_k": top_k,
                    "chunk_count": indexed["chunk_count"],
                    "recall": round(hits / len(query_results), 4),
                    "mean_reciprocal_rank": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
                    "average_query_ms": round(
                        sum(item["elapsed_ms"] for item in query_results) / len(query_results), 3
                    ),
                    "average_context_words": round(
                        sum(item["context_word_count"] for item in query_results) / len(query_results), 1
                    ),
                    "queries": query_results,
                }
            )

    multi_chunk_results = [item for item in results if item["chunk_count"] > 1]
    ranked = sorted(
        multi_chunk_results,
        key=lambda item: (
            -item["recall"],
            -item["mean_reciprocal_rank"],
            item["top_k"],
            item["average_context_words"],
            item["average_query_ms"],
        ),
    )
    evidence = {
        "embedding_backend": "hashing",
        "embedding_dimension": 384,
        "question_count": len(questions),
        "recommended": {
            key: ranked[0][key]
            for key in (
                "chunk_size",
                "overlap",
                "top_k",
                "chunk_count",
                "recall",
                "mean_reciprocal_rank",
                "average_query_ms",
                "average_context_words",
            )
        },
        "selection_note": "Las configuraciones que producen un solo chunk se excluyen porque no evalúan recuperación selectiva.",
        "configurations": results,
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / "task_8_2_rag_results.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence["recommended"], ensure_ascii=False, indent=2))
    for item in results:
        print(
            f"chunk={item['chunk_size']} overlap={item['overlap']} top_k={item['top_k']} "
            f"recall={item['recall']:.2f} mrr={item['mean_reciprocal_rank']:.2f} "
            f"context_words={item['average_context_words']:.1f} avg_ms={item['average_query_ms']:.3f}"
        )


if __name__ == "__main__":
    main()
