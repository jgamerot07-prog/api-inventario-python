from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    # Todas las fechas se guardan con zona horaria (TIMESTAMPTZ) para que los reportes
    # por día no se desfasen sin importar dónde esté el servidor
    type_annotation_map = {datetime: DateTime(timezone=True)}


def get_db() -> Iterator[Session]:
    """Abre una sesión por petición y la cierra al terminar."""
    with SessionLocal() as session:
        yield session
