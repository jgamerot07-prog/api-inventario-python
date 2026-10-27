from tests.conftest import product_by_sku

NEW_PRODUCT = {
    "sku": "BEB-099",
    "name": "Té helado 500 ml",
    "category_id": 1,
    "price": 3500,
    "cost": 2200,
    "min_stock": 5,
    "initial_stock": 20,
}


def test_list_is_paginated(client, seller):
    res = client.get("/api/v1/products", params={"limit": 5}, headers=seller).json()
    assert res["total"] == 13
    assert len(res["items"]) == 5


def test_search_by_name_or_sku(client, seller):
    by_name = client.get("/api/v1/products", params={"q": "arroz"}, headers=seller).json()
    by_sku = client.get("/api/v1/products", params={"q": "gra-001"}, headers=seller).json()
    assert by_name["items"][0]["sku"] == by_sku["items"][0]["sku"] == "GRA-001"


def test_low_stock_filter(client, seller):
    items = client.get("/api/v1/products", params={"low_stock": True}, headers=seller).json()["items"]
    assert {p["sku"] for p in items} == {"BEB-003", "LAC-003", "SNK-002"}
    assert all(p["low_stock"] for p in items)


def test_create_product_registers_initial_stock(client, admin):
    res = client.post("/api/v1/products", json=NEW_PRODUCT, headers=admin)
    assert res.status_code == 201
    product = res.json()
    assert product["stock"] == 20

    movements = client.get(f"/api/v1/products/{product['id']}/movements", headers=admin).json()
    assert movements[0]["type"] == "entrada"
    assert movements[0]["reason"] == "Stock inicial"


def test_product_validations(client, admin):
    duplicated = client.post("/api/v1/products", json={**NEW_PRODUCT, "sku": "BEB-001"}, headers=admin)
    assert duplicated.status_code == 409

    below_cost = client.post("/api/v1/products", json={**NEW_PRODUCT, "price": 1000}, headers=admin)
    assert below_cost.status_code == 422

    bad_sku = client.post("/api/v1/products", json={**NEW_PRODUCT, "sku": "té helado"}, headers=admin)
    assert bad_sku.status_code == 422

    no_category = client.post("/api/v1/products", json={**NEW_PRODUCT, "category_id": 999}, headers=admin)
    assert no_category.status_code == 404


def test_update_does_not_change_stock(client, admin):
    product = product_by_sku(client, admin, "GRA-001")
    data = {
        "sku": "GRA-001",
        "name": "Arroz premium 1 kg",
        "category_id": product["category"]["id"],
        "price": 5000,
        "cost": 3500,
        "min_stock": 10,
        "stock": 9999,  # se ignora: el stock solo cambia con movimientos
    }
    updated = client.put(f"/api/v1/products/{product['id']}", json=data, headers=admin).json()
    assert updated["name"] == "Arroz premium 1 kg"
    assert updated["stock"] == product["stock"]


def test_deactivated_product_is_hidden(client, admin):
    product = product_by_sku(client, admin, "SNK-001")
    assert client.delete(f"/api/v1/products/{product['id']}", headers=admin).status_code == 204
    assert client.get("/api/v1/products", params={"q": "SNK-001"}, headers=admin).json()["total"] == 0
    with_inactive = client.get(
        "/api/v1/products", params={"q": "SNK-001", "include_inactive": True}, headers=admin
    ).json()
    assert with_inactive["items"][0]["active"] is False


def test_stock_entries_and_adjustments(client, admin):
    product = product_by_sku(client, admin, "BEB-003")  # stock 4
    url = f"/api/v1/products/{product['id']}/movements"

    entry = client.post(url, json={"type": "entrada", "quantity": 10, "reason": "Compra"}, headers=admin)
    assert entry.json()["stock_after"] == 14

    adjustment = client.post(
        url, json={"type": "ajuste", "quantity": -2, "reason": "Vencidos"}, headers=admin
    )
    assert adjustment.json()["stock_after"] == 12


def test_stock_can_never_be_negative(client, admin):
    product = product_by_sku(client, admin, "SNK-002")  # stock 2
    url = f"/api/v1/products/{product['id']}/movements"
    res = client.post(url, json={"type": "ajuste", "quantity": -5}, headers=admin)
    assert res.status_code == 409
    assert "Stock insuficiente" in res.json()["detail"]


def test_invalid_movements(client, admin):
    url = "/api/v1/products/1/movements"
    assert client.post(url, json={"type": "venta", "quantity": 1}, headers=admin).status_code == 422
    assert client.post(url, json={"type": "entrada", "quantity": -1}, headers=admin).status_code == 422
    assert client.post(url, json={"type": "ajuste", "quantity": 0}, headers=admin).status_code == 422


def test_seller_cannot_change_inventory(client, seller):
    res = client.post("/api/v1/products/1/movements", json={"type": "entrada", "quantity": 5}, headers=seller)
    assert res.status_code == 403


def test_categories(client, admin):
    created = client.post("/api/v1/categories", json={"name": "Panadería"}, headers=admin)
    assert created.status_code == 201
    assert client.post("/api/v1/categories", json={"name": "panadería"}, headers=admin).status_code == 409
    # Una categoría con productos no se puede borrar; una vacía sí
    assert client.delete("/api/v1/categories/1", headers=admin).status_code == 409
    assert client.delete(f"/api/v1/categories/{created.json()['id']}", headers=admin).status_code == 204
