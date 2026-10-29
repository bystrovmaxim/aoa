# tests/maxitor/test_load_aoa_service_action.py
"""Tests for LoadAOAServiceAction: Pydantic validation, aspect logic, downloads through a stub gateway."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from maxitor.front.model.core.actions.load_aoa_service_action import (
    LoadAOAServiceAction,
    LoadAOAServiceParams,
    LoadAOAServiceResult,
)
from maxitor.front.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, Document, Unreachable

from aoa.action_machine.model import BaseState

# ─── Helpers ─────────────────────────────────────────────────────────────────

_ACTION = LoadAOAServiceAction()

_MINIMAL_COORDINATOR: dict[str, Any] = {
    "nodes": [{"id": "n1", "type": "Domain", "label": "D", "properties": {}}],
    "edges": [],
}

_VALID_ENVELOPE = {"coordinator_json": json.dumps(_MINIMAL_COORDINATOR)}


def _state(**kwargs: Any) -> BaseState:
    return BaseState(**kwargs)


# ─── LoadAOAServiceParams ─────────────────────────────────────────────────────


def test_params_rejects_empty_string() -> None:
    with pytest.raises(Exception, match="at least 1 character"):
        LoadAOAServiceParams(service_url="")


def test_params_rejects_whitespace_only() -> None:
    with pytest.raises(Exception, match="at least 1 character"):
        LoadAOAServiceParams(service_url="   ")


def test_params_strips_whitespace() -> None:
    p = LoadAOAServiceParams(service_url="  http://127.0.0.1:8001  ")
    assert p.service_url == "http://127.0.0.1:8001"


def test_params_accepts_base_url() -> None:
    p = LoadAOAServiceParams(service_url="http://127.0.0.1:8001")
    assert p.service_url == "http://127.0.0.1:8001"


def test_params_accepts_full_endpoint_url() -> None:
    p = LoadAOAServiceParams(service_url="http://127.0.0.1:8001/examples/model/graph-json")
    assert p.service_url == "http://127.0.0.1:8001/examples/model/graph-json"


# ─── validate_url_aspect ─────────────────────────────────────────────────────


async def test_validate_url_accepts_bare_host_text() -> None:
    """A bare host without a scheme is accepted and defaults to https."""
    params = LoadAOAServiceParams(service_url="http://placeholder")
    # Override after construction to bypass Pydantic min_length
    object.__setattr__(params, "service_url", "not-a-url")
    result = await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == "https://not-a-url"


async def test_validate_url_rejects_ftp_scheme() -> None:
    params = LoadAOAServiceParams(service_url="http://placeholder")
    object.__setattr__(params, "service_url", "ftp://host:21")
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]


async def test_validate_url_rejects_missing_host() -> None:
    params = LoadAOAServiceParams(service_url="http://placeholder")
    object.__setattr__(params, "service_url", "http://")
    with pytest.raises(ValueError, match="no host"):
        await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]


async def test_validate_url_accepts_http() -> None:
    params = LoadAOAServiceParams(service_url="http://127.0.0.1:8001")
    result = await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == "http://127.0.0.1:8001"


async def test_validate_url_accepts_https() -> None:
    params = LoadAOAServiceParams(service_url="https://example.com")
    result = await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == "https://example.com"


# ─── normalize_url_aspect ────────────────────────────────────────────────────

_ENDPOINT = "/examples/model/graph-json"


async def test_normalize_appends_path_to_base_url() -> None:
    state = _state(service_graph_json_url="http://127.0.0.1:8001")
    result = await _ACTION.normalize_url_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == f"http://127.0.0.1:8001{_ENDPOINT}"


async def test_normalize_strips_trailing_slash_before_appending() -> None:
    state = _state(service_graph_json_url="http://127.0.0.1:8001/")
    result = await _ACTION.normalize_url_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == f"http://127.0.0.1:8001{_ENDPOINT}"


async def test_normalize_leaves_full_endpoint_url_unchanged() -> None:
    full = f"http://127.0.0.1:8001{_ENDPOINT}"
    state = _state(service_graph_json_url=full)
    result = await _ACTION.normalize_url_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == full


async def test_normalize_leaves_full_endpoint_url_with_trailing_slash() -> None:
    full = f"http://127.0.0.1:8001{_ENDPOINT}/"
    state = _state(service_graph_json_url=full)
    result = await _ACTION.normalize_url_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["service_graph_json_url"] == full.rstrip("/")


# ─── validate_service_aspect ─────────────────────────────────────────────────

_URL = f"http://127.0.0.1:8001{_ENDPOINT}"


class _StubGateway:
    """Stands in for ``GraphSourceGateway``: returns one prepared answer and records the URL asked."""

    def __init__(self, answer: Document | Unreachable) -> None:
        self.answer = answer
        self.urls: list[str] = []

    async def fetch(self, url: str) -> Document | Unreachable:
        """Record ``url`` and return the prepared answer."""
        self.urls.append(url)
        return self.answer


def _document(json_body: Any, *, etag: str | None = None) -> Document:
    """A 2xx answer whose body is ``json_body`` serialized."""
    body = json.dumps(json_body).encode()
    return Document(body=body, sha256=hashlib.sha256(body).hexdigest(), etag=etag, last_modified=None)


def _connections(answer: Document | Unreachable) -> dict[str, Any]:
    """Connections carrying a stub gateway that returns ``answer``."""
    return {GRAPH_SOURCE_CONNECTION_KEY: _StubGateway(answer)}


async def test_validate_service_raises_on_http_error() -> None:
    state = _state(service_graph_json_url=_URL)
    with pytest.raises(ValueError, match="HTTP 404"):
        await _ACTION.validate_service_aspect(None, state, None, _connections(Unreachable("HTTP 404", status=404)))  # type: ignore[arg-type]


async def test_validate_service_raises_when_unreachable() -> None:
    state = _state(service_graph_json_url=_URL)
    with pytest.raises(ValueError, match=r"Cannot reach AOA service .*connection refused"):
        await _ACTION.validate_service_aspect(None, state, None, _connections(Unreachable("connection refused")))  # type: ignore[arg-type]


async def test_validate_service_raises_when_coordinator_json_missing() -> None:
    state = _state(service_graph_json_url=_URL)
    with pytest.raises(ValueError, match="coordinator_json"):
        await _ACTION.validate_service_aspect(None, state, None, _connections(_document({"other_field": "value"})))  # type: ignore[arg-type]


async def test_validate_service_raises_when_coordinator_json_not_string() -> None:
    state = _state(service_graph_json_url=_URL)
    answer = _document({"coordinator_json": {"already": "parsed"}})
    with pytest.raises(ValueError, match="coordinator_json"):
        await _ACTION.validate_service_aspect(None, state, None, _connections(answer))  # type: ignore[arg-type]


async def test_validate_service_returns_raw_coordinator_json_and_the_source_identity() -> None:
    state = _state(service_graph_json_url=_URL)
    raw = json.dumps(_MINIMAL_COORDINATOR)
    answer = _document({"coordinator_json": raw}, etag='"abc"')
    result = await _ACTION.validate_service_aspect(None, state, None, _connections(answer))  # type: ignore[arg-type]
    assert result["coordinator_json_raw"] == raw
    assert result["service_graph_json_url"] == _URL
    assert result["source_identity"] == {"sha256": answer.sha256, "etag": '"abc"', "last_modified": ""}


# ─── parse_service_graph_aspect ──────────────────────────────────────────────


async def test_parse_raises_on_invalid_json() -> None:
    state = _state(service_graph_json_url=_URL, coordinator_json_raw="not-json{{")
    with pytest.raises(ValueError, match="not valid JSON"):
        await _ACTION.parse_service_graph_aspect(None, state, None, {})  # type: ignore[arg-type]


async def test_parse_raises_when_nodes_missing() -> None:
    bad = json.dumps({"edges": []})
    state = _state(service_graph_json_url=_URL, coordinator_json_raw=bad)
    with pytest.raises(ValueError, match="'nodes'"):
        await _ACTION.parse_service_graph_aspect(None, state, None, {})  # type: ignore[arg-type]


async def test_parse_raises_when_edges_missing() -> None:
    bad = json.dumps({"nodes": []})
    state = _state(service_graph_json_url=_URL, coordinator_json_raw=bad)
    with pytest.raises(ValueError, match="'edges'"):
        await _ACTION.parse_service_graph_aspect(None, state, None, {})  # type: ignore[arg-type]


async def test_parse_returns_service_graph_data() -> None:
    raw = json.dumps(_MINIMAL_COORDINATOR)
    identity = {"sha256": "0" * 64, "etag": "", "last_modified": ""}
    state = _state(service_graph_json_url=_URL, coordinator_json_raw=raw, source_identity=identity)
    result = await _ACTION.parse_service_graph_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["service_graph_data"] == _MINIMAL_COORDINATOR
    assert result["service_graph_json_url"] == _URL
    assert result["source_identity"] == identity


# ─── build_duckdb_graph_summary ──────────────────────────────────────────────


async def test_build_summary_returns_correct_counts() -> None:
    coordinator = {
        "nodes": [
            {"id": "d.child", "type": "Domain", "label": "Child", "properties": {"name": "C", "description": ""}},
            {"id": "d.parent", "type": "Domain", "label": "Parent", "properties": {"name": "P", "description": ""}},
        ],
        "edges": [
            {"source_id": "d.child", "target_id": "d.parent", "type": "parent_domain", "relationship": "Generalization", "is_dag": False},
        ],
    }
    identity = {"sha256": "a" * 64, "etag": '"v1"', "last_modified": ""}
    state = _state(service_graph_json_url=_URL, service_graph_data=coordinator, source_identity=identity)
    result = await _ACTION.build_duckdb_graph_summary(None, state, None, {})  # type: ignore[arg-type]
    assert isinstance(result, LoadAOAServiceResult)
    assert result.node_count == 2
    assert result.edge_count == 1
    assert result.service_graph_json_url == _URL
    assert (result.content_sha256, result.etag, result.last_modified) == ("a" * 64, '"v1"', "")


async def test_build_summary_empty_graph() -> None:
    coordinator = {"nodes": [], "edges": []}
    state = _state(service_graph_json_url=_URL, service_graph_data=coordinator, source_identity={"sha256": "0" * 64, "etag": "", "last_modified": ""})
    result = await _ACTION.build_duckdb_graph_summary(None, state, None, {})  # type: ignore[arg-type]
    assert result.node_count == 0
    assert result.edge_count == 0
