"""Tests de integración de ejecución y recuperación de ejecuciones (Fase 2).

Cubre el flujo completo del criterio de aceptación: crear un grafo, ejecutarlo, y recuperar el
historial de la ejecución.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_execute_and_fetch_execution(client: TestClient, graph_payload: dict[str, Any]) -> None:
    graph = client.post("/graphs", json=graph_payload).json()

    resp = client.post(f"/graphs/{graph['id']}/execute", json={"input": {}})
    assert resp.status_code == 201
    execution = resp.json()
    assert execution["status"] == "completed"
    assert execution["thread_id"]
    assert execution["graph_id"] == graph["id"]
    assert execution["graph_version"] == 1
    # El handler placeholder del agente 'a' escribe su salida determinista en el canal 'log'.
    assert "[agent:a] Hola" in execution["final_state"]["log"]

    fetched = client.get(f"/executions/{execution['id']}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == execution["id"]
    assert body["thread_id"] == execution["thread_id"]
    assert body["status"] == "completed"


def test_execute_without_body(client: TestClient, graph_payload: dict[str, Any]) -> None:
    graph = client.post("/graphs", json=graph_payload).json()
    resp = client.post(f"/graphs/{graph['id']}/execute")
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"


def test_execute_graph_not_found(client: TestClient) -> None:
    resp = client.post("/graphs/9999/execute", json={"input": {}})
    assert resp.status_code == 404


def test_get_execution_not_found(client: TestClient) -> None:
    resp = client.get("/executions/9999")
    assert resp.status_code == 404


def test_execution_snapshot_is_reproducible(
    client: TestClient, graph_payload: dict[str, Any]
) -> None:
    """Editar el grafo tras ejecutarlo no altera lo que la ejecución previa corrió."""
    graph = client.post("/graphs", json=graph_payload).json()
    execution = client.post(f"/graphs/{graph['id']}/execute").json()
    assert execution["graph_version"] == 1
    assert "[agent:a] Hola" in execution["final_state"]["log"]

    # Editar el grafo (nueva versión, prompt distinto).
    updated_payload = {
        **graph_payload,
        "version": 2,
        "nodes": [
            {"type": "start", "id": "s"},
            {"type": "agent", "id": "a", "system_prompt": "Cambiado", "output_key": "log"},
            {"type": "end", "id": "e"},
        ],
    }
    put_resp = client.put(f"/graphs/{graph['id']}", json=updated_payload)
    assert put_resp.status_code == 200
    assert put_resp.json()["version"] == 2

    # La ejecución previa conserva su versión original: refleja el snapshot, no la edición.
    fetched = client.get(f"/executions/{execution['id']}").json()
    assert fetched["graph_version"] == 1
    assert "[agent:a] Hola" in fetched["final_state"]["log"]
