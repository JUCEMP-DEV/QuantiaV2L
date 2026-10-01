from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VisionResult:
    provider: str
    model: str

    text: str

    data: dict[str, Any] | list[Any] | None = None

    fallback_used: bool = False

    raw: dict[str, Any] = field(
        default_factory=dict,
        repr=False,
    )


class VisionProviderError(RuntimeError):
    """Error controlado del proveedor multimodal."""


class VisionProvider(ABC):
    """
    Contrato común para proveedores multimodales de Quantia.

    El resto del sistema no debe conocer detalles específicos
    de Gemini ni de ningún proveedor futuro.
    """

    @abstractmethod
    def analyze(
        self,
        *,
        prompt: str,
        media_bytes: bytes,
        media_mime_type: str,
        response_json_schema: dict[str, Any] | None = None,
    ) -> VisionResult:
        raise NotImplementedError