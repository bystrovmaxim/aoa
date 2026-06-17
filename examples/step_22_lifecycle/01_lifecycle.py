"""
01_lifecycle.py — Lifecycle: status as a finite-state machine, not a bare string

Usually an object's status is a string with no rules: status = "paid". Nothing
stops status = "delivered" straight from "draft"; the allowed transitions live in
someone's head or a stale comment.

In AOA a Lifecycle is a finite automaton declared in code, attached to an Entity:
  - the template (allowed states and transitions) is built once in the class body
    with a fluent builder: .state(key, label).to(...).initial()/intermediate()/final();
  - an instance holds only the current state: OrderLifecycle("draft");
  - transition() returns a NEW lifecycle (never mutates); an illegal jump raises
    InvalidTransitionError; the graph validates the automaton at startup.

Tutorial: ../../docs/tutorials/step-22-lifecycle_draft.md  ·  topic: Lifecycle (FSM)

Run:
    uv run python examples/step_22_lifecycle/01_lifecycle.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Lifecycle
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.domain.lifecycle import InvalidTransitionError
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


class OrderLifecycle(Lifecycle):
    # Template: states + allowed transitions, declared once in the class body.
    _template = (
        Lifecycle()
        .state("draft", "Draft").to("paid", "cancelled").initial()
        .state("paid", "Paid").to("shipped", "cancelled").intermediate()
        .state("shipped", "Shipped").to("delivered").intermediate()
        .state("delivered", "Delivered").final()
        .state("cancelled", "Cancelled").final()
    )


@entity(description="Customer order", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    total: float = Field(ge=0, description="Order total")
    lifecycle: OrderLifecycle = Field(description="Order lifecycle state")


def main() -> None:
    # 1) Startup check: building the graph validates the automaton structure.
    ActionProductMachine()
    print("1) Machine built — lifecycle automaton validated at startup")

    # 2) Instance holds only the current state; the template knows the rest.
    order = OrderEntity(id="ord-1", total=1500.0, lifecycle=OrderLifecycle("draft"))
    lc = order.lifecycle
    print("\n2) Current state and rules:")
    print(f"   current_state={lc.current_state!r}  is_initial={lc.is_initial}  "
          f"available={sorted(lc.available_transitions)}")
    print(f"   can_transition('paid')={lc.can_transition('paid')}  "
          f"can_transition('shipped')={lc.can_transition('shipped')}")

    # 3) Legal transition returns a NEW lifecycle (immutable); apply via model_copy.
    paid = order.lifecycle.transition("paid")
    order = order.model_copy(update={"lifecycle": paid})
    print("\n3) After transition('paid'):")
    print(f"   order.lifecycle.current_state={order.lifecycle.current_state!r}  "
          f"(original 'draft' instance untouched)")

    # 4) Illegal jump is rejected — not at deploy, here and now.
    print("\n4) Illegal transition:")
    try:
        order.lifecycle.transition("delivered")  # paid -> delivered is not an edge
    except InvalidTransitionError as exc:
        print(f"   transition('delivered') -> InvalidTransitionError: {exc}")


if __name__ == "__main__":
    main()
