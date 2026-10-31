# Feature Specification: Maxitor Compares Two Versions on Use-Case Diagrams

**Feature Branch**: `feature/issue-292-use-case-diff`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Issue #292 (Graph history): comparison on use-case diagrams. Source: https://github.com/bystrovmaxim/aoa/issues/292, mockup specs/030-graph-history/mockup/index.html (screen Use case: changed inside), previous steps specs/038-erd-diff, specs/039-full-graph-diff, specs/040-full-graph-map. Bring over everything of value built for the ERD and the full graph that the issue does not name. Branch already created: feature/issue-292-use-case-diff."

## Context: what is true today, checked on 2026-10-31

- **Diff exists on the ERD and on the map** (specs 038, 040). On a use-case diagram the same mode shows version B as in One, and the button names the range without counts.
- **The server already compares.** One read gives the status of every changed element and the counts; a second gives one element's differences. An element it leaves out is unchanged. Each element is compared alone: a changed result field changes the status of that field, and never of the action that owns it.
- **A use-case diagram draws actions, roles and five kinds of link**: association (`@check_roles`), include and extend (`@depends` between actions), action generalization, role generalization. It is built for one domain from one version, and closes over parents and `@depends` targets, so it can draw actions of other domains. Its links carry no protocol `id` in the answer; only their kind and two ends.
- **What an action owns in the graph** (the demo's graph, read on 2026-10-31): `Params` and `Result` through `generic:*`, their `Field` and `PropertyField` nodes (with `Sensitive`), `SummaryAspect` and `RegularAspect`, the aspects' `Checker` and `RequiredContext`, `ErrorHandler`, `Compensator`, `AccessDecide`. A `Field` reaches an `Entity` only through `entity_schema`, which only points at it. A `Result` or `Params` node may be shared: 61 actions hold 51 `Result` nodes.
- **The card reads one or more elements** and joins their differences; it is shared by the ERD and the map.
- **Two choices were made after the issue was written**: the map's version button counts every change the diagram marks, nodes and links (spec 040, FR-024, replacing spec 039's nodes only), and the change stepper belongs on every diagram that marks a comparison (spec 040, FR-025e).

## What this step takes from the ERD and the full graph

The issue names statuses, "changed inside", the card and the counts. The rest of what a comparison became over #290, #291 and #319 is not in it, and a use-case diagram without it would be the one diagram that reads differently. This step carries over:

| From | What | Where here |
|------|------|------------|
| 038 | "No changes" and nothing faded when nothing drawn changed | FR-013 |
| 038 | A status readable as a sign, not by colour alone | FR-006 |
| 038 | The left panel's `+` and `−` pages: a domain only in A opens | FR-015 |
| 038 | The card's closing rules, and following Live | FR-012, FR-014 |
| 038 | A refused comparison, a `1.0` graph | Edge Cases |
| 040 | Counts of everything marked, nodes and links | FR-010 |
| 040 | The change stepper, its list, Shift + ↑ ↓, its legend, in a room | FR-016 – FR-019 |
| 040 | The filter panel with Changes, and the gear shift that paints | FR-020 – FR-023 |
| 040 | A step does not depend on what is in view | FR-017 |

## The acceptance stand

The maintainer's decision (2026-10-31): this step is accepted in the real Maxitor on the history `erd-full` in `.demo-history/` (out of git), extended through its builder, `.demo-history/build_erd_full.py`. The static page `.demo-history/map-demo` stays a reference for the look only.

The stand MUST hold: an action whose only change is a new result field; one whose only change is a changed field; one whose params changed; one with a reworded aspect; an action added and one removed; a role added and one removed; an association added and one removed; an include or extend whose mode changed; an action of another domain drawn through a dependency, changed inside; a domain only in A and one only in B; a pair with nothing drawn changed although the graph changed.

## Clarifications

### Session 2026-10-31

- Q: On which stand is this step accepted? → A: On `erd-full` in the real Maxitor; `map-demo` is a reference for the look.
- Q: Does this step bring the ERD's filter panel, with Changes and the gear shift, to the use-case diagram? → A: Yes, whole, in place of the domain legend.
- Q: Does a changed link to a resource count as changed inside? → A: Yes: everything an action owns that the diagram does not draw counts, the issue's three kinds being examples.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See what a release did to a domain's use cases (Priority: P1)

With A and B chosen, the developer opens a domain's use cases. Both versions are drawn at once: new actions and roles green, removed ones red and dashed, changed ones amber, the links following, everything else faded. The version button counts the changes.

