from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Category, MovementType, Product, StockMovement
from app.schemas.common import Page, error_responses
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
    StockMovementIn,
    StockMovementOut,
)
from app.services.inventory import apply_movement, lock_products

router = APIRouter(prefix="/products", tags=["Productos e inventario"], responses=error_responses(401))


def _get_product(db: DbSession, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("El producto no existe")
    return product


def _validate_refs(db: DbSession, sku: str, category_id: int, exclude_id: int | None = None) -> None:
    if db.get(Category, category_id) is None:
        raise NotFoundError("La categoría no existe")
    stmt = select(Product.id).where(Product.sku == sku)
    if exclude_id:
        stmt = stmt.where(Product.id != exclude_id)
    if db.scalar(stmt):
        raise ConflictError(f"Ya existe un producto con el SKU {sku}")


@router.get("", response_model=Page[ProductOut], summary="Buscar productos")
def list_products(
    db: DbSession,
    _user: CurrentUser,
    q: Annotated[str | None, Query(description="Busca por nombre o SKU")] = None,
    category_id: int | None = None,
    low_stock: Annotated[bool, Query(description="Solo productos con stock bajo")] = False,
    include_inactive: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    filters = []
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
    if category_id:
        filters.append(Product.category_id == category_id)
    if low_stock:
        filters.append(Product.stock <= Product.min_stock)
    if not include_inactive:
        filters.append(Product.active)

    total = db.scalar(select(func.count(Product.id)).where(*filters))
    items = db.scalars(
        select(Product).where(*filters).order_by(Product.name).limit(limit).offset(offset)
    ).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductOut, summary="Ver un producto")
def get_product(product_id: int, db: DbSession, _user: CurrentUser):
    return _get_product(db, product_id)


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto",
    responses=error_responses(403, 404, 409),
)
def create_product(data: ProductCreate, db: DbSession, admin: AdminUser):
    _validate_refs(db, data.sku, data.category_id)
    product = Product(**data.model_dump(exclude={"initial_stock"}), stock=0)
    db.add(product)
    db.flush()
    if data.initial_stock:
        apply_movement(
            db,
            product,
            quantity=data.initial_stock,
            type=MovementType.PURCHASE,
            user_id=admin.id,
            reason="Stock inicial",
        )
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut, summary="Editar producto")
def update_product(product_id: int, data: ProductUpdate, db: DbSession, _admin: AdminUser):
    """Edita los datos del producto. El stock solo cambia con movimientos de inventario."""
    product = _get_product(db, product_id)
    _validate_refs(db, data.sku, data.category_id, exclude_id=product_id)
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desactivar producto")
def deactivate_product(product_id: int, db: DbSession, _admin: AdminUser):
    """No se borra para conservar el historial de ventas: se marca como inactivo."""
    _get_product(db, product_id).active = False
    db.commit()


@router.post(
    "/{product_id}/movements",
    response_model=StockMovementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar entrada o ajuste de inventario",
    responses=error_responses(403, 404, 409),
)
def add_movement(product_id: int, data: StockMovementIn, db: DbSession, admin: AdminUser):
    product = lock_products(db, [product_id])[product_id]
    movement = apply_movement(
        db, product, quantity=data.quantity, type=data.type, user_id=admin.id, reason=data.reason
    )
    db.commit()
    return movement


@router.get(
    "/{product_id}/movements",
    response_model=list[StockMovementOut],
    summary="Historial de inventario de un producto",
)
def list_movements(
    product_id: int,
    db: DbSession,
    _user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    _get_product(db, product_id)
    return db.scalars(
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.id.desc())
        .limit(limit)
    ).all()
