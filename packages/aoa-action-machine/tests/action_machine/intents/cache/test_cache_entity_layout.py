# packages/aoa-action-machine/tests/action_machine/intents/cache/test_cache_entity_layout.py
"""
``layout=CacheLayout.ENTITIES`` and ``@cache_entity_key``: the rules of the mode.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 12.7, points 1–3, of issue #413. The layout and the entity key come together;
the entity key is a declaration like the others; the Result needs a field typed by
an entity with an ``id``; the graph shows the entity key and links the write to the
entity types it stores, and the dead-tag check counts them. Refused classes are
declared inside their tests, so no other graph sees them.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.exceptions.aspect_signature_error import AspectSignatureError
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph.validators.cache_tags_validator import CacheTagsError, validate_cache_tags
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import CacheLayout, cache_entity_key, cache_invalidate, cache_key, cache_write
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.stub_params import StubParams
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

from ....support.domain_model.domains import OrdersDomain, OrdersStorage


@entity(description="An order of the layout tests", resource=OrdersStorage)
class LayoutOrderCoreEntity(BaseCoreEntity):
    """An order with an id."""

    id: str = Field(description="Order id")
    total: float = Field(description="Total")


@entity(description="A customer of the layout tests", resource=OrdersStorage)
class LayoutCustomerCoreEntity(BaseCoreEntity):
    """Owns lists of orders."""

    id: str = Field(description="Customer id")


class OrdersListResult(BaseResult):
    """A list of orders and a count."""

    orders: list[LayoutOrderCoreEntity] = Field(description="Orders")
    total_count: int = Field(description="How many")


@meta(description="Lists orders, entity by entity", domain=OrdersDomain)
@check_roles(GuestRole)
class ListLayoutOrdersAction(BaseAction[StubParams, OrdersListResult]):
    """The accepted form of the mode."""

    @cache_key("The customer's orders")
    async def orders_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "customer:c1"

    @cache_entity_key("One order, as a row")
    async def order_cache_entity_key(
        self, params: StubParams, box: ToolsBox, connections: Connections, entity: LayoutOrderCoreEntity
    ) -> str:
        return f"order:{entity.id}:row"

    @cache_write("Keep the list order by order", tags=(LayoutCustomerCoreEntity,), layout=CacheLayout.ENTITIES)
    async def orders_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: OrdersListResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=LayoutCustomerCoreEntity, key="c1")]

    @summary_aspect("List")
    async def list_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrdersListResult:
        return OrdersListResult(orders=[], total_count=0)


@meta(description="Drops orders and customers' lists", domain=OrdersDomain)
@check_roles(GuestRole)
class DropLayoutAction(BaseAction[StubParams, OrdersListResult]):
    """Invalidates both types the list caches."""

    @cache_invalidate("Drop", tags=(LayoutOrderCoreEntity, LayoutCustomerCoreEntity))
    async def layout_cache_invalidate(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: OrdersListResult
    ) -> list[CacheTag] | None:
        return []

    @summary_aspect("Drop")
    async def drop_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrdersListResult:
        return OrdersListResult(orders=[], total_count=0)


def test_the_graph_shows_the_entity_key_and_links_the_stored_entity_type() -> None:
    """12.7.3: an ``entity_key`` node, and ``caches`` to the declared tag and to the entity type stored."""
    node = ActionGraphNode(ListLayoutOrdersAction)
    kinds = [companion.properties["kind"] for companion in node.get_companion_nodes() if companion.node_type == "Cache"]
    edges = {(edge.edge_name, edge.target_node_id) for edge in node.get_all_edges()}
    assert kinds == ["key", "write", "entity_key"]
    assert ("caches", TypeIntrospection.full_qualname(LayoutCustomerCoreEntity)) in edges
    assert ("caches", TypeIntrospection.full_qualname(LayoutOrderCoreEntity)) in edges
    assert ("@cache_entity_key", f"{TypeIntrospection.full_qualname(ListLayoutOrdersAction)}:order_cache_entity_key") in edges


def test_the_dead_tag_check_counts_the_stored_entity_type() -> None:
    """12.7.3: nobody dropping the order type makes the list's entity entries dead tags."""
    validate_cache_tags([SimpleNamespace(node_obj=ListLayoutOrdersAction), SimpleNamespace(node_obj=DropLayoutAction)])
    with pytest.raises(CacheTagsError, match="ListLayoutOrdersAction caches LayoutOrderCoreEntity, but no action invalidates it"):

        @meta(description="Drops customers' lists only", domain=OrdersDomain)
        @check_roles(GuestRole)
        class DropListsOnlyAction(BaseAction[StubParams, OrdersListResult]):
            @cache_invalidate("Drop lists", tags=(LayoutCustomerCoreEntity,))
            async def lists_cache_invalidate(
                self, params: StubParams, box: ToolsBox, connections: Connections, result: OrdersListResult
            ) -> list[CacheTag] | None:
                return []

        validate_cache_tags([SimpleNamespace(node_obj=ListLayoutOrdersAction), SimpleNamespace(node_obj=DropListsOnlyAction)])


