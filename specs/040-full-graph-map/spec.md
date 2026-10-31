# Feature Specification: Maxitor's Full Graph as a Map

**Feature Branch**: `feature/issue-319-full-graph-map`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Issue #319 (https://github.com/bystrovmaxim/aoa/issues/319): the full graph as a map, for graphs tens of times larger. It takes over every requirement of #291 (spec 039). The filter panel's paint switch comes to the full graph, and switching it opens that filter section and folds the others, on every diagram with the panel. Branch already created: feature/issue-319-full-graph-map."

## Context: what is true today, checked on 2026-10-31

- **The full graph is one picture of everything.** The browser receives every node and link, lays them out, and draws them with a graph engine. On the stand (`erd-full`, 3 213 nodes, 4 805 links): first opening 7.3 s with the page blocked for up to 4.6 s at a time, opening again 2.7 s, stalls of up to 170 ms on zoom and pan.
- **Maxitor is growing into a catalog of every service** (the maintainer, 2026-10-31), so the graph is expected to grow tens of times. At 30 times the size, the graph would be about 110 MB of JSON by a linear estimate: the browser could not even receive it.
- **The server is not today's bottleneck**: a held graph is read in 0.08 s, 172 kB gzipped, 3.7 MB of JSON. The page reads it four times where once would do.
- **What the browser can draw**: plain WebGL held 120 frames a second at 32 thousand dots and 48 thousand lines, and 12 frames a second at 321 thousand and 480 thousand. That was bare dots and lines at random positions, with no icons or labels.
- **What Graphviz can lay out**: `sfdp` with `overlap=scale` laid the stand's graph out in 0.53 s in WebAssembly, against 5.9 s for today's layout. Without `overlap=scale` the result is an unreadable blob.
- **#291 is on hold.** Its branch `feature/issue-291-full-graph-comparison` compares two versions on the full graph and adds a filter panel, but switching off a large node type freezes the page for about 25 s. It is not merged. This spec takes over its requirements (spec 039) and replaces one of its decisions: the browser no longer lays out the union of two versions.
- **Parts of that branch stay useful**: the protocol's id on every edge, the rules of the comparison, the panel's filters, the filters in the address, the stand's versions.
- **The gear shift.** On the ERD a switch at the foot of the filter panel chooses which section paints the diagram: Domains, Kinds or, in Diff, Changes. One's choice and Diff's are kept apart, a room shares them and the address carries them. Clicking it changes the colours only: the open section stays open. The full graph has no such switch.
- **The stand.** `erd-full` holds 15 versions and Live, with changes across several domains, a domain only in A and one only in B, a changed generalization, a pair where only a link changed, and a pair where nothing drawn changed.

## Clarifications

### Session 2026-10-31

- Q: Does this work build a level for services above domains? → A: No. It comes later, in another task; this work only must not rule it out.
- Q: Inside a domain that changed between versions, may old nodes shift? → A: Yes. A domain's layout depends only on its content, so a changed domain may rearrange itself; other domains stay in place, and Diff draws one picture at B's positions.
- Q: What paints the full graph when it opens in One? → A: Domains, as on the ERD; Diff starts with Changes.
- Q: What happens to what a hidden node contains? → A: It leaves the screen with its parent, and the outline is redrawn. A filter row with nothing left on screen for that reason dims, but stays on or off as it was: hiding by containment and switching a row are separate axes, and neither changes the other. A dimmed row says what keeps it hidden.
- Q: Must a filter show what it did to a domain? → A: Yes. Nodes stay where they are, but the domain's outline is redrawn around what is left, its name moves there, and it says how much is left.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the whole system at a glance (Priority: P1)

A developer opens the full graph of a large system. Instead of a dense tangle they see its domains as named areas, sized by what they hold, with bundled links between them. The picture is on screen at once and the page stays alive.

**Why this priority**: This is what makes a catalog-sized graph readable at all, and everything else stands on it.

**Independent Test**: Open the generated graph of about 100 000 nodes; time the first picture; count what the browser read; try to interact while it opens.

