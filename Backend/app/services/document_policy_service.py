from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pypdf import PdfReader
from PIL import Image

from app.core.config import settings
from app.services.document_repository_service import DocumentRepository
from app.services.document_storage_service import DocumentStorage
from app.services.vector_store_service import VectorStore


@dataclass(frozen=True)
class DocumentInspection:
    page_count: int


@dataclass(frozen=True)
class DocumentCleanupResult:
    deleted: int
    failed: int


IMAGE_FORMATS_BY_EXTENSION = {
    ".png": {"PNG"},
    ".jpg": {"JPEG"},
    ".jpeg": {"JPEG"},
    ".bmp": {"BMP"},
    ".tif": {"TIFF"},
    ".tiff": {"TIFF"},
}


def inspect_document(path: Path, extension: str) -> DocumentInspection:
    if extension in {".txt", ".md", ".json"}:
        return _inspect_text(path, extension)
    if extension == ".pdf":
        return _inspect_pdf(path)
    if extension in IMAGE_FORMATS_BY_EXTENSION:
        return _inspect_image(path, extension)
    raise ValueError("Tipo de archivo no soportado.")


def enforce_upload_policy(
    repository: DocumentRepository,
    *,
    user_id: str,
    checksum: str,
    incoming_size: int,
) -> None:
    if settings.document_reject_duplicates:
        duplicate = repository.find_by_checksum(user_id, checksum)
        if duplicate is not None:
            raise DocumentDuplicateError(str(duplicate.get("id") or ""))

    document_count, used_bytes = repository.usage(user_id)
    if document_count >= settings.document_max_user_documents:
        raise DocumentQuotaError("Se alcanzo la cantidad maxima de documentos permitidos para el usuario.")
    if used_bytes + incoming_size > settings.document_max_user_bytes:
        raise DocumentQuotaError("La carga supera la cuota total de almacenamiento del usuario.")


def cleanup_expired_documents(
    repository: DocumentRepository,
    storage: DocumentStorage,
    vector_store: VectorStore,
    *,
    user_id: str,
    now: datetime | None = None,
) -> DocumentCleanupResult:
    current_time = now or datetime.now(timezone.utc)
    retention_before = _cutoff(current_time, days=settings.document_retention_days)
    failed_before = _cutoff(current_time, hours=settings.document_failed_retention_hours)
    if retention_before is None and failed_before is None:
        return DocumentCleanupResult(deleted=0, failed=0)

    candidates = repository.list_cleanup_candidates(
        user_id,
        retention_before=retention_before,
        failed_before=failed_before,
        limit=settings.document_cleanup_batch_size,
    )
    deleted = 0
    failed = 0
    for record in candidates:
        document_id = str(record.get("id") or "")
        try:
            vector_store.clear(document_id=document_id)
            storage.delete(
                bucket=str(record.get("storage_bucket") or ""),
                object_path=str(record.get("storage_object_path") or ""),
            )
            if repository.delete(document_id, user_id) is not None:
                deleted += 1
        except Exception:
            failed += 1
    return DocumentCleanupResult(deleted=deleted, failed=failed)


class DocumentDuplicateError(ValueError):
    def __init__(self, document_id: str):
        super().__init__("El usuario ya cargo un documento con el mismo contenido.")
        self.document_id = document_id


class DocumentQuotaError(ValueError):
    pass


def _inspect_text(path: Path, extension: str) -> DocumentInspection:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("El archivo de texto no contiene UTF-8 valido.") from exc
    if "\x00" in text:
        raise ValueError("El archivo declarado como texto contiene datos binarios.")
    if extension == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("El archivo JSON no tiene una estructura valida.") from exc
    return DocumentInspection(page_count=1)


def _inspect_pdf(path: Path) -> DocumentInspection:
    with path.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise ValueError("La firma del archivo no corresponde a un PDF.")
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError("No se aceptan documentos PDF cifrados.")
        page_count = len(reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("El archivo PDF no tiene una estructura valida.") from exc
    return _validate_page_count(page_count)


def _inspect_image(path: Path, extension: str) -> DocumentInspection:
    try:
        with Image.open(path) as image:
            detected_format = str(image.format or "").upper()
            if detected_format not in IMAGE_FORMATS_BY_EXTENSION[extension]:
                raise ValueError("La firma de la imagen no coincide con su extension.")
            page_count = int(getattr(image, "n_frames", 1) or 1)
            image.verify()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("El archivo no contiene una imagen valida.") from exc
    return _validate_page_count(page_count)


def _validate_page_count(page_count: int) -> DocumentInspection:
    if page_count <= 0:
        raise ValueError("El documento no contiene paginas.")
    if page_count > settings.document_max_pages:
        raise DocumentPageLimitError(page_count)
    return DocumentInspection(page_count=page_count)


class DocumentPageLimitError(ValueError):
    def __init__(self, page_count: int):
        super().__init__(f"El documento contiene {page_count} paginas y supera el limite permitido.")
        self.page_count = page_count


def _cutoff(now: datetime, *, days: int = 0, hours: int = 0) -> datetime | None:
    if days <= 0 and hours <= 0:
        return None
    return now - timedelta(days=days, hours=hours)
