from __future__ import annotations

import math
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from app.schemas.quantia_extraction import (
    BoundingBox,
    EvidenceItem,
    QuantiaExtractionSchema,
)
from app.legacy.quantia_spatial.pdf_plan_evidence_extractor import (
    PDFEvidenceItem,
    PDFPlanEvidence,
)
from app.legacy.quantia_spatial.quantia_extraction_reconciler import (
    MetricCandidate,
    QuantiaReconciliationResult,
)


# ============================================================
# RESULTADOS DE GROUNDING
# ============================================================


@dataclass(slots=True)
class GroundedTextField:
    """
    Campo semántico Gemini contrastado contra texto vectorial.

    matched=True significa únicamente que existe evidencia
    textual compatible en el PDF.
    """

    field: str

    value: str | None

    matched: bool

    matches: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )


@dataclass(slots=True)
class GroundedMetricCandidate:
    """
    Métrica propuesta por Gemini contrastada contra la
    evidencia numérica del PDF.

    REGLA FUNDAMENTAL:

        value_present_in_pdf=True
        !=
        association_validated=True

    Ejemplo:

        Gemini:
            recámara.largo_m = 2.60

        PDF:
            aparecen tres valores 2.60

    Resultado:

        value_present_in_pdf = True
        ambiguous_numeric_match = True
        association_validated = False

    La asociación correcta deberá resolverse después con:

        posición
        + ejes
        + líneas
        + espacios
        + geometría.
    """

    element_type: str
    element_id: str

    level: str | None

    field: str

    metric_kind: str

    value: float

    model_state: str

    model_confidence: float

    model_source: str

    value_present_in_pdf: bool

    match_count: int

    ambiguous_numeric_match: bool

    pdf_matches: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    candidate_evidence: list[
        str
    ] = field(
        default_factory=list
    )

    association_validated: bool = False

    association_reason: str | None = None


@dataclass(slots=True)
class StairGrounding:
    """
    Grounding textual preliminar de una escalera.

    La presencia de SUBE / BAJA / ARRIBA / ABAJO ayuda como
    evidencia, pero todavía no define su geometría.
    """

    id_propuesto: str | None

    nivel: str | None

    sentido: str | None

    vector_text_match: bool

    matches: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    source: str = "vision"


@dataclass(slots=True)
class QuantiaGroundingResult:
    """
    Resultado de grounding documental PDF.

    Fusiona:

        Gemini
        + reconciliador
        + evidencia vectorial PyMuPDF

    y prepara la siguiente etapa:

        grounding espacial / geométrico.

    Este servicio todavía NO:

    - crea muros;
    - genera polígonos;
    - asigna una cota a un tramo;
    - asigna un eje a un muro;
    - promociona medidas Gemini.
    """

    extraction: QuantiaExtractionSchema

    document_fields: list[
        GroundedTextField
    ] = field(
        default_factory=list
    )

    levels: list[
        GroundedTextField
    ] = field(
        default_factory=list
    )

    metric_candidates: list[
        GroundedMetricCandidate
    ] = field(
        default_factory=list
    )

    stairs: list[
        StairGrounding
    ] = field(
        default_factory=list
    )

    axis_evidence: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    dimension_evidence: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    structural_evidence: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    unmatched_pdf_dimensions: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    notes: list[str] = field(
        default_factory=list
    )

    def audit_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "document_fields": [
                asdict(
                    item
                )
                for item
                in self.document_fields
            ],

            "levels": [
                asdict(
                    item
                )
                for item
                in self.levels
            ],

            "metric_candidates": [
                asdict(
                    item
                )
                for item
                in self.metric_candidates
            ],

            "stairs": [
                asdict(
                    item
                )
                for item
                in self.stairs
            ],

            "axis_evidence":
                self.axis_evidence,

            "dimension_evidence":
                self.dimension_evidence,

            "structural_evidence":
                self.structural_evidence,

            "unmatched_pdf_dimensions":
                self.unmatched_pdf_dimensions,

            "notes":
                self.notes,
        }


# ============================================================
# SERVICIO
# ============================================================


