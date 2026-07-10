"""Esquemas Pydantic de request/response de la API (Fase 2).

Separados de los modelos de DB (``app/db/models.py``): definen el contrato HTTP. El body de
crear/actualizar grafo no está acá porque se recibe como ``dict`` crudo y se valida contra el
schema del core (``GraphDefinition``) para poder devolver un 400 claro (ver ``routes/graphs``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphRead(BaseModel):
    """Grafo tal como lo devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: int
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExecuteRequest(BaseModel):
    """Body de ``POST /graphs/{id}/execute``: el estado inicial del grafo."""

    input: dict[str, Any] = Field(default_factory=dict)


class ExecutionRead(BaseModel):
    """Ejecución tal como la devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    graph_id: int
    graph_version: int
    thread_id: str
    status: str
    final_state: dict[str, Any]
    error: str | None
    created_at: datetime
    finished_at: datetime | None
