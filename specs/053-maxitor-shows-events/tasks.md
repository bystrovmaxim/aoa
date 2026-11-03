# Tasks: Maxitor shows events

**Input**: [spec.md](spec.md), [plan.md](plan.md). Tests are required: every phase is verified adversarially.

## Phase 1: The view of events (one commit)

### Foundation

- [x] T001 Add the test graph with all three modes and all five kinds of method in packages/maxitor/web/tests/fixtures/graph-events.json
- [x] T002 [P] Add the Event icon in packages/maxitor/web/client/src/lib/icons/graph_node_disk_icons.ts

### US1, US2: the diagram

- [x] T003 [US1] Add the action and schema in packages/maxitor/web/maxitor/web/model/diagrams/actions/domain_events_diagram_action.py and domain_events_diagram_action_schema.py, per contracts/events-diagram.md and the band rules of data-model.md
- [x] T004 [US1] Add the all-domains action in packages/maxitor/web/maxitor/web/model/diagrams/actions/all_events_diagram_action.py
- [x] T005 [US1] Add sidebar rows `events_domain` and all domains, after Use case, in packages/maxitor/web/maxitor/web/model/diagrams/actions/ (the sidebar action) and packages/maxitor/web/client/src/components/navigation/LeftSidebar/LeftSidebar.tsx
- [x] T006 [US1] Add the selection and address `view=events` in packages/maxitor/web/client/src/model/diagramSelection.ts and packages/maxitor/web/client/src/app/App.tsx
- [x] T007 [US2] Add packages/maxitor/web/client/src/api/domainEventsDiagram.ts, packages/maxitor/web/client/src/model/domainEventsDiagram.ts and packages/maxitor/web/client/src/lib/buildDomainEventsDotSource.ts
- [x] T008 [US2] Add packages/maxitor/web/client/src/components/diagrams/EventsDiagramViewer/ with label, bands, Use case controls and README
- [x] T009 [US1] Add tests for the three modes, an empty domain and a 1.2 document ("No events") beside the action
- [x] T010 [US2] Add tests for all five kinds, and that a method with no event is not drawn, in buildDomainEventsDotSource.test.ts

### US3: the card

- [x] T011 [US3] Extend packages/maxitor/web/client/src/components/diagrams/ElementCard/ElementCard.tsx with the event's fields, methods with actions, domains; the vocabulary label on a domain's card; links per Clarifications
- [x] T012 [US3] Add tests in packages/maxitor/web/client/src/components/diagrams/ElementCard/ElementCard.test.tsx

### US4: comparison

- [x] T013 [US4] Mark events, links, vocabulary changes and changed fields in EventsDiagramViewer, counted with other changes, on the Use case model
- [x] T014 [US4] Support Side by side and rooms, with the "Not in ..." notice, in packages/maxitor/web/client/src/components/diagrams/SideBySide/SideBySide.tsx
- [x] T015 [US4] Add tests for a pair differing by one event and one link, and for 1.2 against 1.3
- [x] T016 Add the Events page to packages/maxitor/web/client/scripts/check-layout-determinism.ts
- [x] T017 Break each rule adversarially against this phase's tests, restore; run quickstart.md on a stand holding all modes and kinds

## Phase 2: Closing check run

- [x] T018 Run the closing check run to zero

## Phase 3: Documentation

- [x] T019 Add events to docs/tutorials/step-26-maxitor.md, its .ru_draft.md, and packages/maxitor/README.md
- [x] T020 Raise the versions of the changed levels in their version.toml

## Phase 4: Changelog

- [x] T021 Write one article in packages/maxitor/CHANGELOG.md and CHANGELOG.ru_draft.md

## Dependencies

T001 first; T003–T010 before T011 and T013; the phases in order. T002 is parallel. MVP: US1 and US2.
