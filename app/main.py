from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.routes import auth, categories, products, reports, sales, users
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.db import engine

DESCRIPTION = """
API REST para gestionar el **inventario y las ventas** de una tienda.

* **Productos y categorías** con búsqueda, filtros y paginación.
* **Inventario** con historial de cada entrada, ajuste y venta.
* **Ventas** que descuentan el stock en una transacción y nunca dejan el inventario en negativo.
* **Reportes**: resumen del negocio, productos más vendidos y ventas por día.
* **Roles**: el administrador gestiona todo; el vendedor registra y consulta sus ventas.

Para probar las rutas protegidas, pulsa **Authorize** e ingresa con `admin@inventario.com` / `Admin123*`.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version="1.0.0",
        contact={"name": "Juan David Gamero Tatis", "url": "https://github.com/jgamerot07-prog"},
        license_info={"name": "MIT"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_request, _exc: IntegrityError):
        # Última línea de defensa: una regla de la base de datos (stock negativo, duplicados...)
        return JSONResponse(status_code=409, content={"detail": "La operación viola una regla de los datos"})

    for router in (
        auth.router,
        users.router,
        categories.router,
        products.router,
        sales.router,
        reports.router,
    ):
        app.include_router(router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/docs")

    @app.get("/health", tags=["Estado"], summary="Estado del servicio")
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
