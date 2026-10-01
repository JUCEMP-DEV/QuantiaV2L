from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.plan_document_analyzer import (
    DocumentTextSpan,
    PlanDocumentAnalysis,
)


# ============================================================
# MODELOS
# ============================================================


@dataclass(slots=True)
class PDFEvidenceItem:
    """
    Evidencia textual extraída directamente del PDF.

    IMPORTANTE:

    Este objeto representa evidencia documental, no una
    interpretación arquitectónica.

    Dos elementos con el mismo texto pueden ser completamente
    distintos si aparecen en coordenadas diferentes.

    Ejemplo:

        2.60  → cota entre ejes C-D
        2.60  → otra cota en otra región

    Por ello la identidad espacial siempre incluye:

        página + bbox
    """

    kind: str

    text: str
    normalized_text: str

    page: int

    x0: float
    y0: float
    x1: float
    y1: float

    center_x: float
    center_y: float

    font: str | None = None
    font_size: float | None = None

    numeric_value: float | None = None
    numeric_unit: str | None = None

    source: str = "pymupdf_vector_text"

    confidence: float = 1.0


@dataclass(slots=True)
class PDFPlanEvidence:
    """
    Evidencias determinísticas obtenidas de un PDF.

    Las listas contienen CANDIDATOS.

    Este servicio no decide todavía:

    - qué número es definitivamente una cota;
    - qué letra es definitivamente un eje;
    - qué texto pertenece a qué espacio;
    - qué geometría corresponde a un muro;
    - qué escala debe gobernar la reconstrucción.

    Esa resolución ocurre posteriormente en el grounding y
    reconciliador de Quantia.
    """

    page_count: int

    all_texts: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    dimension_candidates: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    level_markers: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    stair_markers: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    structural_markers: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    title_candidates: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    scale_candidates: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    drawing_type_candidates: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    north_markers: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    axis_candidates: list[
        PDFEvidenceItem
    ] = field(
        default_factory=list
    )

    miscellaneous_keywords: list[
        PDFEvidenceItem
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
# EXTRACTOR
# ============================================================


class PDFPlanEvidenceExtractor:
    """
    Extrae evidencia determinística desde texto vectorial PDF.

    Este servicio forma parte de:

        PDF
        ↓
        PyMuPDF
        ↓
        texto + coordenadas
        ↓
        PDFPlanEvidenceExtractor
        ↓
        grounding / reconciliador

    NO interpreta arquitectura completa.

    Su trabajo consiste únicamente en identificar candidatos
    documentales útiles conservando:

    - texto original;
    - página;
    - coordenadas;
    - tamaño de fuente;
    - valor numérico cuando sea inequívocamente parseable;
    - clasificación preliminar.

    REGLA FUNDAMENTAL:

        candidato ≠ verdad final

    Por ejemplo:

        "2.60"

    puede ser candidato a cota, pero todavía debe relacionarse
    espacialmente con líneas de dimensión, ejes y geometría.
    """

    # ========================================================
    # EXPRESIONES
    # ========================================================

    # Acepta:
    #
    # 2
    # 2.60
    # 2,60
    # 2.600
    # 2.60 m
    # 260 cm
    #
    # No asigna unidad si el documento no la presenta.

    DIMENSION_RE = re.compile(
        r"^\s*"
        r"(?P<value>\d+(?:[.,]\d{1,3})?)"
        r"\s*"
        r"(?P<unit>mm|cm|m)?"
        r"\s*$",
        re.IGNORECASE,
    )

    # Acepta principalmente:
    #
    # 1:25
    # 1 / 25
    # escala 1:25
    # esc 1:25
    # esc. 1/25

    SCALE_RE = re.compile(
        r"^\s*"
        r"(?:(?:escala|esc)\.?\s*:?\s*)?"
        r"\d+\s*[:/]\s*\d+"
        r"\s*$",
        re.IGNORECASE,
    )

    AXIS_NUMERIC_RE = re.compile(
        r"^\d{1,3}$"
    )

    AXIS_ALPHA_RE = re.compile(
        r"^[A-Z]$"
    )

    # ========================================================
    # VOCABULARIO
    # ========================================================

    # Los textos se normalizan sin acentos para comparar.

    LEVEL_MARKERS = {
        "planta baja",
        "planta alta",
        "azotea",
        "nivel 1",
        "nivel 2",
        "nivel 3",
        "nivel 4",
        "pb",
        "pa",
    }

    STAIR_MARKERS = {
        "arriba",
        "abajo",
        "sube",
        "baja",
    }

    STRUCTURAL_KEYWORDS = {
        "castillo",
        "armex",
        "cadena",
        "dala",
        "trabe",
        "columna",
        "losa",
        "cimentacion",
        "zapata",
        "contratrabe",
    }

    DRAWING_TYPE_KEYWORDS = {
        "arquitectonico",
        "planta arquitectonica",
        "corte",
        "fachada",
        "detalle",
    }

    NORTH_MARKERS = {
        "norte",
        "n",
    }

    MISCELLANEOUS_KEYWORDS = {
        "wc",
        "bano",
        "medio bano",
        "recamara",
        "recamaras",
        "cocina",
        "sala",
        "estancia",
        "comedor",
        "patio",
        "cochera",
        "garage",
        "escalera",
        "escaleras",
        "vestibulo",
        "pasillo",
        "circulacion",
        "terraza",
        "lavado",
        "lavanderia",
        "servicio",
    }

    TITLE_KEYWORDS = {
        "casa habitacion",
        "proyecto",
        "plano",
    }

    # ========================================================
    # API PÚBLICA
    # ========================================================

    def extract(
        self,
        analysis: PlanDocumentAnalysis,
    ) -> PDFPlanEvidence:
        """
        Extrae evidencia textual del análisis PyMuPDF.

        Puede ejecutarse sobre:

        - PDF vectorial;
        - PDF híbrido;
        - PDF clasificado como escaneado.

        En un PDF completamente raster probablemente no existirán
        text_spans y la salida textual será vacía.

        Eso no es un error: la evidencia deberá venir de OCR.
        """

        if analysis.document_type not in {
            "pdf_vector_or_hybrid",
            "pdf_raster_or_scanned",
        }:
            raise ValueError(
                "La evidencia PDF solo puede "
                "extraerse desde un documento PDF."
            )

        evidence = PDFPlanEvidence(
            page_count=
                analysis.page_count
        )

        if not analysis.pages:
            evidence.notes.append(
                "El análisis PDF no contiene páginas "
                "con evidencia vectorial."
            )

            return evidence

        for page in analysis.pages:
            for span in page.text_spans:
                item = self._to_item(
                    span
                )

                # --------------------------------------------
                # TODOS LOS TEXTOS
                # --------------------------------------------
                #
                # Nunca deduplicamos semánticamente esta lista.
                #
                # La posición es evidencia.
                # --------------------------------------------

                evidence.all_texts.append(
                    item
                )

                self._classify_item(
                    item,
                    evidence,
                )

        if evidence.all_texts:
            evidence.notes.append(
                "Se extrajo evidencia textual vectorial "
                "con coordenadas visuales."
            )
        else:
            evidence.notes.append(
                "No se encontró texto vectorial utilizable. "
                "La lectura textual deberá depender de OCR."
            )

        evidence.notes.append(
            "Las clasificaciones son candidatos documentales; "
            "no constituyen asociaciones geométricas definitivas."
        )

        return evidence

    # ========================================================
    # NORMALIZACIÓN
    # ========================================================

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        """
        Normalización utilizada exclusivamente para clasificación.

        Conservamos item.text con el contenido original.

        normalized_text:

        - minúsculas;
        - sin acentos;
        - espacios normalizados.

        Ejemplo:

            "  RECÁMARA  "
                ↓
            "recamara"
        """

        raw = str(
            text or ""
        ).strip().lower()

        decomposed = unicodedata.normalize(
            "NFD",
            raw,
        )

        without_accents = "".join(
            character
            for character in decomposed
            if unicodedata.category(
                character
            ) != "Mn"
        )

        return " ".join(
            without_accents.split()
        )

    # ========================================================
    # CREACIÓN DE EVIDENCIA
    # ========================================================

    def _to_item(
        self,
        span: DocumentTextSpan,
    ) -> PDFEvidenceItem:
        normalized = (
            self._normalize_text(
                span.text
            )
        )

        numeric_value, numeric_unit = (
            self._parse_numeric_candidate(
                normalized
            )
        )

        x0 = float(
            span.x0
        )

        y0 = float(
            span.y0
        )

        x1 = float(
            span.x1
        )

        y1 = float(
            span.y1
        )

        return PDFEvidenceItem(
            kind=
                "text",

            text=
                span.text,

            normalized_text=
                normalized,

            page=
                span.page,

            x0=
                x0,

            y0=
                y0,

            x1=
                x1,

            y1=
                y1,

            center_x=
                (x0 + x1) / 2.0,

            center_y=
                (y0 + y1) / 2.0,

            font=
                span.font,

            font_size=
                span.size,

            numeric_value=
                numeric_value,

            numeric_unit=
                numeric_unit,

            source=
                "pymupdf_vector_text",

            confidence=
                1.0,
        )

    # ========================================================
    # NÚMEROS
    # ========================================================

    def _parse_numeric_candidate(
        self,
        normalized_text: str,
    ) -> tuple[
        float | None,
        str | None,
    ]:
        """
        Parsea un candidato numérico sin interpretar su función.

        IMPORTANTE:

        Obtener:

            numeric_value = 2.60

        NO significa:

            dimensión confirmada = 2.60 m

        La unidad solo se conserva cuando aparece explícitamente.

        Si no existe unidad:

            numeric_unit = None

        El grounding posterior deberá resolver el significado.
        """

        match = self.DIMENSION_RE.fullmatch(
            normalized_text
        )

        if match is None:
            return None, None

        raw_value = (
            match.group(
                "value"
            )
        )

        raw_unit = (
            match.group(
                "unit"
            )
        )

        if not raw_value:
            return None, None

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
            raw_unit.lower()
            if raw_unit
            else None
        )

        return value, unit

    # ========================================================
    # CLASIFICACIÓN
    # ========================================================

    def _classify_item(
        self,
        item: PDFEvidenceItem,
        evidence: PDFPlanEvidence,
    ) -> None:
        raw = str(
            item.text or ""
        ).strip()

        normalized = (
            item.normalized_text
        )

        if not raw:
            return

        # ----------------------------------------------------
        # COTAS NUMÉRICAS CANDIDATAS
        # ----------------------------------------------------
        #
        # Un número puede ser simultáneamente:
        #
        # - cota;
        # - eje numérico;
        # - número de detalle;
        # - número de página;
        #
        # No resolvemos aquí la ambigüedad.
        # ----------------------------------------------------

        if (
            item.numeric_value
            is not None
        ):
            self._append_spatial_candidate(
                evidence.dimension_candidates,
                self._clone_with_kind(
                    item,
                    "dimension_candidate",
                ),
            )

        # ----------------------------------------------------
        # ESCALA
        # ----------------------------------------------------

        if self.SCALE_RE.fullmatch(
            normalized
        ):
            self._append_spatial_candidate(
                evidence.scale_candidates,
                self._clone_with_kind(
                    item,
                    "scale_candidate",
                ),
            )

        elif (
            (
                "escala" in normalized
                or re.search(
                    r"(?<!\w)esc\.?(?!\w)",
                    normalized,
                )
            )
            and any(
                character.isdigit()
                for character in normalized
            )
        ):
            self._append_spatial_candidate(
                evidence.scale_candidates,
                self._clone_with_kind(
                    item,
                    "scale_candidate",
                ),
            )

        # ----------------------------------------------------
        # TÍTULO
        # ----------------------------------------------------

        if self._contains_any_phrase(
            normalized,
            self.TITLE_KEYWORDS,
        ):
            self._append_spatial_candidate(
                evidence.title_candidates,
                self._clone_with_kind(
                    item,
                    "title_candidate",
                ),
            )

        # ----------------------------------------------------
        # NIVELES
        # ----------------------------------------------------
        #
        # Coincidencia exacta deliberada.
        #
        # "Planta Baja" es nivel.
        #
        # No debe generar automáticamente un marcador
        # de escalera por contener la palabra "baja".
        # ----------------------------------------------------

        if normalized in self.LEVEL_MARKERS:
            self._append_spatial_candidate(
                evidence.level_markers,
                self._clone_with_kind(
                    item,
                    "level_marker",
                ),
            )

        # ----------------------------------------------------
        # ESCALERAS
        # ----------------------------------------------------

        if normalized in self.STAIR_MARKERS:
            self._append_spatial_candidate(
                evidence.stair_markers,
                self._clone_with_kind(
                    item,
                    "stair_marker",
                ),
            )

        # ----------------------------------------------------
        # REFERENCIAS CONSTRUCTIVAS
        # ----------------------------------------------------

        if self._contains_any_phrase(
            normalized,
            self.STRUCTURAL_KEYWORDS,
        ):
            self._append_spatial_candidate(
                evidence.structural_markers,
                self._clone_with_kind(
                    item,
                    "structural_marker",
                ),
            )

        # ----------------------------------------------------
        # TIPO DE PLANO
        # ----------------------------------------------------

        if self._contains_any_phrase(
            normalized,
            self.DRAWING_TYPE_KEYWORDS,
        ):
            self._append_spatial_candidate(
                evidence.drawing_type_candidates,
                self._clone_with_kind(
                    item,
                    "drawing_type_candidate",
                ),
            )

        # ----------------------------------------------------
        # NORTE
        # ----------------------------------------------------
        #
        # "N" puede ser:
        #
        # - norte;
        # - eje N.
        #
        # Conservamos ambas posibilidades.
        # El reconciliador resolverá con posición y simbología.
        # ----------------------------------------------------

        if normalized in self.NORTH_MARKERS:
            self._append_spatial_candidate(
                evidence.north_markers,
                self._clone_with_kind(
                    item,
                    "north_marker",
                ),
            )

        # ----------------------------------------------------
        # VOCABULARIO ARQUITECTÓNICO
        # ----------------------------------------------------
        #
        # Estos textos son útiles para localizar espacios,
        # pero NO se convierten aquí en espacios geométricos.
        # ----------------------------------------------------

        if self._contains_any_phrase(
            normalized,
            self.MISCELLANEOUS_KEYWORDS,
        ):
            self._append_spatial_candidate(
                evidence.miscellaneous_keywords,
                self._clone_with_kind(
                    item,
                    "miscellaneous_keyword",
                ),
            )

        # ----------------------------------------------------
        # EJES NUMÉRICOS
        # ----------------------------------------------------
        #
        # Un entero pequeño puede ser eje o cota.
        #
        # Conservamos la ambigüedad.
        # ----------------------------------------------------

        if self.AXIS_NUMERIC_RE.fullmatch(
            raw
        ):
            self._append_spatial_candidate(
                evidence.axis_candidates,
                self._clone_with_kind(
                    item,
                    "axis_candidate",
                ),
            )

        # ----------------------------------------------------
        # EJES ALFABÉTICOS
        # ----------------------------------------------------

        if self.AXIS_ALPHA_RE.fullmatch(
            raw.upper()
        ):
            self._append_spatial_candidate(
                evidence.axis_candidates,
                self._clone_with_kind(
                    item,
                    "axis_candidate",
                ),
            )

    # ========================================================
    # COINCIDENCIA DE PALABRAS / FRASES
    # ========================================================

    @staticmethod
    def _contains_any_phrase(
        normalized_text: str,
        keywords: set[str],
    ) -> bool:
        """
        Busca palabras o frases completas.

        Evita coincidencias accidentales por subcadena.

        Ejemplos:

            "sala" sí coincide con "SALA"

            "pa" no coincide dentro de:
                "patio"

            "bano" sí coincide con:
                "medio bano"

        Los textos y keywords ya están normalizados sin acentos.
        """

        for keyword in keywords:
            pattern = (
                r"(?<!\w)"
                + re.escape(
                    keyword
                )
                + r"(?!\w)"
            )

            if re.search(
                pattern,
                normalized_text,
                flags=re.IGNORECASE,
            ):
                return True

        return False

    # ========================================================
    # DEDUPLICACIÓN ESPACIAL
    # ========================================================

    @classmethod
    def _append_spatial_candidate(
        cls,
        target: list[PDFEvidenceItem],
        item: PDFEvidenceItem,
    ) -> None:
        """
        Elimina únicamente duplicados prácticamente idénticos.

        NO deduplica por texto.

        Esto es crítico.

        Incorrecto:

            "2.60" en cualquier parte del plano
            =
            el mismo elemento

        Correcto:

            texto
            + página
            + coordenadas
            =
            evidencia individual

        Algunos PDF pueden contener el mismo texto duplicado
        exactamente en la misma posición debido a capas o
        entidades superpuestas.

        Solo ese caso se elimina.
        """

        for existing in target:
            if not cls._same_spatial_item(
                existing,
                item,
            ):
                continue

            return

        target.append(
            item
        )

    @staticmethod
    def _same_spatial_item(
        first: PDFEvidenceItem,
        second: PDFEvidenceItem,
        tolerance: float = 0.01,
    ) -> bool:
        if (
            first.page
            != second.page
        ):
            return False

        if (
            first.normalized_text
            != second.normalized_text
        ):
            return False

        return (
            abs(
                first.x0
                - second.x0
            )
            <= tolerance
            and abs(
                first.y0
                - second.y0
            )
            <= tolerance
            and abs(
                first.x1
                - second.x1
            )
            <= tolerance
            and abs(
                first.y1
                - second.y1
            )
            <= tolerance
        )

    # ========================================================
    # CLONADO
    # ========================================================

    @staticmethod
    def _clone_with_kind(
        item: PDFEvidenceItem,
        kind: str,
    ) -> PDFEvidenceItem:
        """
        Conserva exactamente la evidencia espacial del span y
        únicamente cambia su clasificación.
        """

        return PDFEvidenceItem(
            kind=
                kind,

            text=
                item.text,

            normalized_text=
                item.normalized_text,

            page=
                item.page,

            x0=
                item.x0,

            y0=
                item.y0,

            x1=
                item.x1,

            y1=
                item.y1,

            center_x=
                item.center_x,

            center_y=
                item.center_y,

            font=
                item.font,

            font_size=
                item.font_size,

            numeric_value=
                item.numeric_value,

            numeric_unit=
                item.numeric_unit,

            source=
                item.source,

            confidence=
                item.confidence,
        )


# ============================================================
# DEPENDENCY FACTORY
# ============================================================


def get_pdf_plan_evidence_extractor(
) -> PDFPlanEvidenceExtractor:
    return PDFPlanEvidenceExtractor()