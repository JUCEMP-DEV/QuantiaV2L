from __future__ import annotations

from app.core.config import get_settings
from app.services.gemini_vision_provider import (
    get_gemini_vision_provider,
)
from app.services.vision_cache_service import (
    CachedVisionProvider,
)
from app.services.vision_provider import VisionProvider


def get_cached_gemini_vision_provider() -> VisionProvider:
    settings = get_settings()

    provider = get_gemini_vision_provider()

    provider_identity = f"{settings.vision_provider}:" + "->".join(
        settings.gemini_models
    )

    return CachedVisionProvider(
        provider=provider,
        cache_dir=settings.vision_cache_dir,
        provider_identity=provider_identity,
        enabled=settings.vision_cache_enabled,
    )
