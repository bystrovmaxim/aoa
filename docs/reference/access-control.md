# Access control reference

Declare roles on the operation class. Declare an object rule only when permission
also depends on the selected object, caller attributes or input. For a complete
program and migration steps, use the [guide](../how-to/roles-and-object-rules.md).
For a guided introduction, use the [tutorial](../tutorials/step-03-authorization-and-roles.md).

## Role declarations

Import `check_roles` from `aoa.action_machine.intents.check_roles` and role types
from `aoa.action_machine.auth`. Declare application roles as subclasses of
`ApplicationRole`; pass classes, not instances or role-name strings.

| Declaration | Invariant |
| --- | --- |
| `@check_roles(Role)` | A caller role must derive from the required role |
| `@check_roles(RoleA, RoleB)` | Either alternative is enough |
| `@check_roles((RoleA, RoleB))` or one list | Same OR choice as positional roles |
| Repeated roles | Deduplicated, preserving first-declaration order |
| `@check_roles(GuestRole)` | No role restriction; an object rule can still refuse |
| `@check_roles(GuestRole, Role)` | The guest alternative keeps the whole role layer open |
| `@check_roles(AnyRole)` | At least one active role; a user identifier alone is insufficient |
| `@check_roles(AnyRole, Role)` | Any active role suffices, including an unrelated application role |
| Caller role marked `SILENCED` | Ignored before matching, including for `AnyRole` |
| Required role marked `UNUSED` | `RoleSpecTypeError` during decorator evaluation |
| Required role marked `DEPRECATED` | `DeprecationWarning` during decorator evaluation |
| Missing `@check_roles` | `MissingCheckRolesError` during model assembly; no implicit public access |

`GuestRole` and `AnyRole` describe requirements; they are not role assignments for
`UserInfo.roles`. A declaration with no role arguments, an empty collection, an
invalid class or a name string remains invalid. Conditions are not role specs.
The [declaration lesson](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py)
checks legal neighboring forms beside the removed forms.

## Object rules

| Contract | Required form |
| --- | --- |
| Decorator import | `from aoa.action_machine.intents.access_decide import access_decide` |
| Declaration | One async method in the operation's own class; inherited checks do not become its object rule |
| Name and description | Name ends in `_access_decide`; description is nonblank |
| Parameters | `(self, params, box, connections)` |
| Declared context | `@context_requires(...)` below `@access_decide`, adding the trailing `ctx: ContextView` |
| Return | An annotated `Verdict` or supported verdict subtype, returning `Allowed`, `Refused` or `Undecided` |
| No declaration | Object step passes; role requirements still apply |
| Policy refusal | `Refused("REASON")`; `Refused()` and `FORBIDDEN_OBJECT` are valid reasonless refusals |
| Failure or non-verdict return | `Undecided` at `ACCESS_DECIDE`; execution raises `AccessUndecided` |

Keep a shared condition in a branch that every admitted caller reaches. Branch
order belongs to the rule; a successful role match does not choose a condition
for that role. See [branch order](../../examples/step_03_authorization_and_roles/17_branch_order.ipynb).

## Gate and verdict formats

Import `Gate`, `Allowed`, `Refused`, `Undecided`, `Verdict` and `FORBIDDEN_OBJECT`
from `aoa.action_machine.intents.access_control`.

| Gate value | Meaning and timing |
| --- | --- |
| `AUTH_COORDINATOR` | Published authentication refusal word; credential verification belongs to the transport/coordinator boundary. The machine's authentication step itself passes. |
| `CHECK_ROLES` | Role requirement, before an execution run starts |
| `ACCESS_DECIDE` | Optional object rule, inside execution after connection validation and before business aspects |

There are exactly three enum members, with identical names and string values.
`WHEN` and `GUARD` are absent; they are not deprecated aliases.

| Answer | JSON form | Execution behavior |
| --- | --- | --- |
| Allowed | `{"kind": "allowed"}` | Continue |
| Refused | `{"kind": "refused", "gate": "ACCESS_DECIDE", "reason": "ORDER_CLOSED"}` | Raise `AccessDenied` |
| Undecided | `{"kind": "undecided", "gate": "ACCESS_DECIDE"}` | Raise `AccessUndecided`; the cause is not part of the wire payload |

A refusal's reason can be null, but a supplied reason cannot be empty or
whitespace-only. `Refused` and `Undecided` default to `ACCESS_DECIDE`. Verdicts are
immutable and reject extra fields. The gate is available on `exc.verdict`, not
on a numeric authorization level.

