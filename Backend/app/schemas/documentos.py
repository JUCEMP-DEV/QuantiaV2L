from typing import Any

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class DocumentoChunk(BaseModel):
    document_id: str = Field(..., description="Identificador interno del documento")
    chunk_id: str = Field(..., description="Identificador del fragmento")
    content: str = Field(..., description="Contenido textual del fragmento")
    embedding: list[float] = Field(default_factory=list, description="Vector del fragmento")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata asociada")


class DocumentoMatch(BaseModel):
    document_id: str = Field(..., description="Identificador interno del documento")
    chunk_id: str = Field(..., description="Identificador del fragmento recuperado")
    content: str = Field(..., description="Contenido recuperado")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata del fragmento")
    score: float = Field(..., description="Puntaje de similitud")


class DocumentoUploadResponse(BaseModel):
    status: Literal["uploaded", "ocr_processing", "ocr_completed", "indexing", "ready", "failed"]
    document_id: str = Field(..., description="Identificador estable del documento")
    user_id: str = Field(..., description="Propietario del documento")
    quote_id: str | None = Field(default=None, description="Cotizacion asociada")
    module_key: str | None = Field(default=None, description="Modulo de vivienda asociado")
    file_name: str = Field(..., description="Nombre del archivo")
    text: str = Field(..., description="Texto extraido o leido")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata del procesamiento OCR")
    indexed: bool = Field(default=False, description="Indica si el documento ya fue indexado para RAG")
    chunk_count: int = Field(default=0, ge=0)
    error_detail: str | None = None


class DocumentoListItem(BaseModel):
    document_id: str = Field(..., description="Identificador interno del documento")
    user_id: str = Field(..., description="Propietario del documento")
    quote_id: str | None = None
    module_key: str | None = None
    file_name: str = Field(..., description="Nombre del archivo")
    status: Literal["uploaded", "ocr_processing", "ocr_completed", "indexing", "ready", "failed"]
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata del procesamiento OCR")
    indexed: bool = Field(default=False, description="Indica si el documento ya fue indexado para RAG")
    chunk_count: int = Field(default=0, ge=0, description="Cantidad de chunks indexados")
    error_detail: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DocumentoListResponse(BaseModel):
    documents: list[DocumentoListItem] = Field(default_factory=list, description="Documentos procesados")


class DocumentoDeleteResponse(BaseModel):
    ok: bool = True
    document_id: str


class DocumentoIndexResponse(BaseModel):
    document_id: str = Field(..., description="Identificador interno del documento")
    chunk_count: int = Field(..., ge=0, description="Cantidad de chunks indexados")
    chunks: list[DocumentoChunk] = Field(default_factory=list, description="Chunks indexados")


class DocumentoQueryRequest(BaseModel):
    text: str = Field(..., description="Texto base o contexto del documento")
    query: str = Field(..., description="Pregunta que se desea responder")

    @field_validator("text", "query")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El campo no puede estar vacio.")
        return value.strip()


class DocumentoAskRequest(BaseModel):
    query: str = Field(..., description="Pregunta que se desea responder")
    top_k: int | None = Field(default=None, ge=1, le=20, description="Cantidad maxima de chunks a recuperar")

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("La pregunta no puede estar vacia.")
        return value.strip()


class DocumentoQueryResponse(BaseModel):
    query: str = Field(..., description="Pregunta original")
    chunks: list[str] = Field(default_factory=list, description="Chunks generados para el contexto")
    context: str = Field(..., description="Contexto recuperado")
    answer: str = Field(..., description="Respuesta generada")


class DocumentoAskResponse(BaseModel):
    query: str = Field(..., description="Pregunta original")
    document_id: str | None = Field(default=None, description="Documento consultado")
    matches: list[DocumentoMatch] = Field(default_factory=list, description="Chunks recuperados")
    context: str = Field(..., description="Contexto recuperado")
    prompt: str = Field(..., description="Prompt enviado al modelo")
    answer: str = Field(..., description="Respuesta generada")


class LLMHealthResponse(BaseModel):
    available: bool = Field(..., description="Indica si Ollama responde")
    host: str = Field(..., description="Host configurado para Ollama")
    model: str = Field(..., description="Modelo configurado para generacion")
    model_available: bool = Field(..., description="Indica si el modelo configurado esta descargado")
    models: list[str] = Field(default_factory=list, description="Modelos disponibles reportados por Ollama")
    error: str | None = Field(default=None, description="Detalle del error cuando Ollama no responde")