class PDFQuantiaGroundingService:
    """
    Grounding documental determinístico para PDF.

    ==========================================================
    RESPONSABILIDADES
    ==========================================================

    PyMuPDF aporta:

        texto
        coordenadas
        números
        ejes candidatos
        cotas candidatas
        marcadores
        evidencia constructiva

    Gemini aporta:

        interpretación semántica
        espacios
        función
        relaciones
        medidas propuestas

    Este servicio compara ambas fuentes sin promover
    asociaciones que todavía no puedan demostrarse.


    ==========================================================
    REGLAS
    ==========================================================

    1. Encontrar un número en PDF confirma únicamente
       existencia documental.

    2. Dos números iguales en posiciones distintas son
       evidencias distintas.

    3. Un valor 2.60 no se asigna a un espacio únicamente
       porque Gemini también haya dicho 2.60.

    4. area_m2 NO se compara contra cotas lineales.

    5. Los ejes se conservan con coordenadas porque serán
       fundamentales en el grounding espacial.

    6. Las cotas Gemini permanecen sin valor_m confirmado.

    7. Ninguna medida Gemini se promociona aquí.

    8. La siguiente etapa deberá relacionar:

           semántica Gemini
           + coordenadas
           + ejes
           + cotas
           + líneas
           + geometría.
    """

    LINEAR_FIELDS = {
        "ancho_m",
        "alto_m",
        "largo_m",
        "fondo_m",
        "valor_m",
        "elevacion_m",
        "espesor_m",
    }

    AREA_FIELDS = {
        "area_m2",
        "superficie_m2",
    }

    # ========================================================
    # API PÚBLICA
    # ========================================================

    def ground(
        self,
        *,
        reconciliation: QuantiaReconciliationResult,
        pdf_evidence: PDFPlanEvidence,
    ) -> QuantiaGroundingResult:
        """
        Ejecuta grounding documental.

        La extracción original se copia para no modificar
        accidentalmente el resultado del reconciliador.
        """

        extraction = (
            reconciliation
            .extraction
            .model_copy(
                deep=True
            )
        )

        # ----------------------------------------------------
        # DOCUMENTO
        # ----------------------------------------------------

        document_fields = (
            self._ground_document_fields(
                extraction,
                pdf_evidence,
            )
        )

        # ----------------------------------------------------
        # NIVELES
        # ----------------------------------------------------

        levels = (
            self._ground_levels(
                extraction,
                pdf_evidence,
            )
        )

        # ----------------------------------------------------
        # MÉTRICAS GEMINI
        # ----------------------------------------------------

        grounded_metrics = (
            self._ground_metric_candidates(
                reconciliation.metric_candidates,
                pdf_evidence,
            )
        )

        # ----------------------------------------------------
        # COTAS GEMINI
        # ----------------------------------------------------
        #
        # Solo agregamos evidencia documental.
        #
        # valor_m sigue sin promoverse.
        # ----------------------------------------------------

        self._ground_canonical_dimensions(
            extraction,
            pdf_evidence,
        )

        # ----------------------------------------------------
        # ESCALERAS
        # ----------------------------------------------------

        stairs = (
            self._ground_stairs(
                extraction,
                pdf_evidence,
            )
        )

        # ----------------------------------------------------
        # EJES
        # ----------------------------------------------------

        axis_evidence = [
            self._evidence_item_to_dict(
                item
            )
            for item
            in pdf_evidence.axis_candidates
        ]

        # ----------------------------------------------------
        # TODAS LAS COTAS VECTORIALES
        # ----------------------------------------------------

        dimension_evidence = [
            self._evidence_item_to_dict(
                item
            )
            for item
            in pdf_evidence.dimension_candidates
        ]

        # ----------------------------------------------------
        # CONSTRUCTIVOS
        # ----------------------------------------------------

        structural_evidence = [
            self._evidence_item_to_dict(
                item
            )
            for item
            in pdf_evidence.structural_markers
        ]

        # ----------------------------------------------------
        # COTAS SIN CORRESPONDENCIA NUMÉRICA
        # ----------------------------------------------------

        unmatched_dimensions = (
            self._find_unmatched_pdf_dimensions(
                grounded_metrics,
                pdf_evidence,
            )
        )

        # ----------------------------------------------------
        # NOTAS
        # ----------------------------------------------------

        notes: list[str] = []

        if pdf_evidence.dimension_candidates:
            notes.append(
                "Las cotas vectoriales conservaron sus "
                "coordenadas. Una coincidencia numérica no "
                "valida todavía su asociación espacial."
            )

        if pdf_evidence.axis_candidates:
            notes.append(
                "Los candidatos de eje fueron preservados "
                "con página y coordenadas para el grounding "
                "espacial posterior."
            )

        if (
            extraction
            .elementos_especiales
            .escaleras
            and not pdf_evidence.stair_markers
        ):
            notes.append(
                "Las escaleras fueron detectadas por visión, "
                "pero PyMuPDF no encontró marcadores vectoriales "
                "SUBE/BAJA/ARRIBA/ABAJO utilizables."
            )

        notes.append(
            "Ninguna métrica propuesta por Gemini fue "
            "promovida a dimensión constructiva."
        )

        notes.append(
            "Las áreas no se compararon contra cotas lineales; "
            "deberán derivarse de geometría validada o de una "
            "evidencia explícita de superficie."
        )

        return QuantiaGroundingResult(
            extraction=
                extraction,

            document_fields=
                document_fields,

            levels=
                levels,

            metric_candidates=
                grounded_metrics,

            stairs=
                stairs,

            axis_evidence=
                axis_evidence,

            dimension_evidence=
                dimension_evidence,

            structural_evidence=
                structural_evidence,

            unmatched_pdf_dimensions=
                unmatched_dimensions,

            notes=
                notes,
        )

    # ========================================================
    # DOCUMENTO
    # ========================================================

    def _ground_document_fields(
        self,
        extraction: QuantiaExtractionSchema,
        evidence: PDFPlanEvidence,
    ) -> list[GroundedTextField]:
        results: list[
            GroundedTextField
        ] = []

        results.append(
            self._text_field_match(
                field_name=
                    "documento.titulo",

                value=
                    extraction.documento.titulo,

                candidates=
                    evidence.title_candidates,
            )
        )

        results.append(
            self._text_field_match(
                field_name=
                    "documento.escala",

                value=
                    extraction.documento.escala,

                candidates=
                    evidence.scale_candidates,
            )
        )

        results.append(
            self._text_field_match(
                field_name=
                    "documento.tipo_plano",

                value=
                    extraction.documento.tipo_plano,

                candidates=
                    evidence.drawing_type_candidates,
            )
        )

        return results

    # ========================================================
    # NIVELES
    # ========================================================

    def _ground_levels(
        self,
        extraction: QuantiaExtractionSchema,
        evidence: PDFPlanEvidence,
    ) -> list[GroundedTextField]:
        results: list[
            GroundedTextField
        ] = []

        for level in extraction.niveles:
            results.append(
                self._text_field_match(
                    field_name=
                        "nivel",

                    value=
                        level.nombre,

                    candidates=
                        evidence.level_markers,
                )
            )

        return results

    # ========================================================
    # MÉTRICAS GEMINI
    # ========================================================

    def _ground_metric_candidates(
        self,
        candidates: list[
            MetricCandidate
        ],
        evidence: PDFPlanEvidence,
    ) -> list[
        GroundedMetricCandidate
    ]:
        """
        Compara métricas Gemini con evidencia PDF.

        IMPORTANTE:

        Solo métricas LINEALES se comparan contra
        dimension_candidates.

        Ejemplo incorrecto anterior:

            area_m2 = 10.66

            PDF contiene una cota "10.66"

            => falso grounding de área.

        Eso queda eliminado.
        """

        result: list[
            GroundedMetricCandidate
        ] = []

        for candidate in candidates:
            metric_kind = (
                self._metric_kind(
                    candidate.field
                )
            )

            model_source = getattr(
                candidate,
                "source",
                "gemini_vision",
            )

            candidate_evidence = list(
                getattr(
                    candidate,
                    "evidence",
                    [],
                )
                or []
            )

            # ------------------------------------------------
            # ÁREAS
            # ------------------------------------------------

            if metric_kind == "area":
                result.append(
                    GroundedMetricCandidate(
                        element_type=
                            candidate.element_type,

                        element_id=
                            candidate.element_id,

                        level=
                            candidate.level,

                        field=
                            candidate.field,

                        metric_kind=
                            metric_kind,

                        value=
                            candidate.value,

                        model_state=
                            candidate.state,

                        model_confidence=
                            candidate.confidence,

                        model_source=
                            model_source,

                        value_present_in_pdf=
                            False,

                        match_count=
                            0,

                        ambiguous_numeric_match=
                            False,

                        pdf_matches=
                            [],

                        candidate_evidence=
                            candidate_evidence,

                        association_validated=
                            False,

                        association_reason=(
                            "Las áreas no se validan contra "
                            "cotas lineales. Deben derivarse "
                            "de geometría validada o de una "
                            "evidencia explícita de superficie."
                        ),
                    )
                )

                continue

            # ------------------------------------------------
            # OTROS TIPOS NO LINEALES
            # ------------------------------------------------

            if metric_kind != "linear":
                result.append(
                    GroundedMetricCandidate(
                        element_type=
                            candidate.element_type,

                        element_id=
                            candidate.element_id,

                        level=
                            candidate.level,

                        field=
                            candidate.field,

                        metric_kind=
                            metric_kind,

                        value=
                            candidate.value,

                        model_state=
                            candidate.state,

                        model_confidence=
                            candidate.confidence,

                        model_source=
                            model_source,

                        value_present_in_pdf=
                            False,

                        match_count=
                            0,

                        ambiguous_numeric_match=
                            False,

                        pdf_matches=
                            [],

                        candidate_evidence=
                            candidate_evidence,

                        association_validated=
                            False,

                        association_reason=(
                            "La métrica no pertenece a una "
                            "categoría que pueda validarse "
                            "contra cotas lineales."
                        ),
                    )
                )

                continue

            # ------------------------------------------------
            # MÉTRICA LINEAL
            # ------------------------------------------------

            matches = (
                self._find_dimension_matches(
                    candidate.value,
                    evidence.dimension_candidates,
                )
            )

            match_count = len(
                matches
            )

            if match_count == 0:
                reason = (
                    "El valor no fue localizado como cota "
                    "vectorial en el PDF."
                )

            elif match_count == 1:
                reason = (
                    "Existe una coincidencia numérica única, "
                    "pero falta demostrar que esa cota "
                    "corresponde espacialmente al elemento."
                )

            else:
                reason = (
                    "Existen varias cotas con el mismo valor. "
                    "La asociación deberá resolverse mediante "
                    "posición, ejes y geometría."
                )

            result.append(
                GroundedMetricCandidate(
                    element_type=
                        candidate.element_type,

                    element_id=
                        candidate.element_id,

                    level=
                        candidate.level,

                    field=
                        candidate.field,

                    metric_kind=
                        metric_kind,

                    value=
                        candidate.value,

                    model_state=
                        candidate.state,

                    model_confidence=
                        candidate.confidence,

                    model_source=
                        model_source,

                    value_present_in_pdf=
                        bool(
                            matches
                        ),

                    match_count=
                        match_count,

                    ambiguous_numeric_match=(
                        match_count > 1
                    ),

                    pdf_matches=[
                        self._evidence_item_to_dict(
                            item
                        )
                        for item
                        in matches
                    ],

                    candidate_evidence=
                        candidate_evidence,

                    association_validated=
                        False,

                    association_reason=
                        reason,
                )
            )

        return result

    # ========================================================
    # TIPO DE MÉTRICA
    # ========================================================

    def _metric_kind(
        self,
        field_name: str,
    ) -> str:
        normalized = str(
            field_name or ""
        ).strip().lower()

        if (
            normalized
            in self.AREA_FIELDS
            or normalized.endswith(
                "_m2"
            )
        ):
            return "area"

        if (
            normalized
            in self.LINEAR_FIELDS
            or normalized.endswith(
                "_m"
            )
        ):
            return "linear"

        return "unknown"

    # ========================================================
    # COTAS DEL SCHEMA
    # ========================================================

    def _ground_canonical_dimensions(
        self,
        extraction: QuantiaExtractionSchema,
        evidence: PDFPlanEvidence,
    ) -> None:
        """
        Agrega evidencia PyMuPDF a las cotas observadas por
        Gemini sin promocionar valor_m.

        El reconciliador conserva:

            valor_original

        pero deja:

            valor_m = None

        hasta grounding geométrico.

        Este método conserva esa regla.
        """

        for level in extraction.niveles:
            for dimension in level.cotas:
                observed_value = (
                    dimension.valor_original
                )

                if observed_value is None:
                    continue

                try:
                    numeric_value = float(
                        observed_value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                matches = (
                    self._find_dimension_matches(
                        numeric_value,
                        evidence.dimension_candidates,
                    )
                )

                if not matches:
                    continue

                for match in matches:
                    evidence_item = (
                        self._to_quantia_evidence(
                            match,
                            numeric_value,
                        )
                    )

                    if self._contains_equivalent_evidence(
                        dimension.evidencia,
                        evidence_item,
                    ):
                        continue

                    dimension.evidencia.append(
                        evidence_item
                    )

                # CRÍTICO:
                #
                # no promocionar todavía.
                dimension.valor_m = None

    # ========================================================
    # ESCALERAS
    # ========================================================

    def _ground_stairs(
        self,
        extraction: QuantiaExtractionSchema,
        evidence: PDFPlanEvidence,
    ) -> list[StairGrounding]:
        results: list[
            StairGrounding
        ] = []

        for stair in (
            extraction
            .elementos_especiales
            .escaleras
        ):
            normalized_direction = (
                self._normalize_text(
                    stair.sentido
                )
            )

            matches: list[
                PDFEvidenceItem
            ] = []

            if normalized_direction:
                for item in (
                    evidence.stair_markers
                ):
                    if (
                        self._normalize_text(
                            item.text
                        )
                        == normalized_direction
                    ):
                        matches.append(
                            item
                        )

            matched = bool(
                matches
            )

            results.append(
                StairGrounding(
                    id_propuesto=
                        stair.id_propuesto,

                    nivel=
                        stair.nivel,

                    sentido=
                        stair.sentido,

                    vector_text_match=
                        matched,

                    matches=[
                        self._evidence_item_to_dict(
                            item
                        )
                        for item
                        in matches
                    ],

                    source=(
                        "pymupdf+vision"
                        if matched
                        else "vision"
                    ),
                )
            )

        return results

    # ========================================================
    # COTAS PDF SIN CORRESPONDENCIA NUMÉRICA
    # ========================================================

    def _find_unmatched_pdf_dimensions(
        self,
        grounded_metrics: list[
            GroundedMetricCandidate
        ],
        evidence: PDFPlanEvidence,
    ) -> list[
        dict[str, Any]
    ]:
        """
        Devuelve cotas PDF que no coincidieron numéricamente
        con ninguna métrica LINEAL propuesta por Gemini.

        Esto NO significa que las demás cotas ya estén
        espacialmente asignadas.

        Únicamente indica coincidencia numérica.
        """

        matched_evidence_keys: set[
            tuple[Any, ...]
        ] = set()

        for metric in grounded_metrics:
            if (
                metric.metric_kind
                != "linear"
            ):
                continue

            for match in metric.pdf_matches:
                key = (
                    match.get(
                        "page"
                    ),
                    match.get(
                        "text"
                    ),
                    tuple(
                        match.get(
                            "bbox",
                            [],
                        )
                    ),
                )

                matched_evidence_keys.add(
                    key
                )

        result: list[
            dict[str, Any]
        ] = []

        for item in (
            evidence.dimension_candidates
        ):
            item_dict = (
                self._evidence_item_to_dict(
                    item
                )
            )

            key = (
                item_dict.get(
                    "page"
                ),
                item_dict.get(
                    "text"
                ),
                tuple(
                    item_dict.get(
                        "bbox",
                        [],
                    )
                ),
            )

            if key in matched_evidence_keys:
                continue

            result.append(
                item_dict
            )

        return result

    # ========================================================
    # MATCH TEXTO
    # ========================================================

    def _text_field_match(
        self,
        *,
        field_name: str,
        value: str | None,
        candidates: list[
            PDFEvidenceItem
        ],
    ) -> GroundedTextField:
        if value is None:
            return GroundedTextField(
                field=
                    field_name,

                value=
                    None,

                matched=
                    False,

                matches=
                    [],
            )

        normalized_value = (
            self._normalize_text(
                value
            )
        )

        matches: list[
            PDFEvidenceItem
        ] = []

        for item in candidates:
            candidate_text = (
                self._normalize_text(
                    item.text
                )
            )

            if (
                not candidate_text
                or not normalized_value
            ):
                continue

            if (
                candidate_text
                == normalized_value
            ):
                matches.append(
                    item
                )
                continue

            # Para títulos/tipos de plano permitimos
            # contención textual.
            #
            # La posición permanece disponible para auditoría.

            if (
                normalized_value
                in candidate_text
            ):
                matches.append(
                    item
                )
                continue

            if (
                candidate_text
                in normalized_value
            ):
                matches.append(
                    item
                )

        return GroundedTextField(
            field=
                field_name,

            value=
                value,

            matched=
                bool(
                    matches
                ),

            matches=[
                self._evidence_item_to_dict(
                    item
                )
                for item
                in matches
            ],
        )

    # ========================================================
    # MATCH NUMÉRICO
    # ========================================================

    def _find_dimension_matches(
        self,
        value_m: float,
        candidates: list[
            PDFEvidenceItem
        ],
    ) -> list[
        PDFEvidenceItem
    ]:
        """
        Busca coincidencias numéricas.

        Si la evidencia PDF contiene unidad explícita:

            mm
            cm
            m

        se convierte a metros.

        Si NO contiene unidad:

            2.60

        se conserva como candidato comparable, pero la ausencia
        de unidad queda registrada en la evidencia y NO produce
        promoción automática.
        """

        matches: list[
            PDFEvidenceItem
        ] = []

        for candidate in candidates:
            comparable_value = (
                self._dimension_value_for_comparison(
                    candidate
                )
            )

            if comparable_value is None:
                continue

            if math.isclose(
                comparable_value,
                value_m,
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                matches.append(
                    candidate
                )

        return matches

    # ========================================================
    # VALOR NUMÉRICO PDF
    # ========================================================

    @staticmethod
    def _dimension_value_for_comparison(
        item: PDFEvidenceItem,
    ) -> float | None:
        """
        Convierte una evidencia PDF a valor comparable.

        Unidad explícita:

            mm → m
            cm → m
            m  → m

        Sin unidad:

            se conserva el número tal como aparece.

        La ausencia de unidad permanece visible en
        PDFEvidenceItem.numeric_unit.
        """

        value = getattr(
            item,
            "numeric_value",
            None,
        )

        if value is None:
            try:
                value = float(
                    str(
                        item.text
                    )
                    .strip()
                    .replace(
                        ",",
                        ".",
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                return None

        unit = getattr(
            item,
            "numeric_unit",
            None,
        )

        if unit is None:
            return float(
                value
            )

        normalized_unit = str(
            unit
        ).strip().lower()

        if normalized_unit == "m":
            return float(
                value
            )

        if normalized_unit == "cm":
            return (
                float(
                    value
                )
                / 100.0
            )

        if normalized_unit == "mm":
            return (
                float(
                    value
                )
                / 1000.0
            )

        return None

    # ========================================================
    # EVIDENCIA QUANTIA
    # ========================================================

    @staticmethod
    def _to_quantia_evidence(
        item: PDFEvidenceItem,
        value: float,
    ) -> EvidenceItem:
        unit = getattr(
            item,
            "numeric_unit",
            None,
        )

        if unit:
            unit_description = (
                f" con unidad explícita {unit}"
            )
        else:
            unit_description = (
                " sin unidad explícita"
            )

        return EvidenceItem(
            descripcion=(
                "Valor numérico "
                f"{value:g} localizado en el PDF"
                f"{unit_description}. "
                "La asociación espacial de esta cota "
                "permanece pendiente."
            ),

            pagina=
                item.page,

            fuente=
                "pymupdf",

            texto_original=
                item.text,

            bbox=
                BoundingBox(
                    x_min=
                        item.x0,

                    y_min=
                        item.y0,

                    x_max=
                        item.x1,

                    y_max=
                        item.y1,
                ),

            confianza=
                1.0,
        )

    # ========================================================
    # EVITAR EVIDENCIA DUPLICADA
    # ========================================================

    @staticmethod
    def _contains_equivalent_evidence(
        existing_items: list[
            EvidenceItem
        ],
        new_item: EvidenceItem,
    ) -> bool:
        """
        Evita agregar repetidamente la misma evidencia si el
        servicio se ejecuta más de una vez.
        """

        for existing in existing_items:
            if (
                existing.fuente
                != new_item.fuente
            ):
                continue

            if (
                existing.pagina
                != new_item.pagina
            ):
                continue

            if (
                existing.texto_original
                != new_item.texto_original
            ):
                continue

            existing_bbox = (
                existing.bbox
            )

            new_bbox = (
                new_item.bbox
            )

            if (
                existing_bbox is None
                and new_bbox is None
            ):
                return True

            if (
                existing_bbox is None
                or new_bbox is None
            ):
                continue

            if (
                math.isclose(
                    existing_bbox.x_min,
                    new_bbox.x_min,
                    abs_tol=1e-6,
                )
                and math.isclose(
                    existing_bbox.y_min,
                    new_bbox.y_min,
                    abs_tol=1e-6,
                )
                and math.isclose(
                    existing_bbox.x_max,
                    new_bbox.x_max,
                    abs_tol=1e-6,
                )
                and math.isclose(
                    existing_bbox.y_max,
                    new_bbox.y_max,
                    abs_tol=1e-6,
                )
            ):
                return True

        return False

    # ========================================================
    # NORMALIZACIÓN TEXTO
    # ========================================================

    @staticmethod
    def _normalize_text(
        value: str | None,
    ) -> str:
        if value is None:
            return ""

        text = unicodedata.normalize(
            "NFKD",
            str(
                value
            ),
        )

        text = "".join(
            character
            for character in text
            if not unicodedata.combining(
                character
            )
        )

        return " ".join(
            text
            .lower()
            .strip()
            .split()
        )

    # ========================================================
    # EVIDENCIA A DICT
    # ========================================================

    def _evidence_item_to_dict(
        self,
        item: PDFEvidenceItem,
    ) -> dict[str, Any]:
        """
        Conserva toda la información espacial necesaria para
        la siguiente fase.

        Especialmente:

            center
            bbox
            numeric_value
            numeric_unit

        No reducir la evidencia solo a texto.
        """

        comparable_value = (
            self._dimension_value_for_comparison(
                item
            )
        )

        numeric_value = getattr(
            item,
            "numeric_value",
            None,
        )

        numeric_unit = getattr(
            item,
            "numeric_unit",
            None,
        )

        center_x = getattr(
            item,
            "center_x",
            (
                item.x0
                + item.x1
            )
            / 2.0,
        )

        center_y = getattr(
            item,
            "center_y",
            (
                item.y0
                + item.y1
            )
            / 2.0,
        )

        source = getattr(
            item,
            "source",
            "pymupdf_vector_text",
        )

        normalized_text = getattr(
            item,
            "normalized_text",
            self._normalize_text(
                item.text
            ),
        )

        return {
            "kind":
                item.kind,

            "text":
                item.text,

            "normalized_text":
                normalized_text,

            "page":
                item.page,

            "bbox": [
                item.x0,
                item.y0,
                item.x1,
                item.y1,
            ],

            "center": [
                center_x,
                center_y,
            ],

            "numeric_value":
                numeric_value,

            "numeric_unit":
                numeric_unit,

            "comparison_value":
                comparable_value,

            "unit_explicit": (
                numeric_unit
                is not None
            ),

            "source":
                source,

            "confidence":
                item.confidence,
        }


# ============================================================
# DEPENDENCY FACTORY
# ============================================================


def get_pdf_quantia_grounding_service(
) -> PDFQuantiaGroundingService:
    return PDFQuantiaGroundingService()