# Implementation Plan: Every entity value has one JSON form

**Branch**: `feature/issue-407-entity-json-forms` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/062-entity-json-forms/spec.md`; issue #407, step 3 of 8 of #399.

## Summary

Three Pydantic schema hooks in `aoa-action-machine`'s domain layer. Relation containers to ordinary entities get a JSON form, a closed JSON Schema naming the target by reference, and one validator for JSON, dicts and containers, with ids validated by the target's `id` type (R1). Dictionary references get one validator for every mode that takes the container, the id object and the reference object, and a reference computed once per declared value (R2). `Lifecycle` gets a JSON form (its status's reference), a JSON Schema with the template's codes, and a validator choosing the declared status (R3). The adapters' code does not change; end-to-end tests prove it.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14)

**Primary Dependencies**: Pydantic 2.14, pydantic-core 2.50

**Storage**: N/A

**Testing**: pytest per package; FastAPI `TestClient`, the MCP adapter's validation and serialization helpers, the LangGraph node binding

**Target Platform**: library

**Project Type**: library (monorepo of packages)

**Performance Goals**: ten dictionary references dumped at least 4 times faster (SC-004)

**Constraints**: Python-mode dumps keep containers and lifecycles; adapter code unchanged; JSON of dictionary references byte-identical

**Scale/Scope**: `domain/relation_containers.py`, `domain/enum_entity.py`, `domain/lifecycle.py`; tests in three packages; step 23 examples with old messages; tutorial steps 22–25 and two how-to pages

## Constitution Check

| Principle | How this plan meets it |
| --- | --- |
| I. The maintainer decides | The maintainer instructed the whole task, commits, PR and merge in this conversation; each phase is still its own commit |
| II. English in code and history | Code, docstrings, commits, spec in English; `tasks.ru_draft.md` and `*.ru_draft.md` pages are Russian and not committed |
| III–V. Headers, AI-CORE blocks, docstrings | The three touched modules update their data-flow notes and AI-CORE blocks to the JSON forms |
| VI. Check run, documentation, changelog last | Phases 6–8 are exactly these three, in this order; each documented case has a script and a notebook |
| Check run | Phase tests after each phase; the closing run before the PR; CI on it; `check_before_pr.sh` for the browsers |

No violation; nothing in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/062-entity-json-forms/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/json-forms.md
├── checklists/requirements.md, checklists/json-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/domain/relation_containers.py   # phases 1, 2
packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py           # phase 2
packages/aoa-action-machine/src/aoa/action_machine/domain/lifecycle.py             # phase 3
packages/aoa-action-machine/tests/action_machine/domain/                          # phases 1–3
packages/aoa-fastapi-adapter/tests/, packages/aoa-mcp-adapter/tests/, packages/aoa-langgraph/tests/   # phase 4
examples/step_22_entity/ … step_25_lifecycle/, examples/how_to/                   # phase 7
docs/tutorials/step-22…25, docs/how-to/dictionary-references.md, explicit-entity-fields.md
```

**Structure Decision**: all behaviour stays in the domain layer of `aoa-action-machine`; the adapter packages get tests only.

## Phases

One phase = one commit.

1. **Relations to ordinary entities** (1.1, 3.1–3.5) — R1. Tests: each case; the recursive pair; UUID ids for One and Many; a target without `id`; a container of another class; an unknown key; error location `customer.id`. Adversarial: the typed dict made open (`extra` allowed) → the unknown-key test fails; ids validated as `Any` → the UUID test fails; `entities` ignored on read → the loaded-zero test fails.
2. **Dictionary references** (4.1–4.5) — R2. Tests: id object and reference object from a dict, One and Many, `[]`; label from the catalogue; schema `anyOf`; byte-identical JSON; a reference computed once; a returned reference cannot change the catalogue. The step-23 examples and the old-message test follow. Adversarial: the JSON-only branch back → the dict tests fail; the stored dict returned as is → the mutation test fails.
3. **Lifecycle** (5.1–5.4) — R3. Tests: JSON form with `properties`; schema enum; read back by code; unknown code and bare string refused; 5.4 identity and changed list; a status's own dump unchanged. Adversarial: build a status from the stored properties → 5.4 fails.
4. **Adapters end to end** (1.3, 4.1, 4.2, 5.1, 10.1) — FastAPI `TestClient` with OpenAPI, MCP validation and result serialization, LangGraph node; the alias field's names pinned per adapter.
5. **Versions** — `aoa-action-machine` raised; adapter packages only if their code changed (tests do not count); graph files checked.
6. **The closing check run**, taken to zero, the example checks included; every test or example with ids of the wrong type is corrected.
7. **Documentation** — tutorial steps 22–25, how-to pages on dictionary references and explicit entity fields; #401 sections 4.3, 4.4, 4.5, 4.10; scripts and notebooks from runs.
8. **Changelog** — one article.

## Complexity Tracking

None.
