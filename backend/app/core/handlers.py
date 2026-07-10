"""Registry de *handlers* de nodo y placeholders deterministas de la Fase 1.

Un ``NodeHandler`` es la función async que LangGraph ejecuta para un nodo: recibe el estado
actual y devuelve una actualización parcial del estado. Este módulo es el **seam** que
permite que fases posteriores inyecten la lógica real sin tocar el compilador:

- Fase 6 reemplaza el handler de ``agent`` por uno que llama a un ``ModelProvider`` (invariante
  2: todo acceso a modelos pasa por esa interfaz).
- Fase 7 reemplaza el de ``tool``/``code`` por uno que corre en el sandbox aislado.

En la Fase 1 los handlers son placeholders deterministas y **sin I/O de red**. En particular
el nodo ``code`` **no ejecuta** el código del usuario in-process (invariante 3): eso solo puede
pasar dentro del sandbox de la Fase 7.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.core.schema import (
    AgentNode,
    CodeNode,
    GraphDefinition,
    Node,
    NodeType,
    ToolNode,
)

# Un handler recibe el estado y devuelve una actualización parcial del estado.
NodeHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
# Una factory construye el handler de un nodo concreto, con acceso a la definición del grafo
# (por ejemplo para conocer el reducer del canal de salida).
HandlerFactory = Callable[[Node, GraphDefinition], NodeHandler]


def _channel_is_append(definition: GraphDefinition, name: str) -> bool:
    """¿El canal ``name`` acumula (reducer ``append``)? Determina la forma del valor escrito."""
    for channel in definition.state_schema:
        if channel.name == name:
            return channel.reducer == "append"
    return False


def _write(definition: GraphDefinition, output_key: str, item: Any) -> dict[str, Any]:
    """Empaqueta ``item`` para el canal ``output_key`` según su reducer.

    En un canal ``append`` la actualización debe ser una lista (el reducer hace ``+``); en uno
    ``replace`` se escribe el valor tal cual.
    """
    if _channel_is_append(definition, output_key):
        return {output_key: [item]}
    return {output_key: item}


def make_agent_handler(node: Node, definition: GraphDefinition) -> NodeHandler:
    """Placeholder de ``agent``: emite una salida determinista, sin llamar a ningún modelo."""
    assert isinstance(node, AgentNode)
    node_id, prompt, output_key = node.id, node.system_prompt, node.output_key

    async def handler(_state: dict[str, Any]) -> dict[str, Any]:
        return _write(definition, output_key, f"[agent:{node_id}] {prompt}")

    return handler


def make_tool_handler(node: Node, definition: GraphDefinition) -> NodeHandler:
    """Placeholder de ``tool``: no ejecuta ninguna herramienta real todavía (Fase 7)."""
    assert isinstance(node, ToolNode)
    node_id, tool_name, output_key = node.id, node.tool_name, node.output_key

    async def handler(_state: dict[str, Any]) -> dict[str, Any]:
        return _write(definition, output_key, f"[tool:{node_id}:{tool_name}] (placeholder)")

    return handler


def make_code_handler(node: Node, definition: GraphDefinition) -> NodeHandler:
    """Placeholder de ``code``: no ejecuta el código del usuario (invariante 3)."""
    assert isinstance(node, CodeNode)
    node_id, output_key = node.id, node.output_key

    async def handler(_state: dict[str, Any]) -> dict[str, Any]:
        return _write(definition, output_key, f"[code:{node_id}] (no ejecutado en Fase 1)")

    return handler


def make_passthrough_handler(node: Node, _definition: GraphDefinition) -> NodeHandler:
    """Handler identidad: no muta el estado. Usado por ``condition`` y ``human_in_loop``."""

    async def handler(_state: dict[str, Any]) -> dict[str, Any]:
        return {}

    return handler


# Registry por tipo de nodo. ``start``/``end`` no tienen handler (se mapean a los sentinels
# START/END de LangGraph en el compilador). Fase 6/7 sobreescriben entradas vía
# ``register_handler`` sin tocar el compilador.
_HANDLER_FACTORIES: dict[NodeType, HandlerFactory] = {
    "agent": make_agent_handler,
    "tool": make_tool_handler,
    "code": make_code_handler,
    "condition": make_passthrough_handler,
    "human_in_loop": make_passthrough_handler,
}


def register_handler(node_type: NodeType, factory: HandlerFactory) -> None:
    """Registra/reemplaza la factory de handler para un tipo de nodo (seam para Fase 6/7)."""
    _HANDLER_FACTORIES[node_type] = factory


def build_handler(
    node: Node,
    definition: GraphDefinition,
    overrides: dict[NodeType, HandlerFactory] | None = None,
) -> NodeHandler:
    """Devuelve el handler para ``node`` según su tipo.

    ``overrides`` (por tipo de nodo) tiene prioridad sobre el registry global: es el punto por
    el que Fase 6/7 —o un test— inyectan handlers reales para una compilación concreta sin
    mutar el estado global del proceso.
    """
    factory = (overrides or {}).get(node.type)
    if factory is None:
        try:
            factory = _HANDLER_FACTORIES[node.type]
        except KeyError as exc:  # pragma: no cover - defensivo: tipos start/end no llegan aquí
            raise ValueError(
                f"No hay handler registrado para el tipo de nodo {node.type!r}."
            ) from exc
    return factory(node, definition)
