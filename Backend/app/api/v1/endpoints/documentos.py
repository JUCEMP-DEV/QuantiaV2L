from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.core.config import settings
from app.core.document_auth import DocumentPrincipal, get_document_principal
from app.core.supabase_client import get_supabase_admin_client
from app.schemas.documentos import (
    DocumentoAskRequest,
    DocumentoAskResponse,
    DocumentoDeleteResponse,
    DocumentoIndexResponse,
    DocumentoListItem,
    DocumentoListResponse,
    DocumentoQueryRequest,
    DocumentoQueryResponse,
    DocumentoUploadResponse,
    LLMHealthResponse,
)
from app.services.document_repository_service import (
    DocumentRepository,
    create_document_repository,
)
from app.services.document_policy_service import (
    DocumentDuplicateError,
    DocumentPageLimitError,
    DocumentQuotaError,
    cleanup_expired_documents,
    enforce_upload_policy,
    inspect_document,
)
from app.services.document_service import DocumentService
from app.services.document_storage_service import (
    DocumentStorage,
    create_document_storage,
)
from app.services.llm_service import LLMServiceError
from app.services.ocr_service import OCRDependencyError, OCRServiceError
from app.services.rag_service import RAGService

from typing import Any, Literal

from app.prompts.quantia_extraction_prompt import (
    QUANTIA_EXTRACTION_PROMPT,
)
from app.prompts.quantia_space_localization_prompt import (
    build_quantia_space_localization_prompt,
)
from app.schemas.gemini_extraction_transport import (
    get_gemini_extraction_transport_schema,
)
from app.schemas.gemini_space_localization_transport import (
    get_gemini_space_localization_schema,
)
from app.schemas.quantia_spatial_contract import (
    QuantiaSpatialContract,
)
from app.services.cached_gemini_vision_provider import (
    get_cached_gemini_vision_provider,
)
from app.legacy.quantia_spatial.quantia_spatial_reconstruction_service import (
    BaseLayerDescriptor,
    QuantiaSpatialReconstructionService,
)
from app.services.plan_document_analyzer import PlanDocumentAnalyzer

router = APIRouter(prefix="/documentos", tags=["documentos"])
service = DocumentService()
repository: DocumentRepository = create_document_repository()
storage: DocumentStorage = create_document_storage()
rag_service = RAGService()


def _create_spatial_reconstruction_service() -> QuantiaSpatialReconstructionService:
    return QuantiaSpatialReconstructionService(
        extraction_prompt=QUANTIA_EXTRACTION_PROMPT,
        extraction_response_json_schema=get_gemini_extraction_transport_schema(),
        localization_prompt_builder=build_quantia_space_localization_prompt,
        localization_response_json_schema=get_gemini_space_localization_schema(),
        vision_provider=get_cached_gemini_vision_provider(),
    )


ALLOWED_EXTENSIONS = (
    service.ocr_service.text_extensions
    | service.ocr_service.image_extensions
    | {".pdf"}
)
CONTENT_TYPES_BY_EXTENSION = {
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".json": {"application/json", "text/plain"},
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".bmp": {"image/bmp", "image/x-ms-bmp"},
    ".tif": {"image/tiff"},
    ".tiff": {"image/tiff"},
}
UPLOAD_CHUNK_SIZE = 1024 * 1024
PROCESSING_VERSION = "ocr-rag-v1"
ALLOWED_MODULE_KEYS = {
    "preliminares",
    "cimentacion",
    "estructura",
    "albanileria",
    "instalaciones",
    "acabados",
    "complementarios_y_equipamiento",
}


