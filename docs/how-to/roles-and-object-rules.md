# Keep roles in the declaration and conditions in the object rule

Use `@check_roles` to state which callers may enter an operation. Put account,
input and object conditions in its optional `@access_decide` method. The role
requirement runs first. Passing it does not bypass the object rule.

An operation with `@check_roles(GuestRole)` and no object rule is explicitly open
at the machine level. Authentication at a transport boundary remains separate.
Adding an object rule can refuse the same guest caller. See the
[guest and active-role scenario](../../examples/step_03_authorization_and_roles/14_guest_and_any.ipynb).

## Migrate an existing declaration

| Previous declaration or handler | Current form |
| --- | --- |
| `@check_roles(grant(ManagerRole))` | `@check_roles(ManagerRole)` |
| A tuple of unconditional grants | A tuple of bare role classes; several positional roles or one list also work |
| `grant(Role, when=condition, reason="EU_TEAM_ONLY")` | Keep the role in `@check_roles`; move the condition into `@access_decide` and return `Refused("EU_TEAM_ONLY")` on failure |
| `guard=condition, guard_reason="AMOUNT_LIMIT"` | Add the shared condition to the same object rule and return `Refused("AMOUNT_LIMIT")` on failure |
| `when(user)` reads caller information | Declare the needed keys with `@context_requires` and read them through `ctx: ContextView` |
| A reasonless object refusal | Return `FORBIDDEN_OBJECT` or `Refused()` |
| A handler branches on `WHEN` or `GUARD` | Handle the migrated condition as `ACCESS_DECIDE`; use `reason` to distinguish its refusals |
| `GuestRole` beside ordinary roles, previously matched as an ordinary alternative | The guest alternative now opens the role layer; remove it if guests must not enter |
| `AnyRole` beside ordinary roles, previously matched as an ordinary alternative | Any active role now satisfies this declaration, including unrelated roles |
| Repeating the same role or exporting its condition fields | Repeated roles produce one edge; regenerate saved exports and read conditions from the object-rule declaration |
| Importing `Grant`, `grant`, `AccessConditionAsyncError` or `ConditionReasonError` | Remove those imports; object rules use verdicts and async methods |

There is one object rule per operation. Combine conditions in that method, with
explicit branches and reasons. Review the meaning of the old conditions before
combining them: a shared guard must constrain every admitted caller, while a
role-specific condition may have applied to only one alternative. Replacing all
conditions with an unconditional OR can accidentally widen access.

Keep role inheritance and active-role filtering in `@check_roles`. An object rule
can request `user.roles` through `@context_requires` when it needs a caller fact
beyond the role requirement; that does not replace the role declaration.
Do not recreate the role gate with string names or manual hierarchy matching.

## Read the caller through declared context

This complete program admits managers at the role gate, then limits cancellation
to an EU account. A US manager receives an object refusal rather than a role
refusal. The method declares exactly the caller field it reads.

Put `@context_requires` immediately below `@access_decide`. Include the trailing
`ctx: ContextView` parameter only when context is requested. The other parameters
are `self, params, box, connections`; the method must be async and have a return
annotation for `Verdict` or a supported verdict subtype.

[script](../../examples/step_03_authorization_and_roles/02_object_rule.py) · [executed notebook](../../examples/step_03_authorization_and_roles/02_object_rule.ipynb)

