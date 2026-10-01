import unittest

from pydantic import ValidationError

from app.schemas.documentos import (
    DocumentoAskRequest,
    DocumentoAskResponse,
    DocumentoIndexResponse,
    DocumentoQueryRequest,
)


class DocumentSchemaTests(unittest.TestCase):
    def test_query_request_trims_text_and_query(self):
        payload = DocumentoQueryRequest(text="  contexto  ", query="  pregunta  ")

        self.assertEqual(payload.text, "contexto")
        self.assertEqual(payload.query, "pregunta")

    def test_query_request_rejects_empty_values(self):
        with self.assertRaises(ValidationError):
            DocumentoQueryRequest(text="   ", query="pregunta")

    def test_ask_request_validates_top_k_bounds(self):
        valid = DocumentoAskRequest(query="pregunta", top_k=3)

        self.assertEqual(valid.top_k, 3)
        with self.assertRaises(ValidationError):
            DocumentoAskRequest(query="pregunta", top_k=0)
        with self.assertRaises(ValidationError):
            DocumentoAskRequest(query="pregunta", top_k=21)

    def test_index_response_accepts_typed_chunks(self):
        response = DocumentoIndexResponse(
            document_id="doc-1",
            chunk_count=1,
            chunks=[
                {
                    "document_id": "doc-1",
                    "chunk_id": "doc-1-0",
                    "content": "contenido",
                    "embedding": [1.0, 0.0],
                    "metadata": {"page": 1},
                }
            ],
        )

        self.assertEqual(response.chunks[0].chunk_id, "doc-1-0")
        self.assertEqual(response.chunks[0].metadata["page"], 1)

    def test_ask_response_accepts_typed_matches(self):
        response = DocumentoAskResponse(
            query="pregunta",
            document_id="doc-1",
            matches=[
                {
                    "document_id": "doc-1",
                    "chunk_id": "doc-1-0",
                    "content": "contenido",
                    "metadata": {},
                    "score": 0.9,
                }
            ],
            context="contenido",
            prompt="prompt",
            answer="respuesta",
        )

        self.assertEqual(response.matches[0].score, 0.9)


if __name__ == "__main__":
    unittest.main()
