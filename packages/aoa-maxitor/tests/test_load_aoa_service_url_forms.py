# packages/aoa-maxitor/tests/test_load_aoa_service_url_forms.py
"""LoadAOAServiceAction accepts service addresses with and without a scheme and port."""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.model import BaseState
from aoa.maxitor.model.core.actions.load_aoa_service_action import (
    LoadAOAServiceAction,
    LoadAOAServiceParams,
)

_ACTION = LoadAOAServiceAction()


def _state(**kwargs: Any) -> BaseState:
    return BaseState(**kwargs)


def _params(raw: str) -> LoadAOAServiceParams:
    return LoadAOAServiceParams(service_url=raw)


async def _normalized(raw: str) -> str:
    validated = await _ACTION.validate_url_aspect(_params(raw), _state(), None, {})
    normalized = await _ACTION.normalize_url_aspect(_params(raw), _state(**validated), None, {})
    return normalized["service_graph_json_url"]


@pytest.mark.asyncio
async def test_scheme_with_port_kept() -> None:
    assert await _normalized("http://demo:8100") == "http://demo:8100/examples/model/graph-json"
    assert await _normalized("https://demo:8100") == "https://demo:8100/examples/model/graph-json"


@pytest.mark.asyncio
async def test_scheme_without_port_kept() -> None:
    assert await _normalized("https://dev.demo.aoa.run") == "https://dev.demo.aoa.run/examples/model/graph-json"


@pytest.mark.asyncio
async def test_bare_host_with_port_defaults_to_http() -> None:
    assert await _normalized("demo:8100") == "http://demo:8100/examples/model/graph-json"
    assert await _normalized("127.0.0.1:8100") == "http://127.0.0.1:8100/examples/model/graph-json"


@pytest.mark.asyncio
async def test_bare_host_without_port_defaults_to_https() -> None:
    assert await _normalized("dev.demo.aoa.run") == "https://dev.demo.aoa.run/examples/model/graph-json"


@pytest.mark.asyncio
async def test_explicit_path_is_used_as_is() -> None:
    assert await _normalized("demo:8100/examples/model/graph-json") == "http://demo:8100/examples/model/graph-json"
    assert (
        await _normalized("https://dev.demo.aoa.run/examples/model/graph-json")
        == "https://dev.demo.aoa.run/examples/model/graph-json"
    )
