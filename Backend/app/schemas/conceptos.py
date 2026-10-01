from pydantic import BaseModel


class CatalogConceptItem(BaseModel):
    code: str
    technical_description: str
    official_description: str
    unit_code: str
    unit_symbol: str
    partida_code: str
    partida_name: str
    default_formula_code: str | None = None
    quantification_mode: str | None = None
    spec_code: str | None = None
    unit_price: float = 0
    source_name: str | None = None


class CatalogConceptListResponse(BaseModel):
    ok: bool
    module_key: str
    source_name: str
    count: int
    concepts: list[CatalogConceptItem]
