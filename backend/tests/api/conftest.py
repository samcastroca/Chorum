"""Fixtures de payloads para los tests de la API (Fase 2)."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def graph_payload() -> dict[str, Any]:
    """``GraphDefinition`` válida mínima: ``start -> a (agent) -> end``."""
    return {
        "name": "demo",
        "state_schema": [{"name": "log", "type": "list", "reducer": "append"}],
        "nodes": [
            {"type": "start", "id": "s"},
            {"type": "agent", "id": "a", "system_prompt": "Hola", "output_key": "log"},
            {"type": "end", "id": "e"},
        ],
        "edges": [
            {"source": "s", "target": "a"},
            {"source": "a", "target": "e"},
        ],
    }


@pytest.fixture
def invalid_graph_payload() -> dict[str, Any]:
    """Grafo inválido: un edge apunta a un nodo inexistente (viola el schema de Fase 1)."""
    return {
        "name": "bad",
        "state_schema": [{"name": "log", "type": "list", "reducer": "append"}],
        "nodes": [
            {"type": "start", "id": "s"},
            {"type": "agent", "id": "a", "system_prompt": "x", "output_key": "log"},
            {"type": "end", "id": "e"},
        ],
        "edges": [
            {"source": "s", "target": "a"},
            {"source": "a", "target": "nope"},
        ],
    }
