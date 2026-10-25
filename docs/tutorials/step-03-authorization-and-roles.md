<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 03 — Verifying the caller and their permissions

[← State](step-02-state-as-x-ray.md) · [Contents](../index.md) · [Saga and compensations →](step-04-saga-and-compensations.md)

Two managers can have the same role without having permission to cancel the
same order. Separate the role requirement from the rule about the particular
call. In AOA, `@check_roles` owns the former and `@access_decide` owns the latter.

Every script linked here runs independently from the repository root. Each has
a matching notebook with the same declarations and calls. The complete program
below requires no preparation from another code block.

## Authentication and authorization: two different questions

Authentication establishes who is calling. A transport or authentication
coordinator builds the caller's `Context`; an operation should not trust a user
identifier merely because a client supplied it. Authorization decides whether
that caller may perform the requested operation.

The machine publishes the authentication word `AUTH_COORDINATOR`, but its own
authentication step passes. Credential validation belongs to the calling boundary.
See [authentication](step-12-authentication.md) and the
[authentication scenario](../../examples/step_03_authorization_and_roles/12_authentication.ipynb).

## Preparation: the objects involved in a call

`BaseParams` holds the request data. `Context.user` holds the established caller
and assigned role classes. An operation derives from `BaseAction[Params, Result]`
and declares `@meta`, `@check_roles` and one `@summary_aspect`.

A role is an `ApplicationRole` subclass with a name and description. Assign its
class in `UserInfo.roles`, rather than its name or an instance. Roles are checked
before the object's rule and before any business aspect.

## RBAC: a role requirement decides the call

`@check_roles(ManagerRole)` admits a caller whose assigned role derives from
`ManagerRole`. A role subclass satisfies its parent requirement; the reverse
does not follow. Roles carry no attached conditions.

The [role script](../../examples/step_03_authorization_and_roles/01_roles.py) and
[notebook](../../examples/step_03_authorization_and_roles/01_roles.ipynb) introduce
this boundary. The [role alternatives](../../examples/step_03_authorization_and_roles/15_alternative_roles.ipynb)
show an independent auditor without giving that auditor a manager's permissions.

## A check without execution: asking about a call before making it

Ask `machine.check_access_decide(context, ActionClass, params)` for a verdict.
Execute with `machine.run(context, ActionClass(), params)`. The former accepts a
class; the latter accepts an instance. Both consult the same access declarations.
A query returns `Allowed`, `Refused` or `Undecided` and can prepare dependencies
and connections, but it does not run business aspects.

A successful query does not guarantee a later run: ownership or policy data may
change in between. Execution checks again. See the
[query script](../../examples/step_03_authorization_and_roles/05_machine_check.py)
and [notebook](../../examples/step_03_authorization_and_roles/05_machine_check.ipynb).

## Authentication: where the caller's identity comes from

An authenticated user can still have no active roles. A user identifier alone
does not satisfy `AnyRole`. Guest access also does not bypass a transport's
credential checks. Configure that boundary through an
[authentication coordinator](../how-to/authoring-auth-coordinator.md).

## The registry: how a role name becomes a role object

External role names must be mapped to application role classes when building
`UserInfo`. `@check_roles` consumes the classes. It rejects role-name strings
rather than guessing which declaration the caller meant.

## RBAC: which roles may call the operation

One role, several positional roles, one tuple or one list express the same kind
of requirement: any declared alternative may match. Duplicate roles collapse
in first-declaration order. A `GuestRole` alternative opens the role layer;
an `AnyRole` alternative requires any active assigned role, even one unrelated
to the other alternatives.

