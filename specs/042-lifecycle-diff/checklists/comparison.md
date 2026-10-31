# Comparison Requirements Checklist: Lifecycle Diagrams

**Purpose**: Unit tests for the requirements of spec 042: their completeness, and their agreement with specs 038, 040 and 041
**Created**: 2026-11-01
**Feature**: [spec.md](../spec.md)

**Note**: `[x]` means the reviewer judged the requirement's quality sufficient, not that the work is done. `/speckit-implement` reads these marks and does not change them.

## Requirement Completeness

- [ ] CHK001 - Is every status's look specified for states and for transitions alike? [Completeness, Spec §FR-005]
- [ ] CHK002 - Is the content of the card specified for each of: changed state, added or removed state, added or removed transition? [Completeness, Spec §FR-013]
- [ ] CHK003 - Is the order of the change list specified, states and transitions both? [Completeness, Spec §FR-017]
- [ ] CHK004 - Are the sections of the filter panel specified for One and for Diff separately? [Completeness, Spec §FR-020]
- [ ] CHK005 - Does the carried-over table name every behaviour that specs 038, 040 and 041 give the other diagrams, or state why one is left out? [Completeness]
- [ ] CHK006 - Are requirements defined for a phone, or is the phone's behaviour fixed by reference? [Gap, Spec §Edge Cases]

## Requirement Clarity

- [ ] CHK007 - Is "grey and dim" defined the same wherever an unchanged element is described? [Clarity, Spec §FR-005]
- [ ] CHK008 - Is "changed" for a state defined so that a change the drawing does not show is plainly included? [Clarity, Spec §FR-005a]
- [ ] CHK009 - Is what the sign `+ − ~` stands on, and where, stated for both a state and a transition? [Ambiguity, Spec §FR-006]
- [ ] CHK010 - Is the rule for colouring an entry or exit dot exact when its arrows have different statuses? [Clarity, Spec §Edge Cases]

## Requirement Consistency

- [ ] CHK011 - Does FR-010's count agree with spec 040 FR-024 and spec 041 FR-010? [Consistency, Spec §FR-010]
- [ ] CHK012 - Is the gear shift's fixed position in Diff reconciled with spec 040 FR-030 – FR-032, and is the difference stated? [Conflict, Spec §FR-023]
- [ ] CHK013 - Is the `~` on a lifecycle row reconciled with spec 038 FR-032, where a page's mark means one version only? [Conflict, Spec §FR-026a]
- [ ] CHK014 - Does the identity of a transition in FR-008 agree with the identity in the issue and in #285? [Consistency, Spec §FR-008]
- [ ] CHK015 - Is the corrected +7 used everywhere, with the issue's +4 named as replaced? [Consistency, Spec §SC-002]
- [ ] CHK016 - Do "no changes" and FR-005 agree on how a diagram with no change looks? [Consistency, Spec §FR-012]

## Acceptance Criteria Quality

- [ ] CHK017 - Can "the same picture" of SC-008 be judged objectively? [Measurability, Spec §SC-008]
- [ ] CHK018 - Is every case in the stand's list tied to at least one requirement or scenario? [Traceability, Spec §The acceptance stand]
- [ ] CHK019 - Are the issue's two criteria each traceable to a success criterion? [Traceability, Spec §SC-002, §SC-003]

## Scenario and Edge Case Coverage

- [ ] CHK020 - Are requirements defined for a lifecycle of one version seen by a follower in a room? [Coverage, Gap]
- [ ] CHK021 - Is the case of A and B both lacking the opened lifecycle covered? [Coverage, Spec §FR-028]
- [ ] CHK022 - Is an initial state that became final, changing both dots' arrows, covered? [Edge Case, Spec §Edge Cases]
- [ ] CHK023 - Is a transition from a state to itself covered in cards, steps and hover? [Edge Case, Spec §Edge Cases]
- [ ] CHK024 - Is a lifecycle's disappearance from the live graph while it is open covered? [Exception Flow, Gap]

## One Unchanged

- [ ] CHK025 - Is it stated exactly what in One may change (panel, hover) and what may not (picture, address)? [Clarity, Spec §FR-024, §FR-030]
- [ ] CHK026 - Is the effect of a filter on One's picture separated from the promise that an untouched page stays as it is? [Consistency, Spec §FR-024, §SC-008]

## Dependencies & Assumptions

- [ ] CHK027 - Is the assumption that a state owns no undrawn part backed by what the graph holds? [Assumption]
- [ ] CHK028 - Is the check on gameoffer's three transitions stated as an assumption until the maintainer's check after the merge? [Assumption, Spec §SC-002]
