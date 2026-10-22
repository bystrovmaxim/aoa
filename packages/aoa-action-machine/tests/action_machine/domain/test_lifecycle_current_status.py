"""Current status objects preserve the lifecycle's code-based public behaviour."""

import pytest
from pydantic import Field

from aoa.action_machine.domain import BaseStateEntity, Lifecycle
from aoa.action_machine.domain.lifecycle import InvalidStateError, InvalidTransitionError


class OrderStateEntity(BaseStateEntity):
    """Describe a status with data that need not be hashable."""

    requires_receipt: bool = Field(default=False, description="Whether a receipt is needed")
    labels: list[str] = Field(default_factory=list, description="Additional domain labels")

    PAID = OrderStateEntity(code="paid", display_name="Payment received", requires_receipt=True)  # noqa: F821
    SHIPPED = OrderStateEntity(code="shipped", display_name="Shipped")  # noqa: F821



class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Allow a paid order to be shipped."""

    _template = Lifecycle().state(OrderStateEntity.PAID).to(OrderStateEntity.SHIPPED).initial().state(OrderStateEntity.SHIPPED).final()


class OtherOrderLifecycle(OrderLifecycle):
    """Use the same codes under a different lifecycle identity."""


def test_current_status_is_the_declared_object():
    """Expose the exact declared object and its domain fields."""
    current = OrderLifecycle("paid")
    assert current.current_status is OrderStateEntity.PAID
    assert current.current_status.requires_receipt is True
    assert current.current_state == "paid"


def test_instance_stores_only_the_status_reference():
    """Keep no second mutable source for the current code."""
    current = OrderLifecycle("paid")
    assert current._current_status is OrderStateEntity.PAID
    assert "_current_state" not in vars(current)


def test_transition_selects_the_declared_target_without_changing_the_original():
    """Create a new lifecycle with the existing destination status."""
    current = OrderLifecycle("paid")
    following = current.transition("shipped")
    assert following is not current
    assert type(following) is OrderLifecycle
    assert following._current_status is OrderStateEntity.SHIPPED
    assert following.current_state == "shipped"
    assert current._current_status is OrderStateEntity.PAID
    assert current.current_state == "paid"


def test_runtime_does_not_construct_status_objects(monkeypatch):
    """Constructing and advancing lifecycles reuses the declared descriptions."""
    def refuse_construction(*args, **kwargs):
        """Fail if runtime tries to instantiate a status description."""
        raise AssertionError("Runtime constructed a status object")

    monkeypatch.setattr(OrderStateEntity, "__init__", refuse_construction)
    current = OrderLifecycle("paid")
    assert current.transition("shipped").current_state == "shipped"


def test_state_info_and_transition_checks_still_use_the_code():
    """Keep template metadata distinct from the domain description."""
    current = OrderLifecycle("paid")
    assert current.current_state_info.key == "paid"
    assert current.current_state_info.is_initial
    assert current.available_transitions == {"shipped"}
    assert current.can_transition("shipped")
    assert not current.can_transition("missing")


def test_invalid_codes_and_transitions_keep_their_exceptions():
    """Preserve errors used by callers before object storage."""
    with pytest.raises(InvalidStateError, match="not defined"):
        OrderLifecycle("missing")
    with pytest.raises(InvalidTransitionError, match="not allowed"):
        OrderLifecycle("shipped").transition("paid")


@pytest.mark.parametrize("attribute", ["current_state", "current_status", "current_state_info"])
def test_template_has_no_current_status(attribute):
    """Reject runtime properties on a template with a useful error."""
    with pytest.raises(RuntimeError, match="is a template, not an instance"):
        getattr(OrderLifecycle._template, attribute)


def test_repr_uses_the_code():
    """Keep diagnostic representations independent of the display label."""
    assert repr(OrderLifecycle("paid")) == "OrderLifecycle('paid')"


def test_equality_includes_the_lifecycle_class():
    """Equal codes in different lifecycles do not mean equal values."""
    assert OrderLifecycle("paid") != OtherOrderLifecycle("paid")
    assert OrderLifecycle("paid").__eq__("paid") is NotImplemented


def test_equality_and_hash_ignore_unhashable_status_fields():
    """Use class and code rather than hashing the status model."""
    current = OrderLifecycle("paid")
    same = OrderLifecycle("paid")
    assert current == same
    assert current != OrderLifecycle("shipped")
    assert hash(current) == hash((OrderLifecycle, "paid"))
    assert {current: "found"}[same] == "found"


def test_template_repr_equality_and_hash_remain_usable():
    """Keep the existing unset-state semantics without reading runtime properties."""
    template = Lifecycle()
    assert repr(template) == "Lifecycle(states=0, initial=0, final=0)"
    assert template == Lifecycle()
    assert hash(template) == hash((Lifecycle, None))
    assert OrderLifecycle() != OrderLifecycle("paid")
    assert OrderLifecycle("paid") != OrderLifecycle()
