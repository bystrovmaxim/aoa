# Research: Events explorer

## The data

- **Decision**: one new AOA action, `GetEventsExplorerAction`, at `GET /api/v1/events-explorer`, answering the whole events graph at once: every domain with its vocabulary flag, every action with its domain, the vocabulary pairs, and every emitting method as `(action, method, kind, event)`, with events and their fields.
- **Rationale**: the explorer opens and closes ports with no round trip, so it needs the whole slice; the graph has a few hundred such elements at most. Endpoints only through actions (house rule). The helpers of `domain_events_diagram_action.py` (`_methods`, `_event_fields`, `_accent_by_domain`, `_action_domain_map`) already read all of it from DuckDB.
- **Alternatives**: extending `/events-diagram` (its shape is a diagram, with no domains without events and no actions without events); one request per port (a round trip per click, and Diff would need two per click).

## The old Events diagram

- **Decision**: remove `EventsDiagramViewer`, `eventsDiagram.ts`, `GetDomainEventsDiagramAction`, `GetAllEventsDiagramAction` and their routes; the sidebar rows `events_all` and `events_domain` and the page keys `events-all` and `events` stay, and both open the explorer — the domain row with that domain's events port open.
- **Rationale**: FR-001; two views of the same facts would drift. Keeping the page keys keeps old addresses and rooms working.

## Layout

- **Decision**: Graphviz `dot` (LR or TB) through the shared WASM loader, read back as `json`; nodes are HTML tables with one cell per port, so lines leave from ports; the client draws its own nodes (HTML) and lines (SVG) at Graphviz's positions. The first layer is kept in order by a `rank=same` chain of invisible edges. `ranksep` 2.8 (LR), `nodesep` 0.7 (TB).
- **Rationale**: proven on the demo; nodes with ports and pills are far easier as HTML than as Graphviz SVG; `dot` is what ERD and Use case use.
- **Alternatives**: Graphviz SVG with clickable cells (fragile hit targets, no per-port controls); a hand-made layered layout (crossings minimisation for free in `dot`).

## Pan and zoom

- **Decision**: reuse `useSvgPanZoom` with `fitToViewBox`, the line SVG sized to Graphviz's box inside the panner; add one function to the hook, `placeAt(clientPoint, contentPoint)`, so a clicked node can be held still after a new layout (FR-022).
- **Rationale**: FR-021 asks for ERD's gestures; the hook is them, and rooms already follow it (`useSvgDiagramSurface`).

## Filter panel

- **Decision**: generalize `ErdFilterPanel` to take a list of sections (`{ id, title, rows, paints }`), keeping its three-section props as a thin wrapper so ERD, Use case and the map do not change; the gear shift takes the painting sections from the list.
- **Rationale**: FR-016, FR-018; one panel everywhere (the maintainer: "on production as today, no check boxes").

## Page state

- **Decision**: page settings of the pages `events` and `events-all`: `mode`, `layout`, `domains`, `off`, `opened`, `paint`, `paint_diff`, `disabled_changes`; the server's room whitelist (`rooms/pages.py`) gets the same names, `opened` and `off` as lists of strings.
- **Rationale**: page settings already go into the address and into a room (spec 028, 038); a new name needs the whitelist too.

## Comparison

- **Decision**: in Diff, load the explorer payload of A and B and the graph comparison, merge them by id (B's where both have it), and mark each node and link with its status; a port's change counts are the changed nodes behind it plus the changed links it would draw, per status. Side by side draws each half's part of the same explored screen, as Use case does with `drawnOn`.
- **Rationale**: the comparison already reports events, `domain_event` and `@emits` edges (#334); `loadEventsDiff` does the same merge today.

## Test graph

- **Decision**: a fixture graph `packages/maxitor/web/tests/fixtures/graph-explorer.json` built from the shape of the demo data: domains of every coverage (vocabulary, empty vocabulary, emitting without one, none), events of every standing, an event held by two vocabularies, an event emitted across domains, actions without events, methods of all five kinds; and a second version differing by one event and one `@emits` edge for Diff.
- **Rationale**: the graph of `aoa-demo` holds two events only (spec, Assumptions).
