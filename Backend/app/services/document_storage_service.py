from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.core.supabase_client import get_supabase_admin_client


@dataclass(frozen=True)
class StoredDocument:
    bucket: str
    object_path: str


class DocumentStorage(Protocol):
    def save(
        self,
        source_path: Path,
        *,
        document_id: str,
        original_file_name: str,
        content_type: str,
    ) -> StoredDocument: ...

    def delete(self, *, bucket: str, object_path: str) -> None: ...


class LocalDocumentStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        source_path: Path,
        *,
        document_id: str,
        original_file_name: str,
        content_type: str,
    ) -> StoredDocument:
        safe_name = Path(original_file_name).name or "documento"
        object_path = f"{document_id}/{safe_name}"
        destination = self.root / document_id / safe_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != destination.resolve():
            shutil.copy2(source_path, destination)
        return StoredDocument(bucket="local", object_path=object_path)

    def read_bytes(
        self,
        *,
        bucket: str,
        object_path: str,
    ) -> bytes: ...

    def read_bytes(
        self,
        *,
        bucket: str,
        object_path: str,
    ) -> bytes:
        candidate = (
            self.root / object_path
        ).resolve()

        root = self.root.resolve()

        if root not in candidate.parents:
            raise ValueError(
                "Ruta local de documento invalida."
            )

        if not candidate.is_file():
            raise FileNotFoundError(
                "Documento local no encontrado."
            )

        return candidate.read_bytes()
    
    
    def delete(self, *, bucket: str, object_path: str) -> None:
        candidate = (self.root / object_path).resolve()
        root = self.root.resolve()
        if root not in candidate.parents:
            raise ValueError("Ruta local de documento invalida.")
        if candidate.exists():
            candidate.unlink()
        parent = candidate.parent
        if parent != root and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


class SupabaseDocumentStorage:
    def __init__(self, bucket: str | None = None) -> None:
        self.bucket = bucket or settings.document_storage_bucket

    def save(
        self,
        source_path: Path,
        *,
        document_id: str,
        original_file_name: str,
        content_type: str,
    ) -> StoredDocument:
        safe_name = Path(original_file_name).name or "documento"
        object_path = f"{document_id}/{safe_name}"
        bucket = get_supabase_admin_client().storage.from_(self.bucket)
        bucket.upload(
            object_path,
            source_path,
            {"content-type": content_type or "application/octet-stream", "upsert": "false"},
        )
        return StoredDocument(bucket=self.bucket, object_path=object_path)

    def read_bytes(
        self,
        *,
        bucket: str,
        object_path: str,
    ) -> bytes:
        response = (
            get_supabase_admin_client()
            .storage
            .from_(bucket or self.bucket)
            .download(object_path)
        )

        if not isinstance(
            response,
            (bytes, bytearray),
        ):
            raise RuntimeError(
                "Supabase no devolvio bytes "
                "para el documento."
            )

        return bytes(response)


    def delete(self, *, bucket: str, object_path: str) -> None:
        get_supabase_admin_client().storage.from_(bucket or self.bucket).remove([object_path])


def create_document_storage(backend: str | None = None) -> DocumentStorage:
    selected = (backend or settings.document_persistence_backend).strip().lower()
    if selected == "local":
        return LocalDocumentStorage()
    if selected == "supabase":
        return SupabaseDocumentStorage()
    raise ValueError(f"DOCUMENT_PERSISTENCE_BACKEND no soportado: {selected}")
