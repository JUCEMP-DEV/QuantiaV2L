from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from io import BytesIO
from typing import Any

import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

from app.services.plan_document_analyzer import (
    DocumentRasterPage,
)


# ============================================================
# EVIDENCIA OCR
# ============================================================


@dataclass(slots=True)
class OCRTextItem:
    text: str
    normalized_text: str

    page: int

    x0: float
    y0: float
    x1: float
    y1: float

    center_x: float
    center_y: float

    confidence: float

    numeric_value: float | None = None
    numeric_unit: str | None = None

    source: str = "ocr_tesseract"


@dataclass(slots=True)
class OCRTextLine:
    text: str

    page: int

    x0: float
    y0: float
    x1: float
    y1: float

    confidence: float

    source: str = "ocr_tesseract"


@dataclass(slots=True)
class OCRPlanTextResult:
    page: int

    width_px: int
    height_px: int

    language: str | None

    tokens: list[
        OCRTextItem
    ] = field(
        default_factory=list
    )

    lines: list[
        OCRTextLine
    ] = field(
        default_factory=list
    )

    dimension_candidates: list[
        OCRTextItem
    ] = field(
        default_factory=list
    )

    axis_candidates: list[
        OCRTextItem
    ] = field(
        default_factory=list
    )

    notes: list[str] = field(
        default_factory=list
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


# ============================================================
# SERVICIO
# ============================================================


class OCRPlanTextService:
    """
    OCR determinístico para raster de planos/croquis.

    Responsabilidad:

        - texto impreso;
        - números;
        - cotas candidatas;
        - etiquetas;
        - ejes candidatos.

    No interpreta arquitectura.

    IMPORTANTE:

        OCR number != cota confirmada
        OCR letter != eje confirmado

    Las coordenadas permanecen exactamente en el sistema
    del DocumentRasterPage recibido.
    """

    DIMENSION_RE = re.compile(
        r"^\s*"
        r"(?P<value>\d+(?:[.,]\d{1,3})?)"
        r"\s*"
        r"(?P<unit>mm|cm|m)?"
        r"\s*$",
        re.IGNORECASE,
    )

    AXIS_ALPHA_RE = re.compile(
        r"^[A-Z]$"
    )

    AXIS_NUMERIC_RE = re.compile(
        r"^\d{1,3}$"
    )

    def __init__(
        self,
        *,
        tesseract_cmd: str | None = None,
        preferred_language: str | None = None,
    ) -> None:
        configured_cmd = (
            tesseract_cmd
            or os.getenv(
                "TESSERACT_CMD"
            )
        )

        if configured_cmd:
            pytesseract.pytesseract.tesseract_cmd = (
                configured_cmd
            )

        self.preferred_language = (
            preferred_language
            or os.getenv(
                "TESSERACT_LANG"
            )
        )

    # ========================================================
    # API
    # ========================================================

    def analyze(
        self,
        *,
        raster: DocumentRasterPage,
    ) -> OCRPlanTextResult:
        image = self._open_image(
            raster
        )

        width, height = (
            image.size
        )

        if (
            width != raster.width_px
            or height != raster.height_px
        ):
            raise ValueError(
                "Las dimensiones OCR no coinciden "
                "con DocumentRasterPage."
            )

        # Solo cambia intensidad, nunca tamaño/geometría.

        grayscale = (
            ImageOps.grayscale(
                image
            )
        )

        language = (
            self._select_language()
        )

        kwargs: dict[str, Any] = {
            "output_type":
                Output.DICT,
        }

        if language:
            kwargs["lang"] = (
                language
            )

        try:
            raw = (
                pytesseract.image_to_data(
                    grayscale,
                    **kwargs,
                )
            )

        except pytesseract.TesseractError as exc:
            raise ValueError(
                "Tesseract no pudo procesar "
                "el raster."
            ) from exc

        tokens: list[
            OCRTextItem
        ] = []

        dimension_candidates: list[
            OCRTextItem
        ] = []

        axis_candidates: list[
            OCRTextItem
        ] = []

        line_groups: dict[
            tuple[int, int, int],
            list[OCRTextItem],
        ] = {}

        count = len(
            raw.get(
                "text",
                []
            )
        )

        for index in range(
            count
        ):
            text = str(
                raw["text"][index]
                or ""
            ).strip()

            if not text:
                continue

            confidence = (
                self._parse_confidence(
                    raw.get(
                        "conf",
                        [],
                    ),
                    index,
                )
            )

            if confidence < 0:
                continue

            try:
                x = int(
                    raw["left"][index]
                )

                y = int(
                    raw["top"][index]
                )

                item_width = int(
                    raw["width"][index]
                )

                item_height = int(
                    raw["height"][index]
                )

            except (
                TypeError,
                ValueError,
                IndexError,
                KeyError,
            ):
                continue

            if (
                item_width <= 0
                or item_height <= 0
            ):
                continue

            x0 = float(
                x
            )

            y0 = float(
                y
            )

            x1 = float(
                x
                + item_width
            )

            y1 = float(
                y
                + item_height
            )

            normalized = (
                self._normalize_text(
                    text
                )
            )

            numeric_value, numeric_unit = (
                self._parse_numeric(
                    normalized
                )
            )

            item = OCRTextItem(
                text=
                    text,

                normalized_text=
                    normalized,

                page=
                    raster.page,

                x0=
                    x0,

                y0=
                    y0,

                x1=
                    x1,

                y1=
                    y1,

                center_x=
                    (x0 + x1)
                    / 2.0,

                center_y=
                    (y0 + y1)
                    / 2.0,

                confidence=
                    confidence,

                numeric_value=
                    numeric_value,

                numeric_unit=
                    numeric_unit,
            )

            tokens.append(
                item
            )

            if (
                numeric_value
                is not None
            ):
                dimension_candidates.append(
                    item
                )

            raw_upper = (
                text.strip().upper()
            )

            if (
                self.AXIS_ALPHA_RE
                .fullmatch(
                    raw_upper
                )
                or self.AXIS_NUMERIC_RE
                .fullmatch(
                    text.strip()
                )
            ):
                axis_candidates.append(
                    item
                )

            group_key = (
                self._safe_int(
                    raw,
                    "block_num",
                    index,
                ),
                self._safe_int(
                    raw,
                    "par_num",
                    index,
                ),
                self._safe_int(
                    raw,
                    "line_num",
                    index,
                ),
            )

            line_groups.setdefault(
                group_key,
                [],
            ).append(
                item
            )

        lines = (
            self._build_lines(
                line_groups
            )
        )

        return OCRPlanTextResult(
            page=
                raster.page,

            width_px=
                raster.width_px,

            height_px=
                raster.height_px,

            language=
                language,

            tokens=
                tokens,

            lines=
                lines,

            dimension_candidates=
                dimension_candidates,

            axis_candidates=
                axis_candidates,

            notes=[
                (
                    "Tesseract trabajó sobre el mismo "
                    "raster canónico utilizado por "
                    "OpenCV y Gemini."
                ),
                (
                    "Los números detectados permanecen "
                    "como candidatos; no se asignaron "
                    "automáticamente a espacios."
                ),
                (
                    "El OCR tradicional tiene prioridad "
                    "sobre texto impreso legible; texto "
                    "manuscrito ambiguo permanece apoyado "
                    "por Gemini."
                ),
            ],
        )

    # ========================================================
    # IMAGEN
    # ========================================================

    @staticmethod
    def _open_image(
        raster: DocumentRasterPage,
    ) -> Image.Image:
        if not raster.image_bytes:
            raise ValueError(
                "El raster OCR está vacío."
            )

        try:
            with Image.open(
                BytesIO(
                    raster.image_bytes
                )
            ) as source:
                return source.convert(
                    "RGB"
                )

        except Exception as exc:
            raise ValueError(
                "No fue posible abrir "
                "el raster para OCR."
            ) from exc

    # ========================================================
    # IDIOMA
    # ========================================================

    def _select_language(
        self,
    ) -> str | None:
        try:
            available = set(
                pytesseract.get_languages(
                    config=""
                )
            )

        except Exception:
            available = set()

        preferred = str(
            self.preferred_language
            or ""
        ).strip()

        if (
            preferred
            and preferred
            in available
        ):
            return preferred

        if "spa" in available:
            return "spa"

        if "eng" in available:
            return "eng"

        return None

    # ========================================================
    # LÍNEAS OCR
    # ========================================================

    @staticmethod
    def _build_lines(
        groups: dict[
            tuple[int, int, int],
            list[OCRTextItem],
        ],
    ) -> list[
        OCRTextLine
    ]:
        result: list[
            OCRTextLine
        ] = []

        for items in groups.values():
            if not items:
                continue

            ordered = sorted(
                items,
                key=lambda item:
                    item.x0,
            )

            text = " ".join(
                item.text
                for item
                in ordered
            ).strip()

            if not text:
                continue

            confidence = (
                sum(
                    item.confidence
                    for item
                    in ordered
                )
                / len(
                    ordered
                )
            )

            result.append(
                OCRTextLine(
                    text=
                        text,

                    page=
                        ordered[0].page,

                    x0=
                        min(
                            item.x0
                            for item
                            in ordered
                        ),

                    y0=
                        min(
                            item.y0
                            for item
                            in ordered
                        ),

                    x1=
                        max(
                            item.x1
                            for item
                            in ordered
                        ),

                    y1=
                        max(
                            item.y1
                            for item
                            in ordered
                        ),

                    confidence=
                        confidence,
                )
            )

        return result

    # ========================================================
    # NUMÉRICO
    # ========================================================

    def _parse_numeric(
        self,
        text: str,
    ) -> tuple[
        float | None,
        str | None,
    ]:
        match = (
            self.DIMENSION_RE
            .fullmatch(
                text
            )
        )

        if match is None:
            return None, None

        raw_value = (
            match.group(
                "value"
            )
        )

        try:
            value = float(
                raw_value.replace(
                    ",",
                    ".",
                )
            )

        except ValueError:
            return None, None

        unit = (
            match.group(
                "unit"
            )
        )

        return (
            value,
            unit.lower()
            if unit
            else None,
        )

    # ========================================================
    # NORMALIZACIÓN
    # ========================================================

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str:
        text = str(
            value or ""
        ).strip().lower()

        decomposed = (
            unicodedata.normalize(
                "NFD",
                text,
            )
        )

        without_accents = "".join(
            character
            for character
            in decomposed
            if unicodedata.category(
                character
            ) != "Mn"
        )

        return " ".join(
            without_accents.split()
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    @staticmethod
    def _parse_confidence(
        values: list[Any],
        index: int,
    ) -> float:
        try:
            value = float(
                values[
                    index
                ]
            )

        except (
            TypeError,
            ValueError,
            IndexError,
        ):
            return -1.0

        if value < 0:
            return -1.0

        return min(
            1.0,
            value / 100.0,
        )

    # ========================================================
    # SAFE INT
    # ========================================================

    @staticmethod
    def _safe_int(
        payload: dict[str, Any],
        key: str,
        index: int,
    ) -> int:
        try:
            return int(
                payload[
                    key
                ][
                    index
                ]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ):
            return 0


# ============================================================
# FACTORY
# ============================================================


def get_ocr_plan_text_service(
) -> OCRPlanTextService:
    return OCRPlanTextService()