**Acceptance Scenarios**:

1. **Given** a graph of any size, **When** the full graph opens, **Then** it shows every domain as a named area whose size follows what it holds, and everything outside domains as one such area.
2. **Given** two domains linked by many links, **When** the overview is shown, **Then** they are joined by one bundle whose thickness follows the number of links, and hovering it says that number.
3. **Given** the generated graph, **When** the overview opens, **Then** it appears in under 1 second and the browser has read only the overview, not the graph.
4. **Given** the page opening, **When** the user pans or clicks, **Then** it answers: no step blocks the page for more than 100 ms.

---

### User Story 2 - Zoom in to see more, as on a map (Priority: P1)

The developer zooms toward a domain. Its entities and operations appear inside its area, then, closer, their fields and states. Nothing already on screen moves; things only appear. Zooming out folds them away again.

**Why this priority**: Without it the overview is a picture of boxes; with it the map reaches every element.

**Independent Test**: On the stand and on the generated graph, zoom from the overview to a single field and back; record each node's position at each step; measure frames and the time a domain takes to open.

**Acceptance Scenarios**:

1. **Given** the overview, **When** the user zooms in past the first threshold, **Then** the domains in view show their entities, operations, roles and resources.
2. **Given** that level, **When** the user zooms in past the second threshold, **Then** the fields, states and other parts appear.
3. **Given** any level, **When** the user zooms in or out, **Then** no element on screen moves relative to the others.
4. **Given** a domain not read yet, **When** it comes into view at a level that shows it, **Then** its detail appears in under 200 ms and its folded area stays on screen until then, never a blank.
5. **Given** the same zoom, **When** two people look at the same place, **Then** they see the same level.
6. **Given** a folded domain, **When** it is clicked, **Then** the map flies to it and unfolds it.
7. **Given** any level, **When** names would collide, **Then** the larger element keeps its name and the other's name waits for a closer zoom, and hovering any element shows its name.

---

### User Story 3 - See what changed, from any distance (Priority: P1)

With A = 0.12.0 and B = 0.13.0 the developer opens the full graph. From far away each domain says how much changed in it; closer, changed elements are ringed, removed ones are dashed red circles, and everything else fades. Nodes stand where they stand in B.

**Why this priority**: This is #291's goal, and a change hidden in a folded domain would be missed without it.

**Independent Test**: On the stand, walk every pair in the spec's "The acceptance stand"; check every mark and every count against the comparison, at every level.

**Acceptance Scenarios**:

1. **Given** a domain with changes inside, **When** it is folded, **Then** it shows `+3 −1 ~2` for its nodes and is not faded; a folded domain with no change fades.
2. **Given** a bundle holding a changed link, **When** folded, **Then** it is marked, and hovering it says how many links changed.
3. **Given** unfolded elements, **When** drawn, **Then** added nodes have a green ring, changed ones an amber ring, removed ones are dashed red circles, links carry their own status, and the rest fades (spec 039, FR-007, FR-008).
4. **Given** a relation that points elsewhere now, **When** drawn, **Then** it is one amber link: solid to its target in B, thin and dashed to its target in A.
5. **Given** a node in both versions, **When** One is switched to Diff, **Then** it stays where it was in B; a node only in A appears beside its old neighbours and pushes nothing aside.
6. **Given** a domain only in A or only in B, **When** the map is shown, **Then** it is an area of its own, marked removed or added.
7. **Given** A and B, **When** the version button is read, **Then** it counts every change drawn, nodes and links, under the filters, whatever the zoom; a link that changed reads as `~1`, never as zero; nothing drawn changed reads "no changes" and nothing fades (spec 039, FR-012, FR-013).
8. **Given** B is Live, **When** the live graph changes, **Then** the marks and counts follow without a reload, within the freshness check, and only the domains that changed are laid out again.
9. **Given** a folded domain with a count, **When** the count is clicked, **Then** the map flies to the first change in that domain, showing it marked with its card open.
10. **Given** Diff, **When** the arrows beside the version button are used, **Then** the map flies to the next or previous change and the control says which, such as `3 of 12`; after the last it returns to the first.
11. **Given** filters on, **When** stepping through changes, **Then** what the filters hide is skipped and the total counts only what is left.

