# Feature Specification: Maxitor: Two Versions Side by Side, and Comparison in Rooms

**Feature Branch**: `feature/issue-294-side-by-side`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Issue #294 (Graph history 9/9): two versions side by side, and comparison in rooms. Source: https://github.com/bystrovmaxim/aoa/issues/294, head issue #273, mockup screen Side by side in specs/030-graph-history/mockup/index.html. All four diagrams in this release; halves carry comparison marks; counts and the change stepper are one for both halves; collapse is shared like filters; Side by side needs two versions."

## Context: what is true today, checked on 2026-11-01

- **The picker has three modes, two working.** One and Diff work on all four diagrams. Side by side stands greyed out, saying "comes later".
- **A page holds one diagram.** The graph being read, the layout mode, the counts, the change stepper and the kept view of the full graph each exist once per tab.
- **A click copies a name** (spec 043). There is no click that selects an element in the sense this work needs.
- **A selection is known only to followers.** What a person selects travels with their hover to the people who follow them; the room as a whole does not hold it.
- **A room already holds A and B.** It keeps its history, its version and, in Diff, the older version. It does not hold whether it is in Diff by a name of its own, and it has no third view.
- **The room's check** compares each person's layout hash and settings digest for a page. Each person has one picture to report.
- **Pointers and screen positions** are relayed to people on the same page, in the coordinates of one picture.

## Clarifications

### Session 2026-11-01

Decisions of the maintainer:

- Q: Which diagrams get Side by side in this release? → A: All four: ERD, full graph, use case, lifecycle.
- Q: Do the halves carry comparison marks? → A: Yes: A shows removed and changed, B added and changed.
- Q: How many counts and steppers does a pair have? → A: One of each; a step acts as a click and selects in both halves.
- Q: How do collapse and the hover card behave across halves? → A: Collapse is shared like filters; a hover card opens in the half under the pointer.
- Q: When is Side by side offered? → A: Like Diff: it needs two versions, and Live can only be B.
- Q: What does a click on a name do in Side by side? → A: It selects the element in both halves, and copies the name as everywhere.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Two versions, each in its own layout (Priority: P1)

A person who has chosen A and B switches to Side by side. A stands on the left, B on the right, each laid out as that version really is, marked with what changed. Each half pans, zooms and changes layout mode on its own; the versions and the filters stay common to both.

**Why this priority**: A serious change can rebuild a picture completely. On one picture such a change is hard to read; this is the view that shows it. Everything else here stands on the two halves.

**Independent Test**: On the stand, open a pair in Side by side on each of the four diagrams, pan and zoom one half, change its layout mode, switch a filter off.

**Acceptance Scenarios**:

1. **Given** two versions chosen, **When** the person picks Side by side, **Then** A is drawn on the left and B on the right, each from its own graph in its own layout.
2. **Given** Side by side, **When** the person looks at A, **Then** it marks removed and changed elements; **When** they look at B, **Then** it marks added and changed elements, each with its colour and its `+`, `−` or `~`.
3. **Given** Side by side, **When** the person pans or zooms one half, **Then** the other half does not move.
4. **Given** Side by side, **When** the person changes one half's layout mode, **Then** only that half is laid out again.
5. **Given** Side by side, **When** a filter or a table's collapse changes, **Then** both halves follow it.
6. **Given** Side by side, **When** the person moves a handle on the track, **Then** the half of that version is redrawn, and roles still follow the position: A is older.
7. **Given** Side by side, **When** the address is reloaded or shared, **Then** the same versions, view and layout modes open.

---

### User Story 2 - One element across both halves (Priority: P1)

The person points at an element in one half and both halves light it, with its links and neighbours, each as that version has them. A click selects it in both, and the other half brings it into view without changing its zoom, or says that it is not in that version.

**Why this priority**: Two pictures laid out differently are of little use until the eye can pass from one to the other. This is what makes the two halves a comparison.

**Independent Test**: On the stand, hover and click an element present in both versions and far from the centre of the other half, then one present in only one version.

**Acceptance Scenarios**:

