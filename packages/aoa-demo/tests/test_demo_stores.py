# tests/test_demo_stores.py
"""The demo's stores: a relation across two databases, and one external service of two domains."""

from __future__ import annotations

import json
from typing import Any

from aoa.action_machine.intents.entities import EntitiesIntentResolver
from aoa.demo.model.billing.entities.payment_event_log import PaymentEventLogCoreEntity
from aoa.demo.model.billing.resources.card_network_gateway import CardNetworkGateway
from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator
from aoa.demo.model.store.resources.card_gateway import StorefrontCardGateway


def _graph() -> dict[str, Any]:
    """Return the demo's graph as the coordinator exports it."""
    return json.loads(build_registered_interchange_coordinator().to_json())


def _short(node_id: str) -> str:
    return node_id.rsplit(".", 1)[-1]


def _targets(graph: dict[str, Any], edge_type: str) -> dict[str, str]:
    """Each source of an ``edge_type`` edge, by short name, mapped to its target's short name."""
    return {
        _short(edge["source_id"]): _short(edge["target_id"]) for edge in graph["edges"] if edge["type"] == edge_type
    }


def test_a_chargeback_relates_to_an_order_of_another_database() -> None:
    """The billing chargeback ticket points at the shop's order, an entity of another domain."""
    graph = _graph()
    domain_of = _targets(graph, "domain")
    relation = next(
        edge
        for edge in graph["edges"]
        if edge["type"] == "entity_relation"
        and _short(edge["source_id"]) == "ChargebackTicketCoreEntity"
        and edge["properties"].get("field_name") == "order"
    )
    assert _short(relation["target_id"]) == "SalesOrderCoreEntity"
    assert domain_of["ChargebackTicketCoreEntity"] == "BillingDomain"
    assert domain_of["SalesOrderCoreEntity"] == "StoreDomain"


def test_the_card_network_gateway_lists_the_payment_events_it_reports() -> None:
    """The billing gateway yields payment events; the storefront gateway yields none and names no domain."""
    graph = _graph()
    domain_of = _targets(graph, "domain")
    assert EntitiesIntentResolver.resolve_entities(CardNetworkGateway) == (PaymentEventLogCoreEntity,)
    assert domain_of["PaymentEventLogCoreEntity"] == "BillingDomain"
    assert EntitiesIntentResolver.resolve_entities(StorefrontCardGateway) == ()
    assert "StorefrontCardGateway" not in domain_of
