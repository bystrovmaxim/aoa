# Contract — the two refusals and what they must say

**Feature**: `specs/011-role-mode-declaration` | **Date**: 2026-10-19

Both refusals raise `RoleModeDeclarationError`. They are the feature's only user-visible output, so their content is a contract, not a style choice. The wording below is the wording verified in `evidence/probes/refusal_probe.py`; the plan fixes it so tests can assert on parts of it without inventing a second sentence.

## Refusal 1 — an argument that is not a member

```text
@role_mode(ViewerRole): expected a RoleMode member, got 'alive'. Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
```

| Property | Requirement |
| --- | --- |
| Error type | `RoleModeDeclarationError` |
| Names the decorator | `@role_mode` |
| Names the role | the class's `__qualname__` |
| Names the received value | `repr` of the argument, so `None` ≠ `'None'` and `42` ≠ `'42'` |
| Names the allowed set | all four members, in enum-definition order, from the enum itself |
| Fires when | the decorator is applied to the class, before `_role_mode_info` is written |
| Tested for | the five kinds named in the issue, the `.value` string, the keyword form, and a foreign enum member |

## Refusal 2 — the decorator without parentheses

```text
@role_mode: expected a RoleMode member, got the class Bare itself — did you mean @role_mode(RoleMode.ALIVE)? Allowed: ALIVE, DEPRECATED, SILENCED, UNUSED.
```

| Property | Requirement |
| --- | --- |
| Error type | the same |
| Names the decorator and the role | `@role_mode` and the class that arrived as the argument |
| Names the received value | the class, identified as a class rather than as a value |
| States the correction | the missing parentheses and one member to write inside them |
| Names the allowed set | the same four, in the same order (FR-020) |
| Fires when | in the decorator's own call, before the class name is bound |
| Must not appear as | a later `TypeError` from `issubclass()` |

## What is not a refusal of this feature

| Situation | Answer | Owner |
| --- | --- | --- |
| the class is not a `RoleModeIntent` | `DecoratorArgumentTypeError` | `RoleMode.declared_for`, when read |
| the role carries no `_role_mode_info` | `RoleModeDeclarationError`, "has no _role_mode_info" | `declared_for`, unchanged |
| the metadata entry is not a member | `RoleModeDeclarationError`, "has invalid _role_mode_info['mode']" | `declared_for`, unchanged (no list of four — decided in clarification) |
| `UNUSED` required through `@check_roles` | `RoleSpecTypeError` | `_validate_required_role_modes` |
| `DEPRECATED` required through `@check_roles` | `DeprecationWarning`, requirement accepted | `_validate_required_role_modes` |
| `SILENCED` held by the user | grants nothing | the access check |

## What the refusals must not become

1. **Not a warning.** A declaration the framework will refuse later is refused now; there is no window in which a wrong mode is accepted with a warning.
2. **Not a coercion.** `"alive"` is never read as `RoleMode.ALIVE`, at either moment.
3. **Not a second vocabulary.** No new error class, no new public helper, no change to any message of the rows in the table above.
