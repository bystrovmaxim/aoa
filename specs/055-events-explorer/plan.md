# Implementation Plan: Events explorer

**Branch**: `feature/issue-371-events-explorer` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

## Summary

The Events diagrams give way to an explorer: one AOA action returns the whole events graph (domains with and without events, vocabularies, all actions, emitting methods with their kinds, events with fields); the client keeps the open ports, computes the layers, the ports and the lines, lays the screen out with Graphviz `dot` and draws its own nodes and lines at Graphviz's positions. ERD's filter panel is generalized to a list of sections and ERD's pan and zoom hook is reused. The demo page of #371 is the reference of behaviour and is not shipped.

## Technical Context

**Language/Version**: Python 3.12 (CI also 3.14); TypeScript, React 19
**Primary Dependencies**: AOA actions, DuckDB graph resource, Graphviz WASM, MUI
**Storage**: graph documents through the existing resources
**Testing**: pytest, Vitest; browsers through `scripts/check_before_pr.sh` (layout determinism)
**Target Platform**: Maxitor web part
**Project Type**: web application
**Performance Goals**: a port opens and the screen is laid out again within half a second on the test graph and on aoa-demo
**Constraints**: endpoints only through actions; no language assumptions; documents older than 1.3 keep opening; ERD, Use case and the map unchanged in behaviour
**Scale/Scope**: one action, one viewer replacing another, one generalized panel, one hook addition

## Constitution Check

- I. Nothing committed, pushed or opened without instruction: the maintainer asked for every phase up to the pull request; each phase is a local commit, nothing is pushed.
- II. English in code and history, no tool attribution: held.
- III–V. Module headers, AI-CORE blocks on the new action and its builder, one-line docstrings on new code: planned.
- VI. The tail is the closing check run, the documentation, the changelog: phases 5, 6, 7. The pull request opens whole.
- House rules: versions of the levels changed raised (`packages/maxitor/web/version.toml`, `maxitor` in `pyproject.toml`); `packages/maxitor/web/graph.json` rebuilt with `graph-builder`; adversarial verification per phase, only the phase's tests run after it.

Gates pass, before and after design.

## Project Structure

```text
packages/maxitor/web/maxitor/web/model/diagrams/actions/   events_explorer_action.py, events_explorer_action_schema.py (new);
                                                           domain_events_diagram_action*.py (removed)
packages/maxitor/web/maxitor/web/api/app.py                 /events-explorer route; old routes removed
packages/maxitor/web/maxitor/web/model/rooms/pages.py       settings of the pages events, events-all
packages/maxitor/web/tests/                                 test_events_explorer_action.py, fixtures/graph-explorer*.json
packages/maxitor/web/graph.json                             rebuilt
packages/maxitor/web/client/src/api/                        eventsExplorer.ts
packages/maxitor/web/client/src/model/                      eventsExplorer.ts (wire)
packages/maxitor/web/client/src/lib/                        eventsExplorer.ts (graph, layers, ports, links, filters, DOT, Diff) + test
packages/maxitor/web/client/src/components/diagrams/        EventsExplorer/ (viewer, nodes, ports, mode pill, README); EventsDiagramViewer/ removed
packages/maxitor/web/client/src/components/ui/              ErdFilterPanel/ (sections list)
packages/maxitor/web/client/src/components/diagrams/ErdViewer/hooks/useSvgPanZoom.ts   placeAt
packages/maxitor/web/client/scripts/check-layout-determinism.ts                        the explorer's pages
docs/tutorials/step-29-maxitor.md
packages/maxitor/CHANGELOG.md
```

**Structure Decision**: one viewer folder, one pure library file holding every rule of the spec (so tests run without a browser), the panel and the hook extended rather than copied.

## Phases

Each phase is one commit.

1. **The data**: `GetEventsExplorerAction`, schema, route, test graph and tests; the old actions and routes removed; `graph.json` rebuilt.
2. **The explorer with its ports and lines**: viewer replacing the Events diagrams on both page keys (the old view, actions and routes removed), mode pill, first layers, nodes with counts, cards, layouts, ERD's pan and zoom with `placeAt`, layers, ports by layer, empty and joining ports, lines between neighbouring layers, method names and lighting on hover, holding the clicked node still, the settings in the room whitelist. A first layer that opens nothing is no commit of its own, so ports come in the same phase.
3. **Filters and paint**: the panel taking a list of sections, the sections of each mode, the gear shift painting nodes and lines.
4. **Comparison and state**: Diff and Side by side marks, change counts on closed ports, the page settings in the address, layout determinism pages.
5. **Closing check run** taken to zero.
6. **Documentation**: the Maxitor chapter.
7. **Changelog** and raised versions.
