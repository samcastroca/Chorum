"""Checkpointer de LangGraph y recuperación de checkpoints intermedios.

El checkpointing **no es opcional** (invariante 6 de CLAUDE.md): cada paso de ejecución queda
persistido bajo el ``thread_id`` de la ejecución. Sobre esa persistencia se construye el
time-travel debugging (Fase 4). Este módulo expone:

- ``create_checkpointer`` / ``close_checkpointer``: fábrica del ``AsyncSqliteSaver`` de
  desarrollo, creado sobre una conexión ``aiosqlite`` explícita (así el saver vive tanto como
  se lo necesite, en vez de depender del context manager de ``from_conn_string``).
- ``list_checkpoints`` / ``get_state_at``: recuperación tipada del historial y del estado
  exacto en un checkpoint concreto de una ejecución ya terminada.

La bifurcación (reanudar desde un checkpoint como nueva ejecución) es de la Fase 4 y se apoya
en ``aupdate_state`` + ``ainvoke`` sobre el config del checkpoint elegido; el diseño de aquí
ya lo habilita sin sobrescribir la ejecución original (invariante 8).
"""

from __future__ import annotations

from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

# La memoria compartida ``file::memory:?cache=shared`` mantiene un único checkpointer por
# proceso; un path de archivo persiste entre procesos. Ambos sirven para recuperar el estado
# mientras la conexión siga viva.
IN_MEMORY = ":memory:"


class CheckpointRef(BaseModel):
    """Resumen de un checkpoint para listados (base de ``GET /executions/{id}/checkpoints``)."""

    checkpoint_id: str
    next_nodes: tuple[str, ...]
    created_at: str | None
    source_step: int | None
    state_summary: dict[str, Any]


class CheckpointState(BaseModel):
    """Estado completo en un checkpoint concreto (base de ``GET .../checkpoints/{id}``)."""

    checkpoint_id: str
    values: dict[str, Any]
    next_nodes: tuple[str, ...]
    metadata: dict[str, Any]


async def create_checkpointer(db_path: str | None = None) -> AsyncSqliteSaver:
    """Crea un ``AsyncSqliteSaver`` listo para usar (tablas ya inicializadas).

    ``db_path=None`` usa una base SQLite en memoria (aislada a esta conexión); pasar una ruta
    de archivo persiste los checkpoints en disco. La conexión queda accesible como
    ``saver.conn`` y debe cerrarse con ``close_checkpointer`` al terminar.
    """
    conn = await aiosqlite.connect(db_path or IN_MEMORY)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    return saver


async def close_checkpointer(saver: AsyncSqliteSaver) -> None:
    """Cierra la conexión SQLite subyacente del checkpointer."""
    await saver.conn.close()


def _thread_config(thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def _checkpoint_id_of(snapshot: Any) -> str | None:
    checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
    return checkpoint_id if isinstance(checkpoint_id, str) else None


async def list_checkpoints(compiled: Any, thread_id: str) -> list[CheckpointRef]:
    """Lista los checkpoints de ``thread_id``, del más nuevo al más viejo.

    Envuelve ``compiled.aget_state_history`` en vistas tipadas. Cada entrada trae el
    ``checkpoint_id`` con el que se puede recuperar el estado exacto de ese paso.
    """
    refs: list[CheckpointRef] = []
    async for snapshot in compiled.aget_state_history(_thread_config(thread_id)):
        checkpoint_id = _checkpoint_id_of(snapshot)
        if checkpoint_id is None:
            continue
        metadata = snapshot.metadata or {}
        refs.append(
            CheckpointRef(
                checkpoint_id=checkpoint_id,
                next_nodes=tuple(snapshot.next),
                created_at=snapshot.created_at,
                source_step=metadata.get("step"),
                state_summary=dict(snapshot.values),
            )
        )
    return refs


async def get_state_at(compiled: Any, thread_id: str, checkpoint_id: str) -> CheckpointState:
    """Recupera el estado exacto de ``thread_id`` en el checkpoint ``checkpoint_id``.

    Pasar ``checkpoint_id`` en el config es lo que permite "viajar" a un paso intermedio de una
    ejecución ya terminada y leer el estado tal como estaba ahí (no solo el estado final).
    """
    snapshot = await compiled.aget_state(_thread_config(thread_id, checkpoint_id))
    metadata = snapshot.metadata or {}
    return CheckpointState(
        checkpoint_id=checkpoint_id,
        values=dict(snapshot.values),
        next_nodes=tuple(snapshot.next),
        metadata=dict(metadata),
    )
