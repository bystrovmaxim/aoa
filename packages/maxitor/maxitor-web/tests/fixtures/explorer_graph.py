"""The test graph of the events explorer (spec 055): every coverage of a domain, every standing of an event, all five kinds."""

from __future__ import annotations

import copy
from typing import Any

#: The five kinds of method and the edge from an action to each.
KINDS = {"RegularAspect": "@regular_aspect", "SummaryAspect": "@summary_aspect", "Compensator": "@compensate", "ErrorHandler": "@on_error", "AccessDecide": "@access_decide"}


def _node(node_id: str, node_type: str, **properties: Any) -> dict[str, Any]:
    """A graph node labelled by the last part of its id: a method by its own name after ``:``."""
    return {"id": node_id, "type": node_type, "label": node_id.rsplit(".", 1)[-1].rsplit(":", 1)[-1], "properties": properties}


def _edge(source: str, edge_type: str, target: str) -> dict[str, Any]:
    """A graph edge of ``edge_type``."""
    return {"id": f"{source}|{edge_type}|{target}", "source_id": source, "target_id": target, "type": edge_type, "relationship": "Association", "is_dag": False, "properties": {}}


def explorer_graph() -> dict[str, Any]:
    """
    Domains: ``d.Orders`` (vocabulary), ``d.Stock`` (vocabulary, no action), ``d.Identity`` (empty vocabulary),
    ``d.Support`` (no vocabulary, emits), ``d.Quiet`` (no events). Events: ``e.Placed`` held by Orders and Stock and
    emitted; ``e.Cancelled`` held and never emitted; ``e.Ticket`` emitted with no vocabulary; ``e.Placed`` also emitted
    by Support's action. ``a.Ping`` emits nothing.
    """
    nodes = [
        _node("d.Orders", "Domain", name="orders", description="", typed_events=True),
        _node("d.Stock", "Domain", name="stock", description="", typed_events=True),
        _node("d.Identity", "Domain", name="identity", description="", typed_events=True),
        _node("d.Support", "Domain", name="support", description="", typed_events=False),
        _node("d.Quiet", "Domain", name="quiet", description="", typed_events=False),
        _node("a.Checkout", "Action", description=""),
        _node("a.Ticket", "Action", description=""),
        _node("a.Ping", "Action", description=""),
        _node("e.Placed", "Event"),
        _node("e.Cancelled", "Event"),
        _node("e.Ticket", "Event"),
        {**_node("e.Placed:order_id", "Field", description="The order", required=True, json_schema_value=False, entity_schema=False), "label": "order_id"},
    ]
    edges = [
        _edge("a.Checkout", "domain", "d.Orders"),
        _edge("a.Ticket", "domain", "d.Support"),
        _edge("a.Ping", "domain", "d.Quiet"),
        _edge("d.Orders", "domain_event", "e.Placed"),
        _edge("d.Orders", "domain_event", "e.Cancelled"),
        _edge("d.Stock", "domain_event", "e.Placed"),
        _edge("e.Placed", "field", "e.Placed:order_id"),
    ]
    for kind, edge_type in KINDS.items():
        method = f"a.Checkout:{kind}"
        properties: dict[str, Any] = {"description": ""}
        if kind == "Compensator":
            properties["target_aspect_name"] = "x"
        nodes.append(_node(method, kind, **properties))
        edges += [_edge("a.Checkout", edge_type, method), _edge(method, "@emits", "e.Placed")]
    nodes += [_node("a.Ticket:open", "SummaryAspect", description=""), _node("a.Ping:pong", "SummaryAspect", description="")]
    edges += [
        _edge("a.Ticket", "@summary_aspect", "a.Ticket:open"),
        _edge("a.Ticket:open", "@emits", "e.Ticket"),
        _edge("a.Ticket:open", "@emits", "e.Placed"),
        _edge("a.Ping", "@summary_aspect", "a.Ping:pong"),
    ]
    return {"nodes": nodes, "edges": edges}


def explorer_graph_b() -> dict[str, Any]:
    """The second version: Orders gains ``e.Refunded`` in its vocabulary, emitted by the checkout's summary."""
    graph = copy.deepcopy(explorer_graph())
    graph["nodes"].append(_node("e.Refunded", "Event"))
    graph["edges"] += [_edge("d.Orders", "domain_event", "e.Refunded"), _edge("a.Checkout:SummaryAspect", "@emits", "e.Refunded")]
    return graph