1. **Given** an element in both versions, **When** the pointer rests on it in either half, **Then** both halves light that element, its links and its neighbours and dim the rest.
2. **Given** a link that points elsewhere in the other version, **When** it is lit, **Then** each half draws it where it points in its own version.
3. **Given** an element in both versions and outside the other half's view, **When** it is clicked, **Then** it is selected in both, its name is copied, and the other half glides to centre it, keeping its zoom, and says so for a moment.
4. **Given** an element in both versions already in the other half's view, **When** it is clicked, **Then** it is selected in both and that half does not move.
5. **Given** an element only in this version, **When** it is clicked, **Then** the other half says "Not in 0.9.0", naming its version, and does not move.
6. **Given** a selection, **When** the person clicks empty space or presses Escape, **Then** it is cleared in both halves.
7. **Given** the change stepper, **When** it steps, **Then** it acts as a click on that change: selected in both halves, centred in each that has it. There is one stepper and one set of counts for the pair.
8. **Given** an element under the pointer, **When** the hover card opens, **Then** it opens in the half under the pointer, and only there.

---

### User Story 3 - Side by side on a phone (Priority: P3)

A phone has no room for two pictures. Side by side is replaced there by an A / B switch that flips one diagram between the two versions, each in its own layout. The selected element stays in the centre across the flip.

**Why this priority**: The desktop view is the feature; the phone needs a way to reach the same comparison.

**Independent Test**: At phone width, open a pair, select an element, flip.

**Acceptance Scenarios**:

1. **Given** a phone, **When** the mode switch opens, **Then** it offers A / B in place of Side by side.
2. **Given** a phone on A with an element selected, **When** the person flips to B, **Then** B is drawn in its own layout with that element in the centre.
3. **Given** a selected element absent from the other version, **When** the person flips, **Then** the diagram says "Not in" that version.
4. **Given** a Side by side link opened on a phone, **When** the page opens, **Then** it opens as A / B, on B.

---

### User Story 4 - The same comparison for everyone in a room (Priority: P2)

People in a room look at the same pair in the same view. One changes A, B, the view, a half's layout mode, a filter or the selection, and it applies for everyone. Zoom stays each person's own; pan does too, until they follow someone.

**Why this priority**: A comparison is often discussed. It needs the halves to exist, so it comes after them.

**Independent Test**: Two browsers in one room: change each shared thing in one, watch the other; zoom and pan; then follow.

**Acceptance Scenarios**:

1. **Given** a room, **When** one person changes A, B or the view, **Then** everyone's view changes to it, whichever page they are on.
2. **Given** a room in Side by side, **When** one person changes a half's layout mode, **Then** the same half changes for everyone on that page.
3. **Given** a room, **When** one person selects an element, **Then** it is selected for everyone, whether they follow or not, and each person's other half locates it.
4. **Given** a room, **When** one person zooms, **Then** nobody else's zoom changes, followers included.
5. **Given** a room, **When** one person pans and nobody follows them, **Then** nobody else's picture moves.
6. **Given** a follower in Side by side, **When** the followed person pans a half, **Then** the follower's same half follows, and the other half stays where it is.
7. **Given** a newcomer joining a room in Side by side, **When** they arrive, **Then** they see the room's versions, view, layout modes and selection.
8. **Given** two people whose picture of a half differs, **When** the room checks, **Then** they are told "your view of this diagram differs", and the check takes in the identity of A and of B.
9. **Given** someone's pointer in a room, **When** it is over a half, **Then** it is shown over that same half for the others.

---

### Edge Cases

- **A whole diagram absent from one version** (a domain or a lifecycle that is added later): that half says "Not in" its version, and the other half still works.
- **One half cannot be read**: it shows its own error and a way to retry; the other half stays.
- **An element hidden by a filter in the other half**: that half says it is hidden by the filters, which differs from "Not in".
- **A field inside a collapsed table**: the other half centres the table. A selected field in a collapsed table stays visible, as a changed row does.
- **The pair changes while something is selected**: the selection stays, and each half locates it again or says "Not in".
- **Live as B**: Side by side works; Live has no version name, so the message says "Not in Live".
- **Handles moved until only one version remains on offer**: A and B never stand on one version; a history of one point offers neither Diff nor Side by side, greyed out, "needs two versions".
- **Leaving Side by side**: One shows B, Diff keeps the pair; each half's pan and zoom are forgotten.
- **The window narrowed to phone width during Side by side**: it becomes A / B on B, and widening brings the halves back.
- **A very large graph drawn twice**: each half shows that it is still being laid out, and the other is usable meanwhile.
- **A click that starts a pan**: a press that moved is a pan, not a click, in either half.

## Requirements *(mandatory)*

### Functional Requirements

#### The two halves

