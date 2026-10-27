import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.inventory import Product
from app.models.user import User


class SaleStatus(enum.StrEnum):
    COMPLETED = "completada"
    CANCELLED = "anulada"


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    customer_name: Mapped[str | None] = mapped_column(String(100))
    total: Mapped[int]
    status: Mapped[SaleStatus] = mapped_column(
        Enum(SaleStatus, name="sale_status", values_callable=lambda e: [m.value for m in e]),
        default=SaleStatus.COMPLETED,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    seller: Mapped[User] = relationship(lazy="joined")
    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def seller_name(self) -> str:
        return self.seller.name


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_sale_items_cantidad_positiva"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    # Se guarda el precio del momento: si luego cambia el precio, la venta no se altera
    unit_price: Mapped[int]
    subtotal: Mapped[int]

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(lazy="joined")

    @property
    def product_name(self) -> str:
        return self.product.name
