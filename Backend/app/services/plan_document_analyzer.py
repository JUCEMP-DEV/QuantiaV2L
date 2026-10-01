from __future__ import annotations

from dataclasses import asdict, dataclass, field
from io import BytesIO
from typing import Any

import pymupdf
from PIL import Image, ImageOps


# ============================================================
# MODELOS DOCUMENTALES
# ============================================================


@dataclass(slots=True)
class DocumentTextSpan:
    text: str

    page: int

    x0: float
    y0: float
    x1: float
    y1: float

    font: str | None = None
    size: float | None = None


@dataclass(slots=True)
class DocumentLine:
    page: int

    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(slots=True)
class DocumentPage:
    page: int

    width: float
    height: float

    rotation: int

    unrotated_width: float
    unrotated_height: float

    text_spans: list[
        DocumentTextSpan
    ] = field(
        default_factory=list
    )

    lines: list[
        DocumentLine
    ] = field(
        default_factory=list
    )


# ============================================================
# RASTER CANÓNICO
# ============================================================


@dataclass(slots=True)
class DocumentRasterPage:
    """
    Raster canónico compartido por:

        Gemini
        OpenCV
        OCR/Tesseract
        overlay 04

    Todas las coordenadas raster posteriores deben referirse
    exactamente a width_px / height_px de esta imagen.
    """

    page: int

    width_px: int
    height_px: int

    mime_type: str

    image_bytes: bytes


# ============================================================
# RESULTADO DOCUMENTAL
# ============================================================


