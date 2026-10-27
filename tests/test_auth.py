def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_returns_token_and_user(client):
    res = client.post(
        "/api/v1/auth/login", data={"username": "ADMIN@inventario.com", "password": "Admin123*"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"


def test_wrong_password_is_rejected(client):
    res = client.post("/api/v1/auth/login", data={"username": "admin@inventario.com", "password": "otra"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Correo o contraseña incorrectos"


def test_protected_routes_need_a_valid_token(client):
    assert client.get("/api/v1/products").status_code == 401
    res = client.get("/api/v1/products", headers={"Authorization": "Bearer token-falso"})
    assert res.status_code == 401


def test_me(client, seller):
    res = client.get("/api/v1/auth/me", headers=seller)
    assert res.json()["email"] == "vendedor@inventario.com"


def test_seller_cannot_use_admin_routes(client, seller):
    assert client.get("/api/v1/users", headers=seller).status_code == 403
    assert client.get("/api/v1/reports/summary", headers=seller).status_code == 403


def test_admin_creates_users_without_duplicates(client, admin):
    data = {
        "name": "Pedro Gómez",
        "email": "pedro@inventario.com",
        "password": "Clave1234",
        "role": "vendedor",
    }
    assert client.post("/api/v1/users", json=data, headers=admin).status_code == 201
    assert client.post("/api/v1/users", json=data, headers=admin).status_code == 409


def test_database_url_is_normalized():
    from app.core.config import Settings

    settings = Settings(database_url="postgres://u:p@host:5432/db")
    assert settings.database_url == "postgresql+psycopg://u:p@host:5432/db"
