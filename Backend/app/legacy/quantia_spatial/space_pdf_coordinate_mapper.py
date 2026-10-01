from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.plan_document_analyzer import (
    PlanDocumentAnalysis,
)


# ============================================================
# BBOX NORMALIZADO
# ============================================================


@dataclass(slots=True, frozen=True)
class NormalizedBBox:
    """
    Región Gemini en coordenadas normalizadas 0..1.

    No representa geometría arquitectónica final.
    """

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return (
            self.x_max
            - self.x_min
        )

    @property
    def height(self) -> float:
        return (
            self.y_max
            - self.y_min
        )

    @property
    def center_x(self) -> float:
        return (
            self.x_min
            + self.x_max
        ) / 2.0

    @property
    def center_y(self) -> float:
        return (
            self.y_min
            + self.y_max
        ) / 2.0


# ============================================================
# BBOX RASTER
# ============================================================


@dataclass(slots=True, frozen=True)
class RasterBBox:
    """
    Región en píxeles del raster canónico.

    Este es el sistema compartido por:

        Gemini
        OpenCV
        OCR/Tesseract
        overlays de 04
    """

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return (
            self.x_max
            - self.x_min
        )

    @property
    def height(self) -> float:
        return (
            self.y_max
            - self.y_min
        )

    @property
    def center_x(self) -> float:
        return (
            self.x_min
            + self.x_max
        ) / 2.0

    @property
    def center_y(self) -> float:
        return (
            self.y_min
            + self.y_max
        ) / 2.0


# ============================================================
# BBOX PDF
# ============================================================


@dataclass(slots=True, frozen=True)
class PDFBBox:
    """
    Región en coordenadas visuales PyMuPDF.

    Unidad:

        puntos PDF

    Origen:

        superior izquierdo

    Igual que page.rect y el raster renderizado.
    """

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return (
            self.x_max
            - self.x_min
        )

    @property
    def height(self) -> float:
        return (
            self.y_max
            - self.y_min
        )

    @property
    def center_x(self) -> float:
        return (
            self.x_min
            + self.x_max
        ) / 2.0

    @property
    def center_y(self) -> float:
        return (
            self.y_min
            + self.y_max
        ) / 2.0


# ============================================================
# LOCALIZACIÓN DE NIVEL
# ============================================================


@dataclass(slots=True)
class MappedLevelLocalization:
    nombre: str

    localizado: bool

    confianza: float

    bbox_normalizado: (
        NormalizedBBox
        | None
    )

    bbox_raster: (
        RasterBBox
        | None
    )

    bbox_pdf: (
        PDFBBox
        | None
    )

    motivo_no_localizado: (
        str
        | None
    ) = None


# ============================================================
# LOCALIZACIÓN DE ESPACIO
# ============================================================


@dataclass(slots=True)
class MappedSpaceLocalization:
    nivel: str

    id_propuesto: str

    nombre: str

    localizado: bool

    confianza: float

    bbox_normalizado: (
        NormalizedBBox
        | None
    )

    bbox_raster: (
        RasterBBox
        | None
    )

    bbox_pdf: (
        PDFBBox
        | None
    )

    evidencia: list[
        str
    ] = field(
        default_factory=list
    )

    motivo_no_localizado: (
        str
        | None
    ) = None


# ============================================================
# DIAGNÓSTICO DE TRANSFORMACIÓN
# ============================================================


