import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from app.api.v1.endpoints import documentos
from app.core.config import settings
from app.core.document_auth import create_access_token
from app.main import app
from app.services.document_repository_service import LocalDocumentRepository
from app.services.document_service import DocumentService
from app.services.document_storage_service import LocalDocumentStorage
from app.services.ocr_service import OCRDependencyError
from app.services.vector_store_service import LocalVectorStore


class DocumentEndpointsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_secret = settings.auth_token_secret
        self.original_max_bytes = settings.document_max_upload_bytes
        self.original_max_pages = settings.document_max_pages
        self.original_max_user_documents = settings.document_max_user_documents
        self.original_max_user_bytes = settings.document_max_user_bytes
        self.original_reject_duplicates = settings.document_reject_duplicates
        self.original_retention_days = settings.document_retention_days
        self.original_failed_retention_hours = settings.document_failed_retention_hours
        settings.auth_token_secret = "test-secret-with-enough-entropy"
        settings.document_max_pages = 100
        settings.document_max_user_documents = 100
        settings.document_max_user_bytes = 500 * 1024 * 1024
        settings.document_reject_duplicates = True
        settings.document_retention_days = 90
        settings.document_failed_retention_hours = 24
        documentos.repository = LocalDocumentRepository()
        documentos.storage = LocalDocumentStorage(Path(self.temp_dir.name) / "stored")
        documentos.service = DocumentService(storage_dir=Path(self.temp_dir.name) / "staging")
        documentos.rag_service.vector_store = LocalVectorStore()
        self.original_chunk_size = documentos.rag_service.chunk_size
        self.original_overlap = documentos.rag_service.overlap
        self.client = TestClient(app)
        self.headers = self._headers("user-1", "user1@example.com")

    def tearDown(self):
        documentos.rag_service.chunk_size = self.original_chunk_size
        documentos.rag_service.overlap = self.original_overlap
        settings.auth_token_secret = self.original_secret
        settings.document_max_upload_bytes = self.original_max_bytes
        settings.document_max_pages = self.original_max_pages
        settings.document_max_user_documents = self.original_max_user_documents
        settings.document_max_user_bytes = self.original_max_user_bytes
        settings.document_reject_duplicates = self.original_reject_duplicates
        settings.document_retention_days = self.original_retention_days
        settings.document_failed_retention_hours = self.original_failed_retention_hours
        self.temp_dir.cleanup()

    def _headers(self, user_id: str, email: str) -> dict[str, str]:
        token = create_access_token(user_id, email)
        self.assertIsNotNone(token)
        return {"Authorization": f"Bearer {token}"}

    def _upload(self, name: str = "sample.txt", content: bytes = b"Documento listado"):
        return self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            files={"file": (name, content, "text/plain")},
        )

    def test_document_router_requires_authentication(self):
        response = self.client.get("/api/documentos")

        self.assertEqual(response.status_code, 401)

    def test_document_router_is_registered_under_api_prefix(self):
        response = self.client.get("/api/documentos", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn("documents", response.json())

    def test_query_endpoint_returns_response(self):
        payload = {
            "text": "El precio del servicio es de 100 pesos.",
            "query": "Cual es el precio?",
        }

        with patch(
            "app.services.llm_service.LLMService._call_ollama",
            return_value="El precio del servicio es de 100 pesos.",
        ):
            response = self.client.post("/api/documentos/query", headers=self.headers, json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "El precio del servicio es de 100 pesos.")

    def test_ocr_test_endpoint_processes_uploaded_text_file(self):
        response = self.client.post(
            "/api/documentos/ocr/test",
            headers=self.headers,
            files={"file": ("sample.txt", b"Linea OCR\n\nContenido real", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ocr_completed")
        self.assertTrue(payload["document_id"])
        self.assertEqual(payload["user_id"], "user-1")
        self.assertFalse(payload["indexed"])
        self.assertNotIn("stored_path", payload)
        self.assertIn("Linea OCR", payload["text"])
        self.assertEqual(payload["metadata"]["original_file_name"], "sample.txt")

    def test_upload_reports_ocr_dependency_error_without_persisting_it_as_text(self):
        with patch.object(
            documentos.service,
            "process_file",
            side_effect=OCRDependencyError("Tesseract no esta disponible."),
        ):
            response = self._upload(name="sample.txt", content=b"contenido OCR")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Tesseract no esta disponible", response.json()["detail"])
        records = documentos.repository.list("user-1")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "failed")
        self.assertEqual(records[0]["ocr_text"], "")
        self.assertIn("Tesseract no esta disponible", records[0]["error_detail"])

    def test_list_documents_returns_only_owner_documents(self):
        upload = self._upload().json()

        owner_response = self.client.get("/api/documentos", headers=self.headers)
        other_response = self.client.get(
            "/api/documentos",
            headers=self._headers("user-2", "user2@example.com"),
        )

        owner_documents = owner_response.json()["documents"]
        self.assertEqual(len(owner_documents), 1)
        self.assertEqual(owner_documents[0]["document_id"], upload["document_id"])
        self.assertEqual(other_response.json()["documents"], [])

    def test_process_document_indexes_uploaded_document(self):
        upload = self._upload(content=b"uno dos tres cuatro cinco seis").json()

        with patch.object(documentos.rag_service.embedding_service, "embed_texts", return_value=[[1.0], [0.5]]):
            response = self.client.post(
                f"/api/documentos/{upload['document_id']}/procesar",
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["document_id"], upload["document_id"])
        self.assertGreater(payload["chunk_count"], 0)
        record = documentos.repository.get(upload["document_id"], "user-1")
        self.assertEqual(record["status"], "ready")

    def test_plan_base_returns_authenticated_canonical_raster(self):
        image_buffer = BytesIO()
        Image.new("RGB", (12, 8), "white").save(image_buffer, format="PNG")

        with patch.object(
            documentos.service,
            "process_file",
            return_value={"text": "", "metadata": {}},
        ):
            upload = self.client.post(
                "/api/documentos/upload",
                headers=self.headers,
                files={
                    "file": (
                        "plano.png",
                        image_buffer.getvalue(),
                        "image/png",
                    )
                },
            )

        self.assertEqual(upload.status_code, 200)
        document_id = upload.json()["document_id"]
        response = self.client.get(
            f"/api/documentos/{document_id}/plano-base?page_number=1",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        raster = Image.open(BytesIO(response.content))
        self.assertEqual(raster.size, (12, 8))

        forbidden = self.client.get(
            f"/api/documentos/{document_id}/plano-base?page_number=1",
            headers=self._headers("user-2", "user2@example.com"),
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_ask_document_indexes_and_answers(self):
        documentos.rag_service.chunk_size = 3
        documentos.rag_service.overlap = 0
        upload = self._upload(content=b"base inicial respuesta relevante").json()

        with patch.object(
            documentos.rag_service.embedding_service,
            "embed_texts",
            return_value=[[1.0, 0.0], [0.0, 1.0]],
        ), patch.object(
            documentos.rag_service.embedding_service,
            "embed_text",
            return_value=[0.0, 1.0],
        ), patch.object(
            documentos.rag_service.llm_service,
            "generate_from_prompt",
            return_value="Respuesta RAG",
        ):
            response = self.client.post(
                f"/api/documentos/{upload['document_id']}/preguntar",
                headers=self.headers,
                json={"query": "respuesta", "top_k": 1},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["document_id"], upload["document_id"])
        self.assertEqual(len(payload["matches"]), 1)
        self.assertEqual(
            payload["answer"],
            f"Respuesta RAG [{payload['matches'][0]['chunk_id']}]",
        )

    def test_other_user_cannot_access_document(self):
        upload = self._upload().json()

        response = self.client.post(
            f"/api/documentos/{upload['document_id']}/preguntar",
            headers=self._headers("user-2", "user2@example.com"),
            json={"query": "algo"},
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_removes_record_chunks_and_file(self):
        upload = self._upload().json()
        document_id = upload["document_id"]
        record = documentos.repository.get(document_id, "user-1")
        stored_file = Path(self.temp_dir.name) / "stored" / record["storage_object_path"]
        self.assertTrue(stored_file.exists())

        response = self.client.delete(f"/api/documentos/{document_id}", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(documentos.repository.get(document_id, "user-1"))
        self.assertFalse(stored_file.exists())
        self.assertEqual(documentos.rag_service.vector_store.list_chunks(document_id), [])

    def test_upload_rejects_unsupported_and_oversized_files(self):
        unsupported = self._upload(name="malware.exe", content=b"x")
        self.assertEqual(unsupported.status_code, 415)

        mime_mismatch = self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            files={"file": ("documento.pdf", b"%PDF", "text/plain")},
        )
        self.assertEqual(mime_mismatch.status_code, 415)

        settings.document_max_upload_bytes = 3
        oversized = self._upload(content=b"1234")
        self.assertEqual(oversized.status_code, 413)

    def test_upload_rejects_spoofed_or_invalid_content(self):
        binary_text = self._upload(name="documento.txt", content=b"texto\x00binario")
        fake_image = self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            files={"file": ("imagen.png", b"no-es-una-imagen", "image/png")},
        )
        invalid_json = self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            files={"file": ("datos.json", b"{invalido", "application/json")},
        )

        self.assertEqual(binary_text.status_code, 415)
        self.assertEqual(fake_image.status_code, 415)
        self.assertEqual(invalid_json.status_code, 415)

    def test_upload_rejects_pdf_over_page_limit(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=100, height=100)
        content = BytesIO()
        writer.write(content)
        settings.document_max_pages = 1

        response = self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            files={"file": ("dos-paginas.pdf", content.getvalue(), "application/pdf")},
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("2 paginas", response.json()["detail"])

    def test_upload_rejects_duplicate_content_for_same_user(self):
        first = self._upload(name="primero.txt", content=b"contenido duplicado")
        second = self._upload(name="segundo.txt", content=b"contenido duplicado")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertIn(first.json()["document_id"], second.json()["detail"])

    def test_upload_enforces_document_count_quota(self):
        settings.document_max_user_documents = 1

        first = self._upload(name="primero.txt", content=b"contenido uno")
        second = self._upload(name="segundo.txt", content=b"contenido dos")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 413)

    def test_upload_removes_stored_object_when_repository_creation_fails(self):
        stored_root = Path(self.temp_dir.name) / "stored"
        with patch.object(documentos.repository, "create", side_effect=RuntimeError("falla inducida")):
            response = self._upload(content=b"contenido temporal")

        self.assertEqual(response.status_code, 500)
        self.assertEqual([path for path in stored_root.rglob("*") if path.is_file()], [])

    def test_upload_validates_quote_and_module_contract(self):
        invalid_quote = self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            data={"quote_id": "no-es-uuid"},
            files={"file": ("sample.txt", b"contenido", "text/plain")},
        )
        invalid_module = self.client.post(
            "/api/documentos/upload",
            headers=self.headers,
            data={"module_key": "desconocido"},
            files={"file": ("sample.txt", b"contenido", "text/plain")},
        )

        self.assertEqual(invalid_quote.status_code, 422)
        self.assertEqual(invalid_module.status_code, 422)

    def test_ask_missing_document_returns_404(self):
        response = self.client.post(
            "/api/documentos/no-existe/preguntar",
            headers=self.headers,
            json={"query": "algo"},
        )

        self.assertEqual(response.status_code, 404)

    def test_llm_health_endpoint_returns_status(self):
        with patch(
            "app.api.v1.endpoints.documentos.rag_service.llm_service.health",
            return_value={
                "available": True,
                "host": "http://localhost:11434",
                "model": "llama3.1:8b",
                "model_available": True,
                "models": ["llama3.1:8b"],
            },
        ):
            response = self.client.get("/api/documentos/llm/health", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["model_available"])


if __name__ == "__main__":
    unittest.main()
