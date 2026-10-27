"""
Carga datos de ejemplo: usuarios, categorías y productos de una tienda de barrio.

    python -m app.seed               # usuarios, categorías y productos
    python -m app.seed --with-sales  # además, ventas de ejemplo de los últimos 7 días
"""

import argparse
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Category, MovementType, Product, Role, Sale, SaleItem, User
from app.services.inventory import apply_movement

CATALOG = {
    "Bebidas": [
        ("BEB-001", "Gaseosa Cola 1.5 L", 4500, 3200, 48),
        ("BEB-002", "Agua sin gas 600 ml", 1800, 1000, 60),
        ("BEB-003", "Jugo de naranja 1 L", 5200, 3900, 4),
    ],
    "Lácteos": [
        ("LAC-001", "Leche entera 1 L", 4200, 3300, 36),
        ("LAC-002", "Queso campesino 500 g", 11500, 8600, 12),
        ("LAC-003", "Yogur de fresa 1 L", 6900, 5100, 3),
    ],
    "Granos": [
        ("GRA-001", "Arroz 1 kg", 4600, 3500, 80),
        ("GRA-002", "Lentejas 500 g", 3900, 2800, 25),
        ("GRA-003", "Fríjol rojo 500 g", 5800, 4300, 18),
    ],
    "Snacks": [
        ("SNK-001", "Papas fritas 110 g", 4300, 2900, 30),
        ("SNK-002", "Galletas de chocolate", 3200, 2100, 2),
    ],
    "Aseo": [
        ("ASE-001", "Jabón de baño x3", 7500, 5400, 20),
        ("ASE-002", "Detergente en polvo 1 kg", 12900, 9700, 9),
    ],
}


def _get_or_create_user(db: Session, name: str, email: str, password: str, role: Role) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
    return user


def seed_base(db: Session) -> User:
    settings = get_settings()
    admin = _get_or_create_user(
        db, settings.admin_name, settings.admin_email.lower(), settings.admin_password, Role.ADMIN
    )
    _get_or_create_user(db, "Valentina Ruiz", "vendedor@inventario.com", "Vendedor123*", Role.SELLER)

    if db.scalar(select(func.count(Product.id))):
        return admin

    for category_name, products in CATALOG.items():
        category = Category(name=category_name)
        db.add(category)
        db.flush()
        for sku, name, price, cost, stock in products:
            product = Product(sku=sku, name=name, category_id=category.id, price=price, cost=cost, stock=0)
            db.add(product)
            db.flush()
            apply_movement(
                db,
                product,
                quantity=stock,
                type=MovementType.PURCHASE,
                user_id=admin.id,
                reason="Stock inicial",
            )
    return admin


def seed_sales(db: Session, admin: User, days: int = 7) -> None:
    """Crea ventas repartidas en los últimos días para que los reportes tengan datos."""
    if db.scalar(select(func.count(Sale.id))):
        return
    rng = random.Random(42)
    seller = db.scalar(select(User).where(User.role == Role.SELLER)) or admin
    products = [p for p in db.scalars(select(Product)).unique() if p.stock > 10]
    now = datetime.now(UTC)

    for day in range(days - 1, -1, -1):
        for _ in range(rng.randint(3, 7)):
            created_at = now - timedelta(days=day, minutes=rng.randint(0, 600))
            sale = Sale(user_id=seller.id, total=0, created_at=created_at)
            db.add(sale)
            db.flush()
            for product in rng.sample(products, rng.randint(1, 3)):
                quantity = rng.randint(1, 3)
                if product.stock - quantity < product.min_stock:
                    continue  # no se deja el producto por debajo del mínimo
                sale.items.append(
                    SaleItem(
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=product.price,
                        subtotal=product.price * quantity,
                    )
                )
                sale.total += product.price * quantity
                movement = apply_movement(
                    db,
                    product,
                    quantity=-quantity,
                    type=MovementType.SALE,
                    user_id=seller.id,
                    sale_id=sale.id,
                )
                movement.created_at = created_at
            if not sale.items:
                db.delete(sale)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--with-sales", action="store_true", help="crear también ventas de ejemplo")
    args = parser.parse_args()

    with SessionLocal() as db:
        admin = seed_base(db)
        if args.with_sales:
            seed_sales(db, admin)
        db.commit()
    print("✔ Datos de ejemplo cargados")


if __name__ == "__main__":
    main()