async def _key(self: Any, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
    return "k"


def test_the_layout_without_an_entity_key_is_refused() -> None:
    """12.7.2: one without the other does nothing."""
    with pytest.raises(DeclarationStructureError, match=r"writes with layout=CacheLayout\.ENTITIES without @cache_entity_key"):

        class LoneLayoutAction(BaseAction[StubParams, OrdersListResult]):
            @cache_key("Key")
            async def lone_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
                return "k"

            @cache_write("Write", layout=CacheLayout.ENTITIES)
            async def lone_cache_write(
                self, params: StubParams, box: ToolsBox, connections: Connections, result: OrdersListResult, duration_ms: float
            ) -> list[CacheTag] | None:
                return []


def test_an_entity_key_without_the_layout_is_refused() -> None:
    """12.7.2: the key of an entity is called only for that layout."""
    with pytest.raises(DeclarationStructureError, match="declares @cache_entity_key without @cache_write"):

        class LoneEntityKeyAction(BaseAction[StubParams, OrdersListResult]):
            @cache_key("Key")
            async def lone_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
                return "k"

            @cache_entity_key("Entity key")
            async def lone_cache_entity_key(
                self, params: StubParams, box: ToolsBox, connections: Connections, entity: LayoutOrderCoreEntity
            ) -> str:
                return "e"

            @cache_write("Write")
            async def lone_cache_write(
                self, params: StubParams, box: ToolsBox, connections: Connections, result: OrdersListResult, duration_ms: float
            ) -> list[CacheTag] | None:
                return []


def test_the_entity_key_is_a_declaration_like_the_others() -> None:
    """12.7.2: suffix and parameters are checked when the class body runs."""
    with pytest.raises(NamingSuffixError, match="must end with '_cache_entity_key'"):

        @cache_entity_key("Key")
        async def order_key(self: Any, params: StubParams, box: ToolsBox, connections: Connections, entity: LayoutOrderCoreEntity) -> str:
            return "e"

    with pytest.raises(AspectSignatureError, match=r"\(self, params, box, connections, entity\)"):

        @cache_entity_key("Key")
        async def bad_cache_entity_key(self: Any, params: StubParams, box: ToolsBox, connections: Connections) -> str:
            return "e"


def _entity_layout_action(result_cls: type) -> type:
    """An entity-by-entity action over ``result_cls``, declared inside a test."""

    @meta(description="Built inside a test", domain=OrdersDomain)
    @check_roles(GuestRole)
    class InsideLayoutAction(BaseAction[StubParams, result_cls]):  # type: ignore[valid-type]
        @cache_key("Key")
        async def inside_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
            return "k"

        @cache_entity_key("Entity key")
        async def inside_cache_entity_key(
            self, params: StubParams, box: ToolsBox, connections: Connections, entity: LayoutOrderCoreEntity
        ) -> str:
            return "e"

        @cache_write("Write", layout=CacheLayout.ENTITIES)
        async def inside_cache_write(
            self, params: StubParams, box: ToolsBox, connections: Connections, result: BaseResult, duration_ms: float
        ) -> list[CacheTag] | None:
            return []

        @summary_aspect("Answer")
        async def inside_summary(
            self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
        ) -> BaseResult:
            return result_cls()  # type: ignore[no-any-return]

    return InsideLayoutAction


def test_a_result_without_an_entity_field_is_refused_at_assembly() -> None:
    """12.7.1: the layout would store nothing entity by entity."""

    class CountOnlyResult(BaseResult):
        total_count: int = Field(default=0, description="How many")

    with pytest.raises(DeclarationStructureError, match="CountOnlyResult has no field typed by an entity"):
        ActionGraphNode(_entity_layout_action(CountOnlyResult))


def test_an_entity_without_an_id_is_refused_at_assembly() -> None:
    """12.7.1: an entity entry is tagged with its type and id."""

    @entity(description="A note without an id", resource=OrdersStorage)
    class NoteWithoutIdCoreEntity(BaseCoreEntity):
        text: str = Field(description="Text")

    class NotesResult(BaseResult):
        notes: list[NoteWithoutIdCoreEntity] = Field(default_factory=list, description="Notes")

    with pytest.raises(DeclarationStructureError, match="NoteWithoutIdCoreEntity of field 'notes' declares no id"):
        ActionGraphNode(_entity_layout_action(NotesResult))


def test_an_entity_key_returns_a_string() -> None:
    """The key of an entity is never ``None``: every entity is stored."""

    @meta(description="Its entity key may return None", domain=OrdersDomain)
    @check_roles(GuestRole)
    class MaybeKeyAction(BaseAction[StubParams, OrdersListResult]):
        @cache_key("Key")
        async def maybe_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
            return "k"

        @cache_entity_key("Entity key")
        async def maybe_cache_entity_key(
            self, params: StubParams, box: ToolsBox, connections: Connections, entity: LayoutOrderCoreEntity
        ) -> str | None:
            return None

        @cache_write("Write", layout=CacheLayout.ENTITIES)
        async def maybe_cache_write(
            self, params: StubParams, box: ToolsBox, connections: Connections, result: OrdersListResult, duration_ms: float
        ) -> list[CacheTag] | None:
            return []

        @summary_aspect("Answer")
        async def maybe_summary(
            self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
        ) -> OrdersListResult:
            return OrdersListResult(orders=[], total_count=0)

    with pytest.raises(AspectSignatureError, match="must return str"):
        ActionGraphNode(MaybeKeyAction)
