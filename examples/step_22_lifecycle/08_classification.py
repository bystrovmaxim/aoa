"""Keep classification in the template.

Use the same paid status as final in one lifecycle and intermediate in another.

Run: uv run python examples/step_22_lifecycle/08_classification.py
"""

from aoa.action_machine.domain import BaseStateEntity, Lifecycle


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

paid = OrderStateEntity(code="paid", display_name="Payment received")
new = OrderStateEntity(code="new", display_name="New")
shipped = OrderStateEntity(code="shipped", display_name="Shipped")
finished_at_payment = Lifecycle().state(new).to(paid).initial().state(paid).final()
continues_to_shipping = Lifecycle().state(new).to(paid).initial().state(paid).to(shipped).intermediate().state(shipped).final()

# Run the case.
assert finished_at_payment.get_state_entity("paid") is continues_to_shipping.get_state_entity("paid")
assert finished_at_payment.get_states()["paid"].is_final
assert continues_to_shipping.get_states()["paid"].is_intermediate
print("first template:", finished_at_payment.get_states()["paid"].state_type.name)
print("second template:", continues_to_shipping.get_states()["paid"].state_type.name)
