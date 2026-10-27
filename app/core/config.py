from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno o del archivo .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "API de Inventario y Ventas"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/inventario"

    jwt_secret: str = "secreto-de-desarrollo-cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    # Costo de bcrypt: 12 en producción; las pruebas usan 4 para ir más rápido
    bcrypt_rounds: int = 12

    cors_origins: list[str] = ["http://localhost:5173"]
    # Zona horaria del negocio para agrupar las ventas por día
    timezone: str = "America/Bogota"

    admin_name: str = "Administrador"
    admin_email: str = "admin@inventario.com"
    admin_password: str = "Admin123*"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Servicios como Render entregan 'postgres://...'; SQLAlchemy necesita el driver explícito."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
