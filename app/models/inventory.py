import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        # La base de datos nunca permite stock negativo, aunque falle el código
        CheckConstraint("stock >= 0", name="ck_products_stock_no_negativo"),
        CheckConstraint("price >= 0 AND cost >= 0", name="ck_products_precios_positivos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    price: Mapped[int]  # precio de venta en pesos colombianos
    cost: Mapped[int]  # costo de compra en pesos colombianos
    stock: Mapped[int] = mapped_column(default=0)
    min_stock: Mapped[int] = mapped_column(default=5)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    category: Mapped[Category] = relationship(back_populates="products", lazy="joined")

    @property
    def low_stock(self) -> bool:
        return self.stock <= self.min_stock


class MovementType(enum.StrEnum):
    PURCHASE = "entrada"
    ADJUSTMENT = "ajuste"
    SALE = "venta"
    SALE_CANCELLED = "anulacion_venta"


class StockMovement(Base):
    """Historial de cada cambio de inventario, para auditoría."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type", values_callable=lambda e: [m.value for m in e])
    )
    quantity: Mapped[int]  # positivo = entra mercancía, negativo = sale
    stock_after: Mapped[int]
    reason: Mapped[str | None] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sales.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