**Why this priority**: This is the step: the picture of who can do what, and how a release changed it.

**Independent Test**: Open a pair on the stand, a domain's use cases; check every mark against the comparison and the button against the marks.

**Acceptance Scenarios**:

1. **Given** A and B, **When** a domain's use cases are shown, **Then** every action, role and link of either version in that domain's diagram is drawn once: added green, removed red and dashed, changed amber, unchanged faded.
2. **Given** a link added, removed or changed, **When** shown, **Then** it takes that status's colour whatever its ends' marks; an unchanged link fades, also between two marked ends.
3. **Given** a `@depends` link whose mode changed from include to extend, **When** shown, **Then** it is one amber link with B's stereotype.
4. **Given** two versions where nothing drawn differs, **When** shown, **Then** the button says "no changes" and the diagram is drawn as in One, nothing faded.
5. **Given** B is Live, **When** the live graph changes, **Then** the marks and counts follow without a reload.
6. **Given** Diff → One, **When** the switch is made, **Then** the diagram is version B again, unmarked.

---

### User Story 2 - An action that changed inside (Priority: P1)

An action's parts are not on this diagram. When one changed, the action is amber, and the diagram does not pretend nothing happened.

**Why this priority**: It is what the issue adds. In gameoffer's 0.8.0 → 0.9.0 no action in OffersDomain came or went, yet three changed: without this the release would look empty.

**Independent Test**: On the stand, change only one result field of an action; that action alone is amber; break the rule and see the test fail.

**Acceptance Scenarios**:

1. **Given** a part of an action added, removed or changed, **When** the use cases are shown, **Then** the action is marked changed, although the action's own node did not change.
2. **Given** gameoffer's 0.8.0 → 0.9.0 in OffersDomain, **When** shown, **Then** `ReadOfferAction`, `ReadOffersAction` and `ReadOfferRequestAction` are marked changed and no other action is.
3. **Given** a `Result` shared by several actions, **When** one of its fields changes, **Then** each action using it is marked.
4. **Given** the same pair on the ERD, **When** shown, **Then** the fields are marked and nothing is propagated: a diagram that draws the parts marks the parts.

---

### User Story 3 - Read which parts changed (Priority: P1)

The developer clicks an action marked changed and the card opens: which parts changed, before and after.

**Why this priority**: The mark says *that* the action changed; on this diagram only the card can say *what*.

**Independent Test**: Click an action changed inside, one changed itself, an added, a removed and an unchanged one; compare the card with the comparison.

**Acceptance Scenarios**:

1. **Given** an action changed inside, **When** clicked, **Then** the card says the action is the same and lists its parts: each added, removed or changed part, grouped under Params, Result, or the aspect it belongs to, with both values.
2. **Given** `ReadOfferRequestAction` on gameoffer's pair, **When** clicked, **Then** the card lists its result's new and changed fields.
3. **Given** an action whose own properties and parts both changed, **When** clicked, **Then** the card lists both.
4. **Given** a role, or an action added or removed, **When** clicked, **Then** the card lists its properties or says it was added or removed in B.
5. **Given** an unchanged element, **When** clicked, **Then** it behaves as in One.

---

### User Story 4 - Walk the changes, and narrow them (Priority: P2)

The developer steps through the changes with the same control as on the ERD and the map, and narrows the diagram with the same panel.

**Why this priority**: A developer who has learned Diff on one diagram must not relearn it here, and a large domain's changes are easier to read one at a time.

**Independent Test**: Step through every change forwards and backwards; open the list; switch a change kind off; repeat in a room.

**Acceptance Scenarios**:

1. **Given** Diff with changes, **When** the stepper is used or Shift + ↑ ↓ pressed, **Then** the diagram goes to each change in turn, with the position and the total shown and its card open.
2. **Given** a change that is a link, **When** stepped to, **Then** the link is brought into view and marked.
3. **Given** the filter panel in Diff, **When** a domain or a change kind is switched off, **Then** those elements leave, and the counts, the stepper and "no changes" follow what is left.
4. **Given** a room, **When** a participant steps or filters, **Then** the room behaves as on the ERD.

### Edge Cases

