# Research: Maxitor Compares Two Versions on the ERD

Every decision below was checked against the code on 2026-10-30 (`main` at `a428e3a4`).

## R1. Where the comparison lives, and how it is installed

**Decision**: a new part of the `maxitor` package, `packages/maxitor/core/graph_compare/` with its own `src/maxitor/graph_compare/` and `tests/`, laid out like `tools/graph_builder/` (its own `pytest.ini`, `pythonpath = src`). It goes into the base install (no extra): `packages/maxitor/pyproject.toml` gains it in `only-include`, `dev-mode-dirs` and `[tool.hatch.build.targets.wheel.sources]`; the root `pyproject.toml` gains it in its source paths, `mypy_path`, the `typecheck` command and the per-path Ruff entry; `scripts/check_run.py` gains its test folder beside `maxitor/tools/graph_builder`.

**Rationale**: the maintainer's layout by kind reserves `core/` for code the app and the tools share (2026-10-29). The base install already holds `graph-builder`, which will use it (R3), so it cannot sit behind an extra.

**Alternatives**: inside the front (`maxitor.front.model.core`) — the tools could not use it without importing the front; a separate distribution — one package `maxitor` is the maintainer's decision.

## R2. The boundary

**Decision**: `scripts/package_boundaries.toml` gets `[standalone.graph_compare]` with `roots = ["packages/maxitor/core/graph_compare/src/maxitor/graph_compare"]`, `import_prefixes = ["maxitor.graph_compare"]`, `forbid = ["maxitor.front", "maxitor.repo_graph_port", "maxitor.graph_builder"]`. A standalone table already forbids every `aoa` import (`check_standalone`). A test of the module itself also walks its imports and accepts only the standard library (`sys.stdlib_module_names`) and itself — so a third-party import (say `jsonschema`) fails too, which the boundary checker does not catch. `[packages.maxitor]` and `[packages.repo_graph_port]` gain `"graph_compare"` in `may_import`; `[standalone.graph_builder]` may import it (it is not in its `forbid`).

**Rationale**: the issue asks for the boundary check; the existing standalone mechanism already enforces "nothing of `aoa`".

## R3. One engine, not two: `graph_builder.differences`

**Decision**: `maxitor.graph_builder.differences` becomes a formatter over `compare`: the same lines (`nodes[id=…].label: Shop → StoreDomain`, `edges[id=…]: added`), the same limit and `… and N more`. Its existing tests stay unchanged and must stay green; they are the proof that the output did not move. What `compare` does not cover — a difference in `schema_version` — the formatter writes as today (`schema_version: 1.0 → 1.1`).

**Rationale**: `differences.py` already compares two graph documents by `id` (for `graph-builder check`). Two engines that answer the same question would drift (memory: no duplicates). The protocol README's own example is that formatter's output.

**Alternatives**: leave it — two comparisons in one package, one of which ignores #285's rule for `1.0` edges.

## R4. The result's shape

**Decision**: `compare(a, b)` takes two parsed documents (`Mapping`) and returns a frozen `Comparison`: `nodes` and `edges`, each a mapping `id → ElementComparison(status, differences)` covering the union, and `counts` (added, removed, changed for nodes and for edges). A `Difference` is `(path, change, before, after)`: `path` a tuple of keys from the element's top (`("properties", "json_schema", "properties", "erid", "type")`), `change` one of `added`, `removed`, `changed`, `before`/`after` the JSON values (`None`-free: an absent side is marked by `change`). Differences are computed for every changed element at once.

**Rationale**: a changed element is rare (gameoffer 0.8.0 → 0.9.0: three changed of ~450), so computing them eagerly costs little and keeps `Comparison` immutable and simple to hold. A tuple path survives keys that contain dots; the formatter of R3 and the card join it for display.

**Rules** (FR-003, FR-004): an object is compared key by key, recursively; anything else — a list included — by equality. The fields compared are every field of the element but `id` (`label`, `type`, `relationship`, `is_dag`, `source_id`, `target_id`, `properties`), so a field the protocol adds later is compared without a code change.

## R5. `1.0` edge ids, without AOA

**Decision**: the module carries #285's rule as data — default `<source_id>|<type>|<target_id>`; `entity_relation` replaces the target by `properties.field_name`; `lifecycle_transition` appends `properties.from_state`; separator `|` — and applies it to every edge of a document whose `schema_version` is `1.0`. A `1.1` edge's own `id` is used as written. A missing or non-string part, a part containing `|`, or two edges with one id refuse the document with `GraphNotComparableError` naming the type and field, or both edges. An unknown `schema_version` is refused the same way (protocol §3: a consumer refuses a version it does not know). A test in the front's suite — which may import AOA — checks that the copied rule gives `aoa.action_machine.graph.edge_identity.edge_id` for every edge of the demo's `graph.json` with `id` removed.

**Rationale**: the module may not import AOA (FR-001); the keep-in-step test lives where both are importable.

## R6. How fast

**Measured**: parsing the demo's `graph.json` (4.4 MB, 3 213 nodes, 4 841 edges) takes ≈ 14 ms; indexing both sides by `id` and comparing equal elements ≈ 2 ms. **Decision**: the test compares two demo graphs (one with a few hundred edits made by the test) and requires under 1 second (SC-002) — far above the measurement, so a slow check-run machine does not flake, yet a quadratic mistake (comparing every element with every other) fails it.

## R7. The server holds the documents it compares

**Decision**: `GraphEntry` gains `document: str` — the graph's JSON text as `LoadAOAServiceAction` already produces it (`coordinator_json_raw`: the envelope unwrapped, or the bare graph). It is the same text the DuckDB build parsed, so the comparison and the diagrams describe one graph; `content_sha256` already identifies it.

