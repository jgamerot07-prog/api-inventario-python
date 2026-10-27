from datetime import date

from pydantic import BaseModel


class Summary(BaseModel):
    sales_today: int
    revenue_today: int
    revenue_month: int
    active_products: int
    low_stock_products: int
    inventory_value_cost: int
    inventory_value_price: int


class TopProduct(BaseModel):
    product_id: int
    sku: str
    name: str
    units_sold: int
    revenue: int


class DailySales(BaseModel):
    day: date
    sales: int
    revenue: int
