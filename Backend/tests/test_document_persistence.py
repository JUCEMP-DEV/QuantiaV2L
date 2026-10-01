import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.core.config import settings
from app.core.document_auth import create_access_token, decode_access_token
from app.services.document_repository_service import LocalDocumentRepository, create_document_repository
from app.services.document_policy_service import cleanup_expired_documents
from app.services.document_storage_service import LocalDocumentStorage, create_document_storage
from app.services.vector_store_service import LocalVectorStore, VectorChunk, create_vector_store


class DocumentAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.original_secret = settings.auth_token_secret
        self.original_ttl = settings.auth_token_ttl_seconds
        settings.auth_token_secret = "test-secret-with-at-least-32-characters"
        settings.auth_token_ttl_seconds = 300

    def tearDown(self):
        settings.auth_token_secret = self.original_secret
        settings.auth_token_ttl_seconds = self.original_ttl

    def test_token_round_trip_preserves_verified_owner(self):
        with patch("app.core.document_auth.time.time", return_value=1000):
            token = create_access_token("user-1", "USER@example.com")
        with patch("app.core.document_auth.time.time", return_value=1100):
            principal = decode_access_token(token or "")

        self.assertEqual(principal.user_id, "user-1")
        self.assertEqual(principal.email, "user@example.com")

    def test_token_rejects_tampering_and_expiration(self):
        with patch("app.core.document_auth.time.time", return_value=1000):
            token = create_access_token("user-1", "user@example.com") or ""

        with self.assertRaises(HTTPException):
            decode_access_token(token[:-1] + ("a" if token[-1] != "a" else "b"))
        with patch("app.core.document_auth.time.time", return_value=1400):
            with self.assertRaises(HTTPException):
                decode_access_token(token)


class LocalDocumentPersistenceTests(unittest.TestCase):
    def _record(self, document_id: str = "doc-1", user_id: str = "user-1"):
        return {
            "id": document_id,
            "user_id": user_id,
            "status": "uploaded",
            "original_file_name": "documento.txt",
        }

    def test_repository_enforces_owner_on_read_update_and_delete(self):
        repository = LocalDocumentRepository()
        repository.create(self._record())

        self.assertIsNone(repository.get("doc-1", "user-2"))
        with self.assertRaises(KeyError):
            repository.update("doc-1", "user-2", {"status": "ready"})
        self.assertIsNone(repository.delete("doc-1", "user-2"))
        self.assertIsNotNone(repository.get("doc-1", "user-1"))

    def test_repository_persists_lifecycle_fields(self):
        repository = LocalDocumentRepository()
        created = repository.create(self._record())
        updated = repository.update(
            "doc-1",
            "user-1",
            {"status": "ready", "chunk_count": 3, "embedding_model": "model-v1"},
        )

        self.assertEqual(created["status"], "uploaded")
        self.assertEqual(updated["status"], "ready")
        self.assertEqual(updated["chunk_count"], 3)
        self.assertIn("updated_at", updated)

    def test_local_storage_namespaces_same_filename_by_document_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "source.txt"
            source.write_text("contenido", encoding="utf-8")
            storage = LocalDocumentStorage(root / "stored")

            first = storage.save(
                source,
                document_id="doc-1",
                original_file_name="repetido.txt",
                content_type="text/plain",
            )
            second = storage.save(
                source,
                document_id="doc-2",
                original_file_name="repetido.txt",
                content_type="text/plain",
            )

            self.assertNotEqual(first.object_path, second.object_path)
            self.assertTrue((root / "stored" / first.object_path).exists())
            self.assertTrue((root / "stored" / second.object_path).exists())

    def test_factories_reject_unknown_backends(self):
        with self.assertRaises(ValueError):
            create_document_repository("desconocido")
        with self.assertRaises(ValueError):
            create_document_storage("desconocido")
        with self.assertRaises(ValueError):
            create_vector_store("desconocido")
        self.assertIsInstance(create_document_repository("local"), LocalDocumentRepository)
        self.assertIsInstance(create_vector_store("local"), LocalVectorStore)

    def test_retention_cleanup_removes_record_file_and_chunks(self):
        original_retention = settings.document_retention_days
        original_failed_retention = settings.document_failed_retention_hours
        try:
            settings.document_retention_days = 30
            settings.document_failed_retention_hours = 24
            now = datetime(2026, 8, 11, tzinfo=timezone.utc)
            old = (now - timedelta(days=31)).isoformat()
            repository = LocalDocumentRepository()
            vector_store = LocalVectorStore()
            with tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                source = root / "source.txt"
                source.write_text("contenido", encoding="utf-8")
                storage = LocalDocumentStorage(root / "stored")
                stored = storage.save(
                    source,
                    document_id="doc-old",
                    original_file_name="documento.txt",
                    content_type="text/plain",
                )
                repository.create(
                    {
                        **self._record("doc-old"),
                        "storage_bucket": stored.bucket,
                        "storage_object_path": stored.object_path,
                        "size_bytes": 9,
                        "file_checksum": "a" * 64,
                        "created_at": old,
                        "updated_at": old,
                    }
                )
                vector_store.upsert_chunks(
                    [
                        VectorChunk(
                            document_id="doc-old",
                            chunk_id="doc-old-0",
                            content="contenido",
                            embedding=[1.0],
                            metadata={},
                        )
                    ]
                )

                result = cleanup_expired_documents(
                    repository,
                    storage,
                    vector_store,
                    user_id="user-1",
                    now=now,
                )

                self.assertEqual(result.deleted, 1)
                self.assertEqual(result.failed, 0)
                self.assertIsNone(repository.get("doc-old", "user-1"))
                self.assertEqual(vector_store.list_chunks("doc-old"), [])
                self.assertFalse((root / "stored" / stored.object_path).exists())
        finally:
            settings.document_retention_days = original_retention
            settings.document_failed_retention_hours = original_failed_retention


if __name__ == "__main__":
    unittest.main()