---

### User Story 4 - The same speed at catalog size (Priority: P1)

The developer works with a graph 30 times today's size as they work with today's: panning, zooming, opening domains, switching filters. Nothing freezes.

**Why this priority**: The 25-second freeze is why #291 was not merged; speed is the reason this work exists.

**Independent Test**: Run the same scripted session on the stand and on the generated graph and compare the timings with the thresholds.

**Acceptance Scenarios**:

1. **Given** the generated graph, **When** the user zooms and pans for a minute, **Then** the picture holds 60 frames a second and no frame takes over 100 ms.
2. **Given** the generated graph, **When** a filter is switched, **Then** the picture follows in under 50 ms.
3. **Given** a long session across many domains, **When** the browser's memory fills, **Then** detail out of view is let go and read again when needed, with no visible difference.

---

### User Story 5 - A new version is simply there (Priority: P2)

A service publishes a new version. Everyone opening it sees its map, laid out once for all of them, with the domains that did not change exactly where they were.

**Why this priority**: The map is useless if its first reader waits, or if the picture reshuffles with every release.

**Independent Test**: Publish a version changing one domain; time its layout; compare positions outside that domain; open it from a second browser and from a second machine.

**Acceptance Scenarios**:

1. **Given** a new version of the generated graph, **When** it is first read, **Then** it is laid out in under 1 minute, and meanwhile the page says so and stays alive.
2. **Given** a version laid out once, **When** anyone opens it, **Then** no layout runs, and it stays so after Maxitor restarts.
3. **Given** two versions differing in one domain, **When** both are shown, **Then** every other domain's elements stand in exactly the same places.
4. **Given** one version, **When** it is opened in Chromium, Firefox, WebKit and Safari, on any screen, **Then** every element has the same position.

---

### User Story 6 - Filter and paint (Priority: P2)

The developer switches off a node type or a domain, and chooses what colours the picture. The switch at the foot of the panel also opens the section it paints by, on the full graph and on every other diagram with this panel.

**Why this priority**: Filters are what #291 promised, and the same panel must behave the same everywhere.

**Independent Test**: On the full graph and on the ERD, in One and in Diff, switch the paint and read which section is open; switch filters; reload; do it in a room.

**Acceptance Scenarios**:

1. **Given** the full graph, **When** it is shown, **Then** the filter panel lists Domains and Node types, with Changes in Diff, one section open at a time, and the gear shift at its foot.
2. **Given** any diagram with this panel, **When** the gear shift is moved to a section, **Then** that section opens, the others fold, and the diagram is painted by it.
3. **Given** a section opened by hand, **When** it is opened, **Then** the paint does not change.
4. **Given** any diagram with this panel, **When** it opens, **Then** the open section is the one that paints.
5. **Given** a section that does not paint, **When** its rows are shown, **Then** their disks are grey, as on the ERD.
6. **Given** a type, domain or change switched off, **When** drawn, **Then** those elements and their links are gone, nothing else moves, and the button counts what is left (spec 039, FR-016a, FR-016b).
7. **Given** a filter that leaves no change, **When** Diff is shown, **Then** the button says "no changes" and nothing fades.
6a. **Given** Entity switched off, **When** drawn, **Then** every entity's fields leave the screen with it, the outlines close around what is left, and the EntityField row dims while staying on; **When** EntityField is switched off and on again meanwhile, **Then** Entity stays as it was.
6b. **Given** a dimmed row, **When** it is hovered or tapped, **Then** it says what keeps its nodes hidden, such as `Hidden: Entity is off`, and offers to switch that on; a row hidden by several says all of them.
7a. **Given** a filter that takes most of a domain away, **When** drawn, at any level, **Then** the domain's outline closes around what is left, its name stands there, and it reads `45 of 394 left`; switching the filter off brings the outline back.
8. **Given** filters and a paint choice, **When** the address is reloaded or opened by a colleague, **Then** they apply; **When** a participant changes one in a room, **Then** everyone follows.

