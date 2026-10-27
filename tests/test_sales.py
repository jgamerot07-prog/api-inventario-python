from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import login, product_by_sku


def sell(client, headers, *items, customer=None):
    payload = {"customer_name": customer, "items": [{"product_id": p, "quantity": q} for p, q in items]}
    return client.post("/api/v1/sales", json=payload, headers=headers)


def test_sale_discounts_stock_and_calculates_total(client, seller):
    rice = product_by_sku(client, seller, "GRA-001")  # $4.600, stock 80
    milk = product_by_sku(client, seller, "LAC-001")  # $4.200, stock 36

    res = sell(client, seller, (rice["id"], 3), (milk["id"], 2), customer="Doña Marta")
    assert res.status_code == 201
    sale = res.json()
    assert sale["total"] == 3 * 4600 + 2 * 4200
    assert sale["seller_name"] == "Valentina Ruiz"
    assert sale["status"] == "completada"

    assert product_by_sku(client, seller, "GRA-001")["stock"] == 77
    assert product_by_sku(client, seller, "LAC-001")["stock"] == 34


def test_price_comes_from_the_server(client, seller):
    rice = product_by_sku(client, seller, "GRA-001")
    payload = {"items": [{"product_id": rice["id"], "quantity": 1, "unit_price": 1}]}
    sale = client.post("/api/v1/sales", json=payload, headers=seller).json()
    assert sale["total"] == 4600


def test_sale_is_all_or_nothing(client, seller):
    rice = product_by_sku(client, seller, "GRA-001")
    cookies = product_by_sku(client, seller, "SNK-002")  # stock 2

    res = sell(client, seller, (rice["id"], 5), (cookies["id"], 3))
    assert res.status_code == 409
    assert "Galletas de chocolate" in res.json()["detail"]
    # El arroz no se descontó porque la venta completa se revirtió
    assert product_by_sku(client, seller, "GRA-001")["stock"] == 80


def test_sale_validations(client, seller, admin):
    assert sell(client, seller).status_code == 422  # sin productos
    assert sell(client, seller, (1, 1), (1, 2)).status_code == 422  # producto repetido
    assert sell(client, seller, (1, 0)).status_code == 422  # cantidad cero
    assert sell(client, seller, (999, 1)).status_code == 404  # no existe

    client.delete("/api/v1/products/1", headers=admin)
    assert sell(client, seller, (1, 1)).status_code == 409  # inactivo


def test_sellers_only_see_their_own_sales(client, admin, seller):
    sell(client, seller, (1, 1))
    sell(client, admin, (2, 1))

    assert client.get("/api/v1/sales", headers=seller).json()["total"] == 1
    assert client.get("/api/v1/sales", headers=admin).json()["total"] == 2
    admin_sale_id = client.get("/api/v1/sales", headers=admin).json()["items"][0]["id"]
    assert client.get(f"/api/v1/sales/{admin_sale_id}", headers=seller).status_code == 404


def test_cancel_sale_returns_stock(client, admin, seller):
    rice = product_by_sku(client, admin, "GRA-001")
    sale = sell(client, seller, (rice["id"], 10)).json()
    assert product_by_sku(client, admin, "GRA-001")["stock"] == 70

    assert client.post(f"/api/v1/sales/{sale['id']}/cancel", headers=seller).status_code == 403

    cancelled = client.post(f"/api/v1/sales/{sale['id']}/cancel", headers=admin)
    assert cancelled.json()["status"] == "anulada"
    assert product_by_sku(client, admin, "GRA-001")["stock"] == 80

    again = client.post(f"/api/v1/sales/{sale['id']}/cancel", headers=admin)
    assert again.status_code == 409

    types = [m["type"] for m in client.get(f"/api/v1/products/{rice['id']}/movements", headers=admin).json()]
    assert types[:2] == ["anulacion_venta", "venta"]


def test_filter_sales_by_status_and_dates(client, admin):
    sale = sell(client, admin, (1, 1)).json()
    sell(client, admin, (2, 1))
    client.post(f"/api/v1/sales/{sale['id']}/cancel", headers=admin)

    cancelled = client.get("/api/v1/sales", params={"status": "anulada"}, headers=admin).json()
    assert cancelled["total"] == 1

    future = client.get("/api/v1/sales", params={"date_from": "2099-01-01"}, headers=admin).json()
    assert future["total"] == 0

    bad_range = client.get(
        "/api/v1/sales", params={"date_from": "2026-02-01", "date_to": "2026-01-01"}, headers=admin
    )
    assert bad_range.status_code == 400


def test_two_simultaneous_sales_cannot_oversell(client, admin):
    """Dos cajeros venden las 2 últimas galletas al mismo tiempo: solo una venta puede pasar."""
    cookies = product_by_sku(client, admin, "SNK-002")  # stock 2

    def buy_two(_):
        with TestClient(app) as other_client:
            headers = login(other_client, "vendedor@inventario.com", "Vendedor123*")
            return sell(other_client, headers, (cookies["id"], 2)).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(buy_two, range(2)))

    assert statuses == [201, 409]
    assert product_by_sku(client, admin, "SNK-002")["stock"] == 0
