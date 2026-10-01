from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


QuoteStatus = Literal["draft", "reviewed", "completed"]


class CotizacionUpsertRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    quote_id: str | None = Field(default=None, alias="quote_id")
    user_email: EmailStr = Field(alias="user_email")
    status: QuoteStatus = "reviewed"
    modulo: str = "vivienda"
    subtipo: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict, alias="payload_json")
    resumen_json: dict[str, Any] = Field(default_factory=dict, alias="resumen_json")
    total: float = 0


class CotizacionItem(BaseModel):
    id: str
    user_id: str | None = None
    user_email: EmailStr
    status: QuoteStatus
    modulo: str
    subtipo: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    resumen_json: dict[str, Any] = Field(default_factory=dict)
    total: float = 0
    created_at: str | None = None
    updated_at: str | None = None


class CotizacionResponse(BaseModel):
    ok: bool = True
    quote: CotizacionItem


class CotizacionListResponse(BaseModel):
    ok: bool = True
    quotes: list[CotizacionItem]
