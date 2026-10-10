# Contract: the "all shapes" enumeration

"All shapes is true rather than intended" is only checkable against an enumeration. This file is that enumeration.

## Procedure

1. Enumerate the interchange graph's published node kinds and edge kinds — from `NodeGraphCoordinator.get_available_types()`.
2. For each kind, answer two questions independently:
   - **Carried** — does the demo model contain at least one element of this kind?
   - **Drawn** — does a Maxitor diagram render this kind?
3. Record every kind in the table below as one of:
   - `carried & drawn` — both yes;
   - `named gap` — either no, with one line saying what is missing and where.

The table is regenerated whenever the graph model or the demo model changes; the recorded picture is judged against the `carried & drawn` rows.

## Current status

Known at plan time (to be filled in full during implementation, from `get_available_types()`):

| Kind | Type | Carried | Drawn | Status |
|------|------|---------|-------|--------|
| `parent_action` | edge | planned (generalization fixtures) | yes (use-case diagram) | to verify |
| `parent_entity` | edge | planned (generalization fixtures) | yes (ERD) | to verify |
| `parent_role` | edge | yes (role chains from #201) | yes (use-case diagram) | carried & drawn |
| `@check_roles` / `@access_decide` / others | edge | yes (#201 fixtures) | yes | carried & drawn |
| entity specialization axis | ERD group | pending #199 | yes after #199 | named gap until #199 lands |
| … every remaining kind | | | | filled during implementation |

Rows left empty above are a gap of this contract, not a pass — the implementation fills them or names the missing piece.
