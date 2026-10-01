from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from math import sqrt
from typing import Any

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(
        self,
        model_name: str | None = None,
        model: Any | None = None,
        backend: str | None = None,
        dimension: int | None = None,
    ):
        self.model_name = model_name or settings.embedding_model
        self._model = model
        self.backend = (backend or settings.embedding_backend).strip().lower().replace("-", "_")
        self.dimension = dimension or settings.embedding_dimension
        if self._model is not None:
            self.backend = "sentence_transformers"
        if self.backend not in {"sentence_transformers", "hashing"}:
            raise EmbeddingServiceError(f"EMBEDDING_BACKEND no soportado: {self.backend}")

    def embed_text(self, text: str) -> list[float]:
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        clean_texts = [self._normalize_text(text) for text in texts]
        if not clean_texts:
            return []
        if any(not text for text in clean_texts):
            raise EmbeddingServiceError("No se pueden generar embeddings de textos vacios.")

        if self.backend == "hashing":
            return [self._hashing_vector(text) for text in clean_texts]

        model = self._get_model()
        try:
            encoded = model.encode(clean_texts, convert_to_numpy=False, normalize_embeddings=True)
        except TypeError:
            encoded = model.encode(clean_texts)
        except Exception as exc:  # pragma: no cover - depends on local model runtime
            raise EmbeddingServiceError(f"Error al generar embeddings: {exc}") from exc

        vectors = self._to_vectors(encoded)
        if len(vectors) != len(clean_texts):
            raise EmbeddingServiceError("El modelo devolvio una cantidad invalida de embeddings.")
        return vectors

    def _hashing_vector(self, text: str) -> list[float]:
        tokens = re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE)
        features = tokens + [f"{left}::{right}" for left, right in zip(tokens, tokens[1:])]
        vector = [0.0] * self.dimension
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            vector[index] += 1.0 if digest[8] & 1 else -1.0
        norm = sqrt(sum(value * value for value in vector))
        if norm == 0:
            raise EmbeddingServiceError("No se pudo generar un embedding para el texto.")
        return [value / norm for value in vector]

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingServiceError(
                "sentence-transformers no esta instalado. Ejecuta pip install -r requirements.txt."
            ) from exc

        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:  # pragma: no cover - may download/load model
            raise EmbeddingServiceError(f"No se pudo cargar el modelo de embeddings {self.model_name}: {exc}") from exc
        return self._model

    def _normalize_text(self, text: str) -> str:
        return " ".join(str(text).split())

    def _to_vectors(self, encoded: Any) -> list[list[float]]:
        if hasattr(encoded, "tolist"):
            encoded = encoded.tolist()
        if not isinstance(encoded, list):
            encoded = list(encoded)

        if encoded and all(isinstance(value, (int, float)) for value in encoded):
            encoded = [encoded]

        vectors = []
        for vector in encoded:
            if hasattr(vector, "tolist"):
                vector = vector.tolist()
            if not isinstance(vector, list):
                vector = list(vector)
            vectors.append([float(value) for value in vector])
        return vectors
