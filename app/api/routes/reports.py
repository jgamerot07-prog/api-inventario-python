from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.schemas.report import DailySales, Summary, TopProduct
from app.services import reports

router = APIRouter(prefix="/reports", tags=["Reportes"])


@router.get("/summary", response_model=Summary, summary="Resumen del negocio")
def get_summary(db: DbSession, _admin: AdminUser):
    """Ventas de hoy y del mes, productos con stock bajo y valor del inventario."""
    return reports.summary(db)


@router.get("/top-products", response_model=list[TopProduct], summary="Productos más vendidos")
def get_top_products(
    db: DbSession,
    _admin: AdminUser,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    return reports.top_products(db, days, limit)


@router.get("/sales-by-day", response_model=list[DailySales], summary="Ventas por día")
def get_sales_by_day(db: DbSession, _admin: AdminUser, days: Annotated[int, Query(ge=1, le=90)] = 7):
    return reports.sales_by_day(db, days)
