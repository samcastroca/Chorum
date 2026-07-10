"""Test de ruteo por condición: un nodo ``condition`` que discrimina según el estado."""

from __future__ import annotations

from typing import Any

import pytest

from app.core import GraphDefinition, run_graph


@pytest.mark.parametrize(
    ("score", "expected"),
    [(20, "[agent:hi] HI"), (2, "[agent:lo] LO")],
)
async def test_condition_routes_both_branches(
    branching_graph: GraphDefinition, checkpointer: Any, score: int, expected: str
) -> None:
    result = await run_graph(branching_graph, {"score": score}, checkpointer=checkpointer)
    assert result.status == "completed"
    assert result.final_state["log"] == [expected]


async def test_default_branch_used_when_no_condition_matches(
    branching_graph: GraphDefinition, checkpointer: Any
) -> None:
    # score ausente -> la comparación gte no matchea -> se toma la arista default (lo).
    result = await run_graph(branching_graph, {}, checkpointer=checkpointer)
    assert result.final_state["log"] == ["[agent:lo] LO"]
