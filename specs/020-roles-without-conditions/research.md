# Research — Roles Without Conditions

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-24

Each decision below is what planning settled, why, and what it rejected. Every claim about
the current repository was read from the source named beside it, not assumed.

## R1 — What `@check_roles` stores

**Decision**: `cls._role_info` keeps one key, `"spec"`, holding a role type or a tuple of role
types. `resolve_grants`, `resolve_guard` and `resolve_guard_reason` are deleted;
`resolve_check_roles` and `resolve_role_mode` stay.

**Rationale**: the spec is already the canonical form — one type or a tuple — and the other two
keys existed only because a grant could carry a condition. Two representations of the same fact
invite drift; the resolver in `check_roles_intent_resolver.py:29-59` becomes three methods shorter.

**Alternatives rejected**: keeping `"grants"` as a normalized list of bare roles. It adds a second
shape with no consumer once conditions are gone.

## R2 — Accepted declaration forms

**Decision**: `@check_roles` accepts one or more positional role types, or a single tuple/list of
role types. Several positional roles and a tuple mean the same thing. Sentinels are allowed in
either form.

**Rationale**: both forms are in use. `packages/aoa-demo/src/aoa/demo/model/access_cascade/actions/two_path_match_shape_action.py:19`
declares `@check_roles(CascadeTraineeRole, CascadeDomainSpecialistRole)` — two positional roles —
and no file in the repository uses the tuple form. Issue #248 §2.1 names a bare role, a tuple,
`GuestRole` and `AnyRole`; keeping the positional form costs nothing and removes a break that the
specification would otherwise have introduced by accident.

**Alternatives rejected**: making the tuple the only multi-role form. It would reject a working
declaration without any requirement asking for it.

## R3 — What a sentinel means inside a choice

**Decision**: the alternatives are read strongest first. If `GuestRole` is among them the
operation is open; otherwise if `AnyRole` is among them the caller needs at least one role that is
not silenced; otherwise matching is `issubclass(user_role, required)` over the caller's active
roles.

**Rationale**: today a sentinel inside a declaration matches nothing, because the framework never
places a sentinel in `UserInfo.roles` (`grep` over `packages/*/src` finds no such assignment), so
`@check_roles(GuestRole, CustomerRole)` silently refuses everyone — the opposite of what a reader
takes from it. The maintainer's rule is that a declaration is a choice between alternatives and a
sentinel keeps the meaning it has alone (Clarifications, second question of the session).

