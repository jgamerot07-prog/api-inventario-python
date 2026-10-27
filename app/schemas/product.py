from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import MovementType


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductBase(BaseModel):
    sku: str = Field(min_length=3, max_length=30, pattern=r"^[A-Z0-9-]+$", examples=["BEB-001"])
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category_id: int
    price: int = Field(ge=0, description="Precio de venta en COP")
    cost: int = Field(ge=0, description="Costo de compra en COP")
    min_stock: int = Field(default=5, ge=0, description="Por debajo de este valor se alerta stock bajo")

    @model_validator(mode="after")
    def price_covers_cost(self):
        if self.price < self.cost:
            raise ValueError("El precio de venta no puede ser menor que el costo")
        return self


class ProductCreate(ProductBase):
    initial_stock: int = Field(default=0, ge=0)


class ProductUpdate(ProductBase):
    active: bool = True


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    category: CategoryOut
    price: int
    cost: int
    stock: int
    min_stock: int
    low_stock: bool
    active: bool


class StockMovementIn(BaseModel):
    type: MovementType = Field(description="'entrada' para compras o 'ajuste' para correcciones")
    quantity: int = Field(description="Positivo suma unidades; en un ajuste puede ser negativo")
    reason: str | None = Field(default=None, max_length=200, examples=["Compra a proveedor"])

    @model_validator(mode="after")
    def check_type(self):
        if self.type not in (MovementType.PURCHASE, MovementType.ADJUSTMENT):
            raise ValueError("Solo se pueden registrar movimientos de tipo 'entrada' o 'ajuste'")
        if self.quantity == 0:
            raise ValueError("La cantidad no puede ser cero")
        if self.type == MovementType.PURCHASE and self.quantity < 0:
            raise ValueError("Una entrada debe tener cantidad positiva")
        return self


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    type: MovementType
    quantity: int
    stock_after: int
    reason: str | None
    user_id: int
    sale_id: int | None
    created_at: datetime
