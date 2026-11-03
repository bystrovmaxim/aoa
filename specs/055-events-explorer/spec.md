# Feature Specification: Events explorer

**Feature Branch**: `feature/issue-371-events-explorer`

**Created**: 2026-11-03

**Status**: Draft

**Input**: Issue #371, "Maxitor: explore events step by step — domains, events and actions opened through ports". The demo page `packages/maxitor/web/client/explore-demo.html` with `src/demo/eventsExplorer/` shows the behaviour this specification describes.

## Overview

Maxitor draws the graph of a service: its **domains**, its **actions**, and the **events** a method of an action may emit. A domain may keep a **vocabulary**: the list of events that belong to it; a domain with a vocabulary may emit only the events of its vocabulary.

Today the page "Events all domains view" draws every action, every emitting method and every event at once, inside one frame. With twenty domains the page is a wall of boxes, and the question a reader asks — *what happens after this, and where does it lead?* — cannot be answered by looking.

The explorer replaces that page. The screen starts with one layer, and the reader opens the graph one link at a time through **ports**, following a path the way process mining tools follow a process.

## Clarifications

### Session 2026-11-03

- Q: How does a closed port in Diff show that changes lie behind it? → A: Beside its number the pill carries a small count per kind of change in that kind's colour — "+1 −1" — and a kind with none is not shown; a port with no change behind it looks as in One.
- Q: Does the first layer of Actions mode list actions without events? → A: No: only the actions that emit; every action of a domain, those without events too, is reached through the domain's actions port.
- Q: What do the address of the page and a room keep? → A: Everything the reader chose: mode, layout, filters, paint and the open ports, each port by its node and its kind.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start from the domains and see how much each declares (Priority: P1)

A reader opens the events explorer and sees only the domains, each telling how many events it has and where they come from, without any frame, action or event on the screen.

**Why this priority**: It is the first screen and the question of coverage: which domains declare their facts, which only produce them, which have none.

**Independent Test**: Open the explorer on the test graph; every domain is on the screen with the right count and kind of count, and nothing else is.

**Acceptance Scenarios**:

1. **Given** the explorer opens, **When** nothing has been chosen, **Then** the mode is Domains and the screen holds every domain and nothing else.
2. **Given** a domain with a vocabulary of four events, **When** it is shown, **Then** it reads "4 in vocabulary".
3. **Given** a domain with an empty vocabulary, **When** it is shown, **Then** it reads "empty vocabulary" and counts as a domain with events.
4. **Given** a domain without a vocabulary whose actions emit three events, **When** it is shown, **Then** it reads "3 emitted · no vocabulary".
5. **Given** a domain without a vocabulary and without emitting actions, **When** it is shown, **Then** it reads "no events", is drawn quieter, and stands after the domains with events.

---

### User Story 2 - Open the next layer through a port (Priority: P1)

The reader opens what a node is linked to, one kind of link at a time, and closes it again, and sees lines only where they mean something.

**Why this priority**: This is the explorer itself: without ports the screen cannot grow from one layer.

**Independent Test**: From a domain, open its events, then the actions of one event, then join one action back; check the nodes, the lines and the numbers on the ports against the test graph.

**Acceptance Scenarios**:

1. **Given** a domain on the first layer, **When** the reader clicks the domain, **Then** its events appear on the next layer, joined to it by lines leaving its events port.
2. **Given** a port with four elements behind it, all hidden, **When** it is shown, **Then** it reads "4 +"; once opened it reads "4 −"; clicking it again hides what it opened, except what another open port still shows.
3. **Given** a node of a kind with no element behind one of its ports, **When** it is shown, **Then** that port is still drawn, reads "0", is quieter and cannot be clicked.
4. **Given** a node on the second layer, **When** it is shown, **Then** it has one port only: the one toward the kind not yet on the path.
5. **Given** a node on the third layer, **When** it is shown, **Then** it has one port only, toward the kind the path started from, drawn with a dashed outline; opening it adds no node and draws the lines from this node to the nodes already on the screen that no line joins it to yet.
6. **Given** an event of one domain also held by another domain on the screen, **When** the event is opened from the first domain, **Then** a line joins it to the second domain as well.
7. **Given** two nodes on the screen whose layers are not neighbours, **When** no open joining port asks for it, **Then** no line joins them.
8. **Given** the reader opens a port, **When** the screen is laid out again, **Then** the clicked node stays where it was on the screen and what it opened is brought into view.

