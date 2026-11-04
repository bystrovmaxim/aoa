# packages/aoa-action-machine/tests/action_machine/graph/test_cache_in_graph.py
"""
The graph shows the cache: its declarations, and the entities they cache and invalidate.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 11.3 and 11.5 of issue #412. Each cache declaration is a ``Cache`` node of
its action; a ``caches`` edge goes from the action to every tag type of its write,
an ``invalidates`` edge to every tag type of its invalidation; the build refuses an
invalidated type no action caches and a cached type no action invalidates. The
broken cases give the validator their nodes directly, so they never reach a graph
another test builds.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph.validators import cache_tags_validator
from aoa.action_machine.graph.validators.cache_tags_validator import CacheTagsError, validate_cache_tags
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import cache_invalidate, cache_key, cache_write
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ...support.domain_model.domains import OrdersDomain


@entity(description="An order the shop caches", domain=OrdersDomain)
class ShopOrderCoreEntity(BaseCoreEntity):
    """An order."""

    id: str = Field(description="Order id")


@entity(description="An invoice nobody caches", domain=OrdersDomain)
class ShopInvoiceCoreEntity(BaseCoreEntity):
    """An invoice."""

    id: str = Field(description="Invoice id")


class OrderIdParams(BaseParams):
    """One order."""

    order_id: str = Field(description="Order id")


class OrderOutResult(BaseResult):
    """An order id back."""

    order_id: str = Field(description="Order id")


@meta(description="Get one order", domain=OrdersDomain)
@check_roles(GuestRole)
class GetShopOrderAction(BaseAction[OrderIdParams, OrderOutResult]):
    """Caches one order."""

    @cache_key("Order by id")
    async def order_cache_key(self, params: OrderIdParams, box: ToolsBox, connections: Connections) -> str | None:
        return params.order_id

    @cache_write("Keep every order", tags=(ShopOrderCoreEntity,))
    async def order_cache_write(
        self, params: OrderIdParams, box: ToolsBox, connections: Connections, result: OrderOutResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=ShopOrderCoreEntity, key=params.order_id)]

    @summary_aspect("Load")
    async def load_summary(
        self, params: OrderIdParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderOutResult:
        return OrderOutResult(order_id=params.order_id)


@meta(description="Update one order", domain=OrdersDomain)
@check_roles(GuestRole)
class UpdateShopOrderAction(BaseAction[OrderIdParams, OrderOutResult]):
    """Drops what the reader cached, and caches nothing itself."""

    @cache_invalidate("Drop the changed order", tags=(ShopOrderCoreEntity,))
    async def order_cache_invalidate(
        self, params: OrderIdParams, box: ToolsBox, connections: Connections, result: OrderOutResult
    ) -> list[CacheTag] | None:
        return [CacheTag(type=ShopOrderCoreEntity, key=params.order_id)]

    @summary_aspect("Update")
    async def update_summary(
        self, params: OrderIdParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderOutResult:
        return OrderOutResult(order_id=params.order_id)


def _edges(node: ActionGraphNode[Any]) -> list[tuple[str, str]]:
    return [(edge.edge_name, edge.target_node_id) for edge in node.get_all_edges() if "cache" in edge.edge_name or edge.edge_name in ("caches", "invalidates")]


def test_each_declaration_is_a_cache_node_of_its_action() -> None:
    """Case 11.5: the reader has a key and a write node with their kind and description."""
    node = ActionGraphNode(GetShopOrderAction)
    cache_nodes = [companion.to_dict() for companion in node.get_companion_nodes() if companion.node_type == "Cache"]
    action_id = TypeIntrospection.full_qualname(GetShopOrderAction)
    assert cache_nodes == [
        {"id": f"{action_id}:order_cache_key", "type": "Cache", "label": "order_cache_key", "properties": {"kind": "key", "description": "Order by id"}},
        {"id": f"{action_id}:order_cache_write", "type": "Cache", "label": "order_cache_write", "properties": {"kind": "write", "description": "Keep every order"}},
    ]


def test_the_action_is_linked_to_what_it_caches_and_invalidates() -> None:
    """Case 11.5: ``caches`` from the reader, ``invalidates`` from the updater, both to the order."""
    order_id = TypeIntrospection.full_qualname(ShopOrderCoreEntity)
    reader, updater = ActionGraphNode(GetShopOrderAction), ActionGraphNode(UpdateShopOrderAction)
    reader_id = TypeIntrospection.full_qualname(GetShopOrderAction)
    assert _edges(reader) == [
        ("@cache_key", f"{reader_id}:order_cache_key"),
        ("@cache_write", f"{reader_id}:order_cache_write"),
        ("caches", order_id),
    ]
    assert _edges(updater) == [
        ("@cache_invalidate", f"{TypeIntrospection.full_qualname(UpdateShopOrderAction)}:order_cache_invalidate"),
        ("invalidates", order_id),
    ]


def test_the_built_graph_holds_the_cache_and_validates_against_the_protocol() -> None:
    """The coordinator's JSON carries the Cache nodes and the new edges, valid against 1.4."""
    document = json.loads(create_node_graph_coordinator().to_json())
    Draft202012Validator(GRAPH_JSON_SCHEMA).validate(document)
    reader_id = TypeIntrospection.full_qualname(GetShopOrderAction)
    order_id = TypeIntrospection.full_qualname(ShopOrderCoreEntity)
    edges = {(edge["source_id"], edge["type"], edge["target_id"], edge["relationship"]) for edge in document["edges"]}
    assert (reader_id, "caches", order_id, "Association") in edges
    assert (reader_id, "@cache_write", f"{reader_id}:order_cache_write", "Composition") in edges
    assert {"key", "write", "invalidate"} <= {node["properties"]["kind"] for node in document["nodes"] if node["type"] == "Cache"}


