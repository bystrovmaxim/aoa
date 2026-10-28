# packages/maxitor/tests/test_api_duckdb_graph_holder.py
"""Tests for DuckDBGraphHolder: the holder answers from the graph bound to the request it serves."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI
from maxitor.viewer.api import app as app_module
from maxitor.viewer.api.app import create_app
from maxitor.viewer.api.duckdb_graph_holder import DuckDBGraphHolder
from maxitor.viewer.api.graph_source_middleware import bound_graph_entry
from maxitor.viewer.api.graph_store import GraphEntry
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources.base_resource import BaseResource

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _payload(domain_id: str) -> dict[str, Any]:
    """Return a minimal coordinator payload holding one domain."""
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": domain_id,
                "label": domain_id,
                "type": "Domain",
                "properties": {"name": domain_id, "description": ""},
            },
        ],
        "edges": [],
    }


def _graph(domain_id: str) -> DuckDBGraphResource:
    """Return a freshly built graph holding one domain."""
    return DuckDBGraphResource.build_from_json(_payload(domain_id))


def _entry(source: str, graph: DuckDBGraphResource) -> GraphEntry:
    """Return the entry a request for ``source`` would be bound to."""
    return GraphEntry(source=source, graph=graph, sidebar=None, last_read=0.0)


# ─── C-1: construction ───────────────────────────────────────────────────────


def test_create_app_builds_exactly_one_holder(monkeypatch: pytest.MonkeyPatch) -> None:
    """One application builds one holder — the six routes share that one value."""
    built: list[DuckDBGraphHolder] = []
    real_holder = app_module.DuckDBGraphHolder

    def _recording_holder() -> DuckDBGraphHolder:
        holder = real_holder()
        built.append(holder)
        return holder

    monkeypatch.setattr(app_module, "DuckDBGraphHolder", _recording_holder)
    create_app()

    assert len(built) == 1
    assert isinstance(built[0], BaseResource)


def test_two_applications_build_two_different_holders(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each application gets its own holder, and no holder keeps a graph of its own."""
    built: list[DuckDBGraphHolder] = []
    real_holder = app_module.DuckDBGraphHolder

    def _recording_holder() -> DuckDBGraphHolder:
        holder = real_holder()
        built.append(holder)
        return holder

    monkeypatch.setattr(app_module, "DuckDBGraphHolder", _recording_holder)
    create_app()
    create_app()

    assert len(built) == 2
    assert built[0] is not built[1]


# ─── C-2: the request's graph ────────────────────────────────────────────────


def test_a_bound_holder_resolves_that_entry() -> None:
    """Inside a binding the holder answers from the entry bound to it."""
    graph = _graph("d.first.Dom")
    holder = DuckDBGraphHolder()

    with bound_graph_entry(_entry("https://a.test/graph-json", graph)):
        assert holder.service is graph.service
        assert holder.execute_fetch_dicts("SELECT id FROM domain") == [{"id": "d.first.Dom"}]


def test_two_bindings_in_sequence_give_two_graphs() -> None:
    """The holder keeps nothing between requests: the next binding is what the next read sees."""
    first = _graph("d.first.Dom")
    second = _graph("d.second.Dom")
    holder = DuckDBGraphHolder()

    with bound_graph_entry(_entry("https://a.test/graph-json", first)):
        assert holder.execute_fetch_dicts("SELECT id FROM domain") == [{"id": "d.first.Dom"}]

    with bound_graph_entry(_entry("https://b.test/graph-json", second)):
        assert holder.execute_fetch_dicts("SELECT id FROM domain") == [{"id": "d.second.Dom"}]


async def test_bindings_do_not_leak_between_tasks() -> None:
    """Two concurrent reads, each bound to its own graph, never see each other's entry."""
    holder = DuckDBGraphHolder()
    first = _graph("d.first.Dom")
    second = _graph("d.second.Dom")

    async def read(graph: DuckDBGraphResource) -> list[dict[str, Any]]:
        with bound_graph_entry(_entry("https://x.test/graph-json", graph)):
            await asyncio.sleep(0)
            return holder.execute_fetch_dicts("SELECT id FROM domain")

    assert await asyncio.gather(read(first), read(second)) == [[{"id": "d.first.Dom"}], [{"id": "d.second.Dom"}]]


def test_a_holder_does_not_read_application_state() -> None:
    """A graph in the application's store is irrelevant: only the binding the request carries counts."""
    app = FastAPI()
    app.state.graph_store = object()
    bound = _graph("d.bound.Dom")

    with bound_graph_entry(_entry("https://a.test/graph-json", bound)):
        assert DuckDBGraphHolder().execute_fetch_dicts("SELECT id FROM domain") == [{"id": "d.bound.Dom"}]


# ─── C-3: the unbound answer ────────────────────────────────────────────────


def test_reading_outside_a_binding_names_the_missing_binding() -> None:
    """The refusal says the request named no source; it does not send the caller to POST /api/load."""
    with pytest.raises(HandleError) as failure:
        _ = DuckDBGraphHolder().service

    message = str(failure.value)
    assert "bound" in message.lower()
    assert "source" in message.lower()
    assert "/api/load" not in message


def test_the_binding_is_reset_after_its_block() -> None:
    """After the block the holder refuses again: the binding belonged to that request only."""
    graph = _graph("d.x.Dom")
    holder = DuckDBGraphHolder()

    with bound_graph_entry(_entry("https://a.test/graph-json", graph)):
        assert holder.service is graph.service

    with pytest.raises(HandleError):
        _ = holder.service


# ─── C-4: the surface and the lifecycle ─────────────────────────────────────


def test_execute_fetch_dicts_delegates_to_the_bound_graph() -> None:
    """The query operation returns what the bound graph returns, unchanged."""
    graph = _graph("d.x.Dom")
    holder = DuckDBGraphHolder()

    with bound_graph_entry(_entry("https://a.test/graph-json", graph)):
        sql = "SELECT id, label FROM domain"
        assert holder.execute_fetch_dicts(sql) == graph.execute_fetch_dicts(sql)


def test_holder_exposes_only_the_two_operations_the_routes_use() -> None:
    """Nothing is forwarded: an attribute of the graph the routes never call is unreachable here."""
    graph = _graph("d.x.Dom")
    holder = DuckDBGraphHolder()

    with bound_graph_entry(_entry("https://a.test/graph-json", graph)):
        assert holder.execute_fetch_dicts("SELECT 1 AS one") == [{"one": 1}]

    assert hasattr(graph, "build_from_json")
    assert not hasattr(holder, "build_from_json")
    assert not hasattr(holder, "_install_database")


def test_holder_has_no_lifecycle_members() -> None:
    """No open, no close, no transaction members — and no wrapper class to hand a nested action."""
    holder = DuckDBGraphHolder()

    for member in ("open", "close", "begin", "commit", "rollback"):
        assert not hasattr(holder, member), member

    assert holder.get_wrapper_class() is None


async def test_holder_reports_no_rollup_support() -> None:
    """An in-memory, read-only graph answers the rollup question with ``False``, not an error."""
    assert await DuckDBGraphHolder().check_rollup_support() is False
