import argparse
import json
import mimetypes
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.config import settings
from app.prompts.quantia_extraction_prompt import (
    QUANTIA_EXTRACTION_PROMPT,
)
from app.schemas.quantia_extraction import (
    get_quantia_extraction_json_schema,
    validate_quantia_extraction,
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


def detect_mime_type(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(
        path.name
    )

    if mime_type == "image/jpg":
        mime_type = "image/jpeg"

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            "Tipo de archivo no soportado para esta prueba: "
            f"{mime_type or 'desconocido'}"
        )

    return mime_type


def build_output_path(
    input_path: Path,
    output_argument: str | None,
) -> Path:
    if output_argument:
        return Path(
            output_argument
        ).resolve()

    return input_path.with_name(
        f"{input_path.stem}.quantia-extraction.json"
    )


def create_provider(
    *,
    allow_fallback: bool,
) -> GeminiVisionProvider:
    if allow_fallback:
        return GeminiVisionProvider()

    # Primera prueba controlada:
    # fuerza Gemini 3.7 únicamente.
    #
    # El proveedor elimina modelos duplicados,
    # por lo que 3.5 no podrá entrar como fallback.
    return GeminiVisionProvider(
        primary_model=
            settings.gemini_primary_model,
        fallback_model=
            settings.gemini_primary_model,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba controlada de extracción "
            "multimodal Quantia V2."
        )
    )

    parser.add_argument(
        "input",
        help=(
            "Ruta de la imagen o PDF "
            "que se analizará."
        ),
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Ruta opcional donde guardar "
            "el JSON validado."
        ),
    )

    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help=(
            "Permite utilizar Gemini 3.5 "
            "si falla Gemini 3.7."
        ),
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
        media_bytes = (
            input_path.read_bytes()
        )

    except OSError as exc:
        print(
            "ERROR: no fue posible leer "
            f"el archivo:\n{exc}"
        )
        return 1

    if not media_bytes:
        print(
            "ERROR: el archivo está vacío."
        )
        return 1

    provider = create_provider(
        allow_fallback=
            args.allow_fallback
    )

    schema = (
        get_quantia_extraction_json_schema()
    )

    print()
    print(
        "========================================"
    )
    print(
        "QUANTIA V2 — PRUEBA GEMINI"
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
        f"Modelos : {provider.models}"
    )
    print(
        f"Fallback: "
        f"{'permitido' if args.allow_fallback else 'desactivado'}"
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

    if result.data is None:
        print(
            "ERROR: Gemini respondió, "
            "pero no existe JSON estructurado."
        )
        return 3

    try:
        extraction = (
            validate_quantia_extraction(
                result.data
            )
        )

    except ValidationError as exc:
        print(
            "ERROR DE VALIDACIÓN PYDANTIC:"
        )
        print(
            exc
        )

        invalid_output = (
            input_path.with_name(
                f"{input_path.stem}"
                ".invalid-gemini-response.json"
            )
        )

        try:
            invalid_output.write_text(
                json.dumps(
                    result.data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            print()
            print(
                "Respuesta inválida guardada en:"
            )
            print(
                invalid_output
            )

        except OSError:
            pass

        return 4

    output_path = build_output_path(
        input_path,
        args.output,
    )

    try:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            extraction.model_dump_json(
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError as exc:
        print(
            "ERROR: Gemini respondió correctamente, "
            "pero no fue posible guardar el resultado:"
        )
        print(
            exc
        )
        return 5

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
        f"Fallback  : {result.fallback_used}"
    )
    print(
        f"Niveles   : {len(extraction.niveles)}"
    )

    total_spaces = sum(
        len(level.espacios)
        for level in extraction.niveles
    )

    print(
        f"Espacios  : {total_spaces}"
    )
    print(
        f"Conflictos: {len(extraction.conflictos)}"
    )
    print(
        "Pendientes: "
        f"{len(extraction.confirmaciones_requeridas)}"
    )
    print()

    print(
        "Resumen:"
    )
    print(
        extraction.resumen
    )
    print()

    print(
        "JSON validado guardado en:"
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