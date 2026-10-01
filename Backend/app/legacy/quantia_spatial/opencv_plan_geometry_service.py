from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from io import BytesIO
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.services.plan_document_analyzer import (
    DocumentRasterPage,
)

# ============================================================
# MODELOS BÁSICOS
# ============================================================


@dataclass(slots=True, frozen=True)
class RasterPoint:
    x: float
    y: float


@dataclass(slots=True)
class RasterLineSegment:
    """
    Segmento geométrico detectado por OpenCV.

    IMPORTANTE:

        línea detectada != muro

    El segmento representa únicamente evidencia raster.
    """

    id: str

    x1: float
    y1: float
    x2: float
    y2: float

    length_px: float

    orientation: str

    angle_deg: float

    source: str

    confidence: float

    merged_from: list[str] = field(default_factory=list)

    @property
    def midpoint_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def midpoint_y(self) -> float:
        return (self.y1 + self.y2) / 2.0


@dataclass(slots=True)
class RasterIntersection:
    id: str

    x: float
    y: float

    horizontal_segment_id: str
    vertical_segment_id: str

    source: str = "opencv"


@dataclass(slots=True)
class RasterContourCandidate:
    """
    Contorno raster candidato.

    No equivale automáticamente a un espacio.
    """

    id: str

    area_px2: float
    perimeter_px: float

    x: int
    y: int
    width: int
    height: int

    closed: bool

    source: str = "opencv"


# ============================================================
# PARÁMETROS EFECTIVOS
# ============================================================


@dataclass(slots=True)
class OpenCVEffectiveParameters:
    image_width_px: int
    image_height_px: int

    otsu_threshold: float

    canny_low: int
    canny_high: int

    directional_kernel_horizontal: int
    directional_kernel_vertical: int

    hough_threshold: int

    min_line_length_px: int
    max_line_gap_px: int

    axis_tolerance_px: float
    merge_gap_px: float

    deskew_angle_deg: float

    deskew_applied: bool


# ============================================================
# DIAGNÓSTICO
# ============================================================


@dataclass(slots=True)
class OpenCVGeometryDiagnostics:
    dark_pixel_ratio: float

    raw_hough_segments: int

    horizontal_raw_segments: int
    vertical_raw_segments: int
    other_raw_segments: int

    merged_horizontal_segments: int
    merged_vertical_segments: int

    intersections: int

    contour_candidates: int

    parameters: OpenCVEffectiveParameters


# ============================================================
# RESULTADO
# ============================================================


@dataclass(slots=True)
class OpenCVPlanGeometryResult:
    """
    Evidencia geométrica raster de una página.

    Toda la geometría permanece en coordenadas PIXEL del
    DocumentRasterPage recibido.

    Esto garantiza que pueda cruzarse directamente con:

        Gemini
        OCR
        bbox raster

    y, para PDF, proyectarse posteriormente al sistema PDF.
    """

    page: int

    width_px: int
    height_px: int

    horizontal_segments: list[RasterLineSegment] = field(default_factory=list)

    vertical_segments: list[RasterLineSegment] = field(default_factory=list)

    other_segments: list[RasterLineSegment] = field(default_factory=list)

    intersections: list[RasterIntersection] = field(default_factory=list)

    contours: list[RasterContourCandidate] = field(default_factory=list)

    diagnostics: OpenCVGeometryDiagnostics | None = None

    notes: list[str] = field(default_factory=list)

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# CONFIGURACIÓN
# ============================================================


@dataclass(slots=True)
class OpenCVGeometryConfig:
    """
    Configuración del pipeline.

    Cuando un parámetro queda en None se calcula respecto a
    las dimensiones del raster.

    Así evitamos usar valores absolutos diseñados para una
    resolución específica.

    Una vez cerrado el benchmark Miguel H / croquis podremos
    congelar un perfil validado si demuestra estabilidad.
    """

    apply_deskew: bool = False

    canny_sigma: float = 0.33

    directional_kernel_ratio: float = 0.025

    hough_threshold_ratio: float = 0.018

    min_line_length_ratio: float = 0.025

    max_line_gap_ratio: float = 0.006

    axis_tolerance_ratio: float = 0.0025

    merge_gap_ratio: float = 0.0075

    minimum_contour_area_ratio: float = 0.0001


# ============================================================
# SERVICIO
# ============================================================