A query uses the same declarations and returns a verdict instead of throwing a
policy refusal. It does not execute business aspects, use the execution cache,
or publish the execution lifecycle. It can prepare dependencies and connections
and publishes its access-query events. A later run checks again. The
[query/execution script](../../examples/step_03_authorization_and_roles/07_three_answers.py)
and [notebook](../../examples/step_03_authorization_and_roles/07_three_answers.ipynb)
assert identical refusal payloads for unchanged inputs.

## Migration refusals

| Removed form | Exception | When |
| --- | --- | --- |
| Import `grant` or `Grant` | `ImportError` | Import |
| `guard=`, `guard_reason=`, `when=` | `RoleSpecTypeError` | Decorator expression evaluation |
| `Gate.WHEN`, `Gate.GUARD` | `AttributeError` | Attribute access |
| `Gate("WHEN")`, `Gate("GUARD")` | `ValueError` | Enum conversion |
| `Refused.model_validate({"gate": "WHEN"})` or `GUARD` | Pydantic `ValidationError` | Payload validation |

Exact keyword messages from the executed migration scenario:

```text
RoleSpecTypeError: @check_roles declares roles only; 'guard' belonged to the removed condition layer. Move the condition into the operation's @access_decide method and return Refused("REASON") or FORBIDDEN_OBJECT for the branch that used to refuse.
RoleSpecTypeError: @check_roles declares roles only; 'guard_reason' belonged to the removed condition layer. Move the condition into the operation's @access_decide method and return Refused("REASON") or FORBIDDEN_OBJECT for the branch that used to refuse.
RoleSpecTypeError: @check_roles declares roles only; 'when' belonged to the removed condition layer. Move the condition into the operation's @access_decide method and return Refused("REASON") or FORBIDDEN_OBJECT for the branch that used to refuse.
```

On Python 3.12, missing members report `AttributeError: type object 'Gate' has no attribute 'WHEN'` or the same message naming `GUARD`.

The enum conversion errors are exactly `ValueError: 'WHEN' is not a valid Gate` and
`ValueError: 'GUARD' is not a valid Gate`. For verdict parsing, each error is at
`gate`, with type `enum` and message
`Input should be 'AUTH_COORDINATOR', 'CHECK_ROLES' or 'ACCESS_DECIDE'`.
The complete Pydantic output, including its version-specific help URL, is saved
in the executed notebook.

Python's import messages begin exactly with
`cannot import name 'grant' from 'aoa.action_machine.intents.check_roles'` or
`cannot import name 'Grant' from 'aoa.action_machine.intents.check_roles'`.
Python appends the installed module's absolute path in parentheses. The
[script](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.py) · [executed notebook](../../examples/step_03_authorization_and_roles/24_role_declarations_and_migration.ipynb) prints the full actual messages
and asserts the stable import names. The former condition exception types
`AccessConditionAsyncError` and `ConditionReasonError` are also removed from
`aoa.action_machine.exceptions`.

Execution refusal messages follow these exact forms:

```text
AccessDenied: Access denied by CHECK_ROLES.
AccessDenied: Access denied by ACCESS_DECIDE: ORDER_CLOSED
```

The first has no reason; the second includes the rule's reason. The
[guest scenario](../../examples/step_03_authorization_and_roles/14_guest_and_any.py)
checks the second string; the [cascade scenario](../../examples/step_03_authorization_and_roles/13_cascade.py)
checks the role and object boundaries.

## Graph exports

| Exported fact | Current representation |
| --- | --- |
| Required role | One `@check_roles` edge per distinct role in declaration order |
| Role-edge properties | Empty object; no `when` or `when_reason` |
| Action properties | Description; no `guard` or `guard_reason` |
| Object rule | A separate `AccessDecide` node, linked by `@access_decide` |
| Context used by the rule | `RequiredContext` companions for the declared keys |

The existing graph schema continues to describe these role and object-rule
nodes and edges; no additional authorization marker is required on the action.
Regenerate cached graph data to remove the former condition data.
The [script](../../examples/step_03_authorization_and_roles/25_access_graph.py) · [executed notebook](../../examples/step_03_authorization_and_roles/25_access_graph.ipynb) verifies the exported properties and context
companion. Graph metadata describes declarations; it does not replace a runtime
access check.
