# Research: Maxitor Compares Two Versions on the Full Graph

Each decision was checked against the code on 2026-10-31.

## R1. Edges get the protocol's id on the server

- **Decision**: `FullGraphAction` gives each edge the protocol's `id`, computed by the rule in `maxitor.graph_compare` from what the `edges` view holds (its `type`, ends and `payload`). `e-<index>` goes away.
- **Rationale**: the comparison is keyed by this id, and FR-001 forbids matching by position. DuckDB's edge tables have no id column, and the rule's one copy outside AOA already lives in `graph_compare`.
- **Alternatives**: a second id field beside `e-<n>`: two ids for one thing. Matching on source, target and type on the client: wrong for a retargeted relation, whose id is kept by design.
- **A graph the rule refuses** (`1.0` only): an edge whose id cannot be computed, or whose id collides, keeps `e-<index>`, so One opens as today; the comparison refuses that pair by itself.
- **Check**: the layout's input and the fingerprint read ends and types, not ids, so the golden hash must not move. A test compares the answer's ids with the graph document's for every edge of the demo graph. The rule needs `field_name` and `from_state`: confirm in the first task that the view's `payload` carries both; if not, add them to the view.

## R2. The union is built on the client, like the ERD's

- **Decision**: in Diff the viewer reads `fullGraph()` for B, `fullGraph(base)` for A and `compareVersions()` at once, and a pure function `unionFullGraph(older, newer, compared)` in `lib/fullGraphDiff.ts` merges them. No new endpoint.
- **Rationale**: the same pattern as `loadErdDiffBundle`; both graphs are already held and cached; a pure function is easy to pin.
- **Alternatives**: a union action on the server: one more cached object per pair, for no gain.

## R3. The order of the union

- **Decision**: each node's answer gains `data.type_slug`, DuckDB's `type`, because `node_type` is the interchange name (`EntityField`, not `entity_field`) and sorts differently. Nodes sort by `(lower(type_slug), lower(title), id)`, edges by `(source, target, type, relationship)`, the action's two orders, by code point (`<`, never `localeCompare`, which differs by engine).
- **Check**: the union of a graph with itself is, node for node, the action's own order. Non-ASCII labels are the one way `toLowerCase` and DuckDB's `lower` could differ; the same test runs on a label with one.

## R4. A retargeted relation in the union

- **Decision**: one edge, its B end, plus a companion edge `<id>#was` to its A target, flagged `was`. Both enter the layout, so the old target stays nearby; only the first is counted or carries the status.
- **Rationale**: FR-009 asks for two lines and one element. G6 needs a distinct id per line.

## R5. Marks live in the node's and edge's data

- **Decision**: `unionFullGraph` writes `data.diff`; `buildGraph`'s style functions read it. Hover's `hub` and `nb` states stay as they are, and they already set `opacity: 1`, so a hovered faded node brightens.
- **Rationale**: the hover code replaces a node's state list, so marks kept as states would be wiped.
- **Values** (mockup): a 2.4 px ring in the green and amber of the ERD's marks; removed: white fill, dashed red stroke; unchanged node opacity 0.28, edge 0.35.
- **"No changes" under a filter**: FR-016c can turn the fading off without a redraw of the layout: `graph.updateData` with `data.diff` cleared, then `draw`; positions are not touched.

## R6. Filters hide, they never lay out

- **Decision**: visibility only (`graph.hideElement` / `showElement`), as the comment in `FullGraphViewer.tsx` already promises ("hiding nodes changes visibility only"). A pure `visibleGraph(union, off, membership)` returns the nodes and edges to show. An edge shows when both ends do.
- **Settings**: `usePageSetting` under `disabled_node_types`, `disabled_domains`, `disabled_changes`, the last the ERD's name, so a room and the address get them the ERD's way (check `lib/viewUrl.ts` lists them).
- **Domain membership**: `buildDomainBubblePlugins`'s member computation moves into an exported `domainMembers(payload)`, used by both. It already follows containment, so a node can be in several domains; a node in none is never hidden by this filter.
- **Hulls**: confirm in the task that a bubble set redraws over shown members only; if it does not, its `members` are updated when the filter changes.

## R7. The panel

- **Decision**: reuse `ErdFilterPanel` with `paint={null}`, adding a `kindsTitle` prop ("Node types"; default "Kinds"). `NodeTypeLegend` goes when nothing imports it. Rows are dimmed, not removed, as on the ERD.
- **Alternatives**: a second panel: two accordions to keep alike.

## R8. The counts

- **Decision**: `setDiffCounts` with the drawn nodes' counts. `DiagramCounts` gains `edgesMarked: boolean`, so the button tells "only edges changed" (FR-013) from "no changes". The ERD passes `false` and is unaffected.

## R9. The cross-engine check over a union

- **Decision**: `check-layout-determinism.ts`'s server also answers a tiny history of two versions: the reference graph, and the reference graph with a fixed edit (nodes and edges added and removed, a relation retargeted). The full graph opens in Diff, and `data-layout-hash` is compared as for any page. A vitest golden hash pins the same union.
- **Rationale**: no test code in production; a port's three read endpoints are small to serve.

## R10. The card

- **Decision**: `node:click` on a node with `data.diff` opens `DiffCard` with a `CardTarget` for that node id; the rest of the card, closing and Live following, are spec 038's.

## R11. The stand

- **Decision**: `.demo-history/build_erd_full.py` gains the cases the spec lists, keeps the first twelve versions' changes, and rewrites `erd-full.url`. It stays out of git. Rebuilding changes the commit hashes, so the link changes too.
