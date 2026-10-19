# Phase 1 — Data model: the role mode as declaration data

**Feature**: `specs/011-role-mode-declaration` | **Date**: 2026-10-19

The feature adds no storage and no new type. It narrows what one existing attribute may hold, and it adds two refusal messages. The entities below are the ones the change reasons about.

## RoleMode (the closed set)

| Member | Value | Definition index | Meaning | Consumer that reads it |
| --- | --- | --- | --- | --- |
| `ALIVE` | `"alive"` | 0 | the role is in force | no consumer blocks it |
| `DEPRECATED` | `"deprecated"` | 1 | outdated, still works | `@check_roles` warns (`DeprecationWarning`) and accepts |
| `SILENCED` | `"silenced"` | 2 | switched off | the access check drops the role from the active set |
| `UNUSED` | `"unused"` | 3 | kept, not used | `@check_roles` refuses to require it (`RoleSpecTypeError`) |

**Invariants**

1. The set is closed: exactly these four members are accepted by `@role_mode`, and the definition order is the order every refusal prints.
2. The *values* are not arguments: `"alive"` and `RoleMode.ALIVE.value` are refused.
3. Membership is of this enum: a member of another `Enum`/`IntEnum`/`StrEnum` is refused, whatever its value.

## Role mode metadata (the stored attribute)

| Field | Where | Type | Written by | Read by |
| --- | --- | --- | --- | --- |
| `_role_mode_info` | the role class | `dict[str, RoleMode]` | `@role_mode` | `RoleMode.declared_for` |
| `_role_mode_info["mode"]` | inside that mapping | `RoleMode` (a member, by identity) | `@role_mode` | `RoleMode.declared_for` and, through it, `@check_roles`, `_active_user_roles`, `_user_role_grants_requirement` |

**Invariants**

1. The key stays `"mode"` and the mapping stays a plain `dict` of one entry; nothing else is added.
2. The stored object is the member handed in — identity, not a copy and not its value (FR-008).
3. The attribute is written only after both checks pass, so a refused declaration leaves no metadata on any class (FR-005).
4. Inheritance is unchanged: a subclass without its own decorator reads its parent's entry through `getattr`.
5. A hand-written or legacy entry that is not a `RoleMode` is still refused by `declared_for` (FR-010).

## Role (the declaration's subject)

A `RoleModeIntent` subclass with `name` and `description`, optionally decorated with a mode. It is the unit the decorator judges and the unit `declared_for` looks up. The feature does not change its shape, its suffix rule, or the requirement that `@check_roles` names it.

## Refusal (the only user-visible output)

| Field | Content | Source of truth |
| --- | --- | --- |
| Error type | `RoleModeDeclarationError` (a `TypeError`) | FR-002 |
| Decorator name | `@role_mode` | FR-004 |
| Role | the class's `__qualname__`; for the bare form, the class that arrived as the argument | FR-004, FR-019 |
| Received value | `repr` of what arrived: `'alive'`, `42`, `None`, `<Other.ALIVE: 'alive'>`, `<class 'Bare'>` | FR-003 |
| Allowed set | `ALIVE, DEPRECATED, SILENCED, UNUSED`, in that order, from the enum | FR-003, FR-020 |
| Correction | for the bare form, the missing parentheses and one example of a correct call | FR-019 |

## Validation rules — where each requirement lands

| Rule | Checked at | Enforced by | Requirement |
| --- | --- | --- | --- |
| the argument is a `RoleMode` member | decorator application to the class | the decorator | FR-001, FR-007 |
| the argument is not a class (missing parentheses) | the decorator's own call | the decorator | FR-019 |
| the accepted member is stored unchanged | decorator application | the decorator | FR-008 |
| the target is a class | decorator application | the decorator (unchanged) | FR-013 |
| a role without metadata is refused | first read | `declared_for` (unchanged) | FR-010 |
| a role with corrupted metadata is refused | first read | `declared_for` (unchanged) | FR-010 |
| `UNUSED` cannot be required | `@check_roles` | `_validate_required_role_modes` (unchanged) | FR-011 |
| `DEPRECATED` warns, requirement accepted | `@check_roles` | `_validate_required_role_modes` (unchanged) | FR-011 |
| `SILENCED` grants nothing | access check | `_active_user_roles`, `_user_role_grants_requirement` (unchanged) | FR-011 |

## The invalid-input space

| Input | Class | Refusal |
| --- | --- | --- |
| `"alive"`, `"deprecated"`, `"silenced"`, `"unused"` | string | set check |
| `RoleMode.ALIVE.value` | string via `.value` | set check |
| `42`, `0`, `None`, `object()` | any non-member | set check |
| another `Enum`'s member with a matching value | foreign member | set check |
| the role class itself (no parentheses) | class | missing-parentheses check |
| `mode="alive"` (keyword) | string, same path | set check |

There is no state transition in this feature: a mode is decided once, at the declaration, and is never updated at run time.
