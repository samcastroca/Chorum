"""Dependencias compartidas de los routers de la API (Fase 2)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.db.session import get_session

__all__ = ["get_checkpointer", "get_session"]


def get_checkpointer(request: Request) -> Any:
    """Devuelve el checkpointer creado una sola vez en el ``lifespan`` (nunca por request).

    El checkpointer es un recurso de conexión de larga vida (invariante 6): se crea al arrancar
    la app y se comparte entre todos los requests, en vez de instanciarse por ejecución.
    """
    return request.app.state.checkpointer
