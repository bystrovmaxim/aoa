# packages/maxitor/front/tests/test_compare_reads.py
"""The two comparison reads (spec 038, FR-018 – FR-021): both versions guarded like any read, computed once per pair, recomputed when Live changes, no key in a log."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.graph_compare import Status, compare

from tests.fixtures.stand_in_port import GRAPH_A, GRAPH_B, StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures


def _sources(maxitor: TestClient, port: StandInPort) -> dict[str, str]:  # noqa: F811
    """The graph sources of the ``live`` history: its three versions by number, and Live."""
    opened = open_history(maxitor, port, "live").json()
    found = {str(at + 1): version["source"] for at, version in enumerate(opened["versions"])}
    return {**found, "live": opened["live"]}


def _read(maxitor: TestClient, port: StandInPort, path: str, key: str | None = None, **query: str) -> Any:  # noqa: F811
    """A comparison read as the browser makes it: the key in the header, never in the query."""
    return maxitor.get(f"/api/v1/{path}", params=query, headers={"X-Maxitor-History-Key": key if key is not None else port.histories["live"].key})


def test_the_statuses_and_counts_of_two_versions(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A = version 1 (the port's graph), B = version 3 (Maxitor's): what changed, as ``compare`` says, unchanged left out."""
    sources = _sources(maxitor, port)
    answer = _read(maxitor, port, "compare", source=sources["3"], a=sources["1"])
    assert answer.status_code == 200, answer.text
    expected = compare(json.loads(GRAPH_B), json.loads(GRAPH_A))
    body = answer.json()
    assert body["counts"]["nodes"] == {"added": expected.node_counts.added, "removed": expected.node_counts.removed, "changed": expected.node_counts.changed}
    assert body["nodes"] == {node_id: item.status.value for node_id, item in expected.nodes.items() if item.status is not Status.UNCHANGED}
    assert body["edges"] == {edge_id: item.status.value for edge_id, item in expected.edges.items() if item.status is not Status.UNCHANGED}
    assert "unchanged" not in set(body["nodes"].values()) | set(body["edges"].values())


def _edited(graph: bytes) -> bytes:
    """``graph`` with one node's label and a nested property changed, and one edge retargeted: what a release does."""
    document = json.loads(graph)
    node = document["nodes"][0]
    node["label"] = node["label"] + " (old)"
    node["properties"]["nested"] = {"deep": {"value": 1}}
    edge = document["edges"][0]
    edge["target_id"] = document["nodes"][1]["id"]
    return json.dumps(document).encode()


def test_one_elements_differences_with_both_values(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A changed node gives every difference by path, before and after; an id in neither version is not found."""
    older = _edited(GRAPH_A)
    port.histories["live"].graphs[port.histories["live"].versions[0]["sha"]] = older
    sources = _sources(maxitor, port)
    expected = compare(json.loads(older), json.loads(GRAPH_A))
    assert expected.node_counts.changed == 1
    changed = next(node_id for node_id, item in expected.nodes.items() if item.status is Status.CHANGED)
    answer = _read(maxitor, port, "compare-element", source=sources["3"], a=sources["1"], kind="node", id=changed)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "changed"
    assert body["differences"] == [
        {"path": list(d.path), "change": d.change.value, **({} if d.change == "added" else {"before": d.before}), **({} if d.change == "removed" else {"after": d.after})}
        for d in expected.nodes[changed].differences
    ]
    missing = _read(maxitor, port, "compare-element", source=sources["3"], a=sources["1"], kind="edge", id="no|such|edge")
    assert (missing.status_code, missing.json()) == (404, {"detail": "not found"})


def test_a_comparison_read_must_name_its_older_version(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """No ``a``: the middleware's 400, word for word."""
    sources = _sources(maxitor, port)
    answer = _read(maxitor, port, "compare", source=sources["3"])
    assert (answer.status_code, answer.json()) == (400, {"detail": "Missing query parameter 'a': name the older version this comparison is from."})


def test_the_older_version_is_guarded_like_any_read(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A wrong key is not found, a refused A gives the port's reason — before B is even acquired."""
    sources = _sources(maxitor, port)
    held_before = maxitor.app.state.graph_store.held  # type: ignore[attr-defined]
    wrong = _read(maxitor, port, "compare", key="wrong-key", source=sources["3"], a=sources["1"])
    assert (wrong.status_code, wrong.json()) == (404, {"detail": "not found"})
    refused = _read(maxitor, port, "compare", source=sources["3"], a=sources["2"])
    assert refused.status_code == 422
    assert "'id' is a required property" in refused.json()["detail"]
    assert maxitor.app.state.graph_store.held == held_before  # type: ignore[attr-defined]


def test_a_pair_is_compared_once_whoever_reads_it(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Two readers, two reads each, of both reads: one computation (SC-009)."""
    sources = _sources(maxitor, port)
    store = maxitor.app.state.comparisons  # type: ignore[attr-defined]
    for _ in range(2):
        assert _read(maxitor, port, "compare", source=sources["3"], a=sources["1"]).status_code == 200
        assert _read(maxitor, port, "compare-element", source=sources["3"], a=sources["1"], kind="node", id="x").status_code == 404
    assert store.computed == 1


def test_live_as_b_is_compared_again_when_live_changes(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """B = Live: once Live serves another graph and is rebuilt, the next read gives the new comparison (FR-020)."""
    sources = _sources(maxitor, port)
    first = _read(maxitor, port, "compare", source=sources["live"], a=sources["1"]).json()
    assert first == _read(maxitor, port, "compare", source=sources["live"], a=sources["1"]).json()
    port.live_body = GRAPH_B
    maxitor.portal.call(maxitor.app.state.graph_store.reload, sources["live"])  # type: ignore[attr-defined, union-attr]
    second = _read(maxitor, port, "compare", source=sources["live"], a=sources["1"]).json()
    assert second["counts"] == {"nodes": {"added": 0, "removed": 0, "changed": 0}, "edges": {"added": 0, "removed": 0, "changed": 0}}
    assert first != second
    assert maxitor.app.state.comparisons.computed == 2  # type: ignore[attr-defined]


def test_no_key_and_no_address_in_any_log_line(maxitor: TestClient, port: StandInPort, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]) -> None:  # noqa: F811
    """Every comparison read and refusal: the key and the version sources appear in no log line and no error body."""
    caplog.set_level(logging.DEBUG)
    sources = _sources(maxitor, port)
    bodies = [
        _read(maxitor, port, "compare", source=sources["3"], a=sources["1"]).text,
        _read(maxitor, port, "compare-element", source=sources["3"], a=sources["1"], kind="node", id="x").text,
        _read(maxitor, port, "compare", key="wrong", source=sources["3"], a=sources["1"]).text,
        _read(maxitor, port, "compare", source=sources["3"], a=sources["2"]).text,
    ]
    # Maxitor's own lines — the actions' box — go to standard output; the rest of the stack to logging.
    printed = capsys.readouterr()
    assert "Comparison computed in" in printed.out
    logged = caplog.text + printed.out + printed.err + "\n".join(bodies)
    assert port.histories["live"].key not in logged
    # httpx names every URL it requests at DEBUG; a version's URL carries no key, and that is #289's port client.
    ours = "\n".join(record.getMessage() for record in caplog.records if not record.name.startswith(("httpx", "httpcore"))) + printed.out + printed.err + "\n".join(bodies)
    for source in (sources["1"], sources["2"], sources["3"]):
        assert source not in ours
    assert all(port.histories["live"].key not in request for request in port.requests)