@dataclass(slots=True)
class PlanDocumentAnalysis:
    mime_type: str

    document_type: str

    page_count: int

    vector_text_available: bool

    vector_geometry_available: bool

    raster_width_px: int | None = None
    raster_height_px: int | None = None

    pages: list[
        DocumentPage
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
# ANALIZADOR
# ============================================================


class PlanDocumentAnalyzer:
    """
    Analizador determinístico de documentos para Quantia V2.

    ==========================================================
    ENTRADAS SOPORTADAS
    ==========================================================

        application/pdf
        image/jpeg
        image/png

    ==========================================================
    COORDENADAS PDF
    ==========================================================

    Las coordenadas PyMuPDF expuestas por este servicio se
    transforman al sistema VISUAL de la página:

        page.rect

    Esto permite posteriormente relacionarlas con el raster
    renderizado de esa misma página.

    ==========================================================
    RESPONSABILIDAD
    ==========================================================

    Este servicio:

        - identifica si existe contenido vectorial;
        - extrae texto vectorial;
        - extrae líneas vectoriales;
        - genera raster canónico.

    Este servicio NO interpreta:

        - muros;
        - habitaciones;
        - puertas;
        - ventanas;
        - cotas;
        - semántica arquitectónica.
    """

    PDF_MIME_TYPE = (
        "application/pdf"
    )

    SUPPORTED_IMAGE_MIME_TYPES = {
        "image/jpeg",
        "image/png",
    }

    # ========================================================
    # ANÁLISIS DOCUMENTAL
    # ========================================================

    def analyze(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
    ) -> PlanDocumentAnalysis:
        self._validate_document(
            document_bytes=
                document_bytes,

            mime_type=
                mime_type,
        )

        normalized_mime = (
            self._normalize_mime(
                mime_type
            )
        )

        if (
            normalized_mime
            == self.PDF_MIME_TYPE
        ):
            return self._analyze_pdf(
                document_bytes
            )

        return self._analyze_image(
            document_bytes=
                document_bytes,

            mime_type=
                normalized_mime,
        )

    # ========================================================
    # PREPARAR RASTER CANÓNICO
    # ========================================================

    def prepare_raster_pages(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
        render_scale: float,
    ) -> list[
        DocumentRasterPage
    ]:
        """
        Genera exactamente la imagen que debe compartirse entre:

            Gemini
            OpenCV
            OCR
            coordinate mappers

        PDF:
            se renderiza con PyMuPDF.

        JPG/PNG:
            se normaliza orientación EXIF y se convierte a PNG.

        render_scale es obligatorio para evitar introducir
        silenciosamente una resolución PDF no acordada.
        """

        self._validate_document(
            document_bytes=
                document_bytes,

            mime_type=
                mime_type,
        )

        normalized_mime = (
            self._normalize_mime(
                mime_type
            )
        )

        if (
            normalized_mime
            == self.PDF_MIME_TYPE
        ):
            return self._render_pdf_pages(
                document_bytes=
                    document_bytes,

                render_scale=
                    render_scale,
            )

        return [
            self._normalize_image_raster(
                document_bytes=
                    document_bytes
            )
        ]

    # ========================================================
    # PDF — ANÁLISIS
    # ========================================================

    def _analyze_pdf(
        self,
        document_bytes: bytes,
    ) -> PlanDocumentAnalysis:
        try:
            document = pymupdf.open(
                stream=
                    document_bytes,

                filetype=
                    "pdf",
            )

        except Exception as exc:
            raise ValueError(
                "No fue posible abrir el PDF "
                "con PyMuPDF."
            ) from exc

        pages: list[
            DocumentPage
        ] = []

        total_text_spans = 0
        total_lines = 0

        try:
            for page_index in range(
                document.page_count
            ):
                page = (
                    document.load_page(
                        page_index
                    )
                )

                page_number = (
                    page_index + 1
                )

                visual_rect = (
                    page.rect
                )

                unrotated_rect = (
                    page.cropbox
                )

                text_spans = (
                    self._extract_text_spans(
                        page,
                        page_number,
                    )
                )

                lines = (
                    self._extract_lines(
                        page,
                        page_number,
                    )
                )

                total_text_spans += len(
                    text_spans
                )

                total_lines += len(
                    lines
                )

                pages.append(
                    DocumentPage(
                        page=
                            page_number,

                        width=
                            float(
                                visual_rect.width
                            ),

                        height=
                            float(
                                visual_rect.height
                            ),

                        rotation=
                            int(
                                page.rotation
                            ),

                        unrotated_width=
                            float(
                                unrotated_rect
                                .width
                            ),

                        unrotated_height=
                            float(
                                unrotated_rect
                                .height
                            ),

                        text_spans=
                            text_spans,

                        lines=
                            lines,
                    )
                )

        finally:
            document.close()

        vector_text_available = (
            total_text_spans > 0
        )

        vector_geometry_available = (
            total_lines > 0
        )

        if (
            vector_text_available
            or vector_geometry_available
        ):
            document_type = (
                "pdf_vector_or_hybrid"
            )

        else:
            document_type = (
                "pdf_raster_or_scanned"
            )

        notes: list[str] = []

        if vector_text_available:
            notes.append(
                "El PDF contiene texto vectorial "
                "extraíble con coordenadas."
            )

        else:
            notes.append(
                "No se detectó texto vectorial "
                "extraíble."
            )

        if vector_geometry_available:
            notes.append(
                "El PDF contiene segmentos "
                "vectoriales extraíbles."
            )

        else:
            notes.append(
                "No se detectó geometría vectorial "
                "utilizable."
            )

        if any(
            page.rotation != 0
            for page
            in pages
        ):
            notes.append(
                "Las coordenadas PDF fueron transformadas "
                "al sistema visual de page.rect."
            )

        return PlanDocumentAnalysis(
            mime_type=
                self.PDF_MIME_TYPE,

            document_type=
                document_type,

            page_count=
                len(
                    pages
                ),

            vector_text_available=
                vector_text_available,

            vector_geometry_available=
                vector_geometry_available,

            raster_width_px=
                None,

            raster_height_px=
                None,

            pages=
                pages,

            notes=
                notes,
        )

    # ========================================================
    # PDF — TEXTO
    # ========================================================

    @staticmethod
    def _extract_text_spans(
        page: pymupdf.Page,
        page_number: int,
    ) -> list[
        DocumentTextSpan
    ]:
        result: list[
            DocumentTextSpan
        ] = []

        raw = page.get_text(
            "dict"
        )

        rotation_matrix = (
            page.rotation_matrix
        )

        for block in raw.get(
            "blocks",
            [],
        ):
            if not isinstance(
                block,
                dict,
            ):
                continue

            lines = block.get(
                "lines"
            )

            if not isinstance(
                lines,
                list,
            ):
                continue

            for line in lines:
                if not isinstance(
                    line,
                    dict,
                ):
                    continue

                spans = line.get(
                    "spans"
                )

                if not isinstance(
                    spans,
                    list,
                ):
                    continue

                for span in spans:
                    if not isinstance(
                        span,
                        dict,
                    ):
                        continue

                    text = str(
                        span.get(
                            "text",
                            "",
                        )
                    ).strip()

                    if not text:
                        continue

                    bbox = span.get(
                        "bbox"
                    )

                    if (
                        not isinstance(
                            bbox,
                            (list, tuple),
                        )
                        or len(
                            bbox
                        )
                        != 4
                    ):
                        continue

                    rect = pymupdf.Rect(
                        float(
                            bbox[0]
                        ),
                        float(
                            bbox[1]
                        ),
                        float(
                            bbox[2]
                        ),
                        float(
                            bbox[3]
                        ),
                    )

                    visual_rect = (
                        rect
                        * rotation_matrix
                    )

                    size = (
                        span.get(
                            "size"
                        )
                    )

                    result.append(
                        DocumentTextSpan(
                            text=
                                text,

                            page=
                                page_number,

                            x0=
                                float(
                                    visual_rect.x0
                                ),

                            y0=
                                float(
                                    visual_rect.y0
                                ),

                            x1=
                                float(
                                    visual_rect.x1
                                ),

                            y1=
                                float(
                                    visual_rect.y1
                                ),

                            font=(
                                str(
                                    span.get(
                                        "font"
                                    )
                                )
                                if span.get(
                                    "font"
                                )
                                else None
                            ),

                            size=(
                                float(
                                    size
                                )
                                if isinstance(
                                    size,
                                    (int, float),
                                )
                                else None
                            ),
                        )
                    )

        return result

    # ========================================================
    # PDF — GEOMETRÍA VECTORIAL
    # ========================================================

    @staticmethod
    def _extract_lines(
        page: pymupdf.Page,
        page_number: int,
    ) -> list[
        DocumentLine
    ]:
        result: list[
            DocumentLine
        ] = []

        try:
            drawings = (
                page.get_drawings()
            )

        except Exception:
            return []

        rotation_matrix = (
            page.rotation_matrix
        )

        for drawing in drawings:
            if not isinstance(
                drawing,
                dict,
            ):
                continue

            items = drawing.get(
                "items",
                [],
            )

            if not isinstance(
                items,
                list,
            ):
                continue

            for item in items:
                if (
                    not isinstance(
                        item,
                        tuple,
                    )
                    or not item
                ):
                    continue

                command = (
                    item[0]
                )

                if (
                    command != "l"
                    or len(
                        item
                    )
                    < 3
                ):
                    continue

                p1 = item[1]
                p2 = item[2]

                if (
                    not hasattr(
                        p1,
                        "x",
                    )
                    or not hasattr(
                        p1,
                        "y",
                    )
                    or not hasattr(
                        p2,
                        "x",
                    )
                    or not hasattr(
                        p2,
                        "y",
                    )
                ):
                    continue

                original_p1 = (
                    pymupdf.Point(
                        float(
                            p1.x
                        ),
                        float(
                            p1.y
                        ),
                    )
                )

                original_p2 = (
                    pymupdf.Point(
                        float(
                            p2.x
                        ),
                        float(
                            p2.y
                        ),
                    )
                )

                visual_p1 = (
                    original_p1
                    * rotation_matrix
                )

                visual_p2 = (
                    original_p2
                    * rotation_matrix
                )

                result.append(
                    DocumentLine(
                        page=
                            page_number,

                        x1=
                            float(
                                visual_p1.x
                            ),

                        y1=
                            float(
                                visual_p1.y
                            ),

                        x2=
                            float(
                                visual_p2.x
                            ),

                        y2=
                            float(
                                visual_p2.y
                            ),
                    )
                )

        return result

    # ========================================================
    # PDF — RENDER CANÓNICO
    # ========================================================

    def _render_pdf_pages(
        self,
        *,
        document_bytes: bytes,
        render_scale: float,
    ) -> list[
        DocumentRasterPage
    ]:
        if isinstance(
            render_scale,
            bool,
        ):
            raise ValueError(
                "render_scale inválido."
            )

        if not isinstance(
            render_scale,
            (int, float),
        ):
            raise ValueError(
                "render_scale debe ser numérico."
            )

        render_scale = float(
            render_scale
        )

        if render_scale <= 0:
            raise ValueError(
                "render_scale debe ser mayor que cero."
            )

        try:
            document = pymupdf.open(
                stream=
                    document_bytes,

                filetype=
                    "pdf",
            )

        except Exception as exc:
            raise ValueError(
                "No fue posible abrir el PDF "
                "para generar el raster."
            ) from exc

        result: list[
            DocumentRasterPage
        ] = []

        matrix = pymupdf.Matrix(
            render_scale,
            render_scale,
        )

        try:
            for page_index in range(
                document.page_count
            ):
                page = (
                    document.load_page(
                        page_index
                    )
                )

                pixmap = (
                    page.get_pixmap(
                        matrix=
                            matrix,

                        alpha=
                            False,
                    )
                )

                image_bytes = (
                    pixmap.tobytes(
                        "png"
                    )
                )

                result.append(
                    DocumentRasterPage(
                        page=
                            page_index + 1,

                        width_px=
                            int(
                                pixmap.width
                            ),

                        height_px=
                            int(
                                pixmap.height
                            ),

                        mime_type=
                            "image/png",

                        image_bytes=
                            image_bytes,
                    )
                )

        finally:
            document.close()

        return result

    # ========================================================
    # IMAGEN — ANÁLISIS
    # ========================================================

    def _analyze_image(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
    ) -> PlanDocumentAnalysis:
        try:
            with Image.open(
                BytesIO(
                    document_bytes
                )
            ) as source:
                image = (
                    ImageOps.exif_transpose(
                        source
                    )
                )

                width, height = (
                    image.size
                )

        except Exception as exc:
            raise ValueError(
                "No fue posible abrir la imagen."
            ) from exc

        return PlanDocumentAnalysis(
            mime_type=
                mime_type,

            document_type=
                "raster_image",

            page_count=
                1,

            vector_text_available=
                False,

            vector_geometry_available=
                False,

            raster_width_px=
                int(
                    width
                ),

            raster_height_px=
                int(
                    height
                ),

            pages=
                [],

            notes=[
                (
                    "El documento es una imagen raster. "
                    "No existe autoridad vectorial."
                )
            ],
        )

    # ========================================================
    # IMAGEN — RASTER CANÓNICO
    # ========================================================

    @staticmethod
    def _normalize_image_raster(
        *,
        document_bytes: bytes,
    ) -> DocumentRasterPage:
        try:
            with Image.open(
                BytesIO(
                    document_bytes
                )
            ) as source:
                image = (
                    ImageOps.exif_transpose(
                        source
                    )
                )

                image = image.convert(
                    "RGB"
                )

                output = (
                    BytesIO()
                )

                image.save(
                    output,
                    format=
                        "PNG",
                )

                width, height = (
                    image.size
                )

                normalized_bytes = (
                    output.getvalue()
                )

        except Exception as exc:
            raise ValueError(
                "No fue posible normalizar "
                "la imagen raster."
            ) from exc

        return DocumentRasterPage(
            page=
                1,

            width_px=
                int(
                    width
                ),

            height_px=
                int(
                    height
                ),

            mime_type=
                "image/png",

            image_bytes=
                normalized_bytes,
        )

    # ========================================================
    # VALIDACIÓN DOCUMENTO
    # ========================================================

    def _validate_document(
        self,
        *,
        document_bytes: bytes,
        mime_type: str,
    ) -> None:
        if not document_bytes:
            raise ValueError(
                "El documento está vacío."
            )

        normalized_mime = (
            self._normalize_mime(
                mime_type
            )
        )

        supported = (
            {
                self.PDF_MIME_TYPE,
            }
            | self.SUPPORTED_IMAGE_MIME_TYPES
        )

        if normalized_mime not in supported:
            raise ValueError(
                "Tipo de documento no soportado: "
                f"{normalized_mime or 'desconocido'}"
            )

    # ========================================================
    # MIME
    # ========================================================

    @staticmethod
    def _normalize_mime(
        value: Any,
    ) -> str:
        return str(
            value or ""
        ).strip().lower()


# ============================================================
# FACTORY
# ============================================================


def get_plan_document_analyzer(
) -> PlanDocumentAnalyzer:
    return PlanDocumentAnalyzer()