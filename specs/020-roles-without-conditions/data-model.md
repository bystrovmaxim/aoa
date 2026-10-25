# Data Model — Roles Without Conditions

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-24

The feature removes fields rather than adding them. What remains is written here so the contracts
and the tests agree on the same five things: the declaration, the object rule, the answer, the
published word, and the order the words are decided in.

## Role declaration

The one fact `@check_roles` carries on an action class. "Role" here is the authorization role
(a `BaseRole` subclass held in `UserInfo.roles`); the relationship "endpoint role" that #261
introduced — the container on a field, checked by `entity_role_compatibility_validator` — is a
different axis, shares no type and is never checked by the role step.

| Field | Type | Rules |
| --- | --- | --- |
| `spec` | `type[BaseRole] \| tuple[type[BaseRole], ...]` | Exactly one of: a role type; a non-empty tuple/list of role types; several positional role types (equivalent to a tuple). A `BaseRole` subclass is required for every member. |
| `alternatives` | derived tuple | `(spec,)` when `spec` is a type, otherwise `spec`. Duplicates are collapsed by identity, first occurrence winning (R4). |
| `sentinel` | derived | `guest` when `GuestRole` is among the alternatives; else `any` when `AnyRole` is among them; else `none`. |

Storage: `cls._role_info = {"spec": ...}`. Nothing else is stored. Removed keys: `grants`,
`guard`, `guard_reason` (R1).

Validation, in this order, all at class definition:

1. no argument at all → refused (`RoleSpecTypeError`);
2. a string, an empty collection, a non-role object, or a leftover condition-bearing object →
   refused, naming the accepted forms and, where the value came from a removed mechanism, naming
   `@access_decide`;
3. any of the keywords `guard`, `guard_reason`, `when` → refused with the migration message
   (R5);
4. any other unknown keyword → refused, naming the accepted forms;
5. a role marked `RoleMode.UNUSED` → refused; `RoleMode.DEPRECATED` → warning (unchanged).

Match semantics (the role step):

| Declaration shape | Answer |
| --- | --- |
| contains `GuestRole` | allow, regardless of the caller's roles |
| contains `AnyRole`, no `GuestRole` | allow when the caller holds at least one role that is not silenced |
| roles only | allow when `issubclass(user_role, required)` holds for at least one active caller role and one alternative; `Refused(gate=CHECK_ROLES)` otherwise |
| no `@check_roles` at all | `MissingCheckRolesError` while the capability is assembled (unchanged) |

`RoleMode.SILENCED` caller roles are dropped before matching (unchanged).

## Object rule

The optional `@access_decide` method of an operation. Unchanged by this feature; restated because
it receives the conditions the declaration loses. The specification and this model say *object
rule*; the code says *object check* in places (`object_gate`,
`ActionGraphNode.get_access_decide_graph_node`) — one concept, two names, and neither is renamed by
this feature.

| Field | Type | Rules |
| --- | --- | --- |
| `method` | async, name ends `_access_decide` | at most one per operation, never inherited |
| `description` | text | declared in the decorator, non-empty |
| `required_context` | declared keys | dot-paths such as `user.user_id` or `user.roles`; the method receives a `ContextView` limited to them |
| `branches` | code | order is the author's; each ends in `Allowed()`, `Refused(reason?)` or `Undecided` |

The rule may read roles through a declared key and reason about them; it may not repeat the match
that `@check_roles` already performs (FR-008).

## Answer

| Type | Fields | Rules |
| --- | --- | --- |
| `Allowed` | `kind="allowed"` | no gate |
| `Refused` | `kind="refused"`, `gate`, `reason?` | `reason` is non-empty text when present; absent when no declared rule produced it. Defaults to `gate=ACCESS_DECIDE` |
| `Undecided` | `kind="undecided"`, `gate`, private `cause` | the cause is absent from every wire form |

`FORBIDDEN_OBJECT` stays the shared `Refused()` an object rule returns for "no such object" and
"not yours".

## Published word

`Gate` is a `StrEnum` with exactly three members after this feature: `AUTH_COORDINATOR`,
`CHECK_ROLES`, `ACCESS_DECIDE`. Both `Refused.gate` and `Undecided.gate` are typed by it, so data
naming `WHEN` or `GUARD` fails validation instead of being coerced (R7).

## Decision order

| Phase | Steps | Words that can end it |
| --- | --- | --- |
| before the run | who is calling, which roles are held | `AUTH_COORDINATOR`, `CHECK_ROLES` |
| inside the run | the object rule | `ACCESS_DECIDE` |

The seam between the phases is where it is today: the machine decides the first phase before the
run exists and the second after connection validation. A step that raises produces `Undecided`
naming its own word, with the failure kept as its cause.

## Graph projection

| Item | Before | After |
| --- | --- | --- |
| `Action → Role` edge | one per grant, carrying `when`/`when_reason` | one per distinct role, no condition data |
| action node properties | `description`, `guard`, `guard_reason` | `description` only, among the unchanged rest |
| `AccessDecide` node | present when the operation declares one | unchanged: description plus required-context companions |
| role node | shared per role, mode in properties | unchanged |
| exported edge `properties` | `{}` | `{}` (no wire change) |
