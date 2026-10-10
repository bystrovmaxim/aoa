# Implementation Plan: The access cascade demonstrator

**Branch**: `feature/issue-201-access-cascade-demonstrator` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-access-cascade-demonstrator/spec.md`

## Summary

The demo package gains a dedicated access-shapes domain — roles at all three levels with a multi-level hierarchy, and operations each producing exactly one access-cascade shape: role check alone, a `when=` refusal on a matched role, a shared `guard=` refusal, a declared object rule, two roles matching one operation, a cascade that stops early, a refusal that is an answer (question path), and a `NoInverse` boundary extreme. Every element's description names the shape it produces. The drawn use-case diagram is recorded as a DOT file and a rendered picture, committed under the feature's `contracts/` directory. No framework or Maxitor code changes are expected: the interchange graph already emits the edges Maxitor draws.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `aoa-action-machine` (BaseAction, BaseRole, SystemRole/ApplicationRole roots, `@check_roles`, `grant(..., when=, reason=)`, `guard=`, `@access_decide`, `NoInverse()` relation markers), `aoa-demo` (model registration: `model/build.py` + its mirror in `interchange_demo_coordinator.py`), `aoa-maxitor` (use-case diagram from DuckDB; read-only for this feature)

**Storage**: DuckDB interchange graph populated by Maxitor's load step; no schema changes

**Testing**: `uv run --extra dev pytest packages/aoa-demo/tests/ -q` (the acceptance gate), plus the repository-wide check run at the tail of the change

**Target Platform**: local development; Maxitor web UI renders the recorded picture

**Project Type**: library demonstrator (fixtures for a drawing)

**Performance Goals**: N/A — fixtures, no runtime load

**Constraints**: existing demo content untouched (FR-014); every added element's description names its shape (FR-011); English only in code and tests; framework naming suffixes (`Action`, `Role`, `Domain`, `Entity`) enforced

**Scale/Scope**: one new domain module group, ~8 role classes, ~8 demonstration operations, one entity fixture, ~6–8 new test cases, two contract artifacts (DOT + PNG)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. The maintainer decides | No commit, push or PR without an explicit instruction in the current conversation | PASS — nothing is committed by planning |
| II. English in code and history | All new fixtures, descriptions, docstrings and tests in English | PASS — planned so; names like `*ShapeAction` are English |
| III. Module headers | Every new module opens with the standard header (`# path`, title, `PURPOSE`, `ARCHITECTURE / DATA FLOW`) | PASS — one task per new module reserves the header |
| IV. AI-CORE blocks | Public classes carry ROLE/CONTRACT (INVARIANTS where they exist) | PASS — planned for domain, roles, actions |
| V. Short docstrings | One-line docstring on every class, function and method | PASS — planned |
| VI. The last three steps | Planning reserves exactly three tail tasks, in order: check run to zero → documentation → one changelog article | PASS — reserved for `/speckit-tasks`; no other task may absorb them |

Re-check after Phase 1: no new violations introduced — the design adds fixtures only; it does not touch the constitution, the graph model, or the check-run machinery.

## Project Structure

### Documentation (this feature)

```text
specs/003-access-cascade-demonstrator/
├── plan.md              # This file
├── spec.md              # Feature specification (+ Clarifications session)
├── checklists/
│   └── requirements.md  # Spec quality checklist (16/16 passing)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── access-shapes.md # The drawing contract: shape → visual element + carrying edge
│   ├── access-shapes.dot    # Recorded DOT (implementation output, lands here)
│   └── access-shapes.png    # Recorded rendered picture (implementation output, lands here)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/aoa-demo/src/aoa/demo/model/
├── build.py                                  # EDIT: register the new domain modules
├── interchange_demo_coordinator.py           # EDIT: mirror the registration list
└── access_cascade/                           # NEW: dedicated access-shapes domain
    ├── __init__.py
    ├── access_cascade_domain.py              # AccessCascadeDomain (name, description)
    ├── roles/
    │   ├── __init__.py
    │   ├── cascade_system_role.py            # SystemRole branch (system level)
    │   ├── cascade_application_roles.py      # ApplicationRole chain, 4 levels deep
    │   └── cascade_domain_roles.py           # BaseRole branch (domain level)
    ├── actions/
    │   ├── __init__.py
    │   ├── role_check_alone_shape_action.py
    │   ├── when_refusal_shape_action.py
    │   ├── guard_refusal_shape_action.py
    │   ├── access_decide_shape_action.py
    │   ├── two_path_match_shape_action.py
    │   ├── early_stop_shape_action.py
    │   └── question_path_shape_action.py
    └── entities/
        ├── __init__.py
        └── cascade_boundary_entity.py        # NoInverse boundary extreme

packages/aoa-demo/tests/model/
└── test_access_cascade_shapes.py             # NEW: runnable proofs (early stop, question path)
```

**Structure Decision**: a dedicated `access_cascade` domain group under the existing demo model, mirroring the layout of sibling domains (one domain module, roles and actions in submodules, an entities package). Registration goes through the single module list — `_MODULES` in `model/build.py`, which the demo coordinator imports — nothing else in the demo package is touched.

## Complexity Tracking

No constitution violations — table intentionally empty.
