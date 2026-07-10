"""Esquema de datos del grafo de agentes (``GraphDefinition`` y sus piezas).

Este módulo es la **única fuente de verdad** sobre qué puede ejecutar el sistema
(invariante 1 de CLAUDE.md). El canvas visual (fases posteriores) serializa/deserializa
contra estos modelos Pydantic, y el compilador (`compiler.py`) los traduce a un
``StateGraph`` de LangGraph.

Decisiones de diseño relevantes:

- Los nodos son una **unión discriminada** por el campo ``type``.
- Las condiciones de los edges son **declarativas** (`Comparison` / `ConditionGroup`), nunca
  cadenas evaluadas con ``eval``/``exec``: el ``GraphDefinition`` proviene de JSON del
  usuario y debe poder validarse y ejecutarse sin abrir una vía de ejecución de código.
- Las API keys nunca viven aquí: un nodo ``agent`` referencia un ``provider_id``, jamás una
  key en texto plano (invariante 5 de CLAUDE.md).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Estado compartido
# ---------------------------------------------------------------------------

ChannelType = Literal["str", "int", "float", "bool", "list", "dict", "any"]
Reducer = Literal["replace", "append"]


class StateChannel(BaseModel):
    """Un canal del estado compartido del grafo.

    Se traduce en runtime a un campo del ``TypedDict`` de estado de LangGraph. Un canal con
    ``reducer="append"`` acumula (``Annotated[list, operator.add]``); ``"replace"`` (default)
    sobrescribe con el último valor.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    type: ChannelType = "any"
    reducer: Reducer = "replace"
    description: str | None = None


# ---------------------------------------------------------------------------
# Condiciones declarativas (sin eval)
# ---------------------------------------------------------------------------

Op = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "contains",
    "truthy",
    "falsy",
    "exists",
]


class Comparison(BaseModel):
    """Comparación hoja evaluada contra el estado.

    ``field`` es un *dotted path* dentro del estado (ej. ``"result.ok"``). ``value`` no se usa
    para los operadores unarios ``truthy``/``falsy``/``exists``. La evaluación vive en
    ``conditions.py`` y solo usa comparaciones de Python (nunca ``eval``).
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    op: Op
    value: Any = None


class ConditionGroup(BaseModel):
    """Combinación lógica de condiciones (``all``/``any``/``not``).

    Los tres campos son opcionales y se combinan con AND entre sí (un grupo vacío es ``True``).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    all: list[EdgeCondition] | None = None
    any: list[EdgeCondition] | None = None
    not_: EdgeCondition | None = Field(default=None, alias="not")


# Alias implícito (forma clásica soportada por Pydantic y mypy). Recursivo: se resuelve en
# ``ConditionGroup.model_rebuild()`` al final del módulo.
EdgeCondition = Comparison | ConditionGroup


# ---------------------------------------------------------------------------
# Nodos (unión discriminada por ``type``)
# ---------------------------------------------------------------------------

NodeType = Literal["start", "end", "agent", "tool", "condition", "code", "human_in_loop"]


class _NodeBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str | None = None


class StartNode(_NodeBase):
    """Punto de entrada del grafo. Se mapea al sentinel ``START`` de LangGraph."""

    type: Literal["start"] = "start"


class EndNode(_NodeBase):
    """Nodo terminal. Se mapea al sentinel ``END`` de LangGraph."""

    type: Literal["end"] = "end"


class AgentNode(_NodeBase):
    """Nodo agente: invoca un modelo vía ``ModelProvider`` (Fase 6).

    En Fase 1 su handler es un *placeholder* determinista que **nunca** llama a un SDK; la
    implementación real se inyecta más adelante a través del registry de handlers, respetando
    el invariante 2 (todo acceso a modelos pasa por ``ModelProvider``).
    """

    type: Literal["agent"] = "agent"
    system_prompt: str
    provider_id: str | None = None  # solo referencia, jamás una key (invariante 5)
    allowed_tools: list[str] = Field(default_factory=list)
    memory_policy: Literal["none", "window", "all"] = "none"
    output_key: str = "messages"


class ToolNode(_NodeBase):
    """Nodo herramienta: ejecuta una tool registrada (Fase 7). Placeholder en Fase 1."""

    type: Literal["tool"] = "tool"
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_key: str


class ConditionNode(_NodeBase):
    """Nodo de ruteo puro (identidad sobre el estado).

    No muta el estado; el ruteo se define en sus edges salientes, cada uno con su
    ``EdgeCondition``. Sirve para que el canvas exprese una decisión explícita como nodo.
    """

    type: Literal["condition"] = "condition"


class CodeNode(_NodeBase):
    """Nodo de código Python.

    **En Fase 1 NO se ejecuta in-process** (invariante 3): el código de usuario solo puede
    correr dentro del sandbox aislado, que se implementa en la Fase 7. El handler placeholder
    devuelve un marcador sin evaluar ``code``.
    """

    type: Literal["code"] = "code"
    code: str
    output_key: str


class HumanInLoopNode(_NodeBase):
    """Nodo que pausa la ejecución esperando input humano.

    Se compila con ``interrupt_before`` de LangGraph: la ejecución se detiene antes del nodo y
    el estado queda checkpointeado, listo para reanudarse (base de time-travel, Fase 4).
    """

    type: Literal["human_in_loop"] = "human_in_loop"
    prompt: str | None = None
    input_key: str = "human_input"


