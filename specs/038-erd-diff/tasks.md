# Tasks: Maxitor Compares Two Versions on the ERD

**Input**: Design documents from `specs/038-erd-diff/`

**Prerequisites**: plan.md, spec.md (US1–US7, FR-001 – FR-034), research.md (R1–R18), data-model.md, contracts/ (graph-compare.md, maxitor-api.md, room-protocol.md, ui.md), quickstart.md, checklists/requirements.md

**Tests**: Required. Every new test is verified adversarially: break the code the way the test must catch, confirm that test fails and no other does, restore, and record the break here.

**Organization**: one phase = one commit. Commit 1 holds the design documents; commits 2–9 are #290's phases 1–8; #290's phase 9 is three commits (check run, documentation, changelog), commits 10–12. A commit is made only on the maintainer's word (constitution I). The full check run is run after code changes only, not after documentation edits.

**Issue checkboxes**: commit 2 → phase 1; 3 → 2; 4 → 3; 5 → 4; 6 → 5; 7 → 6; 8 → 7; 9 → 8; commits 10–12 → phase 9 (ticked after commit 12). Every tick carries its sha (`gh issue edit 290`, the body fetched and checked for length before it is written back).

**Paths**: `M` = `packages/maxitor`, `GC` = `M/core/graph_compare`, `GCS` = `GC/src/maxitor/graph_compare`, `GCT` = `GC/tests`, `GB` = `M/tools/graph_builder/src/maxitor/graph_builder`, `F` = `M/front`, `FS` = `F/src/maxitor/front`, `FT` = `F/tests`, `FC` = `F/client/src`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story of spec.md (US1–US7)
- Every new Python module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every public function, class, action and resource carries an AI-CORE block (IV); every class, function and method a one-line docstring (V), TypeScript included. Every new client component folder has `index.ts` and a `README.md` beside it. Every endpoint is an action. No key and no whole address in a URL, a log or an error (spec 037, FR-010b, FR-011 – FR-011b).

---

## Phase 1: Setup — design documents (commit 1)

- [X] T001 Prepare commit 1 with `specs/038-erd-diff/` only (spec, plan, research, data model, contracts, quickstart, `checklists/requirements.md`, tasks; `tasks.ru_draft.md` stays out): `docs(spec): specify comparing two versions on the ERD (#290)`.

---

## Phase 2: The comparison of two graphs (commit 2) · US1 — #290 phase 1

**Goal**: `maxitor.graph_compare.compare(a, b)` — a status for every element, every difference by property path, the counts; `1.0` edges get #285's ids; standard library only (FR-001 – FR-008; research R1–R6; contracts/graph-compare.md).

**Independent test**: `uv run pytest GCT M/tools/graph_builder/tests -q`; the demo pair under 1 s.

