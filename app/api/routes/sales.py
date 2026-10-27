from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models import Role, Sale, SaleStatus
from app.schemas.common import Page, error_responses
from app.schemas.sale import SaleCreate, SaleOut
from app.services import sales as sales_service

router = APIRouter(prefix="/sales", tags=["Ventas"], responses=error_responses(401))


def _start_of(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=ZoneInfo(get_settings().timezone))


@router.post(
    "",
    response_model=SaleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar venta",
    responses=error_responses(404, 409),
)
def create_sale(data: SaleCreate, db: DbSession, user: CurrentUser):
    """
    Registra la venta y descuenta el inventario. Si algún producto no tiene stock
    suficiente, no se guarda nada y se responde 409.
    """
    return sales_service.create_sale(db, data, user)


@router.get("", response_model=Page[SaleOut], summary="Listar ventas")
def list_sales(
    db: DbSession,
    user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: Annotated[SaleStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Los vendedores solo ven sus propias ventas; el administrador ve todas."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_from no puede ser posterior a date_to")

    filters = []
    if user.role != Role.ADMIN:
        filters.append(Sale.user_id == user.id)
    if date_from:
        filters.append(Sale.created_at >= _start_of(date_from))
    if date_to:
        filters.append(Sale.created_at < _start_of(date_to + timedelta(days=1)))
    if status_filter:
        filters.append(Sale.status == status_filter)

    total = db.scalar(select(func.count(Sale.id)).where(*filters))
    items = (
        db.scalars(
            select(Sale)
            .where(*filters)
            .order_by(Sale.created_at.desc(), Sale.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{sale_id}", response_model=SaleOut, summary="Ver una venta")
def get_sale(sale_id: int, db: DbSession, user: CurrentUser):
    sale = db.get(Sale, sale_id)
    if sale is None or (user.role != Role.ADMIN and sale.user_id != user.id):
        raise NotFoundError("La venta no existe")
    return sale


@router.post(
    "/{sale_id}/cancel",
    response_model=SaleOut,
    summary="Anular venta",
    responses=error_responses(403, 404, 409),
)
def cancel_sale(sale_id: int, db: DbSession, admin: AdminUser):
    """Anula la venta y devuelve las unidades al inventario."""
    return sales_service.cancel_sale(db, sale_id, admin)
