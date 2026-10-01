from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# ============================================================
# BASE
# ============================================================


class QuantiaExtractionBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ExtractionState(str, Enum):
    DETECTADO = "DETECTADO"
    INFERIDO = "INFERIDO"
    NO_IDENTIFICADO = "NO_IDENTIFICADO"
    CONFLICTO = "CONFLICTO"


class CoordinateSystem(str, Enum):
    METROS = "metros"
    PDF_POINTS = "pdf_points"
    PIXELES = "pixeles"
    PAGINA_NORMALIZADA = "pagina_normalizada"


# ============================================================
# EVIDENCIA
# ============================================================


class BoundingBox(QuantiaExtractionBase):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class EvidenceItem(QuantiaExtractionBase):
    descripcion: str

    pagina: int | None = Field(
        default=None,
        ge=1,
    )

    fuente: Literal[
        "vision",
        "pymupdf",
        "ocr",
        "documento",
        "usuario",
    ] = "vision"

    texto_original: str | None = None

    bbox: BoundingBox | None = None

    confianza: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


# ============================================================
# GEOMETRÍA OBSERVADA
# ============================================================


class Point2D(QuantiaExtractionBase):
    x: float
    y: float


class DetectedGeometry(QuantiaExtractionBase):
    """
    Geometría propuesta por una fuente documental o visual.

    IMPORTANTE:
    Solo una geometría cuyo sistema de coordenadas sea
    'metros' podrá convertirse directamente a la geometría
    constructiva de Diseño de la vivienda.

    Pixel, PDF points o coordenadas normalizadas se conservan
    como evidencia y deberán transformarse posteriormente.
    """

    tipo: Literal[
        "rectangulo",
        "poligono",
        "linea",
        "bbox",
    ] | None = None

    sistema_coordenadas: CoordinateSystem | None = None

    vertices: list[Point2D] = Field(
        default_factory=list
    )


# ============================================================
# UBICACIÓN Y RELACIONES
# ============================================================


class SpaceLocation(QuantiaExtractionBase):
    zona: str | None = None

    referencia: str | None = None

    norte_de: list[str] = Field(
        default_factory=list
    )

    sur_de: list[str] = Field(
        default_factory=list
    )

    este_de: list[str] = Field(
        default_factory=list
    )

    oeste_de: list[str] = Field(
        default_factory=list
    )


class SpaceRelations(QuantiaExtractionBase):
    comunica_con: list[str] = Field(
        default_factory=list
    )

    comparte_muro_con: list[str] = Field(
        default_factory=list
    )

    norte: str | None = None
    sur: str | None = None
    este: str | None = None
    oeste: str | None = None


# ============================================================
# PUERTAS
# ============================================================


class ExtractedDoor(QuantiaExtractionBase):
    id_propuesto: str | None = None

    hacia: str | None = None

    ancho_m: float | None = Field(
        default=None,
        gt=0,
    )

    alto_m: float | None = Field(
        default=None,
        gt=0,
    )

    ubicacion: str | None = None

    muro_referencia: str | None = None

    estado: ExtractionState = (
        ExtractionState.NO_IDENTIFICADO
    )

    confianza: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# VENTANAS
# ============================================================


class ExtractedWindow(QuantiaExtractionBase):
    id_propuesto: str | None = None

    ancho_m: float | None = Field(
        default=None,
        gt=0,
    )

    alto_m: float | None = Field(
        default=None,
        gt=0,
    )

    ubicacion: str | None = None

    muro_referencia: str | None = None

    estado: ExtractionState = (
        ExtractionState.NO_IDENTIFICADO
    )

    confianza: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# ESPACIOS
# ============================================================


class ExtractedSpace(QuantiaExtractionBase):
    id_propuesto: str

    nombre: str

    tipo: str | None = None

    ancho_m: float | None = Field(
        default=None,
        gt=0,
    )

    largo_m: float | None = Field(
        default=None,
        gt=0,
    )

    area_m2: float | None = Field(
        default=None,
        gt=0,
    )

    ubicacion: SpaceLocation = Field(
        default_factory=SpaceLocation
    )

    relaciones: SpaceRelations = Field(
        default_factory=SpaceRelations
    )

    geometria: DetectedGeometry | None = None

    puertas: list[ExtractedDoor] = Field(
        default_factory=list
    )

    ventanas: list[ExtractedWindow] = Field(
        default_factory=list
    )

    doble_altura: bool | None = None

    estado: ExtractionState

    confianza: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# MUROS
# ============================================================


class ExtractedWall(QuantiaExtractionBase):
    id_propuesto: str

    tipo: Literal[
        "perimetral",
        "interior",
        "compartido",
        "no_identificado",
    ] = "no_identificado"

    longitud_m: float | None = Field(
        default=None,
        gt=0,
    )

    espacios: list[str] = Field(
        default_factory=list
    )

    referencia: str | None = None

    geometria: DetectedGeometry | None = None

    estado: ExtractionState

    confianza: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# COTAS
# ============================================================


class ExtractedDimension(QuantiaExtractionBase):
    texto_original: str | None = None

    valor_original: float | None = None

    unidad_original: str | None = None

    valor_m: float | None = Field(
        default=None,
        gt=0,
    )

    referencia: str | None = None

    estado: ExtractionState

    confianza: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# NIVEL
# ============================================================


class ExtractedLevel(QuantiaExtractionBase):
    nombre: str

    elevacion_m: float | None = None

    espacios: list[ExtractedSpace] = Field(
        default_factory=list
    )

    muros: list[ExtractedWall] = Field(
        default_factory=list
    )

    cotas: list[ExtractedDimension] = Field(
        default_factory=list
    )


