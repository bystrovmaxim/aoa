# Tasks: Events in the graph and its JSON

**Input**: Design documents from `specs/052-events-in-graph-json/`

**Tests**: Included. The repository's rule is adversarial verification: each phase proves its tests by breaking the code the test must catch, against the test files of that phase alone.

**Organization**: One phase is one commit, in the order of issue #334. A commit is made only on the maintainer's instruction. Paths use `AM` for `packages/aoa-action-machine/src/aoa/action_machine` and `AMT` for `packages/aoa-action-machine/tests`.

## Phase 1: Protocol version 1.3 (US3)

**Goal**: The protocol has words for events; older versions are unchanged.

**Independent test**: A hand-written minimal `1.3` document passes the schema; each listed mistake fails it.

- [X] T001 [US3] Create `packages/open-gnomon-protocol/graph/1.3.json` from `1.2.json` with the four changes of `contracts/graph-1.3.md`: `schema_version` `const "1.3"` and `$id`; `Event` vertex with `maxProperties: 0`; required boolean `typed_events` on `Domain`; `emits` and `domain_event` as definitions of their own in `link`, with `relationship` `const "Association"` and `const "Aggregation"`, `is_dag` `const false`, and empty properties
- [X] T002 [US3] Update `packages/open-gnomon-protocol/README.md`: badge, example, specification table, "Vocabulary of version 1.3" with 24 node types and 33 edge types, the version table; neutral words, no framework class
- [X] T003 [US3] Add the `1.3` entry to `packages/open-gnomon-protocol/CHANGELOG.md`, saying that `typed_events` is required, so a `1.2` document does not become `1.3` by changing its version
- [X] T004 [US3] Add tests in `packages/maxitor/tools/graph_builder/tests/test_schemas.py`, read straight from the protocol file: a valid document with all new words passes; `Event` with properties, `Domain` without `typed_events`, `@emits` with a relationship other than Association and `domain_event` with one other than Aggregation are refused; `1.0`–`1.2` files equal `main`
- [X] T005 [US3] Run the phase tests; break each schema rule in turn, confirm the matching test fails, restore

## Phase 2: The graph (US1, US2)

**Goal**: The AOA graph and its JSON carry events exactly as the mode table says.

**Independent test**: One graph with domains in all three modes matches FR-006.

- [X] T006 [US1] Export the system field names as a public constant in `AM/model/base_event.py`
- [X] T007 [P] [US1] Create `AM/graph/edges/emits_graph_edge.py`: `@emits`, Association, `is_dag` false, empty properties, with a static builder reading `EMITS_ATTR` from a method
- [X] T008 [P] [US1] Create `AM/graph/edges/domain_event_graph_edge.py`: `domain_event`, Aggregation, `is_dag` false, empty properties, with a static builder reading `getattr(domain_cls, "events", ())`
- [X] T009 [US1] Create `AM/graph/nodes/event_graph_node.py`: `NODE_TYPE` `Event`, dotted `id`, class name `label`, empty properties, `field` and `property` edges and companions as in `params_graph_node.py`, dropping the system fields
- [X] T010 [US1] Create `AM/graph/inspectors/event_graph_node_inspector.py` on the `BaseEvent` axis: `_get_node` returns a node only for an event named in the `events` or `@emits` of a class in the graph, skipping `exclude_graph_model` classes; register it in `AM/graph/node_graph_coordinator_factory.py`
- [X] T011 [US1] Add `typed_events` (`hasattr(domain_cls, "events")`) and `domain_event` edges in `AM/graph/nodes/domain_graph_node.py`, in `properties`, `to_dict` and `get_all_edges`
- [X] T012 [US1] Add `@emits` edges in `AM/graph/nodes/regular_aspect_graph_node.py`, `summary_aspect_graph_node.py`, `compensator_graph_node.py`, `error_handler_graph_node.py`, `access_decide_graph_node.py`
- [X] T013 [US1] Write `"schema_version": "1.3"` in `AM/graph/core/node_graph_coordinator.py`, and update the version in its module docstring
- [X] T014 [US3] Copy `packages/open-gnomon-protocol/graph/1.3.json` over `AM/graph/graph_json_schema.json`, byte for byte, and change the path and the version in the docstring of `AM/graph/graph_json_schema.py`; `tests/scripts/test_schema_copies.py` holds the two equal
- [X] T015 [US1] Update every test pinned to `1.2` under `AMT/action_machine/graph/` and `AMT/action_machine/graph_host/`, found with a search for `schema_version` and `"1.2"`; the changed files are tests of this phase
- [X] T016 [US1] Add `AMT/action_machine/graph/test_events_in_graph.py`: all three modes against FR-006; one event from several methods and domains is one node; five kinds of method; `events = ()`; inherited and replaced vocabulary; listed but not emitted; subclass is its own event; parent action's methods give no edges; event with no fields; no system fields; field description and `""`; `PropertyField`; two builds give identical JSON
- [X] T017 [US2] Extend `AMT/action_machine/graph/test_emits_vocabulary_validator.py`, which already covers the five kinds: the message names action, method, event and domain; a subclass of a listed event fails; mode 2 passes. Change `AM/graph/validators/emits_vocabulary_validator.py` only if a test shows a gap
- [X] T018 Run the phase tests; break the code for each test (drop the filter of T010, the system-field drop, one kind of method, `typed_events` as truthiness, one marker of the validator), confirm only the matching test fails, restore

