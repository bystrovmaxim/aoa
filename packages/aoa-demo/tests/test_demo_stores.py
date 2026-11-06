# tests/test_demo_stores.py
"""The demo's stores: a relation across two databases, and one external service of two domains."""

from __future__ import annotations

import json
from typing import Any

from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator


def _graph() -> dict[str, Any]:
    """Return the demo's graph as the coordinator exports it."""
    return json.loads(build_registered_interchange_coordinator().to_json())


def _short(node_id: str) -> str:
    return node_id.rsplit(".", 1)[-1]


def _targets(graph: dict[str, Any], edge_type: str) -> dict[str, str]:
    """Each source of an ``edge_type`` edge, by short name, mapped to its target's short name."""
    return {_short(edge["source_id"]): _short(edge["target_id"]) for edge in graph["edges"] if edge["type"] == edge_type}


def test_a_chargeback_relates_to_an_order_of_another_database() -> None:
    """The billing warehouse's chargeback ticket points at the shop database's order."""
    graph = _graph()
    stored_in = _targets(graph, "entity_resource")
    source_of = _targets(graph, "resource_data_source")
    relation = next(
        edge
        for edge in graph["edges"]
        if edge["type"] == "entity_relation" and _short(edge["source_id"]) == "ChargebackTicketCoreEntity" and edge["properties"].get("field_name") == "order"
    )
    assert _short(relation["target_id"]) == "SalesOrderCoreEntity"
    assert stored_in["ChargebackTicketCoreEntity"] == "BillingWarehouseStorage"
    assert stored_in["SalesOrderCoreEntity"] == "StorefrontDatabaseStorage"
    assert source_of[stored_in["ChargebackTicketCoreEntity"]] == "BillingWarehouseDataSource"
    assert source_of[stored_in["SalesOrderCoreEntity"]] == "ShopDataSource"


def test_the_card_network_is_one_service_of_two_domains() -> None:
    """Billing and the storefront each reach the card network through one resource of their own."""
    graph = _graph()
    domain_of = _targets(graph, "domain")
    resources = sorted(resource for resource, source in _targets(graph, "resource_data_source").items() if source == "CardNetworkDataSource")
    assert resources == ["CardNetworkGateway", "StorefrontCardGateway"]
    assert sorted(domain_of[resource] for resource in resources) == ["BillingDomain", "StoreDomain"]
