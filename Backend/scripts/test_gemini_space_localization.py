import argparse
import json
import mimetypes
import sys
from pathlib import Path

from app.core.config import settings
from app.prompts.quantia_space_localization_prompt import (
    build_quantia_space_localization_prompt,
)
from app.schemas.gemini_space_localization_transport import (
    get_gemini_space_localization_schema,
)
from app.schemas.quantia_extraction import (
    QuantiaExtractionSchema,
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
            "Tipo de imagen no soportado: "
            f"{mime_type or 'desconocido'}"
        )

    return mime_type


def load_quantia_extraction(
    path: Path,
) -> QuantiaExtractionSchema:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise ValueError(
            f"No fue posible leer el JSON canónico: {exc}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"El JSON canónico no es válido: {exc}"
        ) from exc

    try:
        return QuantiaExtractionSchema.model_validate(
            payload
        )

    except Exception as exc:
        raise ValueError(
            "El archivo no cumple "
            "QuantiaExtractionSchema."
        ) from exc


def expected_structure(
    extraction: QuantiaExtractionSchema,
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}

    for level in extraction.niveles:
        result[level.nombre] = {
            space.id_propuesto
            for space in level.espacios
        }

    return result


def validate_localization_result(
    *,
    data: dict,
    extraction: QuantiaExtractionSchema,
) -> list[str]:
    errors: list[str] = []

    expected = expected_structure(
        extraction
    )

    returned_levels = data.get(
        "niveles",
        []
    )

    if not isinstance(
        returned_levels,
        list,
    ):
        return [
            "El campo niveles no es una lista."
        ]

    seen_levels: set[str] = set()

    for level in returned_levels:
        if not isinstance(
            level,
            dict,
        ):
            errors.append(
                "Existe un nivel que no es objeto JSON."
            )
            continue

        level_name = str(
            level.get(
                "nombre",
                "",
            )
        ).strip()

        if not level_name:
            errors.append(
                "Existe un nivel sin nombre."
            )
            continue

        seen_levels.add(
            level_name
        )

        if level_name not in expected:
            errors.append(
                f"Gemini agregó un nivel no solicitado: "
                f"{level_name}"
            )
            continue

        spaces = level.get(
            "espacios",
            []
        )

        if not isinstance(
            spaces,
            list,
        ):
            errors.append(
                f"{level_name}: espacios no es lista."
            )
            continue

        returned_ids: set[str] = set()

        for space in spaces:
            if not isinstance(
                space,
                dict,
            ):
                errors.append(
                    f"{level_name}: espacio inválido."
                )
                continue

            space_id = str(
                space.get(
                    "id_propuesto",
                    "",
                )
            ).strip()

            if not space_id:
                errors.append(
                    f"{level_name}: espacio sin id_propuesto."
                )
                continue

            returned_ids.add(
                space_id
            )

            if (
                space_id
                not in expected[level_name]
            ):
                errors.append(
                    f"{level_name}: Gemini agregó "
                    f"ID no solicitado {space_id}"
                )

            localized = space.get(
                "localizado"
            )

            bbox = space.get(
                "bbox_normalizado"
            )

            confidence = space.get(
                "confianza"
            )

            if localized is True:
                if not isinstance(
                    bbox,
                    dict,
                ):
                    errors.append(
                        f"{space_id}: localizado=true "
                        "pero bbox es null."
                    )
                    continue

                try:
                    x_min = float(
                        bbox["x_min"]
                    )
                    y_min = float(
                        bbox["y_min"]
                    )
                    x_max = float(
                        bbox["x_max"]
                    )
                    y_max = float(
                        bbox["y_max"]
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    errors.append(
                        f"{space_id}: bbox inválido."
                    )
                    continue

                if not (
                    0 <= x_min < x_max <= 1
                    and
                    0 <= y_min < y_max <= 1
                ):
                    errors.append(
                        f"{space_id}: bbox fuera "
                        "del rango normalizado."
                    )

                if isinstance(
                    confidence,
                    (int, float),
                ):
                    if float(
                        confidence
                    ) < 0.5:
                        errors.append(
                            f"{space_id}: localizado=true "
                            "con confianza menor a 0.50."
                        )

            if localized is False:
                if bbox is not None:
                    errors.append(
                        f"{space_id}: localizado=false "
                        "pero bbox no es null."
                    )

        missing_ids = (
            expected[level_name]
            - returned_ids
        )

        for missing_id in sorted(
            missing_ids
        ):
            errors.append(
                f"{level_name}: falta "
                f"{missing_id}"
            )

    missing_levels = (
        set(
            expected.keys()
        )
        - seen_levels
    )

    for level_name in sorted(
        missing_levels
    ):
        errors.append(
            f"Falta nivel: {level_name}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba de localización visual "
            "de espacios Quantia."
        )
    )

    parser.add_argument(
        "image",
        help="Imagen renderizada del plano.",
    )

    parser.add_argument(
        "canonical_json",
        help=(
            "JSON canónico generado por "
            "el reconciliador Quantia."
        ),
    )

    args = parser.parse_args()

    image_path = Path(
        args.image
    ).expanduser().resolve()

    canonical_path = Path(
        args.canonical_json
    ).expanduser().resolve()

    if not image_path.exists():
        print(
            "ERROR: no existe la imagen:"
        )
        print(
            image_path
        )
        return 1

    if not canonical_path.exists():
        print(
            "ERROR: no existe el JSON canónico:"
        )
        print(
            canonical_path
        )
        return 1

    try:
        mime_type = detect_mime_type(
            image_path
        )

        extraction = load_quantia_extraction(
            canonical_path
        )

    except ValueError as exc:
        print(
            f"ERROR: {exc}"
        )
        return 2

    try:
        image_bytes = (
            image_path.read_bytes()
        )

    except OSError as exc:
        print(
            "ERROR leyendo imagen:"
        )
        print(
            exc
        )
        return 3

    prompt = (
        build_quantia_space_localization_prompt(
            extraction
        )
    )

    schema = (
        get_gemini_space_localization_schema()
    )

    # =========================================================
    # PRUEBA CONTROLADA
    # =========================================================
    #
    # Usamos Gemini 3.5 para validar primero esta tarea
    # de localización, porque ya sabemos que:
    #
    # - acepta la imagen;
    # - acepta responseJsonSchema;
    # - está funcionando con nuestro transporte compacto.
    #
    # La arquitectura de producción mantendrá 3.7 principal
    # y 3.5 fallback.
    # =========================================================

    provider = GeminiVisionProvider(
        primary_model=
            settings.gemini_fallback_model,

        fallback_model=
            settings.gemini_fallback_model,
    )

    expected = expected_structure(
        extraction
    )

    total_expected_spaces = sum(
        len(ids)
        for ids in expected.values()
    )

    print()
    print(
        "========================================"
    )
    print(
        "QUANTIA V2 — SPACE LOCALIZATION"
    )
    print(
        "========================================"
    )

    print(
        f"Imagen          : {image_path.name}"
    )

    print(
        f"MIME            : {mime_type}"
    )

    print(
        f"Modelo          : {provider.models[0]}"
    )

    print(
        f"Niveles esperados: {len(expected)}"
    )

    print(
        f"Espacios esperados: "
        f"{total_expected_spaces}"
    )

    print()

    try:
        result = provider.analyze(
            prompt=prompt,

            media_bytes=image_bytes,

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
        return 4

    if not isinstance(
        result.data,
        dict,
    ):
        print(
            "ERROR: Gemini no devolvió "
            "un objeto JSON."
        )
        return 5

    validation_errors = (
        validate_localization_result(
            data=result.data,
            extraction=extraction,
        )
    )

    output_path = (
        image_path.with_name(
            f"{image_path.stem}"
            ".space-localization.json"
        )
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
        return 6

    # =========================================================
    # REPORTE
    # =========================================================

    levels = result.data.get(
        "niveles",
        []
    )

    localized_spaces = 0
    unresolved_spaces = 0

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
        f"Proveedor       : {result.provider}"
    )

    print(
        f"Modelo          : {result.model}"
    )

    print(
        f"Niveles devueltos: {len(levels)}"
    )

    print()

    for level in levels:
        if not isinstance(
            level,
            dict,
        ):
            continue

        print(
            f"NIVEL: {level.get('nombre')}"
        )

        print(
            "  Localizado:",
            level.get(
                "localizado"
            ),
        )

        print(
            "  Confianza :",
            level.get(
                "confianza"
            ),
        )

        spaces = level.get(
            "espacios",
            []
        )

        if not isinstance(
            spaces,
            list,
        ):
            continue

        for space in spaces:
            if not isinstance(
                space,
                dict,
            ):
                continue

            localized = (
                space.get(
                    "localizado"
                )
                is True
            )

            if localized:
                localized_spaces += 1
            else:
                unresolved_spaces += 1

            print(
                "   -",
                space.get(
                    "id_propuesto"
                ),
                "|",
                space.get(
                    "nombre"
                ),
                "| localizado=",
                localized,
                "| confianza=",
                space.get(
                    "confianza"
                ),
            )

            if localized:
                print(
                    "     bbox=",
                    space.get(
                        "bbox_normalizado"
                    ),
                )

            else:
                print(
                    "     motivo=",
                    space.get(
                        "motivo_no_localizado"
                    ),
                )

        print()

    print(
        f"Espacios localizados : "
        f"{localized_spaces}"
    )

    print(
        f"Espacios no resueltos: "
        f"{unresolved_spaces}"
    )

    print(
        f"Errores estructurales: "
        f"{len(validation_errors)}"
    )

    print()

    if validation_errors:
        print(
            "VALIDACIÓN:"
        )

        for error in validation_errors:
            print(
                f" - {error}"
            )

        print()

    print(
        "JSON guardado en:"
    )
    print(
        output_path
    )

    print()

    if validation_errors:
        return 7

    print(
        "CONTROL OK — Gemini conservó "
        "la estructura Quantia."
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )