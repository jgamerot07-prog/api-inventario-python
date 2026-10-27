import os

# La configuración de pruebas se define antes de importar la app
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/inventario_test"
)

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_base  # noqa: E402

TABLES = "stock_movements, sale_items, sales, products, categories, users"


@pytest.fixture(scope="session", autouse=True)
def database():
    """Crea el esquema desde cero con las migraciones de Alembic (así también se prueban)."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    command.upgrade(Config("alembic.ini"), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_data():
    """Cada prueba arranca con los datos de ejemplo recién cargados."""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        seed_base(db)
        db.commit()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client, "admin@inventario.com", "Admin123*")


@pytest.fixture
def seller(client):
    return login(client, "vendedor@inventario.com", "Vendedor123*")


def product_by_sku(client: TestClient, headers: dict, sku: str) -> dict:
    res = client.get("/api/v1/products", params={"q": sku}, headers=headers)
    return res.json()["items"][0]
