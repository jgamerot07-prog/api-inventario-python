from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Product, Sale, SaleItem, SaleStatus
from app.schemas.report import DailySales, Summary, TopProduct


def _local_day(column):
    """Convierte un timestamp a la fecha local del negocio (por defecto, Colombia)."""
    return cast(func.timezone(get_settings().timezone, column), Date)


def _today() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


def summary(db: Session) -> Summary:
    today = _today()
    completed = Sale.status == SaleStatus.COMPLETED
    sale_day = _local_day(Sale.created_at)

    sales_today, revenue_today = db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0)).where(
            completed, sale_day == today
        )
    ).one()
    revenue_month = db.scalar(
        select(func.coalesce(func.sum(Sale.total), 0)).where(completed, sale_day >= today.replace(day=1))
    )
    active, low, value_cost, value_price = db.execute(
        select(
            func.count(Product.id),
            func.count(Product.id).filter(Product.stock <= Product.min_stock),
            func.coalesce(func.sum(Product.stock * Product.cost), 0),
            func.coalesce(func.sum(Product.stock * Product.price), 0),
        ).where(Product.active)
    ).one()

    return Summary(
        sales_today=sales_today,
        revenue_today=revenue_today,
        revenue_month=revenue_month,
        active_products=active,
        low_stock_products=low,
        inventory_value_cost=value_cost,
        inventory_value_price=value_price,
    )


def top_products(db: Session, days: int, limit: int) -> list[TopProduct]:
    since = _today() - timedelta(days=days - 1)
    units = func.sum(SaleItem.quantity).label("units")
    rows = db.execute(
        select(Product.id, Product.sku, Product.name, units, func.sum(SaleItem.subtotal))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.status == SaleStatus.COMPLETED, _local_day(Sale.created_at) >= since)
        .group_by(Product.id)
        .order_by(units.desc(), Product.name)
        .limit(limit)
    ).all()
    return [TopProduct(product_id=r[0], sku=r[1], name=r[2], units_sold=r[3], revenue=r[4]) for r in rows]


def sales_by_day(db: Session, days: int) -> list[DailySales]:
    """Ventas de los últimos `days` días, incluidos los días sin ventas (en cero)."""
    today = _today()
    since = today - timedelta(days=days - 1)
    day = _local_day(Sale.created_at).label("day")
    rows = db.execute(
        select(day, func.count(Sale.id), func.sum(Sale.total))
        .where(Sale.status == SaleStatus.COMPLETED, day >= since)
        .group_by(day)
    ).all()
    by_day = {r[0]: (r[1], r[2]) for r in rows}
    result = []
    for offset in range(days):
        current = since + timedelta(days=offset)
        count, revenue = by_day.get(current, (0, 0))
        result.append(DailySales(day=current, sales=count, revenue=revenue))
    return result