async def _process_uploaded_document(
    file: UploadFile,
    *,
    principal: DocumentPrincipal,
    quote_id: str | None = None,
    module_key: str | None = None,
) -> DocumentoUploadResponse:
    _cleanup_user_documents(principal.user_id)
    document_id = str(uuid4())
    original_file_name = Path(file.filename or "documento").name
    normalized_quote_id = _validate_quote_ownership(quote_id, principal)
    normalized_module_key = _validate_module_key(module_key)
    extension = Path(original_file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de archivo no soportado: {extension or 'sin extension'}.",
        )
    content_type = _validate_content_type(extension, file.content_type)

    temp_path: Path | None = None
    stored = None
    record_created = False
    try:
        temp_path, size_bytes, checksum = await _stage_upload(
            file, document_id, extension
        )
        try:
            inspection = inspect_document(temp_path, extension)
            enforce_upload_policy(
                repository,
                user_id=principal.user_id,
                checksum=checksum,
                incoming_size=size_bytes,
            )
        except DocumentDuplicateError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Documento duplicado. document_id existente: {exc.document_id}",
            ) from exc
        except DocumentQuotaError as exc:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
            ) from exc
        except DocumentPageLimitError as exc:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
            ) from exc
        stored = storage.save(
            temp_path,
            document_id=document_id,
            original_file_name=original_file_name,
            content_type=content_type,
        )
        record = repository.create(
            {
                "id": document_id,
                "user_id": principal.user_id,
                "quote_id": normalized_quote_id,
                "module_key": normalized_module_key,
                "original_file_name": original_file_name,
                "storage_bucket": stored.bucket,
                "storage_object_path": stored.object_path,
                "mime_type": content_type,
                "size_bytes": size_bytes,
                "file_checksum": checksum,
                "status": "uploaded",
                "ocr_text": "",
                "ocr_metadata": {"source_page_count": inspection.page_count},
                "embedding_model": settings.embedding_model,
                "processing_version": PROCESSING_VERSION,
                "chunk_count": 0,
                "error_detail": None,
            }
        )
        record_created = True
        repository.update(
            document_id,
            principal.user_id,
            {"status": "ocr_processing", "error_detail": None},
        )
        ocr_result = service.process_file(temp_path)
        record = repository.update(
            document_id,
            principal.user_id,
            {
                "status": "ocr_completed",
                "ocr_text": ocr_result.get("text", ""),
                "ocr_metadata": {
                    **dict(ocr_result.get("metadata") or {}),
                    "source_page_count": inspection.page_count,
                    "file_name": original_file_name,
                    "original_file_name": original_file_name,
                    "file_checksum": checksum,
                },
                "error_detail": None,
            },
        )
        return _to_upload_response(record)
    except OCRServiceError as exc:
        if record_created:
            try:
                repository.update(
                    document_id,
                    principal.user_id,
                    {"status": "failed", "error_detail": str(exc)[:2000]},
                )
            except Exception:
                pass
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if isinstance(exc, OCRDependencyError)
            else 422
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except HTTPException:
        if stored is not None and not record_created:
            storage.delete(bucket=stored.bucket, object_path=stored.object_path)
        raise
    except Exception as exc:
        if record_created:
            try:
                repository.update(
                    document_id,
                    principal.user_id,
                    {"status": "failed", "error_detail": str(exc)[:2000]},
                )
            except Exception:
                pass
        elif stored is not None:
            try:
                storage.delete(bucket=stored.bucket, object_path=stored.object_path)
            except Exception:
                pass
        if (
            "documents_user_checksum_uidx" in str(exc)
            or "duplicate key" in str(exc).lower()
        ):
            raise HTTPException(
                status_code=409,
                detail="El usuario ya cargo un documento con el mismo contenido.",
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        await file.close()


async def _stage_upload(
    file: UploadFile, document_id: str, extension: str
) -> tuple[Path, int, str]:
    service.storage_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size_bytes = 0
    with NamedTemporaryFile(
        mode="wb",
        prefix=f"upload-{document_id}-",
        suffix=extension,
        dir=service.storage_dir,
        delete=False,
    ) as buffer:
        temp_path = Path(buffer.name)
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > settings.document_max_upload_bytes:
                buffer.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"El archivo supera el limite de {settings.document_max_upload_bytes} bytes.",
                )
            digest.update(chunk)
            buffer.write(chunk)
    if size_bytes == 0:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="El archivo esta vacio.")
    return temp_path, size_bytes, digest.hexdigest()


