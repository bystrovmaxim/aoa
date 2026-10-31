# Requirements Quality Checklist: The Full Graph as a Map

**Purpose**: Test whether spec 040's requirements on levels, reading in parts, the layout, the comparison, filters and the look are complete, clear and consistent
**Created**: 2026-10-31
**Feature**: [spec.md](../spec.md)

**Ownership**: `[x]` means a reviewer judged the requirement's quality sufficient. It does not mean the work is done. `/speckit-implement` reads these markers and does not change them.

## Requirement Completeness

- [ ] CHK001 - Are the zoom thresholds between levels stated, or tied to a rule that fixes them? [Gap, Spec §FR-002]
- [ ] CHK002 - Is the amount of detail kept in the browser stated? [Completeness, Spec §FR-012]
- [ ] CHK003 - Are requirements stated for how long stored layouts and places are kept? [Gap, Spec §FR-015]
- [ ] CHK004 - Does the spec say which history owns the places for a graph with no history? [Gap, Spec §FR-016]
- [ ] CHK005 - Is the look stated specifically enough to approve or refuse? [Clarity, Spec §FR-009a]
- [ ] CHK006 - Does the spec define what the card shows for a marked link? [Gap, Spec §FR-026]

## Requirement Clarity

- [ ] CHK007 - Is "beside its neighbours" for a node only in A precise enough to test? [Clarity, Spec §FR-021]
- [ ] CHK008 - Is "fades rather than pops" quantified? [Clarity, Spec §FR-009a]
- [ ] CHK009 - Is "as far as their sizes require" testable for an area that grew? [Measurability, Spec §FR-016]
- [ ] CHK010 - Is the stepping order defined for an area that is added or removed as a whole? [Clarity, Spec §FR-025b]

## Requirement Consistency

- [ ] CHK011 - Do FR-003 "no element moves" and FR-029a "the name stands with what is left" agree on what may move? [Consistency, Spec §FR-003, §FR-029a]
- [ ] CHK012 - Do the 50 ms of SC-003 and the outlines of FR-029a fit together? [Conflict, Spec §SC-003, §FR-029a]
- [ ] CHK013 - Does FR-032's change to the ERD agree with what spec 038 promises about the panel? [Consistency, Spec §FR-032]
- [ ] CHK014 - Are the clarification on rearranging domains and SC-008 consistent? [Consistency, Spec §SC-008]

## Acceptance Criteria Quality

- [ ] CHK015 - Is the generated graph defined closely enough for two runs to compare? [Measurability, Spec §The acceptance stand]
- [ ] CHK016 - Is SC-015's approval tied to a named set of screens? [Measurability, Spec §SC-015]
- [ ] CHK017 - Can SC-002 be measured the same way on a machine with no discrete GPU? [Measurability, Spec §SC-002]

## Scenario and Edge Case Coverage

- [ ] CHK018 - Is a filter switched on while the map is flying to a change covered? [Edge Case, Gap]
- [ ] CHK019 - Is stepping covered when the next change's domain cannot be read? [Exception Flow, Gap]
- [ ] CHK020 - Is a version whose layout failed for every area covered? [Exception Flow, Spec §Edge Cases]
- [ ] CHK021 - Are two rooms of different filters on one version covered? [Coverage, Gap]

## Non-Functional Requirements

- [ ] CHK022 - Is memory in the browser bounded in the requirements? [Gap, Spec §FR-012]
- [ ] CHK023 - Are server memory and storage bounded for catalog size? [Gap, Spec §FR-015]
- [ ] CHK024 - Are keyboard requirements stated for stepping and for opening a card? [Gap, Spec §FR-025b]

## Dependencies and Assumptions

- [ ] CHK025 - Is the dependency on native Graphviz in every environment stated? [Dependency, Spec §Assumptions]
- [ ] CHK026 - Is the assumption that the stepping list stays small for one release validated? [Assumption, Spec §FR-025c]

## Notes

- Items are written for the reviewer; none is pre-checked.
