from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.vision_provider import (
    VisionProvider,
    VisionResult,
)

VISION_CACHE_VERSION = 1


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_json_hash(value: Any) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return sha256_bytes(serialized.encode("utf-8"))


def build_vision_signature(
    *,
    prompt: str,
    media_bytes: bytes,
    media_mime_type: str,
    response_json_schema: dict[str, Any] | None,
    provider_identity: str,
) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("El prompt no puede estar vacío.")

    if (
        not isinstance(
            media_bytes,
            (bytes, bytearray),
        )
        or not media_bytes
    ):
        raise ValueError("media_bytes no puede estar vacío.")

    return {
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "media_sha256": sha256_bytes(bytes(media_bytes)),
        "media_mime_type": str(media_mime_type or "").strip().lower(),
        "response_schema_sha256": stable_json_hash(response_json_schema),
        "provider_identity": str(provider_identity or "").strip(),
    }


class CachedVisionProvider(VisionProvider):
    """
    Decorador de VisionProvider con caché por contenido.

    HIT:
        devuelve VisionResult guardado.

    MISS:
        ejecuta el proveedor real y guarda el resultado.

    La clave depende de:
        - prompt
        - contenido visual
        - MIME
        - JSON Schema
        - identidad/configuración del proveedor

    El pipeline superior no necesita conocer si el resultado
    vino de Gemini o del caché.
    """

    _locks_guard = threading.Lock()
    _key_locks: dict[str, threading.Lock] = {}

    def __init__(
        self,
        *,
        provider: VisionProvider,
        cache_dir: Path,
        provider_identity: str,
        enabled: bool = True,
    ) -> None:
        self.provider = provider
        self.cache_dir = Path(cache_dir)
        self.provider_identity = str(provider_identity or "").strip()
        self.enabled = bool(enabled)

        if not self.provider_identity:
            raise ValueError("provider_identity es obligatorio.")

        if self.enabled:
            self.cache_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

    def analyze(
        self,
        *,
        prompt: str,
        media_bytes: bytes,
        media_mime_type: str,
        response_json_schema: dict[str, Any] | None = None,
    ) -> VisionResult:
        if not self.enabled:
            return self.provider.analyze(
                prompt=prompt,
                media_bytes=media_bytes,
                media_mime_type=media_mime_type,
                response_json_schema=response_json_schema,
            )

        signature = build_vision_signature(
            prompt=prompt,
            media_bytes=media_bytes,
            media_mime_type=media_mime_type,
            response_json_schema=response_json_schema,
            provider_identity=self.provider_identity,
        )

        cache_key = stable_json_hash(
            {
                "cache_version": VISION_CACHE_VERSION,
                "signature": signature,
            }
        )

        cache_path = self._cache_path(cache_key)

        cached = self._load(
            path=cache_path,
            expected_signature=signature,
        )

        if cached is not None:
            print(
                f"[vision-cache] HIT {cache_key[:12]}",
                flush=True,
            )
            return cached

        # Evita que dos peticiones idénticas del mismo proceso
        # lancen Gemini simultáneamente.
        lock = self._lock_for_key(cache_key)

        with lock:
            # Segunda comprobación después de esperar el lock.
            cached = self._load(
                path=cache_path,
                expected_signature=signature,
            )

            if cached is not None:
                print(
                    f"[vision-cache] HIT {cache_key[:12]}",
                    flush=True,
                )
                return cached

            print(
                f"[vision-cache] MISS {cache_key[:12]}",
                flush=True,
            )

            result = self.provider.analyze(
                prompt=prompt,
                media_bytes=media_bytes,
                media_mime_type=media_mime_type,
                response_json_schema=response_json_schema,
            )

            try:
                self._write(
                    path=cache_path,
                    signature=signature,
                    result=result,
                )

                print(
                    f"[vision-cache] WRITE {cache_key[:12]}",
                    flush=True,
                )

            except (
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                # Un problema de caché nunca debe invalidar una
                # respuesta Gemini que ya fue obtenida.
                print(
                    "[vision-cache] WRITE FAIL " f"{cache_key[:12]}: {exc}",
                    flush=True,
                )

            return result

    def _cache_path(
        self,
        cache_key: str,
    ) -> Path:
        # Sharding simple para evitar miles de archivos
        # en un único directorio.
        return self.cache_dir / cache_key[:2] / f"{cache_key}.json"

    @classmethod
    def _lock_for_key(
        cls,
        cache_key: str,
    ) -> threading.Lock:
        with cls._locks_guard:
            lock = cls._key_locks.get(cache_key)

            if lock is None:
                lock = threading.Lock()
                cls._key_locks[cache_key] = lock

            return lock

    @staticmethod
    def _load(
        *,
        path: Path,
        expected_signature: dict[str, Any],
    ) -> VisionResult | None:
        if not path.is_file():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))

            if not isinstance(
                payload,
                dict,
            ):
                return None

            if payload.get("cache_version") != VISION_CACHE_VERSION:
                return None

            if payload.get("signature") != expected_signature:
                return None

            cached_result = payload.get("result")

            if not isinstance(
                cached_result,
                dict,
            ):
                return None

            provider = str(
                cached_result.get(
                    "provider",
                    "",
                )
            ).strip()

            model = str(
                cached_result.get(
                    "model",
                    "",
                )
            ).strip()

            text = cached_result.get("text")

            raw = cached_result.get("raw")

            if not provider or not model:
                return None

            if not isinstance(
                text,
                str,
            ):
                return None

            if not isinstance(
                raw,
                dict,
            ):
                return None

            return VisionResult(
                provider=provider,
                model=model,
                text=text,
                data=cached_result.get("data"),
                fallback_used=bool(
                    cached_result.get(
                        "fallback_used",
                        False,
                    )
                ),
                raw=raw,
            )

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:
            print(
                f"[vision-cache] INVALID {path.name}: {exc}",
                flush=True,
            )

            return None

    @staticmethod
    def _write(
        *,
        path: Path,
        signature: dict[str, Any],
        result: VisionResult,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "cache_version": VISION_CACHE_VERSION,
            "signature": signature,
            "result": {
                "provider": result.provider,
                "model": result.model,
                "text": result.text,
                "data": result.data,
                "fallback_used": bool(result.fallback_used),
                "raw": result.raw,
            },
        }

        temporary_path = path.with_name(
            f"{path.name}.{os.getpid()}." f"{uuid4().hex}.tmp"
        )

        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(path)
