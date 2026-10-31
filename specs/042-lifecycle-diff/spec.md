# Feature Specification: Maxitor Compares Two Versions on Lifecycle Diagrams

**Feature Branch**: `feature/issue-293-lifecycle-diff`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Issue #293 (Graph history): comparison on lifecycle diagrams. Source: https://github.com/bystrovmaxim/aoa/issues/293, mockup specs/030-graph-history/mockup/index.html (screen Lifecycle that A does not have), previous steps specs/038-erd-diff, specs/039-full-graph-diff, specs/040-full-graph-map, specs/041-use-case-diff. Bring over everything of value built for the ERD, the full graph and the use-case diagram that the issue does not name. Accepted on the local stand erd-full in .demo-history, extended through build_erd_full.py. Known issue conflict: criterion 1 says the button counts +4, while spec 040 FR-024 counts every marked node and link. Branch already created: feature/issue-293-lifecycle-diff."

## Context: what is true today, checked on 2026-11-01

- **Diff exists on the ERD, the map and the use-case diagrams** (specs 038, 040, 041). On a lifecycle diagram the same mode shows version B as in One, and the button names the range without counts.
- **The server already compares.** Every state is a graph node and every transition a graph edge, so both already have a status. A transition's `id` is its lifecycle's source state, its target state and the state it leaves (spec 038, FR-006, from #285), so two transitions into one state from different states are already two elements.
- **A lifecycle diagram draws one lifecycle of one entity**: its states and its transitions, an entry dot leading to each initial state and an exit dot reached from each final state. The diagram has zoom, two layout directions (left to right, top to bottom) and following in a room. It has no card, no hover lighting, no filter panel and no stepper.
- **The answer a lifecycle diagram reads** carries no `id` for a transition, only its two ends, and is read from one version only.
- **The left panel** already lists the pages of A and of B together and marks those of one version with `+` or `−` (spec 038, FR-032), and holds one lifecycle row per entity's lifecycle under its domain (spec 041, FR-029). Whether such a lifecycle row opens has not been tried: the diagram reads one version, the shown one.
- **What a state carries** beyond its name: its kind (initial, intermediate, final), its key, its lifecycle's class and its attributes, among them display name, order and declared colours.
- **One choice was made after the issue was written**: the button counts every change the diagram marks, nodes and links (spec 040, FR-024; spec 041, FR-010). The issue's "+4" and the mockup's are the four states alone; gameoffer's new lifecycle has four states and three transitions, so the same rule gives **+7**. This spec follows the rule, and the issue's criterion is corrected to match.

## What this step takes from the ERD, the full graph and the use-case diagram

The issue names statuses, the left panel's pages, the counts and the card. The rest of what a comparison became over #290, #291, #292 and #319 is not in it, and a lifecycle diagram without it would be the one diagram that reads differently. This step carries over:

| From | What | Where here |
|------|------|------------|
| 038 | "No changes" and nothing faded when nothing drawn changed | FR-012 |
| 038 | A status readable as a sign, not by colour alone | FR-006 |
| 038 | The card's closing rules, and following Live | FR-014, FR-015 |
| 038 | A refused comparison, a `1.0` graph | Edge Cases |
| 040 | Counts of everything marked, nodes and links | FR-010 |
| 040 | The change stepper, its list, Shift + ↑ ↓, its legend, in a room | FR-016 – FR-019 |
| 040 | The filter panel with Changes, and the gear shift that paints | FR-020 – FR-024 |
| 040 | A step does not depend on what is in view | FR-017 |
| 041 | A link has a card of its own | FR-013 |
| 041 | Hover lighting an element, its links and what they reach | FR-025 |
| 041 | 1-hop, on at first | FR-022 |
| 041 | One input for one pair, one picture | FR-004 |
| 041 | Open pull requests on the track, Live as A | Edge Cases |

## The acceptance stand

The maintainer's decision (2026-11-01): this step is accepted in the real Maxitor on the same stand as #290, #291 and #292, the history `erd-full` in `.demo-history/` (out of git), extended through its builder, `.demo-history/build_erd_full.py`.

The stand MUST hold: a lifecycle only in B and one only in A, on an entity present in both; a state added and one removed; a state renamed in its display name; a state whose kind changed; a state whose declared colour changed; a transition added and one removed; a transition moved to another target; two transitions into one state from different states, one of them new; a lifecycle that gained a second initial state; a state whose order alone changed; a pair where a lifecycle did not change although the graph did; an entity moved to another domain with its lifecycle.

## Clarifications

### Session 2026-11-01

- Q: What should the filter panel on a lifecycle diagram be? → A: In One and in Diff: a section of state kinds and, in Diff, Changes; the gear shift paints by kinds in One and by changes in Diff; 1-hop on at first.
- Q: Is a state marked when only something the diagram does not draw changed, such as its order or its lifecycle's class? → A: Yes: every change of a state's properties marks it, and the card says what changed.
- Q: How do unchanged elements look in Diff? → A: Grey and dim, not faded in their own colours.
- Q: How does the left panel show a lifecycle that exists in both versions and changed? → A: With `~` on its row (it is the agent's decision, the maintainer told it to go on with its own): a domain can hold a dozen lifecycles, and this one has no other way to be found.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See what a release did to a lifecycle (Priority: P1)

With A and B chosen, the developer opens a lifecycle. Both versions are drawn at once: new states and transitions green, removed ones red and dashed, changed states amber, everything else grey and dim. The version button counts the changes.

**Why this priority**: This is the step: a lifecycle says what can happen to an entity, and a release that changes it changes the product's rules.

**Independent Test**: Open a pair on the stand, a lifecycle that changed; check every mark against the comparison and the button against the marks.

**Acceptance Scenarios**:

1. **Given** A and B, **When** a lifecycle is shown, **Then** every state and transition of either version is drawn once: added green, removed red and dashed, changed amber, unchanged grey and dim.
2. **Given** two transitions into one state from different states, one of them new in B, **When** shown, **Then** they are two transitions, one green and one grey.
3. **Given** a transition that leads to another state in B, **When** shown, **Then** it is two transitions, the old one red and the new one green, never one amber.
4. **Given** a transition added between two unchanged states, or an unchanged one between two marked states, **When** shown, **Then** it takes its own status, whatever its ends' marks.
5. **Given** two versions where nothing drawn differs, **When** shown, **Then** the button says "no changes" and the diagram is drawn as in One, nothing faded.
6. **Given** B is Live, **When** the live graph changes, **Then** the marks and counts follow without a reload.
7. **Given** Diff → One, **When** the switch is made, **Then** the diagram is version B again, unmarked and exactly as before this work.

---

### User Story 2 - A lifecycle that only one version has (Priority: P1)

The developer sees in the left panel a lifecycle marked `+` or `−`, opens it, and sees all of it green or all of it red.

**Why this priority**: It is the issue's first criterion and the real case behind it: gameoffer's `OfferRequestCoreEntity` got its lifecycle in 0.9.0.

**Independent Test**: On the stand, open the lifecycle only in B and the one only in A from the left panel, and by a shared address.

**Acceptance Scenarios**:

1. **Given** a lifecycle only in B, **When** the left panel is shown, **Then** its row is marked `+`, and opening it draws every state and transition green, the entry and exit dots too.
2. **Given** a lifecycle only in A, **When** opened, **Then** its row is marked `−` and everything is red and dashed.
3. **Given** gameoffer's 0.8.0 → 0.9.0, **When** the lifecycle of `OfferRequestCoreEntity` is opened, **Then** it is all green and the button counts +7: four states, three transitions (issue, criterion 1, corrected).
4. **Given** a lifecycle only in A is open in Diff, **When** Diff → One is chosen, or the range moves to a pair without it, **Then** the page says the lifecycle is not in this version and offers the way back, as a domain does.

---

### User Story 3 - Read what changed (Priority: P1)

The developer clicks a marked state or transition and the card opens: what changed, before and after.

**Why this priority**: A mark says *that* a state changed; a renamed state and one that became final look alike on the diagram, and only the card can tell them apart.

**Independent Test**: Click a state changed in name, in kind and in colour, an added and a removed state, an added transition and an unchanged element; compare each with the comparison.

**Acceptance Scenarios**:

1. **Given** a changed state, **When** clicked, **Then** the card lists every property that changed by its path, with its value in A and in B.
2. **Given** a state whose kind changed from intermediate to final, **When** clicked, **Then** the card says so in plain words, and the diagram draws it as final.
3. **Given** an added or removed state, **When** clicked, **Then** the card says it was added or removed in B and lists its kind and name.
4. **Given** an added or removed transition, **When** clicked, **Then** the card names the state it leaves and the state it enters, by their display names.
5. **Given** an unchanged element, **When** clicked, **Then** it behaves as in One.

---

### User Story 4 - Walk the changes, narrow them, trace them (Priority: P2)

The developer steps through the changes with the same control as on the other diagrams, narrows the diagram with the same panel, and hovers a state to see where it leads.

**Why this priority**: A developer who has learned Diff on one diagram must not relearn it here, and a dense lifecycle (the demo's reach a dozen states) is easier to read one change at a time.

**Independent Test**: Step through every change forwards and backwards; open the list; switch a change kind off; hover a state; repeat in a room.

**Acceptance Scenarios**:

1. **Given** Diff with changes, **When** the stepper is used or Shift + ↑ ↓ pressed, **Then** the diagram goes to each change in turn, with the position and the total shown and its card open.
2. **Given** a change that is a transition, **When** stepped to, **Then** the transition is brought into view and marked.
3. **Given** the filter panel in Diff, **When** a change kind is switched off, **Then** those elements leave with the transitions touching them, and the counts, the stepper and "no changes" follow what is left.
4. **Given** a state, **When** hovered, in One or in Diff, **Then** it, its transitions and the states they reach light up and the rest dims, and a room follows it.
5. **Given** a room, **When** a participant steps or filters, **Then** the room behaves as on the ERD.

### Edge Cases

- **An initial or final state added, removed or of another kind** — the entry or exit dot's arrow to it follows that state: an arrow of one version only takes green or red, an arrow in both stays grey. The dots and their arrows are not elements of the graph: they are never counted, stepped to or opened.
- **The entry and exit dots themselves** — drawn when either version needs them; green or red only when every arrow on them has that status.
- **A state with a declared colour** — in Diff the status's colour replaces it, and an unchanged state is grey and dim. One keeps it.
- **A lifecycle's class renamed or moved under the same field** — every state's class changed, so every state is amber and each card says so. It is what the comparison says, and it is true.
- **A state's order changed only** — it is a changed attribute, amber like any other: the comparison decides, not the drawing.
- **A state renamed by its key** — a removal plus an addition, with its transitions (spec 038, FR-007). By its display name only — one amber state.
- **An entity moved to another domain with its lifecycle** — under the same id, the row stands under each domain, marked `−` and `+`, and both open one and the same diagram.
- **A transition from a state to itself** — marked and clickable like any other.
- **A lifecycle with no state in the shown version** — it has no row (spec 041, FR-027); in Diff the union decides.
- **A filter hiding the element of an open card** — the card closes.
- **A `1.0` graph, a graph refused as not comparable, a refused version, Live unreachable** — as on the ERD (spec 038).
- **Live as A, a pull request as B** — works as on the other diagrams (spec 041, FR-032).
- **Switching A or B while a layout runs** — only the current pair is drawn.
- **Both layout directions** — each works in Diff as in One, and a room shares it.
- **A phone** — a tap opens a card, the panel starts as the Filter pill, as on the other diagrams.

## Requirements *(mandatory)*

### Functional Requirements

**The union**

- **FR-001**: In Diff a lifecycle diagram MUST draw the union of A's and B's diagram of that lifecycle: every state and transition of either, each once, matched by the protocol's `id`, never by position.
- **FR-002**: A transition's status MUST be read from the protocol edge it is drawn from, so the answer a lifecycle diagram reads MUST carry that edge's `id`, and that answer MUST otherwise stay as it is in One.
- **FR-003**: An element in both versions MUST be drawn with B's label and kind.
- **FR-004**: The union MUST be laid out by the diagram's own rules and directions, with one input for one pair, so that one pair gives one picture.

**The marks**

- **FR-005**: Added elements MUST be green, changed amber, removed red with a dashed outline, unchanged grey and dim, whatever colour they declare, as long as the changes paint (FR-023).
- **FR-005a**: A state MUST be marked changed when any of its properties differs, a property the diagram does not draw included (spec 038, FR-003); the drawing never decides a status.
- **FR-006**: Each mark's status MUST also be readable as `+`, `−` or `~`, on the element itself and on its card, so that colour is not the only signal. A state MUST keep its shape from One: a final state reads as final by its arrow to the exit dot, with no second outline.
- **FR-007**: A transition MUST carry its own status, inherited from neither end.
- **FR-008**: A transition leading to another state, or leaving another state, MUST be a removal plus an addition, because its identity is its lifecycle, the state it leaves and the state it enters. Nothing on this diagram is drawn as a retargeted link.
- **FR-009**: The entry and exit dots and their arrows MUST follow FR-005 as the Edge Cases say, and MUST NOT be counted, stepped to or opened.

**The counts**

- **FR-010**: The version button MUST read `◷ A <name of A> → B <name of B>  +<added> −<removed> ~<changed> ▾`, counting every change the diagram marks, states and transitions.
- **FR-011**: The counts MUST be of what is drawn after the filters.
- **FR-012**: When nothing drawn changed, the button MUST say "no changes" and the diagram MUST be drawn as in One.

**The card**

- **FR-013**: A click on a marked state or transition MUST open spec 038's card (FR-028, FR-029): every property that changed by its path, with both values; an added or removed one says so, and a transition is named by the display names of its two states. A hover and a card MUST show names, never an internal id.
- **FR-014**: The card MUST close by a click outside or Escape, and when its element is filtered away.
- **FR-015**: When B is Live and the live graph changes, marks, counts and an open card MUST follow without a reload.

**The stepper**

- **FR-016**: The change stepper of spec 040 (FR-025b, FR-025d, FR-025e) MUST stand on this diagram with the same look, list, keys and legend.
- **FR-017**: The list of changes MUST be built from the whole drawn diagram, not from what is in view, in one defined order, and hold every change the diagram marks, transitions as well as states.
- **FR-018**: A step MUST bring the change into view and open its card, a transition's too.
- **FR-019**: In a room a follower MUST see the control as on the ERD (spec 040, FR-025f).

**Filters**

- **FR-020**: The diagram MUST have the ERD's filter panel, in One and in Diff, with an Elements section of the state kinds present (Initial, Intermediate, Final) and, in Diff, Changes. It has no Domains section: a lifecycle belongs to one entity.
- **FR-021**: A switched-off state kind or change MUST hide its elements and the transitions touching them; a transition's own change kind switched off MUST hide that transition.
- **FR-022**: A 1-hop switch, on at first as on the ERD, MUST bring back what stands one transition away from what the filters left.
- **FR-023**: In Diff the panel MUST carry the gear shift (spec 040, FR-030 – FR-032), between Elements and Changes, on Changes at first, where everything unchanged is grey and dim (FR-005). Painted by kinds, a state keeps its kind's fill, its outline says its status, and an unchanged one keeps its kind, dim. One has one section, so no gear shift.
- **FR-024**: Filters and paint MUST be carried by the address and shared by a room, One's paint and Diff's kept apart. Untouched, the panel MUST leave One's picture as it is today.

**Hover**

- **FR-025**: Hovering a state or a transition MUST light it, its transitions and what they reach, and dim the rest, as on the use-case diagram, in One and in Diff; a room follows it. A transition MUST be easy to hit at every zoom.

**The left panel**

- **FR-026**: A lifecycle row marked `+` or `−` MUST open, its diagram read from the version that has it (spec 038, FR-032), also from a shared address.
- **FR-026a**: In Diff a lifecycle row in both versions MUST be marked `~` when any of its states or transitions was added, removed or changed. This mark belongs to lifecycle rows alone.
- **FR-027**: Opening a lifecycle MUST expand its domain in the left panel, in Diff as in One, a row of one version included.
- **FR-028**: A lifecycle absent from the shown version or pair MUST say so and offer a way back; it MUST NOT show an error.

**The server and the tail**

- **FR-029**: Reading a lifecycle of a version MUST be an AOA action and MUST obey spec 037's rules for keys and logs; an endpoint added for this MUST be an action too.
- **FR-030**: The drawing in One MUST NOT change by this work, the panel and the hover apart: the same version gives the same picture.
- **FR-031**: The marks on the ERD, the map and the use-case diagrams MUST NOT change by this work.
- **FR-032**: The change MUST end with the check run taken to zero, then the documentation — every case above, as a runnable script and a notebook — with the page's Russian draft beside it, then the changelog, one article (Principle VI).

### Key Entities

- **State**: a node of the lifecycle, with its kind and attributes; the diagram's main mark.
- **Transition**: an edge of the lifecycle, known by the state it leaves and the state it enters.
- **Entry and exit dots**: pieces of the drawing, not of the graph.
- **Diagram counts**: every change the diagram marks, by status.
- **Change list**: the marked changes of one diagram, in one order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every pair walked on the acceptance stand, the button's counts equal the diagram's marks of each kind.
- **SC-002**: After the merge, on the real stand, gameoffer's 0.8.0 → 0.9.0 opens the lifecycle of `OfferRequestCoreEntity` from the left panel, all green, and the button counts +7 (issue, criterion 1, corrected).
- **SC-003**: Two transitions into one state from different states are told apart in 100 % of the stand's cases: each has its own mark, count, step and card (issue, criterion 2).
- **SC-004**: 100 % of a changed element's changed properties appear on its card, each with both values.
- **SC-005**: Every change of a diagram is reached by stepping, each exactly once in one round.
- **SC-006**: Two versions with nothing drawn changed say "no changes" and fade nothing.
- **SC-007**: With B on Live, a change shows on the open diagram within the freshness check (30 seconds), with no reload.
- **SC-008**: A lifecycle in One gives the same picture before and after this work, on every lifecycle of the demo.
- **SC-009**: Marks on the ERD, the map and the use-case diagrams do not change: the same pair gives the same marks before and after.
- **SC-010**: The check run passes, every step.

## Assumptions

- **The issue's text is corrected to +7** in criterion 1, and its title and "step" line are made to agree, once the maintainer confirms the spec.
- **Graphviz stays** the engine of lifecycle diagrams, and the union is laid out as the ERD's is: switching to Diff may move states.
- **The comparison needs no new rule on the server.** States and transitions own nothing the diagram does not draw, so there is no "changed inside" here; the structural edge that ties a state to its lifecycle is not drawn and not counted.
- **The issue's criteria are checked on gameoffer by the maintainer after the merge**, as in #291 and #292; being done is accepted on the stand.
- **The mockup's picture is a stand-in**: its look of marks is the reference, its count of +4 is not.
- **Side by side** stays greyed out (#294).
- **Pictures** in the issue body are still to be added by the maintainer.
