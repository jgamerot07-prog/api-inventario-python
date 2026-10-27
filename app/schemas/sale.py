from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import SaleStatus


class SaleItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=1000)


class SaleCreate(BaseModel):
    customer_name: str | None = Field(default=None, max_length=100)
    items: list[SaleItemIn] = Field(min_length=1, max_length=100)

    @field_validator("items")
    @classmethod
    def no_repeated_products(cls, items: list[SaleItemIn]) -> list[SaleItemIn]:
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Un producto aparece repetido; suma las cantidades en una sola línea")
        return items


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    unit_price: int
    subtotal: int


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str | None
    seller_name: str
    total: int
    status: SaleStatus
    created_at: datetime
    items: list[SaleItemOut]
