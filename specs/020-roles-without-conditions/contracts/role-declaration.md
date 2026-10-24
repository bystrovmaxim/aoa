# Contract — Role Declaration

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)

This is what a project author may write, what each form means, and what happens to a declaration
that still belongs to the removed mechanism. It is the contract the acceptance tests assert.

## Accepted forms

| Declaration | Meaning |
| --- | --- |
| `@check_roles(CustomerRole)` | the caller holds `CustomerRole` or a subclass of it |
| `@check_roles(CustomerRole, AdminRole)` | the caller holds either — a choice, not both |
| `@check_roles((CustomerRole, AdminRole))` | the same choice, written as a tuple |
| `@check_roles(GuestRole)` | open: no role is required |
| `@check_roles(AnyRole)` | the caller holds at least one role that is not silenced |
| `@check_roles(GuestRole, CustomerRole)` | open, because the open alternative is satisfied by any caller |
| `@check_roles(AnyRole, CustomerRole)` | at least one role that is not silenced |
| `@check_roles((A, A))` | the same as `@check_roles(A)`; a repeated role is one role |

`RoleMode` keeps its meaning: `UNUSED` is refused where it is declared required, `DEPRECATED`
warns, `SILENCED` never grants anything.

## Refused forms

Every refusal happens at class definition, before any call runs.

| Declaration | Answer |
| --- | --- |
| `@check_roles()` | `RoleSpecTypeError`: at least one role is required |
| `@check_roles("CustomerRole")` | `RoleSpecTypeError`: a role type, not a name |
| `@check_roles(())` or `@check_roles([])` | `RoleSpecTypeError`/`DecoratorArgumentValueError`: an empty choice is not a choice |
| `@check_roles(CustomerRole, guard=..., guard_reason=...)` | `RoleSpecTypeError` whose text contains `@access_decide` and shows the replacement |
| `@check_roles(CustomerRole, when=...)` | the same migration refusal |
| `@check_roles(CustomerRole, required=True)` | `RoleSpecTypeError`: the keyword is not part of a role declaration |
| `@check_roles(grant(CustomerRole))` | `NameError` at import, because `grant` is not a published name any more |
| `from ...check_roles import grant, Grant` | `ImportError` naming the missing symbol |

The migration message is a sentence, not a stack trace. Its shape:

```text
@check_roles declares roles only; the keyword 'guard' belonged to the removed condition layer.
Move that condition into the operation's @access_decide method — for example
``@access_decide("...")`` on ``cancel_order_access_decide`` — and return Refused("REASON") for
the branch that used to refuse.
```

## Interplay with the object rule

| Declaration | Result |
| --- | --- |
| `@check_roles(GuestRole)`, no `@access_decide` | builds; every caller is allowed (an explicitly open operation) |
| `@check_roles(CustomerRole)`, no `@access_decide` | builds; the role gate is the whole rule |
| `@check_roles(CustomerRole)` + `@access_decide` | the role gate decides first, the object rule decides inside the run |
| `@check_roles(GuestRole)` + `@access_decide` | the whole rule is object-level |
| two `@access_decide` methods | refused (unchanged) |
| `@access_decide` inherited from a base action | never inherited (unchanged) |

The object rule may declare `user.roles` and reason about roles for what a single declaration
cannot say. It must not repeat the match the declaration already performs.

## Where the contract is asserted

- `packages/aoa-action-machine/tests/action_machine/intents/check_roles/` — accepted forms,
  refusals, migration message, sentinel-in-a-choice outcomes.
- `packages/aoa-action-machine/tests/action_machine/intents/access_control/test_roles.py` — match
  semantics, silenced roles, `AnyRole`.
- `packages/aoa-demo/tests/model/test_access_cascade_shapes.py` — the declaration as the demo
  shows it.
