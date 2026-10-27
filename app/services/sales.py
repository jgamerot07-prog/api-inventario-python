from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import MovementType, Sale, SaleItem, SaleStatus, User
from app.schemas.sale import SaleCreate
from app.services.inventory import apply_movement, lock_products


def create_sale(db: Session, data: SaleCreate, seller: User) -> Sale:
    """Registra una venta y descuenta el inventario en una sola transacción."""
    products = lock_products(db, (item.product_id for item in data.items))

    inactive = [p.name for p in products.values() if not p.active]
    if inactive:
        raise ConflictError(f"Productos no disponibles para la venta: {', '.join(inactive)}")

    sale = Sale(user_id=seller.id, customer_name=data.customer_name, total=0)
    db.add(sale)
    db.flush()  # para obtener el id de la venta

    total = 0
    for item in data.items:
        product = products[item.product_id]
        # El precio lo pone el servidor, nunca el cliente
        subtotal = product.price * item.quantity
        total += subtotal
        sale.items.append(
            SaleItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
                subtotal=subtotal,
            )
        )
        apply_movement(
            db,
            product,
            quantity=-item.quantity,
            type=MovementType.SALE,
            user_id=seller.id,
            sale_id=sale.id,
        )

    sale.total = total
    db.commit()
    db.refresh(sale)
    return sale


def cancel_sale(db: Session, sale_id: int, user: User) -> Sale:
    """Anula una venta y devuelve las unidades al inventario."""
    sale = db.scalars(select(Sale).where(Sale.id == sale_id).with_for_update(of=Sale)).unique().first()
    if sale is None:
        raise NotFoundError("La venta no existe")
    if sale.status == SaleStatus.CANCELLED:
        raise ConflictError("La venta ya estaba anulada")

    products = lock_products(db, (item.product_id for item in sale.items))
    for item in sale.items:
        apply_movement(
            db,
            products[item.product_id],
            quantity=item.quantity,
            type=MovementType.SALE_CANCELLED,
            user_id=user.id,
            sale_id=sale.id,
            reason=f"Anulación de la venta #{sale.id}",
        )

    sale.status = SaleStatus.CANCELLED
    db.commit()
    db.refresh(sale)
    return sale
