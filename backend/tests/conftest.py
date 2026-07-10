"""Fixtures compartidas para la suite de tests del backend."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente de test de FastAPI contra la app real."""
    with TestClient(app) as test_client:
        yield test_client
