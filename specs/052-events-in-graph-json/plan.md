# Implementation Plan: Events in the graph and its JSON

**Branch**: `feature/issue-334-events-in-graph-json` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/052-events-in-graph-json/spec.md`

## Summary

Publish Open Gnomon Protocol `1.3` with the words `Event`, `@emits`, `domain_event` and `typed_events`. Teach the AOA graph to produce them, from the `@emits` and `events` declarations #333 already stores. Teach the three consumers to read them. The build check already exists and only needs proof for all five kinds of method. Decisions and their reasons are in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14); TypeScript for the Maxitor client, which needs no change here

**Primary Dependencies**: Pydantic (event fields), JSON Schema 2020-12, DuckDB (Maxitor's graph store)

**Storage**: Graph JSON files kept in the repository; DuckDB in memory in Maxitor

**Testing**: pytest per package; phase tests only, the closing check run in CI

**Target Platform**: Library and tools; no new runtime target

**Project Type**: Monorepo of libraries, a protocol and a web tool

**Performance Goals**: The graph grows by the declared events only; no new cost for a graph without events

**Constraints**: Published schema files never change; the same code gives the same document; a graph with no events differs from `1.2` only in `schema_version` and `typed_events`

**Scale/Scope**: About 12 modules in `aoa-action-machine`, 3 in Maxitor, the protocol folder, 3 kept graph files

## Constitution Check

| Rule | Status |
|---|---|
| I. The maintainer decides | Pass: nothing is committed without an instruction; each phase below is a commit only when asked |
| II. English | Pass: all artifacts and code in English |
| III–V. Headers, AI-CORE, docstrings | Pass: new modules follow them; `EventGraphNode` and the two edges carry AI-CORE blocks |
| VI. Tail of three steps | Pass: phases 5, 6, 7 are the check run, the documentation, the changelog, each its own task; documentation shows every case as a script and a notebook |
| Check run: every check once | Pass: phases run their own tests; CI runs the closing run; browsers via `check_before_pr.sh` |
| Versions | Pass: each changed level is raised before the pull request opens |

Re-checked after design: no violations, nothing for Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/052-events-in-graph-json/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/graph-1.3.md
└── tasks.md            (created by /speckit-tasks)
```

### Source Code (repository root)

```text
packages/open-gnomon-protocol/
├── graph/1.3.json                      new
├── README.md, CHANGELOG.md             vocabulary, version table
packages/aoa-action-machine/src/aoa/action_machine/
├── model/base_event.py                 the system field names become importable
├── graph/nodes/event_graph_node.py     new
├── graph/edges/emits_graph_edge.py     new
├── graph/edges/domain_event_graph_edge.py  new
├── graph/inspectors/event_graph_node_inspector.py  new
├── graph/node_graph_coordinator_factory.py  registers the inspector
├── graph/nodes/domain_graph_node.py    typed_events, domain_event edges
├── graph/nodes/{regular_aspect,summary_aspect,compensator,error_handler,access_decide}_graph_node.py  @emits edges
├── graph/core/node_graph_coordinator.py  writes 1.3
├── graph/graph_json_schema.json, graph_json_schema.py  copy of 1.3
packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/events.py  field descriptions
packages/maxitor/
├── tools/graph_builder/maxitor/graph_builder/schemas/  1.3.json, SCHEMA_VERSIONS
├── core/graph_compare/maxitor/graph_compare/compare.py  KNOWN_VERSIONS
├── web/maxitor/web/model/diagrams/resources/duckdb_graph_resource.py  event table, known types
├── web/maxitor/web/model/diagrams/actions/list_node_types_action.py  the event slug
packages/aoa-demo/graph.json, packages/maxitor/web/graph.json, packages/maxitor/tools/repo_graph_port/graph.json  regenerated
```

**Structure Decision**: Follow the existing one-file-per-node, one-file-per-edge layout, and one inspector per axis.

## Phases

One phase is one commit, in the order of the issue.

1. Protocol `1.3`: schema, `README.md`, `CHANGELOG.md`.
2. The graph: nodes, edges, `typed_events`, the document writes `1.3`, AOA's copy of the schema, the tests pinned to `1.2`; additions to the tests of the build check.
3. The readers: graph builder, comparison, Maxitor's store.
4. Field descriptions of the `aoa-demo` events; regenerated graph files.
5. Closing check run taken to zero.
6. Documentation: every case, script and notebook.
7. Changelog, and the raised versions.
