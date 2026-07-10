"""Tests de grafos con ciclo: terminación por condición y límite de iteraciones."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core import GraphDefinition, HandlerFactory, run_graph


async def test_cycle_terminates_on_condition(
    cycle_graph: Callable[[int], GraphDefinition],
    checkpointer: Any,
    increment_handlers: dict[str, HandlerFactory],
) -> None:
    result = await run_graph(
        cycle_graph(25), {"count": 0}, checkpointer=checkpointer, handlers=increment_handlers
    )
    assert result.status == "completed"
    assert result.final_state["count"] == 3


async def test_cycle_respects_max_iterations(
    cycle_graph: Callable[[int], GraphDefinition],
    checkpointer: Any,
    increment_handlers: dict[str, HandlerFactory],
) -> None:
    # max_iterations=2 no alcanza a llegar a count==3: se corta con status recursion_limit
    # en vez de propagar la excepción o colgarse en un bucle infinito.
    result = await run_graph(
        cycle_graph(2), {"count": 0}, checkpointer=checkpointer, handlers=increment_handlers
    )
    assert result.status == "recursion_limit"
    assert result.error is not None
