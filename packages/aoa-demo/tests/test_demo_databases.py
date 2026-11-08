# packages/aoa-demo/tests/test_demo_databases.py
"""
The demo is a set of databases: one database of three domains is one resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The storefront, the support desk and inventory kept their data in one database,
each reaching it through a resource of its own. A resource is a database, so that
database is now one resource: ``ShopDatabaseStorage`` lists the entities of all
three domains, and the three old storage modules are gone. Every other demo
storage still keeps its own database and declares its entities with ``@entities``.

The graph shows the merge from the outside: one ``resource_entity`` edge per
listed entity, no ``domain`` edge leaving a resource, and one resource where the
three used to be.
"""

from __future__ import annotations

import importlib.util
import json
from typing import Any

import pytest

from aoa.action_machine.graph.core.exclude_graph_model import excluded_from_graph_model
from aoa.action_machine.intents.entities import EntitiesIntentResolver, entities_info_is_set
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.billing.entities.payment_event_log import PaymentEventLogCoreEntity
from aoa.demo.model.billing.resources.card_network_gateway import CardNetworkGateway
from aoa.demo.model.databases import ShopDatabaseStorage
from aoa.demo.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)
from aoa.demo.model.messaging.entities.msg_recipient_device_seen import RecipientDeviceSeenCoreEntity
from aoa.demo.model.messaging.resources.notification_gateway import NotificationGateway

_SHOP_DATABASE = "ShopDatabaseStorage"
# The union of the three storages: 43 storefront, 5 support and 13 inventory entities.
_SHOP_ENTITIES = 61

# An entity of each domain the shop database now holds.
_ONE_ENTITY_PER_DOMAIN = {
    "StoreDomain": "SalesOrderCoreEntity",
    "SupportDomain": "SupportTicketAggregateCoreEntity",
    "InventoryDomain": "FacilityWarehouseCoreEntity",
}

# Entities of databases that stayed separate; the shop database must not list them.
_OTHER_DATABASES = {
    "ProductCoreEntity",
    "PaymentEventLogCoreEntity",
    "CartMergeTraceCoreEntity",
}

_REMOVED_MODULES = [
    "aoa.demo.model.store.resources.storefront_database_storage",
    "aoa.demo.model.support.resources.storage",
    "aoa.demo.model.inventory.resources.storage",
]


def _graph() -> dict[str, Any]:
    """Return the demo's built graph as the coordinator exports it."""
    return json.loads(build_registered_interchange_coordinator().to_json())


def _short(node_id: str) -> str:
    """The class name a node id ends with."""
    return node_id.rsplit(".", 1)[-1]


def _resource_targets(graph: dict[str, Any], resource_name: str) -> list[str]:
    """The target ids of the ``resource_entity`` edges leaving the resource named ``resource_name``."""
    source_ids = {node["id"] for node in graph["nodes"] if node["type"] == "Resource" and node["label"] == resource_name}
    return [
        edge["target_id"]
        for edge in graph["edges"]
        if edge["type"] == "resource_entity" and edge["source_id"] in source_ids
    ]


def test_the_shop_database_lists_every_entity_of_the_three_domains() -> None:
    """One database, one list: 61 distinct entities, an entity of each domain among them."""
    names = [entity_cls.__name__ for entity_cls in EntitiesIntentResolver.resolve_entities(ShopDatabaseStorage)]

    assert len(names) == _SHOP_ENTITIES
    assert len(set(names)) == _SHOP_ENTITIES
    assert set(_ONE_ENTITY_PER_DOMAIN.values()) <= set(names)
    assert not (_OTHER_DATABASES & set(names))


def test_the_graph_merges_the_three_resources_into_one_database() -> None:
    """The resource reaches each listed entity once and has no domain edge of its own."""
    graph = _graph()
    targets = _resource_targets(graph, _SHOP_DATABASE)
    domain_of = {
        _short(edge["source_id"]): _short(edge["target_id"]) for edge in graph["edges"] if edge["type"] == "domain"
    }
    shop_id = next(node["id"] for node in graph["nodes"] if node["label"] == _SHOP_DATABASE)

    assert len(targets) == _SHOP_ENTITIES
    assert len(set(targets)) == _SHOP_ENTITIES
    assert {domain_of[_short(target)] for target in targets} == set(_ONE_ENTITY_PER_DOMAIN)
    assert not any(edge["type"] == "domain" and edge["source_id"] == shop_id for edge in graph["edges"])


@pytest.mark.parametrize("module_name", _REMOVED_MODULES)
def test_a_removed_storage_module_cannot_be_imported(module_name: str) -> None:
    """The merged database replaces the three modules; none of them has a spec left."""
    try:
        spec = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        spec = None
    assert spec is None


def _demo_resources_descending(root: type[BaseResource]) -> list[type[BaseResource]]:
    """Every loaded demo resource below ``root``, the graph-excluded implementations left out."""
    found: list[type[BaseResource]] = []
    seen: set[type[BaseResource]] = set()

    def walk(cls: type[BaseResource]) -> None:
        for child in cls.__subclasses__():
            if child in seen:
                continue
            seen.add(child)
            if child.__module__.startswith("aoa.demo.model") and not excluded_from_graph_model(child):
                found.append(child)
            walk(child)

    walk(root)
    return found


def test_every_demo_storage_declares_the_entities_of_its_database() -> None:
    """A storage is a database: each concrete demo storage carries its own ``@entities`` list."""
    import_sample_registration_modules()
    storages = [
        resource_cls
        for resource_cls in _demo_resources_descending(BaseResource)
        if issubclass(resource_cls, BaseStorage) and not resource_cls.__name__.endswith("Wrapper")
    ]

    assert storages
    for storage_cls in storages:
        assert entities_info_is_set(storage_cls), storage_cls.__qualname__


def test_the_two_entity_holding_gateways_keep_their_lists() -> None:
    """A gateway that holds entities lists them; the merge did not touch the two."""
    assert EntitiesIntentResolver.resolve_entities(CardNetworkGateway) == (PaymentEventLogCoreEntity,)
    assert EntitiesIntentResolver.resolve_entities(NotificationGateway) == (RecipientDeviceSeenCoreEntity,)
