"""Test de un pipeline lineal ``start -> a -> b -> c -> end``."""

from __future__ import annotations

from typing import Any

from app.core import GraphDefinition, run_graph


async def test_linear_pipeline_accumulates_in_order(
    linear_graph: GraphDefinition, checkpointer: Any
) -> None:
    result = await run_graph(linear_graph, {}, checkpointer=checkpointer)

    assert result.status == "completed"
    assert result.next_nodes == ()
    assert result.thread_id  # se generó un thread_id
    assert result.final_state["log"] == [
        "[agent:a] A",
        "[agent:b] B",
        "[agent:c] C",
    ]


async def test_explicit_thread_id_is_respected(
    linear_graph: GraphDefinition, checkpointer: Any
) -> None:
    result = await run_graph(linear_graph, {}, checkpointer=checkpointer, thread_id="mi-thread")
    assert result.thread_id == "mi-thread"
