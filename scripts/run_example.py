#!/usr/bin/env python
"""Demo de la Fase 1: carga un grafo en JSON, lo ejecuta y recupera un checkpoint intermedio.

No hay API ni UI todavía; este script es la forma de ver el motor de orquestación funcionando
de punta a punta (y de verificar el criterio de aceptación "un grafo de 3 agentes en JSON se
ejecuta desde un script").

Uso (con el entorno del backend ya instalado):

    cd backend && uv run python ../scripts/run_example.py
    cd backend && uv run python ../scripts/run_example.py ../examples/linear_pipeline.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core import (  # noqa: E402  (import tras ajustar sys.path)
    GraphDefinition,
    close_checkpointer,
    create_checkpointer,
    get_state_at,
    list_checkpoints,
    run_graph,
)

DEFAULT_GRAPH = REPO_ROOT / "examples" / "linear_pipeline.json"


async def main(path: Path) -> None:
    definition = GraphDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))
    checkpointer = await create_checkpointer()
    try:
        result = await run_graph(definition, {}, checkpointer=checkpointer)
        print(f"grafo:        {definition.name}")
        print(f"thread_id:    {result.thread_id}")
        print(f"status:       {result.status}")
        print(f"estado final: {result.final_state}")

        checkpoints = await list_checkpoints(result.compiled, result.thread_id)
        print(f"\ncheckpoints ({len(checkpoints)}), del primero al último:")
        for ref in reversed(checkpoints):
            print(f"  paso={ref.source_step}  proximo={ref.next_nodes}  estado={ref.state_summary}")

        # Recuperar un checkpoint intermedio (uno con nodos pendientes, a mitad de camino).
        intermediate = [c for c in checkpoints if c.next_nodes]
        if intermediate:
            target = intermediate[len(intermediate) // 2]
            recovered = await get_state_at(result.compiled, result.thread_id, target.checkpoint_id)
            print(
                f"\nrecuperado en checkpoint {target.checkpoint_id[:8]} "
                f"(proximo={recovered.next_nodes}): {recovered.values}"
            )
    finally:
        await close_checkpointer(checkpointer)


if __name__ == "__main__":
    graph_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GRAPH
    asyncio.run(main(graph_path))
