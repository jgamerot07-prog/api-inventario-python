from fastapi import APIRouter, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Category, Product
from app.schemas.product import CategoryIn, CategoryOut

router = APIRouter(prefix="/categories", tags=["Categorías"])


def _ensure_unique(db: DbSession, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Category.id).where(func.lower(Category.name) == name.lower())
    if exclude_id:
        stmt = stmt.where(Category.id != exclude_id)
    if db.scalar(stmt):
        raise ConflictError("Ya existe una categoría con ese nombre")


@router.get("", response_model=list[CategoryOut], summary="Listar categorías")
def list_categories(db: DbSession, _user: CurrentUser):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED, summary="Crear categoría")
def create_category(data: CategoryIn, db: DbSession, _admin: AdminUser):
    _ensure_unique(db, data.name)
    category = Category(name=data.name)
    db.add(category)
    db.commit()
    return category


@router.put("/{category_id}", response_model=CategoryOut, summary="Renombrar categoría")
def update_category(category_id: int, data: CategoryIn, db: DbSession, _admin: AdminUser):
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("La categoría no existe")
    _ensure_unique(db, data.name, exclude_id=category_id)
    category.name = data.name
    db.commit()
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar categoría")
def delete_category(category_id: int, db: DbSession, _admin: AdminUser):
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("La categoría no existe")
    if db.scalar(select(func.count(Product.id)).where(Product.category_id == category_id)):
        raise ConflictError("No se puede eliminar: la categoría tiene productos")
    db.delete(category)
    db.commit()