def _get_document_record(
    document_id: str, principal: DocumentPrincipal
) -> dict[str, Any]:
    record = repository.get(document_id, principal.user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return record


def _cleanup_user_documents(user_id: str) -> None:
    cleanup_expired_documents(
        repository,
        storage,
        rag_service.vector_store,
        user_id=user_id,
    )


def _index_document(
    record: dict[str, Any], principal: DocumentPrincipal
) -> dict[str, Any]:
    document_id = str(record["id"])
    repository.update(
        document_id, principal.user_id, {"status": "indexing", "error_detail": None}
    )
    try:
        rag_service.vector_store.clear(document_id=document_id)
        result = rag_service.index_document(
            str(record.get("ocr_text") or ""),
            document_id=document_id,
            metadata={
                "file_name": record.get("original_file_name"),
                "user_id": principal.user_id,
                "quote_id": record.get("quote_id"),
                "module_key": record.get("module_key"),
                "file_checksum": record.get("file_checksum"),
                "embedding_model": settings.embedding_model,
                "processing_version": PROCESSING_VERSION,
            },
        )
        chunk_count = int(result.get("chunk_count") or 0)
        if chunk_count <= 0:
            raise ValueError("El documento no produjo chunks indexables.")
        repository.update(
            document_id,
            principal.user_id,
            {
                "status": "ready",
                "chunk_count": chunk_count,
                "embedding_model": settings.embedding_model,
                "processing_version": PROCESSING_VERSION,
                "error_detail": None,
            },
        )
        return result
    except Exception as exc:
        repository.update(
            document_id,
            principal.user_id,
            {"status": "failed", "chunk_count": 0, "error_detail": str(exc)[:2000]},
        )
        raise


def _to_upload_response(record: dict[str, Any]) -> DocumentoUploadResponse:
    return DocumentoUploadResponse(
        status=record.get("status") or "failed",
        document_id=str(record.get("id") or ""),
        user_id=str(record.get("user_id") or ""),
        quote_id=record.get("quote_id"),
        module_key=record.get("module_key"),
        file_name=str(record.get("original_file_name") or "documento"),
        text=str(record.get("ocr_text") or ""),
        metadata=dict(record.get("ocr_metadata") or {}),
        indexed=record.get("status") == "ready",
        chunk_count=int(record.get("chunk_count") or 0),
        error_detail=record.get("error_detail"),
    )


def _to_list_item(record: dict[str, Any]) -> DocumentoListItem:
    return DocumentoListItem(
        document_id=str(record.get("id") or ""),
        user_id=str(record.get("user_id") or ""),
        quote_id=record.get("quote_id"),
        module_key=record.get("module_key"),
        file_name=str(record.get("original_file_name") or "documento"),
        status=record.get("status") or "failed",
        metadata=dict(record.get("ocr_metadata") or {}),
        indexed=record.get("status") == "ready",
        chunk_count=int(record.get("chunk_count") or 0),
        error_detail=record.get("error_detail"),
        created_at=_optional_text(record.get("created_at")),
        updated_at=_optional_text(record.get("updated_at")),
    )


def _optional_text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _validate_quote_ownership(
    value: str | None, principal: DocumentPrincipal
) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    try:
        quote_id = str(UUID(normalized))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="quote_id debe ser un UUID valido."
        ) from exc

    if settings.document_persistence_backend == "supabase":
        result = (
            get_supabase_admin_client()
            .table("app_cotizaciones")
            .select("id")
            .eq("id", quote_id)
            .eq("user_id", principal.user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Cotizacion no encontrada para el usuario autenticado.",
            )
    return quote_id


def _validate_module_key(value: str | None) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    if normalized not in ALLOWED_MODULE_KEYS:
        raise HTTPException(
            status_code=422,
            detail="module_key no corresponde a un modulo de vivienda soportado.",
        )
    return normalized


def _validate_content_type(extension: str, declared: str | None) -> str:
    allowed = CONTENT_TYPES_BY_EXTENSION.get(extension, set())
    normalized = str(declared or "").split(";", maxsplit=1)[0].strip().lower()
    if (
        normalized
        and normalized not in allowed
        and normalized != "application/octet-stream"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="El MIME declarado no coincide con la extension del archivo.",
        )
    return sorted(allowed)[0] if allowed else "application/octet-stream"


@router.post("/upload", response_model=DocumentoUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    quote_id: str | None = Form(default=None),
    module_key: str | None = Form(default=None),
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    return await _process_uploaded_document(
        file,
        principal=principal,
        quote_id=quote_id,
        module_key=module_key,
    )


@router.post("/ocr/test", response_model=DocumentoUploadResponse)
async def test_ocr_document(
    file: UploadFile = File(...),
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    return await _process_uploaded_document(file, principal=principal)


@router.get("", response_model=DocumentoListResponse)
async def list_documents(
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    _cleanup_user_documents(principal.user_id)
    return DocumentoListResponse(
        documents=[
            _to_list_item(record) for record in repository.list(principal.user_id)
        ]
    )


@router.post("/{document_id}/procesar", response_model=DocumentoIndexResponse)
async def process_document_for_rag(
    document_id: str,
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    try:
        return DocumentoIndexResponse(
            **_index_document(_get_document_record(document_id, principal), principal)
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/{document_id}/analizar-plano",
    response_model=QuantiaSpatialContract,
)
def analyze_plan_document(
    document_id: str,
    page_number: int = 1,
    pdf_render_scale: float | None = None,
    ocr_strategy: Literal[
        "auto",
        "always",
    ] = "auto",
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    record = _get_document_record(
        document_id,
        principal,
    )

    mime_type = str(record.get("mime_type") or "").strip().lower()

    if mime_type not in {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }:
        raise HTTPException(
            status_code=415,
            detail=("El análisis arquitectónico " "solo soporta PDF, JPG y PNG."),
        )

    if page_number < 1:
        raise HTTPException(
            status_code=422,
            detail="page_number debe ser mayor o igual a 1.",
        )

    if mime_type == "application/pdf" and pdf_render_scale is None:
        raise HTTPException(
            status_code=422,
            detail=("pdf_render_scale es obligatorio " "para documentos PDF."),
        )

    if pdf_render_scale is not None and pdf_render_scale <= 0:
        raise HTTPException(
            status_code=422,
            detail="pdf_render_scale debe ser mayor que cero.",
        )

    try:
        document_bytes = storage.read_bytes(
            bucket=str(record.get("storage_bucket") or ""),
            object_path=str(record.get("storage_object_path") or ""),
        )

        base_layer = BaseLayerDescriptor(
            id=(f"{document_id}" f"-PAGE-{page_number}"),
            nombre=str(record.get("original_file_name") or "documento"),
            referencia=None,
            visible=True,
            bloqueado=True,
            ocultable=True,
            bloqueable=True,
        )

        reconstruction_service = _create_spatial_reconstruction_service()

        result = reconstruction_service.reconstruct_page(
            document_bytes=document_bytes,
            mime_type=mime_type,
            page_number=page_number,
            base_layer=base_layer,
            pdf_render_scale=pdf_render_scale,
            ocr_strategy=ocr_strategy,
            thickness_evidence=None,
            domain_rule_targets=None,
        )

        return result.contract

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Archivo original no encontrado.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get("/{document_id}/plano-base")
def get_plan_base_raster(
    document_id: str,
    page_number: int = 1,
    pdf_render_scale: float | None = None,
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    """Return the same canonical raster coordinate space used by 03.2."""
    record = _get_document_record(document_id, principal)
    mime_type = str(record.get("mime_type") or "").strip().lower()

    if mime_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(
            status_code=415,
            detail="El documento no admite una capa raster de plano.",
        )

    if page_number < 1:
        raise HTTPException(
            status_code=422,
            detail="page_number debe ser mayor o igual a 1.",
        )

    if mime_type == "application/pdf" and pdf_render_scale is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "pdf_render_scale es obligatorio para reproducir "
                "el raster canónico del análisis."
            ),
        )

    if pdf_render_scale is not None and pdf_render_scale <= 0:
        raise HTTPException(
            status_code=422,
            detail="pdf_render_scale debe ser mayor que cero.",
        )

    try:
        document_bytes = storage.read_bytes(
            bucket=str(record.get("storage_bucket") or ""),
            object_path=str(record.get("storage_object_path") or ""),
        )
        analyzer = PlanDocumentAnalyzer()
        raster_pages = analyzer.prepare_raster_pages(
            document_bytes=document_bytes,
            mime_type=mime_type,
            render_scale=(
                float(pdf_render_scale)
                if mime_type == "application/pdf"
                else 1.0
            ),
        )
        raster = next(
            (item for item in raster_pages if item.page == page_number),
            None,
        )

        if raster is None:
            raise HTTPException(
                status_code=404,
                detail="La página solicitada no existe en el documento.",
            )

        return Response(
            content=raster.image_bytes,
            media_type=raster.mime_type,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Archivo original no encontrado.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{document_id}/preguntar", response_model=DocumentoAskResponse)
async def ask_document(
    document_id: str,
    payload: DocumentoAskRequest,
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    try:
        record = _get_document_record(document_id, principal)
        if record.get("status") != "ready":
            _index_document(record, principal)
        result = rag_service.answer_from_retrieval(
            payload.query, document_id=document_id, top_k=payload.top_k
        )
        return DocumentoAskResponse(**result)
    except HTTPException:
        raise
    except LLMServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{document_id}", response_model=DocumentoDeleteResponse)
async def delete_document(
    document_id: str,
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    record = _get_document_record(document_id, principal)
    try:
        rag_service.vector_store.clear(document_id=document_id)
        storage.delete(
            bucket=str(record.get("storage_bucket") or ""),
            object_path=str(record.get("storage_object_path") or ""),
        )
        deleted = repository.delete(document_id, principal.user_id)
        if deleted is None:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
    except HTTPException:
        raise
    except Exception as exc:
        try:
            repository.update(
                document_id,
                principal.user_id,
                {
                    "status": "failed",
                    "error_detail": f"Fallo al eliminar: {exc}"[:2000],
                },
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail="No se pudo eliminar completamente el documento."
        ) from exc
    return DocumentoDeleteResponse(document_id=document_id)


@router.get("/llm/health", response_model=LLMHealthResponse)
async def llm_health(principal: DocumentPrincipal = Depends(get_document_principal)):
    return LLMHealthResponse(**rag_service.llm_service.health())


@router.post("/query", response_model=DocumentoQueryResponse)
async def query_document(
    payload: DocumentoQueryRequest,
    principal: DocumentPrincipal = Depends(get_document_principal),
):
    try:
        result = rag_service.answer_with_context(payload.text, payload.query)
        return DocumentoQueryResponse(**result)
    except LLMServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