class OpenCVPlanGeometryService:
    """
    Extracción geométrica raster para Quantia V2.

    ==========================================================
    PROCESO
    ==========================================================

    DocumentRasterPage
          ↓
    decodificación
          ↓
    escala de grises
          ↓
    binarización Otsu
          ↓
    detección de orientación dominante
          ↓
    deskew si corresponde
          ↓
    máscara de líneas horizontales/verticales
          ↓
    Canny
          ↓
    HoughLinesP
          ↓
    clasificación horizontal/vertical
          ↓
    agrupación de segmentos colineales
          ↓
    continuidad
          ↓
    intersecciones
          ↓
    contornos candidatos
          ↓
    evidencia geométrica para reconciliador


    ==========================================================
    RESPONSABILIDAD
    ==========================================================

    OpenCV detecta:

        - trazos;
        - líneas;
        - continuidad;
        - intersecciones;
        - contornos.

    OpenCV NO decide:

        - qué línea es muro;
        - qué contorno es habitación;
        - qué zona es cocina;
        - qué segmento corresponde a una cota;
        - dimensiones reales en metros.

    Nunca convierte píxeles directamente a metros.
    """

    NUMERIC_TOLERANCE = 1e-6

    def __init__(
        self,
        *,
        config: OpenCVGeometryConfig | None = None,
    ) -> None:
        self.config = config or OpenCVGeometryConfig()

    # ========================================================
    # API
    # ========================================================

    def analyze(
        self,
        *,
        raster: DocumentRasterPage,
    ) -> OpenCVPlanGeometryResult:
        image = self._decode_image(raster.image_bytes)

        original_height, original_width = image.shape[:2]

        if original_width != raster.width_px or original_height != raster.height_px:
            raise ValueError(
                "Las dimensiones reales de la imagen "
                "no coinciden con DocumentRasterPage."
            )

        # ----------------------------------------------------
        # ESCALA DE GRISES
        # ----------------------------------------------------

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        # ----------------------------------------------------
        # BINARIZACIÓN
        # ----------------------------------------------------
        #
        # Fondo blanco → 0
        # tinta/trazos → 255
        # ----------------------------------------------------

        otsu_threshold, binary = cv2.threshold(
            gray,
            0,
            255,
            (cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU),
        )

        # ----------------------------------------------------
        # DESKEW
        # ----------------------------------------------------

        deskew_angle = self._estimate_deskew_angle(binary)

        deskew_applied = False

        if (
            self.config.apply_deskew
            and abs(deskew_angle) > 0.1
            and abs(deskew_angle) <= 10.0
        ):
            image = self._rotate_image(
                image,
                deskew_angle,
            )

            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

            otsu_threshold, binary = cv2.threshold(
                gray,
                0,
                255,
                (cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU),
            )

            deskew_applied = True

        height, width = binary.shape[:2]

        minimum_dimension = min(
            width,
            height,
        )

        # ----------------------------------------------------
        # PARÁMETROS ESCALADOS
        # ----------------------------------------------------

        horizontal_kernel_length = max(
            3,
            int(round(width * self.config.directional_kernel_ratio)),
        )

        vertical_kernel_length = max(
            3,
            int(round(height * self.config.directional_kernel_ratio)),
        )

        min_line_length = max(
            8,
            int(round(minimum_dimension * self.config.min_line_length_ratio)),
        )

        max_line_gap = max(
            2,
            int(round(minimum_dimension * self.config.max_line_gap_ratio)),
        )

        hough_threshold = max(
            10,
            int(round(minimum_dimension * self.config.hough_threshold_ratio)),
        )

        axis_tolerance = max(
            1.0,
            minimum_dimension * self.config.axis_tolerance_ratio,
        )

        merge_gap = max(
            2.0,
            minimum_dimension * self.config.merge_gap_ratio,
        )

        # ----------------------------------------------------
        # MÁSCARAS DIRECCIONALES
        # ----------------------------------------------------

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                horizontal_kernel_length,
                1,
            ),
        )

        vertical_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                1,
                vertical_kernel_length,
            ),
        )

        horizontal_mask = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            horizontal_kernel,
        )

        vertical_mask = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            vertical_kernel,
        )

        # ----------------------------------------------------
        # LINE MASK
        # ----------------------------------------------------

        line_mask = cv2.bitwise_or(
            horizontal_mask,
            vertical_mask,
        )

        # Conservar un pequeño cierre topológico para unir
        # interrupciones raster menores.
        line_mask = cv2.morphologyEx(
            line_mask,
            cv2.MORPH_CLOSE,
            np.ones(
                (3, 3),
                dtype=np.uint8,
            ),
        )

        # ----------------------------------------------------
        # CANNY
        # ----------------------------------------------------

        canny_low, canny_high = self._automatic_canny_thresholds(gray)

        edges = cv2.Canny(
            line_mask,
            canny_low,
            canny_high,
            apertureSize=3,
            L2gradient=True,
        )

        # ----------------------------------------------------
        # HOUGH
        # ----------------------------------------------------

        hough = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=(np.pi / 180.0),
            threshold=hough_threshold,
            minLineLength=min_line_length,
            maxLineGap=max_line_gap,
        )

        raw_segments = self._build_hough_segments(hough)

        raw_horizontal = [
            segment for segment in raw_segments if segment.orientation == "horizontal"
        ]

        raw_vertical = [
            segment for segment in raw_segments if segment.orientation == "vertical"
        ]

        raw_other = [
            segment for segment in raw_segments if segment.orientation == "other"
        ]

        # ----------------------------------------------------
        # AGRUPACIÓN / CONTINUIDAD
        # ----------------------------------------------------

        merged_horizontal = self._merge_horizontal_segments(
            raw_horizontal,
            axis_tolerance=axis_tolerance,
            merge_gap=merge_gap,
        )

        merged_vertical = self._merge_vertical_segments(
            raw_vertical,
            axis_tolerance=axis_tolerance,
            merge_gap=merge_gap,
        )

        # ----------------------------------------------------
        # INTERSECCIONES
        # ----------------------------------------------------

        intersections = self._find_intersections(
            horizontal=merged_horizontal,
            vertical=merged_vertical,
            tolerance=axis_tolerance,
        )

        # ----------------------------------------------------
        # CONTORNOS
        # ----------------------------------------------------

        contours = self._extract_contour_candidates(
            line_mask,
            image_width=width,
            image_height=height,
        )

        dark_pixel_ratio = float(np.count_nonzero(binary)) / float(binary.size)

        diagnostics = OpenCVGeometryDiagnostics(
            dark_pixel_ratio=dark_pixel_ratio,
            raw_hough_segments=len(raw_segments),
            horizontal_raw_segments=len(raw_horizontal),
            vertical_raw_segments=len(raw_vertical),
            other_raw_segments=len(raw_other),
            merged_horizontal_segments=len(merged_horizontal),
            merged_vertical_segments=len(merged_vertical),
            intersections=len(intersections),
            contour_candidates=len(contours),
            parameters=OpenCVEffectiveParameters(
                image_width_px=width,
                image_height_px=height,
                otsu_threshold=float(otsu_threshold),
                canny_low=canny_low,
                canny_high=canny_high,
                directional_kernel_horizontal=horizontal_kernel_length,
                directional_kernel_vertical=vertical_kernel_length,
                hough_threshold=hough_threshold,
                min_line_length_px=min_line_length,
                max_line_gap_px=max_line_gap,
                axis_tolerance_px=axis_tolerance,
                merge_gap_px=merge_gap,
                deskew_angle_deg=deskew_angle,
                deskew_applied=deskew_applied,
            ),
        )

        return OpenCVPlanGeometryResult(
            page=raster.page,
            width_px=width,
            height_px=height,
            horizontal_segments=merged_horizontal,
            vertical_segments=merged_vertical,
            other_segments=raw_other,
            intersections=intersections,
            contours=contours,
            diagnostics=diagnostics,
            notes=[
                (
                    "OpenCV trabajó sobre el mismo "
                    "DocumentRasterPage utilizado por "
                    "la ruta visual."
                ),
                (
                    "Las líneas fueron detectadas, "
                    "clasificadas y agrupadas por "
                    "continuidad geométrica."
                ),
                (
                    "Las intersecciones son evidencia "
                    "geométrica y no nodos constructivos "
                    "confirmados."
                ),
                (
                    "Los contornos son candidatos raster; "
                    "no representan automáticamente espacios."
                ),
                ("No se realizó ninguna conversión " "de píxeles a metros."),
                ("Ninguna línea fue promovida " "automáticamente a muro."),
            ],
        )

    # ========================================================
    # DECODIFICACIÓN
    # ========================================================

    @staticmethod
    def _decode_image(
        image_bytes: bytes,
    ) -> np.ndarray:
        if not image_bytes:
            raise ValueError("El raster está vacío.")

        buffer = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            buffer,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError("OpenCV no pudo decodificar " "el raster.")

        return image

    # ========================================================
    # CANNY AUTOMÁTICO
    # ========================================================

    def _automatic_canny_thresholds(
        self,
        gray: np.ndarray,
    ) -> tuple[int, int]:
        """
        Canny adaptado al contraste real de la imagen.

        Evita fijar thresholds diseñados únicamente para
        Miguel H o una resolución concreta.
        """

        median = float(np.median(gray))

        sigma = float(self.config.canny_sigma)

        lower = int(
            max(
                0,
                (1.0 - sigma) * median,
            )
        )

        upper = int(
            min(
                255,
                (1.0 + sigma) * median,
            )
        )

        if upper <= lower:
            lower = 50
            upper = 150

        return (
            lower,
            upper,
        )

    # ========================================================
    # DESKEW
    # ========================================================

    @staticmethod
    def _estimate_deskew_angle(
        binary: np.ndarray,
    ) -> float:
        """
        Estima inclinación global únicamente cuando existen
        suficientes trazos largos.

        No intenta corregir perspectiva.
        """

        edges = cv2.Canny(
            binary,
            50,
            150,
            apertureSize=3,
        )

        minimum_dimension = min(binary.shape[:2])

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=(np.pi / 180.0),
            threshold=max(
                30,
                int(minimum_dimension * 0.03),
            ),
            minLineLength=max(
                20,
                int(minimum_dimension * 0.08),
            ),
            maxLineGap=max(
                3,
                int(minimum_dimension * 0.005),
            ),
        )

        if lines is None:
            return 0.0

        # OpenCV puede devolver HoughLinesP como:
        #
        #   (N, 1, 4)
        #
        # o:
        #
        #   (N, 4)
        #
        # dependiendo de la versión/build.
        #
        # Normalizamos siempre a:
        #
        #   (N, 4)
        #
        normalized_lines = np.asarray(lines).reshape(
            -1,
            4,
        )

        deviations: list[float] = []

        for (
            x1,
            y1,
            x2,
            y2,
        ) in normalized_lines:
            dx = float(x2 - x1)

            dy = float(y2 - y1)

            if abs(dx) <= 1e-9 and abs(dy) <= 1e-9:
                continue

            angle = math.degrees(
                math.atan2(
                    dy,
                    dx,
                )
            )

            # Llevar al eje horizontal/vertical
            # más cercano.
            normalized = ((angle + 45.0) % 90.0) - 45.0

            if abs(normalized) <= 10.0:
                deviations.append(normalized)

        if not deviations:
            return 0.0

        return float(
            np.median(
                np.asarray(
                    deviations,
                    dtype=np.float64,
                )
            )
        )

    # ========================================================
    # ROTACIÓN
    # ========================================================

    @staticmethod
    def _rotate_image(
        image: np.ndarray,
        angle_deg: float,
    ) -> np.ndarray:
        height, width = image.shape[:2]

        center = (
            width / 2.0,
            height / 2.0,
        )

        matrix = cv2.getRotationMatrix2D(
            center,
            angle_deg,
            1.0,
        )

        return cv2.warpAffine(
            image,
            matrix,
            (
                width,
                height,
            ),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(
                255,
                255,
                255,
            ),
        )

    # ========================================================
    # HOUGH → SEGMENTOS
    # ========================================================

    def _build_hough_segments(
        self,
        lines: Any,
    ) -> list[RasterLineSegment]:
        if lines is None:
            return []

        normalized_lines = np.asarray(lines).reshape(
            -1,
            4,
        )

        result: list[RasterLineSegment] = []

        for index, (
            raw_x1,
            raw_y1,
            raw_x2,
            raw_y2,
        ) in enumerate(
            normalized_lines,
            start=1,
        ):
            x1 = float(raw_x1)
            y1 = float(raw_y1)
            x2 = float(raw_x2)
            y2 = float(raw_y2)

            dx = x2 - x1
            dy = y2 - y1

            length = math.hypot(
                dx,
                dy,
            )

            if length <= self.NUMERIC_TOLERANCE:
                continue

            angle = math.degrees(
                math.atan2(
                    dy,
                    dx,
                )
            )

            orientation = self._orientation_from_angle(angle)

            # Normalizar dirección para facilitar merge.

            if orientation == "horizontal":
                if x2 < x1:
                    x1, x2 = (
                        x2,
                        x1,
                    )

                    y1, y2 = (
                        y2,
                        y1,
                    )

            elif orientation == "vertical":
                if y2 < y1:
                    x1, x2 = (
                        x2,
                        x1,
                    )

                    y1, y2 = (
                        y2,
                        y1,
                    )

            result.append(
                RasterLineSegment(
                    id=f"CV_RAW_{index}",
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    length_px=length,
                    orientation=orientation,
                    angle_deg=angle,
                    source="opencv_hough",
                    confidence=1.0,
                    merged_from=[],
                )
            )

        return result

    # ========================================================
    # ORIENTACIÓN
    # ========================================================

    @staticmethod
    def _orientation_from_angle(
        angle_deg: float,
    ) -> str:
        """
        Clasifica respecto al eje geométrico dominante.

        No significa que sea un muro.
        """

        normalized = angle_deg % 180.0

        horizontal_distance = min(
            abs(normalized),
            abs(normalized - 180.0),
        )

        vertical_distance = abs(normalized - 90.0)

        if horizontal_distance <= 5.0:
            return "horizontal"

        if vertical_distance <= 5.0:
            return "vertical"

        return "other"

    # ========================================================
    # MERGE HORIZONTAL
    # ========================================================

    def _merge_horizontal_segments(
        self,
        segments: list[RasterLineSegment],
        *,
        axis_tolerance: float,
        merge_gap: float,
    ) -> list[RasterLineSegment]:
        """
        Une segmentos horizontales colineales o casi colineales.

        Esto representa continuidad gráfica.

        NO rellena automáticamente puertas/ventanas con gaps
        grandes; esa continuidad virtual pertenece a la etapa
        de muros/openings.
        """

        if not segments:
            return []

        ordered = sorted(
            segments,
            key=lambda item: (
                item.midpoint_y,
                item.x1,
            ),
        )

        groups: list[list[RasterLineSegment]] = []

        for segment in ordered:
            assigned = False

            for group in groups:
                reference_y = float(np.mean([item.midpoint_y for item in group]))

                if abs(segment.midpoint_y - reference_y) > axis_tolerance:
                    continue

                group_min_x = min(
                    min(
                        item.x1,
                        item.x2,
                    )
                    for item in group
                )

                group_max_x = max(
                    max(
                        item.x1,
                        item.x2,
                    )
                    for item in group
                )

                segment_min_x = min(
                    segment.x1,
                    segment.x2,
                )

                segment_max_x = max(
                    segment.x1,
                    segment.x2,
                )

                gap = max(
                    0.0,
                    max(
                        segment_min_x - group_max_x,
                        group_min_x - segment_max_x,
                    ),
                )

                if gap <= merge_gap:
                    group.append(segment)

                    assigned = True
                    break

            if not assigned:
                groups.append([segment])

        result: list[RasterLineSegment] = []

        for index, group in enumerate(
            groups,
            start=1,
        ):
            x1 = min(
                min(
                    item.x1,
                    item.x2,
                )
                for item in group
            )

            x2 = max(
                max(
                    item.x1,
                    item.x2,
                )
                for item in group
            )

            y = float(np.mean([item.midpoint_y for item in group]))

            result.append(
                RasterLineSegment(
                    id=f"CV_H_{index}",
                    x1=x1,
                    y1=y,
                    x2=x2,
                    y2=y,
                    length_px=abs(x2 - x1),
                    orientation="horizontal",
                    angle_deg=0.0,
                    source="opencv_continuity",
                    confidence=1.0,
                    merged_from=[item.id for item in group],
                )
            )

        return result

    # ========================================================
    # MERGE VERTICAL
    # ========================================================

    def _merge_vertical_segments(
        self,
        segments: list[RasterLineSegment],
        *,
        axis_tolerance: float,
        merge_gap: float,
    ) -> list[RasterLineSegment]:
        if not segments:
            return []

        ordered = sorted(
            segments,
            key=lambda item: (
                item.midpoint_x,
                item.y1,
            ),
        )

        groups: list[list[RasterLineSegment]] = []

        for segment in ordered:
            assigned = False

            for group in groups:
                reference_x = float(np.mean([item.midpoint_x for item in group]))

                if abs(segment.midpoint_x - reference_x) > axis_tolerance:
                    continue

                group_min_y = min(
                    min(
                        item.y1,
                        item.y2,
                    )
                    for item in group
                )

                group_max_y = max(
                    max(
                        item.y1,
                        item.y2,
                    )
                    for item in group
                )

                segment_min_y = min(
                    segment.y1,
                    segment.y2,
                )

                segment_max_y = max(
                    segment.y1,
                    segment.y2,
                )

                gap = max(
                    0.0,
                    max(
                        segment_min_y - group_max_y,
                        group_min_y - segment_max_y,
                    ),
                )

                if gap <= merge_gap:
                    group.append(segment)

                    assigned = True
                    break

            if not assigned:
                groups.append([segment])

        result: list[RasterLineSegment] = []

        for index, group in enumerate(
            groups,
            start=1,
        ):
            y1 = min(
                min(
                    item.y1,
                    item.y2,
                )
                for item in group
            )

            y2 = max(
                max(
                    item.y1,
                    item.y2,
                )
                for item in group
            )

            x = float(np.mean([item.midpoint_x for item in group]))

            result.append(
                RasterLineSegment(
                    id=f"CV_V_{index}",
                    x1=x,
                    y1=y1,
                    x2=x,
                    y2=y2,
                    length_px=abs(y2 - y1),
                    orientation="vertical",
                    angle_deg=90.0,
                    source="opencv_continuity",
                    confidence=1.0,
                    merged_from=[item.id for item in group],
                )
            )

        return result

    # ========================================================
    # INTERSECCIONES
    # ========================================================

    @staticmethod
    def _find_intersections(
        *,
        horizontal: list[RasterLineSegment],
        vertical: list[RasterLineSegment],
        tolerance: float,
    ) -> list[RasterIntersection]:
        result: list[RasterIntersection] = []

        seen: set[tuple[int, int]] = set()

        counter = 0

        for h_segment in horizontal:
            hx_min = min(
                h_segment.x1,
                h_segment.x2,
            )

            hx_max = max(
                h_segment.x1,
                h_segment.x2,
            )

            hy = (h_segment.y1 + h_segment.y2) / 2.0

            for v_segment in vertical:
                vx = (v_segment.x1 + v_segment.x2) / 2.0

                vy_min = min(
                    v_segment.y1,
                    v_segment.y2,
                )

                vy_max = max(
                    v_segment.y1,
                    v_segment.y2,
                )

                if not (hx_min - tolerance <= vx <= hx_max + tolerance):
                    continue

                if not (vy_min - tolerance <= hy <= vy_max + tolerance):
                    continue

                rounded_key = (
                    int(round(vx)),
                    int(round(hy)),
                )

                if rounded_key in seen:
                    continue

                seen.add(rounded_key)

                counter += 1

                result.append(
                    RasterIntersection(
                        id=f"CV_I_{counter}",
                        x=vx,
                        y=hy,
                        horizontal_segment_id=h_segment.id,
                        vertical_segment_id=v_segment.id,
                        source="opencv",
                    )
                )

        return result

    # ========================================================
    # CONTORNOS
    # ========================================================

    def _extract_contour_candidates(
        self,
        line_mask: np.ndarray,
        *,
        image_width: int,
        image_height: int,
    ) -> list[RasterContourCandidate]:
        contours, _ = cv2.findContours(
            line_mask,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        image_area = float(image_width * image_height)

        minimum_area = image_area * self.config.minimum_contour_area_ratio

        result: list[RasterContourCandidate] = []

        counter = 0

        for contour in contours:
            area = float(cv2.contourArea(contour))

            if area < minimum_area:
                continue

            perimeter = float(
                cv2.arcLength(
                    contour,
                    True,
                )
            )

            x, y, width, height = cv2.boundingRect(contour)

            if width <= 1 or height <= 1:
                continue

            counter += 1

            result.append(
                RasterContourCandidate(
                    id=f"CV_C_{counter}",
                    area_px2=area,
                    perimeter_px=perimeter,
                    x=int(x),
                    y=int(y),
                    width=int(width),
                    height=int(height),
                    closed=True,
                    source="opencv",
                )
            )

        result.sort(key=lambda item: (-item.area_px2))

        return result


# ============================================================
# FACTORY
# ============================================================


def get_opencv_plan_geometry_service() -> OpenCVPlanGeometryService:
    return OpenCVPlanGeometryService()
