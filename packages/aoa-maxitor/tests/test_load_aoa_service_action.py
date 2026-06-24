# tests/maxitor/test_load_aoa_service_action.py
"""Tests for LoadAOAServiceAction: Pydantic validation, aspect logic, httpx mocking."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aoa.action_machine.model import BaseState
from aoa.maxitor.model.core.actions.load_aoa_service_action import (
    LoadAOAServiceAction,
    LoadAOAServiceParams,
    LoadAOAServiceResult,
)

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


async def test_validate_url_rejects_plain_text() -> None:
    params = LoadAOAServiceParams(service_url="http://placeholder")
    # Override after construction to bypass Pydantic min_length
    object.__setattr__(params, "service_url", "not-a-url")
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        await _ACTION.validate_url_aspect(params, _state(), None, {})  # type: ignore[arg-type]


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


def _mock_response(status_code: int, json_body: Any) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response

        resp.raise_for_status.side_effect = HTTPStatusError(
            message=str(status_code),
            request=MagicMock(spec=Request),
            response=MagicMock(spec=Response, status_code=status_code),
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


async def test_validate_service_raises_on_http_error() -> None:
    state = _state(service_graph_json_url=_URL)
    mock_resp = _mock_response(404, {})
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(ValueError, match="HTTP 404"):
            await _ACTION.validate_service_aspect(None, state, None, {})  # type: ignore[arg-type]


async def test_validate_service_raises_when_coordinator_json_missing() -> None:
    state = _state(service_graph_json_url=_URL)
    mock_resp = _mock_response(200, {"other_field": "value"})
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(ValueError, match="coordinator_json"):
            await _ACTION.validate_service_aspect(None, state, None, {})  # type: ignore[arg-type]


async def test_validate_service_raises_when_coordinator_json_not_string() -> None:
    state = _state(service_graph_json_url=_URL)
    mock_resp = _mock_response(200, {"coordinator_json": {"already": "parsed"}})
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(ValueError, match="coordinator_json"):
            await _ACTION.validate_service_aspect(None, state, None, {})  # type: ignore[arg-type]


async def test_validate_service_returns_raw_coordinator_json_string() -> None:
    state = _state(service_graph_json_url=_URL)
    raw = json.dumps(_MINIMAL_COORDINATOR)
    mock_resp = _mock_response(200, {"coordinator_json": raw})
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await _ACTION.validate_service_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["coordinator_json_raw"] == raw
    assert result["service_graph_json_url"] == _URL


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
    state = _state(service_graph_json_url=_URL, coordinator_json_raw=raw)
    result = await _ACTION.parse_service_graph_aspect(None, state, None, {})  # type: ignore[arg-type]
    assert result["service_graph_data"] == _MINIMAL_COORDINATOR
    assert result["service_graph_json_url"] == _URL


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
    state = _state(service_graph_json_url=_URL, service_graph_data=coordinator)
    result = await _ACTION.build_duckdb_graph_summary(None, state, None, {})  # type: ignore[arg-type]
    assert isinstance(result, LoadAOAServiceResult)
    assert result.node_count == 2
    assert result.edge_count == 1
    assert result.service_graph_json_url == _URL


async def test_build_summary_empty_graph() -> None:
    coordinator = {"nodes": [], "edges": []}
    state = _state(service_graph_json_url=_URL, service_graph_data=coordinator)
    result = await _ACTION.build_duckdb_graph_summary(None, state, None, {})  # type: ignore[arg-type]
    assert result.node_count == 0
    assert result.edge_count == 0
