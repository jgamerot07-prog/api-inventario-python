from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import MovementType, Product, StockMovement


def lock_products(db: Session, product_ids: Iterable[int]) -> dict[int, Product]:
    """
    Bloquea las filas de los productos hasta el fin de la transacción (SELECT ... FOR UPDATE).

    Si dos ventas intentan llevarse la última unidad al mismo tiempo, la segunda espera
    a que termine la primera y luego ve el stock ya actualizado. Se bloquean en orden
    de id para que dos ventas nunca se esperen mutuamente (deadlock).
    """
    ids = sorted(set(product_ids))
    stmt = select(Product).where(Product.id.in_(ids)).order_by(Product.id).with_for_update(of=Product)
    products = {p.id: p for p in db.scalars(stmt).unique()}
    missing = [pid for pid in ids if pid not in products]
    if missing:
        raise NotFoundError(f"No existen los productos: {', '.join(map(str, missing))}")
    return products


def apply_movement(
    db: Session,
    product: Product,
    *,
    quantity: int,
    type: MovementType,
    user_id: int,
    reason: str | None = None,
    sale_id: int | None = None,
) -> StockMovement:
    """Cambia el stock de un producto ya bloqueado y deja el registro en el historial."""
    new_stock = product.stock + quantity
    if new_stock < 0:
        raise ConflictError(
            f"Stock insuficiente para '{product.name}': hay {product.stock} y se necesitan {-quantity}"
        )
    product.stock = new_stock
    movement = StockMovement(
        product_id=product.id,
        type=type,
        quantity=quantity,
        stock_after=new_stock,
        reason=reason,
        user_id=user_id,
        sale_id=sale_id,
    )
    db.add(movement)
    return movement