**Rationale**: the DuckDB tables are normalised per type and drop fields the diagrams do not read; rebuilding a document from them would be lossy. Keeping the text costs about its size (4.4 MB for the demo) per held graph, bounded by the store's `max_graphs`.

**Alternatives**: download the version again for each comparison — a second port request per pair, and Live could move between the two reads.

## R8. Two sources in one read

**Decision**: the comparison reads are `GET /api/v1/compare?source=<B>&a=<A>` and `GET /api/v1/compare-element?source=<B>&a=<A>&kind=node|edge&id=<id>`. `GraphSourceMiddleware` already guards `source` (version access with the key header, build, refusals); for a path in `/api/v1/compare*` it guards `a` the same way and binds its entry to a second context variable (`current_base_entry()`). Both versions belong to the same history and travel with the same key header.

**Rationale**: every rule of spec 037 about keys, refusals and logs is enforced in one place already; a second, hand-written guard inside an action would be a second place to get them wrong. The reads stay AOA actions behind the adapter (house rule).

## R9. The comparison is held, once per pair

**Decision**: a new resource `ComparisonStore` (process memory) keyed by `(content_sha256 of A, content_sha256 of B)`, holding the `Comparison`, bounded (32 pairs, the one read longest ago leaving) and built under a per-key lock so two readers who arrive together compute it once (SC-009). Keying by content, not source, makes Live automatic: when the live graph is rebuilt its hash changes and the next read computes a new comparison (FR-020); an old pair is never wrong, only unused.

## R10. What the client asks, and where the ERD's union is made

**Decision**: the comparison read returns the counts and the status of every element that is **not** unchanged (unchanged is everything else in the union); the client draws the ERD from the two ERD reads it already knows how to make — `list-entities` for A and for B with the same domains — merged into one payload (`mergeErdPayloads`), and marks it with the statuses (`markErd`). The mapping from ERD things to graph ids is the protocol's own: a table is its `Entity` node; a scalar row is the `EntityField` node `<entity>:<field>` together with its `entity_field` edge; a relation row and its line are one `entity_relation` edge `<entity>|entity_relation|<field>` (#285). The button's counts are the marks of the drawn diagram, each element once (Assumptions of the spec).

**Rationale**: the ERD's layout, kinds, groups and dictionaries stay where they are built today; only marks are added. Sending only changed statuses keeps the read small (the demo's union is ~8 000 elements; a release changes tens).

**Alternatives**: a server-side "ERD diff" action — a second ERD builder to keep in step with `list-entities`.

## R11. A row's status

**Decision**: a scalar row takes the strongest status of its `EntityField` node and its `entity_field` edge (removed/added if either is; changed if either is). A field that only moved (its `ordinal` changed) is therefore changed, and its card says `ordinal 2 → 3`. A relation row takes its edge's status; when the edge's difference includes `target_id`, the line is drawn twice (FR-024) and the row's type reads `~~OldTarget~~ → NewTarget`.

## R12. Drawing the marks

**Decision**: `buildDotSource` reads an optional `diff` on entities, fields and relations: added — green frame and header, `+` in the header; removed — red, dashed frame (`STYLE="ROUNDED,DASHED"` on the card's `<TABLE>`; Graphviz takes a comma list there — the first task of the ERD phase proves it on the WASM build the client ships, and falls back to a dashed node outline behind the label if it does not); changed — amber; unchanged — the domain colour at reduced opacity. Rows get a small `+ − ~` marker cell and a tint. A retargeted relation emits two edges: solid amber to B's target, thin dashed amber to A's target. The SVG post-pass already finds cells by id (`erdCellId`); the card opens from the same ids. The table-style check (`check-erd-table-style.ts`) gets cases for each mark.

## R13. The range on the track

**Decision**: the rules of FR-010–FR-013 are a pure module `lib/versionRange.ts` (`moveHandle`, `dropHandle`, `stepHandle`, `shiftBoth`, `oneToDiff`, `normalise`), unit-tested on its own; `VersionTrack` gets a `range` mode that draws two handles and the dark stretch and calls it. Handles are named by position (`left` = A, `right` = B) at each render, so a drag past the other just changes which index is smaller.

## R14. The address bar and the room

**Decision**: `urlState` gains `a` and `mode` (`mode=diff` only in Diff); `b` stays. The room's `version` message gains `a` (`null` in One) — `{"type": "version", "a": "<sha>"|null, "b": "<sha>"|"live"}` both ways — so mode, A and B travel as one value and two changes at once end with the last (FR-016). `SetRoomVersionAction` checks the range rules on the server too (A older than B, not equal, Live never A) and refuses a broken one to its sender.

## R15. The left panel in Diff

**Decision**: the client reads the sidebar of A and of B (`/api/sidebar?source=…`, both held already) and merges them by page key; a page in one only gets `+` or `−` (`mergeSidebars`). Opening it reads that page's ERD for both; the side that lacks it contributes nothing, so everything is added or removed.

## R16. Messages

**Decision**: `VersionMessage` is reused twice side by side; a new `VersionsBetween` lists the versions strictly between A and B, newest first, each a row with its first line that opens to the whole `VersionMessage`. On a phone the two stand one under the other (CSS only).

## R17. The other diagrams in Diff

**Decision**: until #291–#293, the full graph, use cases and lifecycles show B as in One and the button names the range without counts (spec, Assumptions).

## R18. Live as B

**Decision**: nothing new on the server (R9). On the client, the existing freshness signals — the 30-second fingerprint outside a room, `graph_changed` in a room — already fire for Live's source; in Diff they also re-read the comparison and B's ERD slices.