@dataclass(slots=True)
class PDFRenderDiagnostics:
    """
    Relación exacta entre:

        página PDF visual
        ↔
        raster canónico

    No aplica umbrales ni decide si una diferencia es
    aceptable. Solo expone las magnitudes observadas.
    """

    pdf_width_pt: float
    pdf_height_pt: float

    image_width_px: int
    image_height_px: int

    pdf_aspect_ratio: float
    image_aspect_ratio: float

    aspect_ratio_difference: float
    aspect_ratio_relative_difference: float

    px_per_pdf_x: float
    px_per_pdf_y: float

    pdf_per_px_x: float
    pdf_per_px_y: float

    scale_difference: float
    scale_relative_difference: float

    dpi_x: float
    dpi_y: float


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class SpacePDFCoordinateMapping:
    page: int

    page_width: float
    page_height: float

    image_width_px: int
    image_height_px: int

    diagnostics: PDFRenderDiagnostics

    levels: list[
        MappedLevelLocalization
    ] = field(
        default_factory=list
    )

    spaces: list[
        MappedSpaceLocalization
    ] = field(
        default_factory=list
    )

    notes: list[
        str
    ] = field(
        default_factory=list
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


# ============================================================
# MAPPER
# ============================================================


class SpacePDFCoordinateMapper:
    """
    Lleva las localizaciones Gemini a los sistemas de
    coordenadas utilizados por Quantia.

    ==========================================================
    CADENA
    ==========================================================

        Gemini bbox 0..1
            ↓
        NormalizedBBox
            ↓
        raster canónico px
            ↓
        RasterBBox
            ↓
        relación PDF/raster observada
            ↓
        PDFBBox

    ==========================================================
    PRINCIPIO
    ==========================================================

    El raster recibido aquí debe ser EXACTAMENTE el mismo
    DocumentRasterPage enviado a:

        Gemini
        OpenCV
        OCR

    No se reconstruyen dimensiones raster a partir del PDF.

    No se supone un DPI.

    No se supone un render_scale.

    Se utilizan las dimensiones reales del raster.

    ==========================================================
    IMPORTANTE
    ==========================================================

    Un bbox Gemini representa una región aproximada.

    NO representa:

        - muro;
        - polígono final;
        - ancho arquitectónico;
        - largo arquitectónico;
        - área;
        - dimensión métrica.
    """

    # ========================================================
    # API
    # ========================================================

    def map(
        self,
        *,
        analysis: PlanDocumentAnalysis,
        localization_payload: dict[
            str,
            Any,
        ],
        image_width_px: int,
        image_height_px: int,
    ) -> SpacePDFCoordinateMapping:
        if not isinstance(
            localization_payload,
            dict,
        ):
            raise ValueError(
                "La localización Gemini debe ser "
                "un objeto JSON."
            )

        if not analysis.pages:
            raise ValueError(
                "El análisis PDF no contiene páginas."
            )

        image_width = (
            self._positive_int(
                image_width_px,
                "image_width_px",
            )
        )

        image_height = (
            self._positive_int(
                image_height_px,
                "image_height_px",
            )
        )

        page_number = (
            self._parse_page_number(
                localization_payload.get(
                    "pagina"
                )
            )
        )

        if (
            page_number < 1
            or page_number
            > len(
                analysis.pages
            )
        ):
            raise ValueError(
                "La página indicada por Gemini "
                "no existe en el PDF."
            )

        page = (
            analysis.pages[
                page_number - 1
            ]
        )

        page_width = float(
            page.width
        )

        page_height = float(
            page.height
        )

        if (
            page_width <= 0
            or page_height <= 0
        ):
            raise ValueError(
                "La página PDF tiene dimensiones "
                "inválidas."
            )

        diagnostics = (
            self._build_diagnostics(
                page_width=
                    page_width,

                page_height=
                    page_height,

                image_width_px=
                    image_width,

                image_height_px=
                    image_height,
            )
        )

        levels_payload = (
            localization_payload.get(
                "niveles"
            )
        )

        if not isinstance(
            levels_payload,
            list,
        ):
            raise ValueError(
                "El campo niveles no es una lista."
            )

        mapped_levels: list[
            MappedLevelLocalization
        ] = []

        mapped_spaces: list[
            MappedSpaceLocalization
        ] = []

        # ====================================================
        # NIVELES
        # ====================================================

        for level in levels_payload:
            if not isinstance(
                level,
                dict,
            ):
                continue

            level_name = str(
                level.get(
                    "nombre",
                    "",
                )
            ).strip()

            if not level_name:
                continue

            requested_localization = (
                level.get(
                    "localizado"
                )
                is True
            )

            (
                level_localized,
                level_normalized,
                level_raster,
                level_pdf,
                level_reason,
            ) = self._map_optional_bbox(
                requested=
                    requested_localization,

                bbox_payload=
                    level.get(
                        "bbox_normalizado"
                    ),

                diagnostics=
                    diagnostics,
            )

            if (
                not requested_localization
            ):
                level_reason = (
                    self._nullable_text(
                        level.get(
                            "motivo_no_localizado"
                        )
                    )
                )

            mapped_levels.append(
                MappedLevelLocalization(
                    nombre=
                        level_name,

                    localizado=
                        level_localized,

                    confianza=
                        self._confidence(
                            level.get(
                                "confianza"
                            )
                        ),

                    bbox_normalizado=
                        level_normalized,

                    bbox_raster=
                        level_raster,

                    bbox_pdf=
                        level_pdf,

                    motivo_no_localizado=
                        level_reason,
                )
            )

            # =================================================
            # ESPACIOS
            # =================================================

            spaces_payload = (
                level.get(
                    "espacios"
                )
            )

            if not isinstance(
                spaces_payload,
                list,
            ):
                continue

            for space in spaces_payload:
                if not isinstance(
                    space,
                    dict,
                ):
                    continue

                space_id = str(
                    space.get(
                        "id_propuesto",
                        "",
                    )
                ).strip()

                if not space_id:
                    continue

                space_name = str(
                    space.get(
                        "nombre",
                        "",
                    )
                ).strip()

                requested_space_localization = (
                    space.get(
                        "localizado"
                    )
                    is True
                )

                (
                    space_localized,
                    space_normalized,
                    space_raster,
                    space_pdf,
                    space_reason,
                ) = self._map_optional_bbox(
                    requested=
                        requested_space_localization,

                    bbox_payload=
                        space.get(
                            "bbox_normalizado"
                        ),

                    diagnostics=
                        diagnostics,
                )

                if (
                    not requested_space_localization
                ):
                    space_reason = (
                        self._nullable_text(
                            space.get(
                                "motivo_no_localizado"
                            )
                        )
                    )

                mapped_spaces.append(
                    MappedSpaceLocalization(
                        nivel=
                            level_name,

                        id_propuesto=
                            space_id,

                        nombre=
                            space_name,

                        localizado=
                            space_localized,

                        confianza=
                            self._confidence(
                                space.get(
                                    "confianza"
                                )
                            ),

                        bbox_normalizado=
                            space_normalized,

                        bbox_raster=
                            space_raster,

                        bbox_pdf=
                            space_pdf,

                        evidencia=
                            self._string_list(
                                space.get(
                                    "evidencia"
                                )
                            ),

                        motivo_no_localizado=
                            space_reason,
                    )
                )

        return SpacePDFCoordinateMapping(
            page=
                page_number,

            page_width=
                page_width,

            page_height=
                page_height,

            image_width_px=
                image_width,

            image_height_px=
                image_height,

            diagnostics=
                diagnostics,

            levels=
                mapped_levels,

            spaces=
                mapped_spaces,

            notes=[
                (
                    "Las localizaciones Gemini fueron "
                    "mapeadas primero al raster canónico."
                ),
                (
                    "Las coordenadas raster se transformaron "
                    "posteriormente al sistema visual PDF."
                ),
                (
                    "PyMuPDF y el raster utilizan origen "
                    "superior izquierdo; no se invirtió Y."
                ),
                (
                    "Las dimensiones reales del raster son "
                    "obligatorias; no se infirió DPI ni "
                    "render_scale."
                ),
                (
                    "Los bbox siguen siendo regiones "
                    "aproximadas y no geometría "
                    "arquitectónica final."
                ),
            ],
        )

    # ========================================================
    # MAPEO OPCIONAL
    # ========================================================

    def _map_optional_bbox(
        self,
        *,
        requested: bool,
        bbox_payload: Any,
        diagnostics: PDFRenderDiagnostics,
    ) -> tuple[
        bool,
        NormalizedBBox | None,
        RasterBBox | None,
        PDFBBox | None,
        str | None,
    ]:
        if not requested:
            return (
                False,
                None,
                None,
                None,
                None,
            )

        try:
            normalized = (
                self._parse_normalized_bbox(
                    bbox_payload
                )
            )

            raster = (
                self._normalized_to_raster(
                    bbox=
                        normalized,

                    image_width_px=
                        diagnostics
                        .image_width_px,

                    image_height_px=
                        diagnostics
                        .image_height_px,
                )
            )

            pdf = (
                self._raster_to_pdf(
                    bbox=
                        raster,

                    diagnostics=
                        diagnostics,
                )
            )

        except ValueError as exc:
            # Una bbox inválida no debe tirar el análisis
            # completo de la página.
            return (
                False,
                None,
                None,
                None,
                str(
                    exc
                ),
            )

        return (
            True,
            normalized,
            raster,
            pdf,
            None,
        )

    # ========================================================
    # PARSE BBOX NORMALIZADO
    # ========================================================

    @staticmethod
    def _parse_normalized_bbox(
        bbox: Any,
    ) -> NormalizedBBox:
        if not isinstance(
            bbox,
            dict,
        ):
            raise ValueError(
                "Se esperaba bbox_normalizado."
            )

        try:
            x_min = float(
                bbox[
                    "x_min"
                ]
            )

            y_min = float(
                bbox[
                    "y_min"
                ]
            )

            x_max = float(
                bbox[
                    "x_max"
                ]
            )

            y_max = float(
                bbox[
                    "y_max"
                ]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "bbox_normalizado inválido."
            ) from exc

        if not (
            0.0
            <= x_min
            < x_max
            <= 1.0
        ):
            raise ValueError(
                "Coordenadas X normalizadas "
                "inválidas."
            )

        if not (
            0.0
            <= y_min
            < y_max
            <= 1.0
        ):
            raise ValueError(
                "Coordenadas Y normalizadas "
                "inválidas."
            )

        return NormalizedBBox(
            x_min=
                x_min,

            y_min=
                y_min,

            x_max=
                x_max,

            y_max=
                y_max,
        )

    # ========================================================
    # NORMALIZADO → RASTER
    # ========================================================

    @staticmethod
    def _normalized_to_raster(
        *,
        bbox: NormalizedBBox,
        image_width_px: int,
        image_height_px: int,
    ) -> RasterBBox:
        return RasterBBox(
            x_min=(
                bbox.x_min
                * image_width_px
            ),

            y_min=(
                bbox.y_min
                * image_height_px
            ),

            x_max=(
                bbox.x_max
                * image_width_px
            ),

            y_max=(
                bbox.y_max
                * image_height_px
            ),
        )

    # ========================================================
    # RASTER → PDF
    # ========================================================

    @staticmethod
    def _raster_to_pdf(
        *,
        bbox: RasterBBox,
        diagnostics: PDFRenderDiagnostics,
    ) -> PDFBBox:
        """
        La transformación se hace desde el raster real,
        no directamente desde el bbox normalizado.

        Esto mantiene una única cadena de coordenadas:

            Gemini
            ↓
            raster
            ↓
            PDF
        """

        return PDFBBox(
            x_min=(
                bbox.x_min
                * diagnostics.pdf_per_px_x
            ),

            y_min=(
                bbox.y_min
                * diagnostics.pdf_per_px_y
            ),

            x_max=(
                bbox.x_max
                * diagnostics.pdf_per_px_x
            ),

            y_max=(
                bbox.y_max
                * diagnostics.pdf_per_px_y
            ),
        )

    # ========================================================
    # PDF → RASTER
    # ========================================================

    @staticmethod
    def pdf_bbox_to_raster(
        *,
        bbox: PDFBBox,
        diagnostics: PDFRenderDiagnostics,
    ) -> RasterBBox:
        """
        Helper para llevar evidencia PyMuPDF al mismo
        sistema raster usado por Gemini/OpenCV/OCR.
        """

        return RasterBBox(
            x_min=(
                bbox.x_min
                * diagnostics.px_per_pdf_x
            ),

            y_min=(
                bbox.y_min
                * diagnostics.px_per_pdf_y
            ),

            x_max=(
                bbox.x_max
                * diagnostics.px_per_pdf_x
            ),

            y_max=(
                bbox.y_max
                * diagnostics.px_per_pdf_y
            ),
        )

    # ========================================================
    # DIAGNÓSTICO PDF ↔ RASTER
    # ========================================================

    @staticmethod
    def _build_diagnostics(
        *,
        page_width: float,
        page_height: float,
        image_width_px: int,
        image_height_px: int,
    ) -> PDFRenderDiagnostics:
        if (
            page_width <= 0
            or page_height <= 0
        ):
            raise ValueError(
                "Dimensiones PDF inválidas."
            )

        if (
            image_width_px <= 0
            or image_height_px <= 0
        ):
            raise ValueError(
                "Dimensiones raster inválidas."
            )

        pdf_aspect_ratio = (
            page_width
            / page_height
        )

        image_aspect_ratio = (
            image_width_px
            / image_height_px
        )

        aspect_difference = abs(
            pdf_aspect_ratio
            - image_aspect_ratio
        )

        aspect_relative_difference = (
            aspect_difference
            / pdf_aspect_ratio
            if pdf_aspect_ratio
            > 0
            else 0.0
        )

        px_per_pdf_x = (
            image_width_px
            / page_width
        )

        px_per_pdf_y = (
            image_height_px
            / page_height
        )

        pdf_per_px_x = (
            page_width
            / image_width_px
        )

        pdf_per_px_y = (
            page_height
            / image_height_px
        )

        scale_difference = abs(
            px_per_pdf_x
            - px_per_pdf_y
        )

        reference_scale = max(
            px_per_pdf_x,
            px_per_pdf_y,
        )

        scale_relative_difference = (
            scale_difference
            / reference_scale
            if reference_scale
            > 0
            else 0.0
        )

        # 72 PDF points = 1 pulgada.
        dpi_x = (
            px_per_pdf_x
            * 72.0
        )

        dpi_y = (
            px_per_pdf_y
            * 72.0
        )

        return PDFRenderDiagnostics(
            pdf_width_pt=
                page_width,

            pdf_height_pt=
                page_height,

            image_width_px=
                image_width_px,

            image_height_px=
                image_height_px,

            pdf_aspect_ratio=
                pdf_aspect_ratio,

            image_aspect_ratio=
                image_aspect_ratio,

            aspect_ratio_difference=
                aspect_difference,

            aspect_ratio_relative_difference=
                aspect_relative_difference,

            px_per_pdf_x=
                px_per_pdf_x,

            px_per_pdf_y=
                px_per_pdf_y,

            pdf_per_px_x=
                pdf_per_px_x,

            pdf_per_px_y=
                pdf_per_px_y,

            scale_difference=
                scale_difference,

            scale_relative_difference=
                scale_relative_difference,

            dpi_x=
                dpi_x,

            dpi_y=
                dpi_y,
        )

    # ========================================================
    # PAGE NUMBER
    # ========================================================

    @staticmethod
    def _parse_page_number(
        value: Any,
    ) -> int:
        if isinstance(
            value,
            bool,
        ):
            raise ValueError(
                "Número de página inválido."
            )

        try:
            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Número de página inválido."
            ) from exc

        if number <= 0:
            raise ValueError(
                "Número de página inválido."
            )

        return number

    # ========================================================
    # POSITIVE INT
    # ========================================================

    @staticmethod
    def _positive_int(
        value: Any,
        name: str,
    ) -> int:
        if isinstance(
            value,
            bool,
        ):
            raise ValueError(
                f"{name} inválido."
            )

        try:
            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"{name} inválido."
            ) from exc

        if number <= 0:
            raise ValueError(
                f"{name} debe ser mayor que cero."
            )

        return number

    # ========================================================
    # CONFIDENCE
    # ========================================================

    @staticmethod
    def _confidence(
        value: Any,
    ) -> float:
        if isinstance(
            value,
            bool,
        ):
            return 0.0

        if not isinstance(
            value,
            (int, float),
        ):
            return 0.0

        result = float(
            value
        )

        return max(
            0.0,
            min(
                1.0,
                result,
            ),
        )

    # ========================================================
    # STRING LIST
    # ========================================================

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            text
            for text
            in (
                str(
                    item or ""
                ).strip()
                for item
                in value
            )
            if text
        ]

    # ========================================================
    # NULLABLE TEXT
    # ========================================================

    @staticmethod
    def _nullable_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(
            value
        ).strip()

        return (
            text
            if text
            else None
        )


# ============================================================
# FACTORY
# ============================================================


def get_space_pdf_coordinate_mapper(
) -> SpacePDFCoordinateMapper:
    return SpacePDFCoordinateMapper()