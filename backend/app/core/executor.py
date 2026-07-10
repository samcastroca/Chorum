"""Ejecución de grafos: ``run_graph`` / ``run_compiled`` y su resultado.

La ejecución es **asíncrona** (``ainvoke``) para alinear con async-by-default (CLAUDE.md),
con el streaming de la Fase 3 (``astream_events``) y con los endpoints async de la Fase 2.

Todo se ejecuta contra un ``checkpointer`` (obligatorio, invariante 6): cada paso queda
persistido bajo un ``thread_id`` para poder recuperar checkpoints intermedios luego. El
``max_iterations`` de la definición se traduce al ``recursion_limit`` de LangGraph; si un ciclo
lo supera, el resultado se reporta con status ``recursion_limit`` en vez de propagar la
excepción.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, ConfigDict, Field

from app.core.compiler import CompiledGraph, compile_graph
from app.core.handlers import HandlerFactory
from app.core.schema import GraphDefinition, NodeType

ExecutionStatus = Literal["completed", "interrupted", "recursion_limit", "error"]


class ExecutionResult(BaseModel):
    """Resultado de ejecutar un grafo.

    ``compiled`` conserva el grafo compilado usado, de modo que la recuperación de checkpoints
    (``list_checkpoints`` / ``get_state_at``) pueda hacerse directamente sobre el mismo
    checkpointer sin recompilar. Se excluye de la serialización.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    thread_id: str
    status: ExecutionStatus
    final_state: dict[str, Any]
    next_nodes: tuple[str, ...] = ()
    error: str | None = None
    compiled: CompiledGraph = Field(default=None, exclude=True, repr=False)


def _build_initial_state(definition: GraphDefinition, user_input: dict[str, Any]) -> dict[str, Any]:
    """Estado inicial: inicializa canales acumulables/colección a vacío y superpone el input.

    Los canales ``append`` (y los de tipo ``list``) necesitan arrancar en ``[]`` para que el
    reducer ``+`` funcione desde el primer paso; los ``dict`` arrancan en ``{}``. Los escalares
    quedan ausentes salvo que el ``user_input`` los provea.
    """
    state: dict[str, Any] = {}
    for channel in definition.state_schema:
        if channel.reducer == "append" or channel.type == "list":
            state[channel.name] = []
        elif channel.type == "dict":
            state[channel.name] = {}
    state.update(user_input)
    return state


async def run_compiled(
    compiled: CompiledGraph,
    definition: GraphDefinition,
    initial_input: dict[str, Any],
    *,
    thread_id: str | None = None,
) -> ExecutionResult:
    """Ejecuta un grafo ya compilado y devuelve su ``ExecutionResult``.

    Genera un ``thread_id`` (uuid4) si no se pasa uno. Traduce ``GraphRecursionError`` a status
    ``recursion_limit`` y detecta interrupciones (``human_in_loop``) inspeccionando el estado
    final: si quedan nodos pendientes, la ejecución está ``interrupted``.
    """
    tid = thread_id or str(uuid4())
    config: dict[str, Any] = {
        "configurable": {"thread_id": tid},
        "recursion_limit": definition.max_iterations,
    }
    state = _build_initial_state(definition, initial_input)

    try:
        raw = await compiled.ainvoke(state, config)
    except GraphRecursionError as exc:
        return ExecutionResult(
            thread_id=tid,
            status="recursion_limit",
            final_state={},
            error=str(exc),
            compiled=compiled,
        )

    snapshot = await compiled.aget_state(config)
    next_nodes = tuple(snapshot.next)
    status: ExecutionStatus = "interrupted" if next_nodes else "completed"
    # Al interrumpirse (human_in_loop), ``ainvoke`` devuelve ``None``: en ese caso el estado
    # vigente es el del snapshot checkpointeado.
    final_values = raw if isinstance(raw, dict) else dict(snapshot.values)
    return ExecutionResult(
        thread_id=tid,
        status=status,
        final_state=dict(final_values),
        next_nodes=next_nodes,
        compiled=compiled,
    )


async def run_graph(
    definition: GraphDefinition,
    initial_input: dict[str, Any],
    *,
    checkpointer: Any,
    thread_id: str | None = None,
    handlers: dict[NodeType, HandlerFactory] | None = None,
) -> ExecutionResult:
    """Compila ``definition`` con el ``checkpointer`` dado y la ejecuta.

    El ``checkpointer`` es obligatorio: no existe una ruta de ejecución sin checkpointing
    (invariante 6). ``handlers`` inyecta factories por tipo de nodo (seam de Fase 6/7). Para
    recuperar checkpoints después, usar ``result.compiled`` con ``list_checkpoints`` /
    ``get_state_at``.
    """
    compiled = compile_graph(definition, checkpointer, handlers=handlers)
    return await run_compiled(compiled, definition, initial_input, thread_id=thread_id)
