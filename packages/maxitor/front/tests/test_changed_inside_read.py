# packages/maxitor/front/tests/test_changed_inside_read.py
"""The read of what changed inside actions (spec 041, FR-024, FR-025): guarded like any comparison, one answer per pair."""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from tests.fixtures.stand_in_port import GRAPH_A, StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures


def _sources(maxitor: TestClient, port: StandInPort) -> dict[str, str]:  # noqa: F811
    """The graph sources of the ``live`` history by version number; version 2 is one the port refuses."""
    opened = open_history(maxitor, port, "live").json()
    return {str(at + 1): version["source"] for at, version in enumerate(opened["versions"])}


def _read(maxitor: TestClient, port: StandInPort, key: str | None = None, **query: str) -> Any:  # noqa: F811
    """The read as the browser makes it."""
    return maxitor.get("/api/v1/compare/changed-inside", params=query, headers={"X-Maxitor-History-Key": key if key is not None else port.histories["live"].key})


def _with_a_result_field_gone(graph: bytes) -> tuple[bytes, str, str]:
    """``graph`` with one result's field removed: the document, the action that owns it, and the field's label."""
    document = json.loads(graph)
    nodes = {node["id"]: node for node in document["nodes"]}
    result_edge = next(e for e in document["edges"] if e["type"] == "generic:result" and any(f["type"] == "field" and f["source_id"] == e["target_id"] for f in document["edges"]))
    field_edge = next(e for e in document["edges"] if e["type"] == "field" and e["source_id"] == result_edge["target_id"])
    document["nodes"] = [node for node in document["nodes"] if node["id"] != field_edge["target_id"]]
    document["edges"] = [edge for edge in document["edges"] if field_edge["target_id"] not in (edge["source_id"], edge["target_id"])]
    return json.dumps(document).encode(), result_edge["source_id"], nodes[field_edge["target_id"]]["label"]


def test_a_field_only_in_b_is_listed_under_its_action(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A = the graph without one result field, B = with it: the owner lists that field as added, under Result."""
    older, action, label = _with_a_result_field_gone(GRAPH_A)
    history = port.histories["live"]
    history.graphs[history.versions[0]["sha"]] = older
    history.graphs[history.versions[2]["sha"]] = GRAPH_A
    sources = _sources(maxitor, port)
    answer = _read(maxitor, port, source=sources["3"], a=sources["1"])
    assert answer.status_code == 200, answer.text
    part = next(part for part in answer.json()["actions"][action] if part["label"] == label)
    assert (part["kind"], part["type"], part["group"], part["status"], part["differences"]) == ("node", "Field", "Result", "added", [])


def test_equal_versions_list_nothing(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Two versions with one graph have no changed part."""
    history = port.histories["live"]
    history.graphs[history.versions[0]["sha"]] = GRAPH_A
    history.graphs[history.versions[2]["sha"]] = GRAPH_A
    sources = _sources(maxitor, port)
    assert _read(maxitor, port, source=sources["3"], a=sources["1"]).json() == {"actions": {}}


def test_a_read_naming_no_second_version_is_refused(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Without ``a`` there is no pair: refused like the other comparison reads."""
    sources = _sources(maxitor, port)
    assert _read(maxitor, port, source=sources["3"]).status_code == 400


def test_a_wrong_key_opens_nothing(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A's read is guarded by its key."""
    sources = _sources(maxitor, port)
    assert _read(maxitor, port, key="wrong", source=sources["3"], a=sources["1"]).status_code in (401, 403, 404)