```python
"""A condition on one role becomes a branch of the object rule.
Run: .venv/bin/python examples/step_03_authorization_and_roles/02_object_rule.py
"""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

# %% Setup


class StoreDomain(BaseDomain):
    """Group the order operations."""

    name = "store"
    description = "Order management"


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


class OrderParams(BaseParams):
    """Identify the order to cancel."""

    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    """Report the cancelled order."""

    order_id: str = Field(description="Cancelled order identifier")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse a manager whose account is not in the EU team")
    @context_requires("user.user_id")
    async def cancel_order_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> Verdict:
        """The role admits any manager; only the EU team passes the object rule."""
        if ctx.get("user.user_id").startswith("eu-"):
            return Allowed()
        return Refused("EU_TEAM_ONLY")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A condition on one role becomes a branch of the object rule."""
    machine = ActionProductMachine(cache_coordinator=None)
    eu = Context(user=UserInfo(user_id="eu-m1", roles=(ManagerRole,)))
    us = Context(user=UserInfo(user_id="us-m1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(eu, CancelOrderAction, OrderParams(order_id="ord-001"))
    assert answer.model_dump(mode="json") == {"kind": "allowed"}
    print("EU manager:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(us, CancelOrderAction, OrderParams(order_id="ord-001"))
    assert answer.model_dump(mode="json") == {"kind": "refused", "gate": "ACCESS_DECIDE", "reason": "EU_TEAM_ONLY"}
    print("US manager:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

Output:

```text
EU manager: {'kind': 'allowed'}
US manager: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'EU_TEAM_ONLY'}
```

## Apply a condition to every admitted caller

An amount limit uses `params` and needs no context view. Return `Allowed()` for
amount 50 and `Refused("AMOUNT_LIMIT")` for amount 150. The
[script](../../examples/step_03_authorization_and_roles/03_shared_object_rule.py) · [executed notebook](../../examples/step_03_authorization_and_roles/03_shared_object_rule.ipynb) shows both calls with assertions.

For several conditions, make branch order deliberate. The
[script](../../examples/step_03_authorization_and_roles/17_branch_order.py) · [executed notebook](../../examples/step_03_authorization_and_roles/17_branch_order.ipynb) admits a service account before checking the EU
team restriction for other managers. Both callers still satisfy `ManagerRole`
through the normal role hierarchy. The
[script](../../examples/step_03_authorization_and_roles/22_reason_in_branch.py) · [executed notebook](../../examples/step_03_authorization_and_roles/22_reason_in_branch.ipynb) demonstrates an order-specific refusal reason
and its accepted neighbor.

## Handle queries and execution

`machine.check_access_decide(context, ActionClass, params)` returns a verdict.
`Allowed` permits the call, `Refused` denies it, and `Undecided` means the machine
could not decide. The query may resolve dependencies and connections and call
the object rule. Keep object rules free of business side effects.

`machine.run(context, ActionClass(), params)` performs access checks again.
A refusal raises `AccessDenied`; inability to decide raises `AccessUndecided`.
Read `exc.verdict.gate` and `exc.verdict.reason`, rather than a numeric level.
A previous successful query is not a reservation of permission.

The [script](../../examples/step_03_authorization_and_roles/07_three_answers.py) · [executed notebook](../../examples/step_03_authorization_and_roles/07_three_answers.ipynb) produces:

```text
check: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'CANCELLATIONS_PAUSED'}
run raises: AccessDenied Access denied by ACCESS_DECIDE: CANCELLATIONS_PAUSED
run verdict: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'CANCELLATIONS_PAUSED'}
```

A rule that raises or returns an invalid value yields `Undecided`, rather than
permission or an ordinary policy refusal. The underlying cause remains server
information. See the [storage failure](../../examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.ipynb)
and [invalid-answer](../../examples/step_03_authorization_and_roles/23_invalid_answer.ipynb) scenarios.

## Account for the later refusal

A former `guard` ran before the execution lifecycle began. Its migrated object
rule runs inside execution, after connection validation and before business
aspects. It may therefore refuse after a start event has been published or
resources have been prepared. Do not rely on it to prevent connection setup.
If a requirement forbids even starting that work, enforce it at the calling
boundary before invoking the machine.

A role refusal still prevents the object rule and summary from running.
The [script](../../examples/step_03_authorization_and_roles/13_cascade.py) · [executed notebook](../../examples/step_03_authorization_and_roles/13_cascade.ipynb) observes both paths through plugin events without
mutable action globals. Policy refusals do not enter `@on_error` or trigger
business compensation; no business aspect has run.

## Diagnose a migration failure

Removed keywords raise `RoleSpecTypeError` while Python evaluates the decorator
expression, before the class declaration finishes. Removed imports raise
`ImportError` immediately. There is no deprecation period that keeps conditions
running. The removed enum values fail both enum conversion and verdict parsing.

See the [exact refusal reference](../reference/access-control.md#migration-refusals)
and the [script](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py) · [executed notebook](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.ipynb). It groups legal role
choices, removed keywords, removed imports and wire-value failures in one lesson.

## Read the resulting graph

The role declaration has one edge per distinct role, in first-declaration order.
Its exported properties are empty. Repeated roles do not create independent
conditions. The action has no `guard` or `guard_reason` property. The object rule
remains a separate `AccessDecide` node with its description and declared context.
Rebuild saved graph exports after migrating conditions.

The [script](../../examples/step_03_authorization_and_roles/25_access_graph.py) · [executed notebook](../../examples/step_03_authorization_and_roles/25_access_graph.ipynb) checks the exported data, deduplication and
`user.user_id` context companion. See also the
[reference](../reference/access-control.md) and
[authorization tutorial](../tutorials/step-03-authorization-and-roles.md).
