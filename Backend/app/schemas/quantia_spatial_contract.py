from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ============================================================
# TIPOS
# ============================================================


SpatialState = Literal[
    "DETECTADO",
    "INFERIDO",
    "NO_IDENTIFICADO",
    "CONFLICTO",
    "CANDIDATO",
    "PENDIENTE",
]

GeometryType = Literal[
    "poligono",
    "linea",
    "segmentos",
    "bbox",
    "punto",
]


# ============================================================
# GEOMETRÍA BÁSICA
# ============================================================


class SpatialPoint(BaseModel):
    x: float
    y: float


class SpatialBBox(BaseModel):
    xMin: float
    yMin: float
    xMax: float
    yMax: float


class RasterGeometry(BaseModel):
    """
    Geometría visual en píxeles.

    No debe utilizarse directamente para calcular:
        - areaM2
        - perimetroM
        - anchoM
        - largoM
    """

    sistemaCoordenadas: Literal["raster_px"] = "raster_px"

    tipo: GeometryType

    vertices: list[SpatialPoint] = Field(
        default_factory=list
    )

    bbox: SpatialBBox | None = None

    areaPx2: float | None = None

    perimetroPx: float | None = None


class MetricGeometry(BaseModel):
    """
    Geometría arquitectónica métrica.
    """

    sistemaCoordenadas: Literal["metric_m"] = "metric_m"

    tipo: GeometryType

    vertices: list[SpatialPoint] = Field(
        default_factory=list
    )

    areaM2: float | None = None

    perimetroM: float | None = None


class SpatialGeometry(BaseModel):
    """
    Los campos superiores representan únicamente
    geometría métrica compatible con 04.

    La geometría raster permanece separada.
    """

    tipo: str = "poligono"

    vertices: list[SpatialPoint] = Field(
        default_factory=list
    )

    areaM2: float | None = None

    perimetroM: float | None = None

    raster: RasterGeometry | None = None

    metrica: MetricGeometry | None = None


# ============================================================
# ORIGEN / EVIDENCIA
# ============================================================


class SpatialOrigin(BaseModel):
    documento: str | None = None

    pagina: int | None = None

    fuente: str

    referencia: str | None = None


class SpatialEvidence(BaseModel):
    fuente: str

    descripcion: str | None = None

    pagina: int | None = None

    textoOriginal: str | None = None

    bboxRaster: SpatialBBox | None = None

    confianza: float | None = None


# ============================================================
# PLANO BASE
# ============================================================


class SpatialBaseLayer(BaseModel):
    id: str

    nombre: str

    mimeType: str

    pagina: int

    anchoPx: int

    altoPx: int

    referencia: str | None = None

    visible: bool

    bloqueado: bool

    ocultable: bool

    bloqueable: bool


# ============================================================
# NIVEL
# ============================================================


class SpatialLevel(BaseModel):
    id: str

    nombre: str

    pagina: int | None = None

    estado: SpatialState

    confianza: float | None = None

    confirmed: bool = False

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )


# ============================================================
# EJES
# ============================================================


class SpatialAxis(BaseModel):
    id: str

    etiqueta: str

    orientacion: Literal[
        "horizontal",
        "vertical",
    ]

    coordenadaPx: float

    coordenadaM: float | None = None

    segmentosSoporte: list[str] = Field(
        default_factory=list
    )

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False


# ============================================================
# COTAS
# ============================================================


class SpatialDimension(BaseModel):
    id: str

    nivel: str | None = None

    valorM: float | None = None

    valorOriginal: str | None = None

    unidadOriginal: str | None = None

    direccion: Literal[
        "horizontal",
        "vertical",
        "desconocida",
    ]

    ejeInicioId: str | None = None

    ejeFinId: str | None = None

    ejeInicioEtiqueta: str | None = None

    ejeFinEtiqueta: str | None = None

    longitudPx: float | None = None

    geometria: SpatialGeometry | None = None

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False


# ============================================================
# OPENINGS
# ============================================================


class SpatialOpeningBase(BaseModel):
    id: str

    nivel: str | None = None

    muroId: str | None = None

    espacioId: str | None = None

    posicionM: float | None = None

    anchoM: float | None = None

    altoM: float | None = None

    anchoPx: float | None = None

    geometria: SpatialGeometry | None = None

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False


class SpatialDoor(SpatialOpeningBase):
    tipoElemento: Literal["puerta"] = "puerta"

    sentido: str | None = None


class SpatialWindow(SpatialOpeningBase):
    tipoElemento: Literal["ventana"] = "ventana"


# ============================================================
# MUROS
# ============================================================


class SpatialWallSide(BaseModel):
    faceId: str | None = None

    espacioId: str | None = None

    espacioNombre: str | None = None

    posicion: str | None = None

    confirmed: bool = False


