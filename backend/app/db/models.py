"""Modelos SQLModel de persistencia (Fase 2).

- ``Graph``: la ``GraphDefinition`` serializada más metadata de gestión, editable in-place.
- ``Execution``: historial de ejecuciones. Guarda el ``thread_id`` de LangGraph (para poder
  cruzar con los checkpoints en la Fase 4) y un snapshot inmutable de la definición que
  realmente corrió, de modo que editar el grafo después no altere lo que una ejecución pasada
  aparenta haber ejecutado.

Las API keys nunca se persisten acá (invariante 5 de CLAUDE.md): sólo se guarda la definición
del grafo, que referencia ``provider_id``, nunca una key en texto plano.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """Timestamp UTC timezone-aware para los defaults."""
    return datetime.now(UTC)


class Graph(SQLModel, table=True):
    """Grafo persistido: la ``GraphDefinition`` serializada más metadata de gestión."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    version: int = Field(default=1)
    definition: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Execution(SQLModel, table=True):
    """Ejecución de un grafo: resultado final más el ``thread_id`` de LangGraph.

    ``definition_snapshot`` congela la definición ejecutada para reproducibilidad: editar el
    grafo después no cambia lo que esta ejecución corrió.
    """

    id: int | None = Field(default=None, primary_key=True)
    graph_id: int = Field(foreign_key="graph.id", index=True)
    graph_version: int
    definition_snapshot: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    thread_id: str = Field(index=True)
    status: str
    final_state: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = Field(default=None)
