# Mutations — the five adversarial checks of FR-018, as a repeatable recipe

**Date**: 2026-10-24

Each mutation is applied in a temporary copy (`git worktree add <tmp> HEAD` or `cp -R . <tmp>`), never
in the user's working tree. A mutation that does not fail its targeted check means the check is
wrong, not the code. Each row names the edit, the command that must fail, and the neighbouring
control that must still pass. The "targeted check" column names the test task that owns it.

## M1 — a leftover `grant(...)` declaration

- **Edit**: in a scratch action module, write `@check_roles(grant(CustomerRole))` and import the
  module (or run the test that does).
- **Must fail**: the import — `grant` is not a published name any more, so `from aoa.action_machine.intents.check_roles import grant` raises `ImportError` and `grant(CustomerRole)` raises `NameError`.
- **Targeted check**: T012 (`test_check_roles_removed_mechanism.py`).
- **Control**: the same action declared `@check_roles(CustomerRole)` builds and its graph carries one role edge.

## M2 — `@check_roles` removed from an operation

- **Edit**: take an action that declares roles and strip the decorator, leaving no `_role_info`.
- **Must fail**: assembling the capability / running it raises `MissingCheckRolesError` (the mandatory-declaration refusal).
- **Targeted check**: T013 (`test_roles.py`).
- **Control**: the same action with `@check_roles(GuestRole)` assembles and runs.

## M3 — a `SILENCED` role still refused

- **Edit**: declare an action `@check_roles(SilencedRole)` where `SilencedRole` is `@role_mode(RoleMode.SILENCED)`, and give a caller that holds `SilencedRole`.
- **Must fail**: the role gate answers `Refused(gate=CHECK_ROLES)` — a silenced caller role grants nothing.
- **Targeted check**: T013 (`test_roles.py`).
- **Control**: a caller holding an `ALIVE` role is allowed by the same action.

## M4 — a `GuestRole` operation open, then refusing

- **Edit**: an action `@check_roles(GuestRole)` with no object rule allows a caller; add an `@access_decide` method that returns `Refused("REASON")`.
- **Must fail**: the same caller now gets `Refused(gate=ACCESS_DECIDE, reason="REASON")` from `machine.run` and from `machine.check_access_decide`.
- **Targeted check**: T015, T021.
- **Control**: the action without the object rule still allows the same caller.

## M5 — a module-level read inside `@access_decide`

- **Edit**: inside an object rule, read a module-level constant instead of a parameter, a declared
  context key or a resource.
- **Must fail**: the code-isolation check of issue #247. **It is not in the tree** (`graph/validators/`
  holds only entity validators), so until #247 lands this mutation is verified by review and a
  recorded search — the result states which of the two produced it.
- **Targeted check**: T017 (recorded search over migrated declarations) and T025 (review in the demo).
- **Control**: a neighbouring object rule that reads only `params`, `connections` and its declared
  context keys passes the same review/search.

## How to run them

For M1–M4, run the owning test module with the mutation applied and with it reverted, in the
temporary copy, and record both outcomes. For M5, record the search command and its hits in
`evidence/role-check-search.md` and note that no automated check yet exists. Restore the copy after
each mutation; the user's working tree is never the place a mutation is applied.

## Recorded outcomes — Procedure 3 (T014)

M1 and M2 were run as scratch scripts under `archive/mutations/` (git-ignored, outside the working
tree) against the installed package.

### M1 — reintroduced `grant` refuses

```text
1) import of `grant`: ImportError: cannot import name 'grant' from 'aoa.action_machine.intents.check_roles'
2) declaration @check_roles(grant(Role)): NameError: name 'grant' is not defined
```

Targeted check: `test_check_roles_removed_mechanism.py::test_grant_import_fails` (green).
Neighbouring control: `test_check_roles_class_roles.py` accepted forms (green).

### M2 — an operation with no `@check_roles` is refused

```text
MissingCheckRolesError: NoRolesAction has no @check_roles declaration; `_role_info['spec']` is required.
```

Targeted check: `test_roles.py::test_check_raises_when_the_action_declares_no_roles` (green).
Neighbouring control: `test_roles.py::test_admin_allowed_with_matching_role` (green).

The scratch files `archive/mutations/m1_reintroduce_grant.py` and
`archive/mutations/m2_remove_check_roles.py` are the record; nothing in the user's working tree was
mutated, so there is nothing to restore.

