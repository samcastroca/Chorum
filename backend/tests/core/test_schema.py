"""Tests de validación del esquema del grafo (``GraphDefinition``)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.schema import AgentNode, GraphDefinition, StartNode


def _graph(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": "g",
        "state_schema": [{"name": "log", "type": "list", "reducer": "append"}],
        "nodes": [
            {"type": "start", "id": "s"},
            {"type": "agent", "id": "a", "system_prompt": "hola", "output_key": "log"},
            {"type": "end", "id": "e"},
        ],
        "edges": [{"source": "s", "target": "a"}, {"source": "a", "target": "e"}],
    }
    base.update(overrides)
    return base


def test_valid_graph_and_helpers() -> None:
    graph = GraphDefinition.model_validate(_graph())
    assert graph.start_node_id() == "s"
    assert graph.end_node_ids() == {"e"}
    assert graph.channel_names() == {"log"}
    assert set(graph.node_map()) == {"s", "a", "e"}


def test_discriminated_union_parses_by_type() -> None:
    graph = GraphDefinition.model_validate(_graph())
    by_id = graph.node_map()
    assert isinstance(by_id["s"], StartNode)
    assert isinstance(by_id["a"], AgentNode)
    assert by_id["a"].system_prompt == "hola"


def test_agent_node_never_stores_a_key() -> None:
    # Invariante 5: un agente referencia un provider_id, jamás una API key en texto plano.
    node = AgentNode(id="a", system_prompt="x", provider_id="anthropic-default")
    assert node.provider_id == "anthropic-default"
    with pytest.raises(ValidationError):
        AgentNode.model_validate({"id": "a", "system_prompt": "x", "api_key": "sk-secret"})


def test_extra_keys_rejected() -> None:
    with pytest.raises(ValidationError):
        GraphDefinition.model_validate(_graph(unexpected="nope"))


def test_duplicate_node_ids_rejected() -> None:
    nodes = [
        {"type": "start", "id": "dup"},
        {"type": "agent", "id": "dup", "system_prompt": "x", "output_key": "log"},
        {"type": "end", "id": "e"},
    ]
    with pytest.raises(ValidationError, match="únicos"):
        GraphDefinition.model_validate(_graph(nodes=nodes))


def test_reserved_id_prefix_rejected() -> None:
    nodes = [
        {"type": "start", "id": "__start__"},
        {"type": "end", "id": "e"},
    ]
    edges = [{"source": "__start__", "target": "e"}]
    with pytest.raises(ValidationError, match="reservado"):
        GraphDefinition.model_validate(_graph(nodes=nodes, edges=edges))


def test_duplicate_channels_rejected() -> None:
    with pytest.raises(ValidationError, match="canal"):
        GraphDefinition.model_validate(_graph(state_schema=[{"name": "log"}, {"name": "log"}]))


@pytest.mark.parametrize(
    ("nodes", "match"),
    [
        (
            [
                {"type": "start", "id": "s"},
                {"type": "start", "id": "s2"},
                {"type": "end", "id": "e"},
            ],
            "exactamente un nodo 'start'",
        ),
        (
            [{"type": "start", "id": "s"}, {"type": "agent", "id": "a", "system_prompt": "x"}],
            "al menos un nodo 'end'",
        ),
    ],
)
def test_start_end_cardinality(nodes: list[dict[str, object]], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        GraphDefinition.model_validate(_graph(nodes=nodes, edges=[]))


def test_dangling_edge_target_rejected() -> None:
    with pytest.raises(ValidationError, match="target inexistente"):
        GraphDefinition.model_validate(
            _graph(edges=[{"source": "s", "target": "a"}, {"source": "a", "target": "ghost"}])
        )


def test_end_node_cannot_have_outgoing_edge() -> None:
    edges = [
        {"source": "s", "target": "a"},
        {"source": "a", "target": "e"},
        {"source": "e", "target": "a"},
    ]
    with pytest.raises(ValidationError, match="salientes"):
        GraphDefinition.model_validate(_graph(edges=edges))


def test_start_needs_outgoing_edge() -> None:
    with pytest.raises(ValidationError, match="saliente"):
        GraphDefinition.model_validate(_graph(edges=[{"source": "a", "target": "e"}]))


def test_condition_field_must_reference_declared_channel() -> None:
    edges = [
        {"source": "s", "target": "a"},
        {"source": "a", "target": "e", "condition": {"field": "ghost", "op": "eq", "value": 1}},
    ]
    with pytest.raises(ValidationError, match="no está declarado"):
        GraphDefinition.model_validate(_graph(edges=edges))


def test_condition_dotted_field_root_must_be_declared() -> None:
    # El root del dotted-path (result) debe existir; los subpaths no se validan estáticamente.
    graph = _graph(
        state_schema=[
            {"name": "result", "type": "dict"},
            {"name": "log", "type": "list", "reducer": "append"},
        ],
        edges=[
            {"source": "s", "target": "a"},
            {"source": "a", "target": "e", "condition": {"field": "result.ok", "op": "truthy"}},
        ],
    )
    assert GraphDefinition.model_validate(graph)  # no levanta


def test_max_iterations_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        GraphDefinition.model_validate(_graph(max_iterations=0))