- **FR-001**: Side by side MUST be a working third mode of the picker on the ERD, the full graph, use-case and lifecycle diagrams, available when Diff is, under the same "needs two versions" rule.
- **FR-002**: A MUST stand on the left and B on the right, each drawn from its own version's graph in a layout computed for that version alone.
- **FR-003**: Each half MUST keep its own pan, zoom and, where the diagram has them, layout mode.
- **FR-004**: The versions, filters, paint and table collapse MUST be common to both halves.
- **FR-005**: Each half MUST carry comparison marks: A removed and changed, B added and changed, with the colours and signs of Diff. Unchanged elements are drawn as in Diff.
- **FR-006**: The picker's button MUST say the versions, "side by side" and the current diagram's counts; there is one set of counts and one change stepper for the pair.
- **FR-007**: The view and each half's layout mode MUST be kept in the address.
- **FR-008**: A half that cannot draw MUST NOT stop the other from working.

#### One element across both

- **FR-010**: A hover in either half MUST light the same element, its links and neighbours in both, by identity, each half drawing a link where its own version has it.
- **FR-011**: A click on an element MUST select it in both halves. A click on a name also copies it, as everywhere (spec 043).
- **FR-012**: If the element is outside the other half's view, that half MUST glide to centre it, keep its zoom and say so for a moment.
- **FR-013**: If the element is not in the other version, that half MUST say "Not in" that version's name and stay where it is. If a filter hides it there, the half MUST say so instead.
- **FR-014**: A step of the change stepper MUST act as a click on that change.
- **FR-015**: A hover card MUST open only in the half under the pointer.

#### Phone

- **FR-020**: At phone width the mode switch MUST offer A / B instead of Side by side, flipping one diagram between the versions, each in its own layout.
- **FR-021**: The selected element MUST stay centred across a flip, or the diagram says "Not in" that version.

#### Rooms

- **FR-030**: A room MUST hold, as a whole and not per page: the history address, A, B and the view, changed by absolute values ("set A to 0.8.0"), never by steps.
- **FR-031**: Filters, collapse and each half's layout mode MUST be shared on their page, as page settings are today.
- **FR-032**: The selection MUST be shared with everyone in the room, not only followers.
- **FR-033**: Zoom MUST never be shared. Pan MUST be shared only with followers, half by half.
- **FR-034**: A newcomer MUST receive all of the above on joining.
- **FR-035**: The room's check MUST compare each half's picture and take in the sha256 of A and of B.
- **FR-036**: Pointers and followed positions MUST stand in the half they belong to.

#### Unchanged

- **FR-040**: One and Diff, and rooms in them, MUST behave as they do today on every diagram.
- **FR-041**: The same version pair and settings MUST give the same layout in each half on every browser engine the check run covers.

### Key Entities

- **Half**: one side of the view: which version it shows, its layout mode, its pan and zoom, and what it reports to the room.
- **Selection**: the one element chosen for the pair, by identity; it may exist in one version only.
- **View**: One, Diff or Side by side; on a phone A / B is how Side by side appears, not a fourth view for a room.
- **Room's comparison state**: history address, A, B and view, held by the room as a whole.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On each of the four diagrams, a pair opens in Side by side with each half in its own layout, and a change in one half's pan, zoom or layout mode moves nothing in the other.
- **SC-002**: A click on an element present in both versions brings it into the other half's view in under one second, with that half's zoom unchanged.
- **SC-003**: Hovering in either half lights the same element in both, without a visible delay.
- **SC-004**: In a two-browser room, a change of A, B, the view, a half's layout mode, a filter or the selection appears in the other browser within one second; zoom never does; pan does only while following.
- **SC-005**: Opening Side by side takes no more than twice the time of opening Diff on the same pair.
- **SC-006**: Every existing check of One, Diff and rooms passes unchanged.

## Assumptions

- The pair's comparison, the marks, the cards and the stepper already exist (#290–#293) and are reused, not redesigned.
- The look follows the mockup's screen Side by side and its Phone screen.
- Each half starts in the layout mode the page has when Side by side opens.
- Selection is not kept in the address: it is a moment of work, held by the room while a room is open.
- Phone width is the width at which Maxitor already treats a screen as a phone.
- Side by side compares exactly two versions; renames are not detected (#273, out of scope).
- Issue #294's phases are rewritten to match the plan, and its "step 10 of 10" becomes 9 of 9.
