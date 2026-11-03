"""Tests for the events explorer's data (spec 055): coverages, standings, the five kinds, and older documents."""

from __future__ import annotations

from typing import Any

import pytest
from maxitor.web.model.diagrams.actions.events_explorer_action import events_explorer
from maxitor.web.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

from tests.fixtures.explorer_graph import KINDS, explorer_graph, explorer_graph_b


@pytest.fixture
def answer() -> dict[str, Any]:
    return events_explorer(DuckDBGraphResource.build_from_json(explorer_graph()))


def test_every_domain_comes_with_its_vocabulary_flag_an_empty_one_too(answer: dict[str, Any]) -> None:
    assert {d["id"]: d["vocabulary"] for d in answer["domains"]} == {"d.Identity": True, "d.Orders": True, "d.Quiet": False, "d.Stock": True, "d.Support": False}


def test_every_action_comes_with_its_domain_those_without_events_too(answer: dict[str, Any]) -> None:
    assert {a["id"]: a["domain_id"] for a in answer["actions"]} == {"a.Checkout": "d.Orders", "a.Ping": "d.Quiet", "a.Ticket": "d.Support"}


def test_vocabularies_are_pairs_and_an_event_may_be_in_two(answer: dict[str, Any]) -> None:
    assert answer["holds"] == [{"domain_id": "d.Orders", "event_id": "e.Cancelled"}, {"domain_id": "d.Orders", "event_id": "e.Placed"}, {"domain_id": "d.Stock", "event_id": "e.Placed"}]


def test_each_emitting_method_names_its_action_kind_and_event(answer: dict[str, Any]) -> None:
    checkout = [e for e in answer["emits"] if e["action_id"] == "a.Checkout"]
    assert {e["kind"] for e in checkout} == set(KINDS)
    assert {e["event_id"] for e in checkout} == {"e.Placed"}
    assert {(e["method"], e["event_id"]) for e in answer["emits"] if e["action_id"] == "a.Ticket"} == {("open", "e.Placed"), ("open", "e.Ticket")}
    assert not [e for e in answer["emits"] if e["action_id"] == "a.Ping"]


def test_events_carry_their_fields(answer: dict[str, Any]) -> None:
    fields = {e["id"]: e["fields"] for e in answer["events"]}
    assert fields["e.Placed"] == [{"name": "order_id", "type": "", "description": "The order"}]
    assert fields["e.Cancelled"] == []


def test_every_list_is_sorted_so_one_graph_gives_one_answer(answer: dict[str, Any]) -> None:
    for name in ("domains", "actions", "events"):
        ids = [row["id"] for row in answer[name]]
        assert ids == sorted(ids), name
    keys = [(e["action_id"], e["method_id"], e["event_id"]) for e in answer["emits"]]
    assert keys == sorted(keys)


def test_the_second_version_adds_one_event_and_one_emitting_link(answer: dict[str, Any]) -> None:
    newer = events_explorer(DuckDBGraphResource.build_from_json(explorer_graph_b()))
    assert {e["id"] for e in newer["events"]} - {e["id"] for e in answer["events"]} == {"e.Refunded"}
    assert len(newer["emits"]) == len(answer["emits"]) + 1


def test_a_document_older_than_events_opens_with_domains_and_actions() -> None:
    old = explorer_graph()
    old["nodes"] = [{**n, "properties": {k: v for k, v in n["properties"].items() if k != "typed_events"}} for n in old["nodes"] if n["type"] in ("Domain", "Action")]
    old["edges"] = [e for e in old["edges"] if e["type"] == "domain"]
    answer = events_explorer(DuckDBGraphResource.build_from_json(old))
    assert (answer["events"], answer["holds"], answer["emits"]) == ([], [], [])
    assert len(answer["domains"]) == 5 and len(answer["actions"]) == 3
    assert not any(d["vocabulary"] for d in answer["domains"])
