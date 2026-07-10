"""Tests de los handlers de nodo: placeholders, seam de override, e invariantes."""

from __future__ import annotations

from typing import Any

from app.core import GraphDefinition, run_graph
from app.core.handlers import _HANDLER_FACTORIES, build_handler, register_handler
from app.core.schema import AgentNode, Node
from app.core.schema import GraphDefinition as GD


def _one_node_graph(node: dict[str, Any], output_channel: str = "out") -> GraphDefinition:
    return GraphDefinition.model_validate(
        {
            "name": "single",
            "state_schema": [{"name": output_channel, "type": "str"}],
            "nodes": [
                {"type": "start", "id": "s"},
                node,
                {"type": "end", "id": "e"},
            ],
            "edges": [{"source": "s", "target": node["id"]}, {"source": node["id"], "target": "e"}],
        }
    )


async def test_agent_placeholder_writes_deterministic_output(checkpointer: Any) -> None:
    graph = _one_node_graph(
        {"type": "agent", "id": "a", "system_prompt": "responde", "output_key": "out"}
    )
    result = await run_graph(graph, {}, checkpointer=checkpointer)
    assert result.final_state["out"] == "[agent:a] responde"


async def test_tool_placeholder_writes_marker(checkpointer: Any) -> None:
    graph = _one_node_graph({"type": "tool", "id": "t", "tool_name": "http", "output_key": "out"})
    result = await run_graph(graph, {}, checkpointer=checkpointer)
    assert "[tool:t:http]" in result.final_state["out"]


async def test_code_node_does_not_execute_user_code(checkpointer: Any) -> None:
    # Invariante 3: el código de usuario NO corre in-process en Fase 1. Si corriera, este
    # `raise` reventaría la ejecución; en cambio el placeholder devuelve un marcador.
    graph = _one_node_graph(
        {
            "type": "code",
            "id": "c",
            "code": "raise RuntimeError('no debe ejecutarse')",
            "output_key": "out",
        }
    )
    result = await run_graph(graph, {}, checkpointer=checkpointer)
    assert result.status == "completed"
    assert "no ejecutado" in result.final_state["out"]


async def test_append_channel_wraps_output_in_list(checkpointer: Any) -> None:
    graph = GraphDefinition.model_validate(
        {
            "name": "single-append",
            "state_schema": [{"name": "out", "type": "list", "reducer": "append"}],
            "nodes": [
                {"type": "start", "id": "s"},
                {"type": "agent", "id": "a", "system_prompt": "hi", "output_key": "out"},
                {"type": "end", "id": "e"},
            ],
            "edges": [{"source": "s", "target": "a"}, {"source": "a", "target": "e"}],
        }
    )
    result = await run_graph(graph, {}, checkpointer=checkpointer)
    assert result.final_state["out"] == ["[agent:a] hi"]


async def test_handler_override_takes_precedence(checkpointer: Any) -> None:
    def custom(node: Node, _definition: GD) -> Any:
        assert isinstance(node, AgentNode)
        key = node.output_key

        async def handler(_state: dict[str, Any]) -> dict[str, Any]:
            return {key: "OVERRIDDEN"}

        return handler

    graph = _one_node_graph({"type": "agent", "id": "a", "system_prompt": "x", "output_key": "out"})
    result = await run_graph(graph, {}, checkpointer=checkpointer, handlers={"agent": custom})
    assert result.final_state["out"] == "OVERRIDDEN"


def test_register_handler_replaces_global_factory() -> None:
    original = _HANDLER_FACTORIES["agent"]
    calls: list[str] = []

    def custom(node: Node, _definition: GD) -> Any:
        calls.append(node.id)

        async def handler(_state: dict[str, Any]) -> dict[str, Any]:
            return {}

        return handler

    try:
        register_handler("agent", custom)
        assert _HANDLER_FACTORIES["agent"] is custom
        # build_handler debe usar la factory registrada globalmente (sin overrides).
        graph = _one_node_graph(
            {"type": "agent", "id": "a", "system_prompt": "x", "output_key": "out"}
        )
        build_handler(AgentNode(id="a", system_prompt="x"), graph)
        assert calls == ["a"]
    finally:
        register_handler("agent", original)
    assert _HANDLER_FACTORIES["agent"] is original


async def test_human_in_loop_interrupts_execution(checkpointer: Any) -> None:
    graph = GraphDefinition.model_validate(
        {
            "name": "hil",
            "state_schema": [{"name": "out", "type": "str"}],
            "nodes": [
                {"type": "start", "id": "s"},
                {"type": "human_in_loop", "id": "h", "prompt": "confirmá"},
                {"type": "end", "id": "e"},
            ],
            "edges": [{"source": "s", "target": "h"}, {"source": "h", "target": "e"}],
        }
    )
    result = await run_graph(graph, {}, checkpointer=checkpointer)
    # interrupt_before pausa antes del nodo human_in_loop: la ejecución queda 'interrupted'.
    assert result.status == "interrupted"
    assert "h" in result.next_nodes
