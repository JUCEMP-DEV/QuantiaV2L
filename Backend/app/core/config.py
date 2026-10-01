from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(BACKEND_DIR / ".env.local"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================================================
    # APLICACIÓN
    # =========================================================

    project_name: str = "Quantia Backend"
    api_v1_prefix: str = "/api"
    debug: bool = False

    # =========================================================
    # SUPABASE
    # =========================================================

    supabase_url: str = Field(
        default="",
        alias="SUPABASE_URL",
    )

    supabase_anon_key: str = Field(
        default="",
        alias="SUPABASE_ANON_KEY",
    )

    supabase_service_role_key: str = Field(
        default="",
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )

    supabase_key: str = Field(
        default="",
        alias="SUPABASE_KEY",
    )

    # =========================================================
    # OCR
    # =========================================================

    ocr_engine: str = Field(
        default="tesseract",
        alias="OCR_ENGINE",
    )

    tesseract_cmd: Path | None = Field(
        default=None,
        alias="TESSERACT_CMD",
    )

    tesseract_language: str = Field(
        default="eng",
        alias="TESSERACT_LANGUAGE",
    )

    tesseract_data_dir: Path | None = Field(
        default=None,
        alias="TESSERACT_DATA_DIR",
    )

    poppler_path: Path | None = Field(
        default=None,
        alias="POPPLER_PATH",
    )

    # =========================================================
    # EMBEDDINGS
    # =========================================================

    embedding_backend: str = Field(
        default="sentence_transformers",
        alias="EMBEDDING_BACKEND",
    )

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )

    embedding_dimension: int = Field(
        default=384,
        ge=1,
        alias="EMBEDDING_DIMENSION",
    )

    # =========================================================
    # DOCUMENTOS
    # =========================================================

    upload_dir: Path = Field(
        default=BACKEND_DIR / "tmp_documents",
        alias="UPLOAD_DIR",
    )

    document_persistence_backend: str = Field(
        default="local",
        alias="DOCUMENT_PERSISTENCE_BACKEND",
    )

    document_table_name: str = Field(
        default="documents",
        alias="DOCUMENT_TABLE_NAME",
    )

    document_storage_bucket: str = Field(
        default="quantia-documents",
        alias="DOCUMENT_STORAGE_BUCKET",
    )

    # Frontend y backend quedan alineados en 100 MB.
    document_max_upload_bytes: int = Field(
        default=100 * 1024 * 1024,
        ge=1024,
        alias="DOCUMENT_MAX_UPLOAD_BYTES",
    )

    document_max_pages: int = Field(
        default=100,
        ge=1,
        alias="DOCUMENT_MAX_PAGES",
    )

    document_max_user_documents: int = Field(
        default=100,
        ge=1,
        alias="DOCUMENT_MAX_USER_DOCUMENTS",
    )

    document_max_user_bytes: int = Field(
        default=500 * 1024 * 1024,
        ge=1024,
        alias="DOCUMENT_MAX_USER_BYTES",
    )

    document_reject_duplicates: bool = Field(
        default=True,
        alias="DOCUMENT_REJECT_DUPLICATES",
    )

    document_retention_days: int = Field(
        default=90,
        ge=0,
        alias="DOCUMENT_RETENTION_DAYS",
    )

    document_failed_retention_hours: int = Field(
        default=24,
        ge=0,
        alias="DOCUMENT_FAILED_RETENTION_HOURS",
    )

    document_cleanup_batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        alias="DOCUMENT_CLEANUP_BATCH_SIZE",
    )

    # =========================================================
    # AUTENTICACIÓN
    # =========================================================

    auth_token_secret: str = Field(
        default="",
        alias="AUTH_TOKEN_SECRET",
    )

    auth_token_ttl_seconds: int = Field(
        default=8 * 60 * 60,
        ge=60,
        alias="AUTH_TOKEN_TTL_SECONDS",
    )

    # =========================================================
    # VECTOR STORE / RAG
    # =========================================================

    vector_store_backend: str = Field(
        default="local",
        alias="VECTOR_STORE_BACKEND",
    )

    vector_table_name: str = Field(
        default="document_chunks",
        alias="VECTOR_TABLE_NAME",
    )

    rag_chunk_size: int = Field(
        default=150,
        ge=20,
        alias="RAG_CHUNK_SIZE",
    )

    rag_chunk_overlap: int = Field(
        default=30,
        ge=0,
        alias="RAG_CHUNK_OVERLAP",
    )

    rag_top_k: int = Field(
        default=3,
        alias="RAG_TOP_K",
    )

    # =========================================================
    # VISIÓN / ANÁLISIS MULTIMODAL
    # =========================================================
    #
    # Proveedor activo de Quantia para interpretación visual.
    #
    # Actualmente:
    #   Principal : Gemini 3.7 Flash
    #   Fallback  : Gemini 3.5 Flash
    #
    # El frontend NO conoce estos modelos.
    # La selección ocurre exclusivamente en Backend.
    # =========================================================

    vision_provider: str = Field(
        default="gemini_qwen",
        alias="VISION_PROVIDER",
    )

    gemini_api_key: str = Field(
        default="",
        alias="GEMINI_API_KEY",
    )

    gemini_primary_model: str = Field(
        default="gemini-3.7-flash",
        alias="GEMINI_PRIMARY_MODEL",
    )

    gemini_fallback_model: str = Field(
        default="gemini-3.5-flash",
        alias="GEMINI_FALLBACK_MODEL",
    )

    qwen_api_key: str = Field(
        default="",
        alias="QWEN_API_KEY",
        validation_alias=AliasChoices(
            "QWEN_API_KEY",
            "HF_TOKEN",
            "ApiKeyLlama",
        ),
    )

    qwen_primary_model: str = Field(
        default="Qwen/Qwen3.5-4B:featherless-ai",
        alias="QWEN_PRIMARY_MODEL",
    )

    qwen_fallback_model: str = Field(
        default="",
        alias="QWEN_FALLBACK_MODEL",
    )

    vision_cache_enabled: bool = Field(
        default=True,
        alias="VISION_CACHE_ENABLED",
    )

    vision_cache_dir: Path = Field(
        default=BACKEND_DIR / "cache" / "vision",
        alias="VISION_CACHE_DIR",
    )
    # =========================================================
    # OLLAMA
    # =========================================================
    #
    # Se conserva porque forma parte de la configuración
    # existente del backend.
    #
    # NO será utilizado como proveedor visual de 03.2.
    # =========================================================

    ollama_host: str = Field(
        default="http://127.0.0.1:11434",
        alias="OLLAMA_HOST",
    )

    ollama_model: str = Field(
        default="llama3.2:3b",
        alias="OLLAMA_MODEL",
    )

    ollama_context_length: int = Field(
        default=2048,
        ge=512,
        alias="OLLAMA_CONTEXT_LENGTH",
    )

    ollama_max_tokens: int = Field(
        default=64,
        ge=1,
        alias="OLLAMA_MAX_TOKENS",
    )

    ollama_timeout_seconds: float = Field(
        default=60.0,
        ge=1,
        alias="OLLAMA_TIMEOUT_SECONDS",
    )

    ollama_temperature: float = Field(
        default=0.2,
        alias="OLLAMA_TEMPERATURE",
    )

    # =========================================================
    # CORS
    # =========================================================

    backend_cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    backend_cors_origin_regex: str | None = Field(
        default=None,
        alias="BACKEND_CORS_ORIGIN_REGEX",
    )

    # =========================================================
    # VALIDADORES
    # =========================================================

    @field_validator(
        "backend_cors_origins",
        mode="before",
    )
    @classmethod
    def parse_cors_origins(cls, value):  # noqa: ANN001
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return []

            return [item.strip() for item in value.split(",") if item.strip()]

        return []

    @field_validator(
        "backend_cors_origin_regex",
        mode="before",
    )
    @classmethod
    def parse_cors_origin_regex(cls, value):  # noqa: ANN001
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            return value or None

        return None

    @field_validator(
        "debug",
        mode="before",
    )
    @classmethod
    def parse_debug(cls, value):  # noqa: ANN001
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {
                "1",
                "true",
                "yes",
                "on",
                "debug",
                "dev",
            }:
                return True

            if normalized in {
                "0",
                "false",
                "no",
                "off",
                "release",
                "prod",
                "production",
                "",
            }:
                return False

        return False

    @field_validator(
        "document_reject_duplicates",
        mode="before",
    )
    @classmethod
    def parse_document_reject_duplicates(cls, value):  # noqa: ANN001
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {
                "1",
                "true",
                "yes",
                "on",
            }:
                return True

            if normalized in {
                "0",
                "false",
                "no",
                "off",
            }:
                return False

        return True

    # =========================================================
    # GEMINI / VISIÓN
    # =========================================================

    @field_validator(
        "vision_provider",
        mode="before",
    )
    @classmethod
    def normalize_vision_provider(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "gemini"

        return value.strip().lower().replace("-", "_")

    @field_validator(
        "gemini_api_key",
        mode="before",
    )
    @classmethod
    def normalize_gemini_api_key(cls, value):  # noqa: ANN001
        return str(value or "").strip()

    @field_validator(
        "gemini_primary_model",
        "gemini_fallback_model",
        mode="before",
    )
    @classmethod
    def normalize_gemini_model(cls, value, info):  # noqa: ANN001
        fallback = (
            "gemini-3.7-flash"
            if info.field_name == "gemini_primary_model"
            else "gemini-3.5-flash"
        )

        if not isinstance(value, str) or not value.strip():
            return fallback

        return value.strip()

    @field_validator(
        "qwen_api_key",
        mode="before",
    )
    @classmethod
    def normalize_qwen_api_key(cls, value):  # noqa: ANN001
        return str(value or "").strip()

    @field_validator(
        "qwen_primary_model",
        "qwen_fallback_model",
        mode="before",
    )
    @classmethod
    def normalize_qwen_model(cls, value, info):  # noqa: ANN001
        fallback = (
            "Qwen/Qwen3.5-4B:featherless-ai"
            if info.field_name == "qwen_primary_model"
            else ""
        )

        if not isinstance(value, str) or not value.strip():
            return fallback

        return value.strip()

    # =========================================================
    # OLLAMA
    # =========================================================

    @field_validator(
        "ollama_host",
        mode="before",
    )
    @classmethod
    def normalize_ollama_host(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "http://127.0.0.1:11434"

        return value.strip().rstrip("/")

    @field_validator(
        "ollama_model",
        mode="before",
    )
    @classmethod
    def normalize_ollama_model(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "llama3.2:3b"

        return value.strip()

    # =========================================================
    # OCR
    # =========================================================

    @field_validator(
        "ocr_engine",
        "tesseract_language",
        mode="before",
    )
    @classmethod
    def normalize_ocr_settings(cls, value, info):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "tesseract" if info.field_name == "ocr_engine" else "eng"

        return value.strip()

    # =========================================================
    # EMBEDDINGS
    # =========================================================

    @field_validator(
        "embedding_model",
        mode="before",
    )
    @classmethod
    def normalize_embedding_model(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "sentence-transformers/all-MiniLM-L6-v2"

        return value.strip()

    @field_validator(
        "embedding_backend",
        mode="before",
    )
    @classmethod
    def normalize_embedding_backend(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "sentence_transformers"

        return value.strip().lower().replace("-", "_")

    # =========================================================
    # VECTOR STORE
    # =========================================================

    @field_validator(
        "vector_store_backend",
        mode="before",
    )
    @classmethod
    def normalize_vector_store_backend(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "local"

        return value.strip().lower()

    @field_validator(
        "vector_table_name",
        mode="before",
    )
    @classmethod
    def normalize_vector_table_name(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "document_chunks"

        return value.strip()

    # =========================================================
    # PERSISTENCIA DOCUMENTAL
    # =========================================================

    @field_validator(
        "document_persistence_backend",
        mode="before",
    )
    @classmethod
    def normalize_document_persistence_backend(cls, value):  # noqa: ANN001
        if not isinstance(value, str) or not value.strip():
            return "local"

        return value.strip().lower()

    @field_validator(
        "document_table_name",
        "document_storage_bucket",
        mode="before",
    )
    @classmethod
    def normalize_document_resource_name(cls, value, info):  # noqa: ANN001
        fallback = (
            "documents"
            if info.field_name == "document_table_name"
            else "quantia-documents"
        )

        if not isinstance(value, str) or not value.strip():
            return fallback

        return value.strip()

    # =========================================================
    # AUTENTICACIÓN
    # =========================================================

    @field_validator(
        "auth_token_secret",
        mode="before",
    )
    @classmethod
    def normalize_auth_token_secret(cls, value):  # noqa: ANN001
        normalized = str(value or "").strip()

        if normalized and len(normalized) < 32:
            raise ValueError("AUTH_TOKEN_SECRET debe tener al menos 32 caracteres.")

        return normalized

    # =========================================================
    # DIRECTORIOS
    # =========================================================

    @field_validator(
        "upload_dir",
        mode="before",
    )
    @classmethod
    def normalize_upload_dir(cls, value):  # noqa: ANN001
        if isinstance(value, Path):
            return value

        if isinstance(value, str):
            value = value.strip()

            if value:
                return Path(value)

        return BACKEND_DIR / "tmp_documents"

    # =========================================================
    # PROPIEDADES DERIVADAS
    # =========================================================

    @property
    def supabase_admin_key(self) -> str:
        return (
            self.supabase_service_role_key
            or self.supabase_key
            or self.supabase_anon_key
        )

    @property
    def gemini_models(self) -> tuple[str, ...]:
        """
        Modelos Gemini habilitados en orden de prioridad.

        Evita repetir el mismo modelo si ambas variables
        de entorno apuntaran accidentalmente al mismo ID.
        """

        models = []

        for model in (
            self.gemini_primary_model,
            self.gemini_fallback_model,
        ):
            if model and model not in models:
                models.append(model)

        return tuple(models)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