---

### User Story 7 - Read one element (Priority: P2)

The developer clicks a marked node and reads what changed.

**Why this priority**: The rings say that something changed; the card says what.

**Independent Test**: Click a changed, an added, a removed and an unchanged node; compare the card with the comparison.

**Acceptance Scenarios**:

1. **Given** a changed node, **When** clicked, **Then** the card lists every changed property with both values.
2. **Given** an added or removed node, **When** clicked, **Then** the card says so.
3. **Given** an unchanged node, **When** clicked, **Then** it behaves as in One.
4. **Given** an open card, **When** its node is filtered away, or the user clicks outside or presses Escape, **Then** it closes.

---

### User Story 8 - Together and on a phone (Priority: P3)

A room looks at one map; someone following a colleague sees the same place at the same level. On a phone the map pans and pinches, and a tap reads a node.

**Why this priority**: Rooms and phones already work on every diagram; the new viewer must not lose them.

**Independent Test**: A room of two tabs in different browsers: move, zoom, filter, follow. A phone-sized screen: pinch, tap, open the Filter pill.

**Acceptance Scenarios**:

1. **Given** a room, **When** a participant is followed, **Then** the follower sees the same place and level, and the leader's hover and pointer.
2. **Given** a phone, **When** a marked node is tapped, **Then** its card opens, and the card says its status.
3. **Given** a phone, **When** the panel is shown, **Then** it starts as the Filter pill, as on the ERD.

### Edge Cases

- **A node in several domains** — it stands in one home domain, the first of them in the domains' order, and the filters count it in all of them.
- **A node in no domain** — it stands in the area outside domains; the domain filter does not hide it.
- **A domain with a few elements, or a huge one** — its area follows what it holds, with a floor so that its name stays readable.
- **A graph of one domain, or none** — the map opens one level closer: there is nothing to fold.
- **A graph of `1.0`** — it opens in One; its links are matched by the id the comparison computes. A graph the comparison refuses is refused in Diff, as on the ERD.
- **A version not laid out yet, opened by two people** — one layout runs; both wait for it.
- **Layout fails for one domain** — the rest of the map is shown, and that domain says it could not be drawn.
- **Live unreachable, a refused version** — as in spec 038.
- **A filter naming what the pair does not have** — no effect, and it stays in the setting.
- **A filter hiding the whole of a domain** — its area goes, and nothing moves.
- **What is left of a domain lies in separate places** — the outline is several shapes, under one name.
- **The chosen paint's section is not offered here** — the first section paints, as on the ERD; the open section follows.
- **A domain folded at the zoom a followed person sees unfolded** — cannot happen: the level follows the zoom.
- **A browser without WebGL, or with it switched off** — the page says so and offers the ERD, rather than a blank picture.
- **A generalization** — not drawn, so a change only in it reads "no changes" here and shows on the ERD (spec 039).
- **Switching A or B while a domain loads** — the old answer is dropped; only the current pair is drawn.

## Requirements *(mandatory)*

### Functional Requirements

**The map**

- **FR-001**: The full graph MUST be drawn as a map of three levels: domains; their entities, operations, roles and resources; their fields, states and other parts.
- **FR-002**: The level MUST depend on the zoom alone, the same for everyone at that zoom.
- **FR-003**: Changing the level MUST only reveal or fold elements: no element on screen may move relative to another.
- **FR-004**: A folded domain MUST be an area named by its domain, sized by what it holds, standing exactly where its elements stand when unfolded.
- **FR-005**: Links between folded areas MUST be bundled: one line per pair of areas, its thickness following the number of links, the number shown on hover.
- **FR-006**: Everything outside domains MUST stand in one area of its own, folded and unfolded like a domain.
- **FR-007**: A click on a folded domain MUST fly the map to it and unfold it.
- **FR-008**: Names MUST follow the level: when two would collide, the larger element keeps its name; hovering any element MUST show its name.
- **FR-009**: Hover MUST brighten an element and its neighbours, as today.
- **FR-009a**: The map MUST keep today's look: soft coloured domain areas with their name tags, nodes as disks with their type's icon, the hover label with its colour stripe, links with arrows, the dotted background. Revealing and folding MUST fade rather than pop. The maintainer MUST approve the look on the stand, beside today's picture, before the viewer is taken further.

