from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.schemas.quantia_extraction import (
    ConstructiveValue,
    EvidenceItem,
    ExtractedConstructiveInfo,
    ExtractedDimension,
    ExtractedDocumentInfo,
    ExtractedDoor,
    ExtractedLevel,
    ExtractedPlot,
    ExtractedSpace,
    ExtractedSpecialElements,
    ExtractedStair,
    ExtractedWindow,
    ExtractionConflict,
    ExtractionState,
    PlotBoundaries,
    QuantiaExtractionSchema,
    RequiredConfirmation,
    SpaceLocation,
    SpaceRelations,
)


# ============================================================
# RESULTADOS DE RECONCILIACIÓN
# ============================================================


@dataclass(slots=True)
class MetricCandidate:
    """
    Medida propuesta por Gemini.

    Esta medida todavía NO ha sido validada mediante:

    - evidencia PDF;
    - OCR;
    - ejes;
    - cadenas de cotas;
    - geometría OpenCV;
    - grounding espacial.

    Por tanto NO puede promoverse directamente como dimensión
    constructiva definitiva.
    """

    element_type: str
    element_id: str

    level: str | None

    field: str
    value: float

    state: str
    confidence: float

    evidence: list[str] = field(
        default_factory=list
    )

    source: str = "gemini_vision"


@dataclass(slots=True)
class QuantiaReconciliationResult:
    """
    Resultado de la primera reconciliación semántica.

    extraction:
        Contrato canónico Quantia todavía SIN geometría
        constructiva confirmada.

    metric_candidates:
        Medidas propuestas por Gemini pendientes de grounding.

    discarded_model_confirmations:
        Preguntas o confirmaciones sugeridas por Gemini que no
        se transfieren automáticamente al usuario.

    discarded_unidentified:
        Datos irrelevantes descartados.

    unmapped_constructive_items:
        Información constructiva detectada que todavía no tiene
        campo canónico específico.
    """

    extraction: QuantiaExtractionSchema

    metric_candidates: list[
        MetricCandidate
    ] = field(
        default_factory=list
    )

    discarded_model_confirmations: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    discarded_unidentified: list[
        str
    ] = field(
        default_factory=list
    )

    unmapped_constructive_items: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )


# ============================================================
# CONSTANTES
# ============================================================


QUANTIA_RELEVANT_UNIDENTIFIED_KEYWORDS = (
    "espesor",
    "altura",
    "altura libre",
    "nivel de piso",
    "n.p.t",
    "npt",
    "cota",
    "dimension",
    "medida",
    "losa",
    "entrepiso",
    "ciment",
    "material",
    "sistema constructivo",
    "sistema estructural",
    "destino",
    "escalera",
    "puerta",
    "ventana",
    "muro",
    "eje",
)


NULL_TEXT_VALUES = {
    "",
    "no especificado",
    "no especificado en plano",
    "no identificado",
    "no identificada",
    "no identificado en plano",
    "no identificada en plano",
    "desconocido",
    "desconocida",
    "null",
    "none",
}


# ============================================================
# HELPERS GENERALES
# ============================================================


