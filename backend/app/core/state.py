"""Construcción del esquema de estado de LangGraph a partir de los ``StateChannel``.

LangGraph necesita un tipo de estado (aquí un ``TypedDict`` dinámico) que declare cada canal
y su *reducer*. Un canal ``append`` se traduce a ``Annotated[list, operator.add]`` para que
las actualizaciones se acumulen en vez de sobrescribir; el resto usa el tipo Python del canal
con semántica de reemplazo (la default de LangGraph).
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.core.schema import StateChannel

_PY_TYPES: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list[Any],
    "dict": dict[str, Any],
    "any": Any,
}


def build_state_type(channels: list[StateChannel]) -> type[Any]:
    """Devuelve un ``TypedDict`` dinámico que representa el estado compartido del grafo.

    - ``reducer="append"`` -> ``Annotated[list[Any], operator.add]`` (acumula).
    - ``reducer="replace"`` -> el tipo Python del canal (sobrescribe).

    Si no hay canales declarados se usa un único canal ``messages`` acumulable como default
    razonable, de modo que el estado nunca sea un ``TypedDict`` vacío.
    """
    annotations: dict[str, Any] = {}
    for channel in channels:
        if channel.reducer == "append":
            annotations[channel.name] = Annotated[list[Any], operator.add]
        else:
            annotations[channel.name] = _PY_TYPES[channel.type]
    if not annotations:
        annotations["messages"] = Annotated[list[Any], operator.add]
    # TypedDict funcional con campos dinámicos: mypy no puede tipar campos calculados en
    # runtime, de ahí el ignore puntual. total=False -> las actualizaciones son parciales.
    return TypedDict("GraphState", annotations, total=False)  # type: ignore
