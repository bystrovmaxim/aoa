# Naming Contract Checklist: Every base class names its descendants

**Purpose**: Review declaration rules, wrapper contracts, migration coverage and delivery requirements before implementation.
**Created**: 2026-11-07
**Feature**: [spec.md](../spec.md)
**Depth / audience**: Standard; maintainer review before implementation.

**Review Ownership**: This custom checklist is reviewer-owned. `[x]` means the requirements-quality criterion has been reviewed and satisfied, not that implementation is complete. Items were generated unchecked and evaluated on 2026-11-07 under the maintainer’s instruction to correct the findings.

## Contract completeness and clarity

- [x] CHK001 Are the permitted resource kind bases identified unambiguously, including whether declaring a kind attribute may grant an exception? [Completeness, Spec FR-001]
- [x] CHK002 Are mixed-kind inheritance and descendant overrides of the kind defined? [Coverage, Gap, Spec FR-001]
- [x] CHK003 Is the wrapper declaration contract sufficient to check every target at model build without constructing a resource? [Clarity, Spec FR-001, Plan Design: Resource kinds]
- [x] CHK004 Are no-wrapper results, inherited wrapper declarations and wrappers of wrappers covered explicitly? [Coverage, Gap, Spec FR-001]
- [x] CHK005 Are errors and their timing defined separately for invalid resource names, direct inheritance, invalid wrapper targets, with handler validation explicitly excluded? [Clarity, Spec US1, US2]
- [x] CHK006 Is the complete list of governed bases and the BaseIntent exception consistent across the specification, plan and tasks? [Consistency, Spec FR-002, T003–T005]

## Migration and consistency

- [x] CHK007 Does the module-renaming plan follow the specification's rule for modules named after one class? [Consistency, Spec Clarifications, Plan Design: Renames]
- [x] CHK008 Is the scope of old-name removal compatible with documenting migration from old names? [Consistency, Spec SC-002, FR-004, FR-006]
- [x] CHK009 Are public exports, tests, demo, scripts, notebooks and documentation all included in migration requirements, with gnomon explicitly excluded? [Completeness, Spec FR-004, Clarifications]

## Acceptance and delivery

- [x] CHK010 Does every naming rule have measurable acceptance criteria and a task for adversarial verification? [Measurability, Spec SC-001, T001–T005]
- [x] CHK011 Do tasks explicitly cover a script and notebook for each new case, including refusals, rather than only renaming existing examples? [Completeness, Constitution VI.4–6, T009]
- [x] CHK012 Is the local check run before documentation distinguished from the later PR CI run, preserving the three-step tail and a complete PR? [Consistency, Constitution VI, T008–T010]

## Notes

Review completed on 2026-11-07 under the maintainer's instruction to correct the findings. These marks concern requirements quality only; implementation tasks remain open.

| Items | Evidence after correction |
|---|---|
| CHK001–CHK002 | Spec: Session 2026-11-07, Resource identity; US1/AC4; plan: Resource kinds |
| CHK003–CHK005 | Spec: Wrapper declaration/results; US1/AC5–6; plan: Wrapper contract; T001 |
| CHK006 | Spec: base list and BaseIntent exception; T003–T005 |
| CHK007 | Plan: Renames; T001, T003, T004 explicitly migrate modules and imports |
| CHK008–CHK009 | Spec: Migration evidence, FR-004, SC-002 and gnomon exclusion; plan: migration scope |
| CHK010 | Spec: US1–US3 and SC-001; plan: Verification and documentation; task traceability table |
| CHK011 | Spec FR-006; plan's case inventory; T009 script/notebook pairs and exact outputs |
| CHK012 | Spec: Delivery; plan: Constitution Check; T008–T010 ordering and later CI |
 `/speckit-implement` reads this state and does not change markers. The built-in `requirements.md` has its own lifecycle.

Scope correction: the maintainer excluded handler changes; T006 is withdrawn. CHK005 and CHK010 were re-evaluated against this narrower scope. No handler implementation or handler-naming tests are changed.
