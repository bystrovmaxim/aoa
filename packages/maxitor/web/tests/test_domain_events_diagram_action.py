"""Tests for the events diagram (spec 053): bands, the five kinds of method, and older documents."""

from __future__ import annotations

from typing import Any

import pytest
from maxitor.web.model.diagrams.actions.domain_events_diagram_action import events_diagram
from maxitor.web.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_KINDS = {"RegularAspect": "@regular_aspect", "SummaryAspect": "@summary_aspect", "Compensator": "@compensate", "ErrorHandler": "@on_error", "AccessDecide": "@access_decide"}


def _node(node_id: str, node_type: str, **properties: Any) -> dict[str, Any]:
    return {"id": node_id, "type": node_type, "label": node_id.rsplit(".", 1)[-1], "properties": properties}


def _edge(source: str, edge_type: str, target: str) -> dict[str, Any]:
    return {"source_id": source, "target_id": target, "type": edge_type, "relationship": "Association", "is_dag": False, "properties": {}}


def _payload() -> dict[str, Any]:
    """Three modes: ``d.Typed`` with a vocabulary, ``d.Open`` emitting without one, ``d.Quiet`` with no events."""
    nodes = [
        _node("d.Typed", "Domain", name="typed", description="", typed_events=True),
        _node("d.Open", "Domain", name="open", description="", typed_events=False),
        _node("d.Quiet", "Domain", name="quiet", description="", typed_events=False),
        _node("a.Pay", "Action", description=""),
        _node("a.Ship", "Action", description=""),
        _node("e.Paid", "Event"),
        _node("e.Idle", "Event"),
        _node("e.Shipped", "Event"),
        {**_node("e.Paid:total", "Field", description="The sum", required=True, json_schema_value=False, entity_schema=False), "label": "total"},
    ]
    edges = [
        _edge("a.Pay", "domain", "d.Typed"),
        _edge("a.Ship", "domain", "d.Open"),
        _edge("d.Typed", "domain_event", "e.Paid"),
        _edge("d.Typed", "domain_event", "e.Idle"),
        _edge("e.Paid", "field", "e.Paid:total"),
    ]
    for kind, edge_type in _KINDS.items():
        method = f"a.Pay:{kind}"
        properties = {"description": ""}
        if kind == "Compensator":
            properties["target_aspect_name"] = "x"
        nodes.append(_node(method, kind, **properties))
        edges += [_edge("a.Pay", edge_type, method), _edge(method, "@emits", "e.Paid")]
    nodes.append(_node("a.Pay:quiet", "RegularAspect", description=""))
    nodes.append(_node("a.Ship:go", "RegularAspect", description=""))
    edges += [_edge("a.Pay", "@regular_aspect", "a.Pay:quiet"), _edge("a.Ship", "@regular_aspect", "a.Ship:go"), _edge("a.Ship:go", "@emits", "e.Shipped"), _edge("a.Ship:go", "@emits", "e.Paid")]
    return {"nodes": nodes, "edges": edges}


def _domain(duck: DuckDBGraphResource, domain_id: str) -> dict[str, Any]:
    return dict(duck.execute_fetch_dicts("SELECT id, label, name, typed_events FROM domain WHERE id = ?", [domain_id])[0])


@pytest.fixture
def duck() -> DuckDBGraphResource:
    return DuckDBGraphResource.build_from_json(_payload())


def test_a_vocabulary_gives_two_bands(duck: DuckDBGraphResource) -> None:
    diagram = events_diagram(duck, _domain(duck, "d.Typed"))
    assert diagram["domain"]["typed_events"] is True
    assert {e["id"]: e["band"] for e in diagram["events"]} == {"e.Paid": "in_vocabulary", "e.Idle": "not_emitted"}


def test_no_vocabulary_gives_one_band(duck: DuckDBGraphResource) -> None:
    diagram = events_diagram(duck, _domain(duck, "d.Open"))
    assert diagram["domain"]["typed_events"] is False
    assert {e["band"] for e in diagram["events"]} == {"emitted"}


def test_a_domain_with_no_events_is_empty(duck: DuckDBGraphResource) -> None:
    diagram = events_diagram(duck, _domain(duck, "d.Quiet"))
    assert (diagram["actions"], diagram["methods"], diagram["events"], diagram["edges"]) == ([], [], [], [])


def test_all_five_kinds_are_drawn_and_a_method_with_no_event_is_not(duck: DuckDBGraphResource) -> None:
    diagram = events_diagram(duck, _domain(duck, "d.Typed"))
    assert {m["kind"] for m in diagram["methods"]} == set(_KINDS)
    assert "a.Pay:quiet" not in {m["id"] for m in diagram["methods"]}
    assert {e["id"] for e in diagram["edges"] if e["edge_kind"] == "emits"} == {f"a.Pay:{k}|@emits|e.Paid" for k in _KINDS}
    assert "a.Pay|@compensate|a.Pay:Compensator" in {e["id"] for e in diagram["edges"]}


def test_an_event_knows_every_producer_and_domain(duck: DuckDBGraphResource) -> None:
    paid = next(e for e in events_diagram(duck, _domain(duck, "d.Typed"))["events"] if e["id"] == "e.Paid")
    assert len(paid["methods"]) == 6
    assert paid["domains"] == [{"id": "d.Typed", "label": "Typed", "in_vocabulary": True}, {"id": "d.Open", "label": "Open", "in_vocabulary": False}]
    assert paid["fields"] == [{"name": "total", "type": "", "description": "The sum"}]


def test_all_domains_draw_each_event_once(duck: DuckDBGraphResource) -> None:
    diagram = events_diagram(duck, None)
    assert sorted(e["id"] for e in diagram["events"]) == ["e.Idle", "e.Paid", "e.Shipped"]
    assert diagram["domain"]["typed_events"] is None


def test_a_domain_card_says_its_vocabulary_on_the_table(duck: DuckDBGraphResource) -> None:
    assert _domain(duck, "d.Typed")["typed_events"] is True
    assert _domain(duck, "d.Open")["typed_events"] is False


def test_a_document_older_than_events_opens() -> None:
    old = _payload()
    old["nodes"] = [{**n, "properties": {k: v for k, v in n["properties"].items() if k != "typed_events"}} for n in old["nodes"] if n["type"] == "Domain"]
    old["edges"] = []
    duck = DuckDBGraphResource.build_from_json(old)
    assert events_diagram(duck, _domain(duck, "d.Quiet"))["events"] == []
