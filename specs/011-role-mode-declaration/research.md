# Phase 0 — Research: a role's mode is refused where it is declared, not where it is read

**Feature**: `specs/011-role-mode-declaration` | **Date**: 2026-10-19

Every unknown in the plan's Technical Context is resolved below. The measurements were taken on this tree (branch `feature/issue-233-role-mode-at-declaration`, from `main` at `45aeee3f`) with runnable probes and a scan, not from the issue's text; where the issue and the tree disagree, the tree is reported.

## R1 — Where the two checks live, and why there are two

**Decision**: two checks in one module, `intents/role_mode/role_mode_decorator.py`, at two points of one call chain:

1. **In `role_mode(mode)` itself — the missing-parentheses check.** `@role_mode` without parentheses passes the class where the mode belongs, so `role_mode` is what receives it; the refusal names the class, which is available here.
2. **In the returned `decorator(cls)` — the set check.** `cls` is needed for the message ("which role"), and this is the point before `_role_mode_info` is written.

**Rationale**

1. The order was measured, not assumed: the decorator expression is evaluated **before** the class body, and the decorator is applied **after** the class is created. Refusing in `role_mode(...)` for an ordinary argument would be a step earlier but could not name the role; refusing in `decorator(cls)` keeps import-time failure and names the role. This is the decision recorded in the spec's clarification session.
2. The bare form cannot be caught by the set check at all: `X = role_mode(X)` returns the inner function and never calls it, which is why the check must sit in `role_mode` itself. Measured today: `ViewerRole` becomes `<function role_mode.<locals>.decorator>`, carries no metadata, and the first reader dies with `TypeError: issubclass() arg 1 must be a class`.
3. Both checks raise the same error class, so a caller's `except RoleModeDeclarationError` covers the two roads to one mistake.

**Alternatives considered**

- **Check only in `role_mode(mode)`.** Rejected: the message could not name the role, which is what the clarification chose the application moment for.
- **Check only in `decorator(cls)`.** Rejected: the bare form stays silent, and the spec now requires it (FR-019).
- **Validate in `RoleMode.declared_for`.** Rejected: it is the defect — validation only happens if something reads the role.

**Evidence** — the evaluation order, measured:

```text
$ .venv/bin/python
decorator expression evaluated, arg = alive
class body runs
decorator applied to Viewer
```

## R2 — The error keeps its existing name

**Decision**: both checks raise `RoleModeDeclarationError`; its docstring widens to state that the argument handed to `@role_mode` may also be the cause, and no new exception module is created.

**Rationale**

1. The class is already public and exported (`exceptions/__init__.py:53,135`), is a `TypeError` subclass, and already names the family "a role's mode is not usable".
2. FR-019's bare form is the same family: the value that arrived is not a mode.
3. No new name means no growth of the public vocabulary (SC-005) and nothing for the demo, the adapters or the docs to learn.

**Alternatives considered**

- **A second error (`RoleModeArgumentError`).** Rejected: two names for one rule, and a caller with `except RoleModeDeclarationError` would start missing the new one — the very failure mode the repository's refusal families avoid (`@check_roles` raises `RoleSpecTypeError` for every role-spec mistake).
- **`DecoratorArgumentValueError`.** Rejected: it means "right type, unusable value" (negative count, empty string); a string where an enum member belongs is the wrong type, and the role-specific error already exists.

## R3 — The allowed list comes from the enum, in declaration order

**Decision**: one module-level constant in `role_mode_decorator.py`, built from the enum:

```python
_ALLOWED_MODES = ", ".join(member.name for member in RoleMode)
```

**Rationale**

1. `Enum` iterates in definition order (`ALIVE, DEPRECATED, SILENCED, UNUSED`) — stable across runs and processes, unlike a set.
2. A literal string would drift the day a fifth member is added; deriving it means the message cannot disagree with the set the check enforces.
3. One constant is enough: both messages quote it, and the plan does not add a public API for presentation.

**Alternatives considered**

- **A `RoleMode` classmethod (`RoleMode.names()`).** Rejected: presentation does not belong on the lifecycle enum, and the enum is public API — its surface would grow for a refusal text.
- **`sorted(...)` or `set(...)`.** Rejected: the first invents an order the enum does not have; the second has no stable order at all.

## R4 — The message shape, measured against its neighbours

**Decision**: the two messages below, both naming the decorator, the role, the value as `repr`, and the four member names.

```text
@role_mode(ViewerRole): expected a RoleMode member, got 'alive'. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
@role_mode: expected a RoleMode member, got the class Bare itself — did you mean @role_mode(RoleMode.ALIVE)? Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
```

**Rationale**

1. The shape follows the package's existing refusals: `@check_roles expected a BaseRole subclass, got {spec!r}.` and `@depends(...): ... got {mode!r}.` — decorator, then what was expected, then what arrived.
2. `!r` is what satisfies FR-003: measured, `None` renders `None` and `"None"` renders `'None'`; `42` renders `42` and `"42"` renders `'42'`; a foreign member renders `<Other.ALIVE: 'alive'>`, which names its class.
3. The role's `__qualname__` matches how `declared_for` already speaks (`Role {role.__qualname__} ...`), so the two refusals read as one family without sharing a sentence.
4. The bare-form message names the class it received and a member to write, so the developer does not have to look up either.

**Evidence** — the intended wording, run against the real `RoleMode` (`evidence/probes/refusal_probe.py`):