**Reading in parts**

- **FR-010**: The browser MUST read an overview first and the detail of what it looks at; it MUST NOT need the whole graph at any zoom or filter.
- **FR-011**: A domain not read yet MUST keep its folded area on screen until its detail arrives.
- **FR-012**: Detail out of view MAY be let go and MUST be read again when needed, with no visible difference.
- **FR-013**: One opening MUST read each thing once.
- **FR-014**: Every read MUST be an AOA action and obey spec 037's rules for keys and logs.

**The layout**

- **FR-015**: A version MUST be laid out on the server, once, and shared by every reader; the result MUST survive a restart of Maxitor.
- **FR-016**: Each domain MUST be laid out on its own, from its content alone and not from any earlier version, so that a domain whose content did not change keeps every element's position in every version, and the domains' own places MUST change only as far as their sizes require. A domain whose content changed MAY rearrange itself.
- **FR-017**: The browser MUST NOT run a layout, so that one version has one picture in every browser and on every screen.
- **FR-018**: While a version is being laid out, the page MUST say so and stay alive; two readers MUST share one layout.
- **FR-019**: Live MUST be laid out the same way; only the domains that changed are laid out again.

**The comparison**

- **FR-020**: The comparison of two versions MUST run on the server, by AOA actions, using spec 038's comparison.
- **FR-021**: Nodes MUST stand where they stand in B. A node only in A MUST appear beside its neighbours in A, moving nothing; a domain only in A MUST stand in free space, moving nothing.
- **FR-022**: Unfolded elements MUST carry spec 039's marks (FR-007 – FR-010): green and amber rings, a dashed red circle, links with their own status, a retargeted relation as one link with a thin dashed line to its target in A, the rest faded; a mark's status MUST also be readable as `+`, `−` or `~` on hover, and in the card on a touch screen.
- **FR-023**: A folded domain MUST show the count of its changes by status, nodes and links, and MUST NOT fade when anything inside it changed; a domain in which neither a node nor a link changed MUST turn grey and dim at every level, as an unchanged table does on the ERD, so that the top level shows at once where nothing happened; a folded bundle holding a changed link MUST be marked, and say how many on hover.
- **FR-024**: The version button MUST read spec 039's `◷ A <name> → B <name>  +<added> −<removed> ~<changed> ▾`, counting every change the diagram marks, nodes and links, each once, under the filters, whatever the zoom, so that the counts add up to the control's total and a change is never read as zero. When nothing drawn changed it MUST say "no changes" and nothing MUST fade.
- **FR-025**: When B is Live and the live graph changes, the marks and counts MUST follow without a reload.
- **FR-025a**: A click on a folded domain's count MUST fly the map to that domain's first change, at the zoom that shows it, marked and with its card open.
- **FR-025b**: In Diff a control beside the version button MUST step through the changes, next and previous, saying the position and the total; it MUST be separate from the arrows that step versions, MUST wrap around, and MUST skip what the filters hide. The order MUST be stable: domains by size, largest first, then each domain's elements in the full graph's order.
- **FR-025g**: The steps and the list MUST hold every change the diagram marks, links as well as nodes: a domain whose only change is a link MUST be reachable, by its count and by the control. A step to a link MUST show both its ends and open its card.
- **FR-009b**: The mouse and the trackpad MUST move the map as they move every other diagram (spec 029, FR-053): a plain wheel or a two-finger swipe pans, Shift turning it sideways; a pinch or Ctrl / ⌘ with the wheel zooms around the pointer; a drag pans and stops where it is let go; a double click does not zoom.
- **FR-025d**: The control MUST be one control with the version button's look: the same height, fill, arrows and chevron. A click on its middle MUST open the list of the changes, grouped, each with its status, so that a change can be chosen directly; choosing one goes to it as a step does.
- **FR-025e**: The control and its list MUST be on every diagram that marks a comparison: the map and the ERD. On the ERD a step goes to the table, row or line, marks it and opens its card where it has one.
- **FR-025f**: In a room a follower MUST see the control as its person does: the position, the list open or closed and at the same scroll, the pointer over it on the same row, and the change marked with its card.
- **FR-025c**: Reaching a change MUST NOT depend on what the browser has loaded: the list of changes MUST come from the server, and a domain not read yet MUST be read on arrival.
- **FR-026**: A click on a marked node MUST open spec 038's card (FR-028, FR-029); an unchanged node MUST behave as in One; a card whose node is filtered away MUST close.