---

### User Story 3 - Start from events or from actions (Priority: P1)

The reader starts from the events, or from the actions that emit, and walks the path in the other directions.

**Why this priority**: Consumers start from the event ("who produces it?"); authors start from the action ("what does it announce?").

**Independent Test**: Switch to Events, open one event's domains, then a domain's actions, then join an action; switch to Actions and do the same in its order.

**Acceptance Scenarios**:

1. **Given** the mode pill, **When** the reader chooses Events, **Then** the first layer is every event, and opened ports and the view start afresh.
2. **Given** Events mode, **When** an event's domains are opened and then a domain's actions, **Then** every action of that domain appears, those without events too, drawn quieter and saying "no events".
3. **Given** that screen, **When** an action's joining port is opened, **Then** lines join it to the events on the screen it emits, and an action that emits none of them reads "0".
4. **Given** the mode pill, **When** the reader chooses Actions, **Then** the first layer is every action that emits.

---

### User Story 4 - Filter and paint by what is on the screen (Priority: P2)

The reader narrows the screen with filters that fit the mode and what is open, and chooses what colours the diagram.

**Why this priority**: Once a few layers are open the screen grows; the reader needs to hide what does not matter and to see one property at a glance.

**Independent Test**: In each mode, open the layers one by one and check which filter sections and paint points are offered; switch rows and paints and check the screen.

**Acceptance Scenarios**:

1. **Given** Domains mode, **When** nothing is open, **Then** the panel offers Domains and Coverage, and the gear shift has two points.
2. **Given** events come onto the screen, **When** the panel is read, **Then** an Events section appears with three rows: in vocabulary and emitted; emitted with no vocabulary; in vocabulary and not emitted.
3. **Given** actions with events come onto the screen, **When** the panel is read, **Then** a Methods section appears with the five kinds of method.
4. **Given** an action without events comes onto the screen, **When** the panel is read, **Then** an Actions section appears with "with events" and "without events".
5. **Given** a section whose rows are all switched off, **When** that hides everything it sorts, **Then** the section stays on the panel to be switched back.
6. **Given** Events or Actions mode, **When** the panel is read, **Then** there is no Coverage section and its rows do not apply.
7. **Given** a kind of method switched off, **When** the screen is drawn, **Then** its lines are gone and an event only it emits no longer belongs to its domain's events.
8. **Given** the gear shift, **When** the reader moves it to a section, **Then** that section opens and colours the nodes and lines it describes, and everything else turns grey; every point paints the screen differently.
9. **Given** the painting section leaves the panel, **When** the screen is drawn, **Then** the domains paint again.

---

### User Story 5 - Compare two versions (Priority: P2)

A reader comparing two versions sees what changed among the events, even inside parts of the graph that are not open.

**Why this priority**: Events are what other services consume; a change in them must not hide behind a closed port.

**Independent Test**: Compare two versions of the test graph differing by one event and one emitting link; find both from the first layer.

**Acceptance Scenarios**:

1. **Given** Diff, **When** an added, removed or changed node or line is on the screen, **Then** it is marked as on the other diagrams.
2. **Given** Diff, **When** a change lies behind a closed port, **Then** the port carries a count per kind of change behind it, in that kind's colour ("+1 −1"); a kind with no change is not shown.
3. **Given** Side by side, **When** each half is drawn, **Then** each shows its own version's part of the same explored screen.

### Edge Cases

