"""Compilación de un ``GraphDefinition`` propio a un ``StateGraph`` de LangGraph.

``compile_graph`` es la traducción entre la única fuente de verdad (el esquema del usuario,
invariante 1) y el motor de ejecución. Responsabilidades:

- Construir el tipo de estado (``state.build_state_type``).
- Agregar un nodo LangGraph por cada nodo real (``agent``/``tool``/``condition``/``code``/
  ``human_in_loop``) usando el registry de handlers; ``start``/``end`` se mapean a los
  sentinels ``START``/``END``.
- Traducir edges: incondicionales -> ``add_edge`` (soporta fan-out); condicionales o salientes
  de un nodo ``condition`` -> un único router vía ``add_conditional_edges`` que evalúa cada
  ``EdgeCondition`` en orden (primer match gana) y usa la arista sin condición como *default*.
- Marcar los nodos ``human_in_loop`` con ``interrupt_before`` (pausa + checkpoint).
- Compilar con el ``checkpointer`` (obligatorio: invariante 6).

Los objetos de LangGraph se tratan como ``Any`` en las fronteras: el esquema del usuario y la
lógica de ruteo/estado sí están tipados, pero no acoplamos este código a los genéricos internos
de LangGraph.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.core.conditions import evaluate
from app.core.handlers import HandlerFactory, build_handler
from app.core.schema import Edge, GraphDefinition, NodeType
from app.core.state import build_state_type

# Tipo del grafo compilado de LangGraph. Se expone como ``Any`` a propósito (ver docstring).
CompiledGraph = Any


def compile_graph(
    definition: GraphDefinition,
    checkpointer: Any,
    *,
    handlers: dict[NodeType, HandlerFactory] | None = None,
) -> CompiledGraph:
    """Compila ``definition`` a un ``CompiledStateGraph`` de LangGraph con checkpointing.

    ``handlers`` permite inyectar factories de handler por tipo de nodo para esta compilación
    (seam de Fase 6/7); si es ``None`` se usan los placeholders del registry global.
    """
    builder: Any = StateGraph(build_state_type(definition.state_schema))

    # 1) Nodos reales (start/end se mapean a los sentinels, no son nodos).
    for node in definition.nodes:
        if node.type in ("start", "end"):
            continue
        builder.add_node(node.id, build_handler(node, definition, handlers))

    # 2) Edges, agrupados por nodo de origen.
    start_id = definition.start_node_id()
    end_ids = definition.end_node_ids()
    node_types = {node.id: node.type for node in definition.nodes}

    def to_lg(node_id: str) -> str:
        if node_id == start_id:
            return START
        if node_id in end_ids:
            return END
        return node_id

    by_source: dict[str, list[Edge]] = defaultdict(list)
    for edge in definition.edges:
        by_source[edge.source].append(edge)

    for source, edges in by_source.items():
        conditional = [edge for edge in edges if edge.condition is not None]
        unconditional = [edge for edge in edges if edge.condition is None]
        is_condition_node = node_types[source] == "condition"

        if not conditional and not is_condition_node:
            # Incondicional puro: una o varias aristas (fan-out) directas.
            for edge in unconditional:
                builder.add_edge(to_lg(source), to_lg(edge.target))
        else:
            _add_router(builder, to_lg(source), conditional, unconditional, to_lg)

    interrupts = [node.id for node in definition.nodes if node.type == "human_in_loop"]
    return builder.compile(checkpointer=checkpointer, interrupt_before=interrupts or None)


def _add_router(
    builder: Any,
    lg_source: str,
    conditional: list[Edge],
    unconditional: list[Edge],
    to_lg: Callable[[str], str],
) -> None:
    """Agrega ruteo condicional: primer match gana; arista sin condición = default (o END)."""
    default_target = to_lg(unconditional[0].target) if unconditional else END
    pairs = [(edge.condition, to_lg(edge.target)) for edge in conditional]

    def router(state: dict[str, Any]) -> str:
        for condition, target in pairs:
            if condition is not None and evaluate(condition, state):
                return target
        return default_target

    path_map: dict[str, str] = {target: target for _, target in pairs}
    path_map[default_target] = default_target
    builder.add_conditional_edges(lg_source, router, path_map)
