# Research: spec 043

## R1. Where a field's description lives

- **Decision**: Protocol 1.2: entity fields, lifecycles, roles and `@connection` links may carry `description`. Everything else that declares one already did.
- **Rationale**: The text existed in the model and was dropped when the graph was built; the schema is `additionalProperties: false`, and a published version never changes. An audit of every node and edge type found these four. `Params`, `Result`, `Checker`, `Sensitive`, `PropertyField` and states declare no description.
- **Alternatives**: Editing 1.1 breaks the protocol's own rule. A side file breaks "the graph is the one source".

## R2. How the ERD knows a field is a lifecycle

- **Decision**: `list-entities` adds `lifecycle_id` to a row, from a `LEFT JOIN` on the `lifecycle` table by `<entity>:lifecycle:<name>`.
- **Rationale**: That is the vertex's defined id (`LifeCycleGraphNode` CONTRACT), so no guess by type name. `mergedFields` spreads a row, so Diff carries it.
- **Alternatives**: The type's name ending in `Lifecycle` is a guess and not language-neutral.

## R3. One read for a card

- **Decision**: `GET /api/v1/element-card?kind=node|edge&id=`, an action reading the `nodes` or `edges` view of the version the read names. Answers `{kind, id, type, label, description, lifecycle_id}`.
- **Rationale**: The map holds no description; a table's and a lifecycle's come the same way. In Diff the client asks B and, if absent, A.

## R4. One path for a person and a follower

- **Decision**: `useGraphvizFocus` takes an optional `onCard` callback and a test for which refs have a card; those show no label. The own-mouse effect and the follower effect both call it. `useHoverCard` holds the delay and the stay.
- **Rationale**: The follower replay already exists; a second channel would drift. When the pointer enters the card the hook reports the ref again, so a follower's card stays too.

## R5. Copy and the phone

- **Decision**: `bindNameCopy` loses its skip and ignores touch; the ERD's `pointerup` card is removed; a touch tap opens the card through the same hook, and the card has a copy button on touch.

## R6. Collapse state

- **Decision**: Page settings `fields_collapsed` (switch) and `fields_except` (list of table ids that differ from it), in `viewUrl` as `collapsed` and `except`.
- **Rationale**: Page settings are already address plus room. Exceptions keep the address short (FR-027), and a table arriving later follows the switch (FR-026). A list of collapsed ids would grow with the diagram.

## R7. Rows keep their index

- **Decision**: `buildDotSource` skips a hidden row but keeps its index in the cell id.
- **Rationale**: `erdDiffCard`, `markRows` and the room's row refs address rows by index in `fields`.

## R8. The control and the view

- **Decision**: A cell `a_cl<table>` in the header, present only where a row would hide, with a `▸`/`▾` glyph; a click is handled like a name. A collapse keeps the view and shifts it so the header stays under the pointer; `prevDrawingRef` does not refit for a collapse change.
- **Rationale**: `drawnData` does not change on a collapse, since the collapse is an input to the DOT only, so no refit occurs by itself.

## R9. Same layout

- **Decision**: `check-layout-determinism.ts` opens the all-domains ERD with `collapsed=1` once, as an added page.

## R10. Miniature

- **Decision**: `lifecycleMiniature(id, read key)` returns a kept promise of SVG text from `loadLifecycle` or `loadLifecycleDiff` and `buildLifecycleFsmDotSource`, read before the viewer's filters. Its `width` and `height` are dropped so the `viewBox` fits the card.
- **Key**: active source and base source, so another version draws anew.

## R11. The map

- **Decision**: `MapEngine.showHover` raises `onHoverElement` in place of the label for a real node; `enterEdge` on a real link does the same; bundles and centres keep their label. `reportHover` gains the edge. The click paths stay (FR-012a).
