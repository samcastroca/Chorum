"""Tests de integración del CRUD de grafos (Fase 2)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_create_graph_valid(client: TestClient, graph_payload: dict[str, Any]) -> None:
    resp = client.post("/graphs", json=graph_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["id"], int)
    assert body["name"] == "demo"
    assert body["version"] == 1
    # La definición se persiste completa (round-trip contra el schema de Fase 1).
    assert len(body["definition"]["nodes"]) == 3
    assert "created_at" in body and "updated_at" in body


def test_create_graph_invalid_returns_400(
    client: TestClient, invalid_graph_payload: dict[str, Any]
) -> None:
    resp = client.post("/graphs", json=invalid_graph_payload)
    assert resp.status_code == 400
    # El detalle viene del ValidationError del core, serializable a JSON.
    assert resp.json()["detail"]


def test_list_graphs(client: TestClient, graph_payload: dict[str, Any]) -> None:
    client.post("/graphs", json=graph_payload)
    client.post("/graphs", json=graph_payload)
    resp = client.get("/graphs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_graph(client: TestClient, graph_payload: dict[str, Any]) -> None:
    created = client.post("/graphs", json=graph_payload).json()
    resp = client.get(f"/graphs/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_graph_not_found(client: TestClient) -> None:
    resp = client.get("/graphs/9999")
    assert resp.status_code == 404


def test_update_graph(client: TestClient, graph_payload: dict[str, Any]) -> None:
    created = client.post("/graphs", json=graph_payload).json()
    updated_payload = {**graph_payload, "name": "demo-v2", "version": 2}
    resp = client.put(f"/graphs/{created['id']}", json=updated_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "demo-v2"
    assert body["version"] == 2
    assert body["id"] == created["id"]


def test_update_graph_not_found(client: TestClient, graph_payload: dict[str, Any]) -> None:
    resp = client.put("/graphs/9999", json=graph_payload)
    assert resp.status_code == 404


def test_update_graph_invalid_returns_400(
    client: TestClient, graph_payload: dict[str, Any], invalid_graph_payload: dict[str, Any]
) -> None:
    created = client.post("/graphs", json=graph_payload).json()
    resp = client.put(f"/graphs/{created['id']}", json=invalid_graph_payload)
    assert resp.status_code == 400
