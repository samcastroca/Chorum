"""Engine y sesión de base de datos (Fase 2).

Sesiones **síncronas** de SQLModel (su modo natural), compatibles tanto con el SQLite de
desarrollo (``sqlite:///``) como con el Postgres de producción (``postgresql+psycopg://``).
Los endpoints son ``async`` y sólo hacen ``await`` sobre la ejecución del grafo; las
operaciones de DB son síncronas y breves.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlmodel import Session

from app.config import get_settings


def _make_engine() -> Engine:
    """Crea el engine desde ``Settings.database_url`` (invariante: única fuente de config)."""
    url = get_settings().database_url
    # SQLite abre la conexión en un thread distinto al del request bajo el threadpool de
    # Starlette; ``check_same_thread=False`` lo permite. Postgres no necesita connect_args.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = _make_engine()


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: entrega una ``Session`` y la cierra al terminar el request."""
    with Session(engine) as session:
        yield session
