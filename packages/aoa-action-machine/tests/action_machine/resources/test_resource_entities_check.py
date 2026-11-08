# packages/aoa-action-machine/tests/action_machine/resources/test_resource_entities_check.py
"""
The return check — a resource answers only with the entities its ``@entities`` lists.

Covers every path and refusal of T005:

- the plan — listed classes, the classes a relation can take outside the list, the
  plan kept in the concrete class's own ``__dict__``, computed by the model build and
  lazily without a machine, never inherited;
- the walk — a listed entity, a partial one, an unlisted one, its exact-class rule for
  a subclass, a reference (an unloaded relation) versus a loaded id-only entity, a
  dictionary member, a lifecycle state, a list, a tuple, a mapping, an async iterator;
- the wrapper — plain functions, coroutine functions and async generators checked;
  private methods, class methods, static methods, properties, plain generators and a
  plain function returning an awaitable left alone; a nesting wrapper checked by the
  plan of the resource it wraps; a test-bench substitute that is a resource checked,
  a bare ``Mock`` not checked;
- a resource without ``@entities`` refusing every entity, and an empty declaration
  refusing them because its list is empty.

The model these tests read lives beside them in ``tests/support/return_check_model.py``.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.exceptions import ResourceEntitiesError
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.resources.base_resource import PUBLIC_METHOD_MARKER
from aoa.action_machine.resources.entities.plan import (
    PLAN_ATTRIBUTE,
    EntitiesPlan,
    compute_entities_plan,
    entities_plan_for_class,
)
from aoa.action_machine.resources.entities.walk import walk_answer
from aoa.action_machine.testing import TestBench
from tests.support.return_check_model import (
    CatalogGateway,
    CurrencyEnumEntity,
    CustomerCoreEntity,
    CustomerOnlyDatabaseStorage,
    EmptyDatabaseStorage,
    FetchThroughResourceAction,
    InheritingShopDatabaseStorage,
    NestedProbeAction,
    OrderCoreEntity,
    OrderLineCoreEntity,
    OrderStateEntity,
    PlanningShopDatabaseStorage,
    PlanningShopStorageWrapper,
    ProductCoreEntity,
    ShopDatabaseStorage,
    TicketCoreEntity,
    TicketDatabaseStorage,
    TicketStatusEnumEntity,
    UndeclaredDatabaseStorage,
    make_order,
    make_product,
)

# ═════════════════════════════════════════════════════════════════════════════
# THE PLAN
# ═════════════════════════════════════════════════════════════════════════════


def test_the_plan_lists_the_declared_classes_in_order() -> None:
    """The plan reads the concrete class's own ``@entities`` and keeps the declaration order."""
    plan = compute_entities_plan(ShopDatabaseStorage)

    assert isinstance(plan, EntitiesPlan)
    assert plan.declared is True
    assert plan.listed == (OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
    assert plan.lists(OrderCoreEntity) is True
    assert plan.lists(ProductCoreEntity) is False


def test_the_plan_marks_only_the_classes_that_can_reach_outside_the_list() -> None:
    """``order`` reaches the catalog through ``line.product``; ``customer`` has no relations."""
    plan = compute_entities_plan(ShopDatabaseStorage)

    assert plan.leaves == frozenset({OrderCoreEntity, OrderLineCoreEntity})
    assert plan.needs_walk(OrderCoreEntity) is True
    assert plan.needs_walk(CustomerCoreEntity) is False


def test_a_relation_to_a_dictionary_is_not_a_way_out_of_the_list() -> None:
    """A dictionary member belongs to the model, so a relation to it does not mark the class."""
    plan = compute_entities_plan(TicketDatabaseStorage)

    assert plan.listed == (TicketCoreEntity,)
    assert plan.leaves == frozenset()


def test_a_subclass_resource_has_its_own_plan() -> None:
    """A subclass with its own ``@entities`` is planned from its own list, not its parent's."""
    parent_plan = compute_entities_plan(ShopDatabaseStorage)
    child_plan = compute_entities_plan(CustomerOnlyDatabaseStorage)

    assert child_plan.listed == (CustomerCoreEntity,)
    assert child_plan.declared is True
    assert parent_plan.listed != child_plan.listed


def test_a_subclass_without_the_declaration_declares_nothing() -> None:
    """A subclass never inherits its parent's plan: it states what its own database holds."""
    plan = compute_entities_plan(InheritingShopDatabaseStorage)

    assert plan.declared is False
    assert plan.listed == ()
    assert plan.leaves == frozenset()


def test_the_plan_is_kept_in_the_concrete_class_own_dict() -> None:
    """The plan lives in ``cls.__dict__['_entities_plan']``, never in a parent's slot."""
    plan = entities_plan_for_class(ShopDatabaseStorage)

    assert ShopDatabaseStorage.__dict__[PLAN_ATTRIBUTE] is plan
    assert CustomerOnlyDatabaseStorage.__dict__.get(PLAN_ATTRIBUTE) is not plan


def test_the_plan_is_computed_lazily_without_a_machine() -> None:
    """A resource used without a machine is checked on its first public call."""
    @meta(description="A database used without a machine")
    @entities(OrderCoreEntity, OrderLineCoreEntity, CustomerCoreEntity)
    class LazyDatabaseStorage(BaseStorage):
        @classmethod
        def get_wrapper_class(cls) -> None:
            return None

        def fetch(self) -> OrderCoreEntity:
            return make_order()

    assert PLAN_ATTRIBUTE not in LazyDatabaseStorage.__dict__

    assert LazyDatabaseStorage().fetch().id == "o1"

    assert isinstance(LazyDatabaseStorage.__dict__[PLAN_ATTRIBUTE], EntitiesPlan)


def test_the_model_build_attaches_a_plan_to_every_resource_node() -> None:
    """``NodeGraphCoordinator.build`` computes the plan for every resource in the graph."""
    coordinator = TestBench().coordinator
    resource_nodes = coordinator.get_nodes_by_type("Resource")

    assert resource_nodes
    for node in resource_nodes:
        assert isinstance(node.node_obj.__dict__.get(PLAN_ATTRIBUTE), EntitiesPlan)
    assert ShopDatabaseStorage.__dict__[PLAN_ATTRIBUTE].listed == (
        OrderCoreEntity,
        OrderLineCoreEntity,
        CustomerCoreEntity,
    )


# ═════════════════════════════════════════════════════════════════════════════
# THE WALK — the root, the containers and the path in the refusal
# ═════════════════════════════════════════════════════════════════════════════


def test_a_listed_entity_passes_and_reaches_the_caller_unchanged() -> None:
    """The listed answer is returned as the method built it, not copied or wrapped."""
    storage = ShopDatabaseStorage()

    order = storage.fetch_order()

    assert isinstance(order, OrderCoreEntity)
    assert order.id == "o1"
    assert order.lines.entities[0].id == "l1"


def test_an_entity_free_answer_passes() -> None:
    """An answer without entities passes at the cost of one type check."""
    assert ShopDatabaseStorage().fetch_entity_free() == {"count": 2}


def test_a_partial_answer_of_a_listed_class_passes() -> None:
    """A shorter answer is a partial of the same listed class, so it is listed."""
    partial = ShopDatabaseStorage().fetch_partial_order()

    assert isinstance(partial, OrderCoreEntity)
    assert partial.id == "o1"


def test_an_unlisted_entity_at_the_root_is_refused_with_all_four_parts() -> None:
    """The refusal names the resource, the entry point, the path and the exact class."""
    with pytest.raises(ResourceEntitiesError) as info:
        ShopDatabaseStorage().fetch_product()

    assert str(info.value) == (
        "ShopDatabaseStorage.fetch_product returned ProductCoreEntity at answer, "
        "which @entities(ShopDatabaseStorage) does not list."
    )


def test_the_refusal_path_names_attributes_and_indices() -> None:
    """The path is ``order.lines[0].product`` — the spec's sentence, verbatim."""
    plan = compute_entities_plan(ShopDatabaseStorage)

    with pytest.raises(ResourceEntitiesError) as info:
        walk_answer(
            make_order(product=make_product()),
            plan,
            "ShopDatabaseStorage",
            "get_order",
            "order",
        )

    assert str(info.value) == (
        "ShopDatabaseStorage.get_order returned ProductCoreEntity at order.lines[0].product, "
        "which @entities(ShopDatabaseStorage) does not list."
    )


def test_a_subclass_of_a_listed_class_is_refused_by_exact_class() -> None:
    """The comparison is ``type(value)``: a subclass is not the class the resource promised."""
    with pytest.raises(ResourceEntitiesError) as info:
        ShopDatabaseStorage().fetch_special_order()

    assert "SpecialOrderCoreEntity" in str(info.value)
    assert "does not list" in str(info.value)


def test_the_exception_is_a_type_error_and_is_exported() -> None:
    """Every AOA refusal of this kind is a ``TypeError`` and is importable from ``exceptions``."""
    from aoa.action_machine.exceptions import ResourceEntitiesError as Exported

    assert Exported is ResourceEntitiesError
    assert issubclass(ResourceEntitiesError, TypeError)


# ═════════════════════════════════════════════════════════════════════════════
# THE WALK — a reference passes, a loaded outside entity is refused
# ═════════════════════════════════════════════════════════════════════════════


def test_an_unloaded_relation_that_leads_out_of_the_list_passes() -> None:
    """A reference holds the id and no entity, so nothing outside the list is loaded."""
    order = ShopDatabaseStorage().fetch_order()

    assert order.lines.entities[0].product.entity is None
    assert order.lines.entities[0].product.id == "p1"


def test_a_loaded_relation_to_an_outside_class_is_refused() -> None:
    """A loaded product is refused even though the relation is the same field."""
    with pytest.raises(ResourceEntitiesError) as info:
        ShopDatabaseStorage().fetch_order_with_loaded_product()

    assert "at answer.lines[0].product" in str(info.value)
    assert "ProductCoreEntity" in str(info.value)


def test_a_loaded_id_only_entity_outside_the_list_is_refused() -> None:
    """A partial entity is still loaded: only an unloaded relation is a reference."""
    with pytest.raises(ResourceEntitiesError) as info:
        ShopDatabaseStorage().fetch_order_with_id_only_product()

    assert "at answer.lines[0].product" in str(info.value)
    assert "ProductCoreEntity" in str(info.value)


# ═════════════════════════════════════════════════════════════════════════════
# THE WALK — containers, iterators and the model's own classes
# ═════════════════════════════════════════════════════════════════════════════


def test_a_list_of_listed_entities_passes() -> None:
    """Every element of a list is checked; all of them are listed."""
    orders = ShopDatabaseStorage().fetch_orders()

    assert [order.id for order in orders] == ["o1", "o1"]


def test_a_tuple_of_listed_entities_passes() -> None:
    """Every element of a tuple is checked; the element listed is accepted."""
    orders = ShopDatabaseStorage().fetch_orders_tuple()

    assert isinstance(orders, tuple)
    assert orders[0].id == "o1"


def test_a_mapping_of_listed_entities_passes() -> None:
    """Every value of a mapping is checked; the key is part of the path."""
    orders = ShopDatabaseStorage().fetch_orders_mapping()

    assert orders["first"].id == "o1"


def test_a_list_element_outside_the_list_is_refused_with_its_index() -> None:
    """The path names the element that failed, not the whole answer."""
    with pytest.raises(ResourceEntitiesError) as info:
        ShopDatabaseStorage().fetch_orders_with_product()

    assert "at answer[1]" in str(info.value)


def test_a_mapping_value_outside_the_list_is_refused_with_its_key() -> None:
    """A mapping value's path uses ``[key]``, as the spec states."""
    with pytest.raises(ResourceEntitiesError) as info:
        ShopDatabaseStorage().fetch_orders_mapping_with_product()

    assert "at answer[bad]" in str(info.value)


def test_a_dictionary_member_passes_without_being_listed() -> None:
    """A ``BaseEnumEntity`` belongs to the model and passes wherever it appears."""
    currency = ShopDatabaseStorage().fetch_currency()

    assert currency is CurrencyEnumEntity.EUR
    # It is loaded inside a walked listed class's relation, and the walk still passes.
    assert ShopDatabaseStorage().fetch_order().currency.entity is currency


def test_a_lifecycle_state_passes_without_being_listed() -> None:
    """A ``BaseStateEntity`` belongs to the model and passes wherever it appears."""
    state = ShopDatabaseStorage().fetch_state()

    assert state is OrderStateEntity.DRAFT


def test_a_dictionary_relation_of_a_listed_class_is_walked_and_passes() -> None:
    """A relation to a dictionary holds its members loaded and is not a way out of the list."""
    ticket = TicketDatabaseStorage().fetch_ticket()

    assert ticket.status.entity is TicketStatusEnumEntity.OPEN


async def test_a_coroutines_answer_is_checked() -> None:
    """A coroutine function's answer is walked after it resolves."""
    assert (await ShopDatabaseStorage().fetch_order_async()).id == "o1"

    with pytest.raises(ResourceEntitiesError):
        await ShopDatabaseStorage().fetch_product_async()


async def test_an_async_iterator_is_checked_element_by_element() -> None:
    """The first element passes; the outside element is refused as it yields."""
    stream = ShopDatabaseStorage().stream_orders()

    first = await anext(stream)
    assert first.id == "o1"

    with pytest.raises(ResourceEntitiesError) as info:
        await anext(stream)
    assert "ProductCoreEntity" in str(info.value)
    await stream.aclose()


async def test_an_async_iterator_stopped_early_checks_only_yielded_elements() -> None:
    """A consumer that stops after the first element never reaches the outside second one."""
    stream = ShopDatabaseStorage().stream_one_order()

    assert (await anext(stream)).id == "o1"
    await stream.aclose()


# ═════════════════════════════════════════════════════════════════════════════
# THE WRAPPER — what is wrapped and what is not
# ═════════════════════════════════════════════════════════════════════════════


def test_a_plain_function_is_wrapped() -> None:
    """A public plain function carries the idempotent wrapper marker."""
    assert getattr(ShopDatabaseStorage.__dict__["fetch_order"], PUBLIC_METHOD_MARKER, False) is True


def test_a_coroutine_function_is_wrapped() -> None:
    """A public coroutine function carries the wrapper marker."""
    assert getattr(ShopDatabaseStorage.__dict__["fetch_order_async"], PUBLIC_METHOD_MARKER, False) is True


def test_an_async_generator_is_wrapped() -> None:
    """A public async generator carries the wrapper marker."""
    assert getattr(ShopDatabaseStorage.__dict__["stream_orders"], PUBLIC_METHOD_MARKER, False) is True


def test_a_private_method_is_not_wrapped() -> None:
    """A name starting with ``_`` is left alone: an outside entity passes through it."""
    assert getattr(ShopDatabaseStorage.__dict__["_fetch_private_product"], PUBLIC_METHOD_MARKER, False) is False
    assert ShopDatabaseStorage()._fetch_private_product().id == "p1"


def test_a_plain_generator_is_not_checked() -> None:
    """A plain generator hands back an object a wrapper cannot see through; it is not wrapped."""
    assert getattr(ShopDatabaseStorage.__dict__["iterate_products"], PUBLIC_METHOD_MARKER, False) is False
    assert [product.id for product in ShopDatabaseStorage().iterate_products()] == ["p1"]


async def test_a_plain_function_returning_an_awaitable_is_not_checked() -> None:
    """The wrapper does not await an awaitable it did not expect, so its answer is unchecked."""
    deferred = ShopDatabaseStorage().defer_product()

    assert (await deferred).id == "p1"


def test_class_static_and_property_are_not_wrapped() -> None:
    """Descriptors are not functions: they bind differently and are left untouched."""
    assert getattr(ShopDatabaseStorage.__dict__["fetch_class_product"], PUBLIC_METHOD_MARKER, False) is False
    assert getattr(ShopDatabaseStorage.__dict__["fetch_static_product"], PUBLIC_METHOD_MARKER, False) is False
    assert getattr(ShopDatabaseStorage.__dict__["product_property"], PUBLIC_METHOD_MARKER, False) is False

    assert ShopDatabaseStorage.fetch_class_product().id == "p1"
    assert ShopDatabaseStorage.fetch_static_product().id == "p1"
    assert ShopDatabaseStorage().product_property.id == "p1"
    assert ShopDatabaseStorage.get_wrapper_class.__func__ is not None


def test_the_wrapper_is_idempotent() -> None:
    """A second pass over the same class finds the marker and wraps nothing twice."""
    from aoa.action_machine.resources.base_resource import wrap_public_methods

    before = ShopDatabaseStorage.__dict__["fetch_order"]
    wrap_public_methods(ShopDatabaseStorage)

    assert ShopDatabaseStorage.__dict__["fetch_order"] is before


# ═════════════════════════════════════════════════════════════════════════════
# A RESOURCE WITHOUT @entities, AN EMPTY DECLARATION AND THE OTHER KINDS
# ═════════════════════════════════════════════════════════════════════════════


def test_a_resource_without_entities_refuses_every_entity() -> None:
    """A resource that declares no ``@entities`` refuses the entity and says so."""
    with pytest.raises(ResourceEntitiesError) as info:
        UndeclaredDatabaseStorage().fetch_order()

    assert str(info.value) == (
        "UndeclaredDatabaseStorage.fetch_order returned OrderCoreEntity at answer, "
        "but UndeclaredDatabaseStorage declares no @entities."
    )


def test_an_empty_declaration_refuses_every_entity() -> None:
    """An empty list is a declaration that the resource returns no entity."""
    with pytest.raises(ResourceEntitiesError) as info:
        EmptyDatabaseStorage().fetch_order()

    assert "which @entities(EmptyDatabaseStorage) does not list." in str(info.value)


def test_a_gateway_is_checked_like_a_storage() -> None:
    """Every resource kind may list its entities, and every kind is checked."""
    gateway = CatalogGateway()

    assert gateway.fetch_product().id == "p1"
    with pytest.raises(ResourceEntitiesError):
        gateway.fetch_customer()


def test_an_inherited_method_is_checked_by_the_concrete_class_plan() -> None:
    """The inherited ``fetch_order`` wrapper reads ``type(self)``, so the subclass's plan applies."""
    storage = CustomerOnlyDatabaseStorage()

    assert storage.fetch_customer().id == "c1"
    with pytest.raises(ResourceEntitiesError) as info:
        storage.fetch_order()

    assert str(info.value).startswith("CustomerOnlyDatabaseStorage.fetch_order returned OrderCoreEntity")


def test_a_subclass_without_entities_refuses_the_parents_entities() -> None:
    """A subclass that declares nothing has no list, even though its parent has one."""
    with pytest.raises(ResourceEntitiesError) as info:
        InheritingShopDatabaseStorage().fetch_order()

    assert "InheritingShopDatabaseStorage declares no @entities." in str(info.value)


# ═════════════════════════════════════════════════════════════════════════════
# THE TEST BENCH — a substitute that is a resource is checked, a bare Mock is not
# ═════════════════════════════════════════════════════════════════════════════


async def test_a_test_bench_substitute_that_is_a_resource_is_checked() -> None:
    """The bench hands over a resource instance, so its own methods check the answer."""
    substitute = ShopDatabaseStorage()
    bench = TestBench(mocks={ShopDatabaseStorage: substitute})

    with pytest.raises(ResourceEntitiesError) as info:
        await bench.run(FetchThroughResourceAction(), FetchThroughResourceAction.Params(), rollup=False)

    assert "ShopDatabaseStorage.fetch_product" in str(info.value)


async def test_a_bare_mock_substitute_is_not_checked() -> None:
    """A bare ``Mock`` is not a resource: its answer is not walked."""
    mock = AsyncMock(spec=ShopDatabaseStorage)
    mock.fetch_product = lambda: make_product()
    bench = TestBench(mocks={ShopDatabaseStorage: mock})

    result = await bench.run(FetchThroughResourceAction(), FetchThroughResourceAction.Params(), rollup=False)

    assert result.value == "p1"


# ═════════════════════════════════════════════════════════════════════════════
# A NESTED ACTION THROUGH SqlStorageWrapper
# ═════════════════════════════════════════════════════════════════════════════


async def test_a_nested_action_receives_the_sql_storage_wrapper() -> None:
    """The child action receives the wrapper — still a ``SqlStorageWrapper`` — not the resource."""
    bench = TestBench()
    storage = PlanningShopDatabaseStorage()

    result = await bench.run(
        NestedProbeAction(),
        NestedProbeAction.Params(mode="identity"),
        rollup=False,
        connections={"db": storage},
    )

    assert result.value == "PlanningShopStorageWrapper:True"


async def test_a_wrappers_answer_is_checked_by_the_plan_of_the_resource_it_wraps() -> None:
    """The wrapper has no ``@entities`` of its own; the wrapped database's plan decides."""
    storage = PlanningShopDatabaseStorage()
    wrapper = PlanningShopStorageWrapper(storage)

    assert (await wrapper.fetch_listed_unchecked()).id == "o1"
    with pytest.raises(ResourceEntitiesError) as info:
        await wrapper.fetch_unchecked()

    assert str(info.value) == (
        "PlanningShopDatabaseStorage.fetch_unchecked returned ProductCoreEntity at answer, "
        "which @entities(PlanningShopDatabaseStorage) does not list."
    )


async def test_a_nested_action_is_checked_by_the_wrapped_plan() -> None:
    """A nested action's call through the wrapper fails at the wrapped database's outside class."""
    bench = TestBench()

    with pytest.raises(ResourceEntitiesError) as info:
        await bench.run(
            NestedProbeAction(),
            NestedProbeAction.Params(mode="fetch"),
            rollup=False,
            connections={"db": PlanningShopDatabaseStorage()},
        )

    assert "PlanningShopDatabaseStorage.fetch_unchecked" in str(info.value)


# ═════════════════════════════════════════════════════════════════════════════
# SC-004 — a loose upper bound in the regular tests
# ═════════════════════════════════════════════════════════════════════════════


def test_the_check_costs_less_than_building_the_same_entities() -> None:
    """A loose guard: walking an answer costs less than building the entities it carries."""
    plan = compute_entities_plan(ShopDatabaseStorage)
    count = 500

    build_started = time.perf_counter()
    built = [make_order() for _ in range(count)]
    build_seconds = time.perf_counter() - build_started

    walk_started = time.perf_counter()
    walk_answer(built, plan, "ShopDatabaseStorage", "fetch_orders", "orders")
    walk_seconds = time.perf_counter() - walk_started

    assert walk_seconds <= build_seconds, f"walk {walk_seconds:.6f}s > build {build_seconds:.6f}s"