Node = Annotated[
    StartNode | EndNode | AgentNode | ToolNode | ConditionNode | CodeNode | HumanInLoopNode,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Edges y definición del grafo
# ---------------------------------------------------------------------------


class Edge(BaseModel):
    """Arista dirigida ``source -> target`` con condición opcional.

    Si ``condition`` es ``None`` la arista es incondicional. Varias aristas condicionales
    desde el mismo origen se evalúan en orden; una arista sin condición actúa como *default*.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    condition: EdgeCondition | None = None


class GraphDefinition(BaseModel):
    """Definición completa de un grafo de agentes: estado + nodos + edges.

    Es lo que se persiste, valida y compila. ``max_iterations`` acota los ciclos y se traduce
    al ``recursion_limit`` de LangGraph.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    version: int = 1
    state_schema: list[StateChannel]
    nodes: list[Node]
    edges: list[Edge]
    max_iterations: int = Field(default=25, gt=0)

    # -- Helpers de consulta -------------------------------------------------

    def node_map(self) -> dict[str, Node]:
        """Índice ``id -> nodo``."""
        return {node.id: node for node in self.nodes}

    def channel_names(self) -> set[str]:
        """Nombres de todos los canales de estado declarados."""
        return {channel.name for channel in self.state_schema}

    def start_node_id(self) -> str:
        """Id del (único) nodo ``start``."""
        return next(node.id for node in self.nodes if node.type == "start")

    def end_node_ids(self) -> set[str]:
        """Ids de los nodos ``end``."""
        return {node.id for node in self.nodes if node.type == "end"}

    # -- Validación ----------------------------------------------------------

    @model_validator(mode="after")
    def _validate(self) -> GraphDefinition:
        self._validate_ids_and_channels()
        self._validate_start_end()
        self._validate_edges()
        self._validate_condition_fields()
        return self

    def _validate_ids_and_channels(self) -> None:
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Los id de nodo deben ser únicos.")
        for node_id in ids:
            if not node_id or node_id.startswith("__"):
                raise ValueError(
                    f"Id de nodo inválido: {node_id!r} (vacío o con prefijo reservado '__')."
                )
        channels = [channel.name for channel in self.state_schema]
        if len(channels) != len(set(channels)):
            raise ValueError("Los nombres de canal de estado deben ser únicos.")

    def _validate_start_end(self) -> None:
        starts = [node for node in self.nodes if node.type == "start"]
        ends = [node for node in self.nodes if node.type == "end"]
        if len(starts) != 1:
            raise ValueError(
                f"El grafo debe tener exactamente un nodo 'start' (tiene {len(starts)})."
            )
        if not ends:
            raise ValueError("El grafo debe tener al menos un nodo 'end'.")

    def _validate_edges(self) -> None:
        known = set(self.node_map())
        start_id = self.start_node_id()
        end_ids = self.end_node_ids()
        outgoing: dict[str, int] = dict.fromkeys(known, 0)
        for edge in self.edges:
            if edge.source not in known:
                raise ValueError(f"Edge con source inexistente: {edge.source!r}.")
            if edge.target not in known:
                raise ValueError(f"Edge con target inexistente: {edge.target!r}.")
            if edge.source in end_ids:
                raise ValueError(f"Un nodo 'end' no puede tener edges salientes: {edge.source!r}.")
            if edge.target == start_id:
                raise ValueError("El nodo 'start' no puede ser destino de un edge.")
            outgoing[edge.source] += 1
        if outgoing[start_id] == 0:
            raise ValueError("El nodo 'start' necesita al menos un edge saliente.")
        for node in self.nodes:
            if node.type == "condition" and outgoing[node.id] == 0:
                raise ValueError(
                    f"El nodo condition {node.id!r} necesita al menos un edge saliente."
                )

    def _validate_condition_fields(self) -> None:
        channels = self.channel_names()
        for edge in self.edges:
            if edge.condition is None:
                continue
            for comparison in _iter_comparisons(edge.condition):
                root = comparison.field.split(".", 1)[0]
                if root not in channels:
                    raise ValueError(
                        f"La condición referencia el campo {comparison.field!r} cuyo canal "
                        f"raíz {root!r} no está declarado en state_schema."
                    )


def _iter_comparisons(condition: EdgeCondition) -> list[Comparison]:
    """Aplana un ``EdgeCondition`` a la lista de ``Comparison`` hoja que contiene."""
    if isinstance(condition, Comparison):
        return [condition]
    result: list[Comparison] = []
    for group in (condition.all, condition.any):
        for sub in group or ():
            result.extend(_iter_comparisons(sub))
    if condition.not_ is not None:
        result.extend(_iter_comparisons(condition.not_))
    return result


# ``from __future__ import annotations`` hace lazy todas las anotaciones; reconstruimos los
# modelos con referencias forward (EdgeCondition recursivo, unión discriminada de nodos) una
# vez que todos los nombres del módulo existen.
ConditionGroup.model_rebuild()
GraphDefinition.model_rebuild()
