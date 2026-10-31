# Requirements Quality Checklist: Comparison on the Full Graph

**Purpose**: Test whether spec 039's requirements on the union, marks, counts, filters and the acceptance stand are complete, clear and consistent
**Created**: 2026-10-31
**Feature**: [spec.md](../spec.md)

**Ownership**: `[x]` means a reviewer judged the requirement's quality sufficient. It does not mean the work is done. `/speckit-implement` reads these markers and does not change them.

## Requirement Completeness

- [ ] CHK001 - Is the set of edges in the union defined, including which edges are left out? [Completeness, Spec §FR-001, §FR-006]
- [ ] CHK002 - Is the edges' order defined exactly enough to give one layout input? [Completeness, Spec §FR-002]
- [ ] CHK003 - Are the visual values of each mark (ring width, colours, fading) stated in the spec or only in the mockup? [Gap, Spec §FR-007]
- [ ] CHK004 - Is what the Changes section lists when a status is absent from the picture specified? [Gap, Spec §FR-016]
- [ ] CHK005 - Are requirements stated for the waiting state while a union is laid out? [Completeness, Spec §Edge Cases]
- [ ] CHK006 - Does the spec say what a filter does to a domain's hull? [Gap, Spec §FR-016a]

## Requirement Clarity

- [ ] CHK007 - Is "fades" quantified, or tied to a named reference? [Clarity, Spec §FR-007]
- [ ] CHK008 - Is "changed" for a node defined against the comparison's own status, not a neighbour's? [Clarity, Spec §FR-010]
- [ ] CHK009 - Is "a panel like the ERD's" specific about what is shared and what differs? [Ambiguity, Spec §FR-016]
- [ ] CHK010 - Is "drawn" used in one meaning across counts, fading and "no changes"? [Clarity, Spec §FR-012, §FR-016b]

## Requirement Consistency

- [ ] CHK011 - Do FR-012's node-only counts agree with spec 038's FR-025 definition of the diagram's counts? [Consistency, Spec §FR-012]
- [ ] CHK012 - Is "no changes" in FR-013 consistent with User Story 1's scenario 5 now that an edges-only case exists? [Consistency, Spec §FR-013]
- [ ] CHK013 - Do the Assumptions on domain colours agree with FR-005? [Consistency, Spec §FR-005]
- [ ] CHK014 - Does the panel replacing the legend conflict with anything spec 026 or 028 promises about the full graph? [Conflict, Spec §FR-016]
- [ ] CHK015 - Do the issue's four phases match the plan's? [Consistency]

## Acceptance Criteria Quality

- [ ] CHK016 - Can SC-001 be measured before the merge without gameoffer? [Measurability, Spec §SC-001]
- [ ] CHK017 - Is the stand's content specific enough that "walked on the stand" has one meaning? [Measurability, Spec §The acceptance stand]
- [ ] CHK018 - Is SC-008's "moves 0 nodes" tied to a stated position tolerance? [Measurability, Spec §SC-008]
- [ ] CHK019 - Does each User Story have a criterion in Success Criteria? [Traceability]

## Scenario and Edge Case Coverage

- [ ] CHK020 - Are requirements defined for a filter set that names a type or domain the current pair lacks? [Edge Case, Gap]
- [ ] CHK021 - Is switching between pairs covered for the filter set: does it persist? [Coverage, Gap]
- [ ] CHK022 - Is a filter hiding a node with an open card covered? [Edge Case, Gap]
- [ ] CHK023 - Is a retargeted relation covered when one of its targets is hidden? [Edge Case, Gap]
- [ ] CHK024 - Are removed-node edges covered when a neighbour exists only in B? [Coverage, Spec §Edge Cases]

## Non-Functional Requirements

- [ ] CHK025 - Is the decision to give a union no time bound of its own recorded with a reason? [Assumption]
- [ ] CHK026 - Does the signal beyond colour cover a touch screen, where a hover label does not exist? [Coverage, Spec §FR-007]
- [ ] CHK027 - Are keyboard requirements stated for opening a card on the full graph? [Gap, Spec §FR-015]

## Dependencies and Assumptions

- [ ] CHK028 - Is the dependency on the stand's history being rebuilt, and on its link changing, stated? [Dependency, Spec §The acceptance stand]
- [ ] CHK029 - Is "generalization edges are out" validated against the node counts the release gives? [Assumption, Spec §FR-006]

## Notes

- Items are written for the reviewer; none is pre-checked.
