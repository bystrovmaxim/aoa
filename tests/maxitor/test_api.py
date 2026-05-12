# tests/maxitor/test_api.py
"""Smoke tests for the Maxitor FastAPI backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


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
    assert p["legend_items"]
    assert any(item["type"] != "unknown" for item in p["legend_items"])


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
    rows = listing["list_domains"]
    assert rows

    qual: str | None = None
    row: dict[str, object] | None = None
    for cand in rows:
        q = str(cand["qualname"])
        response = client.get(
            "/api/v1/erd/domains",
            params={"domain_qualnames": q, "include_one_hop_neighbors": "true"},
        )
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"domain_slices"}
        slices = body["domain_slices"]
        assert len(slices) == 1
        slice0 = slices[0]
        entities = slice0["list_entities"]["entities"]
        if entities:
            qual = q
            row = slice0
            break

    assert qual is not None, "fixture graph must expose at least one domain with ERD entities"
    assert row is not None
    assert set(row) == {"domain_label", "domain_qualname", "list_entities"}
    assert row["domain_qualname"] == qual
    assert "entities" in row["list_entities"] and "relations" in row["list_entities"]
    entities = row["list_entities"]["entities"]
    assert entities
    assert any(len(entity.get("fields", ())) >= 1 for entity in entities)
    for entity in row["list_entities"]["entities"]:
        assert "domain_qualname" in entity
        assert isinstance(entity["domain_qualname"], str)
    assert any(e["domain_qualname"] == qual for e in row["list_entities"]["entities"])


def test_erd_domains_batch_empty(client: TestClient) -> None:
    response = client.get(
        "/api/v1/erd/domains",
        params=[("include_one_hop_neighbors", "false")],
    )
    assert response.status_code == 200
    assert response.json() == {"domain_slices": []}


def test_erd_domains_batch_multi(client: TestClient) -> None:
    listing = client.get("/api/v1/erd/domain-qualnames").json()
    quals = [listing["list_domains"][i]["qualname"] for i in range(min(2, len(listing["list_domains"])))]
    if len(quals) < 2:
        pytest.skip("need at least two domains in fixture graph")
    response = client.get(
        "/api/v1/erd/domains",
        params=[
            ("domain_qualnames", quals[0]),
            ("domain_qualnames", quals[1]),
            ("include_one_hop_neighbors", "false"),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert [s["domain_qualname"] for s in body["domain_slices"]] == quals