- A graph document older than events (protocol before 1.3) opens the explorer with domains and no events, and no error.
- A domain filtered out is never counted on a port and never drawn.
- An event held by several vocabularies is one node, joined to each of its domains on the screen.
- A long name is cut with an ellipsis on the node and shown whole on its card.
- A port opened on a node that later leaves the screen is remembered and applies again when the node comes back.
- A first layer too tall for the screen starts readable at its top, not shrunk to fit.
- The first layer keeps its order however the layers after it are drawn.
- A filter section title fits on one line; a title too long is cut, never wrapped.

## Requirements *(mandatory)*

### Functional Requirements

**Modes**

- **FR-001**: The explorer MUST replace the page "Events all domains view"; the Events row of a domain in the sidebar MUST open the explorer in Domains mode with that domain's events already open.
- **FR-002**: A pill in the middle of the top of the canvas MUST switch the mode between Domains, Events and Actions, each with its count; Domains MUST be the default. Changing the mode MUST close every port and fit the new first layer. A notice of the workspace (a merged pull request, a room's message) MUST stand below the pill, as far from it as the pill is from the top, never over it.
- **FR-003**: The first layer MUST be every domain in Domains mode (domains with events first, then the others, each group by name), every event in Events mode, and every action that emits in Actions mode (actions without events are reached only through a domain's actions port).

**Nodes**

- **FR-004**: A domain MUST be drawn as a node, never as a frame around other nodes, with its count of events as in User Story 1.
- **FR-005**: An action MUST show its domain's name under its own; an action without events MUST be quieter and say "no events".
- **FR-006**: An event held by no vocabulary MUST be told apart from one held by a vocabulary.
- **FR-007**: Resting on a node MUST open its card: for an event its fields with descriptions, every method that emits it with its action and kind, and its domains; for a domain its counts and its emitting actions; for an action what it emits.

**Ports and lines**

- **FR-008**: Every node MUST have ports, a short line out of its edge ending in a pill with an icon of what it leads to, a number, and "+" or "−": a domain's ports lead to its events and to all its actions; an event's to the actions that emit it and to its domains; an action's to the events it emits and to its domain.
- **FR-009**: Ports MUST follow the layer: the first layer has both its ports; the second has one, toward the kind not yet on the path; the third has one joining port, toward the kind the path started from, which adds no node.
- **FR-010**: A port with nothing behind it MUST be drawn with "0", quieter and inert, so the nodes of a column line up.
- **FR-011**: Clicking a node MUST open or close its main port (domain: events; event: actions; action: events) or, when that is empty or not offered, its first port with something behind it.
- **FR-012**: A line MUST be drawn only when both its ends are on the screen and stand on neighbouring layers, or when an open joining port asks for it; it MUST leave its node by the port of its kind. Lines MUST have no arrows.
- **FR-013**: The four kinds of line MUST be told apart by what they join and by their stroke: domain–event solid (in the vocabulary), domain–event dotted (emitted by a domain without a vocabulary), action–event solid (a method emits it), domain–action dashed (an action of the domain).
- **FR-014**: A method's name MUST show beside the start of its line while the line or one of its ends is under the pointer, and not otherwise.
- **FR-015**: Resting on a node or a line MUST light it and its lines and dim the rest.

**Filters and paint**

- **FR-016**: The filter panel MUST keep the look and behaviour of ERD's (fixed width, one section open at a time, rows switched by a click and dimmed when off, titles on one line) and MUST take its sections from the mode and the screen, as in the table below; whether a section is offered MUST be read from the screen as it would be with every row on.

  | Section | Rows | Offered |
  |---|---|---|
  | Domains | every domain | always |
  | Coverage | with events · without events | in Domains mode |
  | Events | in vocabulary, emitted · emitted, no vocabulary · in vocabulary, not emitted | while events are on the screen |
  | Methods | the five kinds of method | while actions with events are on the screen |
  | Actions | with events · without events | while an action without events is on the screen |

- **FR-017**: A row whose kind has nothing on the screen MUST be dimmed; filters MUST hide what they hide everywhere, ports' numbers included.
- **FR-018**: Every section MUST be able to paint the diagram; the gear shift at the panel's foot MUST have one point per section on the panel; moving it MUST open that section; painting MUST colour nodes as well as lines (by Methods: a strip of the kinds of method behind each action and event, and the kind's colour on a node with one kind only); everything not painted MUST be grey.

**Layout and view**

- **FR-019**: The toolbar MUST offer two layouts, left to right (the default) and top to bottom, with zoom, fit, the switch of hover cards and a button that closes every port; top to bottom MUST move the ports under the node.
- **FR-020**: Layers MUST stand far enough apart across the flow that the lines out of one port part before they arrive.
- **FR-021**: Moving and zooming MUST be ERD's: a two-finger swipe or a plain wheel moves the picture, a pinch or Ctrl / ⌘ with the wheel zooms about the pointer, a drag moves it, the buttons zoom by ERD's steps within ERD's limits.
- **FR-022**: Opening a port MUST keep the clicked node still on the screen and bring what it opened into view; a mode, filter or layout change MUST fit the screen.

**Comparison, state and data**

- **FR-023**: In Diff and Side by side, the explorer MUST mark nodes and lines as other diagrams do, and a closed port MUST carry a count per kind of change behind it (added, removed, changed), each in its colour, showing only the kinds present; a port with no change behind it MUST look as in One.
- **FR-024**: The mode, the layout, the filters, the paint and the open ports (each by its node and its kind) MUST be part of the page's state: the address of the page and a room MUST keep them.
- **FR-025**: The explorer MUST read domains (with and without events), vocabularies (empty ones included), actions (with and without events), the methods that emit and their kinds, events with their fields, and every link between them from the graph document only, in one answer, served through an AOA action.
- **FR-026**: The explorer MUST make no assumption about the language a service is written in beyond the graph document.

### Key Entities

- **Domain**: an area of the business; has a vocabulary (possibly empty) or none; owns actions.
- **Vocabulary**: the events a domain declares; a domain with one may emit only those.
- **Action**: an operation of a domain; has methods of five kinds; emits events through them, or none.
- **Method**: regular aspect, summary aspect, compensator, error handler or access decision; emits events.
- **Event**: a typed fact with fields; one node however many methods and domains name it; its standing is in vocabulary and emitted, emitted with no vocabulary, or in vocabulary and not emitted.
- **Port**: one kind of link of a node on the screen, with the number of elements behind it, open or closed, leading on or joining.
- **Layer**: the distance of a node from the first layer along the open ports; decides its ports.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From the first screen, a reader finds which actions emit a given event of a given domain in at most two clicks.
- **SC-002**: The first screen of Domains mode holds only domains — no action, no event, no line — on every graph.
- **SC-003**: For every port on the test graph, the number shown equals the elements behind it under the filters on, with no omission and no element counted twice.
- **SC-004**: Every point of the gear shift, in every mode and at every layer, paints the screen differently from every other point.
- **SC-005**: A comparison differing by one event and one emitting link shows both, from the first layer, without opening a port blindly.
- **SC-006**: A page opened from its address, or by a follower in a room, shows the same nodes, open ports, filters and paint.

## Assumptions

- The graph document already carries every fact the explorer needs (#334, protocol 1.3); the protocol does not change.
- The graph of `aoa-demo` holds only two events, so a test graph built for this feature, and the acceptance stand, hold domains of every coverage, events of every standing, events held by several vocabularies, events emitted across domains, actions without events and methods of all five kinds.
- The demo page and its data are a reference for behaviour only; they are not shipped.
- ERD's filter panel and pan-and-zoom code are reused; the panel is generalized to take any list of sections, and ERD keeps its own sections.
- The per-domain Events diagram of #335 stays reachable only through the explorer (FR-001).
- Reading recorded runs (event logs) is out of scope: this is the structure of the graph only. ERD and Use case do not change.
- The work ends with the closing check run, the documentation (the Maxitor chapter) and the changelog, in that order.
