# Feature Specification: Maxitor shows events

**Feature Branch**: `feature/issue-335-maxitor-shows-events`

**Created**: 2026-11-02

**Status**: Draft

**Input**: Issue #335, "Maxitor shows events: which method emits what, and which domain holds it", part of #95, depends on #334.

## Clarifications

### Session 2026-11-02

- Q: Where does a reader see a domain's events and which method emits what? → A: On a new diagram of a domain, "Events", beside ERD and Use case: actions, their methods, and the events they emit, left to right, inside the domain's frame. Methods with no event are not drawn. ERD and Use case do not change.
- Q: Where is the vocabulary shown? → A: In the header of the domain's frame, as "Vocabulary" or "No vocabulary", and on the domain's card. With a vocabulary the events stand in two bands: "In vocabulary", and "Not emitted" for those no method of the domain emits. Without one there is a single band, "Emitted".
- Q: What opens from an event? → A: The common card: its fields with descriptions, every method with its action, its domains. A method or domain on the card leads on to it.

- Q: Is there a diagram for all domains? → A: Yes, as for Use case: one row for all domains together, and one per domain placed after Use case.
- Q: What of a method with no event? → A: It is not drawn on the diagram; its card shows no events.
- Q: What of a method emitting an event of another domain's vocabulary? → A: The event is drawn in the method's domain, in the band that domain's own vocabulary gives. In mode 3 the build refuses an event outside the domain's vocabulary.
- Q: What does a comparison show beyond added and removed? → A: A domain gaining or losing its vocabulary is a change of the domain, and its label changes. A changed field marks the event changed, and the card names the change.
- Q: What of Side by side and older documents? → A: A domain on one side only gives the "Not in ..." notice, as on other diagrams. A document older than 1.3 keeps the row, and the page says "No events".
- Q: How are the steps of SC-003 counted? → A: Opening the domain's diagram, then hovering the event.
- Q: What does "leads on" open? → A: A method opens the Use case diagram of its domain on its action; a domain opens its Events diagram. Controls are direction, boundary, the domain filter on the diagram of all domains, and the changes filter.
- Q: Which domains does an event belong to? → A: Those holding it in a vocabulary, then those whose methods emit it.
- Q: What are the five kinds? → A: The node types `RegularAspect`, `SummaryAspect`, `Compensator`, `ErrorHandler`, `AccessDecide`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See what a domain holds (Priority: P1)

A reader opens a domain in Maxitor and sees the events of that domain, and whether the domain has a vocabulary of events.

**Why this priority**: The domain is where a reader starts. Without this view, events in the graph file stay unread.

**Independent Test**: Open one domain of each mode in the demo graph and name its events and its mode from the page alone.

**Acceptance Scenarios**:

1. **Given** a domain with a vocabulary, **When** it is opened, **Then** every event of the vocabulary is shown and the page says the domain has a vocabulary.
2. **Given** a domain without a vocabulary whose methods emit events, **When** it is opened, **Then** those events are shown and the page says the domain has no vocabulary.
3. **Given** a domain with no events, **When** it is opened, **Then** the page says so plainly.

---

### User Story 2 - See which method emits what (Priority: P1)

A reader sees, for each method of each action that emits, the events it may emit, for all five kinds of method: aspects, summaries, compensators, error handlers and access decisions.

**Why this priority**: This is the question that events exist to answer without reading method bodies.

**Independent Test**: Take an action with methods of all five kinds, each declaring events, and read the pairs of method and event from the page.

**Acceptance Scenarios**:

1. **Given** a method that declares events, **When** the reader looks at it, **Then** each declared event is shown joined to it, whatever the kind of method.
2. **Given** a method that declares no event, **When** the diagram is opened, **Then** the method is not drawn, and its card shows no events.

---

### User Story 3 - Start from an event (Priority: P1)

A reader chooses an event and sees every method that produces it, the domain or domains it belongs to, and its fields with their descriptions.

**Why this priority**: Consumers of an event start from the event: they ask who produces it.

**Independent Test**: Choose an event named by several methods and by several domains and compare the page with the graph file.

**Acceptance Scenarios**:

1. **Given** an event emitted by several methods, **When** it is chosen, **Then** all of them are shown, each with its action.
2. **Given** an event held by several domains, **When** it is chosen, **Then** all of them are shown.
3. **Given** an event outside any vocabulary, **When** it is chosen, **Then** the page shows the domains of the methods that emit it, and says that no vocabulary holds it.

---

### User Story 4 - Compare two versions (Priority: P2)

A reader compares two versions of a graph and sees the events added and removed, and the links between methods and events that appeared or went away.

**Why this priority**: A change in the facts a service publishes matters to everyone who consumes them.

**Independent Test**: Compare a pair of versions differing by one event and one emitting link.

**Acceptance Scenarios**:

1. **Given** an event only in B, **When** the versions are compared, **Then** it is marked added; only in A, marked removed.
2. **Given** a link between a method and an event only on one side, **When** the versions are compared, **Then** the link is marked the same way.
3. **Given** a version older than events, **When** it is compared with a version holding them, **Then** the comparison opens and its events are added.

### Edge Cases

- A graph document of a version older than `1.3` opens with no events and no error.
- An event field without a description is shown with an empty description.
- One event held by several domains is one event, not a copy per domain.
- A long event class name stays readable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Maxitor MUST read events, their fields, the domain's vocabulary flag and the links of events only from the graph document.
- **FR-002**: Maxitor MUST offer each domain an Events diagram showing its events, in the bands of the clarifications, and a label saying whether it has a vocabulary; the domain's card MUST carry the same label.
- **FR-003**: Maxitor MUST show the events of a method for all five kinds of method.
- **FR-004**: From an event, Maxitor MUST show every method producing it, each with its action, and its domains.
- **FR-005**: The card of an event MUST show its fields and their descriptions, and its methods and domains MUST lead on to them.
- **FR-006**: Events MUST have an icon of their own, on every view that draws them.
- **FR-007**: A comparison MUST mark events and their links as added or removed, and MUST count them with the other changes.
- **FR-008**: Documents older than `1.3` MUST keep opening.
- **FR-009**: Rooms, the address of a page and Side by side MUST treat the events view as they treat other diagrams.
- **FR-010**: The view MUST make no assumption about the language a service is written in beyond the graph document.

### Key Entities

- **Event**: a typed fact, with fields; one node however many methods and domains name it.
- **Domain**: holds events; has a vocabulary or not.
- **Method**: one of five kinds, belongs to an action, emits events.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every event of the test graph, the methods and domains shown match the graph file, with no omission.
- **SC-002**: All five kinds of method are shown with their events on the test graph.
- **SC-003**: A reader finds who produces an event in at most two steps from the domain.
- **SC-004**: A comparison differing by one event and one link reports exactly those two changes.

## Assumptions

- The graph document already carries everything needed (#334); the protocol does not change.
- The graph of `aoa-demo` holds only two events, emitted by a regular aspect and a summary, and one domain with a vocabulary. So a test graph built for this feature, and the acceptance stand, hold all three modes and methods of all five kinds.
- The phases are those of the issue: the view, the closing check run, the documentation, the changelog.