- **A domain only in A or only in B** — its page opens and its diagram is drawn from the version that has it, every element marked.
- **An action drawn from another domain** through a parent or a dependency — marked like any drawn action, changed inside included.
- **A changed parent action** — the parent is marked; its children are not: a parent is drawn, so it carries its own mark.
- **An action that moved to another domain under the same id** — drawn on both domains' diagrams, marked changed inside; the card names the domain in A and in B. Under a new id it is a removal plus an addition (spec 038, FR-007).
- **An added or removed action** — its status stands; its parts are not listed and do not make it "changed".
- **A field's nested schema** — when the field's own properties carry it, its difference shows on the card by its path.
- **An action with only a link changed** — not marked: the link carries the mark, because the link is drawn.
- **An action's undrawn link changed** (a resource through `@connection`) — that is changed inside, and the card lists it.
- **A filter hiding the element of an open card** — the card closes.
- **A `1.0` graph, a graph refused as not comparable, a refused version, Live unreachable** — as on the ERD (spec 038).
- **Switching A or B while a layout runs** — only the current pair is drawn.
- **Boundary off, Dot, Neato, FDP** — each layout mode works in Diff as in One.

## Requirements *(mandatory)*

### Functional Requirements

**The union**

- **FR-001**: In Diff a use-case diagram MUST draw the union of A's and B's diagram of that domain: every action, role and link of either, each once, matched by the protocol's `id`, never by position.
- **FR-002**: A link's status MUST be read from the protocol edge it is drawn from; a drawn link standing for several edges MUST take a single status by a stated rule.
- **FR-003**: An element in both versions MUST be drawn with B's label and stereotype.
- **FR-004**: The union MUST be laid out by the diagram's own rules and modes, with one input for one pair, so that one pair gives one picture.

**The marks**

