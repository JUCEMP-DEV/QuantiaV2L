from __future__ import annotations

import json
from pathlib import Path

from app.services.cached_gemini_vision_provider import (
    get_cached_gemini_vision_provider,
)
from app.services.vision_cache_service import (
    VISION_CACHE_VERSION,
    stable_json_hash,
)
from app.services.vision_provider import VisionResult

REPLAY_DIR = Path("tests") / "output" / "miguel_h" / "gemini_replay"

REPLAY_FILES = (
    "miguel_h_gemini_extraction_replay.json",
    "miguel_h_gemini_localization_replay.json",
)


def main() -> None:
    cached_provider = get_cached_gemini_vision_provider()

    print(
        "Vision cache:",
        cached_provider.cache_dir,
    )

    print(
        "Provider identity:",
        cached_provider.provider_identity,
    )

    imported = 0

    for filename in REPLAY_FILES:
        replay_path = REPLAY_DIR / filename

        if not replay_path.is_file():
            raise FileNotFoundError(f"No existe replay: {replay_path}")

        replay_payload = json.loads(replay_path.read_text(encoding="utf-8"))

        replay_signature = replay_payload.get("signature")

        replay_result = replay_payload.get("result")

        if not isinstance(
            replay_signature,
            dict,
        ):
            raise RuntimeError(f"Firma inválida: {replay_path}")

        if not isinstance(
            replay_result,
            dict,
        ):
            raise RuntimeError(f"Resultado inválido: {replay_path}")

        # Firma utilizada por el caché general.
        signature = {
            **replay_signature,
            "provider_identity": cached_provider.provider_identity,
        }

        cache_key = stable_json_hash(
            {
                "cache_version": VISION_CACHE_VERSION,
                "signature": signature,
            }
        )

        cache_path = cached_provider._cache_path(cache_key)

        result = VisionResult(
            provider=str(
                replay_result.get(
                    "provider",
                    "",
                )
            ),
            model=str(
                replay_result.get(
                    "model",
                    "",
                )
            ),
            text=str(
                replay_result.get(
                    "text",
                    "",
                )
            ),
            data=replay_result.get("data"),
            fallback_used=bool(
                replay_result.get(
                    "fallback_used",
                    False,
                )
            ),
            raw=replay_result.get("raw") or {},
        )

        cached_provider._write(
            path=cache_path,
            signature=signature,
            result=result,
        )

        imported += 1

        print(f"IMPORT {filename}")
        print(f"  key:  {cache_key[:12]}")
        print(f"  path: {cache_path}")

    print()
    print(f"Importados: {imported}")


if __name__ == "__main__":
    main()