A caller role marked `SILENCED` contributes no permission. Requiring an `UNUSED`
role fails during declaration; a `DEPRECATED` role warns. The
[reference table](../reference/access-control.md#role-declarations) states the
boundaries, and the [silenced-role scenario](../../examples/step_03_authorization_and_roles/16_silenced_role.ipynb)
compares an active manager with a silenced descendant.

The [guest script](../../examples/step_03_authorization_and_roles/14_guest_and_any.py)
and [notebook](../../examples/step_03_authorization_and_roles/14_guest_and_any.ipynb)
show open execution, a guest refused by an object rule, mixed sentinels, an
independent auditor, an identified caller without roles and a silenced caller:

```text
guest, anonymous: {'kind': 'allowed'}
any, anonymous: {'kind': 'refused', 'gate': 'CHECK_ROLES', 'reason': None}
any, manager: {'kind': 'allowed'}
guest run: {'order_id': 'ord-001'}
guest with object rule: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'ORDER_CLOSED'}
AccessDenied: Access denied by ACCESS_DECIDE: ORDER_CLOSED
guest beside manager: {'kind': 'allowed'}
any beside manager, auditor: {'kind': 'allowed'}
any, identified without roles: {'kind': 'refused', 'gate': 'CHECK_ROLES', 'reason': None}
any, silenced only: {'kind': 'refused', 'gate': 'CHECK_ROLES', 'reason': None}
```

## ABAC: conditions on the caller and on the input

Conditions belong in the operation's optional object rule. A limit on an input
amount needs only `params`. A rule reading caller information additionally
requests context keys. Neither condition belongs on `@check_roles`.

Here is a complete program applying the same amount limit to every admitted
manager. It contains both the accepted and refused call, with assertions.

[script](../../examples/step_03_authorization_and_roles/03_shared_object_rule.py) · [executed notebook](../../examples/step_03_authorization_and_roles/03_shared_object_rule.ipynb)

```python
"""A shared condition becomes the object rule itself.
Run: .venv/bin/python examples/step_03_authorization_and_roles/03_shared_object_rule.py
"""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
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


class CancellationParams(OrderParams):
    """Add the requested cancellation amount."""

    amount: int = Field(description="Requested amount")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[CancellationParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse a cancellation above the amount limit")
    async def cancel_order_access_decide(
        self,
        params: CancellationParams,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        """The shared limit on every caller is now a branch of the object rule."""
        if params.amount <= 100:
            return Allowed()
        return Refused("AMOUNT_LIMIT")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self, params: CancellationParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A shared condition becomes the object rule itself."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(
        caller, CancelOrderAction, CancellationParams(order_id="ord-001", amount=50)
    )
    assert answer.model_dump(mode="json") == {"kind": "allowed"}
    print("amount 50:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(
        caller, CancelOrderAction, CancellationParams(order_id="ord-001", amount=150)
    )
    assert answer.model_dump(mode="json") == {"kind": "refused", "gate": "ACCESS_DECIDE", "reason": "AMOUNT_LIMIT"}
    print("amount 150:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())
```

Output:

```text
amount 50: {'kind': 'allowed'}
amount 150: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'AMOUNT_LIMIT'}
```

The [caller-context scenario](../../examples/step_03_authorization_and_roles/02_object_rule.ipynb)
adds an EU-team rule using `@context_requires("user.user_id")` and `ContextView`.
Its [complete guide](../how-to/roles-and-object-rules.md#read-the-caller-through-declared-context)
explains the decorator order and the extra parameter.

## Authorization and preconditions: where the line is

An object rule answers whether the caller may perform the call. Business
validation belongs in the operation's params, aspects and result checks.
Both can inspect an amount, but their meaning and handling differ: a permission
refusal raises `AccessDenied`, while a business failure follows the operation's
error and compensation policy.

## Per-object authorization: may this caller touch this order

Use params to identify the object, a declared dependency or connection to read
its state, and declared context to identify the caller. Return `Allowed()` when
permission is established. Return `Refused("REASON")` for a named policy refusal,
or `FORBIDDEN_OBJECT` for a reasonless object refusal. A reasonless refusal is
valid; a supplied reason cannot be blank.

The [ownership script](../../examples/step_03_authorization_and_roles/04_access_decide.py)
and [notebook](../../examples/step_03_authorization_and_roles/04_access_decide.ipynb)
give a missing order and another caller's order the same public answer.
The [context scenario](../../examples/step_03_authorization_and_roles/10_context_in_the_check.ipynb)
shows the restricted view. The [branch-order scenario](../../examples/step_03_authorization_and_roles/17_branch_order.ipynb)
shows a service-account branch preceding the team restriction, while the
[reason scenario](../../examples/step_03_authorization_and_roles/22_reason_in_branch.ipynb)
compares a closed order with an open one.

## Two outcomes: a refusal is not a failure

A policy decision is `Refused`. A storage exception or an invalid returned value
leaves the machine unable to decide and produces `Undecided`. The original cause
stays on the server. Execution raises `AccessDenied` for the former and
`AccessUndecided` for the latter; read their `verdict` attributes.

The [query/execution script](../../examples/step_03_authorization_and_roles/07_three_answers.py)
and [notebook](../../examples/step_03_authorization_and_roles/07_three_answers.ipynb)
produce this exact refusal on both paths:

```text
check: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'CANCELLATIONS_PAUSED'}
run raises: AccessDenied Access denied by ACCESS_DECIDE: CANCELLATIONS_PAUSED
run verdict: {'kind': 'refused', 'gate': 'ACCESS_DECIDE', 'reason': 'CANCELLATIONS_PAUSED'}
```

Compare the [storage-failure scenario](../../examples/step_03_authorization_and_roles/08_refusal_is_not_a_failure.ipynb),
[reason formats](../../examples/step_03_authorization_and_roles/09_reasons.ipynb),
[failure event](../../examples/step_03_authorization_and_roles/21_failure_event.ipynb)
and [invalid answer](../../examples/step_03_authorization_and_roles/23_invalid_answer.ipynb).

## The cascade: the order every check runs in

The published gate words are exactly `AUTH_COORDINATOR`, `CHECK_ROLES` and
`ACCESS_DECIDE`. Role requirements run before the execution lifecycle starts.
An object rule runs inside execution, after connection validation and before
business aspects. If no object rule is declared, that step passes.

A migrated condition can now refuse after execution has started and connections
have been prepared. It cannot guarantee that connection setup never happens.
Place such an admission requirement before invoking the machine. A role refusal
still prevents the object check from running.

The [cascade script](../../examples/step_03_authorization_and_roles/13_cascade.py)
and [notebook](../../examples/step_03_authorization_and_roles/13_cascade.ipynb)
observe the reached steps with a plugin:

```text
manager refused at: ACCESS_DECIDE
manager called: ['object']
stranger refused at: CHECK_ROLES
stranger called: []
```

Neither policy refusal enters `@on_error` or business compensation. No business
aspect has run at the point of refusal.

## Observability: what a plugin sees

Access-query events describe a preliminary question independently of execution.
Execution can publish a start event before an object refusal; a start does not
promise successful completion. Use the [event scenario](../../examples/step_03_authorization_and_roles/11_events.ipynb)
and the [plugin guide](../how-to/authoring-plugin.md) to observe the boundaries.

The graph also separates the role requirement from the object rule. Role edges
have empty properties; the object rule has its own `AccessDecide` node and
required-context companions. The [graph script](../../examples/step_03_authorization_and_roles/25_access_graph.py)
and [notebook](../../examples/step_03_authorization_and_roles/25_access_graph.ipynb)
inspect the current public representation, including a repeated role.

## Invariants: how a wrong declaration is caught

An operation must declare roles explicitly, including `GuestRole` for public
access. It may declare at most one object rule in its own class. An inherited
object method does not declare the child's policy. The method is async, ends in
`_access_decide`, has a nonblank description and an annotated verdict return.

| Lesson | Runnable script | Notebook |
| --- | --- | --- |
| One object rule | [06_the_declaration.py](../../examples/step_03_authorization_and_roles/06_the_declaration.py) | [notebook](../../examples/step_03_authorization_and_roles/06_the_declaration.ipynb) |
| Role lifecycle declaration | [17_a_wrong_role_mode.py](../../examples/step_03_authorization_and_roles/17_a_wrong_role_mode.py) | [notebook](../../examples/step_03_authorization_and_roles/17_a_wrong_role_mode.ipynb) |
| Nonblank description | [18_empty_description.py](../../examples/step_03_authorization_and_roles/18_empty_description.py) | [notebook](../../examples/step_03_authorization_and_roles/18_empty_description.ipynb) |
| Method signature | [19_wrong_signature.py](../../examples/step_03_authorization_and_roles/19_wrong_signature.py) | [notebook](../../examples/step_03_authorization_and_roles/19_wrong_signature.ipynb) |
| Return annotation | [20_missing_return_type.py](../../examples/step_03_authorization_and_roles/20_missing_return_type.py) | [notebook](../../examples/step_03_authorization_and_roles/20_missing_return_type.ipynb) |
| Role choices and migration refusals | [24_role_declarations_and_migration.py](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py) | [notebook](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.ipynb) |

The [reference](../reference/access-control.md#migration-refusals) gives the exact
new migration refusals and identifies whether they occur at import, decorator
evaluation, conversion or payload validation. Other declaration errors remain
covered by the linked lessons.

## Migration: if you used the previous API

Replace unconditional `grant(Role)` wrappers with bare roles. Move `when` and
`guard` conditions into one `@access_decide` method, returning their reason from
the refusing branch. Remove the old condition imports and handle the migrated
refusal as `ACCESS_DECIDE`; `WHEN` and `GUARD` are no longer valid gate values.

Follow the [migration table and full context example](../how-to/roles-and-object-rules.md#migrate-an-existing-declaration).
The [migration script](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py)
and [notebook](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.ipynb)
run accepted neighbors and all removed keyword/import cases together.

## Check your understanding

1. Why can a manager pass the role requirement and still receive `ACCESS_DECIDE`?
2. What does `AnyRole` answer for an identified caller with no active roles?
3. What happens when `GuestRole` is written beside `ManagerRole`?
4. Why is an object rule the wrong place to prevent connection setup?
5. Which exception does execution raise if the rule cannot read its data?
6. Why must a subclass declare its own object rule?

Change the limit in the complete program from 100 to 200. Predict which assertion
will fail, then restore the limit. Remove the caller's role and predict why the
refusal now says `CHECK_ROLES` before the amount rule can answer.

Continue to [Saga and compensations](step-04-saga-and-compensations.md) for failures
after business work has already begun.