- **FR-005**: Added elements MUST be green, changed amber, removed red with a dashed outline, unchanged faded.
- **FR-006**: Each mark's status MUST also be readable as `+`, `−` or `~`, in the element's hover label and on its card, so that colour is not the only signal.
- **FR-007**: A link MUST carry its own status, inherited from neither end.
- **FR-008**: An action MUST be marked changed when any of its parts was added, removed or changed. Its parts are what it owns and the diagram does not draw: its params, its result and their fields and properties, its aspects with their checkers and required context, its error handlers, compensators and object rules, and its links the diagram does not draw, to them, to resources or to its domain. A drawn element (a role, a domain's action) or a link the diagram draws MUST NOT be a part. The walk MUST stop at those, and MUST NOT cross into entities.
- **FR-009**: An element that draws its own parts MUST NOT be touched by FR-008: on the ERD and the map every mark stays the element's own status in the comparison.

**The counts**

- **FR-010**: The version button MUST read `◷ A <name of A> → B <name of B>  +<added> −<removed> ~<changed> ▾`, counting every change the diagram marks, actions, roles and links, an action changed inside as one changed element.
- **FR-011**: The counts MUST be of what is drawn after the filters.

**The card**

- **FR-012**: A click on a marked action, role or link MUST open spec 038's card (FR-028, FR-029); for an action changed inside it MUST say in one line that the action is the same, then list the changed parts by name, grouped by the part they belong to, each with its values in A and B.
- **FR-013**: When nothing drawn changed, the button MUST say "no changes" and the diagram MUST be drawn as in One. A change inside an action is drawn, so it is a change.
- **FR-014**: When B is Live and the live graph changes, marks, counts and an open card MUST follow without a reload.
- **FR-015**: The left panel's `+` and `−` pages MUST open on a domain found in one version only (spec 038, FR-032).

**The stepper**

- **FR-016**: The change stepper of spec 040 (FR-025b, FR-025d, FR-025e) MUST stand on this diagram with the same look, list, keys and legend.
- **FR-017**: The list of changes MUST be built from the whole drawn diagram, not from what is in view, in one defined order, and hold every change the diagram marks, links as well as nodes.
- **FR-018**: A step MUST bring the change into view and open its card, a link's too.
- **FR-019**: In a room a follower MUST see the control as on the ERD (spec 040, FR-025f).

**Filters**

- **FR-020**: The diagram MUST have the ERD's filter panel with Domains, and in Diff Changes, replacing the domain legend, in One and in Diff.
- **FR-021a**: The panel MUST have an Elements section, Actions and Roles, with grey disks: it paints nothing and has no place on the gear shift. What it switches off MUST hide with its links; 1-hop MAY bring it back, as on the ERD, where it stands one link from what is left. The counts and the steps MUST follow what is drawn.
- **FR-021**: A switched-off domain or change MUST hide its elements and their links. A 1-hop switch, on at first as on the ERD, MUST bring back what stands one link away from what the filters left.
- **FR-022**: The gear shift MUST paint as on the ERD: Domains in One, Changes in Diff (spec 040, FR-030 – FR-032). Painted by changes, everything unchanged MUST be grey and dim; painted by domains it keeps its colour, dim.
- **FR-023**: Filters and paint MUST be carried by the address and shared by a room, One's paint and Diff's kept apart.

**The left panel and the lifecycles** (the maintainer's request of 2026-11-01)

- **FR-027**: The left panel MUST hold only rows that open something: Applications with Full graph view, ERD all domains view and Use case all domains view; Domains with each domain's Entity domain view, Use case view and its lifecycles. The Application row and the Roles, Actions, Entities and Resources sections MUST go.
- **FR-027a**: A domain with no entities MUST have no Entity domain view, and one with no actions no Use case view. A domain left with no rows MUST stay in the panel, dim, saying it is empty.
- **FR-028**: Use case all domains view MUST draw every action and every role on one diagram, with everything a domain's use cases have, Diff included.
- **FR-029**: A domain MUST hold one lifecycle row per lifecycle of its entities, each opening that lifecycle's own diagram: as many rows as entities have one. An entity with several lifecycles has a row for each, named by its field.

**Open pull requests on the track** (the maintainer's decision of 2026-11-01; it replaces spec 037, FR-016 "Live last" and spec 038, FR-011 "Live MUST only ever be B")

- **FR-032**: The track MUST read: versions, Live, then the open pull requests by date, the oldest first. Their work is ahead of what runs, so A = Live, B = a pull request MUST read as progress. Roles still follow position, so Live MAY be A when a pull request is B.

**Hover**

- **FR-033**: Hovering an action, a role or a link on a use-case diagram MUST light it, its links and what they reach, and dim the rest, as on the ERD, in One and in Diff; a room follows it. A link MUST be easy to hit at every zoom, and a hover MUST show names, never an internal id.

**The server and the tail**

- **FR-024**: What an action's parts are, and which changed, MUST be decided on the server, by AOA actions, in one place, so that the marks, the counts, the card and the stepper read one answer and cannot disagree.
- **FR-025**: Every read MUST obey spec 037's rules for keys and logs.
- **FR-026**: The change MUST end with the check run taken to zero, then the documentation — every case above, as a runnable script and a notebook — with the page's Russian draft beside it, then the changelog, one article (Principle VI).

### Key Entities

- **Part of an action**: what it owns and a use-case diagram does not draw.
- **Changed inside**: an action whose own node is unchanged and at least one of whose parts is not.
- **Mark**: what a drawn element shows of its status.
- **Diagram counts**: every change the diagram marks, by status.
- **Change list**: the marked changes of one diagram, in one order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every pair walked on the acceptance stand, the button's counts equal the diagram's marks of each kind.
- **SC-002**: After the merge, on the real stand, gameoffer's 0.8.0 → 0.9.0 in OffersDomain marks exactly three actions changed, and `ReadOfferRequestAction`'s card lists its result's new and changed fields (issue, criteria 1 and 2).
- **SC-003**: 100 % of an action's changed parts appear on its card, each with both values.
- **SC-004**: An action with no changed part and no changed property is never marked, in 100 % of a test's actions.
- **SC-005**: Marks on the ERD and the map do not change by this work: the same pair gives the same marks before and after.
- **SC-006**: Every change of a diagram is reached by stepping, each exactly once in one round.
- **SC-007**: Two versions with nothing drawn changed say "no changes" and fade nothing.
- **SC-008**: With B on Live, a change shows on the open diagram within the freshness check (30 seconds), with no reload.
- **SC-009**: The check run passes, every step.

## Assumptions

- **Graphviz stays** the engine of use-case diagrams, and the union is laid out as the ERD's is: switching to Diff may move elements. The map's rule that nodes stand where they stand in B is the map's own, for a layout it holds on the server.
- **A link has a card here**, unlike on the ERD and the map: on this diagram links are half of what a release changes, and the maintainer asked for it on 2026-10-31.
- **The issue's criteria are checked on gameoffer by the maintainer after the merge**, as in #291; being done is accepted on the stand.
- **A parent's change does not reach its children**, and an entity's change does not reach an action: a parent is drawn, and `entity_schema` only points at an entity the action does not own. On gameoffer, if a field's items are such an entity, their change shows on the ERD and not here; the maintainer's check after the merge settles it.
- **The mockup's picture is a stand-in**; its marks and its card are the reference.
- **Side by side** stays greyed out (#294); lifecycles stay as they are (#293).
- **Pictures** in the issue body are still to be added by the maintainer.
