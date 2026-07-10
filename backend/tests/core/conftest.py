"""Fixtures del motor de orquestación (core).

Provee un ``checkpointer`` async con teardown garantizado (evita que el hilo no-daemon de
aiosqlite bloquee la salida del proceso), builders de grafos reutilizados por varios tests, y
un handler de incremento inyectable para ejercitar ciclos terminantes de forma determinista.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest

from app.core import (
    GraphDefinition,
    HandlerFactory,
    close_checkpointer,
    create_checkpointer,
)
from app.core.handlers import NodeHandler
from app.core.schema import Node, NodeType, ToolNode


@pytest.fixture
async def checkpointer() -> AsyncIterator[object]:
    """``AsyncSqliteSaver`` en memoria, cerrado en teardown."""
    saver = await create_checkpointer()
    try:
        yield saver
    finally:
        await close_checkpointer(saver)


def _make_increment(node: Node, _definition: GraphDefinition) -> NodeHandler:
    """Factory de handler que incrementa el canal ``output_key`` del nodo (para ciclos)."""
    assert isinstance(node, ToolNode)
    key = node.output_key

    async def handler(state: dict[str, object]) -> dict[str, object]:
        current = state.get(key, 0)
        assert isinstance(current, int)
        return {key: current + 1}

    return handler


@pytest.fixture
def increment_handlers() -> dict[NodeType, HandlerFactory]:
    """Override que hace del nodo ``tool`` un incrementador determinista."""
    return {"tool": _make_increment}


@pytest.fixture
def linear_graph() -> GraphDefinition:
    """``start -> a -> b -> c -> end``; cada agente agrega su salida al canal ``log``."""
    return GraphDefinition.model_validate(
        {
            "name": "linear",
            "state_schema": [{"name": "log", "type": "list", "reducer": "append"}],
            "nodes": [
                {"type": "start", "id": "s"},
                {"type": "agent", "id": "a", "system_prompt": "A", "output_key": "log"},
                {"type": "agent", "id": "b", "system_prompt": "B", "output_key": "log"},
                {"type": "agent", "id": "c", "system_prompt": "C", "output_key": "log"},
                {"type": "end", "id": "e"},
            ],
            "edges": [
                {"source": "s", "target": "a"},
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c"},
                {"source": "c", "target": "e"},
            ],
        }
    )


@pytest.fixture
def branching_graph() -> GraphDefinition:
    """Nodo ``condition`` que enruta según ``score``: >=10 -> ``hi``, si no -> ``lo`` (default)."""
    return GraphDefinition.model_validate(
        {
            "name": "branching",
            "state_schema": [
                {"name": "score", "type": "int"},
                {"name": "log", "type": "list", "reducer": "append"},
            ],
            "nodes": [
                {"type": "start", "id": "s"},
                {"type": "condition", "id": "c"},
                {"type": "agent", "id": "hi", "system_prompt": "HI", "output_key": "log"},
                {"type": "agent", "id": "lo", "system_prompt": "LO", "output_key": "log"},
                {"type": "end", "id": "e"},
            ],
            "edges": [
                {"source": "s", "target": "c"},
                {
                    "source": "c",
                    "target": "hi",
                    "condition": {"field": "score", "op": "gte", "value": 10},
                },
                {"source": "c", "target": "lo"},
                {"source": "hi", "target": "e"},
                {"source": "lo", "target": "e"},
            ],
        }
    )


@pytest.fixture
def cycle_graph() -> Callable[[int], GraphDefinition]:
    """Builder de un ciclo: ``inc`` incrementa ``count``; se sale cuando ``count >= 3``."""

    def build(max_iterations: int = 25) -> GraphDefinition:
        return GraphDefinition.model_validate(
            {
                "name": "cycle",
                "max_iterations": max_iterations,
                "state_schema": [{"name": "count", "type": "int"}],
                "nodes": [
                    {"type": "start", "id": "s"},
                    {"type": "tool", "id": "inc", "tool_name": "increment", "output_key": "count"},
                    {"type": "condition", "id": "chk"},
                    {"type": "end", "id": "e"},
                ],
                "edges": [
                    {"source": "s", "target": "inc"},
                    {"source": "inc", "target": "chk"},
                    {
                        "source": "chk",
                        "target": "e",
                        "condition": {"field": "count", "op": "gte", "value": 3},
                    },
                    {"source": "chk", "target": "inc"},
                ],
            }
        )

    return build