**Alternatives rejected**: refusing the mixed declaration (contradicts the maintainer's answer);
keeping the unsatisfiable alternative and documenting it (leaves a trap in the public surface).

## R4 — The same role named twice

**Decision**: duplicates collapse by identity, in declaration order, for both matching and the
graph.

**Rationale**: two identical `Action → Role` edges carried information only while each grant could
have its own `when=`. With conditions gone they are the same edge twice. Collapsing keeps the
declaration valid — `@check_roles((A, A))` is not a mistake worth an exception — and keeps the
graph honest.

**Alternatives rejected**: refusing duplicates as a declaration error (a new failure mode for a
declaration that harms nobody).

## R5 — How the removed names go away

**Decision**: `intents/check_roles/grant.py` is deleted, so `from ...check_roles import grant` and
`Grant` fail as absent names. `check_roles` is declared as `check_roles(*specs, **unsupported)`;
any unsupported keyword is refused at class definition with a `RoleSpecTypeError`, and when the
keyword is `guard`, `guard_reason` or `when` the message names `@access_decide` and shows the
replacement shape.

**Rationale**: issue #248 acceptance criterion 1 asks for a clear message where a declaration can
still be written, and the maintainer chose full removal with a migration message. Python alone
would answer `TypeError: check_roles() got an unexpected keyword argument 'guard'`, which names
nothing a migrating author can act on.

**Alternatives rejected**: a tombstone function that raises when called (a dead public name kept
alive); letting the interpreter's `TypeError` stand (no guidance).

## R6 — Code that loses its last user

**Decision**: delete `intents/check_roles/reason_validation.py`
(`require_reason_alongside`), `exceptions/access_condition_async_error.py`
(`AccessConditionAsyncError`) and `exceptions/condition_reason_error.py` (`ConditionReasonError`),
with their imports, `__all__` entries and tests.

**Rationale**: each described one rule of the removed mechanism — a condition and its reason are
declared together, a condition must be synchronous — and nothing else in the repository uses them
(`grep` over `packages/*/src`: the only readers are `check_roles_decorator.py:224` and
`grant.py:35`, both of which go away). Vulture inspects `packages/aoa-action-machine/src`, so dead
code there is a check-run concern as well as a design one.

**Note**: `exceptions/__init__.py` already lists `AccessConditionAsyncError` and
`AuthorizationError` twice each in `__all__` (`__init__.py:64-65`, `:77-78`). The duplicate of a
removed name disappears with the name; the other duplicate is pre-existing and is left alone.

**Alternatives rejected**: keeping the exceptions as reserved public API. A published exception
with no raiser documents a mechanism the framework no longer has.

## R7 — The published vocabulary

**Decision**: `Gate` keeps `AUTH_COORDINATOR`, `CHECK_ROLES`, `ACCESS_DECIDE`. `Refused.gate` and
`Undecided.gate` are typed by that enum, so an answer rebuilt from data that names `WHEN` or
`GUARD` fails validation as an unknown member.

**Rationale**: the words are a published contract (`gate.py:57-70`). Deprecated members that are
never emitted keep every consumer branching on states the framework cannot produce, and a stored
answer that claims one would be trusted instead of rejected.

**Alternatives rejected**: keeping `WHEN`/`GUARD` as deprecated enum members. The issue's open
question 1 asked exactly this, and criterion 1 answers it: gone from the public API.

## R8 — The cascade

**Decision**: `GATES_BEFORE_RUN` becomes `(Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES)`;
`GATES_AT_OBJECT` stays `(Gate.ACCESS_DECIDE,)`; `guard_answer` and `guard_gate` are deleted with
their `__all__` entries and their entries in `_STEPS`; the module header states three ordered
steps and three answers instead of four and five.

**Rationale**: `cascade.py:86` and `:205-211` are the only places that name `GUARD` as a step. The
seam between the pre-run phase and the in-run phase does not move, which is what the machine
depends on.

**Alternatives rejected**: keeping an empty `guard_gate` for compatibility. A step that always
passes is a lie in the ordered list.

## R9 — The role checker

**Decision**: `RoleChecker.check` reads the single spec, applies R3 and answers
`Refused(gate=Gate.CHECK_ROLES)` or `None`. `_spec_from_grants`, the grant loop and the
`role_matched`/`refused_reason` bookkeeping go with them; the module docstring describes one step
with one answer.

**Rationale**: `roles.py:156-172` exists to express "a grant whose condition refused is skipped,
not fatal". With no conditions the loop has nothing to skip.

**Alternatives rejected**: an `AnyRole`-style helper reused by `@access_decide`. The issue excludes
a role helper, and the object rule keeps its own context keys.

## R10 — The graph

**Decision**: `RoleGraphEdge` is built from a role class alone (`properties={}`), and
`get_role_edges` reads the spec and deduplicates per R4. `ActionGraphNode.properties` loses
`guard` and `guard_reason`. The AI-CORE blocks of `Gate`, `Refused`, `Undecided`,
`RoleGraphEdge`, `ActionGraphNode`, `RoleGraphNode`, `CheckRolesIntentResolver` and
`CheckRolesIntent` are rewritten to say what is true after the change. Maxitor is not touched.

**Rationale**: `ActionGraphNode.get_properties` (`action_graph_node.py:105-113`) and
`RoleGraphEdge.__init__` (`role_graph_edge.py:63-76`) are the only carriers. Maxitor reads node
properties generically and filters by `access_decide` as its own node type
(`duckdb_graph_resource.py:1251`), and a search of its Python and TypeScript sources finds no gate
word, so nothing downstream breaks.

**Alternatives rejected**: adding an `authorization="access_decide"` property to the action node —
the `AccessDecide` node already is that statement (spec, Decisions).

## R11 — The demo package

**Decision**: `cancel_order` keeps `@check_roles(CustomerRole)` and gains
`cancel_order_access_decide`, which answers `Refused("ORDER_LOCKED")` for a locked order and
`FORBIDDEN_OBJECT` for another customer's order. `when_refusal_shape_action.py` becomes
`object_rule_refusal_shape_action.py` (`ObjectRuleRefusalShapeAction` — the author's own reason) and
`guard_refusal_shape_action.py` becomes `forbidden_object_shape_action.py`
(`ForbiddenObjectShapeAction` — the shared framework refusal for everyone). `actions/__init__.py`,
`tests/model/test_access_cascade_shapes.py` and `tests/fastapi_mcp_services/test_cancel_order.py`
follow.

**Rationale**: the maintainer chose to rewrite all three on `@access_decide`. The two shapes stay
distinct because what used to separate them — a matched role's condition versus a shared condition —
is now `Refused("REASON")` versus `FORBIDDEN_OBJECT`, which is a real difference a reader learns
from. The old names were reachable only from `actions/__init__.py` and the two test modules, so the
rename is contained.

**Alternatives rejected**: keeping the old file names with new content. A module named
`guard_refusal_shape_action` teaches a word the framework no longer has.

## R12 — Teaching material

**Decision**: rewrite six example pages in place — `02_grant`, `03_guard`, `07_three_answers`,
`13_cascade`, `17_grant_fallback`, `22_reason_required` — with each script and its notebook kept in
step. The numbers 01–23 are preserved (17 keeps two pages). The four suffixes that name the removed
mechanism are renamed to what the page now teaches: `02_object_rule`, `03_shared_object_rule`,
`17_branch_order`, `22_reason_in_branch`. The tutorial sections that teach conditions
(`step-03-authorization-and-roles.md:623-830`, the reason mistake at `:1914-1969`, the migration
note at `:2045`), the reference statements at `intents-and-invariants.md:148-170`, and the glossary
entries are rewritten; a Russian draft sits beside every documentation page written, and drafts stay
outside the commit.

**Rationale**: the maintainer's constraint was the numbering, and page numbers do not move. Keeping
a suffix such as `grant_fallback` would leave the removed word in the tree that FR-015 rewrites and
SC-001 searches, and the tutorial links are rewritten in the same phase, so the rename costs
nothing. Package-level `CHANGELOG.md` files are history and are not rewritten; only
`docs/CHANGELOG.md` receives the new article, last.

**Alternatives rejected**: keeping all file names (leaves four names that teach a removed word);
deleting the pages (contracts the maintainer's decision to keep the numbers).

## R13 — Test migration shape

**Decision**: seventeen test modules name the removed mechanism — fifteen in `aoa-action-machine`,
two in `aoa-demo`. Of those, fifteen keep their subject and are migrated in place (thirteen in the
package plus the demo's two), the grant test is replaced by a removal test
(`test_check_roles_removed_mechanism.py`), and `test_reason_validation.py` is deleted with the
pairing rule it was the only witness of. One module outside the seventeen,
`tests/action_machine/exceptions/test_access_condition_async_error.py`, is deleted because a deleted
exception is all it tested, and two modules outside them are extended with new cases
(`test_check_roles_class_roles.py`, `test_access_decide_context.py`). The `RoleMode` and
cascade-order tests keep their subjects and change only their declarations.

**Rationale**: `grep` over both test trees, matching `grant(`, `guard=`, `guard_reason`, `Grant`,
`Gate.WHEN`, `Gate.GUARD`, finds exactly those seventeen files; the exception module that is also
deleted does not appear in that search because it names the exception rather than the declaration.
The adversarial mutations FR-018 lists are added as tests inside these modules rather than in a new
directory, so a reader looking for "what the role layer promises" finds them where the rest of the
role tests live.