def _drop_invoices_action() -> type:
    """An invalidation of a type nobody caches, declared inside a test so no other graph sees it."""

    @meta(description="Drop invoices", domain=OrdersDomain)
    @check_roles(GuestRole)
    class DropInvoiceAction(BaseAction[OrderIdParams, OrderOutResult]):
        @cache_invalidate("Drop invoices", tags=(ShopInvoiceCoreEntity,))
        async def invoice_cache_invalidate(
            self, params: OrderIdParams, box: ToolsBox, connections: Connections, result: OrderOutResult
        ) -> list[CacheTag] | None:
            return [CacheTag(type=ShopInvoiceCoreEntity, key="i1")]

    return DropInvoiceAction


def _keep_invoices_action() -> type:
    """A write of a type nobody invalidates."""

    @meta(description="Keep invoices", domain=OrdersDomain)
    @check_roles(GuestRole)
    class KeepInvoiceAction(BaseAction[OrderIdParams, OrderOutResult]):
        @cache_key("Invoice")
        async def invoice_cache_key(self, params: OrderIdParams, box: ToolsBox, connections: Connections) -> str | None:
            return params.order_id

        @cache_write("Keep invoices", tags=(ShopInvoiceCoreEntity,))
        async def invoice_cache_write(
            self, params: OrderIdParams, box: ToolsBox, connections: Connections, result: OrderOutResult, duration_ms: float
        ) -> list[CacheTag] | None:
            return []

    return KeepInvoiceAction


def _nodes(*actions: type) -> list[SimpleNamespace]:
    return [SimpleNamespace(node_obj=action) for action in actions]


def test_a_dead_invalidation_is_refused() -> None:
    """Case 11.3: an invalidated type no action caches."""
    with pytest.raises(CacheTagsError, match=r"^DropInvoiceAction drops ShopInvoiceCoreEntity, but no action caches it\.$"):
        validate_cache_tags(_nodes(GetShopOrderAction, UpdateShopOrderAction, _drop_invoices_action()))


def test_a_dead_tag_is_refused() -> None:
    """Case 11.3: a cached type no action invalidates."""
    with pytest.raises(CacheTagsError, match=r"^KeepInvoiceAction caches ShopInvoiceCoreEntity, but no action invalidates it"):
        validate_cache_tags(_nodes(GetShopOrderAction, UpdateShopOrderAction, _keep_invoices_action()))


def test_a_writer_and_an_invalidator_of_one_type_pass() -> None:
    """A type cached by one action and invalidated by another is balanced; a node that is not an action is skipped."""
    validate_cache_tags([*_nodes(GetShopOrderAction, UpdateShopOrderAction, _drop_invoices_action(), _keep_invoices_action()), SimpleNamespace(node_obj=ShopOrderCoreEntity)])


def test_the_graph_build_runs_this_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """The coordinator calls the check on every build."""

    def refuse(nodes: Any) -> None:
        raise CacheTagsError("the build asked")

    monkeypatch.setattr(cache_tags_validator, "validate_cache_tags", refuse)
    with pytest.raises(CacheTagsError, match="the build asked"):
        create_node_graph_coordinator()
