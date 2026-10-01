import argparse
import json
import mimetypes
import sys
from pathlib import Path

from app.core.config import settings
from app.prompts.quantia_extraction_prompt import (
    QUANTIA_EXTRACTION_PROMPT,
)
from app.schemas.gemini_extraction_transport import (
    get_gemini_extraction_transport_schema,
)
from app.services.gemini_vision_provider import (
    GeminiVisionProvider,
)
from app.services.vision_provider import (
    VisionProviderError,
)


SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}


def detect_mime_type(
    path: Path,
) -> str:
    mime_type, _ = mimetypes.guess_type(
        path.name
    )

    if mime_type == "image/jpg":
        mime_type = "image/jpeg"

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            "Tipo de archivo no soportado: "
            f"{mime_type or 'desconocido'}"
        )

    return mime_type


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba Gemini usando el schema compacto "
            "de transporte Quantia V2."
        )
    )

    parser.add_argument(
        "input",
        help="Ruta de la imagen o PDF.",
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    ).expanduser().resolve()

    if not input_path.exists():
        print(
            f"ERROR: no existe el archivo:\n"
            f"{input_path}"
        )
        return 1

    if not input_path.is_file():
        print(
            f"ERROR: la ruta no es un archivo:\n"
            f"{input_path}"
        )
        return 1

    try:
        mime_type = detect_mime_type(
            input_path
        )

    except ValueError as exc:
        print(
            f"ERROR: {exc}"
        )
        return 1

    try:
        media_bytes = input_path.read_bytes()

    except OSError as exc:
        print(
            f"ERROR leyendo archivo:\n{exc}"
        )
        return 1

    if not media_bytes:
        print(
            "ERROR: archivo vacío."
        )
        return 1

    # =========================================================
    # PRUEBA CONTROLADA
    # =========================================================
    #
    # Utilizamos únicamente Gemini 3.5 en esta prueba.
    #
    # Ya comprobamos que:
    # - acepta la imagen;
    # - responde HTTP 200;
    # - acepta responseJsonSchema simple.
    #
    # Ahora queremos aislar únicamente la compatibilidad
    # del schema compacto Quantia.
    # =========================================================

    provider = GeminiVisionProvider(
        primary_model=
            settings.gemini_fallback_model,

        fallback_model=
            settings.gemini_fallback_model,
    )

    schema = (
        get_gemini_extraction_transport_schema()
    )

    print()
    print(
        "========================================"
    )
    print(
        "QUANTIA V2 — TRANSPORT SCHEMA"
    )
    print(
        "========================================"
    )
    print(
        f"Archivo : {input_path.name}"
    )
    print(
        f"MIME    : {mime_type}"
    )
    print(
        f"Tamaño  : "
        f"{len(media_bytes) / (1024 * 1024):.2f} MB"
    )
    print(
        f"Modelo  : {provider.models[0]}"
    )
    print(
        "Schema  : Gemini transport"
    )
    print()

    try:
        result = provider.analyze(
            prompt=
                QUANTIA_EXTRACTION_PROMPT,

            media_bytes=
                media_bytes,

            media_mime_type=
                mime_type,

            response_json_schema=
                schema,
        )

    except VisionProviderError as exc:
        print(
            "ERROR DEL PROVEEDOR:"
        )
        print(
            str(exc)
        )
        return 2

    if not isinstance(
        result.data,
        dict,
    ):
        print(
            "ERROR: Gemini no devolvió "
            "un objeto JSON."
        )
        return 3

    required_keys = {
        "resumen",
        "documento",
        "predio",
        "niveles",
        "informacion_constructiva",
        "conflictos",
        "datos_no_identificados",
        "confirmaciones_requeridas",
    }

    received_keys = set(
        result.data.keys()
    )

    missing_keys = (
        required_keys
        - received_keys
    )

    if missing_keys:
        print(
            "ERROR: faltan campos principales:"
        )

        for key in sorted(
            missing_keys
        ):
            print(
                f"  - {key}"
            )

        return 4

    output_path = input_path.with_name(
        f"{input_path.stem}"
        ".gemini-transport.json"
    )

    try:
        output_path.write_text(
            json.dumps(
                result.data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        print(
            "ERROR guardando resultado:"
        )
        print(
            exc
        )
        return 5

    niveles = result.data.get(
        "niveles",
        []
    )

    total_spaces = 0
    total_stairs = 0
    total_dimensions = 0

    if isinstance(
        niveles,
        list,
    ):
        for nivel in niveles:
            if not isinstance(
                nivel,
                dict,
            ):
                continue

            espacios = nivel.get(
                "espacios",
                [],
            )

            escaleras = nivel.get(
                "escaleras",
                [],
            )

            cotas = nivel.get(
                "cotas",
                [],
            )

            if isinstance(
                espacios,
                list,
            ):
                total_spaces += len(
                    espacios
                )

            if isinstance(
                escaleras,
                list,
            ):
                total_stairs += len(
                    escaleras
                )

            if isinstance(
                cotas,
                list,
            ):
                total_dimensions += len(
                    cotas
                )

    conflictos = result.data.get(
        "conflictos",
        []
    )

    pendientes = result.data.get(
        "confirmaciones_requeridas",
        []
    )

    print()
    print(
        "========================================"
    )
    print(
        "RESULTADO"
    )
    print(
        "========================================"
    )
    print(
        f"Proveedor : {result.provider}"
    )
    print(
        f"Modelo    : {result.model}"
    )
    print(
        f"Niveles   : {len(niveles)}"
    )
    print(
        f"Espacios  : {total_spaces}"
    )
    print(
        f"Escaleras : {total_stairs}"
    )
    print(
        f"Cotas     : {total_dimensions}"
    )

    if isinstance(
        conflictos,
        list,
    ):
        print(
            f"Conflictos: {len(conflictos)}"
        )

    if isinstance(
        pendientes,
        list,
    ):
        print(
            f"Pendientes: {len(pendientes)}"
        )

    print()
    print(
        "Resumen:"
    )
    print(
        result.data.get(
            "resumen",
            "",
        )
    )

    print()
    print(
        "JSON guardado en:"
    )
    print(
        output_path
    )
    print()

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )