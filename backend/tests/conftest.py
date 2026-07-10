"""Fixtures compartidas para la suite de tests del backend."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.db.models  # noqa: F401 - registra las tablas en SQLModel.metadata
from app.api.deps import get_session
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente de test de FastAPI con una DB SQLite en memoria aislada por test.

    Sobrescribe la dependencia ``get_session`` para no tocar la DB real (``chorum.db``); usa un
    ``StaticPool`` para que la única conexión in-memory se comparta entre los threads del
    threadpool de Starlette. El ``lifespan`` crea el checkpointer en memoria (default
    ``checkpointer_db_path=None``), así no hace falta override adicional.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