**The filter panel**

- **FR-027**: The full graph MUST have the ERD's filter panel with Domains and Node types, and Changes in Diff, in One and in Diff, listing what the graph or the pair holds.
- **FR-028**: A switched-off type, domain or change MUST hide its elements and their links, and move nothing. The domain filter MUST NOT hide a node in no domain, and MUST hide a node in several domains only when all of them are off.
- **FR-029**: Counts, "no changes" and fading MUST follow what the filters leave.
- **FR-028a**: A hidden node MUST take everything below it off the screen with it, at any depth: a domain its entities, actions and resources, an application its domains and roles, an entity its fields and lifecycle, a lifecycle its states, an action its aspects, params and result. A transition between states and a schema reference hold nothing. So switching off the type Domain leaves what is outside domains.
- **FR-028b**: A row whose nodes are all off the screen because of something else switched off MUST dim, and MUST keep its own state: switching it on or off MUST NOT change any other row, and switching another row MUST NOT change it. Those are two separate axes.
- **FR-028c**: A dimmed row MUST carry a quiet mark that opens a card in the look of the change card: what stands above it and is switched off, with an arrow from those to the row, and one button that switches them on. The card opens on hover and on a tap, and a follower in a room sees it. A dimmed row that is switched on but hidden, and a row switched off, MUST look different.
- **FR-029a**: At every level a domain's outline MUST be redrawn around what the filters leave, its name MUST stand with what is left, and it MUST read how much is left of how much, such as `45 of 394 left`. Nothing else may move. A bundle MUST follow too: its thickness counts the links left, and it goes when none is.
- **FR-030**: The full graph's panel MUST carry the gear shift: Domains, Node types and, in Diff, Changes paint the picture, the nodes of the map and the disks of the section. The full graph MUST start painted by Domains in One and by Changes in Diff. A section that does not paint MUST show grey disks. Rings keep their meaning under any paint.
- **FR-031**: On every diagram with this panel, moving the gear shift to a section MUST open that section and fold the others.
- **FR-032**: On every diagram with this panel, the section open when it first shows MUST be the one that paints. Opening a section by hand MUST NOT change the paint; folding it MUST NOT either.
- **FR-033**: Filters and paint MUST be carried by the address and shared by a room, One's paint and Diff's kept apart, as on the ERD.

**Rooms, phones, browsers**

- **FR-034**: Rooms MUST work on the map as on today's full graph: shared filters, following, pointers and hover.
- **FR-035**: On a phone, the map MUST pan and pinch, a tap MUST open a marked node's card, and the panel MUST start as the Filter pill.
- **FR-036**: A browser that cannot draw the map MUST say so and offer the ERD.

**The tail**

- **FR-037**: The change MUST end with the check run taken to zero, then the documentation — every case above, as a runnable script and a notebook — with the page's Russian draft beside it, then the changelog, one article (Principle VI).

### Key Entities

