# Research: Entity Kinds Travel with the Graph, and the ERD Shows Every Line It Should

Every decision below was checked against the code on 2026-10-26; where a probe was run, its result is quoted.

## R1. Where the display name is declared

- **Decision**: Each kind base declares `KIND_LABEL: ClassVar[str] = "Association"` in its own body. `BaseEntity.__init_subclass__` already recognises a kind base (`_is_kind_base`: inherits `BaseEntity` directly and defines its own `__init_subclass__`); for such a class it additionally requires `"KIND_LABEL" in cls.__dict__` with a non-empty, stripped string, else `DeclarationStructureError` naming the class. `entity_kind_label_of(entity_cls)` sits beside `entity_kind_of` and reads `KIND_LABEL` from the same base `entity_kind_of` finds.
- **Rationale**: The name lives on the class that declares the kind, like the word does; no registry. `cls.__dict__` refuses a label inherited from a mixin, so each kind states its own.
- **Alternatives considered**: Deriving the name from the class name (cannot produce "Association" from `Assoc`); a table of names in the engine or in Maxitor (rejected in issue #239 §7.3 — it makes other producers' kinds second-class); the docstring's first line (fragile, not a contract).

## R2. The wire contract

- **Decision**: In `graph_json_schema.py`, `entity_kind` keeps `type: string`, `minLength: 1`, gains `pattern: ^[a-z][a-z0-9_]*$`, loses `enum`; a new `entity_kind_label` property is `type: string`, `minLength: 1`, not in `required`. The conditional branch "if `entity_kind` is `enum`, `values` is required" stays.
- **Rationale**: The word stays mandatory and malformed words still fail loudly; the label is optional so producers without names stay valid.
- **Alternatives considered**: Requiring the label (breaks every non-AOA producer and old exports); dropping the pattern (would admit `Core` and `core entity`, which the acceptance criteria reject).

## R3. Loading kinds in Maxitor

- **Decision**: `_fill_table_entity` reads `p.get("entity_kind")`: missing or blank → `"unknown"`; non-string → `ValueError` naming the node id. Same for `entity_kind_label`, with missing or blank → `NULL`. The `entity` table gets `entity_kind_label VARCHAR` (nullable); the `nodes` view's `json_object` includes it, so the reconstructed node payload carries it.
- **Rationale**: FR-005; an old export or a foreign graph loads and stays visible.
- **Alternatives considered**: Dropping rows without a kind (hides data); guessing `core` (invents a kind — rejected by issue #239 §7.1).

## R4. `list-entity-kinds`

- **Decision**: `ListEntityKindsAction` modelled on `ListDomainsAction`: `SELECT entity_kind, MIN(NULLIF(trim(entity_kind_label), '')) AS label FROM entity WHERE id NOT LIKE 'tests.%' AND strpos(id, '<locals>') = 0 GROUP BY entity_kind ORDER BY lower(entity_kind)`; a `NULL` label becomes the word with its first character upper-cased, in Python. Route `/api/v1/list-entity-kinds` beside `/list-domains`. Rows: `{entity_kind, label}`; no colour, no count.
- **Rationale**: FR-006, FR-007; the same exclusion rule as domains.
- **Alternatives considered**: Colour per kind (the maintainer chose one grey); counts (rejected on the mockup).

## R5. Lines between tables on screen

- **Decision**: In `relation_sql` and the reference half, drop `WHERE er.source_id IN domain_entity OR er.target_id IN domain_entity`; the joins on `selected_entity` for both ends already express "both on screen". `parent_entity_sql` gets the same `selected_entity` CTE instead of `domain_entity` for both ends. `ListEntitiesAction` additionally computes one request-wide list `relations` over the union of all requested slices' `selected_entity` sets, with the same row shape, at the top level of the result beside `domain_slices`. The merged all-domains ERD draws that list, pruned to the tables on screen; a single slice keeps using its own list.
- **Rationale**: Reproduced on 2026-10-26: neighbour↔neighbour relations and generalizations are dropped per slice, and a cross-slice line (`OfferCoreEntity`–`IndustryEnumEntity`) exists in no slice. The `fk` rows already join `selected_entity` on both ends, so a card's FK rows and its lines will agree.
- **Specialization axis → dictionary**: each `entity_specialization_edges` group (head, field) whose `dictionary_qualname` is an entity in `selected_entity` yields one row `{source: head, target: dictionary, relationship_kind: "reference", source_field: field_name, target_field: null, source_cardinality: "zero_many", target_cardinality: "one"}`, in the per-slice and the request-wide lists. Checked on the reference graph: one axis, `UserEventCoreEntity.kind` → `EventKindEnumEntity`; no other edge joins the two.
- **Alternatives considered**: Client-side reconstruction from FK rows (FK rows carry no inverse and no references); asking for every domain's slice always (costs payload for no reason).

## R6. One line per association

- **Decision**: Pair in SQL: a relation row `r` and the row `i` with `i.source_id = r.target_id AND i.field_name = r.inverse_field AND i.target_id = r.source_id` are one association. The canonical row is the one whose field has cardinality `one` (the FK holder); for one-one or many-many, the one with the smaller `source_id`, then the smaller `field_name` (self-relations). Output adds `source_field` (canonical field) and `target_field` (inverse field or `NULL`); `source_cardinality` / `target_cardinality` keep today's vocabulary (`one`, `zero_many`): target end = canonical field's cardinality (`one` → `one`, `many` → `zero_many`); source end = inverse field's cardinality, or today's derived value when there is no inverse. `label` stays.
- **Rationale**: On the admingameoffer graph: 46 relation fields → 34 associations, every declared inverse finds its partner, and only `OfferRequestCoreEntity` ↔ `OfferRequestItemDetailEntity` keeps two lines (`chosen_offer` has no inverse). The canonical rule gives the same direction on every load (FR-025).
- **Alternatives considered**: Pairing in the client (needs `inverse_field` on the wire and duplicates logic for the request-wide list); merging every relation of a pair (hides `chosen_offer`; rejected in the spec).

## R7. Drawing the ends

- **Decision**: Association edges get `dir=both`, `arrowhead` and `arrowtail` = `tee` for `one`, `crow` for `zero_many`, `headlabel` = `source_field` (the role at the target end), `taillabel` = `target_field` (the role at the source end, empty when absent), `labelfontsize=9` (today's label size), and no `label`. Generalizations keep `arrowhead=empty`; references get the same ends from their cardinalities and the field name as `headlabel`.
- **Rationale**: Probe on the client's WASM Graphviz: `dir=both arrowtail=crow arrowhead=tee headlabel=… taillabel=…` renders both roles. Graphviz routes parallel edges between the same nodes apart, so two associations of one pair stay distinct (FR-026, checked in the ERD check).
- **Alternatives considered**: Custom SVG markers in the post-pass (re-implements what Graphviz draws natively, and diverges from production look).

## R8. Addressable cells

- **Decision**: A cell the post-pass must find carries `ID` **and** `TOOLTIP`. Probe on WASM Graphviz 1.21: `ID` alone leaves no id in the SVG; `ID` + `TOOLTIP` (or `HREF`) gives `<g id="<node>_<ID>"><a xlink:title="…">` wrapping the cell's `<polygon>` fill and its `<text>`. Name cells use `TOOLTIP="Click to copy"`; the kind slot uses the kind's label; type cells use the type text.
- **Rationale**: One mechanism serves FR-017 (icon tooltip), FR-029 (marking by text) and FR-034/FR-037 (copy targets and their tooltip).
- **Alternatives considered**: Locating rows by coordinates (fragile across layouts); `HREF` (turns cells into links, changes cursor and keyboard focus).

## R9. Header icon and minimum width

- **Decision**: The header stays one `TD` with the domain colour and `WIDTH="210"`; inside, a borderless nested table holds the icon slot (fixed width and height, `ID` + `TOOLTIP`) and the name cell (`ID` + `TOOLTIP`), centred together. The post-pass inserts the white glyph into the slot's box. The `spec` glyph is drawn at 80 % of its box with the stroke widened by 1/0.8.
- **Rationale**: Probe with the production markup: header fill is a plain rectangle with or without `WIDTH`; `containNodeFills.ts` rounds it by trimming every fill to the card contour, so the minimum width and the nested table keep the rounded corners. `GenderEnumEntity` 122.4 → 212 pt, a `NotificationEntity`-shaped table 138.9 → 212 pt, heights unchanged. Fills inside `<a>` wrappers already exist today (the specialization type cell has a `TOOLTIP`) and the containment check passes, so `readCards` handles them; the new ERD check asserts it again.
- **Alternatives considered**: Splitting the header into coloured cells (fills would not be one band; risks the trimming); Graphviz `IMG` (WASM cannot load image files).

## R10. Type column

- **Decision**: `buildDotSource.ts` stops appending the `reference_qualname` suffix and sets `ALIGN="RIGHT"` on type cells; the server's `fk` rows return `target.label` as `type`. The module docstring and example comment in `list_entities_action.py` that quote `FK -> …` are updated.
- **Rationale**: FR-031, FR-032; nothing pins the old text (searched tests and docs).

## R11. Line hover

- **Decision**: The post-pass clones each `g.edge`'s path into a transparent hit path (`stroke-width: 10`, `pointer-events: stroke`) inside the same group; CSS on `g.edge:hover` sets the visible path's stroke to `#475569` and width 2.4, the arrowheads' fill and stroke to the same colour, and the role labels to bold `#334155`. On `mouseenter` the edge group is re-appended to its parent (drawn on top). Transitions of ~100 ms are disabled under `prefers-reduced-motion`.
- **Rationale**: FR-027, FR-028; CSS keeps the hover state out of React.
- **Alternatives considered**: Widening the visible stroke permanently (changes the production look).

## R12. Marking fields

- **Decision**: Each association row in the payload already names `source`, `target`, `source_field`, `target_field`. The post-pass builds a map from (table, field) to the `<g>` ids of that field's name and type cells (both its own row and its FK row). On edge hover it sets `font-weight: bold` and the darker fills (`#0f172a` name, `#334155` type) on those `<text>` elements; with no `target_field`, it marks the target's key rows (`primary_key`). Leaving restores them. No `<polygon>` is touched.
- **Rationale**: FR-029: the mark is the text only. Row hover reuses the same map in reverse: (table, field) → the edges whose `source_field` or `target_field` it is, plus, for a key row, the edges without `target_field` pointing at its table.

## R13. Copy

- **Decision**: Delegated pointer handlers on the SVG: on `pointerdown` remember the point; on `pointerup` within 4 px on a name cell (`g[id$="_hn"]`, `g[id*="_fn_"]`), call `navigator.clipboard.writeText(name)` and show an MUI `Snackbar` "Copied <name>" for 1.5 s, anchored bottom-centre above the zoom toolbar; on rejection, select the `<text>` node's contents and show "Selected <name> — press Cmd/Ctrl+C". Name cells get `cursor: copy`.
- **Rationale**: FR-034–FR-037; the pan handler of `useSvgPanZoom` already distinguishes drags, the 4 px rule matches it.
- **Alternatives considered**: `document.execCommand("copy")` (deprecated).

## R14. Filter panel

- **Decision**: New `components/ui/ErdFilterPanel/` with its README, using `floatingLegendPanelSx` / `legendRowSx` / `legendDiskImgSx` / `legendRowLabelSx` for the chrome; `width: 148px` fixed; `maxHeight: calc(100% - 12px - <zoom toolbar bottom 10 + its height + 12>)`; `overflowY: auto; overscrollBehavior: contain`. Sections are buttons with a chevron and the small-caps title; open section in component state, `"domains"` on mount. Labels `noWrap` with an MUI `Tooltip` shown only when `scrollWidth > clientWidth`. On `sm` and below the panel starts as a "Filter" pill; opened, the close button sits at the end of the first section header. Domain rows reuse today's disk; kind rows use a grey `#94a3b8` disk drawn like `svgDataUriForGraphNodeIcon` with the kind glyph.
- **Rationale**: FR-008–FR-014; same chrome as production.

## R15. Kind filter state

- **Decision**: `ErdGraphvizCanvas` keeps `enabledEntityKinds` beside `enabledDomains`, persisted in a module-level `Map` keyed by `diagramResetKey` like `enabledDomainsByDiagramKey`; applied after the domain merge together with `filterGraphByEntityQuals`; relations and containers pruned once at the end.
- **Rationale**: FR-015; the existing pattern.

## R16a. Specialization container

- **Decision**: The cluster in `buildDotSource.ts` becomes `style="rounded,dashed,filled"`, `fillcolor="#0f172a0d"`, `penwidth=2`; colour `#94a3b8`, `fontsize=10`, `margin=12` and the label stay.
- **Rationale**: Probe on WASM Graphviz 1.21: the SVG path gets `fill="#0f172a" fill-opacity="0.05"` and `stroke-width="2"`; the canvas pattern shows through. No post-pass touches clusters.
- **Alternatives considered**: An opaque light-grey fill (hides the canvas pattern and is removed by the backdrop sanitizer's light-fill rule); a darker outline colour (changes the production look beyond what was asked).

## R16. Reference data and palette

- **Decision**: The admingameoffer `graph-json` fetched on 2026-10-26 is byte-identical (SHA-256 `a9d73e90…f84cf`) to the copy already frozen as `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz`; that file is the reference, not a second copy. Backend tests build their expectations from a reduced fixture shaped like it (two neighbours joined to each other, a neighbour specialization, a cross-slice pair, a field with an inverse and one without). Slate `#64748b` is replaced by `#f97316` at position 8 of `_EXTRA_LIST_DOMAIN_COLORS` and `ENTITY_COLORS`.
- **Rationale**: Counts in the spec must not move with the live service; FR-019.

## R17. Before and after, against production (2026-10-27)

Compared on the same source (`https://admingameoffer.aoa.run/graph-json`, byte-identical to the frozen reference graph) and the same views — `EventsDomain` with 1-hop and the all-domains ERD — between `https://maxitor.aoa.run` and a local build of this branch (`uv run uvicorn aoa.maxitor.api.app:app` on 8000, `npm run dev` on 5173; the demo package is not started). Every visible difference, and the requirement that names it:

| Difference | Named by |
|---|---|
| One filter panel with Domains and Kinds instead of the Domains legend | FR-008–FR-014 |
| A white kind icon right before every table name, the two centred together | FR-016, FR-017 |
| Small tables 212 pt wide (`GenderEnumEntity`, `EventKindEnumEntity`, `PlatformEnumEntity`) | FR-033 |
| Types on the right edge; no `→ <Dictionary>`, no `FK -> ` | FR-031, FR-032 |
| The specialization container half a tone darker, outline 2 px | FR-020 |
| 40 lines on the all-domains ERD (34 associations, 5 generalizations, 1 axis line) instead of 46 relation lines plus references; roles at the ends, crow's-foot ends, no middle labels | FR-021–FR-026 |
| `UserEventCoreEntity` → `EventKindEnumEntity` (`kind`) now drawn | FR-021 |
| The layout itself moved: Graphviz lays out a graph with fewer edges differently | consequence of FR-023 |

Unchanged as required (FR-038): fonts (Helvetica 11/12 pt), cell padding, row tints, domain colours of the first seven domains, rounded outlines, the zoom toolbar, the sidebar.

Two defects were found by this comparison and fixed in the same phase:

- **The canvas lost every listener on the drawing the user sees.** Production and this branch alike: `g.node` had no `cursor: pointer` and the SVG no `style.width` — React re-applied `dangerouslySetInnerHTML` on every render of the canvas (one zoom click is enough) and replaced the SVG, so the table hover never worked on the real page. The canvas now places the markup itself in its layout effect; after a zoom click the SVG, its size, the table hover and the new line hover are all still there.
- **The fixed width cut a common name.** The production panel is as wide as its content: 148 px on this graph's `EventsDomain` ERD, where `ShowcasesDomain` needs a 98 px label; the 146 px taken earlier from an older screenshot cut it to `ShowcasesDom…`. The fixed width is 148 px.
