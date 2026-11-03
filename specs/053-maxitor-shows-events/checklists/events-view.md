# Events View Checklist: Maxitor shows events

**Purpose**: Test the quality of the requirements for the Events diagram, its card, comparison and old documents
**Created**: 2026-11-02
**Feature**: [spec.md](../spec.md)

`[x]` means a reviewer found the requirement well written, not that it is built.

## Requirement Completeness

- [ ] CHK001 - Is the place of the Events row among a domain's diagrams specified? [Gap, Spec §FR-002]
- [ ] CHK002 - Is an Events diagram for all domains together either required or excluded? [Gap]
- [ ] CHK003 - Are the filters and the layout controls of the diagram specified? [Gap, Spec §FR-009]
- [ ] CHK004 - Is what a method's card and a domain's card add about events specified? [Completeness, Spec §FR-002]

## Requirement Clarity

- [ ] CHK005 - Is "leads on" defined: which page opens for a method and for a domain? [Clarity, Spec §FR-005]
- [ ] CHK006 - Is "belongs to" defined for an event outside any vocabulary? [Clarity, Spec §US-3]
- [ ] CHK007 - Is "Not emitted" defined for an event emitted only in another domain? [Clarity, Clarifications]

## Requirement Consistency

- [ ] CHK008 - Does Scenario 3 of Story 1 agree with the rule that methods with no event are not drawn? [Consistency, Spec §US-1]
- [ ] CHK009 - Does Story 2 "for each method" agree with the diagram leaving such methods out? [Conflict, Spec §US-2]

## Acceptance Criteria Quality

- [ ] CHK010 - Can "at most two steps" in SC-003 be counted objectively? [Measurability, Spec §SC-003]
- [ ] CHK011 - Can SC-001 be checked without a reader's judgement? [Measurability, Spec §SC-001]

## Scenario and Edge Case Coverage

- [ ] CHK012 - Is an event emitted by a method of another domain than the event's vocabulary covered? [Coverage, Gap]
- [ ] CHK013 - Is a comparison where a domain gains or loses its vocabulary covered? [Coverage, Gap]
- [ ] CHK014 - Is a comparison where an event's field changes covered? [Coverage, Gap]
- [ ] CHK015 - Is an event in a domain present on one side only covered in Side by side? [Coverage, Spec §FR-009]
- [ ] CHK016 - Is the diagram of a domain in a document older than 1.3 defined: row hidden, or an empty page? [Edge Case, Spec §FR-008]

## Dependencies & Assumptions

- [ ] CHK017 - Is the assumption that the demo graph holds all modes and all five kinds validated? [Assumption]
- [ ] CHK018 - Is the set of five kinds of method named once and consistently with the document's node types? [Assumption, Spec §FR-003]

## Notes

- `/speckit-implement` reads this checklist and does not change its marks.