```text
wrong string: @role_mode(ViewerRole): expected a RoleMode member, got 'alive'. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
wrong number: @role_mode(CounterRole): expected a RoleMode member, got 42. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
none: @role_mode(EmptyRole): expected a RoleMode member, got None. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
other enum: @role_mode(ForeignRole): expected a RoleMode member, got <Other.ALIVE: 'alive'>. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
missing parentheses: @role_mode: expected a RoleMode member, got the class Bare itself — did you mean @role_mode(RoleMode.ALIVE)? Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
accepted member: accepted -> <class 'Good'>; stored verbatim: True
```

## R5 — What the tests add, and what they deliberately do not repeat

**Decision**: one new module, `packages/aoa-action-machine/tests/action_machine/intents/role_mode/test_role_mode_decorator_invariants.py`, mirroring the source tree (`intents/role_mode/` has no test directory today). It covers: four members accepted (identity), the returned class is the same object, the five refusal kinds plus the foreign enum and the keyword form, the bare form, the message content, the no-metadata-on-refusal rule, and `declared_for`'s two guards. The three context rules are **not** re-tested here: `test_role_checker_pr2.py:50` (`UNUSED` → `RoleSpecTypeError`, `DEPRECATED` → warning) and `intents/access_control/test_roles.py:156` (`SILENCED` grants nothing) already own them, and the feature leaves them untouched — the closing run proves they stayed green.

**Rationale**

1. `intents/role_mode/` is one of four intent directories without a test module of its own (with `action_schema`, `on`, `sensitive`), and the invariants of one decorator deserve one module rather than an addition to `test_check_roles_class_roles.py`, which tests the decorator's consumers.
2. Duplicating the context-rule tests would tempt a future edit to "fix" one copy, and the point of FR-011 is that those rules live with their consumers — the tests should too.
3. FR-005 (no metadata on refusal) is not observable through decorator syntax, where the class is never bound; the test applies the returned decorator to a class by hand and asserts `_role_mode_info` is absent.

**Alternatives considered**

- **Extend `test_check_roles_class_roles.py`.** Rejected: that module's subject is `@check_roles`; it already carries one `@role_mode` smoke test, which stays.
- **A property-based / hypothesis suite.** Rejected: the input space is five named kinds and one bare form, each with a message obligation; four `pytest.raises` cases test it more legibly than a generator.

## R6 — AI-CORE blocks: both symbols get one

**Decision**: `role_mode` (public module-level function, rewritten) and `RoleModeDeclarationError` (public class, docstring widened) each gain an `AI-CORE-BEGIN/END` block.

**Rationale**

1. Principle IV applies to both: a public module-level function and a public class. The function's block states the closed set — the rule it now enforces; the class's block states which two moments raise it and what the message always contains.
2. The precedent is in the exception family itself: 7 of 55 exception modules carry a block, and `missing_check_roles_error.py` — the error raised beside this one by `@check_roles` — is among them. Adding one here follows the family rather than inventing a shape.
3. Both symbols are being edited anyway, and the constitution's debt clause says debt is paid as files are touched.

**Alternatives considered**

- **Function only, exception left block-less.** Rejected: measured 7 of 55 exceptions already carry blocks, so "the family has none" is not true and the omission would be a new gap rather than a preserved style.
- **Neither.** Rejected: the function is the change's centre, and principle IV names module-level functions explicitly.

## R7 — Where the invariant is documented, and in what shape

**Decision**: `docs/reference/intents-and-invariants.md`, a bullet in `## Mandatory roles` (checked: the page mentions no `@role_mode` today), plus one runnable snippet showing the refusal. The changelog gets one article at the top of `docs/CHANGELOG.md`, dated `2026-10-19`, in the form the two existing dated entries use.

**Rationale**

1. The page already opens that section with the role vocabulary and `@check_roles`; a reader looking for "what may I put in `@role_mode`" arrives there.
2. Constitution VI.4 asks every case to be shown: the bullet shows one accepted declaration and one refusal, which is the whole feature.
3. The changelog form is reader-facing prose, not a file list (constitution VI.3), matching the 2026-10-18 entry.

**Alternatives considered**

- **A new page under `docs/explanation/`.** Rejected: the invariant belongs beside the others, and a new page is not what a one-rule change needs.
- **Only a docstring change.** Rejected: FR-017 and the issue both name the reference page.

## R8 — The corpus does not move

**Decision**: no call site changes; the scan is kept as evidence so the claim stays reproducible.

**Rationale**: `evidence/scan_role_mode_calls.py` finds 69 real calls, all members (59 `ALIVE`, 7 `SILENCED`, 2 `DEPRECATED`, 1 `UNUSED`) and 4 prose placeholders. Zero non-member arguments, so the new check refuses nothing in the repository — which is what makes SC-003 checkable by the closing run rather than by editing files.

**Evidence**

```text
$ python3 specs/011-role-mode-declaration/evidence/scan_role_mode_calls.py
real calls: 69 {'RoleMode.ALIVE': 59, 'RoleMode.SILENCED': 7, 'RoleMode.DEPRECATED': 2, 'RoleMode.UNUSED': 1}
by carrier: {'.py': 64, '.ipynb': 1, '.md': 4}
placeholders in prose: 4
arguments that are neither a member nor a known placeholder: 0
```

## R9 — The check type-checks cleanly

**Decision**: the `isinstance(mode, type)` branch and the `isinstance(mode, RoleMode)` branch stay as written, with no casts and no `type: ignore`.

**Rationale**: mypy accepts both on a parameter annotated `RoleMode` — probed (`evidence/probes/typecheck_probe.py`): the only remark was an unused ignore in the probe's own calling helper, not on either check. Ruff and pylint see ordinary `isinstance` calls, so no suppression is introduced on a function the check run lints.
