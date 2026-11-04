# Implementation Plan: An entity tells the truth in Python

**Branch**: `feature/issue-405-entity-truth-in-python` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/060-entity-truth-in-python/spec.md`; issue #405, step 1 of 8 of #399.

## Summary

Two fixes in `aoa-action-machine`'s domain layer. Relation containers stop forwarding names that start and end with `__` to their entity and get explicit copy, deep-copy and pickle support (cases 1.1–1.5). `BaseEntity.partial()` sets only the given fields, without `model_construct`, so no default or default factory of an unloaded field runs; a field is loaded when the instance holds it, with no flag (cases 2.1–2.3). Equality stays as it is (research R1).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14)

**Primary Dependencies**: Pydantic 2.14

**Storage**: N/A

**Testing**: pytest, per package

**Target Platform**: library

**Project Type**: library (monorepo of packages)

**Performance Goals**: no measurable change; `partial()` does less work than today

**Constraints**: public signatures unchanged; equality unchanged (FR-009)

**Scale/Scope**: two modules — `domain/relation_containers.py`, `domain/entity.py` — their tests, one example, two tutorial pages, one how-to page

## Constitution Check

| Principle | How this plan meets it |
| --- | --- |
| I. The maintainer decides | No commit, push or pull request without an instruction; every phase ends with a diff to show |
| II. English in code and history | All code, docstrings, commits and the spec in English; only `tasks.ru_draft.md` is Russian, and it is not committed |
| III–V. Headers, AI-CORE blocks, docstrings | The two touched modules keep their headers; new methods get one-line docstrings; the AI-CORE blocks of `BaseEntity` and the containers are updated to the new contract |
| VI. Check run, documentation, changelog last | Phases 3–5 are exactly these three, in this order; examples run (the example checks) |
| Check run | After each phase only that phase's tests run; the closing run is CI's, plus `scripts/check_before_pr.sh` for the browsers |

No violation; nothing in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/060-entity-truth-in-python/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/entity-api.md
├── checklists/requirements.md
└── tasks.md            (/speckit-tasks)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/domain/relation_containers.py   # phase 1
├── src/aoa/action_machine/domain/entity.py                # phase 2
└── tests/action_machine/domain/                           # tests of both phases
packages/aoa-langgraph/tests/                              # case 1.3
examples/step_22_entity/, examples/step_24_relations/      # phase 4, as needed
docs/tutorials/step-22-entity.md, step-24-relations.md, docs/how-to/dictionary-references.md
```

**Structure Decision**: the change stays inside the domain layer of `aoa-action-machine`; the LangGraph package gets a test only.

## Phases

One phase = one commit.

1. **Relation containers** (cases 1.1–1.5). `__getattr__` refuses dunder names; `__reduce__` on both bases, which `copy`, `deepcopy` and `pickle` all use. Tests: each case, plus forwarding of an ordinary name and `RelationNotLoadedError` for an unloaded one; the LangGraph node test of 1.3. Adversarial: dunder forwarding back → 1.1–1.4 fail; `__reduce__` removed → the deep copies of 1.4 and the copies, deep copies and pickles of 1.5 fail.
2. **Partial entities** (cases 2.1–2.3). `partial()` builds the instance itself (R1); `__getattr__`, `is_field_loaded`, `get_field_value` read presence in `__dict__`; `_partial_instance` and `_loaded_fields` go away. Tests: each case, equality of a partial with every field, `model_copy(update=...)`, the revisited assertion of `test_entity_partial_getattr.py`, and a test pinning the four slots against Pydantic. Adversarial: `model_construct` back.
3. **Versions** — raise the version of each level that changed (`aoa-action-machine`; `aoa-langgraph` only if it changed beyond tests) and rebuild the graph files if they change.
4. **The closing check run**, taken to zero, the example checks included.
5. **Documentation** — tutorial steps 22 and 24 and the how-to page on dictionary references, explanations from #401 sections 4.1 and 4.2, examples from runs.
6. **Changelog** — one article.

## Complexity Tracking

None.
