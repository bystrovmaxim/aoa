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


def test_sidebar(client: TestClient) -> None:
    response = client.get("/api/sidebar")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"level1_nodes", "level2_diagrams", "level2_nodes", "level3_diagrams"}
    assert payload["level1_nodes"]


def test_graph_diagram_html(client: TestClient) -> None:
    response = client.get("/api/diagrams/graph")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Interchange graph" in response.text


def test_erd_diagram_html_all_domains(client: TestClient) -> None:
    response = client.get("/api/diagrams/erd")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Interchange ERD" in response.text or "ERD" in response.text


def test_erd_diagram_html_one_domain(client: TestClient) -> None:
    sidebar = client.get("/api/sidebar").json()
    domain_qual: str | None = None
    for row in sidebar["level3_diagrams"]:
        if row.get("type") == "erd_domain" and row.get("parent_id"):
            domain_qual = str(row["parent_id"])
            break
    assert domain_qual is not None

    path = quote(domain_qual, safe="")
    response = client.get(f"/api/diagrams/erd/{path}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
