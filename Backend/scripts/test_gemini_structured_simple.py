import json
import sys

import requests

from app.core.config import settings


BASE_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)


def main() -> int:
    model = settings.gemini_fallback_model

    if not settings.gemini_api_key:
        print("ERROR: GEMINI_API_KEY no configurada.")
        return 1

    schema = {
        "type": "object",
        "properties": {
            "resultado": {
                "type": "string",
            },
            "confianza": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        },
        "required": [
            "resultado",
            "confianza",
        ],
        "additionalProperties": False,
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Responde que la prueba de "
                            "structured output fue correcta "
                            "y asigna confianza 1."
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType":
                "application/json",

            "responseJsonSchema":
                schema,
        },
    }

    headers = {
        "x-goog-api-key":
            settings.gemini_api_key,

        "Content-Type":
            "application/json",
    }

    url = (
        f"{BASE_URL}/"
        f"{model}:generateContent"
    )

    print()
    print(
        "QUANTIA — STRUCTURED OUTPUT SIMPLE"
    )
    print(
        f"Modelo: {model}"
    )
    print()

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )

    except requests.RequestException as exc:
        print(
            f"ERROR DE CONEXIÓN: {exc}"
        )
        return 2

    print(
        f"HTTP: {response.status_code}"
    )

    try:
        data = response.json()

    except ValueError:
        print(
            response.text
        )
        return 3

    if not response.ok:
        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 4

    candidates = data.get(
        "candidates",
        []
    )

    if not candidates:
        print(
            "ERROR: respuesta sin candidatos."
        )
        return 5

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    if not parts:
        print(
            "ERROR: respuesta sin contenido."
        )
        return 6

    text = parts[0].get(
        "text",
        "",
    )

    print(
        "RESPUESTA:"
    )
    print(
        text
    )

    try:
        parsed = json.loads(
            text
        )

    except json.JSONDecodeError:
        print(
            "ERROR: la respuesta no es JSON válido."
        )
        return 7

    print()
    print(
        "JSON válido:"
    )
    print(
        json.dumps(
            parsed,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )