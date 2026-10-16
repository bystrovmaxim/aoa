# tests/maxitor/test_api_duckdb_graph_holder.py
"""Tests for DuckDBGraphHolder: the application-scoped diagram graph as one ready resource."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI

from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.maxitor.api import app as app_module
from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.duckdb_graph_holder import DuckDBGraphHolder
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

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


def _application_with(domain_id: str) -> tuple[FastAPI, DuckDBGraphResource]:
    """Return an application whose slot already holds a graph for ``domain_id``."""
    app = FastAPI()
    graph = _graph(domain_id)
    app.state.duckdb_graph = graph
    return app, graph


# ─── C-1: identity and construction ──────────────────────────────────────────


def test_create_app_builds_exactly_one_holder(monkeypatch: pytest.MonkeyPatch) -> None:
    """One application builds one holder — the six routes share that one value."""
    built: list[DuckDBGraphHolder] = []
    real_holder = app_module.DuckDBGraphHolder

    def _recording_holder(app: FastAPI) -> DuckDBGraphHolder:
        holder = real_holder(app)
        built.append(holder)
        return holder

    monkeypatch.setattr(app_module, "DuckDBGraphHolder", _recording_holder)
    create_app()

    assert len(built) == 1
    assert isinstance(built[0], BaseResource)


def test_two_applications_build_two_different_holders(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each application gets its own holder, bound to itself and not to a module global."""
    built: list[DuckDBGraphHolder] = []
    real_holder = app_module.DuckDBGraphHolder

    def _recording_holder(app: FastAPI) -> DuckDBGraphHolder:
        holder = real_holder(app)
        built.append(holder)
        return holder

    monkeypatch.setattr(app_module, "DuckDBGraphHolder", _recording_holder)
    create_app()
    create_app()

    assert len(built) == 2
    assert built[0] is not built[1]


def test_a_holder_reads_only_its_own_application_slot() -> None:
    """The holder resolves the slot of the application it was built with, and no other."""
    first_app, _ = _application_with("d.first.Dom")
    second_app, _ = _application_with("d.second.Dom")

    first_rows = DuckDBGraphHolder(first_app).execute_fetch_dicts("SELECT id FROM domain")
    second_rows = DuckDBGraphHolder(second_app).execute_fetch_dicts("SELECT id FROM domain")

    assert first_rows == [{"id": "d.first.Dom"}]
    assert second_rows == [{"id": "d.second.Dom"}]


def test_a_holder_does_not_read_a_second_application() -> None:
    """Each holder answers from its own application, even when the other one is empty."""
    loaded_app, _ = _application_with("d.loaded.Dom")
    empty_app = FastAPI()

    assert DuckDBGraphHolder(loaded_app).execute_fetch_dicts("SELECT id FROM domain") == [
        {"id": "d.loaded.Dom"},
    ]
    assert not hasattr(empty_app.state, "duckdb_graph")


# ─── C-2: the operations ─────────────────────────────────────────────────────


def test_holder_resolves_the_slot_on_every_read() -> None:
    """Repeated reads return the same graph, and a replacement is what the next read sees."""
    app, first = _application_with("d.first.Dom")
    holder = DuckDBGraphHolder(app)

    assert holder.service is first.service
    assert holder.service is first.service

    second = _graph("d.second.Dom")
    app.state.duckdb_graph = second

    assert holder.service is second.service
    assert holder.service is not first.service


def test_execute_fetch_dicts_delegates_to_the_loaded_graph() -> None:
    """The query operation returns what the loaded graph returns, unchanged."""
    app, graph = _application_with("d.x.Dom")
    holder = DuckDBGraphHolder(app)

    sql = "SELECT id, label FROM domain"
    assert holder.execute_fetch_dicts(sql) == graph.execute_fetch_dicts(sql)


def test_holder_exposes_only_the_two_operations_the_routes_use() -> None:
    """Nothing is forwarded: an attribute of the graph the routes never call is unreachable here."""
    app, graph = _application_with("d.x.Dom")
    holder = DuckDBGraphHolder(app)

    assert holder.execute_fetch_dicts("SELECT 1 AS one") == [{"one": 1}]
    assert hasattr(graph, "build_from_json")
    assert not hasattr(holder, "build_from_json")
    assert not hasattr(holder, "_install_database")


# ─── C-4: lifecycle ──────────────────────────────────────────────────────────


def test_holder_has_no_lifecycle_members() -> None:
    """No open, no close, no transaction members — and no wrapper class to hand a nested action."""
    holder = DuckDBGraphHolder(FastAPI())

    for member in ("open", "close", "begin", "commit", "rollback"):
        assert not hasattr(holder, member), member

    assert holder.get_wrapper_class() is None


async def test_holder_reports_no_rollup_support() -> None:
    """An in-memory, read-only graph answers the rollup question with ``False``, not an error."""
    assert await DuckDBGraphHolder(FastAPI()).check_rollup_support() is False


# ─── C-3: the unloaded answer ────────────────────────────────────────────────


def test_reading_before_a_load_names_the_situation() -> None:
    """The refusal says what is wrong and what to do, not what some factory returned."""
    app = FastAPI()
    app.state.duckdb_graph = None

    with pytest.raises(HandleError) as failure:
        _ = DuckDBGraphHolder(app).service

    message = str(failure.value)
    assert "not loaded" in message.lower()
    assert "/api/load" in message


def test_absent_slot_and_empty_slot_answer_alike() -> None:
    """A read before the lifespan has run fails exactly as a read of an empty slot does."""
    started = FastAPI()
    started.state.duckdb_graph = None
    never_started = FastAPI()
    assert not hasattr(never_started.state, "duckdb_graph")

    messages: list[str] = []
    for app in (started, never_started):
        with pytest.raises(HandleError) as failure:
            DuckDBGraphHolder(app).execute_fetch_dicts("SELECT 1 AS one")
        messages.append(str(failure.value))

    assert messages[0] == messages[1]


def test_the_unloaded_failure_is_not_a_type_error_about_a_factory() -> None:
    """The failure is about the situation, never about the shape of a connection value."""
    app = FastAPI()
    app.state.duckdb_graph = None

    with pytest.raises(HandleError) as failure:
        _ = DuckDBGraphHolder(app).service

    assert not isinstance(failure.value, TypeError)
    assert "must return BaseResource" not in str(failure.value)


def test_reading_after_a_load_raises_nothing() -> None:
    """Once a graph is loaded the same read answers, with no failure at all."""
    app, graph = _application_with("d.x.Dom")
    holder = DuckDBGraphHolder(app)

    assert holder.service is graph.service
    assert holder.execute_fetch_dicts("SELECT 1 AS one") == [{"one": 1}]
