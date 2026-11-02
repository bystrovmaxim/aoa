# Feature Specification: Events in the graph and its JSON

**Feature Branch**: `feature/issue-334-events-in-graph-json`

**Created**: 2026-11-02

**Status**: Draft

**Input**: Issue #334, "Events in the graph and its JSON: Open Gnomon Protocol 1.3", part of #95, depends on #333.

## Clarifications

### Session 2026-11-02

- Q: What does an `Event` node look like in the JSON? → A: As `Params`: empty node properties, the class path as `id`, the class name as `label`; fields are `Field` nodes carrying the description written in `Field(description=...)`, and class properties are `PropertyField` nodes.
- Q: What happens when an event field has no description? → A: It is allowed, as for `Params`: the field's description is an empty string and the build passes. The events of `aoa-demo` gain descriptions on all their fields.
- Q: How do events look in Maxitor until #335? → A: As they come: the full graph draws them without an icon of their own, nothing hides them, and there is no temporary code. The other diagrams do not change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a service's events from its graph file (Priority: P1)

A consumer of the graph (a viewer, an architecture check, a coding agent, a tool in another language) opens a service's graph document and learns which events exist, what fields each has, which methods emit each one, and which domains allow it. It needs neither AOA nor Python, and it does not run the service.

**Why this priority**: This is the purpose of the feature. Events declared in code stay invisible to everything outside the process until the document carries them.

**Independent Test**: Build the graph of a service holding domains in all three modes, export it, and answer every question above from the file alone.

**Acceptance Scenarios**:

1. **Given** a domain in mode 1 and no `@emits` on its methods, **When** the graph is exported, **Then** it holds no event nodes and no event edges for that domain, and the domain's `typed_events` is `false`.
2. **Given** a domain without `events` whose method declares `@emits`, **When** the graph is exported, **Then** the document holds an `Event` node for each named event and an `@emits` edge from the method to it, no `domain_event` edge, and `typed_events` is `false`.
3. **Given** a domain with `events`, **When** the graph is exported, **Then** the document holds an `Event` node for each event in `events` and in `@emits`, a `domain_event` edge to each event in `events`, `@emits` edges from the methods, and `typed_events` is `true`.
4. **Given** one event named by several methods and several domains, **When** the graph is exported, **Then** the document holds exactly one `Event` node for it, with its fields as `Field` nodes joined by `field` edges.
5. **Given** an action with methods of all five kinds, each with `@emits`, **When** the graph is exported, **Then** each method has its `@emits` edges, whatever its kind.

---

### User Story 2 - A wrong declaration stops the build (Priority: P1)

A developer names an event in `@emits` of a method in a mode 3 domain and forgets to add it to the domain's `events`. The graph build fails and names the mistake, before the first request.

**Why this priority**: Mode 3 promises that a delivered event is always in the vocabulary. Without this check the promise only fails at runtime, possibly on a rare failure path.

**Independent Test**: Declare such a method and build the graph; then add the event to `events` and build again.

**Acceptance Scenarios**:

1. **Given** a mode 3 domain and a method of it whose `@emits` names an event outside `events`, **When** the graph is built, **Then** the build fails with an error naming the action, the method, the event and the domain.
2. **Given** a compensator, an error handler or an access decision in that position, **When** the graph is built, **Then** the build fails the same way.
3. **Given** a mode 2 domain, **When** a method names any event, **Then** the build passes, because the domain has no vocabulary to break.

---

### User Story 3 - The protocol has a version that speaks of events (Priority: P1)

An author of a producer or a consumer in any language reads the published protocol and finds the word for an event, its edges and the domain's property, in neutral terms, in a new version. Published versions are as they were.

**Why this priority**: Without a published version the exported document fails its own schema, so User Story 1 cannot exist.

**Independent Test**: Validate an exported document against the new schema, and confirm the files of the older versions are byte for byte unchanged.

**Acceptance Scenarios**:

1. **Given** a document produced by the current code, **When** it is validated, **Then** it declares version `1.3` and passes the `1.3` schema.
2. **Given** the protocol's reader-facing pages, **When** they are read, **Then** the version table and the vocabulary describe `Event`, `@emits`, `domain_event` and `typed_events`, without naming a class of any one framework.

---

### User Story 4 - Existing consumers keep working (Priority: P2)

Every consumer in the repository (the graph builder, the graph comparison, Maxitor) opens both new `1.3` documents and older documents, including history kept in repositories. Comparing two versions of a graph reports events added and removed like any other element.

**Why this priority**: A consumer refuses a version it does not know, so once the producer writes `1.3`, a consumer left behind stops working.

**Independent Test**: Open a `1.3` document and a `1.2` document in each consumer; compare a pair that differs by one event and one `@emits` edge.

**Acceptance Scenarios**:

1. **Given** a `1.3` document, **When** Maxitor opens it, **Then** it loads as any other document does.
2. **Given** a `1.0`, `1.1` or `1.2` document, **When** a consumer opens it, **Then** it reads as before.
3. **Given** two graph versions, one with an added event and one extra `@emits` edge, **When** they are compared, **Then** the comparison names exactly those two elements as added, and removing them reports them as removed.
4. **Given** a document of a version no consumer knows, **When** it is opened, **Then** it is refused as such documents are today.

---

### Edge Cases

- A domain declares `events = ()`: `typed_events` is `true`, with no `domain_event` edges. This is how a reader tells an empty vocabulary from no vocabulary.
- A domain inherits `events` from a parent domain: it is in mode 3, with `typed_events` `true` and a `domain_event` edge to each inherited event; declaring its own replaces them.
- An event listed in `events` that no `@emits` names: it has an `Event` node and a `domain_event` edge, and no `@emits` edge.
- One event in the `events` of several domains: one node, one `domain_event` edge from each domain.
- A subclass of a listed event: it is a different event, with its own node, and the build check does not accept it in place of its parent.
- An action inherits from a parent action: only the methods of its own class give `@emits` edges to it.
- An event with no fields of its own: an `Event` node with no `field` edges.
- The system fields of an event (`level`, `channels`, `domain`, `domain_name`) describe delivery, not the fact: they do not become `Field` nodes.
- A method in a nested action answers to its own action's domain in the build check.