def _normalize_for_matching(
    value: Any,
) -> str:
    """
    Normalización exclusivamente para comparaciones internas.

    No modifica el texto que termina en el schema.
    """

    text = str(
        value or ""
    ).strip().lower()

    decomposed = unicodedata.normalize(
        "NFD",
        text,
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


def _normalize_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    normalized = (
        _normalize_for_matching(
            text
        )
    )

    normalized_nulls = {
        _normalize_for_matching(
            item
        )
        for item in NULL_TEXT_VALUES
    }

    if normalized in normalized_nulls:
        return None

    return text


def _required_text(
    value: Any,
    *,
    field_name: str,
) -> str:
    text = _normalize_text(
        value
    )

    if text is None:
        raise ValueError(
            f"Campo requerido vacío: {field_name}"
        )

    return text


def _number(
    value: Any,
) -> float | None:
    """
    Convierte únicamente valores numéricos explícitos.

    No interpreta strings numéricos porque esa normalización
    corresponde al transporte/schema previo.
    """

    if isinstance(
        value,
        bool,
    ):
        return None

    if not isinstance(
        value,
        (int, float),
    ):
        return None

    number = float(
        value
    )

    if number <= 0:
        return None

    return number


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

    number = float(
        value
    )

    if number < 0:
        return 0.0

    if number > 1:
        return 1.0

    return number


def _state(
    value: Any,
) -> ExtractionState:
    """
    Mantiene únicamente estados válidos del contrato Quantia.

    Gemini no puede crear estados nuevos.
    """

    try:
        return ExtractionState(
            str(
                value
            ).strip()
        )

    except (
        ValueError,
        AttributeError,
    ):
        return (
            ExtractionState.NO_IDENTIFICADO
        )


def _string_list(
    value: Any,
) -> list[str]:
    if not isinstance(
        value,
        list,
    ):
        return []

    result: list[str] = []

    for item in value:
        text = _normalize_text(
            item
        )

        if text is not None:
            result.append(
                text
            )

    return result


def _evidence(
    value: Any,
) -> list[EvidenceItem]:
    """
    La evidencia contenida en este transporte procede de la
    interpretación visual Gemini.

    Posteriormente podrán agregarse evidencias:

    - pymupdf;
    - ocr;
    - opencv;
    - grounding;
    - regla Quantia.
    """

    descriptions = (
        _string_list(
            value
        )
    )

    return [
        EvidenceItem(
            descripcion=
                description,

            fuente=
                "vision",
        )
        for description in descriptions
    ]


# ============================================================
# MÉTRICAS CANDIDATAS
# ============================================================


def _register_metric_candidate(
    candidates: list[
        MetricCandidate
    ],
    *,
    element_type: str,
    element_id: str,
    level: str | None,
    field_name: str,
    value: Any,
    state: Any,
    confidence: Any,
    evidence: Any,
) -> None:
    """
    Guarda una medida Gemini para grounding posterior.

    NO modifica todavía el schema canónico.
    """

    number = _number(
        value
    )

    if number is None:
        return

    candidates.append(
        MetricCandidate(
            element_type=
                element_type,

            element_id=
                element_id,

            level=
                level,

            field=
                field_name,

            value=
                number,

            state=
                _state(
                    state
                ).value,

            confidence=
                _confidence(
                    confidence
                ),

            evidence=
                _string_list(
                    evidence
                ),

            source=
                "gemini_vision",
        )
    )


# ============================================================
# DOCUMENTO
# ============================================================


def _build_document(
    payload: dict[str, Any],
) -> ExtractedDocumentInfo:
    document = payload.get(
        "documento"
    )

    if not isinstance(
        document,
        dict,
    ):
        document = {}

    return ExtractedDocumentInfo(
        titulo=
            _normalize_text(
                document.get(
                    "titulo"
                )
            ),

        tipo_plano=
            _normalize_text(
                document.get(
                    "tipo_plano"
                )
            ),

        escala=
            _normalize_text(
                document.get(
                    "escala"
                )
            ),

        orientacion=
            _normalize_text(
                document.get(
                    "orientacion"
                )
            ),

        paginas_analizadas=[],
    )


# ============================================================
# PREDIO
# ============================================================


def _build_plot(
    payload: dict[str, Any],
    *,
    metric_candidates: list[
        MetricCandidate
    ],
) -> ExtractedPlot:
    """
    Gemini puede leer:

        ancho
        fondo
        área

    pero estas medidas NO se promueven automáticamente.

    Caso Miguel H:

        una asociación métrica visual plausible resultó ser
        incorrecta hasta contrastarla contra los ejes.

    Por tanto ancho/fondo/área permanecen pendientes de
    grounding.
    """

    plot = payload.get(
        "predio"
    )

    if not isinstance(
        plot,
        dict,
    ):
        plot = {}

    boundaries = plot.get(
        "colindancias"
    )

    if not isinstance(
        boundaries,
        dict,
    ):
        boundaries = {}

    state = _state(
        plot.get(
            "estado"
        )
    )

    confidence = _confidence(
        plot.get(
            "confianza"
        )
    )

    evidence = plot.get(
        "evidencia"
    )

    _register_metric_candidate(
        metric_candidates,
        element_type=
            "predio",
        element_id=
            "PREDIO",
        level=
            None,
        field_name=
            "ancho_m",
        value=
            plot.get(
                "ancho_m"
            ),
        state=
            state.value,
        confidence=
            confidence,
        evidence=
            evidence,
    )

    _register_metric_candidate(
        metric_candidates,
        element_type=
            "predio",
        element_id=
            "PREDIO",
        level=
            None,
        field_name=
            "fondo_m",
        value=
            plot.get(
                "fondo_m"
            ),
        state=
            state.value,
        confidence=
            confidence,
        evidence=
            evidence,
    )

    # Si Gemini ofrece área explícita, también queda como
    # candidata independiente.
    #
    # NO calculamos ancho × fondo todavía.

    _register_metric_candidate(
        metric_candidates,
        element_type=
            "predio",
        element_id=
            "PREDIO",
        level=
            None,
        field_name=
            "area_m2",
        value=
            plot.get(
                "area_m2"
            ),
        state=
            state.value,
        confidence=
            confidence,
        evidence=
            evidence,
    )

    return ExtractedPlot(
        ancho_m=
            None,

        fondo_m=
            None,

        area_m2=
            None,

        acceso_principal=
            _normalize_text(
                plot.get(
                    "acceso_principal"
                )
            ),

        orientacion=
            _normalize_text(
                plot.get(
                    "orientacion"
                )
            ),

        colindancias=
            PlotBoundaries(
                norte=
                    _normalize_text(
                        boundaries.get(
                            "norte"
                        )
                    ),

                sur=
                    _normalize_text(
                        boundaries.get(
                            "sur"
                        )
                    ),

                este=
                    _normalize_text(
                        boundaries.get(
                            "este"
                        )
                    ),

                oeste=
                    _normalize_text(
                        boundaries.get(
                            "oeste"
                        )
                    ),
            ),

        estado=
            state,

        confianza=
            confidence,

        evidencia=
            _evidence(
                evidence
            ),
    )


# ============================================================
# PUERTAS
# ============================================================


def _build_doors(
    doors: Any,
    *,
    space_id: str,
    level_name: str,
    metric_candidates: list[
        MetricCandidate
    ],
) -> list[ExtractedDoor]:
    if not isinstance(
        doors,
        list,
    ):
        return []

    result: list[
        ExtractedDoor
    ] = []

    for index, door in enumerate(
        doors,
        start=1,
    ):
        if not isinstance(
            door,
            dict,
        ):
            continue

        candidate_id = (
            f"{space_id}_PUERTA_{index}"
        )

        state = _state(
            door.get(
                "estado"
            )
        )

        confidence = _confidence(
            door.get(
                "confianza"
            )
        )

        evidence = door.get(
            "evidencia"
        )

        for field_name in (
            "ancho_m",
            "alto_m",
        ):
            _register_metric_candidate(
                metric_candidates,
                element_type=
                    "puerta",
                element_id=
                    candidate_id,
                level=
                    level_name,
                field_name=
                    field_name,
                value=
                    door.get(
                        field_name
                    ),
                state=
                    state.value,
                confidence=
                    confidence,
                evidence=
                    evidence,
            )

        result.append(
            ExtractedDoor(
                id_propuesto=
                    candidate_id,

                hacia=
                    _normalize_text(
                        door.get(
                            "hacia"
                        )
                    ),

                # Pendientes de grounding.
                ancho_m=
                    None,

                alto_m=
                    None,

                ubicacion=
                    _normalize_text(
                        door.get(
                            "ubicacion"
                        )
                    ),

                # La referencia real al muro solo existe
                # después de reconstrucción geométrica.
                muro_referencia=
                    None,

                estado=
                    state,

                confianza=
                    confidence,

                evidencia=
                    _evidence(
                        evidence
                    ),
            )
        )

    return result


# ============================================================
# VENTANAS
# ============================================================


def _build_windows(
    windows: Any,
    *,
    space_id: str,
    level_name: str,
    metric_candidates: list[
        MetricCandidate
    ],
) -> list[ExtractedWindow]:
    if not isinstance(
        windows,
        list,
    ):
        return []

    result: list[
        ExtractedWindow
    ] = []

    for index, window in enumerate(
        windows,
        start=1,
    ):
        if not isinstance(
            window,
            dict,
        ):
            continue

        candidate_id = (
            f"{space_id}_VENTANA_{index}"
        )

        state = _state(
            window.get(
                "estado"
            )
        )

        confidence = _confidence(
            window.get(
                "confianza"
            )
        )

        evidence = window.get(
            "evidencia"
        )

        for field_name in (
            "ancho_m",
            "alto_m",
        ):
            _register_metric_candidate(
                metric_candidates,
                element_type=
                    "ventana",
                element_id=
                    candidate_id,
                level=
                    level_name,
                field_name=
                    field_name,
                value=
                    window.get(
                        field_name
                    ),
                state=
                    state.value,
                confidence=
                    confidence,
                evidence=
                    evidence,
            )

        result.append(
            ExtractedWindow(
                id_propuesto=
                    candidate_id,

                ancho_m=
                    None,

                alto_m=
                    None,

                ubicacion=
                    _normalize_text(
                        window.get(
                            "ubicacion"
                        )
                    ),

                muro_referencia=
                    None,

                estado=
                    state,

                confianza=
                    confidence,

                evidencia=
                    _evidence(
                        evidence
                    ),
            )
        )

    return result


# ============================================================
# ESPACIOS
# ============================================================


def _build_space(
    space: dict[str, Any],
    *,
    level_name: str,
    metric_candidates: list[
        MetricCandidate
    ],
) -> ExtractedSpace:
    """
    Gemini identifica principalmente:

    - recinto;
    - nombre;
    - función;
    - relaciones;
    - vanos visibles.

    Pero:

        bbox Gemini != geometría del espacio

    y:

        medidas Gemini != medidas confirmadas

    La geometría final será creada posteriormente.
    """

    space_id = _required_text(
        space.get(
            "id_propuesto"
        ),
        field_name=(
            "niveles[].espacios[].id_propuesto"
        ),
    )

    space_name = _required_text(
        space.get(
            "nombre"
        ),
        field_name=(
            "niveles[].espacios[].nombre"
        ),
    )

    state = _state(
        space.get(
            "estado"
        )
    )

    confidence = _confidence(
        space.get(
            "confianza"
        )
    )

    evidence = space.get(
        "evidencia"
    )

    for field_name in (
        "ancho_m",
        "largo_m",
        "area_m2",
    ):
        _register_metric_candidate(
            metric_candidates,
            element_type=
                "espacio",
            element_id=
                space_id,
            level=
                level_name,
            field_name=
                field_name,
            value=
                space.get(
                    field_name
                ),
            state=
                state.value,
            confidence=
                confidence,
            evidence=
                evidence,
        )

    return ExtractedSpace(
        id_propuesto=
            space_id,

        nombre=
            space_name,

        tipo=
            _normalize_text(
                space.get(
                    "tipo"
                )
            ),

        ancho_m=
            None,

        largo_m=
            None,

        area_m2=
            None,

        ubicacion=
            SpaceLocation(
                zona=
                    _normalize_text(
                        space.get(
                            "ubicacion"
                        )
                    ),

                referencia=
                    None,
            ),

        relaciones=
            SpaceRelations(
                comunica_con=
                    _string_list(
                        space.get(
                            "comunica_con"
                        )
                    ),

                comparte_muro_con=
                    _string_list(
                        space.get(
                            "comparte_muro_con"
                        )
                    ),
            ),

        # Nunca usar bbox Gemini como polígono.
        geometria=
            None,

        puertas=
            _build_doors(
                space.get(
                    "puertas"
                ),
                space_id=
                    space_id,
                level_name=
                    level_name,
                metric_candidates=
                    metric_candidates,
            ),

        ventanas=
            _build_windows(
                space.get(
                    "ventanas"
                ),
                space_id=
                    space_id,
                level_name=
                    level_name,
                metric_candidates=
                    metric_candidates,
            ),

        doble_altura=
            None,

        estado=
            state,

        confianza=
            confidence,

        evidencia=
            _evidence(
                evidence
            ),
    )


# ============================================================
# COTAS VISUALES GEMINI
# ============================================================


def _build_dimensions(
    dimensions: Any,
    *,
    level_name: str,
    metric_candidates: list[
        MetricCandidate
    ],
) -> list[ExtractedDimension]:
    """
    Las cotas leídas por Gemini se conservan como observaciones.

    El número NO gobierna todavía la geometría.

    Ejemplo:

        Gemini detecta 2.60

    Todavía falta demostrar:

        qué tramo mide;
        entre qué ejes;
        en qué planta;
        qué geometría controla.

    Por eso valor_m queda pendiente de grounding.
    """

    if not isinstance(
        dimensions,
        list,
    ):
        return []

    result: list[
        ExtractedDimension
    ] = []

    for index, dimension in enumerate(
        dimensions,
        start=1,
    ):
        if not isinstance(
            dimension,
            dict,
        ):
            continue

        value = _number(
            dimension.get(
                "valor_m"
            )
        )

        state = _state(
            dimension.get(
                "estado"
            )
        )

        confidence = _confidence(
            dimension.get(
                "confianza"
            )
        )

        evidence = dimension.get(
            "evidencia"
        )

        candidate_id = (
            f"{level_name}_COTA_{index}"
        )

        if value is not None:
            _register_metric_candidate(
                metric_candidates,
                element_type=
                    "cota",
                element_id=
                    candidate_id,
                level=
                    level_name,
                field_name=
                    "valor_m",
                value=
                    value,
                state=
                    state.value,
                confidence=
                    confidence,
                evidence=
                    evidence,
            )

        result.append(
            ExtractedDimension(
                texto_original=
                    _normalize_text(
                        dimension.get(
                            "texto"
                        )
                    ),

                # Conservamos la lectura original como
                # observación del modelo.
                valor_original=
                    value,

                unidad_original=(
                    "m"
                    if value is not None
                    else None
                ),

                # Todavía NO gobierna geometría.
                valor_m=
                    None,

                referencia=
                    _normalize_text(
                        dimension.get(
                            "referencia"
                        )
                    ),

                estado=
                    state,

                confianza=
                    confidence,

                evidencia=
                    _evidence(
                        evidence
                    ),
            )
        )

    return result


# ============================================================
# ESCALERAS
# ============================================================


def _build_stairs(
    stairs: Any,
    *,
    level_name: str,
    metric_candidates: list[
        MetricCandidate
    ],
) -> list[ExtractedStair]:
    if not isinstance(
        stairs,
        list,
    ):
        return []

    result: list[
        ExtractedStair
    ] = []

    for index, stair in enumerate(
        stairs,
        start=1,
    ):
        if not isinstance(
            stair,
            dict,
        ):
            continue

        candidate_id = (
            f"{level_name}_ESCALERA_{index}"
        )

        state = _state(
            stair.get(
                "estado"
            )
        )

        confidence = _confidence(
            stair.get(
                "confianza"
            )
        )

        evidence = stair.get(
            "evidencia"
        )

        for field_name in (
            "ancho_m",
            "largo_m",
        ):
            _register_metric_candidate(
                metric_candidates,
                element_type=
                    "escalera",
                element_id=
                    candidate_id,
                level=
                    level_name,
                field_name=
                    field_name,
                value=
                    stair.get(
                        field_name
                    ),
                state=
                    state.value,
                confidence=
                    confidence,
                evidence=
                    evidence,
            )

        result.append(
            ExtractedStair(
                id_propuesto=
                    candidate_id,

                nivel=
                    level_name,

                tipo=
                    _normalize_text(
                        stair.get(
                            "tipo"
                        )
                    ),

                ancho_m=
                    None,

                largo_m=
                    None,

                sentido=
                    _normalize_text(
                        stair.get(
                            "sentido"
                        )
                    ),

                ubicacion=
                    _normalize_text(
                        stair.get(
                            "ubicacion"
                        )
                    ),

                comunica_con=
                    _string_list(
                        stair.get(
                            "comunica_con"
                        )
                    ),

                estado=
                    state,

                confianza=
                    confidence,

                evidencia=
                    _evidence(
                        evidence
                    ),
            )
        )

    return result


# ============================================================
# NIVELES
# ============================================================


def _build_levels(
    payload: dict[str, Any],
    *,
    metric_candidates: list[
        MetricCandidate
    ],
) -> tuple[
    list[ExtractedLevel],
    list[ExtractedStair],
]:
    levels_payload = payload.get(
        "niveles"
    )

    if not isinstance(
        levels_payload,
        list,
    ):
        return [], []

    levels: list[
        ExtractedLevel
    ] = []

    all_stairs: list[
        ExtractedStair
    ] = []

    for level in levels_payload:
        if not isinstance(
            level,
            dict,
        ):
            continue

        level_name = _required_text(
            level.get(
                "nombre"
            ),
            field_name=
                "niveles[].nombre",
        )

        spaces_payload = (
            level.get(
                "espacios"
            )
        )

        spaces: list[
            ExtractedSpace
        ] = []

        if isinstance(
            spaces_payload,
            list,
        ):
            for space in spaces_payload:
                if not isinstance(
                    space,
                    dict,
                ):
                    continue

                spaces.append(
                    _build_space(
                        space,
                        level_name=
                            level_name,
                        metric_candidates=
                            metric_candidates,
                    )
                )

        stairs = _build_stairs(
            level.get(
                "escaleras"
            ),
            level_name=
                level_name,
            metric_candidates=
                metric_candidates,
        )

        all_stairs.extend(
            stairs
        )

        levels.append(
            ExtractedLevel(
                nombre=
                    level_name,

                # No inferir elevación sin evidencia.
                elevacion_m=
                    None,

                espacios=
                    spaces,

                # Los muros aparecen después del grounding
                # OpenCV/ejes/espacios.
                muros=
                    [],

                cotas=
                    _build_dimensions(
                        level.get(
                            "cotas"
                        ),
                        level_name=
                            level_name,
                        metric_candidates=
                            metric_candidates,
                    ),
            )
        )

    return (
        levels,
        all_stairs,
    )


# ============================================================
# INFORMACIÓN CONSTRUCTIVA
# ============================================================


def _constructive_value(
    item: dict[str, Any],
) -> ConstructiveValue:
    return ConstructiveValue(
        valor=
            _normalize_text(
                item.get(
                    "valor"
                )
            ),

        estado=
            _state(
                item.get(
                    "estado"
                )
            ),

        confianza=
            _confidence(
                item.get(
                    "confianza"
                )
            ),

        evidencia=
            _evidence(
                item.get(
                    "evidencia"
                )
            ),
    )


def _build_constructive_info(
    payload: dict[str, Any],
) -> tuple[
    ExtractedConstructiveInfo,
    list[dict[str, Any]],
]:
    items = payload.get(
        "informacion_constructiva"
    )

    if not isinstance(
        items,
        list,
    ):
        items = []

    system_constructive = None
    system_structural = None
    foundation = None
    slab = None

    materials: list[
        ConstructiveValue
    ] = []

    unmapped: list[
        dict[str, Any]
    ] = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        field_name = (
            _normalize_text(
                item.get(
                    "campo"
                )
            )
            or ""
        )

        normalized = (
            _normalize_for_matching(
                field_name
            )
        )

        value = (
            _constructive_value(
                item
            )
        )

        if (
            "sistema constructivo"
            in normalized
        ):
            system_constructive = (
                value
            )
            continue

        if (
            "sistema estructural"
            in normalized
        ):
            system_structural = (
                value
            )
            continue

        if "ciment" in normalized:
            foundation = (
                value
            )
            continue

        if (
            "tipo de losa"
            in normalized
            or "sistema de losa"
            in normalized
            or "sistemas de losa"
            in normalized
            or "entrepiso"
            in normalized
        ):
            slab = (
                value
            )
            continue

        if "material" in normalized:
            materials.append(
                value
            )
            continue

        # No eliminar información no mapeada.
        #
        # Castillo, Armex, cadenas, etc. pueden ser útiles
        # después para reglas Quantia.

        unmapped.append(
            dict(
                item
            )
        )

    return (
        ExtractedConstructiveInfo(
            sistema_constructivo=
                system_constructive,

            sistema_estructural=
                system_structural,

            tipo_cimentacion=
                foundation,

            tipo_losa=
                slab,

            alturas=
                [],

            materiales=
                materials,
        ),
        unmapped,
    )


# ============================================================
# CONFLICTOS
# ============================================================


def _build_conflicts(
    payload: dict[str, Any],
) -> list[ExtractionConflict]:
    items = payload.get(
        "conflictos"
    )

    if not isinstance(
        items,
        list,
    ):
        return []

    result: list[
        ExtractionConflict
    ] = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        description = _normalize_text(
            item.get(
                "descripcion"
            )
        )

        if description is None:
            continue

        result.append(
            ExtractionConflict(
                codigo=
                    None,

                descripcion=
                    description,

                elementos_relacionados=
                    _string_list(
                        item.get(
                            "elementos"
                        )
                    ),

                evidencia=
                    _evidence(
                        item.get(
                            "evidencia"
                        )
                    ),

                requiere_confirmacion=
                    True,
            )
        )

    return result


# ============================================================
# DATOS NO IDENTIFICADOS
# ============================================================


def _is_quantia_relevant_unidentified(
    text: str,
) -> bool:
    normalized = (
        _normalize_for_matching(
            text
        )
    )

    return any(
        keyword
        in normalized
        for keyword
        in QUANTIA_RELEVANT_UNIDENTIFIED_KEYWORDS
    )


def _filter_unidentified(
    payload: dict[str, Any],
) -> tuple[
    list[str],
    list[str],
]:
    items = _string_list(
        payload.get(
            "datos_no_identificados"
        )
    )

    accepted: list[str] = []
    discarded: list[str] = []

    for item in items:
        if (
            _is_quantia_relevant_unidentified(
                item
            )
        ):
            accepted.append(
                item
            )
        else:
            discarded.append(
                item
            )

    return (
        accepted,
        discarded,
    )


# ============================================================
# CONFIRMACIONES
# ============================================================


def _build_quantia_confirmations(
    conflicts: list[
        ExtractionConflict
    ],
) -> list[RequiredConfirmation]:
    """
    Gemini NO gobierna las preguntas al usuario.

    En esta fase solo un conflicto explícito genera una
    confirmación.

    Posteriormente:

        grounding
        + geometría
        + reglas Quantia

    podrán generar otras confirmaciones.
    """

    confirmations: list[
        RequiredConfirmation
    ] = []

    for conflict in conflicts:
        confirmations.append(
            RequiredConfirmation(
                elemento=
                    conflict.descripcion,

                motivo=(
                    "Existe información documental "
                    "contradictoria que debe resolverse "
                    "antes de utilizar el dato."
                ),

                referencia=
                    None,
            )
        )

    return confirmations


# ============================================================
# VALIDACIÓN TRANSPORTE
# ============================================================


def _validate_transport_payload(
    payload: Any,
) -> dict[str, Any]:
    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "El resultado Gemini debe ser "
            "un objeto JSON."
        )

    required = {
        "resumen",
        "documento",
        "predio",
        "niveles",
        "informacion_constructiva",
        "conflictos",
        "datos_no_identificados",
        "confirmaciones_requeridas",
    }

    missing = (
        required
        - set(
            payload.keys()
        )
    )

    if missing:
        raise ValueError(
            "Resultado Gemini incompleto. "
            "Faltan campos: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )

    return payload


# ============================================================
# RECONCILIADOR PRINCIPAL
# ============================================================


def reconcile_gemini_transport(
    payload: dict[str, Any],
) -> QuantiaReconciliationResult:
    """
    Convierte la salida Gemini al primer contrato canónico
    de Quantia.

    Esta función realiza RECONCILIACIÓN SEMÁNTICA,
    no grounding geométrico.

    ==========================================================
    REGLAS
    ==========================================================

    Gemini puede promover:

        - título;
        - tipo de plano;
        - nombres de niveles;
        - espacios;
        - funciones;
        - relaciones;
        - puertas/ventanas observadas;
        - escaleras;
        - información constructiva;
        - conflictos.

    Gemini NO puede promover directamente:

        - ancho del predio;
        - fondo del predio;
        - área del predio;
        - ancho/largo/área de espacios;
        - dimensiones de puertas;
        - dimensiones de ventanas;
        - dimensiones de escaleras;
        - cotas como geometría gobernante;
        - muros;
        - polígonos;
        - bbox como geometría.

    Todas las métricas pasan a:

        metric_candidates

    y deberán ser verificadas posteriormente mediante:

        PyMuPDF
        + OCR
        + OpenCV
        + ejes
        + cadenas de cotas
        + grounding espacial
        + reglas Quantia.
    """

    data = (
        _validate_transport_payload(
            payload
        )
    )

    metric_candidates: list[
        MetricCandidate
    ] = []

    # ========================================================
    # NIVELES / ESPACIOS / VANOS / COTAS
    # ========================================================

    levels, stairs = (
        _build_levels(
            data,
            metric_candidates=
                metric_candidates,
        )
    )

    # ========================================================
    # INFORMACIÓN CONSTRUCTIVA
    # ========================================================

    constructive_info, unmapped = (
        _build_constructive_info(
            data
        )
    )

    # ========================================================
    # CONFLICTOS
    # ========================================================

    conflicts = (
        _build_conflicts(
            data
        )
    )

    # ========================================================
    # NO IDENTIFICADOS
    # ========================================================

    unidentified, discarded_unidentified = (
        _filter_unidentified(
            data
        )
    )

    # ========================================================
    # CONFIRMACIONES PROPUESTAS POR GEMINI
    # ========================================================

    model_confirmations = (
        data.get(
            "confirmaciones_requeridas"
        )
    )

    if not isinstance(
        model_confirmations,
        list,
    ):
        model_confirmations = []

    # ========================================================
    # SCHEMA CANÓNICO
    # ========================================================

    extraction = QuantiaExtractionSchema(
        schema_version=
            "1.0",

        resumen=
            _required_text(
                data.get(
                    "resumen"
                ),
                field_name=
                    "resumen",
            ),

        documento=
            _build_document(
                data
            ),

        predio=
            _build_plot(
                data,
                metric_candidates=
                    metric_candidates,
            ),

        niveles=
            levels,

        elementos_especiales=
            ExtractedSpecialElements(
                escaleras=
                    stairs,

                huecos_losa=
                    [],

                dobles_alturas=
                    [],

                patios=
                    [],
            ),

        informacion_constructiva=
            constructive_info,

        conflictos=
            conflicts,

        datos_no_identificados=
            unidentified,

        confirmaciones_requeridas=
            _build_quantia_confirmations(
                conflicts
            ),
    )

    return QuantiaReconciliationResult(
        extraction=
            extraction,

        metric_candidates=
            metric_candidates,

        discarded_model_confirmations=[
            item
            for item in model_confirmations
            if isinstance(
                item,
                dict,
            )
        ],

        discarded_unidentified=
            discarded_unidentified,

        unmapped_constructive_items=
            unmapped,
    )