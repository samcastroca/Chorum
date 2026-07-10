"""Motor de orquestación: esquema de grafo, compilación a LangGraph y checkpointing.

API pública del core (Fase 1). Base del time-travel debugging (Fase 4): el checkpointing está
habilitado desde el diseño, no como agregado posterior (invariante 6 de CLAUDE.md).
"""

from __future__ import annotations

from app.core.checkpointing import (
    CheckpointRef,
    CheckpointState,
    close_checkpointer,
    create_checkpointer,
    get_state_at,
    list_checkpoints,
)
from app.core.compiler import CompiledGraph, compile_graph
from app.core.executor import ExecutionResult, ExecutionStatus, run_compiled, run_graph
from app.core.handlers import (
    HandlerFactory,
    NodeHandler,
    build_handler,
    register_handler,
)
from app.core.schema import (
    AgentNode,
    CodeNode,
    Comparison,
    ConditionGroup,
    ConditionNode,
    Edge,
    EdgeCondition,
    EndNode,
    GraphDefinition,
    HumanInLoopNode,
    Node,
    NodeType,
    StartNode,
    StateChannel,
    ToolNode,
)

__all__ = [
    # Esquema
    "GraphDefinition",
    "StateChannel",
    "Edge",
    "EdgeCondition",
    "Comparison",
    "ConditionGroup",
    "Node",
    "NodeType",
    "StartNode",
    "EndNode",
    "AgentNode",
    "ToolNode",
    "ConditionNode",
    "CodeNode",
    "HumanInLoopNode",
    # Compilación y ejecución
    "compile_graph",
    "CompiledGraph",
    "run_graph",
    "run_compiled",
    "ExecutionResult",
    "ExecutionStatus",
    # Handlers (seam para Fase 6/7)
    "NodeHandler",
    "HandlerFactory",
    "build_handler",
    "register_handler",
    # Checkpointing y recuperación
    "create_checkpointer",
    "close_checkpointer",
    "list_checkpoints",
    "get_state_at",
    "CheckpointRef",
    "CheckpointState",
]
