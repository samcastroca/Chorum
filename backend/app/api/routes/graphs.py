"""Endpoints REST de grafos: CRUD (``POST/GET/PUT``) + ejecución (Fase 2).

Al guardar un grafo la definición se valida contra el schema de Fase 1 (``GraphDefinition``);
si es inválida se devuelve un 400 con el detalle. La ejecución es síncrona: se corre el grafo,
se persiste la ``Execution`` con su ``thread_id`` y se devuelve ya completada.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from sqlmodel import Session, select

from app.api.deps import get_checkpointer, get_session
from app.api.schemas import ExecuteRequest, ExecutionRead, GraphRead
from app.core import GraphDefinition, run_graph
from app.db.models import Execution, Graph

router = APIRouter(prefix="/graphs", tags=["graphs"])


def _validate_definition(body: dict[str, Any]) -> GraphDefinition:
    """Valida el body contra el schema de Fase 1; 400 con detalle claro si es inválido.

    Se usa ``json.loads(exc.json())`` en vez de ``exc.errors()`` porque los ``ValueError`` que
    levantan los validadores del core quedan en ``ctx`` como objetos no serializables a JSON;
    ``exc.json()`` los stringifica y evita un 500 al codificar la respuesta.
    """
    try:
        return GraphDefinition.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.loads(exc.json()),
        ) from exc


@router.post("", response_model=GraphRead, status_code=status.HTTP_201_CREATED)
async def create_graph(
    body: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> Graph:
    """Crea un grafo a partir de una ``GraphDefinition`` válida."""
    definition = _validate_definition(body)
    graph = Graph(
        name=definition.name,
        version=definition.version,
        definition=definition.model_dump(mode="json", by_alias=True),
    )
    session.add(graph)
    session.commit()
    session.refresh(graph)
    return graph


@router.get("", response_model=list[GraphRead])
async def list_graphs(session: Session = Depends(get_session)) -> list[Graph]:
    """Lista todos los grafos guardados."""
    return list(session.exec(select(Graph)).all())


@router.get("/{graph_id}", response_model=GraphRead)
async def get_graph(graph_id: int, session: Session = Depends(get_session)) -> Graph:
    """Devuelve un grafo por id, o 404 si no existe."""
    graph = session.get(Graph, graph_id)
    if graph is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grafo no encontrado.")
    return graph


@router.put("/{graph_id}", response_model=GraphRead)
async def update_graph(
    graph_id: int,
    body: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> Graph:
    """Actualiza in-place un grafo existente con una nueva ``GraphDefinition`` válida."""
    graph = session.get(Graph, graph_id)
    if graph is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grafo no encontrado.")
    definition = _validate_definition(body)
    graph.name = definition.name
    graph.version = definition.version
    graph.definition = definition.model_dump(mode="json", by_alias=True)
    graph.updated_at = datetime.now(UTC)
    session.add(graph)
    session.commit()
    session.refresh(graph)
    return graph


@router.post(
    "/{graph_id}/execute",
    response_model=ExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
async def execute_graph(
    graph_id: int,
    request: ExecuteRequest | None = None,
    session: Session = Depends(get_session),
    checkpointer: Any = Depends(get_checkpointer),
) -> Execution:
    """Ejecuta un grafo (síncrono) y persiste la ``Execution`` resultante.

    Se genera un ``thread_id`` propio y se pasa a ``run_graph`` para que quede asociado a esta
    ejecución (necesario para recuperar checkpoints en la Fase 4). Se guarda un snapshot de la
    definición ejecutada para reproducibilidad. Cualquier error inesperado se persiste como una
    ejecución con status ``error`` en vez de propagarse.
    """
    graph = session.get(Graph, graph_id)
    if graph is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grafo no encontrado.")

    definition = GraphDefinition.model_validate(graph.definition)
    initial_input = (request or ExecuteRequest()).input
    thread_id = str(uuid4())

    try:
        result = await run_graph(
            definition,
            initial_input,
            checkpointer=checkpointer,
            thread_id=thread_id,
        )
        exec_status = result.status
        final_state = result.final_state
        error = result.error
    except Exception as exc:  # noqa: BLE001 - se persiste como ejecución fallida, no se propaga
        exec_status = "error"
        final_state = {}
        error = str(exc)

    execution = Execution(
        graph_id=graph_id,
        graph_version=graph.version,
        definition_snapshot=graph.definition,
        thread_id=thread_id,
        status=exec_status,
        final_state=final_state,
        error=error,
        finished_at=datetime.now(UTC),
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution
