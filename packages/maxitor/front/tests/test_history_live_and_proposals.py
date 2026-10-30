# packages/maxitor/front/tests/test_history_live_and_proposals.py
"""Live and the newest version as one point (FR-036), and open pull requests passed to the tab (FR-037)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from maxitor.front.model.core.history_address import version_source
from maxitor.front.model.core.same_graph import same_graph

from tests.fixtures.stand_in_port import GRAPH_A, GRAPH_B, StandInPort, version
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures


def test_the_same_graph_whatever_its_order_spacing_or_a_services_wrapper() -> None:
    """Nodes and edges in another order, other spacing, the graph wrapped as a service answers it: the same graph."""
    document = json.loads(GRAPH_A)
    shuffled = {"edges": list(reversed(document["edges"])), "nodes": list(reversed(document["nodes"])), **{k: v for k, v in document.items() if k not in ("nodes", "edges")}}
    assert same_graph(GRAPH_A, json.dumps(shuffled).encode())
    assert same_graph(json.dumps({"coordinator_json": GRAPH_A.decode()}).encode(), GRAPH_A)
    assert not same_graph(GRAPH_A, GRAPH_B)
    assert not same_graph(b"not json", b"not json")


def test_live_running_the_newest_versions_graph_is_one_point_with_it(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """``live``'s newest version is the graph Live runs: its sha is named; ``live-one``'s newest is another graph: none."""
    newest = port.histories["live"].versions[-1]["sha"]
    assert open_history(maxitor, port, "live").json()["live_same_as"] == newest
    assert open_history(maxitor, port, "live-one").json()["live_same_as"] is None
    assert open_history(maxitor, port, "two").json()["live_same_as"] is None


def test_open_pull_requests_reach_the_tab_with_their_state_and_source(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """The port's open pull requests come through as the port lists them, each with the source its head's graph is read under."""
    proposal = {**version(9, GRAPH_B), "pr": {"number": 158, "title": "Bundles", "body": "", "url": "", "state": "approved"}}
    history = port.histories["live"]
    history.proposals = [proposal]
    history.graphs[proposal["sha"]] = GRAPH_B
    body = open_history(maxitor, port, "live").json()
    assert [(p["sha"], p["pr"]["state"]) for p in body["proposals"]] == [(proposal["sha"], "approved")]
    assert body["proposals"][0]["source"] == version_source(port.name("live"), None, proposal["sha"])
    # A tab reads the open pull request's graph like a version's.
    read = maxitor.get("/api/v1/full-graph", params={"source": body["proposals"][0]["source"]}, headers={"X-Maxitor-History-Key": history.key})
    assert read.status_code == 200, read.text