## Requirements *(mandatory)*

### Functional Requirements

**The graph**

- **FR-001**: The graph MUST hold one `Event` node per event class referred to by any `events` or `@emits`, however many methods and domains refer to it.
- **FR-002**: An `Event` node MUST have the shape of a `Params` node: empty node properties, the class path as `id`, the class name as `label`. Its own fields MUST be `Field` nodes joined by `field` edges, each with the description written on the field, and its class properties MUST be `PropertyField` nodes; the system fields MUST NOT appear.
- **FR-002a**: A field with no description MUST NOT stop the build; its description in the graph is an empty string. Every field of an event in `aoa-demo` MUST have a description.
- **FR-003**: Each event in a domain's `events`, declared or inherited, MUST be joined to that domain by a `domain_event` edge.
- **FR-004**: Each event in the `@emits` of a method MUST be joined to that method's node by an `@emits` edge, for `RegularAspect`, `SummaryAspect`, `Compensator`, `ErrorHandler` and `AccessDecide` alike.
- **FR-005**: The `Domain` node MUST carry `typed_events`: `true` when the domain has `events`, an empty tuple included, and `false` otherwise.
- **FR-006**: Nodes and edges MUST match the following table:

| Mode | `Event` nodes | `@emits` edges | `domain_event` edges | `typed_events` |
|---|---|---|---|---|
| 1 | none | none | none | `false` |
| 2 | those named in `@emits` | yes | none | `false` |
| 3 | those in `events` and in `@emits` | yes | yes | `true` |

- **FR-007**: Each `Event` node and each new edge MUST have a stable `id`, the same across builds of the same code, so that comparison treats them like any other element.
- **FR-008**: The graph build MUST fail when a method of a mode 3 domain names in `@emits` an event outside that domain's `events`, for all five kinds of method, and the error MUST name the action, the method, the event and the domain.
- **FR-009**: Everything in FR-001 to FR-006 MUST reach the exported JSON document.

**The protocol**

- **FR-010**: The protocol MUST gain version `1.3` as a new schema file, adding the node type `Event`, the edge types `@emits` and `domain_event`, and the `typed_events` property on `Domain`.
- **FR-011**: The schema files of `1.0`, `1.1` and `1.2` MUST stay unchanged.
- **FR-012**: The protocol's `README.md` (vocabulary and version table) and `CHANGELOG.md` MUST describe `1.3`, in neutral words that speak of an event and its fields and name no framework class.
- **FR-013**: The producer MUST write `1.3`.

**The consumers**

- **FR-014**: The graph builder, the graph comparison and Maxitor MUST read `1.3`, and MUST keep reading `1.0`, `1.1` and `1.2`.
- **FR-014a**: In Maxitor, `Event` nodes and their edges MUST appear on the full graph with no icon of their own and no filter, and the ERD, lifecycle and use-case diagrams MUST stay as they are.
- **FR-015**: A consumer MUST go on refusing a version it does not know.
- **FR-016**: Comparing two graph versions MUST report events and their edges as added or removed like any other element.
- **FR-017**: The graph files kept in the repository MUST be regenerated, and the saved-graph check MUST pass on them.

**The tail of the change**

- **FR-018**: Documentation MUST show every case of this feature (each mode, the empty vocabulary, the inherited vocabulary, the build refusal), each as a runnable script and a notebook.
- **FR-019**: The change MUST end with the closing check run, the documentation and the changelog, in that order, and MUST raise the version of every level it changes.

### Key Entities

- **Event**: a typed fact a service can publish. One per event class. Has a stable identity, a name, fields and class properties, and no properties of its own; referred to by methods and domains.
- **Field**: one attribute of an event, the same kind of element as a field of `Params` or `Result`.
- **`@emits` edge**: "this method may emit this event"; from a method to an event.
- **`domain_event` edge**: "this domain's vocabulary holds this event"; from a domain to an event.
- **`typed_events`**: a property of a domain saying whether it has a vocabulary at all.
- **Protocol version `1.3`**: the published definition of the words above.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a sample service with domains in all three modes, 100% of declared events, fields, method declarations and vocabulary entries can be recovered from the document alone, with no access to the code.
- **SC-002**: Each of the five kinds of method, in a mode 3 domain, stops the build when it names an event outside the vocabulary: 5 of 5.
- **SC-003**: Every exported document in the repository passes the `1.3` schema, and the older schema files differ from `main` in 0 bytes.
- **SC-004**: Every consumer opens documents of all four versions, and a document of an unknown version is refused in every consumer.
- **SC-005**: Two builds of the same code give identical documents, and a comparison of graphs differing by one event and one edge reports exactly those two elements.
- **SC-006**: A reader tells "no vocabulary" from "empty vocabulary" from the document in one lookup.

## Assumptions

- #333 is merged: `BaseEvent`, `@emits` and `events` exist, and `aoa-demo` runs in mode 3.
- Showing events in Maxitor is #335: its icon, card and event view are not part of this work.
- The build check of FR-008 already exists from #333; here it stays and is proved for all five kinds of method.
- The modes are those of #95: an event is matched by exact class, and one event may be in several vocabularies.
- The build check adds nothing for modes 1 and 2, and it does not look for lines with `kwargs`, which are declared nowhere and fail at runtime.
- Publishing packages, tags and deployment are out of scope.
