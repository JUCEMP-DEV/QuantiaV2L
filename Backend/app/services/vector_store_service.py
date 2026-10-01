from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import sqrt
from typing import Any, Protocol

from app.core.config import settings
from app.core.supabase_client import get_supabase_admin_client


@dataclass(frozen=True)
class VectorChunk:
    document_id: str
    chunk_id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VectorStore(Protocol):
    def upsert_chunks(self, chunks: list[VectorChunk]) -> list[VectorChunk]: ...

    def list_chunks(self, document_id: str | None = None) -> list[VectorChunk]: ...

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        document_id: str | None = None,
    ) -> list[tuple[VectorChunk, float]]: ...

    def clear(self, document_id: str | None = None) -> None: ...


class LocalVectorStore:
    def __init__(self):
        self._chunks: dict[str, VectorChunk] = {}

    def upsert_chunks(self, chunks: list[VectorChunk]) -> list[VectorChunk]:
        for chunk in chunks:
            self._validate_chunk(chunk)
            self._chunks[self._key(chunk.document_id, chunk.chunk_id)] = chunk
        return chunks

    def list_chunks(self, document_id: str | None = None) -> list[VectorChunk]:
        chunks = list(self._chunks.values())
        if document_id is not None:
            chunks = [chunk for chunk in chunks if chunk.document_id == document_id]
        return sorted(chunks, key=lambda chunk: (chunk.document_id, chunk.chunk_id))

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        document_id: str | None = None,
    ) -> list[tuple[VectorChunk, float]]:
        candidates = self.list_chunks(document_id=document_id)
        scored = [(chunk, self._cosine_similarity(query_embedding, chunk.embedding)) for chunk in candidates]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: max(0, top_k)]

    def clear(self, document_id: str | None = None) -> None:
        if document_id is None:
            self._chunks.clear()
            return
        keys = [key for key, chunk in self._chunks.items() if chunk.document_id == document_id]
        for key in keys:
            self._chunks.pop(key, None)

    def _validate_chunk(self, chunk: VectorChunk) -> None:
        if not chunk.document_id.strip():
            raise ValueError("document_id es obligatorio.")
        if not chunk.chunk_id.strip():
            raise ValueError("chunk_id es obligatorio.")
        if not chunk.content.strip():
            raise ValueError("content es obligatorio.")
        if not chunk.embedding:
            raise ValueError("embedding es obligatorio.")

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot_product = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(a * a for a in left))
        right_norm = sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)

    def _key(self, document_id: str, chunk_id: str) -> str:
        return f"{document_id}:{chunk_id}"


class SupabaseVectorStore:
    def __init__(self, table_name: str | None = None) -> None:
        self.table_name = table_name or settings.vector_table_name

    def upsert_chunks(self, chunks: list[VectorChunk]) -> list[VectorChunk]:
        if not chunks:
            return []
        rows = []
        for chunk in chunks:
            _validate_vector_chunk(chunk)
            if len(chunk.embedding) != settings.embedding_dimension:
                raise ValueError(
                    "La dimension del embedding no coincide con EMBEDDING_DIMENSION "
                    f"({len(chunk.embedding)} != {settings.embedding_dimension})."
                )
            rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata,
                    "chunk_index": int(chunk.metadata.get("chunk_index", 0)),
                }
            )
        result = (
            get_supabase_admin_client()
            .table(self.table_name)
            .upsert(rows, on_conflict="chunk_id")
            .execute()
        )
        if result.data is None:
            raise RuntimeError("Supabase no confirmo el almacenamiento de chunks.")
        return chunks

    def list_chunks(self, document_id: str | None = None) -> list[VectorChunk]:
        query = get_supabase_admin_client().table(self.table_name).select(
            "document_id,chunk_id,content,embedding,metadata,chunk_index"
        )
        if document_id is not None:
            query = query.eq("document_id", document_id)
        result = query.order("chunk_index").execute()
        return [_row_to_chunk(row) for row in (result.data or [])]

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        document_id: str | None = None,
    ) -> list[tuple[VectorChunk, float]]:
        if not query_embedding or not document_id:
            return []
        result = get_supabase_admin_client().rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": max(0, top_k),
                "filter_document_id": document_id,
            },
        ).execute()
        return [(_row_to_chunk(row), float(row.get("similarity") or 0.0)) for row in (result.data or [])]

    def clear(self, document_id: str | None = None) -> None:
        if not document_id:
            raise ValueError("document_id es obligatorio para eliminar chunks en Supabase.")
        get_supabase_admin_client().table(self.table_name).delete().eq("document_id", document_id).execute()


def create_vector_store(backend: str | None = None) -> VectorStore:
    selected = (backend or settings.vector_store_backend).strip().lower()
    if selected == "local":
        return LocalVectorStore()
    if selected == "supabase":
        return SupabaseVectorStore()
    raise ValueError(f"VECTOR_STORE_BACKEND no soportado: {selected}")


def _validate_vector_chunk(chunk: VectorChunk) -> None:
    if not chunk.document_id.strip():
        raise ValueError("document_id es obligatorio.")
    if not chunk.chunk_id.strip():
        raise ValueError("chunk_id es obligatorio.")
    if not chunk.content.strip():
        raise ValueError("content es obligatorio.")
    if not chunk.embedding:
        raise ValueError("embedding es obligatorio.")


def _row_to_chunk(row: dict[str, Any]) -> VectorChunk:
    embedding = row.get("embedding") or []
    if isinstance(embedding, str):
        embedding = [float(item) for item in embedding.strip("[]").split(",") if item.strip()]
    metadata = dict(row.get("metadata") or {})
    metadata.setdefault("chunk_index", row.get("chunk_index", 0))
    return VectorChunk(
        document_id=str(row.get("document_id") or ""),
        chunk_id=str(row.get("chunk_id") or ""),
        content=str(row.get("content") or ""),
        embedding=[float(item) for item in embedding],
        metadata=metadata,
    )