- [X] T002 Baseline: `bash scripts/run_checks_with_log.sh` on the branch after commit 1; record the `OK` count and wall time here. **Recorded**: run at `3e286588` (commit 1): 41 of 41 steps `OK`, no `FAIL`; wall time 74.4 s; no file changed.
- [X] T003 Create the part (research R1): `GC/README.md` (what it compares, the result, the refusals, "standard library only"), `GC/pytest.ini` (`testpaths = tests`, `pythonpath = src`, as `M/tools/graph_builder/pytest.ini`), `GCS/__init__.py` exporting `compare`, `Comparison`, `ElementComparison`, `Difference`, `Counts`, `Status`, `Change`, `GraphNotComparableError`, and `GCS/py.typed`. Register it: `M/pyproject.toml` — `core/graph_compare/src/maxitor` in `only-include`, `core/graph_compare/src` in `dev-mode-dirs` and in `[tool.hatch.build.targets.wheel.sources]` mapped to `""`; root `pyproject.toml` — the source path beside `packages/maxitor/tools/graph_builder/src` (line ~122 and ~414), `mypy_path`, the `typecheck` command, and a per-path Ruff entry like graph_builder's if the same rule needs it; `scripts/check_run.py` — its test folder beside `"maxitor/tools/graph_builder"`. **Recorded**: as planned; no per-path Ruff entry was needed (the refusal's name ends in `Error`). The package's comment on its folders names `core/<name>/`.
- [X] T004 Boundaries (research R2): `scripts/package_boundaries.toml` — `[standalone.graph_compare]` with `roots = ["packages/maxitor/core/graph_compare/src/maxitor/graph_compare"]`, `import_prefixes = ["maxitor.graph_compare"]`, `forbid = ["maxitor.front", "maxitor.repo_graph_port", "maxitor.graph_builder"]`; add `"graph_compare"` to `may_import` of `[packages.maxitor]` and `[packages.repo_graph_port]`. Check that `scripts/check_package_boundaries.py` maps the new prefix (it reads every standalone table's `import_prefixes`). **Recorded**: the checker maps the new prefix as it is; `check_package_boundaries.py` passes.
- [X] T005 [US1] `GCS/comparison.py` (data-model "The comparison"): `Status` (`StrEnum`: `added`, `removed`, `changed`, `unchanged`), `Change` (`added`, `removed`, `changed`), frozen dataclasses `Difference(path: tuple[str, ...], change: Change, before: Any, after: Any)`, `ElementComparison(status: Status, differences: tuple[Difference, ...])` — "`differences` is non-empty exactly when `status` is `changed`", `Counts(added: int, removed: int, changed: int)`, `Comparison(nodes: Mapping[str, ElementComparison], edges: Mapping[str, ElementComparison], node_counts: Counts, edge_counts: Counts)` with read-only mappings (`MappingProxyType`); `GraphNotComparableError(ValueError)`.
- [X] T006 [US1] `GCS/edge_ids.py` (research R5): the rule as data — `_MEMBER = {"entity_relation": "field_name"}`, `_SUFFIX = {"lifecycle_transition": "from_state"}`, separator `|`; `edge_id(row) -> str` gives `<source_id>|<type>|<target_id>`, the member in place of the target, the suffix appended; a missing, empty, non-string part or one containing `|` raises `GraphNotComparableError` naming the edge type and the field. Its header says it is a copy of #285's rule (`aoa.action_machine.graph.edge_identity`) kept in step by T010.
- [X] T007 [US1] `GCS/compare.py` — `compare(a, b) -> Comparison` (research R4, R5): refuse a `schema_version` other than `"1.0"`/`"1.1"`, missing or non-list `nodes`/`edges`, an element without a string `id` (any node, a `1.1` edge — naming its position and kind), two nodes or two edges with one id (naming the id); index each side by id (`edge_id` for every edge of a `1.0` document; a `1.1` edge's own `id`); the union gets added / removed / changed / unchanged; an element's fields compared are all but `id`; `_walk(before, after, path)` recurses into objects key by key, yields `added`/`removed` for a key on one side, `changed` for a leaf that differs, and compares anything else — lists included — as one value; counts per kind. Pure; no I/O; standard library only. **Recorded**: a refusal names the side, `Graph A` or `Graph B`; the union keeps A's order, then B's new ids.
- [X] T008 [P] [US1] `GCT/test_compare.py` with small hand-written graphs: every status (one added node, one removed, one changed label, one unchanged); two edges between the same two nodes with different types get their own statuses; an `entity_relation` whose `target_id` changed is one changed edge with the difference `("target_id",)` and both values; a nested property (`properties.json_schema.properties.erid.type`) named by its full path, and a nested key added and removed; a list property compared as one value (its path ends at the property); a rename is one removed plus one added; two equal graphs — all unchanged, counts zero; an element moved within its array is unchanged; a `1.0` graph against a `1.1` graph of the same model — all unchanged; each refusal of contracts/graph-compare.md with its message. **Recorded**: `GCT/test_graph_compare.py`, 19 tests (10 of them the parametrised refusals); file names carry `graph_compare` because each tests folder is a package `tests`.
- [X] T009 [P] [US1] `GCT/test_boundary.py`: walk every module under `GCS` with `ast` and accept only imports in `sys.stdlib_module_names` or of `maxitor.graph_compare` itself. `GCT/test_speed.py`: load `packages/aoa-demo/graph.json`, make B by changing a few hundred elements (labels, a nested property, retargeting `entity_relation` edges, removing and adding nodes), compare, and require under 1 s (SC-002); also assert the counts equal the edits made. **Recorded**: `GCT/test_graph_compare_boundary.py`, `GCT/test_graph_compare_speed.py` (330 node edits, 50 retargeted relations, removed nodes' edges counted): 0.12 s including the deep copy and both parses.
- [X] T010 [P] [US1] `FT/test_edge_rule_in_step.py` (the front's suite may import AOA): for every edge of `packages/aoa-demo/graph.json` with `id` removed, `maxitor.graph_compare.edge_ids.edge_id(row) == aoa.action_machine.graph.edge_identity.edge_id(row)`, and equals the written `id`. **Recorded**: also asserts the demo has both special edge types, so the test cannot pass vacuously.
- [X] T011 [US1] `GB/differences.py` over `compare` (research R3): keep the signature `differences(old, new, limit=20)` and the lines `nodes[id=…].<path>: <before> → <after>`, `nodes[id=…]: added|removed`, `edges[id=…]…`, the `SHOWN_CHARACTERS` shortening and `… and N more`; a `schema_version` difference stays written as `schema_version: 1.0 → 1.1`; a document `compare` refuses falls back to the generic walk so `graph-builder check` still explains a malformed file. Order as today (nodes first, by id; then edges). `M/tools/graph_builder/tests/test_differences.py` must pass **unchanged**; if a line moves, fix the formatter, not the test. **Recorded**: graph_builder's 79 tests pass with its tests folder untouched.
- [X] T012 [US1] Adversarial, the three suites each (`GCT`, graph_builder's, `FT/test_edge_rule_in_step.py`): (1) drop the `entity_relation` member from `edge_ids.py` → only the `1.0` test and T010 fail; (2) add `import jsonschema` to `compare.py` → only `test_boundary.py` fails; (3) walk lists item by item → only the list-as-value test fails; (4) index by position instead of id → the moved-element test and others of T008 fail, graph_builder's ordering test too. Restore. Record here. **Recorded**, each suite on its own: (1) `entity_relation`'s member dropped → 2 in `test_graph_compare.py` (`…1_0_graph…`, the refusal case for a missing `field_name`, which then no longer refuses) and the keep-in-step test; graph_builder 79 pass. (2) `import jsonschema` in `compare.py` → only the boundary test (the boundary checker would not see it). (3) lists walked item by item → `test_a_list_is_one_value` and graph_builder's `test_an_array_without_ids_is_compared_as_a_value` — the same rule, now one engine. (4) keyed by position → 11 of the part's tests and 7 of graph_builder's (its differences, `check`'s and the writer's), the keep-in-step test untouched. Restored: 21, 79, 1 pass. Running the three folders in one pytest call fails to collect (two packages named `tests`); quickstart now runs each on its own.
- [X] T013 Check run green; prepare commit 2: `feat(maxitor): compare two graphs (#290)`; tick #290 phase 1. **Recorded**: 42 of 42 `OK` (the new step `Pytest maxitor/core/graph_compare` among them), 70.7 s; the first run found two raw-string `match=` patterns and an unused counter in the tests (Ruff), fixed; `graph-builder write` changed no file.

---

## Phase 3: Picking a range (commit 3) · US2 — #290 phase 2

**Goal**: Diff on; two handles, roles by position, never on one version, Live only as B; keys; `mode`/`a`/`b` in the address; the room shares the range (FR-009 – FR-017; research R13, R14; contracts/ui.md, room-protocol.md).

**Independent test**: quickstart's picker rows; `npx vitest run` for `versionRange`, `VersionTrack`, `VersionPicker`, rooms.

- [ ] T014 [P] [US2] `FC/lib/versionRange.ts` (data-model "State transitions of the range"): over the track's ordered point keys (versions oldest first, then Live when present): `oneToDiff(points, v)` — "B is V and A is the version before it; on the oldest version, B moves to the next one and A takes the oldest"; `dropHandle(points, range, handle, target, direction)` — a target equal to the other end moves one further in `direction`, then `normalise`; `stepHandle(points, range, handle, ±1)` — the same rule, returning which side the moved handle now is (focus follows it); `shiftBoth(points, range, ±1)` — both move, nothing when either would leave the track; `homeEnd(points, range, handle, end)`; `normalise(points, a, b)` — orders by position, swaps a reversed pair, "Live is never A", equal ends → One on that version; `diffOffered(points)` — at least two points. Pure; no React.
- [ ] T015 [P] [US2] `FC/lib/versionRange.test.ts`: each rule; a property test over random sequences of drops, steps and shifts on tracks of 2, 3 and 12 points with and without Live: after every move `a` is before `b`, `a ≠ b`, `a ≠ live` (SC-003).
- [ ] T016 [US2] `FC/components/history/VersionTrack/VersionTrack.tsx`: a `range` prop — two handles (chips `A <name>` / `B <name>` in their handle's style), the stretch between them dark; drag uses `dropHandle` with the drag's direction; a handle dragged to an edge of a long track scrolls it along; a handle out of view pinned to its edge, as the single handle is; ← → on a focused handle `stepHandle` with focus kept on the moved handle; Shift + ← → `shiftBoth`; Home/End; each handle's accessible name by role ("A, 0.8.0, older version"). The picker opens with B in view, and A too when both fit (FR-017). One mode unchanged.
- [ ] T017 [US2] `FC/components/history/VersionPicker/VersionPicker.tsx`: Diff enabled when `diffOffered`, else greyed with the hint "needs two versions"; Side by side stays greyed, "comes later"; switching uses `oneToDiff` and Diff → One keeps B (FR-013, FR-015).
- [ ] T018 [US2] `FC/lib/urlState.ts`: `mode` (`diff`, absent in One) and `a` beside `history` and `b`, written with the key kept after `#key=` as today; `readUrlDeepLink` returns them; `FC/app/App.tsx` and `FC/app/useOpenHistory.ts` hold the range (`HistoryRange`: `mode`, `a`, `b`), restore it from the address through `normalise` (a reversed pair opens swapped and the bar is corrected; `a=b` → One; `a=live` swapped or One), and fall back an end the history lacks as One does, then apply the rules (edge cases of the spec). A version leaving the list moves its end toward the other; meeting → One, with the notice.
- [ ] T019 [US2] Rooms, server (contracts/room-protocol.md): `FS/model/rooms/resources/room_registry.py` — `Room.version_a: str | None` in `snapshot()` (`welcome.room.version_a`); `FS/model/rooms/actions/set_room_version_action.py` — accept optional `a`; refuse to the sender, room unmoved: `a == b`, `a == "live"`, `a` not older than `b` on the history's list, `a` missing or refused; broadcast `{"type": "version", "b", "a", "by"}`. The room link carries `mode`, `a`, `b`.
- [ ] T020 [US2] Rooms, client: `FC/rooms/protocol.ts` (`a` on `version` both ways, `version_a` in `welcome`), `FC/rooms/roomStore.ts`, `FC/rooms/useRoomSession.ts` — a local change sends `{type: "version", b, a}` (normalised); a received one sets the range; a newcomer takes the room's.
- [ ] T021 [P] [US2] Tests: `FC/components/history/VersionTrack/range.test.tsx` — drag past swaps roles; drop on the other goes one further; Live only as B; keys with and without Shift, focus stays on the moved handle; Home/End; accessible names. `FC/components/history/VersionPicker/VersionPicker.test.tsx` — Diff greyed "needs two versions" in M3 and M6, on in M2/M4/M5; One ↔ Diff. `FC/lib/urlState.test.ts` (or the existing test) — `mode`/`a`/`b` written and read, key kept; a reversed link swapped. `FT/test_room_version.py` — a range moves every participant; two at once end on one; each refusal goes to its sender only. `FC/rooms/historyRoom.test.ts` — the range from `welcome` and from `version`.
- [ ] T022 [US2] Adversarial: let `dropHandle` leave a handle on the other's point → only the never-meet tests fail (the property test among them); accept `a == "live"` in `SetRoomVersionAction` → only its refusal test fails. Restore. Record here.
- [ ] T023 Check run green; prepare commit 3: `feat(maxitor): pick two versions on the track (#290)`; tick #290 phase 2.

---

## Phase 4: The comparison on the server (commit 4) · US3 (server) — #290 phase 3

**Goal**: two AOA actions over two held versions; a comparison computed once per pair, recomputed when Live changes; every key and log rule kept (FR-018 – FR-021; research R7–R9; contracts/maxitor-api.md).

**Independent test**: `uv run pytest FT -q -k compare`.

- [ ] T024 [US3] `FS/model/core/actions/load_aoa_service_action.py` — the result gains `graph_text: str` (the graph's JSON text as `coordinator_json_raw` holds it: the envelope unwrapped, or the bare graph); `FS/api/graph_store.py` — `GraphEntry.document: str`, filled by `build_graph_entry` (research R7). The entry's AI-CORE invariants name it.
- [ ] T025 [US3] `FS/api/graph_source_middleware.py` (research R8): for a path starting `/api/v1/compare`, read `a` like `source`; missing → `400 {"detail": "Missing query parameter 'a': name the older version this comparison is from."}`; a version source → the same `_version_refusal` with the same key header; `store.acquire(a, key)`; bind it to a second context variable read by `current_base_entry()`; refusals in the order `a`, then `source`; reset in `finally`.
- [ ] T026 [US3] `FS/model/diagrams/resources/comparison_store.py` — `ComparisonStore` (research R9): `get(entry_a, entry_b) -> Comparison`, keyed by `(entry_a.content_sha256, entry_b.content_sha256)`, at most 32 pairs (the one read longest ago leaves), one computation per key under an `asyncio.Lock` per key, the work in `asyncio.to_thread` so a large pair does not stall the loop; `GraphNotComparableError` raised with which version (`A`/`B`) it came from. Built in `FS/api/app.py`'s lifespan and handed to the two actions as a connection.
- [ ] T027 [US3] `FS/model/diagrams/actions/compare_versions_action.py` — `CompareVersionsAction` at `GET /api/v1/compare` (contracts/maxitor-api.md): `{counts: {nodes, edges}, nodes: {id: status}, edges: {id: status}}`, unchanged left out; `FS/model/diagrams/actions/compare_element_action.py` — `CompareElementAction` at `GET /api/v1/compare-element` with `kind` (`node`|`edge`) and `id`: `{status, differences: [{path, change, before?, after?}]}`, `before` absent for `added`, `after` for `removed`; an id in neither → `404 {"detail": "not found"}`. Both read the two entries through a resource over `current_graph_entry()`/`current_base_entry()` (the way `DuckDBGraphHolder` reads the one entry), never from `app.state`; `GraphNotComparableError` → `422 {"detail": "<which version>: <reason>"}`. A computed comparison logs at `debug`: `Comparison <sha_a[:8]>…<sha_b[:8]> computed in <ms> ms, <counts>` — no address, no key.
- [ ] T028 [P] [US3] `FT/test_compare_reads.py` over the stand-in port (`FT/fixtures/stand_in_port.py` gains a history whose versions differ: an added entity, a removed field, a retargeted relation, a nested change): statuses and counts as built; one element's differences with both values; `a` missing → `400`; a wrong key on `a` → `404` before `source` is read; a refused version as `a` → `422`; a second read does not compute again (a counter on the store, SC-009); B on Live, the live graph changed and rebuilt → the next read gives the new comparison (FR-020); the key and the addresses in no log line or error body (`caplog`, every channel).
- [ ] T029 [US3] Adversarial: key `ComparisonStore` by source instead of content → only the Live-recompute test fails; skip the guard on `a` in the middleware → only the wrong-key-on-`a` test fails; put the source in the debug line → only the secrecy assertion fails. Restore. Record here.
- [ ] T030 Check run green; prepare commit 4: `feat(maxitor): compare two versions on the server (#290)`; tick #290 phase 3.

---

## Phase 5: The ERD comparison (commit 5) · US3 (client) — #290 phase 4

**Goal**: the ERD draws the union, marked; a retargeted relation is one amber link; the counts on the button; "no changes"; Live as B follows (FR-022 – FR-027; research R10–R12, R18; contracts/ui.md "ERD marks").

**Independent test**: quickstart's ERD rows; vitest for `erdDiff`, `buildDotSource`; the ERD style checks.

- [ ] T031 [US3] Prove the removed table's frame first (research R12): render a card with `STYLE="ROUNDED,DASHED"` through the client's Graphviz WASM in `F/client/scripts/check-erd-table-style.ts`; if the frame is not dashed, use a dashed node outline behind the label instead. Record which here.
- [ ] T032 [P] [US3] `FC/api/compare.ts`: `compareVersions(history, a, b)` and `compareElement(history, a, b, kind, id)` over the two reads, the key in `X-Maxitor-History-Key` as `FC/api/history.ts` sends it, refusals surfaced as One's are.
- [ ] T033 [P] [US3] `FC/lib/erdDiff.ts` (research R10, R11): `mergeErdPayloads(a, b)` — the union of entities (by `id`), fields (by name within an entity) and relations (by `source` + `source_field`), B's version of an element where both have it, `previous_type` and `previous_target` from A where they differ; `markErd(union, compare)` — a table's `diff` from its `Entity` node; a scalar row from the strongest of its `EntityField` node `<entity>:<field>` and its `entity_field` edge `<entity>|entity_field|<entity>:<field>`; a relation row and its line from the edge `<entity>|entity_relation|<field>`; everything absent from `compare` is `unchanged`; `diagramCounts(marked)` — tables, rows and links of the drawn diagram, each element once (a relation's row and line are one), a field of a new table counted as added.
- [ ] T034 [US3] `FC/lib/buildDotSource.ts`: optional `diff` on `ErdEntity`, `ErdField`, `ErdRelation`, `previous_type` on `ErdField`, `previous_target` on `ErdRelation` (data-model "ErdMark"); marks per contracts/ui.md — added green frame and header with `+`, rows green tint with `+`; removed red with the dashed frame (T031), rows red tint with `−` and the name struck through; changed amber with `~` (a table only when its own properties changed); unchanged faded; a type change written `~~old~~ → new` when it fits the cell, else left to the card; a retargeted relation as two DOT edges: solid amber to the B target, thin dashed amber to the A target (both tables in the union); every mark carries its glyph, not colour alone. Without `diff` the output is byte-for-byte today's.
- [ ] T035 [US3] Wire it: `FC/lib/loadErdDomainsBundle.ts` (or a sibling) loads `list-entities` for A and for B with the same domains plus `compareVersions`, merges and marks; `FC/components/diagrams/ErdViewer/ErdViewer.tsx` draws the marked payload in Diff; `FC/components/history/VersionButton/VersionButton.tsx` reads `◷ A <name> → B <name>  +N −N ~N ▾` (each count in its colour) from `diagramCounts`, `no changes` when all are zero (then the diagram is drawn as in One, nothing faded), and the range without counts on the other diagrams (research R17). Live as B: the existing fingerprint (outside a room) and `graph_changed` (in a room) re-read the comparison and B's slices (research R18). Filters, layout mode, pan and zoom as in One (FR-027).
- [ ] T036 [P] [US3] Tests: `FC/lib/erdDiff.test.ts` — union; marks per status; a row from node + edge; a retarget gives one relation with `previous_target`; counts equal marks; all-unchanged → zero. `FC/lib/buildDotSource.test.ts` — each mark in the DOT; the retarget as two edges, one dashed; no `diff` → unchanged output (snapshot of today's). `FC/components/history/VersionButton/VersionButton.test.tsx` — counts text, "no changes", range without counts. The ERD style check scripts gain a marked fixture checked on WASM.
- [ ] T037 [US3] Adversarial: draw a retargeted relation as a removed plus an added line → only the one-amber-link tests fail; count a relation's row and line twice → only the counts test fails; fade on "no changes" → only its test fails. Restore. Record here.
- [ ] T038 Check run green; prepare commit 5: `feat(maxitor): the ERD shows what changed between two versions (#290)`; tick #290 phase 4.

---

## Phase 6: The card (commit 6) · US4 — #290 phase 5

**Goal**: a click on a marked table or row opens every changed property, before and after (FR-028, FR-029; contracts/ui.md "Card").

- [ ] T039 [US4] `FC/components/history/DiffCard/` (`DiffCard.tsx`, `index.ts`, `README.md`): given the element's kind and id, reads `compareElement` and lists each difference — the path joined with `.`, before → after; "Added in <B>" / "Removed in <B>" for added and removed; values rendered as text (strings as they are, other JSON as JSON text), never HTML; closes on a click outside or Escape; follows a new comparison when B is Live and closes when its element is no longer marked.
- [ ] T040 [US4] `FC/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx`: a click on a marked table header or row (found by `erdCellId`) opens `DiffCard` for its element (the `Entity`, the `EntityField` node, or the `entity_relation` edge); an unchanged one behaves as in One.
- [ ] T041 [P] [US4] `FC/components/history/DiffCard/DiffCard.test.tsx`: a changed field lists every changed property with both values (SC-006); a retarget shows `target_id` old → new; added/removed wording; a value `<script>alert(1)</script>` shown as text; Escape closes. Adversarial: render values with `dangerouslySetInnerHTML` → only the `<script>` test fails. Restore. Record here.
- [ ] T042 Check run green; prepare commit 6: `feat(maxitor): a changed element's card (#290)`; tick #290 phase 5.

---

## Phase 7: The messages (commit 7) · US5 — #290 phase 6

**Goal**: A's message left, B's right; the versions between, newest first (FR-030, FR-031; research R16).

- [ ] T043 [US5] `FC/components/history/VersionPicker/VersionPicker.tsx`: in Diff two `VersionMessage`s side by side — A left, B right — each ~9 lines, scrolling on its own with the thin visible scrollbar; Live as B shows Live's closing line on B's side; on a phone stacked A over B.
- [ ] T044 [US5] `FC/components/history/VersionsBetween/` (`VersionsBetween.tsx`, `index.ts`, `README.md`): one line "N versions between" (absent when none), opening the versions strictly between A and B, newest first; a closed row shows its name and its message's first line; a click opens the whole message through `VersionMessage`.
- [ ] T045 [P] [US5] Tests: `FC/components/history/VersionsBetween/VersionsBetween.test.tsx` — order newest first, first-line preview, a row opens whole, absent when adjacent; `VersionPicker.test.tsx` — A left and B right, Live's line on B's side. Adversarial: order the between list oldest first → only its order test fails. Restore. Record here.
- [ ] T046 Check run green; prepare commit 7: `feat(maxitor): both versions' messages and the versions between (#290)`; tick #290 phase 6.

---

## Phase 8: Pages in one version only (commit 8) · US6 — #290 phase 7

**Goal**: the left panel lists A's and B's pages together, `+`/`−` on a page in one only; on it everything is added or removed (FR-032; research R15).

- [ ] T047 [P] [US6] `FC/lib/sidebarDiff.ts`: `mergeSidebars(a, b)` — the union by page key (domain qualname, entity id for a lifecycle, and so on, as `FC/lib/sidebarNavigation.ts` keys them), `only: "a" | "b"` on a page in one only (data-model "SidebarMark").
- [ ] T048 [US6] `FC/components/navigation/LeftSidebar/`: in Diff read the sidebar of A and of B and show the merged one with `+` (only in B) and `−` (only in A); in One unchanged. A one-sided ERD page: the side without it contributes nothing, so `markErd` marks everything added or removed.
- [ ] T049 [P] [US6] Tests: `FC/lib/sidebarDiff.test.ts` — union and marks; the left panel's test — marks in Diff, none in One; a page only in B is all green (via `markErd`). Adversarial: merge by label instead of page key → only the union test fails. Restore. Record here.
- [ ] T050 Check run green; prepare commit 8: `feat(maxitor): pages that exist in one version only (#290)`; tick #290 phase 7.

---

## Phase 9: Phone (commit 9) · US7 — #290 phase 8

**Goal**: Diff on a phone: the button in the phone bar with A, B and counts, shortened; the sheet holds switch, range, messages stacked; 44 px handles (FR-033).

- [ ] T051 [US7] `VersionButton` short form (`A 0.8.0 → B 0.9.0 +15 −1 ~3`, names shortened first); the sheet in `VersionPicker` with the range and stacked messages; `VersionTrack` `touch` gives both handles a 44 px target.
- [ ] T052 [P] [US7] `FC/components/history/VersionPicker/VersionPicker.phone.test.tsx`: Diff at phone width — the button's short form, the sheet's parts, messages stacked, each handle and point ≥ 44 px. Adversarial: 24 px handles on a phone → only the touch-target test fails. Restore. Record here.
- [ ] T053 [US7] Run Maxitor in the browser pane on the local test histories (quickstart "By hand") at desktop and phone width: every row of the quickstart table, a room of two tabs, B on Live; screenshot each for the report.
- [ ] T054 Check run green; prepare commit 9: `feat(maxitor): comparing two versions on a phone (#290)`; tick #290 phase 8.

---

## Phase 10: Closing — check run, documentation, changelog — #290 phase 9

- [ ] T055 Closing check run to zero; record against T002. Commit 10 only if the run changed files: `chore(checks): the closing check run of #290 (#290)`.
- [ ] T056 Documentation (Principle VI): `docs/how-to/compare-two-versions.md` and its `.ru_draft.md` — the comparison of two graphs (statuses, paths, counts, `1.0` against `1.1`, a rename, refusals) and Diff in Maxitor (picking a range and its rules, the address, the room, the ERD's marks, a retargeted relation, the counts, "no changes", the card, the messages and the versions between, one-sided pages, the phone); `examples/step_26_maxitor/17_compare_two_versions.py` and `.ipynb` — every case of `compare` executed, then Maxitor's two compare reads over a port the example builds, the notebook's output equal to the script's; `GC/README.md`; `M/README.md` and its draft (the new part); `F/README.md` and its draft (the two reads); `GB`'s README if it mentions `differences`; the docs index; the tutorial's step 26. Commit 11: `docs(maxitor): comparing two versions (#290)`.
- [ ] T057 Changelog: one article in `docs/CHANGELOG.md` (and `M/CHANGELOG.md` if the package keeps its own entries) — what comparing two versions gives a user, in plain words, with the nuances (A is always older, Live only as B, what the colours mean, "no changes", the other diagrams come next); no technical detail. Commit 12: `docs(changelog): comparing two versions on the ERD (#290)`. Tick #290 phase 9.

---

## Dependencies

- Commit 2 (comparison) first: commits 4–8 use it.
- Commit 3 (range) and commit 4 (server) are independent of each other; both precede commit 5.
- Commit 5 (ERD) precedes 6 (card), 8 (one-sided pages: `markErd`).
- Commit 7 (messages) needs only commit 3.
- Commit 9 (phone) last of the features; then 10–12 in that order.

## Parallel examples

- Phase 2: T008, T009, T010 together once T005–T007 exist.
- Phase 3: T014 + T015 beside T019 (server rooms).
- Phase 5: T032 and T033 together; T036 once T033–T034 exist.

## Implementation strategy

The issue's order is the dependency order; there is no smaller release than the whole step (the maintainer: full result or nothing). Each commit leaves the check run green.
