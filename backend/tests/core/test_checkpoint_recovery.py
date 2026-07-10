"""Test clave de la Fase 1: recuperar el estado exacto en checkpoints intermedios.

Es el criterio de aceptación que habilita el time-travel debugging (Fase 4): dado el
``thread_id`` de una ejecución ya terminada, poder reconstruir el estado tal como estaba en
cualquiera de sus pasos, no solo el final.
"""

from __future__ import annotations

from typing import Any

from app.core import (
    GraphDefinition,
    get_state_at,
    list_checkpoints,
    run_graph,
)


async def test_recover_intermediate_state_after_completion(
    linear_graph: GraphDefinition, checkpointer: Any
) -> None:
    result = await run_graph(linear_graph, {}, checkpointer=checkpointer, thread_id="t-recover")
    assert result.status == "completed"
    assert result.final_state["log"] == ["[agent:a] A", "[agent:b] B", "[agent:c] C"]

    # 1) Listar los checkpoints de la ejecución ya terminada.
    refs = await list_checkpoints(result.compiled, "t-recover")
    assert len(refs) >= 4  # start, tras a, tras b, tras c (final)
    # El historial viene del más nuevo al más viejo: el primero es el estado final.
    assert refs[0].next_nodes == ()
    assert refs[0].state_summary["log"] == ["[agent:a] A", "[agent:b] B", "[agent:c] C"]

    # 2) Recuperar un checkpoint intermedio: el estado justo antes de ejecutar 'b'
    #    (después de que corrió 'a'). Debe reflejar solo la salida de 'a'.
    mid = next(ref for ref in refs if ref.next_nodes == ("b",))
    recovered = await get_state_at(result.compiled, "t-recover", mid.checkpoint_id)

    assert recovered.values["log"] == ["[agent:a] A"]
    # ...y es distinto del estado final: efectivamente "viajamos" a un paso intermedio.
    assert recovered.values["log"] != result.final_state["log"]
    assert recovered.next_nodes == ("b",)


async def test_each_step_has_a_distinct_checkpoint(
    linear_graph: GraphDefinition, checkpointer: Any
) -> None:
    result = await run_graph(linear_graph, {}, checkpointer=checkpointer, thread_id="t-steps")
    refs = await list_checkpoints(result.compiled, "t-steps")

    # Cada checkpoint tiene un id único y el estado crece monótonamente hacia atrás en el log.
    ids = [ref.checkpoint_id for ref in refs]
    assert len(ids) == len(set(ids))

    logs_by_pending = {ref.next_nodes: ref.state_summary.get("log", []) for ref in refs}
    assert logs_by_pending[("a",)] == []
    assert logs_by_pending[("b",)] == ["[agent:a] A"]
    assert logs_by_pending[("c",)] == ["[agent:a] A", "[agent:b] B"]


async def test_unknown_thread_has_no_checkpoints(
    linear_graph: GraphDefinition, checkpointer: Any
) -> None:
    # Compilamos para tener un grafo enlazado al checkpointer, pero no ejecutamos ese thread.
    result = await run_graph(linear_graph, {}, checkpointer=checkpointer, thread_id="real")
    refs = await list_checkpoints(result.compiled, "thread-inexistente")
    assert refs == []
