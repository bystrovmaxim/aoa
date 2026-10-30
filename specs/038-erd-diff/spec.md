# Feature Specification: Maxitor Compares Two Versions on the ERD

**Feature Branch**: `feature/issue-290-erd-diff`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "Issue #290 (Graph history 5/9): Maxitor compares two versions on the ERD. Source: https://github.com/bystrovmaxim/aoa/issues/290, mockup specs/030-graph-history/mockup/index.html, previous step specs/037-history-one-version. Branch already created: feature/issue-290-erd-diff."

## Context: what is true today, checked on 2026-10-30

- **Maxitor opens a history and shows one version** (#289, spec 037, merged into `main` as `a428e3a4`). The version button names the shown version; the picker has one track with one handle; the address bar carries `history`, `b` and the key after `#key=`; a room shares its version. Each version's graph is built once and held like any graph.
- **The mode switch already has Diff and Side by side, greyed out** with the hint "comes later" (`VersionPicker.tsx`). This step turns Diff on; Side by side stays greyed out.
- **Nothing compares two graphs.** #287 (the comparison function) was closed on 2026-10-29 and moved into this issue's first phase. The protocol only says how: two revisions are compared by `id`, never by position; their difference is the elements added, removed and changed under the same `id` (Open Gnomon Protocol, §4).
- **Edge ids.** A graph of `1.1` gives every edge an `id`; a graph of `1.0` gives none. The rule (#285, spec 031) is `<source_id>|<type>|<target_id>`, except `entity_relation` (`<source_id>|entity_relation|<field_name>`, so a relation whose target changes keeps its id) and `lifecycle_transition` (the default plus `|<from_state>`). Today the rule lives in AOA (`aoa.action_machine.graph.edge_identity.edge_id`), which the comparison may not import (§1 of the issue: it knows nothing of AOA).
- **There is no `packages/maxitor/core/` folder yet.** Maxitor's layout by kind (the maintainer, 2026-10-29) reserves `core/` for code the app and the tools share; this step creates it with its first module.
- **A version's message** is its pull request's title and body, or its commit's message, shown as plain text with two kinds of links (spec 037, FR-028, FR-028a). The mockup's "merge commit message" was superseded by that decision; this step shows two such messages.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare two graphs anywhere (Priority: P1)

A tool, a test or Maxitor's server has two documents of the Open Gnomon Protocol — from a port, from a file, from `git show` — and asks what changed between them: which nodes and edges were added, removed or changed, and, for a changed one, exactly which properties, with both values.

**Why this priority**: Every comparison this step and the next ones draw stands on it, and it is useful alone: a CI job or a coding agent can compare two revisions with nothing but the standard library.

**Independent Test**: Compare small hand-written graphs covering every status, a retargeted relation, a nested property, a `1.0` graph against a `1.1` one, a rename and two equal graphs; compare two versions of the demo's graph and time it.

**Acceptance Scenarios**:

1. **Given** graphs A (older) and B (newer), **When** they are compared, **Then** every node and every edge of either graph gets exactly one status: added (in B only), removed (in A only), changed (in both, something differs) or unchanged.
2. **Given** an `entity_relation` whose field now points at another entity, **When** compared, **Then** the edge is changed — one element, not a removal and an addition — and its difference names `target_id` with both values.
3. **Given** a node whose nested property changed (one field inside a `json_schema`), **When** compared, **Then** the difference names the full property path down to that field, with both values; a nested key that appeared or disappeared is named as added or removed.
4. **Given** a `1.0` graph and a `1.1` graph of the same model, **When** compared, **Then** the `1.0` graph's edge ids are computed by #285's rule, and an unchanged edge is unchanged.
5. **Given** a node renamed (a new `id`), **When** compared, **Then** it shows as one removal and one addition.
6. **Given** two equal graphs, **When** compared, **Then** every element is unchanged and every count is zero.
7. **Given** two edges between the same two nodes with different types, **When** compared, **Then** each gets its own status.
8. **Given** two versions of the demo's graph (3 213 nodes), **When** compared, **Then** the comparison finishes within the bound its test fixes.

---

### User Story 2 - Pick two versions (Priority: P1)

In an open history the developer switches the picker from One to Diff. The track now holds a range: two handles, A and B, the stretch between them dark. They drag either handle anywhere — past the other one too — and the left handle is always A, the older, the right one B, the newer.

**Why this priority**: Without a range there is nothing to compare.

**Independent Test**: In a history of 12 versions and Live, switch to Diff, drag each handle past the other, drop one on the other's point, use the keyboard with and without Shift, open a link that names the two the other way round.

**Acceptance Scenarios**:

1. **Given** One on version V, **When** Diff is chosen, **Then** B is V and A is the version before it; on the oldest version, B moves to the next one and A takes the oldest.
2. **Given** Diff, **When** a handle is dragged past the other, **Then** they swap roles as it passes: the left one is A, the right one B, and the dark stretch follows.
3. **Given** Diff, **When** a handle is dropped on the other's point, **Then** it goes to the next point in the direction it was moving; the two never stand on one version.
4. **Given** Diff with Live on the track, **When** a handle is moved onto Live, **Then** Live is B; Live is never A.
5. **Given** a focused handle, **When** ← or → is pressed, **Then** it steps, past the other handle too, the roles swapping as it passes, and focus stays on the handle moved; **When** Shift + ← → is pressed, **Then** both handles move together, keeping the distance, and stop at the ends.
6. **Given** Diff, **When** the address bar is read, **Then** it carries `mode=diff`, `a` and `b`; **When** a link with `a` newer than `b` is opened, **Then** the two open swapped.
7. **Given** a room in Diff, **When** a participant moves a handle or switches the mode, **Then** every participant moves with it, as with a room's version.

---

### User Story 3 - See what changed on the ERD (Priority: P1)

With A = 0.8.0 and B = 0.9.0, the ERD of the offers domain shows both versions at once: new tables and fields green, removed red with a dashed outline, changed amber, the rest faded. The version button counts them. A field that now points at another table is one amber link, drawn solid to where it points now and thin and dashed to where it pointed before.

**Why this priority**: This is what the developer came for: what a release changed in the data model, at a glance.

**Independent Test**: Open gameoffer's history, A = 0.8.0, B = 0.9.0, the offers domain's ERD; check every mark against the comparison of the two graphs; open a domain where nothing changed.

**Acceptance Scenarios**:

1. **Given** A and B, **When** the ERD is shown, **Then** it draws the union of A and B: added green, removed red with a dashed outline, changed amber, unchanged faded; rows (fields) get the same marks.
2. **Given** gameoffer's 0.8.0 → 0.9.0 and the offers domain, **When** shown, **Then** the two new tables, the new fields and links, `is_activated` removed and `OfferRequestItemDetailEntity` changed are marked, and the button counts them.
3. **Given** the shown diagram, **When** the version button is read, **Then** it says `◷ A 0.8.0 → B 0.9.0  +15 −1 ~3 ▾` with this diagram's counts, and there is no separate legend.
4. **Given** a field whose type changed, **When** its row is shown, **Then** it is amber and, when it fits, reads `~~str~~ → str | None`.
5. **Given** a relation whose field now points at another entity, **When** shown, **Then** it is one amber link: solid to its target in B, thin and dashed to its target in A; never a red link plus a green one.
6. **Given** a relation whose field is gone, **When** shown, **Then** the link is red; a relation whose field is new is green.
7. **Given** a diagram where nothing changed (another domain changed, or changes cancelled out between far-apart versions), **When** shown, **Then** the button says "no changes" and the diagram is drawn normally, nothing faded.
8. **Given** B is Live, **When** the live graph changes, **Then** the comparison is computed again and the marks and counts follow without a reload.

---

### User Story 4 - Read what exactly changed (Priority: P2)

The developer clicks an amber field or table and a card opens listing every property that changed, before and after.

**Why this priority**: The marks say *that* something changed; the card says *what*, which the colour alone cannot.

**Independent Test**: Click a changed field, a changed table, an added and a removed element; compare the card with the comparison's differences.

**Acceptance Scenarios**:

1. **Given** a changed field, **When** it is clicked, **Then** a card lists every changed property by its path, with its value in A and in B.
2. **Given** a changed table, **When** it is clicked, **Then** its card lists the table's own changed properties.
3. **Given** an added or a removed element, **When** it is clicked, **Then** its card says it was added in B or removed in B.
4. **Given** an unchanged element, **When** it is clicked, **Then** it behaves as in One.

---

### User Story 5 - Read why both versions exist (Priority: P2)

Under the track, A's message stands on the left and B's on the right; below them one line, "N versions between", opens the messages of the versions in between.

**Why this priority**: The two messages explain the two ends; the versions between explain how one became the other.

**Independent Test**: Pick two versions with long messages and several versions between; open the list; open one row.

**Acceptance Scenarios**:

1. **Given** Diff, **When** the picker is open, **Then** A's message is on the left and B's on the right, each stopping at about nine lines and scrolling on its own, both always shown.
2. **Given** versions between A and B, **When** the line "N versions between" is clicked, **Then** they open newest first; a closed row previews its message's first line; a click opens the whole message.
3. **Given** A and B adjacent, **When** the picker is open, **Then** there is no "versions between" line.
4. **Given** B is Live, **When** the picker is open, **Then** B's side has no message and says when Live was last checked, as in One.
5. **Given** a phone, **When** the sheet is open, **Then** the two messages stand one under the other.

---

### User Story 6 - Open a page that exists in only one version (Priority: P2)

A domain added in B, or removed in B, is still reachable: the left panel lists what exists in either version and marks each such page `+` or `−`; on it everything is green or red.

**Why this priority**: Without it the most important change of a release — a whole new domain — could not be opened at all.

**Independent Test**: Compare two versions where a domain was added and another removed; open each from the left panel.

**Acceptance Scenarios**:

1. **Given** Diff, **When** the left panel is shown, **Then** it lists the pages of A and of B together and marks a page found only in B with `+` and only in A with `−`.
2. **Given** a page only in B, **When** it is opened, **Then** everything on it is green; only in A, everything is red.
3. **Given** One again, **When** the left panel is shown, **Then** it lists only the shown version's pages, unmarked.

---

### User Story 7 - Diff on a phone (Priority: P3)

On a phone the version button sits in the phone bar with the counts; the sheet holds the mode switch, the range and the two messages.

**Why this priority**: Maxitor works on a phone; Diff must not break it, but the desktop comes first.

**Independent Test**: Open a history at a phone's width; switch to Diff in the sheet; move both handles by touch.

**Acceptance Scenarios**:

1. **Given** a phone's width in Diff, **When** the phone bar is shown, **Then** the version button carries A, B and the counts, shortened to fit.
2. **Given** the sheet, **When** it is open, **Then** it holds the switch, the range and the messages one under the other; each handle is a touch target of at least 44 px.

### Edge Cases

- **A history of one version without Live (M3) or no version (M6, M7)** — there are not two points: Diff is shown greyed out with the hint "needs two versions".
- **One version and Live (M5)** — A is the version, B is Live; neither can move.
- **Live unreachable while B is Live** — the diagram shows Live's unreachable state, as in One, with no marks and no counts.
- **A refused version as A or B** — the comparison is not drawn; the workspace says which end is refused and why, as in One.
- **A or B disappears from the list** — the end that disappeared moves to its neighbour in the direction of the other handle (A to the next newer, B to the next older); if that would put both on one point, Diff moves to One on the remaining version; the user is told, as in One.
- **A link naming the same version as `a` and `b`** — opens in One on that version.
- **A link naming `a=live`** — Live is never A: the two are swapped when `b` is a version; when `b` is also Live, it opens in One on Live.
- **A link naming a version the history lacks** — that end falls back as in One; the rules above then apply.
- **Switching Diff → One** — keeps B as the version.
- **Two edges of one `1.0` graph get the same computed id** — the graph is refused as not comparable, with both edges named; a `1.1` graph cannot have it (the build refuses it).
- **An edge of a `1.0` graph lacks the property its type's rule needs** — the graph is refused as not comparable, naming the type and the property.
- **A property's value is a list** — the list is compared as a whole value; its path names the property, not an item.
- **A changed element that the ERD does not draw** (an action's change in the offers domain) — not counted on the ERD; the next steps' diagrams count it.
- **A table that only moved to another domain** — on each domain's ERD it is, by the page's own union, added on one and removed on the other, and changed (its domain link) in the card.
- **The comparison of a very large graph** — the comparison on the server is computed once per pair A, B and held while either is held; a second reader does not compute it again.
- **Live changes while a card is open** — the card follows the new comparison; when its element is no longer changed, it closes.

## Requirements *(mandatory)*

### Functional Requirements

**The comparison of two graphs**

- **FR-001**: Maxitor MUST have a module that compares two graph documents of the Open Gnomon Protocol, `compare(a, b)`, A the older and B the newer, in Maxitor's shared core; it MUST need nothing beyond the standard library and MUST NOT import AOA, Maxitor's app or any tool, and the repository's boundary check MUST enforce it.
- **FR-002**: `compare` MUST give every node and every edge of A and B exactly one status, matched by `id`: added (in B only), removed (in A only), changed (in both and anything differs), unchanged.
- **FR-003**: An element MUST be changed when its `label`, `type`, `relationship`, `is_dag`, any property, or, for an edge, its `source_id` or `target_id` differs. Position in its array MUST NOT matter.
- **FR-004**: For a changed element `compare` MUST give every difference by its property path — nested objects included, down to the leaf that differs — each one added, removed or changed, with the value in A and the value in B. A list MUST be compared as one value.
- **FR-005**: `compare` MUST give the counts: added, removed and changed, for nodes and edges.
- **FR-006**: A `1.0` graph MUST be compared too: its edge ids MUST be computed by #285's rule, which the module MUST carry itself (not import from AOA), and the same rule MUST give the same id as AOA's `edge_id` for every edge of the demo's graph. A graph whose computed edge ids collide, or whose edge lacks its rule's property, MUST be refused naming the edges, or the type and the property.
- **FR-007**: A rename MUST be a removal plus an addition: identity is the `id`.
- **FR-008**: Two versions of the demo's graph MUST be compared within a bound fixed by a test.

**Picking two versions**

- **FR-009**: In Diff the switch MUST be on Diff, and the track MUST hold a range: two handles, A always the older and B the newer, the stretch between them dark. Side by side MUST stay greyed out with "comes later".
- **FR-010**: Roles MUST follow position, not the handle: the left handle MUST be A and the right one B; either MAY be dragged past the other, and they MUST swap roles as it passes.
- **FR-011**: The two handles MUST never stand on one version: dropped on the other's point, a handle MUST go to the next point in the direction it was moving. Live MUST only ever be B.
- **FR-012**: ← and → MUST move the focused handle, past the other one too, swapping roles as it passes, focus staying on the moved handle; Shift + ← → MUST move both handles together, keeping the distance, and do nothing when either would leave the track; Home and End MUST move the focused handle to the ends, by the same rules.
- **FR-013**: Switching One → Diff MUST keep the version as B and put A on the one before it (on the oldest version: B to the next one, A on the oldest); Diff → One MUST keep B.
- **FR-014**: The address bar MUST carry `mode` (`diff`; absent in One), `a` and `b` in the form of spec 037 (FR-022) next to `history` and the key; opening such an address MUST restore them; a link naming them the other way round MUST open with the two swapped; the edge cases decide the rest.
- **FR-015**: Diff MUST be offered only when the history has two points to pick (M2, M4, M5); otherwise it MUST be greyed out with the hint "needs two versions".
- **FR-016**: Inside a room, the mode, A and B MUST belong to the room like its version (spec 037, FR-022a): any participant's change MUST move everyone, the last change winning; the room link MUST carry them; a participant who joins MUST get the room's current ones. A change that breaks a rule above MUST be refused to the participant who made it and MUST NOT move the room.
- **FR-017**: The picker MUST open with B in view, and A too when both fit; dragging a handle to an edge of a long track MUST scroll it along; a handle out of view MUST be pinned to its edge, as in One.

**The comparison on the server**

- **FR-018**: The comparison MUST be computed on Maxitor's server by AOA actions, from the two held versions, with `compare` (FR-001); any endpoint for it MUST be an action (house rule: API only through actions).
- **FR-019**: One read MUST give the status of every element of the union of A and B and the counts; a second read MUST give one element's differences by property path.
- **FR-020**: The comparison MUST be computed once per pair and held while both versions are held, shared by every reader; when B is Live and the live graph changes, it MUST be computed again and the open pages MUST follow without a reload.
- **FR-021**: The reads MUST obey every rule of spec 037 for keys and logs (FR-009, FR-010b, FR-011–FR-011e): a key travels only in a header, no log names a whole address or a key, a refused key is "not found".

**The ERD comparison**

- **FR-022**: In Diff the ERD MUST draw the union of A and B: added green, removed red with a dashed outline, changed amber, unchanged faded; rows (fields) MUST get the same marks; every mark MUST carry `+`, `−` or `~` as well as its colour, so that the colour is not the only signal.
- **FR-023**: A field MUST be changed when its type changes — shown in the row as `~~<type in A>~~ → <type in B>` when it fits, otherwise in its card alone — or when its relation points at another entity.
- **FR-024**: A relation whose field is still there but points at another entity MUST be one amber link: solid to its target in B, thin and dashed to its target in A. A link MUST be red only when its field is gone, and green only when its field is new.
- **FR-025**: The version button MUST read `◷ A <name of A> → B <name of B>  +<added> −<removed> ~<changed> ▾`, the counts being those of this diagram (Assumptions); there MUST be no separate legend.
- **FR-026**: When nothing on the shown diagram changed, the button MUST say "no changes" instead of the counts and the diagram MUST be drawn as in One, nothing faded.
- **FR-027**: The ERD's filters, layout mode and pan and zoom MUST work in Diff as in One.

**The card**

- **FR-028**: A click on a marked table or row MUST open its card: every property that changed, by its path, with its value in A and in B; for an added or removed element, that it was added or removed in B. Values MUST be shown as plain text.
- **FR-029**: The card MUST close by a click outside or Escape, and MUST follow a new comparison when B is Live (edge cases).

**The messages**

- **FR-030**: Under the track MUST stand A's message on the left and B's on the right — the sides of the track — always shown, each box stopping at about nine lines and scrolling on its own with a thin visible scrollbar, each rendered by spec 037's rules (FR-028, FR-028a); Live's side MUST carry its closing line (spec 037, FR-030) instead of a message.
- **FR-031**: Below them one line, "N versions between", MUST open the versions strictly between A and B, newest first; a closed row MUST preview its message's first line, and a click MUST open the whole message. With no version between, the line MUST be absent.

**Pages in one version only**

- **FR-032**: In Diff the left panel MUST list the pages of A and of B together and mark a page that exists only in B with `+` and only in A with `−`; opening such a page MUST show everything on it as added or removed.

**Phone**

- **FR-033**: On a phone the version button MUST sit in the phone bar with A, B and the counts, shortened to fit; the sheet MUST hold the switch, the range and the two messages one under the other; every handle and point MUST be a touch target of at least 44 px.

**The tail**

- **FR-034**: The change MUST end with the check run taken to zero, then the documentation — the comparison of two graphs shown as a runnable script and a notebook, and Diff on the ERD — with the page's Russian draft beside it, then the changelog, one article (Principle VI).

### Key Entities

- **Graph document**: one revision of a service's model in the Open Gnomon Protocol, `1.0` or `1.1`: nodes and edges, each with an `id` (computed for a `1.0` edge).
- **Comparison**: the result of comparing A with B: a status per element of their union, the differences of each changed element, and the counts.
- **Status**: added, removed, changed or unchanged — exactly one per element.
- **Difference**: one property path of a changed element, its kind (added, removed, changed) and its values in A and B.
- **Range**: the two picked versions, A the older and B the newer (Live only as B), with the mode; carried by the address bar and, in a room, by the room.
- **Diagram counts**: the added, removed and changed elements the shown diagram draws.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every test comparison, every element of A and B has exactly one status, and every nested difference is named by its full property path (issue, criterion 6).
- **SC-002**: Two versions of the demo's graph (3 213 nodes) compare in under 1 second on the machine that runs the check run.
- **SC-003**: The handles never stand on one version in any sequence of drags, drops and keys a test plays; dragging one past the other swaps A and B; a reversed link opens swapped (criterion 1).
- **SC-004**: On gameoffer's 0.8.0 → 0.9.0, the offers domain's ERD marks the two new tables, the new fields and links, `is_activated` removed and `OfferRequestItemDetailEntity` changed, and the button's counts equal the number of marks of each kind (criterion 2).
- **SC-005**: A relation retargeted between A and B is drawn as 1 amber link, never as a red and a green one (criterion 3).
- **SC-006**: The card of a changed field lists 100 % of its changed properties, each with both values (criterion 4).
- **SC-007**: A diagram where nothing changed says "no changes" and fades nothing (criterion 5).
- **SC-008**: With B on Live, a change of the live graph shows on the open ERD within the freshness check (30 seconds), with no reload.
- **SC-009**: A comparison asked for by a second reader is not computed again.
- **SC-010**: The check run passes, every step.

## Assumptions

- **The diagram's counts** are the graph elements the shown diagram draws — on the ERD, its tables, its rows (fields) and its links — counted once each by status; a field of a new table counts as added like the table. A changed element the diagram does not draw (an action) is not counted here; the next steps' diagrams count their own.
- **Rooms share Diff** like they share a version (FR-016), because #289 already made the version a room setting and a room whose participants saw different comparisons would break following. Side by side's own sharing rules are #294's.
- **gameoffer's history** is read from the stand's port (`https://repo-graph-port.aoa.run`); its versions 0.8.0 and 0.9.0 are what acceptance criterion 2 checks. The type change of `erid` and the retargeted `chosen_offer` are the mockup's illustrations, not real; tests use made-up graphs for them.
- **The edge-id rule** is copied into the comparison module (it cannot import AOA); a test keeps the two in step on the demo's graph.
- **Messages** follow spec 037 (title and body of the pull request, or the commit's message), not the mockup's merge commit message.
- **The full graph, use cases, lifecycles** in Diff are the next steps (#291–#293); in this step they show B as in One, with the button naming the range without counts.
- **Side by side** stays greyed out with "comes later" (#294).
- **Pictures** in the issue body are still to be added by the maintainer; the mockup is the reference.