class SpatialWallSegment(BaseModel):
    id: str

    rol: Literal[
        "wall_trace",
        "opening_bridge",
    ]

    geometria: SpatialGeometry

    estado: SpatialState

    confirmed: bool = False


class SpatialWall(BaseModel):
    id: str

    nivel: str | None = None

    grupoContinuidadId: str

    orientacion: Literal[
        "horizontal",
        "vertical",
    ]

    tipo: Literal[
        "exterior",
        "interior",
        "incierto",
    ] = "incierto"

    espesorM: float | None = None

    espesorFuente: str | None = None

    espesorEstado: SpatialState

    # Evidencia raster observada. Nunca debe interpretarse como
    # espesor constructivo ni convertirse a metros sin una
    # calibración arquitectónica explícita.
    espesorObservadoPx: float | None = None

    espesorObservadoFuente: str | None = None

    ladoA: SpatialWallSide | None = None

    ladoB: SpatialWallSide | None = None

    segmentos: list[SpatialWallSegment] = Field(
        default_factory=list
    )

    puertaIds: list[str] = Field(
        default_factory=list
    )

    ventanaIds: list[str] = Field(
        default_factory=list
    )

    espacioIds: list[str] = Field(
        default_factory=list
    )

    longitudRealPx: float | None = None

    longitudTopologicaPx: float | None = None

    geometria: SpatialGeometry | None = None

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False


# ============================================================
# ZONA SEMÁNTICA
# ============================================================


class SpatialSemanticZone(BaseModel):
    id: str

    espacioGeometricoId: str

    sourceSpaceId: str | None = None

    nivel: str | None = None

    nombre: str

    tipo: str | None = None

    geometria: SpatialGeometry

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False


# ============================================================
# ESPACIO
# ============================================================


class SpatialSpaceDimension(BaseModel):
    id: str

    eje: Literal[
        "x",
        "y",
    ]

    valorM: float

    ejeInicio: str | None = None

    ejeFin: str | None = None

    estado: SpatialState

    confirmed: bool = False


class SpatialSpace(BaseModel):
    id: str

    faceId: str | None = None

    nombre: str

    tipo: str

    nivel: str

    anchoM: float | None = None

    largoM: float | None = None

    areaM2: float | None = None

    geometria: SpatialGeometry

    dobleAltura: bool = False

    semanticMode: str | None = None

    zonaIds: list[str] = Field(
        default_factory=list
    )

    muroIds: list[str] = Field(
        default_factory=list
    )

    puertaIds: list[str] = Field(
        default_factory=list
    )

    ventanaIds: list[str] = Field(
        default_factory=list
    )

    dimensiones: list[SpatialSpaceDimension] = Field(
        default_factory=list
    )

    puerta: SpatialDoor | None = None

    ventana: SpatialWindow | None = None

    puertas: list[SpatialDoor] = Field(
        default_factory=list
    )

    ventanas: list[SpatialWindow] = Field(
        default_factory=list
    )

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianzaIA: float | None = None

    estado: SpatialState

    confirmed: bool = False


# ============================================================
# ESCALERA
# ============================================================


class SpatialStair(BaseModel):
    id: str

    nivel: str | None = None

    tipo: str | None = None

    sentido: str | None = None

    anchoM: float | None = None

    largoM: float | None = None

    geometria: SpatialGeometry | None = None

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    evidencia: list[SpatialEvidence] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False


# ============================================================
# METADATOS GEOMÉTRICOS
# ============================================================


class SpatialGeometryMetadata(BaseModel):
    anchoRasterPx: int

    altoRasterPx: int

    sistemaRaster: Literal["raster_px"] = "raster_px"

    sistemaMetrico: Literal["metric_m"] = "metric_m"

    geometriaMetricaCompleta: bool

    notas: list[str] = Field(
        default_factory=list
    )


# ============================================================
# CONTRATO 03.2 → 04
# ============================================================


class QuantiaSpatialContract(BaseModel):
    planoBase: SpatialBaseLayer

    niveles: list[SpatialLevel] = Field(
        default_factory=list
    )

    ejes: list[SpatialAxis] = Field(
        default_factory=list
    )

    muros: list[SpatialWall] = Field(
        default_factory=list
    )

    espacios: list[SpatialSpace] = Field(
        default_factory=list
    )

    zonasSemanticas: list[SpatialSemanticZone] = Field(
        default_factory=list
    )

    puertas: list[SpatialDoor] = Field(
        default_factory=list
    )

    ventanas: list[SpatialWindow] = Field(
        default_factory=list
    )

    escaleras: list[SpatialStair] = Field(
        default_factory=list
    )

    cotas: list[SpatialDimension] = Field(
        default_factory=list
    )

    geometria: SpatialGeometryMetadata

    origen: list[SpatialOrigin] = Field(
        default_factory=list
    )

    confianza: float | None = None

    estado: SpatialState

    confirmed: bool = False
