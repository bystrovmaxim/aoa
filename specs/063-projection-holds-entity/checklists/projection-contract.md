# Projection Contract Requirements Checklist

**Purpose**: Requirements quality for projections and entity-typed fields, before tasks
**Created**: 2026-11-04
**Feature**: [spec.md](../spec.md)

- [x] CHK001 Are all input kinds of a projection named (full entity, partial entity, dict) for every mode? [Completeness, FR-001]
- [x] CHK002 Is it stated which checks a projected value passes (schema and field type) and in which order they report? [Clarity, FR-002, research R2]
- [x] CHK003 Is the refusal for a missing required projection field specified with what the message names? [Measurability, FR-003]
- [x] CHK004 Are both dump modes specified for a projection? [Completeness, FR-004, Clarifications]
- [x] CHK005 Is the declaration-time refusal of a schema naming a non-field specified, including a schema without `properties`? [Edge case, FR-006, R3]
- [x] CHK006 Are `| None` and `list[...]` covered for both the refusal of partials and the graph edge? [Coverage, FR-007, FR-008]
- [x] CHK007 Is the dictionary kind's place stated for the refusal (never partial) and for the edge (included)? [Consistency, Clarifications, Edge Cases]
- [x] CHK008 Is the boundary with #407's relation forms stated for a projection listing a relation field? [Dependency, Edge Cases]
- [x] CHK009 Is performance stated as measured and reported, not asserted? [Measurability, SC-004]
- [x] CHK010 Is the impact on code that treats a projection value as a `dict` named? [Assumption, Assumptions, R6]