## Phase 3: The readers (US4)

**Goal**: All consumers read `1.0`–`1.3` and refuse the unknown.

**Independent test**: A `1.3` and a `1.2` document open in each consumer; two graphs differing by one event and one edge compare exactly.

- [X] T019 [US4] Copy `1.3.json` to `packages/maxitor/tools/graph_builder/maxitor/graph_builder/schemas/`, add it to `SCHEMA_VERSIONS` in `schemas/__init__.py`, and add the fixture `packages/maxitor/tools/graph_builder/tests/fixtures/graph-1.3.json`
- [X] T020 [US4] Add `1.3` to `KNOWN_VERSIONS` in `packages/maxitor/core/graph_compare/maxitor/graph_compare/compare.py`
- [X] T021 [US4] In `packages/maxitor/web/maxitor/web/model/diagrams/resources/duckdb_graph_resource.py` add an `event` table, its filling, `Event` and both edge types to `_assert_no_unknown_graph_types`, and read `typed_events` tolerantly, since older documents lack it
- [X] T022 [US4] Add the `event` slug to `_DUCK_SLUG_TO_INTERCHANGE` in `packages/maxitor/web/maxitor/web/model/diagrams/actions/list_node_types_action.py`; no colour, no icon, no filter
- [X] T023 [P] [US4] Extend `packages/maxitor/tools/graph_builder/tests/test_schemas.py`: `1.3` fixture accepted, `9.9` refused
- [X] T024 [P] [US4] Extend `packages/maxitor/core/graph_compare/tests/test_graph_compare.py`: an added and a removed event and `@emits` edge are reported as exactly those elements; `1.2` against `1.3` compares; `9.9` refused
- [X] T025 [P] [US4] Add `packages/maxitor/web/tests/test_duckdb_event_nodes.py`: a `1.3` document loads, events and edges are on the full graph, ERD, lifecycle and use-case results equal those of the same document without events, a `1.2` document loads
- [X] T026 [US4] Run the phase tests; break each list and the table, confirm the matching test fails, restore

## Phase 4: The graph files

- [X] T027 Add a `description` to every field in `packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/events.py`
- [X] T028 Add `aoa.demo.fastapi_mcp_services.actions` to `_MODULES` in `packages/aoa-demo/src/aoa/demo/model/build.py`, so the demo's graph holds its events. Regenerate `packages/aoa-demo/graph.json`, `packages/maxitor/web/graph.json` and `packages/maxitor/tools/repo_graph_port/graph.json` with `graph-builder`, check they hold events and pass `graph-builder check`, and update the demo's node and edge counts in `packages/open-gnomon-protocol/README.md`

## Phase 5: Closing check run

- [X] T029 Take every check this machine can run to zero, `graph-builder check` included; CI's closing run and `scripts/check_before_pr.sh` follow on the pushed commit, on instruction

## Phase 6: Documentation

- [X] T030 Add the page on events in the graph (each mode, empty and inherited vocabulary, build refusal, comparison) to `docs/tutorials/step-11-object-events.md`, or its own page if it outgrows the chapter, and update `docs/how-to/read-the-full-graph-map.md`
- [X] T031 Add each case as a script and a notebook in `examples/step_11_object_events/`, running each and pasting what it printed; run `examples/step_26_maxitor/21_element_card.py`, `22_version_file.py` and `23_version_track.py` with their notebooks, and raise their `1.2` where the text describes the current version
- [X] T032 Write the Russian version beside each new page as `<page>.ru_draft.md`

## Phase 7: Changelog

- [X] T033 Write one article in `docs/CHANGELOG.md` about what this work created, in plain words
- [X] T034 Raise the version of every changed level: `packages/open-gnomon-protocol/version.toml` to `1.3.0`, and `version.toml` of `aoa-action-machine`, `aoa-demo`, `maxitor`, `maxitor/web`, `maxitor/tools/graph_builder`, plus any other level `version-gate` names

## Phase 8: The stand

- [X] T035 Start the demo stand and open the full graph of the local history in diff mode (`view=full-graph`), with two versions of which the newer holds this work; events (`OrderRequestedEvent`, `OrderValidatedEvent`) and their edges must be visible. A screenshot goes into the report; no commit

## Dependencies & Execution Order

- Phases run in order 1 → 8. Phase 2 needs the schema of phase 1; phase 3 needs documents of phase 2; phase 4 needs phase 3, since `graph-builder check` must know `1.3`.
- US3 comes first in the issue's order, although all P1 stories are equal, because no document is valid without it.
- Tests of phase 2 run on built graphs, not through Maxitor, so phase 2 stands alone until phase 3 lands.

## Parallel Examples

- Phase 2: T007 and T008 are separate files.
- Phase 3: T023, T024 and T025 are separate test files.

## Implementation Strategy

There is no partial delivery: the pull request opens whole after phase 7. Phases 1–3 are the core; a producer writing `1.3` without its readers must not reach `main`.
