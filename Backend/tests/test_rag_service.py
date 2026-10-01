import unittest
from unittest.mock import Mock, patch

from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.vector_store_service import LocalVectorStore


class RAGServiceTests(unittest.TestCase):
    def test_default_chunking_uses_configured_values(self):
        with (
            patch.object(settings, "rag_chunk_size", 150),
            patch.object(settings, "rag_chunk_overlap", 30),
        ):
            service = RAGService()

        self.assertEqual(service.chunk_size, 150)
        self.assertEqual(service.overlap, 30)

    def test_chunk_text_splits_content_by_tokens(self):
        service = RAGService(chunk_size=4, overlap=1)
        text = "uno dos tres cuatro cinco seis siete ocho nueve diez"

        chunks = service.chunk_text(text)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "uno dos tres cuatro")
        self.assertEqual(chunks[1], "cuatro cinco seis siete")
        self.assertEqual(chunks[2], "siete ocho nueve diez")

    def test_chunk_text_applies_overlap(self):
        service = RAGService(chunk_size=5, overlap=2)
        text = "uno dos tres cuatro cinco seis siete ocho"

        chunks = service.chunk_text(text)

        self.assertEqual(chunks[0].split()[-2:], chunks[1].split()[:2])

    def test_chunk_text_returns_empty_for_blank_text(self):
        service = RAGService()

        self.assertEqual(service.chunk_text("   \n\t"), [])

    def test_index_document_stores_chunks_with_embeddings(self):
        embedding_service = Mock()
        embedding_service.embed_texts.return_value = [[1.0, 0.0], [0.0, 1.0]]
        vector_store = LocalVectorStore()
        service = RAGService(
            chunk_size=3,
            overlap=0,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        result = service.index_document(
            "uno dos tres cuatro cinco seis",
            document_id="doc-1",
            metadata={"file_name": "sample.txt"},
        )

        self.assertEqual(result["document_id"], "doc-1")
        self.assertEqual(result["chunk_count"], 2)
        self.assertEqual(len(vector_store.list_chunks(document_id="doc-1")), 2)
        self.assertEqual(result["chunks"][0]["metadata"]["file_name"], "sample.txt")
        embedding_service.embed_texts.assert_called_once_with(["uno dos tres", "cuatro cinco seis"])

    def test_retrieve_chunks_orders_by_semantic_similarity(self):
        embedding_service = Mock()
        embedding_service.embed_texts.return_value = [[1.0, 0.0], [0.0, 1.0]]
        embedding_service.embed_text.return_value = [0.0, 1.0]
        vector_store = LocalVectorStore()
        service = RAGService(
            chunk_size=3,
            overlap=0,
            embedding_service=embedding_service,
            vector_store=vector_store,
            top_k=2,
        )
        service.index_document("chunk uno base chunk dos relevante", document_id="doc-1")

        matches = service.retrieve_chunks("consulta relevante", document_id="doc-1")

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["content"], "chunk dos relevante")
        self.assertGreater(matches[0]["score"], matches[1]["score"])
        embedding_service.embed_text.assert_called_once_with("consulta relevante")

    def test_retrieve_context_returns_ordered_context(self):
        embedding_service = Mock()
        embedding_service.embed_texts.return_value = [[1.0, 0.0], [0.0, 1.0]]
        embedding_service.embed_text.return_value = [0.0, 1.0]
        service = RAGService(
            chunk_size=2,
            overlap=0,
            embedding_service=embedding_service,
            vector_store=LocalVectorStore(),
            top_k=1,
        )
        service.index_document("primero bloque segundo bloque", document_id="doc-1")

        result = service.retrieve_context("segundo", document_id="doc-1")

        self.assertEqual(result["document_id"], "doc-1")
        self.assertEqual(result["context"], "segundo bloque")
        self.assertEqual(len(result["matches"]), 1)

    def test_build_prompt_formats_context_with_chunk_ids(self):
        service = RAGService()
        matches = [
            {"chunk_id": "doc-1-0", "content": "Costo directo de obra", "score": 0.9, "metadata": {}},
            {"chunk_id": "doc-1-1", "content": "Incluye materiales", "score": 0.8, "metadata": {}},
        ]

        prompt = service.build_prompt("Que incluye?", matches=matches)

        self.assertIn("usando exclusivamente los fragmentos proporcionados", prompt)
        self.assertIn("No hay informacion suficiente en el documento", prompt)
        self.assertIn("[doc-1-0] Costo directo de obra", prompt)
        self.assertIn("[doc-1-1] Incluye materiales", prompt)
        self.assertIn("Pregunta:\nQue incluye?", prompt)

    def test_answer_with_context_sends_rag_prompt_to_llm(self):
        llm_service = Mock()
        llm_service.generate_from_prompt.return_value = "El precio del servicio es de 100 pesos."
        service = RAGService(chunk_size=50, overlap=10, llm_service=llm_service)

        result = service.answer_with_context(
            "El precio del servicio es de 100 pesos.",
            "Cual es el precio?",
        )

        self.assertIn("precio", result["answer"].lower())
        prompt = llm_service.generate_from_prompt.call_args.args[0]
        self.assertIn("[contexto] El precio del servicio", prompt)
        self.assertIn("Cual es el precio?", prompt)

    def test_answer_from_retrieval_returns_no_context_without_llm_call(self):
        embedding_service = Mock()
        embedding_service.embed_text.return_value = [1.0, 0.0]
        llm_service = Mock()
        service = RAGService(
            embedding_service=embedding_service,
            vector_store=LocalVectorStore(),
            llm_service=llm_service,
        )

        result = service.answer_from_retrieval("pregunta sin documento", document_id="missing")

        self.assertEqual(result["matches"], [])
        self.assertEqual(result["answer"], "No se encontro suficiente contexto para responder.")
        llm_service.generate_from_prompt.assert_not_called()

    def test_answer_from_retrieval_rejects_empty_query(self):
        service = RAGService()

        with self.assertRaises(ValueError):
            service.answer_from_retrieval("   ")

    def test_answer_from_retrieval_respects_top_k(self):
        embedding_service = Mock()
        embedding_service.embed_texts.return_value = [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]]
        embedding_service.embed_text.return_value = [1.0, 0.0]
        llm_service = Mock()
        llm_service.generate_from_prompt.return_value = "Respuesta top k"
        service = RAGService(
            chunk_size=2,
            overlap=0,
            embedding_service=embedding_service,
            vector_store=LocalVectorStore(),
            llm_service=llm_service,
            top_k=3,
        )
        service.index_document("uno dos tres cuatro cinco seis", document_id="doc-1")

        result = service.answer_from_retrieval("uno", document_id="doc-1", top_k=1)

        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["answer"], "Respuesta top k [doc-1-0]")
        self.assertIn("[doc-1-0] uno dos", result["prompt"])
    def test_answer_from_retrieval_uses_semantic_context_prompt(self):
        embedding_service = Mock()
        embedding_service.embed_texts.return_value = [[1.0, 0.0], [0.0, 1.0]]
        embedding_service.embed_text.return_value = [0.0, 1.0]
        llm_service = Mock()
        llm_service.generate_from_prompt.return_value = "Respuesta con contexto"
        service = RAGService(
            chunk_size=2,
            overlap=0,
            embedding_service=embedding_service,
            vector_store=LocalVectorStore(),
            llm_service=llm_service,
            top_k=1,
        )
        service.index_document("primer bloque segundo bloque", document_id="doc-1")

        result = service.answer_from_retrieval("segundo", document_id="doc-1")

        self.assertEqual(result["answer"], "Respuesta con contexto [doc-1-1]")
        self.assertEqual(result["context"], "segundo bloque")
        self.assertIn("prompt", result)
        self.assertIn("[doc-1-1] segundo bloque", result["prompt"])

    def test_ground_answer_citation_replaces_invalid_model_identifier(self):
        service = RAGService()
        matches = [
            {
                "chunk_id": "doc-1-3",
                "content": "La instalacion hidraulica utilizara tuberia PPR.",
                "score": 0.8,
            },
            {
                "chunk_id": "doc-1-1",
                "content": "La estructura utilizara concreto reforzado.",
                "score": 0.7,
            },
        ]

        answer = service._ground_answer_citation("PPR. [identificador-inventado]", matches)

        self.assertEqual(answer, "PPR. [doc-1-3]")

    def test_ground_answer_citation_standardizes_no_information_response(self):
        service = RAGService()
        matches = [{"chunk_id": "doc-1-0", "content": "Contexto sin respuesta", "score": 0.5}]

        answer = service._ground_answer_citation(
            "No hay información suficiente en el documento para determinar la marca.",
            matches,
        )

        self.assertEqual(answer, "No hay informacion suficiente en el documento.")


if __name__ == "__main__":
    unittest.main()

