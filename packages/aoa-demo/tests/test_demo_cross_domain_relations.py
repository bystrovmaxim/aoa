"""
The demo's entities are linked across domains, so tools that draw the model meet the hard cases.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A model whose domains never point at each other draws as islands: an ERD of one
domain has no neighbour to bring in, folded domains have no line between them,
and a filter has nothing to cut. The demo therefore keeps relations between
entities of different domains — a support participant, a courier attempt and an
audit event point at the identity's person; an order line and a clinical SKU at
the catalog's product; shipments, freight legs and telemetry at a warehouse;
analytics and settlement at billing. This test reads the demo's graph file and
fails if those relations thin out again.
"""

from __future__ import annotations

import json
from pathlib import Path

GRAPH = Path(__file__).resolve().parents[1] / "graph.json"
#: How many relations between entities of different domains the demo keeps at least, and over how many domains.
LEAST_CROSS_RELATIONS = 10
LEAST_LINKED_DOMAINS = 8


def _cross_domain_relations() -> list[tuple[str, str]]:
    """Every ``entity_relation`` whose two entities lie in different domains, as a pair of domains."""
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    domain_of = {
        edge["source_id"]: edge["target_id"]
        for edge in graph["edges"]
        if nodes.get(edge["source_id"], {}).get("type") == "Entity"
        and nodes.get(edge["target_id"], {}).get("type") == "Domain"
    }
    return [
        (domain_of[edge["source_id"]], domain_of[edge["target_id"]])
        for edge in graph["edges"]
        if edge["type"] == "entity_relation"
        and edge["source_id"] in domain_of
        and edge["target_id"] in domain_of
        and domain_of[edge["source_id"]] != domain_of[edge["target_id"]]
    ]


def test_entities_of_different_domains_are_linked() -> None:
    """The demo keeps enough relations across domains to draw neighbours, bundles between folded domains and 1-hop."""
    pairs = _cross_domain_relations()
    assert len(pairs) >= LEAST_CROSS_RELATIONS, pairs


def test_the_links_across_domains_reach_most_domains() -> None:
    """The relations do not all meet in one pair of domains: most domains take part in at least one."""
    domains = {domain for pair in _cross_domain_relations() for domain in pair}
    assert len(domains) >= LEAST_LINKED_DOMAINS, sorted(domains)
