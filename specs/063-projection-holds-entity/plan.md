# Implementation Plan: A projection holds the entity

**Branch**: `feature/issue-408-projection-holds-entity` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: issue #408, step 4 of 8 of #399.

## Summary

A projection's value becomes a partial entity with exactly the projection's fields, read from an entity or a dict and checked by the projection's schema and by the entity's field types (R1, R2); a projection names only fields of its entity (R3); a field typed by the bare entity refuses a partial one (R4); every field typed by an entity gets an `entity_schema` edge (R5).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14) · **Primary Dependencies**: Pydantic 2.14 · **Testing**: pytest per package · **Project Type**: library monorepo

**Constraints**: adapters unchanged; the published projection schema unchanged; error wording `<Entity> wire projection: …` kept

**Scale/Scope**: `domain/partial_fields.py` (new), `domain/relation_containers.py`, `domain/entity_schema_marker.py`, `domain/entity.py`, `graph/nodes/field_graph_node.py`, `graph/nodes/property_field_graph_node.py`, `graph/edges/entity_schema_graph_edge.py`; tests; the demo's projection test; tutorial steps 17, 18, 22

## Constitution Check

| Principle | How |
| --- | --- |
| I | The maintainer instructed the whole task, PR and merge; one phase = one commit |
| II | English in code and history; Russian only in `*_draft.md` |
| III–V | Touched modules update notes and AI-CORE blocks; the new module gets its header |
| VI | Phases 5–7: check run, documentation, changelog |

No violation.

## Phases

One phase = one commit.

1. **Projections** (6.1–6.3) — R1–R3. Tests: entity/partial/dict in, JSON out, outside field unreadable, missing required field named, Params give an entity with attribute and dict-style reads, a value the schema takes but the field type refuses, an entity of another class, a schema naming a non-field. Adversarial: the dict kept as the value; the field-type check skipped; the property check removed.
2. **Bare entity refuses a partial** (6.4) — R4. Tests: bare, `| None`, `list[...]`; full accepted; message names what is loaded and points to `.schema(...)`. Adversarial: the after step removed.
3. **Graph edge** (7.1) — R5. Tests: bare, `| None`, `list[...]`, a dictionary type, a projection unchanged. Adversarial: the annotation branch removed.
4. **Graph files and versions**.
5. **Closing check run**.
6. **Documentation** — steps 17, 18, 22; #401 sections 4.6, 4.7.
7. **Changelog**.
