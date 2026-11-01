# Feature Specification: Maxitor: One Card on Hover, and Tables That Collapse

**Feature Branch**: `feature/issue-320-283-field-card-and-collapse`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Issues #320 and #283 together, on one branch. Source: https://github.com/bystrovmaxim/aoa/issues/320 and https://github.com/bystrovmaxim/aoa/issues/283, whose nine questions are answered in the issue. One card on hover for every ERD field and table and everything on the full graph, with a lifecycle miniature; collapsing a table to its header and key rows. Accepted on the local stand erd-full in .demo-history."

## Context: what is true today, checked on 2026-11-01

- **A field has two hints.** A changed field in Diff has a white card, opened by a click. Every other field has a small text label: the name, or the type's full annotation. It looks like a browser tooltip but is Maxitor's own label, shown to the person and to a follower alike.
- **One click means two things.** A click on a name copies it, except on a changed row or table, where it opens the card.
- **The card is read when it opens**, property by property, and only in Diff. It closes by a click outside or by Escape. The change stepper opens it too, and a follower sees that card through the stepper.
- **A hover is already shared in a room:** what the followed person hovers is replayed for the follower.
- **What a field carries:** name, type, full annotation, primary key and foreign key flags, and in Diff its status and earlier type. It carries no description. A field has no mark saying it is a lifecycle, though a lifecycle's own id is built from its entity and field names.
- **The full graph** names an element on hover and gives a card only to a change, on a click. What the map holds for a node is its label, its type and its place: no description.
- **A table always shows all its fields** (#282).
- **The ERD's filters, layout and modes** live in the address and are shared in a room.
- **The check run** already requires three browser engines to draw the same layout.

## Clarifications

### Session 2026-11-01

Answers agreed with the maintainer and recorded in #283:

- Q: What does a collapsed table keep? → A: Its header and the rows that have a line: the primary key and the foreign keys.
- Q: What can be collapsed? → A: One table by a control on its header, and all tables from the toolbar. A specialization block is not collapsed for now.
- Q: Where do the lines go? → A: They stay on their rows, because those rows stay.
- Q: How does hover work on a collapsed table? → A: Key rows light their lines as today. A hover on the header shows the card, which lists all the fields.
- Q: Is collapsing shared in a room? → A: Yes, like filters.
- Q: Does it survive a reload? → A: Yes, it is kept in the address.
- Q: What is the default? → A: Everything expanded, including the tables 1-hop brings in.
- Q: May tables move? → A: Yes. The diagram is laid out again, and the same-layout check covers a collapsed state.
- Q: What about a comparison? → A: A changed row stays visible in a collapsed table.
- Q: How is a name copied on a phone, where a tap opens the card? → A: By a button in the card.
- Q: Which hints stay as they are? → A: The use-case and lifecycle diagrams keep their label, drawn white. ERD lines get the card: the maintainer found a line's ids of no use.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One card for every field (Priority: P1)

A person rests the pointer on any field of the ERD, or on a table's header, and a card appears with what that thing is. In a comparison the same card also says what it was and what it is now. A click now only copies a name.

**Why this priority**: It ends the two kinds of hint and the click with two meanings. Everything else in this work is built on this card.

**Independent Test**: On the stand, hover an unchanged field, a changed field and a header in One and in Diff; click each name and check the clipboard.

**Acceptance Scenarios**:

1. **Given** an unchanged field, **When** the pointer rests on it for about 300 ms, **Then** a card shows its name, its type and its description, and no text label appears.
2. **Given** a changed field in Diff, **When** the pointer rests on it, **Then** the card also shows each changed property, before and after.
3. **Given** the pointer crosses the diagram without stopping, **When** it passes over fields, **Then** no card appears.
4. **Given** an open card, **When** the pointer moves from the field onto the card, **Then** the card stays open, and it closes once the pointer has left both.
5. **Given** any field or header, changed or not, **When** its name is clicked, **Then** the name is copied and no card is opened by the click.
6. **Given** a phone, **When** a person taps a field, **Then** the card opens, and a button in it copies the name.
7. **Given** a room, **When** the followed person's card opens, **Then** the follower sees the same card in the same place on the diagram, and it closes when theirs does.
8. **Given** the change stepper, **When** it stands on a change, **Then** that change's card opens as it does today and stays until the step moves or it is closed.

---

### User Story 2 - A lifecycle in the card (Priority: P2)

A person hovers a field that is a lifecycle and sees a small picture of it in the card, without leaving the diagram. A click on the picture opens the full diagram. In a comparison, added and removed states carry their colours.

**Why this priority**: It is the reason the card is more than a tooltip, but it needs the card first.

**Independent Test**: On the stand, hover a lifecycle field in One and in Diff, watch what is read, click the miniature.

**Acceptance Scenarios**:

1. **Given** a lifecycle field, **When** its card opens, **Then** the whole lifecycle is shown fitted into the card, about 300 px wide.
2. **Given** a field that is not a lifecycle, **When** its card opens, **Then** no lifecycle is read and no miniature is shown.
3. **Given** a lifecycle field the pointer only crossed, **When** no card opened, **Then** nothing of the lifecycle is read.
4. **Given** a miniature seen once, **When** the same card opens again in the same version or pair, **Then** it appears with no new read.
5. **Given** a miniature, **When** it is clicked, **Then** the full diagram of that lifecycle opens in the same mode and versions.
6. **Given** Diff, **When** a lifecycle changed, **Then** added and removed states carry the colours and signs of the full diagram, and unchanged states are dim.
7. **Given** a lifecycle of 30 states, **When** its card opens, **Then** all of them are in the picture, with nothing cut off.

---

### User Story 3 - The same card on the full graph (Priority: P3)

A person hovers an element of the full graph and sees the same card: what the element is, its description, what changed in a comparison, and the miniature on a lifecycle.

**Why this priority**: It extends the one card to the second diagram that has only a name today.

**Independent Test**: On the stand's map, hover a node, a link, a lifecycle and a change; watch what is read.

**Acceptance Scenarios**:

1. **Given** a node on the map, **When** the pointer rests on it, **Then** the card says what kind of element it is, its name and its description.
2. **Given** a changed node or link in Diff, **When** the pointer rests on it, **Then** the card also says what changed.
3. **Given** a lifecycle node, **When** its card opens, **Then** it shows the miniature of User Story 2.
4. **Given** a folded domain or a bundle, **When** the pointer rests on it, **Then** it behaves as it does today.
5. **Given** a hover, **When** the card opens, **Then** what it shows was read for that one element at that moment, and nothing was read for elements merely crossed.

---

### User Story 4 - Collapse one table (Priority: P2)

On a big diagram a person wants to see how tables connect, not what is in each. They collapse a table to its header and key rows, and expand it again.

**Why this priority**: It is the point of #283, and the more important half of it: it works on the one table in the way.

**Independent Test**: On the stand, collapse tables of each shape, follow the lines, reload, and repeat in a room and in Diff.

**Acceptance Scenarios**:

1. **Given** an expanded table, **When** its header control is used, **Then** it shows the header and its key rows, and says how many fields are hidden.
2. **Given** a collapsed table, **When** the control is used again, **Then** every field is back.
3. **Given** a collapsed table, **When** the pointer rests on a key row, **Then** its lines and the tables they join light up as today.
4. **Given** a collapsed table, **When** the pointer rests on the header, **Then** the card lists all its fields, hidden ones included.
5. **Given** a collapsed table in Diff, **When** a non-key row changed, **Then** that row stays visible with its mark, and the stepper can stand on it.
6. **Given** a collapsed table, **When** the page is reloaded or the address is opened elsewhere, **Then** the same tables are collapsed.
7. **Given** a room, **When** one person collapses a table, **Then** everyone viewing that shared picture sees it collapsed.
8. **Given** a table is collapsed, **When** the diagram is laid out again, **Then** that table's header stays where it was on the screen.

---

### User Story 5 - Collapse all tables (Priority: P3)

A person collapses every table at once from the toolbar to read the shape of the diagram, and opens the few they care about.

**Why this priority**: It is a shortcut over User Story 4.

**Independent Test**: On the stand, collapse all, expand one, add a table by 1-hop, reload, expand all.

**Acceptance Scenarios**:

1. **Given** an expanded diagram, **When** the toolbar control is used, **Then** every table is collapsed and the control offers to expand all.
2. **Given** all collapsed, **When** one table is expanded, **Then** the rest stay collapsed.
3. **Given** all collapsed, **When** 1-hop or a filter brings a table in, **Then** it comes in collapsed.
4. **Given** all collapsed on a diagram of hundreds of tables, **When** the address is copied, **Then** it stays short.
5. **Given** any collapse state, **When** three browser engines draw it, **Then** the layout is the same in all three.

---

### Edge Cases

- **A field with no description**, such as an implicit `id` the model never declared: the card leaves that line out; it never says "no description".
- **A graph built before descriptions existed**: the same; nothing fails.
- **The card's read fails**: the card still shows what the diagram already knows, name and type, and says the rest could not be read.
- **A lifecycle cannot be read**: the card says so in place of the picture; the field's card stays.
- **A lifecycle field in only one version of a comparison**: the miniature is all added or all removed, and a click opens it as the left panel's row does (spec 042).
- **The pointer leaves before the read ends**: the answer is dropped, and it never opens a card on another element.
- **The diagram is panned or zoomed under an open card**: the card closes.
- **Near an edge of the diagram**: the card stays whole inside the view and does not cover the row it describes.
- **Hovering while a stepper card is open**: the stepper's card stays; hovers open no second card.
- **Long content**: the card scrolls inside and has a limit on its height.
- **A pointer drag**: dragging the diagram opens no card and copies nothing.
- **A table with nothing to hide** (every row a key or, in Diff, changed): it has no control. In One and in Diff the control appears only where it would hide a row.
- **A table with no key rows**: it collapses to its header alone.
- **A non-key row that has a line**: it stays, because every line needs its row.
- **A foreign key whose line is filtered out**: the row stays, so hiding a filter does not change which rows a table keeps.
- **Tables inside a specialization block**: each collapses alone; the block stays.
- **A table collapsed, then filtered out and back**: it comes back collapsed.
- **A collapsed table that no longer exists in another version**: the address entry is ignored.
- **One and Diff**: the collapse state carries over between them, and a row that only Diff keeps visible goes back to hidden in One.
- **Following**: the follower's own pointer opens no card, as it holds no hover today.
- **A comparison that fails**: the card behaves as in One.

## Requirements *(mandatory)*

### Functional Requirements

**The one card**

- **FR-001**: Every field and every table header on the ERD, and every node and link on the full graph other than folded domains and bundles, MUST have the same card, in place of the text label.
- **FR-001a**: When a row is too small on screen to read or aim at (under 10 px for a pointer, 20 px for a finger), a hover or a tap anywhere on its table MUST open the table's card.
- **FR-002**: The card MUST appear after the pointer has rested about 300 ms, and MUST NOT appear for an element merely crossed.
- **FR-003**: The card MUST stay open while the pointer is on it or on its element, and close after the pointer has left both, or on Escape.
- **FR-004**: The card MUST show the element's name, what it is or its type, and its description when it has one.
- **FR-005**: In Diff, the card of a changed, added or removed element MUST also show what FR-028 of spec 038 shows: every changed property, before and after, or one line saying it was added or removed.
- **FR-006**: The table's card MUST list all its fields by name, hidden or not; the type and description of the field under the pointer or finger MUST stand in one reserved place below the list, so the card does not move.
- **FR-006c**: A table's card MUST hide its field list at first, behind a control that says how many fields there are; a person's choice MUST hold for every table in that browser; with the list hidden no field shows, and in Diff the control MUST count what changed, unless every row changed, as in a table that came or went whole.
- **FR-006a**: In Diff, the table's card MUST list what changed first, with its mark, a changed type reading old → new in the same place below as any type, and a table whose fields changed MUST wear the changed status, though the table itself did not.
- **FR-006b**: In Diff, an unchanged element's card MUST have the shape of a changed one: the status disk beside the name. One disk stands for a status everywhere, in the filter panels and on the cards: `+ − ~` in their colours and a grey `=` for unchanged.
- **FR-007**: A click on a name MUST copy it, on every field and header, in every mode, and MUST NOT open a card.
- **FR-008**: A tap on a phone MUST open the card, and the card MUST then offer a button that copies the name. A tap outside closes it.
- **FR-009**: The change stepper's card MUST keep its behaviour: opened by the step, closed by a click outside or Escape, and no hover opens another card while it stands.
- **FR-010**: In a room, a follower MUST see the followed person's card, with the same content and place on the diagram, including its miniature, opened and closed with theirs, and what happens inside it: the field list, the field pointed at and the scroll.
- **FR-010b**: Over a list whose scroll a follower shares, the leader's pointer MUST stay where it is on the follower's screen while the rows move under it.
- **FR-010a**: A card MUST stand on the side of its element that leaves in sight what the hover lights: related tables, active lines and their labels; where no side does, the one that covers least.
- **FR-011**: An ERD line MUST have a card: what joins what by table and field, its kind and cardinalities, its description and in Diff its change. The use-case and lifecycle diagrams keep a label, drawn white like the card.
- **FR-012**: Hover lighting of rows, lines and tables MUST work as it does today, alongside the card.
- **FR-011a**: A toolbar icon MUST switch cards off and on for this person in this browser; they start on. Collapsing all is an icon too.
- **FR-012a**: A click on the full graph MUST stay as it is today: on a change it opens that change's card and moves the stepper; elsewhere it closes the card or flies to a domain.

**What a card reads**

- **FR-013**: What a card shows beyond what the diagram holds MUST be read for that one element, in the shown version or pair, when the card opens, through an AOA action.
- **FR-014**: A read MUST NOT be started for an element whose card did not open, and a late answer MUST NOT reach another element's card.

**The lifecycle miniature**

- **FR-015**: A field or node that is a lifecycle MUST show a miniature of its diagram in its card, and a table MUST show one for each lifecycle it holds; nothing else may show one.
- **FR-015a**: Pointing at a lifecycle field MUST leave its picture bright and dim the others; the field itself takes no highlight.
- **FR-016**: The lifecycle MUST be read and drawn only when its card opens, and kept for that version or pair, so a second opening reads and draws nothing.
- **FR-017**: The miniature MUST fit the whole lifecycle into a width of about 300 px, whatever its size.
- **FR-018**: A click on the miniature MUST open the full diagram of that lifecycle in the same mode and versions.
- **FR-019**: In Diff, the miniature MUST mark states as the full diagram does (spec 042): added and removed in their colours and signs, unchanged dim.

**Collapsing**

- **FR-020**: A person MUST be able to collapse and expand one table by a control on its header, and all tables by a control on the toolbar.
- **FR-021**: A collapsed table MUST show its header, its primary key rows, its foreign key rows and any other row that has a line, and MUST say how many fields are hidden.
- **FR-022**: In Diff, a collapsed table MUST also show every added, removed and changed row, so the stepper never leads to a hidden row.
- **FR-023**: Lines MUST stay on their rows, with their end labels as today.
- **FR-024**: A specialization block MUST NOT collapse as a whole; its tables collapse one by one.
- **FR-025**: The default MUST be every table expanded, including those 1-hop brings in; the 1-hop switch MUST NOT change which fields a table lists.
- **FR-026**: After all are collapsed, a table that comes onto the diagram MUST come in collapsed, and a table expanded by hand MUST stay expanded until all are collapsed or expanded again.
- **FR-027**: The collapse state MUST be kept in the address, so a reload and a copied link give the same picture, and its length MUST NOT grow with the size of the diagram when all tables are collapsed.
- **FR-028**: The collapse state MUST be shared in a room in the same way as filters.
- **FR-029**: A collapse MUST lay the diagram out again, keeping the header of the table it acted on where it was on the screen; a toolbar action keeps the view as it is.
- **FR-030**: The check that every browser engine draws the same layout MUST cover at least one state with tables collapsed, and one such state in Diff.

**What stays**

- **FR-031**: With everything expanded, the ERD's drawing MUST be what it was before this work, apart from the header control.

### Key Entities

- **Card subject**: the field, table, node or link a card describes; known to the diagram by its kind and id, in the shown version or pair.
- **Card content**: what it is, its name, its description, its changes in Diff, and for a table its fields.
- **Lifecycle picture**: one lifecycle's drawing for one version or pair, drawn once and kept.
- **Collapse state**: whether tables are collapsed by default on this view, and the tables that differ from that default.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every field and header on the stand's ERD shows the card within half a second of resting on it, and none shows the old label.
- **SC-002**: Sweeping the pointer across a whole diagram opens no card and starts no read.
- **SC-003**: On every field and header, changed or not, one click copies the name and does nothing else.
- **SC-004**: Hovering 50 lifecycle fields in a row leaves panning and zooming as smooth as before, and a second visit to any of them reads nothing.
- **SC-005**: The stand's largest lifecycle fits whole into the card, and in Diff every added and removed state is visible and marked.
- **SC-006**: A follower sees every card the followed person sees, in a test covering One, Diff and the map.
- **SC-007**: Collapsing all tables on the stand's largest diagram makes it at least a third less tall, and every line still ends on a visible row.
- **SC-008**: In Diff with all tables collapsed, the stepper reaches every change on a visible element.
- **SC-009**: A copied link with collapsed tables opens the same picture, and the address with all tables collapsed is no more than 40 characters longer than without.
- **SC-010**: Three browser engines give one layout for each collapse state in the check run.

## The acceptance stand

The maintainer's rule stands: this is accepted in the real Maxitor on the history `erd-full` in `.demo-history/` (out of git), extended through its builder. The stand MUST hold: a field with a description and one without; a lifecycle field unchanged, changed and only in one version; a lifecycle of at least 30 states; a table with no key rows; a table of keys only; a table with a changed non-key row; a table in a specialization block; a dictionary reference row.

## Assumptions

- **Order**: the card comes first, because a collapsed table shows its hidden fields in it.
- **One specification, one branch**: #320 and #283 share them at the maintainer's word; every commit references the issue it serves.
- **Description**: every description the model declares reaches the graph file. Fields of entities, lifecycles, roles and `@connection` links gained theirs in protocol version 1.2, a new version because a published one never changes. A comparison of a 1.1 graph with a 1.2 one shows those as changes once.
- **A lifecycle field**: is recognised from data the graph already has; the plan decides how the ERD learns it.
- **The delay and sizes** of about 300 ms and 300 px are tuned on the stand, not fixed to the pixel.
- **Keyboard**: the card does not open by keyboard focus in this step, as the label did not.
- **A real phone and Safari** are checked as in #319: on emulation now, on a device later.
- **Depends on** specs 038, 040, 041 and 042, all merged, and #319.
- **Out of scope**: new miniatures of other diagrams, collapsing specialization blocks, changes to folded domains and bundles, cards on the use-case and lifecycle diagrams.
