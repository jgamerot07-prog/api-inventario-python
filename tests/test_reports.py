from tests.conftest import product_by_sku


def test_summary(client, admin):
    rice = product_by_sku(client, admin, "GRA-001")
    client.post("/api/v1/sales", json={"items": [{"product_id": rice["id"], "quantity": 2}]}, headers=admin)

    summary = client.get("/api/v1/reports/summary", headers=admin).json()
    assert summary["sales_today"] == 1
    assert summary["revenue_today"] == 9200
    assert summary["revenue_month"] == 9200
    assert summary["active_products"] == 13
    assert summary["low_stock_products"] == 3
    assert summary["inventory_value_price"] > summary["inventory_value_cost"] > 0


def test_cancelled_sales_are_not_counted(client, admin):
    sale = client.post(
        "/api/v1/sales", json={"items": [{"product_id": 1, "quantity": 1}]}, headers=admin
    ).json()
    client.post(f"/api/v1/sales/{sale['id']}/cancel", headers=admin)
    assert client.get("/api/v1/reports/summary", headers=admin).json()["sales_today"] == 0


def test_top_products(client, admin):
    rice = product_by_sku(client, admin, "GRA-001")
    water = product_by_sku(client, admin, "BEB-002")
    client.post(
        "/api/v1/sales",
        json={
            "items": [{"product_id": rice["id"], "quantity": 1}, {"product_id": water["id"], "quantity": 5}]
        },
        headers=admin,
    )
    top = client.get("/api/v1/reports/top-products", headers=admin).json()
    assert [p["sku"] for p in top] == ["BEB-002", "GRA-001"]
    assert top[0]["units_sold"] == 5
    assert top[0]["revenue"] == 9000


def test_sales_by_day_includes_days_without_sales(client, admin):
    client.post("/api/v1/sales", json={"items": [{"product_id": 1, "quantity": 1}]}, headers=admin)
    days = client.get("/api/v1/reports/sales-by-day", params={"days": 7}, headers=admin).json()
    assert len(days) == 7
    assert days[-1]["sales"] == 1
    assert all(d["sales"] == 0 for d in days[:-1])
