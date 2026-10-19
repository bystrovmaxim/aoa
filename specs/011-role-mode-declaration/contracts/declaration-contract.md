# Contract — what `@role_mode` accepts and what it stores

**Feature**: `specs/011-role-mode-declaration` | **Date**: 2026-10-19

This is the interface the change establishes. It is written as the contract a caller may rely on, not as an implementation sketch; the checker itself is one `isinstance` in one function.

## The call

```python
@role_mode(RoleMode.ALIVE)
class ViewerRole(ApplicationRole):
    name = "viewer"
    description = "Can read the catalog"
```

`role_mode(mode)` is a decorator factory: it takes exactly one argument and returns a class decorator. The annotation stays `mode: RoleMode`.

## What is accepted

| Argument | Accepted | Stored in `_role_mode_info["mode"]` |
| --- | --- | --- |
| `RoleMode.ALIVE` | yes | the member itself (identity) |
| `RoleMode.DEPRECATED` | yes | the member itself |
| `RoleMode.SILENCED` | yes | the member itself |
| `RoleMode.UNUSED` | yes | the member itself |

Nothing else is accepted. In particular: `"alive"` and the other three string values, `RoleMode.ALIVE.value`, a number, `None`, an arbitrary object, a member of any other enum, and the role class itself (the `@role_mode` form without parentheses).

## What is stored

1. The attribute is `_role_mode_info`, a plain `dict` with the single key `"mode"`.
2. The value is the member handed in — compared by identity, not by equality.
3. The attribute is written only after the argument has passed; a refused declaration writes nothing (`FR-005`).
4. The decorated class is returned unchanged; the decorator adds the attribute and does nothing else (`FR-009`).
5. Inheritance is untouched: a subclass without its own decorator reads its parent's entry through `getattr`.

## When the refusal happens

| | |
| --- | --- |
| Moment | while the statement declaring the role is executed, at the decorator's application to the class |
| Import | yes — the module that declares the role fails to import; no graph is assembled, no call is served |
| What has run | the class body has run, and a wrong argument is refused before `_role_mode_info` is written |
| What exists | the class object; its name is not bound |
| Error | `RoleModeDeclarationError`, the public `TypeError` subclass the package already exports |

## What this contract does not cover

1. **The target's base.** `@role_mode` does not check that the class is a `RoleModeIntent`; `RoleMode.declared_for` refuses a foreign class with `DecoratorArgumentTypeError` when something reads it. Unchanged.
2. **The target's type.** A non-class target keeps `DecoratorTargetError`, raised before the mode is judged. Unchanged.
3. **Fitness for a context.** `UNUSED` cannot be required, `DEPRECATED` warns, `SILENCED` grants nothing. These stay rules of `@check_roles` and the access check; the decorator knows only membership (`FR-011`).
4. **A missing or corrupted entry.** A role with no `_role_mode_info`, or with an entry a human wrote, is still refused by `declared_for`, with its current wording (`FR-010`).

## Compatibility

All 69 declaration sites in this repository pass a member (measured: `evidence/scan_role_mode_calls.py`), so the contract refuses nothing that exists. The four prose placeholders (`@role_mode(...)`, `@role_mode(RoleMode.…)`) are text, not calls, and are untouched.
