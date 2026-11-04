# JSON Contract Requirements Checklist: Every entity value has one JSON form

**Purpose**: Check that the requirements of the JSON forms are complete, unambiguous and testable before tasks are written (requirements quality, not implementation)
**Created**: 2026-11-04
**Feature**: [spec.md](../spec.md)

## Completeness

- [x] CHK001 Is the JSON form specified for each container cardinality (One, Many) and each load state (not loaded, loaded, loaded with zero rows)? [Completeness, Spec FR-001, US1/AC1, AC4]
- [x] CHK002 Is the Python-mode dump behaviour specified for every value kind (relation, dictionary reference, lifecycle)? [Completeness, Clarifications, FR-001, FR-007]
- [x] CHK003 Are all accepted input shapes listed for every value kind and every mode (container/lifecycle instance, dict, JSON)? [Completeness, FR-002, FR-005, FR-007]
- [x] CHK004 Is the id type rule specified both for a target with `id` and without? [Completeness, FR-003]
- [x] CHK005 Is the JSON Schema requirement stated for validation and for serialization mode where they differ (dictionary references, lifecycle)? [Completeness, FR-005, FR-008, data-model]
- [x] CHK006 Are nullable fields (`… | None`) covered? [Edge Cases]

## Clarity

- [x] CHK007 Is "loaded" defined by an observable marker in JSON (`"entity"` / `"entities"` present) rather than by a flag? [Clarity, FR-001]
- [x] CHK008 Is the meaning of a missing field inside a target defined (not loaded)? [Clarity, Clarifications, FR-002]
- [x] CHK009 Is it stated which input keys are ignored rather than refused (reference `display_name`/`properties`; lifecycle keys beside `code`)? [Clarity, FR-005, FR-007]
- [x] CHK010 Is "the same message" for bare codes left open deliberately — refused, wording may change? [Clarity, contracts]

## Consistency

- [x] CHK011 Do the dictionary reference's input rules agree with those of a field typed by the dictionary (reference read by `code`, label from the catalogue)? [Consistency, US2/AC4]
- [x] CHK012 Does the lifecycle's output shape match the dictionary reference shape? [Consistency, FR-007]
- [x] CHK013 Do the requirements keep #405's Python-mode behaviour (containers kept) and #406's schema behaviour untouched? [Consistency, Clarifications]

## Acceptance criteria & coverage

- [x] CHK014 Does every case of #407 map to an acceptance scenario or edge case? [Coverage, SC-001]
- [x] CHK015 Is the round trip stated as observable state (ids with types, loaded state, selected declared values), not as `==` alone? [Measurability, SC-002]
- [x] CHK016 Is the performance criterion relative and marked as measured, not asserted? [Measurability, SC-004]

## Dependencies & scope

- [x] CHK017 Is the boundary with #408 (projections), #409 (round-trip over every Result), #414 (private attributes) explicit? [Scope, Out of Scope]
- [x] CHK018 Is the partial target's schema gap (required fields a partial may omit) recorded as a known limit rather than left implicit? [Gap, Clarifications]

## Notes

- Checked against spec.md on creation; every item passes. CHK018 is a recorded limit, not an open question.
