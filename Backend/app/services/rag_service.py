from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_store_service import VectorChunk, VectorStore, create_vector_store


class RAGService:
    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
        llm_service: LLMService | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        top_k: int | None = None,
    ):
        resolved_chunk_size = chunk_size if chunk_size is not None else settings.rag_chunk_size
        resolved_overlap = overlap if overlap is not None else settings.rag_chunk_overlap
        self.chunk_size = max(1, resolved_chunk_size)
        self.overlap = max(0, min(resolved_overlap, self.chunk_size - 1))
        self.llm_service = llm_service or LLMService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or create_vector_store()
        self.top_k = max(1, top_k if top_k is not None else settings.rag_top_k)

    def chunk_text(self, text: str) -> list[str]:
        tokens = self._tokenize(text)
        if not tokens:
            return []
        if len(tokens) <= self.chunk_size:
            return [" ".join(tokens)]

        chunks: list[str] = []
        step = self.chunk_size - self.overlap
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            if chunk_tokens:
                chunks.append(" ".join(chunk_tokens))
            if end >= len(tokens):
                break
            start += step

        return chunks

    def index_document(
        self,
        text: str,
        document_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chunks = self.chunk_text(text)
        if not chunks:
            return {
                "document_id": document_id or str(uuid4()),
                "chunk_count": 0,
                "chunks": [],
            }

        resolved_document_id = document_id or str(uuid4())
        embeddings = self.embedding_service.embed_texts(chunks)
        vector_chunks = []
        for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_metadata = {
                **(metadata or {}),
                "chunk_index": index,
                "chunk_size": self.chunk_size,
                "overlap": self.overlap,
            }
            vector_chunks.append(
                VectorChunk(
                    document_id=resolved_document_id,
                    chunk_id=f"{resolved_document_id}-{index}",
                    content=content,
                    embedding=embedding,
                    metadata=chunk_metadata,
                )
            )

        stored_chunks = self.vector_store.upsert_chunks(vector_chunks)
        return {
            "document_id": resolved_document_id,
            "chunk_count": len(stored_chunks),
            "chunks": [chunk.to_dict() for chunk in stored_chunks],
        }

    def retrieve_chunks(
        self,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not query or not query.strip():
            return []

        query_embedding = self.embedding_service.embed_text(query)
        results = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k if top_k is not None else self.top_k,
            document_id=document_id,
        )
        return [
            {
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "score": score,
            }
            for chunk, score in results
        ]

    def retrieve_context(
        self,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        matches = self.retrieve_chunks(query=query, document_id=document_id, top_k=top_k)
        context = "\n\n".join(match["content"] for match in matches) if matches else "No hay contexto disponible."
        return {
            "query": query,
            "document_id": document_id,
            "matches": matches,
            "context": context,
        }

    def build_prompt(self, query: str, matches: list[dict[str, Any]] | None = None, context: str | None = None) -> str:
        if not query or not query.strip():
            raise ValueError("La pregunta no puede estar vacia.")

        context_block = self._format_context_block(matches=matches, context=context)
        return (
            "Responde la pregunta usando exclusivamente los fragmentos proporcionados.\n"
            "Reglas obligatorias:\n"
            "1. Copia solo la respuesta minima respaldada por el texto; no amplíes siglas ni agregues explicaciones.\n"
            "2. No inventes datos, marcas, fechas, definiciones ni identificadores.\n"
            "3. Si la respuesta existe, usa exactamente: <respuesta breve> [<identificador exacto del fragmento>].\n"
            "4. Si no existe, responde exactamente: No hay informacion suficiente en el documento.\n"
            "5. La respuesta debe tener como maximo dos oraciones.\n\n"
            f"Contexto recuperado:\n{context_block}\n\n"
            f"Pregunta:\n{query.strip()}\n\n"
            "Respuesta:"
        )

    def build_context(self, chunks: list[str], query: str) -> str:
        if not chunks:
            return "No hay contexto disponible."

        ranked = self._rank_chunks(chunks, query)
        context_parts = []
        for chunk in ranked[: self.top_k]:
            context_parts.append(chunk)
        return "\n\n".join(context_parts)

    def _rank_chunks(self, chunks: list[str], query: str) -> list[str]:
        query_lower = query.lower()
        query_tokens = self._query_tokens(query)
        scored = []
        for index, chunk in enumerate(chunks):
            chunk_lower = chunk.lower()
            score = 0
            if query_lower and query_lower in chunk_lower:
                score += 3
            score += sum(1 for token in query_tokens if token in chunk_lower)
            scored.append((score, -index, chunk))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [chunk for _, _, chunk in scored]

    def answer_with_context(self, text: str, query: str) -> dict[str, Any]:
        chunks = self.chunk_text(text)
        context = self.build_context(chunks, query)
        return {
            "query": query,
            "chunks": chunks,
            "context": context,
            "answer": self._build_answer(context, query),
        }

    def answer_from_retrieval(
        self,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("La pregunta no puede estar vacia.")

        retrieved = self.retrieve_context(query=query, document_id=document_id, top_k=top_k)
        prompt = self.build_prompt(query=query, matches=retrieved["matches"])
        if not retrieved["matches"]:
            answer = "No se encontro suficiente contexto para responder."
        else:
            answer = self._generate_from_prompt_or_context(prompt=prompt, context=retrieved["context"], query=query)
            answer = self._ground_answer_citation(answer, retrieved["matches"])
        return {
            **retrieved,
            "prompt": prompt,
            "answer": answer,
        }

    def _build_answer(self, context: str, query: str) -> str:
        if not context or context == "No hay contexto disponible.":
            return "No se encontro suficiente contexto para responder."

        prompt = self.build_prompt(query=query, context=context)
        return self._generate_from_prompt_or_context(prompt=prompt, context=context, query=query)

    def _generate_from_prompt_or_context(self, prompt: str, context: str, query: str) -> str:
        if hasattr(self.llm_service, "generate_from_prompt"):
            return self.llm_service.generate_from_prompt(prompt)
        return self.llm_service.generate_answer(context, query)

    def _ground_answer_citation(self, answer: str, matches: list[dict[str, Any]]) -> str:
        cleaned_answer = re.sub(r"\s*\[[^\]]+\]\s*", " ", str(answer or "")).strip()
        cleaned_answer = re.sub(r"\s+", " ", cleaned_answer)
        normalized_answer = self._normalized_tokens(cleaned_answer)
        refusal_tokens = self._normalized_tokens("No hay informacion suficiente en el documento")
        if refusal_tokens and len(normalized_answer & refusal_tokens) / len(refusal_tokens) >= 0.8:
            return "No hay informacion suficiente en el documento."
        if not cleaned_answer or not matches:
            return cleaned_answer

        support_tokens = {
            token
            for token in normalized_answer
            if len(token) > 2 or token.isdigit()
        }
        supported_match = max(
            matches,
            key=lambda match: (
                len(support_tokens & self._normalized_tokens(str(match.get("content", "")))),
                float(match.get("score") or 0.0),
            ),
        )
        chunk_id = str(supported_match.get("chunk_id") or "").strip()
        return f"{cleaned_answer} [{chunk_id}]" if chunk_id else cleaned_answer

    @staticmethod
    def _normalized_tokens(value: str) -> set[str]:
        return {token.casefold() for token in re.findall(r"[^\W_]+", value or "", flags=re.UNICODE)}

    def _format_context_block(self, matches: list[dict[str, Any]] | None = None, context: str | None = None) -> str:
        if matches:
            formatted = []
            for index, match in enumerate(matches, start=1):
                chunk_id = match.get("chunk_id") or f"fragmento-{index}"
                content = str(match.get("content", "")).strip()
                if content:
                    formatted.append(f"[{chunk_id}] {content}")
            if formatted:
                return "\n\n".join(formatted)

        if context and context.strip() and context != "No hay contexto disponible.":
            return f"[contexto] {context.strip()}"
        return "No hay contexto disponible."

    def _tokenize(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        normalized = re.sub(r"\s+", " ", text).strip()
        return re.findall(r"\S+", normalized)

    def _query_tokens(self, query: str) -> set[str]:
        return {token.lower() for token in re.findall(r"\w+", query or "") if token.strip()}

