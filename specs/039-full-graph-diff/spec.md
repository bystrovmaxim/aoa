# Feature Specification: Maxitor Compares Two Versions on the Full Graph

**Feature Branch**: `feature/issue-291-full-graph-comparison`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Issue #291 (Graph history 6/9): comparison on the full graph. Source: https://github.com/bystrovmaxim/aoa/issues/291, mockup specs/030-graph-history/mockup/index.html (screen Full graph), previous step specs/038-erd-diff. Branch already created: feature/issue-291-full-graph-comparison."

## Context: what is true today, checked on 2026-10-31

- **Diff exists, on the ERD only** (#290, spec 038). The picker, the two handles, the address bar, the room, the messages and the left panel all work in Diff. On the full graph the same mode shows version B as in One, and the button names the range without counts (spec 038, Assumptions). This step ends that.
- **The server already compares.** One read gives the status of every changed element and the counts, per kind; a second gives one element's differences. An element it leaves out is unchanged. A pair is compared by the protocol's `id`, never by position (spec 038, FR-002, FR-003).
- **The real counts of the release this issue names** are written in `specs/030-graph-history/pr-faq.ru_draft.md`: gameoffer 0.8.0 → 0.9.0 is nodes +23 −1 ~5, edges +34 −1 ~9.
- **The full graph's edges carry no protocol `id`.** The full graph's answer numbers them by position (`e-0`, `e-1`, …), so the same edge has different numbers in two versions, and it cannot be matched to the comparison as it stands.
- **The full graph leaves out generalization edges** (`full_graph_action.py`); they remain in the graph and in the comparison.
- **The layout is proven the same on every engine for one graph**: a golden hash on a frozen reference, and the cross-engine check (`check-layout-determinism.ts`) in the check run, over the graphs it opens. A union of two versions is not one of them yet.
- **The remembered arrangement** is keyed by a fingerprint of node ids and types, edges and layout settings, and holds twenty entries; a union has its own fingerprint without any change to the store.
- **The full graph has no filters.** The issue says "the node-type and domain filters work together with the comparison", but its node-type panel is a read-only legend, its domains are coloured hulls, and the mockup's screen shows neither filter. The filter panel exists on the ERD only. The maintainer decided on 2026-10-31 that this step builds the panel (User Story 4); the issue's three phases do not list it yet.

## Clarifications

### Session 2026-10-31

- Q: Does the gameoffer criterion (+23 −1 ~5) stay a condition of being done? → A: Being done is accepted on `erd-full`; the maintainer checks gameoffer's numbers on the real stand after the merge.

- Q: Does the full graph's filter panel carry the ERD's Changes section? → A: Yes: in Diff only, a third section, as on the ERD.
- Q: What does the domain filter do with nodes in no domain? → A: Nothing: they stay on the picture; only the node-type filter (or the Changes filter) can hide them. A node in several domains leaves when all of them are off.

## The acceptance stand

The maintainer's decision (2026-10-31): this step is accepted on the same local demo stand as #290, the history `erd-full` in `.demo-history/` (out of git), and that stand is extended for it through its builder, `.demo-history/build_erd_full.py`.

Today its twelve versions and Live change only entities, their fields, relations and lifecycles, all in the Inventory domain. For this step it MUST also hold: changes in several domains; a changed, an added and a removed node of other kinds (an action at least); a domain found only in A and one found only in B; a changed generalization edge; and a pair of versions with nothing drawn changed. Each User Story and each Edge Case that can be seen in the browser is walked on this stand.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See what a release changed across the whole graph (Priority: P1)

With A = 0.8.0 and B = 0.9.0, the developer opens the full graph. It shows both versions at once: new nodes ringed green, changed ones ringed amber, a removed one as a dashed red circle, the edges following, everything else faded. The version button counts the changes.

**Why this priority**: This is the whole step: the only picture of a release that crosses every domain and every kind of element.

**Independent Test**: Open gameoffer's history, A = 0.8.0, B = 0.9.0, the full graph; check every mark against the comparison and the button against the release's counts.

**Acceptance Scenarios**:

1. **Given** A and B, **When** the full graph is shown, **Then** it draws every node and edge of either version: added nodes with a green ring, changed with an amber ring, removed as a dashed red circle, unchanged faded.
2. **Given** an edge that was added, removed or changed, **When** shown, **Then** it takes that status's colour (a removed one dashed), whatever its two nodes' marks; an unchanged edge fades, also between two marked nodes.
3. **Given** gameoffer's 0.8.0 → 0.9.0, **When** the version button is read, **Then** it says `◷ A 0.8.0 → B 0.9.0  +23 −1 ~5 ▾`.
4. **Given** a relation whose field now points at another entity, **When** shown, **Then** it is one amber edge: solid to its target in B, thin and dashed to its target in A; never a red edge plus a green one (spec 038, FR-024).
5. **Given** two versions whose drawn nodes and edges do not differ, **When** shown, **Then** the button says "no changes" and the graph is drawn as in One, nothing faded.
6. **Given** B is Live, **When** the live graph changes, **Then** the comparison, the layout, the marks and the counts follow without a reload.
7. **Given** Diff → One, **When** the switch is made, **Then** the graph is version B again, in its own layout, unmarked.

---

### User Story 2 - The same picture for everyone (Priority: P1)

Two developers, or a room, open the same pair on different browsers and screens and see every node in the same place, as the full graph has promised since #271; coming back to the pair does not lay it out again.

**Why this priority**: A room that talks about "the green cluster on the right" needs one picture, and the union of a large graph is the slowest thing this step draws.

**Independent Test**: Run the cross-engine check over a union of two versions; open a pair twice in one browser and see the second time skip the layout; swap the order the two versions arrive in.

**Acceptance Scenarios**:

1. **Given** one pair A, B, **When** its union is laid out in Chromium, Firefox and WebKit at both sizes, **Then** every node has the same position.
2. **Given** the union, **When** its nodes are ordered, **Then** the order is the full graph's own: lower-case type, lower-case label, id.
3. **Given** a pair laid out once, **When** it is opened again in that browser, **Then** its remembered arrangement is used and no layout runs.
4. **Given** a pair and a single version, **When** both have been opened, **Then** each has its own remembered arrangement and neither overwrites the other.
5. **Given** a room in Diff on the full graph, **When** a participant follows another, **Then** the pan follows as in One and both see the same picture.

---

### User Story 3 - Read what exactly changed (Priority: P2)

The developer clicks a marked node and the card opens: the same card as on the ERD.

**Why this priority**: The rings say *that* something changed; the card says *what*.

**Independent Test**: Click a changed, an added, a removed and an unchanged node; compare the card with the comparison's differences.

**Acceptance Scenarios**:

1. **Given** a changed node, **When** it is clicked, **Then** a card lists every changed property by its path, with its value in A and in B.
2. **Given** an added or a removed node, **When** it is clicked, **Then** its card says it was added or removed in B.
3. **Given** an unchanged node, **When** it is clicked, **Then** it behaves as in One.
4. **Given** an open card, **When** the user clicks outside or presses Escape, **Then** it closes; **When** B is Live and the element is no longer changed, **Then** it closes by itself.

---

### User Story 4 - Narrow the comparison with filters (Priority: P2)

The developer switches off a node type or a domain, in Diff as in One: those nodes leave the picture, the rest stay exactly where they were, and the button counts what is left.

**Why this priority**: A release's changes in a 3 000-node graph are easier to read one domain at a time; the issue asks for it, and the ERD already works this way.

**Independent Test**: In One and in Diff, switch a node type and a domain off and on; compare positions before and after; read the button; reload the address; do the same in a room.

**Acceptance Scenarios**:

1. **Given** the full graph in One or in Diff, **When** it is shown, **Then** a filter panel like the ERD's lists the node types and the domains, one section open at a time, everything on.
2. **Given** a node type or a domain switched off, **When** the graph is drawn, **Then** those nodes and every edge touching them are gone and every remaining node keeps its position.
3. **Given** Diff with a filter on, **When** the button is read, **Then** it counts the drawn nodes only; everything on gives the whole graph's counts (+23 −1 ~5 on gameoffer).
4. **Given** Diff with a filter that leaves no change on the picture, **When** shown, **Then** the button says "no changes" and nothing fades.
5. **Given** Diff, **When** the panel is read, **Then** it lists the types and domains of the union, a domain found only in A included.
6. **Given** a filter set, **When** the address is reloaded or opened by a colleague, **Then** the same filters apply; **When** a participant changes one in a room, **Then** everyone follows, as on the ERD.

### Edge Cases

- **A domain only in A or only in B** — its hull is drawn, over its union members; its members carry their marks.
- **A node that changed only in its links** — not marked: a node's mark is its own status in the comparison; its edges carry theirs. The button's ~5 counts exactly this.
- **A changed generalization edge** — not drawn on the full graph, so not marked; it is not in the button's count, which counts nodes.
- **A node's label, type or colour differing between A and B** — the node is drawn as in B; the card tells the difference.
- **A node removed, with its edges** — the edges are drawn and marked removed; the layout places it among the union like any node.
- **A `1.0` graph as A or B** — its edges are matched by the id the comparison computes for them (spec 038, FR-006).
- **A `1.0` graph whose edge id cannot be computed, or whose computed ids collide** — Diff shows the comparison's refusal, as on the ERD; in One the full graph still opens as it does today, such an edge keeping a positional id.
- **A filter hiding the node of an open card** — the card closes.
- **A filter naming a type, domain or change the current pair does not have** — it has no effect and stays in the setting, so it applies again on a pair that has it.
- **A graph refused as not comparable, a refused version, Live unreachable** — as on the ERD (spec 038, Edge Cases).
- **The union's layout still running** — the same waiting state as One, and no marks or counts until the positions are there.
- **Switching A or B while a layout runs** — the running layout's result is dropped; only the current pair is drawn.
- **Twenty pairs remembered** — the least recently used is dropped, as for single graphs.
- **No secure origin or no IndexedDB** — nothing is remembered, and the layout runs each time, as in One.
- **Hover** — the existing hover labels and neighbour glow work in Diff; hovering a faded node brightens it as in One.

## Requirements *(mandatory)*

### Functional Requirements

**The union**

- **FR-001**: In Diff the full graph MUST draw the union of A and B: every node and every drawn edge of either version, each once, matched by the protocol's `id`, never by position.
- **FR-002**: The union's nodes MUST be in the full graph's order (lower-case type, lower-case label, id), and its edges in one defined order, so that a pair has one input to the layout whatever way it was built.
- **FR-003**: The union MUST be laid out by the full graph's own rules and settings; no second layout may exist for it.
- **FR-004**: A union MUST have its own remembered arrangement, under the existing fingerprint and bound, with no change to how arrangements are stored; a single version's arrangement MUST stay intact.
- **FR-005**: A node or edge in both versions MUST be drawn with B's label, type and colour.
- **FR-006**: Generalization edges MUST stay out of the union, as out of the full graph in One.

**The marks**

- **FR-007**: An added node MUST have a green ring, a changed node an amber ring, a removed node a dashed red circle; every unchanged node MUST fade. Each mark's status MUST also be readable in the node's hover label as `+`, `−` or `~`, so that colour is not the only signal; on a touch screen, which has no hover, the card opened by a tap says it.
- **FR-008**: An edge MUST carry its own status from the comparison: green added, amber changed, red and dashed removed, faded unchanged. It MUST NOT inherit a status from its nodes.
- **FR-009**: A relation retargeted between A and B MUST be one amber edge: solid to its target in B, thin and dashed to its target in A.
- **FR-010**: A node's mark MUST be that node's status in the comparison, with nothing propagated from its edges or neighbours: the full graph draws the parts, so it marks the parts.
- **FR-011**: Marks, fading, domain hulls, hover, pan and zoom MUST work together, and in a room as in One.

**The counts**

- **FR-012**: The version button MUST read `◷ A <name of A> → B <name of B>  +<added> −<removed> ~<changed> ▾`, the counts being the drawn nodes' (Assumptions); gameoffer 0.8.0 → 0.9.0 MUST read +23 −1 ~5.
- **FR-013**: When no drawn node or edge changed, the button MUST say "no changes" and the graph MUST be drawn as in One, nothing faded. When only edges changed, the button MUST read `+0 −0 ~0` and the edges MUST be marked: the counts are nodes', and "no changes" would be false.
- **FR-014**: When B is Live and the live graph changes, the union, its layout, the marks and the counts MUST follow without a reload.

**The card**

- **FR-015**: A click on a marked node MUST open the card spec 038 defines (FR-028, FR-029): every property that changed with both values, or that it was added or removed in B. A click on an unchanged node MUST behave as in One.

**Filters**

- **FR-016**: The full graph MUST have a filter panel with the ERD's chrome and accordion behaviour, with two sections, node types and domains, in One and in Diff; in Diff it MUST list the union's types and domains and add a third section, Changes, as on the ERD. It replaces the read-only node-type legend.
- **FR-016a**: A switched-off type, domain or change MUST hide its nodes and every edge touching them, and MUST NOT move any other node or run the layout: the layout's input stays the whole graph or union.
- **FR-016b**: The domain filter MUST NOT hide a node that belongs to no domain; a node in several domains MUST be hidden only when all of them are off.
- **FR-016c**: In Diff the counts, "no changes" and the fading MUST be those of the nodes and edges still drawn.
- **FR-016d**: The filters MUST be carried by the address and shared by a room, as the ERD's are.

**The tail**

- **FR-017**: The cross-engine check MUST cover a union of two versions, in the check run.
- **FR-018**: The change MUST end with the check run taken to zero, then the documentation — every case above, as a runnable script and a notebook — with the page's Russian draft beside it, then the changelog, one article (Principle VI).

### Key Entities

- **Union**: every node and drawn edge of A and B, each once, in the full graph's order; the input of one layout.
- **Mark**: what a drawn element shows of its status in the comparison.
- **Remembered arrangement**: a graph's positions in this browser, under its fingerprint; a union is one more graph to it.
- **Diagram counts**: on the full graph, the drawn nodes in each status.
- **Filter set**: the node types and domains switched off; carried by the address and, in a room, by the room.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every pair walked on the acceptance stand, the button's counts equal the comparison's node counts and the graph's marks of each kind; after the merge, on the real stand, gameoffer's 0.8.0 → 0.9.0 reads +23 −1 ~5 (issue, criterion 1).
- **SC-002**: The union's positions are identical in Chromium, Firefox and WebKit, at both sizes of the cross-engine check (issue, criterion 2).
- **SC-003**: Every marked edge's status equals the comparison's status for its id, in 100 % of a test's edges, a retargeted relation included.
- **SC-004**: Opening a pair the second time in one browser runs no layout.
- **SC-005**: The card of a changed node lists 100 % of its changed properties, each with both values.
- **SC-006**: Two versions with nothing changed say "no changes" and fade nothing.
- **SC-007**: With B on Live, a change of the live graph shows on the open full graph within the freshness check (30 seconds), with no reload.
- **SC-008**: Switching any filter moves 0 nodes, and the button's counts equal the drawn marks of each kind.
- **SC-009**: The check run passes, every step.

## Assumptions

- **The button counts nodes only.** The issue names nodes +23 −1 ~5; the release's edges (+34 −1 ~9) are drawn and marked, not counted. A full graph has no row-and-line double counting to resolve, so it does not need the ERD's rule.
- **Switching to Diff moves nodes.** A union is a different graph from either version, so its layout is its own; #271 promises the same picture for the same input, not the same position across inputs. This follows the issue.
- **The mockup's picture is a stand-in**; its marks and its counts are the reference, not its shape.
- **The panel filters, it does not paint**: the ERD's choice of what colours the diagram stays the ERD's; the full graph's nodes keep their type colours under the marks.
- **A card opens on nodes only**, as the issue says; an edge has its colour and no card in this step.
- **The domains' colours** in Diff are B's; a domain found only in A keeps its colour from A, so two domains may share a colour, as a palette that repeats already allows.
- **Phone**: the button and the sheet are spec 038's; the graph has nothing phone-specific, and a tap opens the card.
- **Side by side** stays greyed out (#294); use cases and lifecycles stay as they are (#292, #293).
- **gameoffer's history** is read from the stand's port, as in spec 038; the retargeted relation is not known to be in that release, so tests use a made-up graph for it.
- **Pictures** in the issue body are still to be added by the maintainer; the mockup is the reference.
