# packages/aoa-action-machine/tests/action_machine/model/test_observable_state.py
"""
One comparison of observable state, which equality does not give.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 8.2 of issue #409. ``observable_difference`` returns the first place two values
differ in what rule 2 of #399 lists — values and their types, loaded fields,
relations' ids, loaded state and loaded entities, declared objects — with its path,
or ``None``. Equality is left as it is.
"""

from __future__ import annotations

import copy
from uuid import UUID

import pytest

from aoa.action_machine.domain import AssociationMany, AssociationOne, observable_difference
from tests.support.round_trip_model import (
    CUSTOMER_ID,
    RtCustomerCoreEntity,
    RtLineCoreEntity,
    RtOrderLifecycle,
    RtOrderStateEntity,
    customer,
    order,
    result,
)


def test_a_many_relation_loaded_with_zero_rows_differs_from_one_never_loaded() -> None:
    """Case 8.2: equal by ==, different by observable state."""
    never = AssociationMany(ids=())
    empty = AssociationMany(ids=(), entities=(), entities_loaded=True)
    assert never == empty
    assert observable_difference(never, empty) == "$: loaded False != True"


def test_a_one_relation_with_and_without_its_entity_differ() -> None:
    """The loaded state of a One relation is observable."""
    bare = AssociationOne(id=CUSTOMER_ID)
    loaded = AssociationOne(id=CUSTOMER_ID, entity=customer())
    assert bare == loaded
    assert observable_difference(bare, loaded) == "$: loaded False != True"


def test_a_partial_entity_differs_from_one_with_a_field_more() -> None:
    """The loaded fields are compared, and the difference names them."""
    held = RtCustomerCoreEntity.partial(id=CUSTOMER_ID, name="Ann")
    assert observable_difference(held, customer()) == "$: loaded fields ['id', 'name'] != ['id', 'name', 'email']"


def test_values_equal_by_eq_of_different_types_differ() -> None:
    """A UUID and its string are equal nowhere they are used, though == may hold for others such as 1 and 1.0."""
    assert observable_difference(1, 1.0) == "$: int != float"
    assert observable_difference(CUSTOMER_ID, str(CUSTOMER_ID)) == "$: UUID != str"


def test_a_status_that_is_not_the_declared_object_differs() -> None:
    """A declared value is compared by which declared object it is."""
    stand_in = copy.copy(RtOrderStateEntity.PAID)
    assert stand_in == RtOrderStateEntity.PAID
    assert observable_difference(RtOrderStateEntity.PAID, stand_in) == "$: not the declared RtOrderStateEntity 'paid'"


def test_lifecycles_differ_by_their_current_status() -> None:
    """A lifecycle is compared by its declared current status."""
    assert observable_difference(RtOrderLifecycle("paid"), RtOrderLifecycle("paid")) is None
    assert observable_difference(RtOrderLifecycle("paid"), RtOrderLifecycle("draft")) == "$: status 'paid' != 'draft'"


def test_the_path_leads_to_the_difference_in_a_deep_result() -> None:
    """A difference inside a Result names where it is."""
    before = result(lines=(RtLineCoreEntity(id="l1", quantity=2),))
    after = result(lines=(RtLineCoreEntity(id="l1", quantity=3),))
    assert observable_difference(before, after) == "$.order.lines.entities[0].quantity: 2 != 3"
    assert observable_difference(before, result(customer_loaded=False)).startswith("$.order.customer: loaded")


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ([1, 2], [1, 2, 3], "$: length 2 != 3"),
        ({"a": 1}, {"b": 1}, "$: keys ['a'] != ['b']"),
        (AssociationMany(ids=("a",)), AssociationMany(ids=("b",)), "$: ids ('a',) != ('b',)"),
        (AssociationOne(id="a"), AssociationOne(id="b"), "$: id 'a' != 'b'"),
    ],
)
def test_sequences_mappings_and_ids_are_compared_item_by_item(before: object, after: object, expected: str) -> None:
    """Containers are compared by their items."""
    assert observable_difference(before, after) == expected


def test_a_value_and_an_independent_copy_with_the_same_state_are_the_same() -> None:
    """Two values built apart with the same observable state give no difference."""
    assert observable_difference(result(), result()) is None
    loaded = result(lines=(RtLineCoreEntity(id="l1", quantity=2),))
    assert observable_difference(loaded, loaded) is None
    assert observable_difference(order(lines=None), order(lines=None)) is None
    assert observable_difference(UUID(int=1), UUID(int=1)) is None