- **Level**: what the map shows at a zoom: domains; their entities and operations; their parts.
- **Area**: a domain, or everything outside domains, as a place on the map with a size.
- **Bundle**: all links between two folded areas, drawn as one.
- **Layout of a version**: every element's position; each domain's part depends only on that domain's content.
- **Overview**: what the browser reads first: areas, bundles, names, counts by type and status.
- **Comparison of a pair**: statuses and counts of A and B, whole and per area.
- **Paint**: which panel section colours the diagram; One's and Diff's kept apart.
- **Filter set**: the types, domains and changes switched off.

## The acceptance stand

The maintainer's decision: this work is accepted on the local stand of #290 and #291, the history `erd-full`, extended through `.demo-history/build_erd_full.py`, and on a **generated graph** of about 100 000 nodes and 150 000 links with realistic shape: many domains, entities with fields, lifecycles with states, links across domains.

Every User Story that can be seen in a browser is walked on the stand, and every threshold is measured on the generated graph.

If a threshold cannot be reached, the steps down are those of #319, §5.

## Success Criteria *(mandatory)*

### Measurable Outcomes

On the generated graph, in Chromium on the machine that runs the check run:

- **SC-001**: The overview appears in under 1 second, and the browser reads under 1 MB for it.
- **SC-002**: Zoom and pan hold 60 frames a second, and no frame takes over 100 ms.
- **SC-003**: Switching a filter takes under 50 ms.
- **SC-004**: A domain's detail appears in under 200 ms.
- **SC-005**: A new version is laid out in under 1 minute; opening it again runs no layout.
- **SC-006**: No step of opening blocks the page for over 100 ms.

On the stand:

- **SC-007**: Across zooming, filtering and switching One ↔ Diff, 0 nodes change position.
- **SC-008**: Between two versions differing in one domain, 0 elements of the other domains change position.
- **SC-017**: With a filter on, at every level, every domain's outline encloses what is left and reads the right numbers, on every filter walked on the stand.
- **SC-009**: Every status at every level, and every count, equals the comparison, on every pair walked.
- **SC-016**: Stepping from the first change to the last visits every change the filters leave, each exactly once, and the total equals the button's counts.
- **SC-010**: One version gives the same positions in Chromium, Firefox, WebKit and Safari.
- **SC-011**: On the full graph and on the ERD, moving the gear shift opens that section and folds the others, every time.
- **SC-012**: A room of two browsers stays on one picture through zoom, filters and following.
- **SC-013**: The check run passes, every step.
- **SC-015**: The maintainer, shown the map and today's full graph side by side on the stand, approves the look.

On a real phone, with the stand and with the generated graph:

- **SC-018**: The overview appears in under 2 seconds, pan and pinch hold 30 frames a second, and no frame takes over 200 ms.

After the merge, on the real stand, by the maintainer:

- **SC-014**: gameoffer's 0.8.0 → 0.9.0 reads `+23 −1 ~5`.

## Assumptions

- **Levels are three** for one service's graph. A level for services above domains comes later, in another task (Clarifications).
- **A node's home domain** is the first of its domains in the domains' order.
- **Thresholds of zoom** are fixed in the plan from the prototype.
- **What opens first** on the ERD changes with FR-032: in Diff, Changes is open, because Changes paints.
- **Search and "find on the map"** are out of scope, except stepping through changes.
- **Links in the step order**: stepping visits changed nodes. A pair where only links changed has nothing to step through in this work; the links are marked where they are.
- **Graphviz stays** the engine of the ERD, use cases and lifecycles; those diagrams do not change, except FR-031 and FR-032 on the ERD.
- **Spec 039 stays the record of the comparison's rules.** This spec replaces its FR-001 – FR-006 (the browser's union and layout) and its fixed panel without paint.
- **The branch of #291** stays unmerged; its parts are taken over as this work needs them. #291 closes when this lands.
- **The WebGL library** is chosen by the prototype in the plan.
- **Numbers at 30 times the size** in Context are linear estimates, not measurements.
- **Pictures** in the issue are to be added by the maintainer.
