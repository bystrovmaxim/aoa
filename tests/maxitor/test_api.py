# tests/maxitor/test_api.py
"""Smoke tests for the Maxitor FastAPI backend."""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from aoa.maxitor.api.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create a TestClient with FastAPI lifespan enabled."""
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_action_adapter_health(client: TestClient) -> None:
    """Mounted FastApiAdapter exposes its own health route."""
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_sidebar(client: TestClient) -> None:
    response = client.get("/api/sidebar")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"level1_nodes", "level2_diagrams", "level2_nodes", "level3_diagrams"}
    assert payload["level1_nodes"]


def test_interchange_graph_payload_json(client: TestClient) -> None:
    response = client.get("/api/v1/graph/interchange")

    assert response.status_code == 200
    body = response.json()
    assert "payload" in body
    p = body["payload"]
    assert "nodes" in p and "edges" in p
    assert isinstance(p["nodes"], list) and isinstance(p["edges"], list)


def test_erd_domain_qualnames_json(client: TestClient) -> None:
    response = client.get("/api/v1/erd/domain-qualnames")

    assert response.status_code == 200
    data = response.json()
    assert "list_domains" in data
    assert isinstance(data["list_domains"], list)
    assert data["list_domains"]
    row0 = data["list_domains"][0]
    assert set(row0) == {"qualname", "color"}
    assert isinstance(row0["qualname"], str) and row0["qualname"]
    assert isinstance(row0["color"], str) and row0["color"].startswith("#")


def test_erd_domain_payload_json(client: TestClient) -> None:
    listing = client.get("/api/v1/erd/domain-qualnames").json()
    qual = listing["list_domains"][0]["qualname"]
    path = quote(qual, safe="")
    response = client.get(f"/api/v1/erd/domains/{path}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"domain_label", "domain_qualifier", "list_entities"}
    assert body["domain_qualifier"] == qual
    assert "entities" in body["list_entities"] and "relations" in body["list_entities"]