# ============================================================
# DOCUMENTO
# ============================================================


class ExtractedDocumentInfo(QuantiaExtractionBase):
    titulo: str | None = None

    tipo_plano: str | None = None

    escala: str | None = None

    orientacion: str | None = None

    paginas_analizadas: list[int] = Field(
        default_factory=list
    )


# ============================================================
# PREDIO
# ============================================================


class PlotBoundaries(QuantiaExtractionBase):
    norte: str | None = None
    sur: str | None = None
    este: str | None = None
    oeste: str | None = None


class ExtractedPlot(QuantiaExtractionBase):
    ancho_m: float | None = Field(
        default=None,
        gt=0,
    )

    fondo_m: float | None = Field(
        default=None,
        gt=0,
    )

    area_m2: float | None = Field(
        default=None,
        gt=0,
    )

    acceso_principal: str | None = None

    orientacion: str | None = None

    colindancias: PlotBoundaries = Field(
        default_factory=PlotBoundaries
    )

    estado: ExtractionState = (
        ExtractionState.NO_IDENTIFICADO
    )

    confianza: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# ESCALERAS
# ============================================================


class ExtractedStair(QuantiaExtractionBase):
    id_propuesto: str | None = None

    nivel: str | None = None

    tipo: str | None = None

    ancho_m: float | None = Field(
        default=None,
        gt=0,
    )

    largo_m: float | None = Field(
        default=None,
        gt=0,
    )

    sentido: str | None = None

    ubicacion: str | None = None

    comunica_con: list[str] = Field(
        default_factory=list
    )

    estado: ExtractionState

    confianza: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


# ============================================================
# ELEMENTOS ESPECIALES
# ============================================================


class ExtractedSpecialElement(
    QuantiaExtractionBase
):
    nombre: str | None = None

    nivel: str | None = None

    descripcion: str | None = None

    ubicacion: str | None = None

    geometria: DetectedGeometry | None = None

    estado: ExtractionState

    confianza: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


class ExtractedSpecialElements(
    QuantiaExtractionBase
):
    escaleras: list[ExtractedStair] = Field(
        default_factory=list
    )

    huecos_losa: list[
        ExtractedSpecialElement
    ] = Field(
        default_factory=list
    )

    dobles_alturas: list[
        ExtractedSpecialElement
    ] = Field(
        default_factory=list
    )

    patios: list[
        ExtractedSpecialElement
    ] = Field(
        default_factory=list
    )


# ============================================================
# INFORMACIÓN CONSTRUCTIVA
# ============================================================


class ConstructiveValue(QuantiaExtractionBase):
    valor: str | None = None

    estado: ExtractionState = (
        ExtractionState.NO_IDENTIFICADO
    )

    confianza: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )


class ExtractedConstructiveInfo(
    QuantiaExtractionBase
):
    sistema_constructivo: (
        ConstructiveValue | None
    ) = None

    sistema_estructural: (
        ConstructiveValue | None
    ) = None

    tipo_cimentacion: (
        ConstructiveValue | None
    ) = None

    tipo_losa: (
        ConstructiveValue | None
    ) = None

    alturas: list[
        ExtractedDimension
    ] = Field(
        default_factory=list
    )

    materiales: list[
        ConstructiveValue
    ] = Field(
        default_factory=list
    )


# ============================================================
# CONFLICTOS
# ============================================================


class ExtractionConflict(
    QuantiaExtractionBase
):
    codigo: str | None = None

    descripcion: str

    elementos_relacionados: list[str] = Field(
        default_factory=list
    )

    evidencia: list[EvidenceItem] = Field(
        default_factory=list
    )

    requiere_confirmacion: bool = True


# ============================================================
# CONFIRMACIONES
# ============================================================


class RequiredConfirmation(
    QuantiaExtractionBase
):
    elemento: str

    motivo: str

    referencia: str | None = None


# ============================================================
# RESULTADO PRINCIPAL
# ============================================================


class QuantiaExtractionSchema(
    QuantiaExtractionBase
):
    """
    Contrato canónico de salida de 03.2.

    Gemini propone.
    Quantia valida.
    El usuario confirma posteriormente en Diseño.
    """

    schema_version: str = "1.0"

    resumen: str

    documento: ExtractedDocumentInfo

    predio: ExtractedPlot

    niveles: list[ExtractedLevel] = Field(
        default_factory=list
    )

    elementos_especiales: (
        ExtractedSpecialElements
    ) = Field(
        default_factory=ExtractedSpecialElements
    )

    informacion_constructiva: (
        ExtractedConstructiveInfo
    ) = Field(
        default_factory=ExtractedConstructiveInfo
    )

    conflictos: list[
        ExtractionConflict
    ] = Field(
        default_factory=list
    )

    datos_no_identificados: list[str] = Field(
        default_factory=list
    )

    confirmaciones_requeridas: list[
        RequiredConfirmation
    ] = Field(
        default_factory=list
    )


# ============================================================
# HELPERS
# ============================================================


def get_quantia_extraction_json_schema() -> dict:
    """
    JSON Schema que se enviará al proveedor Gemini
    para solicitar Structured Output.
    """

    return QuantiaExtractionSchema.model_json_schema()


def validate_quantia_extraction(
    payload: dict,
) -> QuantiaExtractionSchema:
    """
    Segunda barrera de validación.

    Incluso si Gemini afirma haber respetado el schema,
    Quantia vuelve a validarlo localmente con Pydantic.
    """

    return QuantiaExtractionSchema.model_validate(
        payload
    )