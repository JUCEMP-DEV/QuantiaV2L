import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings
from app.schemas.quantia_extraction import (
    get_quantia_extraction_json_schema,
)


BASE_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)


def detect_mime_type(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(
        path.name
    )

    if mime_type == "image/jpg":
        mime_type = "image/jpeg"

    if not mime_type:
        raise ValueError(
            "No se pudo determinar el MIME type."
        )

    return mime_type


def clean_schema(
    schema: dict[str, Any],
) -> dict[str, Any]:
    unsupported = {
        "default",
        "exclusiveMinimum",
        "exclusiveMaximum",
    }

    def clean(value: Any) -> Any:
        if isinstance(value, list):
            return [
                clean(item)
                for item in value
            ]

        if not isinstance(value, dict):
            return value

        result = {}

        for key, item in value.items():
            if key in unsupported:
                continue

            result[key] = clean(item)

        return result

    return clean(schema)


def build_contents(
    *,
    image_bytes: bytes,
    mime_type: str,
) -> list[dict[str, Any]]:
    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "Analiza brevemente esta imagen. "
                        "No inventes información."
                    )
                },
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": encoded,
                    }
                },
            ],
        }
    ]


def execute_test(
    *,
    name: str,
    model: str,
    contents: list[dict[str, Any]],
    generation_config: dict[str, Any] | None,
) -> None:
    url = (
        f"{BASE_URL}/"
        f"{model}:generateContent"
    )

    payload: dict[str, Any] = {
        "contents": contents,
    }

    if generation_config:
        payload["generationConfig"] = (
            generation_config
        )

    headers = {
        "x-goog-api-key":
            settings.gemini_api_key,

        "Content-Type":
            "application/json",
    }

    print()
    print(
        "========================================"
    )
    print(name)
    print(
        "========================================"
    )

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )

    except requests.RequestException as exc:
        print(
            f"ERROR CONEXIÓN: {exc}"
        )
        return

    print(
        f"HTTP: {response.status_code}"
    )

    try:
        data = response.json()

    except ValueError:
        print(
            response.text[:3000]
        )
        return

    if response.ok:
        candidates = data.get(
            "candidates",
            []
        )

        if candidates:
            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            if parts:
                text = parts[0].get(
                    "text"
                )

                if text:
                    print(
                        "RESPUESTA:"
                    )
                    print(
                        text[:1500]
                    )

        print(
            "OK"
        )
        return

    print(
        "ERROR:"
    )

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )[:5000]
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        help="Ruta de imagen de prueba.",
    )

    args = parser.parse_args()

    path = Path(
        args.input
    ).expanduser().resolve()

    if not path.exists():
        print(
            f"No existe:\n{path}"
        )
        return 1

    if not settings.gemini_api_key:
        print(
            "GEMINI_API_KEY no configurada."
        )
        return 1

    mime_type = detect_mime_type(
        path
    )

    image_bytes = path.read_bytes()

    contents = build_contents(
        image_bytes=image_bytes,
        mime_type=mime_type,
    )

    model = (
        settings.gemini_fallback_model
    )

    print()
    print(
        "QUANTIA — DIAGNÓSTICO STRUCTURED OUTPUT"
    )
    print(
        f"Modelo: {model}"
    )
    print(
        f"Archivo: {path.name}"
    )

    # =========================================================
    # TEST 1
    # Gemini multimodal sin schema
    # =========================================================

    execute_test(
        name="TEST 1 — SIN SCHEMA",
        model=model,
        contents=contents,
        generation_config=None,
    )

    # =========================================================
    # TEST 2
    # responseJsonSchema mínimo
    # =========================================================

    simple_schema = {
        "type": "object",
        "properties": {
            "descripcion": {
                "type": "string",
            },
            "confianza": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        },
        "required": [
            "descripcion",
            "confianza",
        ],
        "additionalProperties": False,
    }

    execute_test(
        name=(
            "TEST 2 — responseJsonSchema SIMPLE"
        ),
        model=model,
        contents=contents,
        generation_config={
            "responseMimeType":
                "application/json",

            "responseJsonSchema":
                simple_schema,
        },
    )

    # =========================================================
    # TEST 3
    # responseSchema mínimo
    # =========================================================

    execute_test(
        name=(
            "TEST 3 — responseSchema SIMPLE"
        ),
        model=model,
        contents=contents,
        generation_config={
            "responseMimeType":
                "application/json",

            "responseSchema":
                simple_schema,
        },
    )

    # =========================================================
    # TEST 4
    # schema completo Quantia usando responseJsonSchema
    # =========================================================

    quantia_schema = clean_schema(
        get_quantia_extraction_json_schema()
    )

    print()
    print(
        "Schema Quantia:"
    )
    print(
        "Definiciones:",
        len(
            quantia_schema.get(
                "$defs",
                {},
            )
        ),
    )

    execute_test(
        name=(
            "TEST 4 — responseJsonSchema QUANTIA"
        ),
        model=model,
        contents=contents,
        generation_config={
            "responseMimeType":
                "application/json",

            "responseJsonSchema":
                quantia_schema,
        },
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )