# Tasks: Maxitor Rooms Polish — One Picture, Faithful Following, the Finer Look

**Input**: Design documents from `specs/029-maxitor-rooms-polish/`

**Prerequisites**: plan.md, spec.md (with clarifications of 2026-10-27), research.md (R1–R17), data-model.md, contracts/ (room-protocol, graph-interchange), quickstart.md

**Tests**: Required. Every requirement is testable and the house rule makes verification adversarial — for each new test, break the code the way the test must catch, confirm that test fails and no other does, restore.

**Organization**: one phase = one commit, in the order of plan.md "Phases" (commit 1 holds the design documents). Every phase ends with **acceptance on the local stand** (research R17, quickstart.md): the agent rebuilds the stand, checks the phase there itself, then gives the maintainer in Russian what to open, what to do and what must be seen; the commit is made only after the maintainer accepts and says so.

**The architectural rule** (spec 028, research R1): no hand-written route, no decision in a middleware, adapter or timer, no store or service reached outside a resource. Relayed messages (`pointer`, `viewport`, `focus`) are spec 028's documented exception: never run as actions, never logged.

**Issue checkboxes**: issue #282 "Plan" lists 18 phases, each ticked with its sha when its commit lands (`gh issue edit 282`). Mapping (commit → issue phase): 2 → 1; 3 → 2; 4 → 3; 5 → 4; 6 → 5; 7 → 6; 8 → 7; 9 → 13; 10 → 12; 11 → 9; 12 → 8; 13 → 10; 14 → 11; 15 → 14; 16 → 15; 17 → 16; 18 → 17; 19 → 18. Commit 1 (design documents) and commit 20 (release preparation) have no issue phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task serves (US1–US7)
- Every new Python module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every new public class carries an AI-CORE block (IV); every class, function and method a one-line docstring (V).
- The acceptance task of each phase: `bash scripts/deploy_demonstrator_stand.sh --local` (Maxitor `http://127.0.0.1:8101`, service `http://demo:8100`), the agent's own check there, then the Russian acceptance list to the maintainer.

---

## Phase 1: Setup — design documents (commit 1)

- [X] T001 Confirm `feature/issue-282-maxitor-rooms-polish` is checked out from `main` (`9a1ea1b0` or later); run `uv run pytest packages/aoa-maxitor/tests packages/aoa-action-machine/tests -q` and, in `packages/aoa-maxitor/client`, `npm test`, recording the green baseline counts here. Done: from `main` at `9a1ea1b0`; baseline aoa-maxitor 302 passed / 1 skipped, aoa-action-machine 3043, aoa-demo 79, client 150.
- [X] T002 Prepare commit 1 with `specs/029-maxitor-rooms-polish/` (spec, checklist, plan, research, data model, contracts, quickstart, tasks; `tasks.ru_draft.md` stays out, `.gitignore` ignores it): `docs(spec): specify Maxitor rooms polish (#282)`. Committed as `fb72152a`.

---

## Phase 2: Room picture on open (commit 2) · US1

**Goal**: one room, one picture (FR-001 … FR-003; research R1).

**Independent Test**: set filters and Neato outside a room, open a room, join from a browser with no settings: both show the same diagram on every page.

- [X] T003 [P] [US1] Create `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/actions/seed_page_settings_action.py`: `SeedPageSettingsAction` with params `page: str`, `values: dict[str, Any]`, connection `RoomRegistry` and `SocketChannel` (as `SetPageSettingAction`); only the room's `created_by` may seed (else `box.warning(Channel.security, …)` and no change); each `name` is set only if `room.settings[page]` has no value for it; each applied value is broadcast as `{"type": "setting", page, name, value, by}`; one `box.info` line naming page and the count applied. Done: field named `settings` (pydantic's `BaseParams` already has `values`); a value the page does not accept is skipped.
- [X] T004 [US1] Register `seed` in the rooms route's `messages` in `packages/aoa-maxitor/src/aoa/maxitor/api/app.py` (next to `setting`). Done.
- [X] T005 [P] [US1] Tests in `packages/aoa-maxitor/tests/rooms/test_seed_page_settings.py`: the creator's seed reaches a guest as `setting` events; a value already set is not overwritten; a seed from a guest changes nothing and logs a security warning; a 5 KB seed is refused with `4413`. Done in `packages/aoa-maxitor/tests/test_rooms_server.py` (the room helpers live there): four tests.
- [X] T006 [US1] In `packages/aoa-maxitor/client/src/lib/pageSettings.ts`: inside a room read the room's value, else the default (drop the own-value fallback); add `ownSettingsByPage(): Record<string, Record<string, unknown>>` for seeding. Done.
- [X] T007 [US1] In `packages/aoa-maxitor/client/src/rooms/useRoomSession.ts`: after the welcome of a room this tab opened (`room=new`), send one `{type: "seed", page, settings: {name: value}}` per setting from `ownSettingsByPage()` (one setting per message, so no message nears the 4 KB limit); a value whose message would exceed 4 KB is not sent and that setting starts at its default; add the message to `packages/aoa-maxitor/client/src/rooms/protocol.ts`. Done in `client/src/rooms/seed.ts` (`seedMessages`, one setting per message, a value over `MAX_MESSAGE_BYTES` left out) and `useRoomSession.ts` (seeded after the welcome is applied, shown at once).
- [X] T008 [P] [US1] Tests in `packages/aoa-maxitor/client/src/lib/pageSettings.test.ts` and `packages/aoa-maxitor/client/src/rooms/rooms.test.ts`: inside a room an own value never shows; the opener sends one seed per setting; a value over 4 KB is not sent; a joiner sends none. Done: three tests in `pageSettings.test.tsx`, two session tests in `rooms.test.ts`.
- [X] T009 [US1] Adversarial check: restore the own-value fallback → only the "own value never shows" test fails; let a guest seed → only the guest test fails; drop the "only where empty" rule → only the overwrite test fails. Restore. Done: five breaks (guest seeds, seed overwrites, own value in a room, no size check, a joiner seeds) — each failed exactly its own test; restored, all green (aoa-maxitor 306 passed / 1 skipped, client 156).
- [X] T010 [US1] Acceptance on the local stand (quickstart "Room picture on open"); prepare commit 2: `feat(maxitor): one room, one picture — the opener's settings seed the room (#282)`. Tick issue phase 1.

---

## Phase 3: Pointers stay (commit 3) · US2

**Goal**: a pointer shows while its person is in the room (FR-020 … FR-022; R5).

**Independent Test**: a still pointer is shown after a minute; it disappears on leave, away, other page, Hide pointers.

- [ ] T011 [P] [US2] In `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/resources/room_registry.py` remove `POINTER_SHOWN_SECONDS` and its window in `catch_up`: the last mouse pointer of every present participant on the page is sent whatever its age; taps (`kind == "touch"`) are still never caught up.
- [ ] T012 [P] [US2] In `packages/aoa-maxitor/client/src/rooms/PointerLayer/PointerLayer.tsx` remove `POINTER_IDLE_MS` and the idle fade; keep hiding on left, away, other page and Hide pointers; taps keep their brief mark.
- [ ] T013 [US2] Tests: `packages/aoa-maxitor/tests/rooms/test_room_registry.py` (a pointer an hour old is caught up; a tap is not; an away participant's is not) and `packages/aoa-maxitor/client/src/rooms/PointerLayer/PointerLayer.test.tsx` (a pointer still after 10 minutes of fake time; gone on leave).
- [ ] T014 [US2] Adversarial check: put back a 10 s window on either side → only its test fails. Restore.
- [ ] T015 [US2] Acceptance on the local stand (quickstart "Pointers stay"); prepare commit 3: `feat(maxitor): pointers stay while their person is in the room (#282)`. Tick issue phase 2.

---

## Phase 4: Follow mirrors focus (commit 4) · US2

**Goal**: the follower sees the followed person's hover, tooltip, selection and panels (FR-010 … FR-013; R2; contracts/room-protocol.md).

**Independent Test**: two browsers, one following: every hover, tooltip, selection, filter-panel section and sidebar branch change appears in the follower; nobody else sees it.

- [ ] T016 [US2] In `room_registry.py` add `focus` to the relayed types with validation from data-model.md — "`kind` from the list, `id` a string ≤ 512 chars, `sidebar` ≤ 200 ids; anything else drops the message"; keep the last focus on the `Tab`; relay it only to tabs of participants whose follow link points at the sender (`send_volatile("focus:<id>")`); when a follow starts, send the target's last focus to the new follower. Add `focus` to `relay=` in `app.py`.
- [ ] T017 [P] [US2] Server tests in `packages/aoa-maxitor/tests/rooms/test_focus_relay.py`: a follower gets focus, a non-follower on the same page does not; invalid fields are dropped; a new follower gets the last focus at once; nothing is logged.
- [ ] T018 [P] [US2] Create `packages/aoa-maxitor/client/src/rooms/focusSurface.ts`: `FocusState` (contracts), `registerFocusSurface(surface: { apply(focus: FocusState | null): void; onLocal(listener: (focus: FocusState) => void): () => void })`, and a sender throttled to 10/s; add `focus` to `protocol.ts`.
- [ ] T019 [US2] Focus surfaces per viewer — ERD (`ErdGraphvizCanvas.tsx`: table/row/edge hover, tooltip, selection), full graph (`FullGraphViewer.tsx`: node hover, tooltip, selection), use case (`UseCaseDiagramViewer.tsx`), lifecycle (`LifecycleFsmViewer.tsx`); panels: `ErdFilterPanel.tsx` open section, `LeftSidebar.tsx` open branches, `CollapsibleLegendPanel.tsx` collapsed state. Each `apply` reuses the viewer's own hover/selection code.
- [ ] T020 [US2] In `packages/aoa-maxitor/client/src/rooms/follow.ts`: while following, apply the target's focus and ignore the follower's own hover/clicks on the diagram; on stop, keep what was shown as the follower's own starting state; a focus that arrives while the follower's page is still drawing is applied once it is drawn, or dropped if a newer one replaced it; a tooltip that would fall outside the follower's screen is kept inside it.
- [ ] T021 [P] [US2] Client tests `packages/aoa-maxitor/client/src/rooms/focusSurface.test.ts` and in `rooms.test.ts`: local changes are sent at most 10/s; a received focus is applied while following and ignored otherwise; stop hands the state back; a focus received before the surface is ready is applied when it registers; a tooltip is clamped to the follower's screen; a touch-only follower still shows the mirrored hover.
- [ ] T022 [US2] Adversarial check: relay focus to the whole page → only the non-follower test fails; drop the catch-up on follow start → only that test fails. Restore.
- [ ] T023 [US2] Update spec 028's rule in `specs/028-maxitor-rooms/spec.md` FR-032 with a pointer to 029 FR-013 (personal *except while following*).
- [ ] T024 [US2] Acceptance on the local stand (quickstart "Follow mirrors focus"); prepare commit 4: `feat(maxitor): the follower sees what the followed person sees (#282)`. Tick issue phase 3.

---

## Phase 5: Smooth follow (commit 5) · US3

**Goal**: the follower glides and settles exactly (FR-014, FR-016; R3).

**Independent Test**: following a continuous pan moves the follower on every frame with no jump over a tenth of the screen; it settles to the pixel within 0.5 s.

- [ ] T025 [US3] In `packages/aoa-maxitor/client/src/rooms/throttle.ts` raise `VIEWPORT_RATE` to 20; in `app.py` set the rooms route's `max_messages_per_second=80`.
- [ ] T026 [US3] In `follow.ts` add the playback: keep the last two viewport samples with arrival times; on every animation frame draw the view interpolated one sample interval behind (centre linear, zoom on a log scale); with no new sample for one interval, settle exactly on the last one; stop the loop when not following.
- [ ] T027 [P] [US3] Tests `packages/aoa-maxitor/client/src/rooms/follow.test.ts` with fake timers and rAF: positions between two samples are interpolated and no frame moves the view by more than a tenth of the screen (SC-003); the view ends exactly on the last sample within 0.5 s of the last one (SC-003); a server test that 50 messages/s pass and 81 close with `4429`.
- [ ] T028 [US3] Adversarial check: centre on each sample directly → the interpolation test fails; drop the settle → the "ends exactly" test fails. Restore.
- [ ] T029 [US3] Acceptance on the local stand (quickstart "Smooth follow"); prepare commit 5: `feat(maxitor): following glides with the followed person (#282)`. Tick issue phase 4.

---

## Phase 6: Following in Firefox (commit 6) · US3

**Goal**: following works in all six directed engine pairs (FR-015; R4).

**Independent Test**: the cross-engine script's follow case passes for every pair.

- [ ] T030 [US3] In `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts` add a follow case: two contexts per directed pair of Chromium, Firefox, WebKit; the leader pans and hovers, the follower's centre and hover must match within 2 px / the same element, and the follower must show the leader's hover within 0.5 s (SC-002); include the switch from one person to another (R7).
- [ ] T031 [US3] Run it, record which pairs fail and why (here, with the evidence), fix the cause in `packages/aoa-maxitor/client/src/rooms/` (suspects in research R4), and re-run until all six pass.
- [ ] T032 [US3] Adversarial check: reintroduce the cause → only the Firefox pairs fail. Restore.
- [ ] T033 [US3] Acceptance on the local stand in Firefox and Chrome (quickstart "Firefox follow"); prepare commit 6: `fix(maxitor): following works in Firefox (#282)`. Tick issue phase 5.

---

## Phase 7: Room controls in Maxitor's style (commit 7) · US5

**Goal**: 16 px icons, 32 px icon buttons, 22 px circles that never touch; a clean switch (FR-050 … FR-052; R6, R7).

**Independent Test**: measured sizes; no ring touches a neighbour; switching whom you follow overlaps nothing.

- [ ] T034 [P] [US5] `packages/aoa-maxitor/client/src/rooms/RoomBar/RoomBar.tsx`, `RoomBanner.tsx`: menu button 32 × 32 with an ~18 px glyph; banner and menu icons 16 px.
- [ ] T035 [P] [US5] `packages/aoa-maxitor/client/src/rooms/Circles/Avatar.tsx`, `Circles.tsx`: room-bar circle 22 px inside a 29 px box that takes layout space; your ring is the box's border; the focus ring drawn inside the box; boxes 4 px apart.
- [ ] T036 [US5] Reproduce the overlap on switching (follow A, *Follow B instead* in B's card) in the browser, record it here, fix it in `ParticipantCard.tsx` / `FollowFrame` / `Circles.tsx`.
- [ ] T037 [P] [US5] Tests `packages/aoa-maxitor/client/src/rooms/Circles/Circles.test.tsx`: box sizes and gaps, rings inside the box; and a geometry check in the cross-engine script: no two circle boxes overlap with every ring combination.
- [ ] T038 [US5] Adversarial check: move the ring back to `box-shadow` outside → the overlap check fails. Restore.
- [ ] T039 [US5] Acceptance on the local stand (quickstart "Room controls"); prepare commit 7: `style(maxitor): room controls in Maxitor's sizes, circles that never touch (#282)`. Tick issue phase 6.

---

## Phase 8: ERD card as in the mockup (commit 8) · US6

**Goal**: header flush with the outline, the mockup's corner curve (FR-032; R8).

**Independent Test**: the ERD style check measures no gap and the radius within 0.5 px.

- [ ] T040 [US6] In `packages/aoa-maxitor/client/src/lib/buildDotSource.ts` draw tables with no outline and no header fill (`BORDER="0"`), keeping cells, sizes and ports.
- [ ] T041 [US6] In `packages/aoa-maxitor/client/src/lib/erdPostPass.ts` draw each card beneath its cells from the table's bounding box: one rounded rectangle (radius 9 px at 100 %, stroke 1.4, the domain colour) and the header as a path with the same top radius filling to the outline; row tints stop 1 px inside the outline.
- [ ] T042 [US6] In `packages/aoa-maxitor/client/scripts/check-erd-table-style.ts` add: no gap between header and outline; outline and header share the radius within 0.5 px; re-check the identical-layout hashes of spec 028 still match (`check-layout-determinism.ts`).
- [ ] T043 [US6] Adversarial check: give the header a 2 px inset → the gap assertion fails. Restore.
- [ ] T044 [US6] Acceptance on the local stand (quickstart "ERD card"); prepare commit 8: `style(maxitor): the ERD card drawn as in the mockup (#282)`. Tick issue phase 7.

---

## Phase 9: Kind icon on the name's axis (commit 9) · US6

**Goal**: the icon's centre on the name's visual centre line (FR-033; R9).

- [ ] T045 [US6] In `placeKindIcons` (`erdPostPass.ts`) centre the icon at `baseline − 0.36 × fontSize` and centre the pair in the header band.
- [ ] T046 [US6] In `check-erd-table-style.ts` measure the icon's centre against the name's bounding-box centre (≤ 0.5 px) for every table of the reference ERD.
- [ ] T047 [US6] Adversarial check: restore the top-of-cell placement → only the axis assertion fails. Restore.
- [ ] T048 [US6] Acceptance on the local stand (quickstart "Icon axis"); prepare commit 9: `style(maxitor): the kind icon on the table name's axis (#282)`. Tick issue phase 13.

---

## Phase 10: Clean field types (commit 10) · US6

**Goal**: every field type reads as one clean name; the full annotation in the tooltip (FR-030, FR-031; R10; contracts/graph-interchange.md).

**Independent Test**: all 39 demo types follow the FR-030 table; an old-form string is cleaned by the client.

- [ ] T049 [P] [US6] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/field_type_label.py`: `field_type_label(annotation) -> str` by the FR-030 table, pure and idempotent ("`clean(clean(x)) == clean(x)`"), with the AI-CORE block moved from `EntityFieldGraphNode.pretty_annotation` (constitution IV debt).
- [ ] T050 [US6] In `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_field_graph_node.py`: `field_type` = `field_type_label(annotation)`, new property `field_annotation` = today's `pretty_annotation`; update the graph JSON schema if it lists node properties.
- [ ] T051 [P] [US6] Tests `packages/aoa-action-machine/tests/graph/test_field_type_label.py`: one case per table row (including `Optional[str]`, `Union[str, None]`, `str | None` → `str | None`; `AssociationOne[X]` → `X`; `Specialization[A | B, K]` → `A | B`; `list[X]` → `X[]`; `Literal["a", "b"]` → `"a" | "b"`), idempotence, and every type of the demo model contains no `UnionType`, `NoneType`, `Union[`, `AssociationOne[` or `Generalization[`.
- [ ] T052 [US6] Maxitor: carry `field_annotation` in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py` (column, nullable for older services) and `list_entities_action.py` (`fields[].annotation`).
- [ ] T053 [P] [US6] Create `packages/aoa-maxitor/client/src/lib/fieldTypeLabel.ts`: `cleanFieldType(raw: string): string` parsing the old forms, idempotent on clean labels; use it in `buildDotSource.ts` for the type cell; the tooltip shows `annotation`, else the raw string; long labels cut with `…`.
- [ ] T054 [P] [US6] Tests `packages/aoa-maxitor/client/src/lib/fieldTypeLabel.test.ts` (each old form → its clean label; idempotence) and `packages/aoa-maxitor/tests/` for `fields[].annotation`.
- [ ] T055 [US6] Adversarial check: drop the `None`-last rule → only its cases fail; skip the client cleaning → only the old-form tests fail. Restore.
- [ ] T056 [US6] Acceptance on the local stand (quickstart "Clean field types"); prepare commit 10: `feat(aoa): field types as one clean name, the full annotation beside it (#282)`. Tick issue phase 12.

---

## Phase 11: ERD line ends and direction (commit 11) · US7

**Goal**: true cardinality with optionality; reference lines the right way (FR-043; R11).

- [ ] T057 [US7] In `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/` record a relation's optionality (annotation admits `None` or default `None`) and expose it as `optional` in `graph/edges/entity_graph_edge.py`; tests in `packages/aoa-action-machine/tests/`.
- [ ] T058 [US7] In `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py` store `optional`; in `list_entities_action.py` return `one` / `zero_one` / `zero_many` / `one_many` and make reference lines `zero_many` at the referring table, `one` at the dictionary; update the example comment and `packages/aoa-maxitor/tests/`.
- [ ] T059 [US7] In `buildDotSource.ts` map ends to Graphviz shapes (first nearest the table): `one` → `teetee`, `zero_one` → `teeodot`, `zero_many` → `crowodot`, `one_many` → `crowtee`; tune `arrowsize` / `penwidth` for readability; keep the UML field-label placement and generalization style.
- [ ] T060 [US7] In `check-erd-table-style.ts` assert on the reference ERD: each end's shape matches its relation; every reference line's crow's foot is at the referring table; refresh the golden of `check-erd-dictionary-values.ts` on purpose.
- [ ] T061 [US7] Adversarial check: swap the reference ends back → only the direction assertion fails; map `zero_one` to `teetee` → only the optionality assertion fails. Restore.
- [ ] T062 [US7] Acceptance on the local stand (quickstart "ERD line ends"); prepare commit 11: `fix(maxitor): ERD line ends show true cardinality, reference lines point the right way (#282)`. Tick issue phase 9.

---

## Phase 12: ERD hover lights joined tables (commit 12) · US7

- [ ] T063 [US7] In `bindLineHover` (`erdPostPass.ts`) give the tables at both ends of the hovered line, or of every line of the hovered row, the hovered-table class, so they stay bright while the rest dims (FR-040, FR-041; R12).
- [ ] T064 [US7] Test in `packages/aoa-maxitor/client/src/lib/erdPostPass.test.ts`: hovering a PK row, an FK row and a line brightens exactly the joined tables; table hover unchanged.
- [ ] T065 [US7] Adversarial check: brighten only the hovered table → the test fails. Restore.
- [ ] T066 [US7] Acceptance on the local stand (quickstart "ERD hover"); prepare commit 12: `feat(maxitor): hovering a key or a line lights every table it joins (#282)`. Tick issue phase 8.

---

## Phase 13: Role labels on hover (commit 13) · US7

- [ ] T067 [US7] In `packages/aoa-maxitor/client/src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx` hide role labels by default and show the label of the role under the pointer, or of the mirrored hover while following (FR-042; R13).
- [ ] T068 [US7] Test in `UseCaseDiagramViewer.test.tsx`: no label without hover; the hovered role's label shows; adversarial check by always showing labels. Restore.
- [ ] T069 [US7] Acceptance on the local stand (quickstart "Role labels"); prepare commit 13: `style(maxitor): role labels appear on hover (#282)`. Tick issue phase 10.

---

## Phase 14: *Kinds* lists the diagram's kinds (commit 14) · US7

- [ ] T070 [US7] In `ErdGraphvizCanvas.tsx` / `ErdFilterPanel.tsx` build the *Kinds* list from the tables shown before the kind filter (after domain and one-hop), with names from `list-entity-kinds`; a kind switched off stays listed (FR-044; R14).
- [ ] T071 [US7] Test in `packages/aoa-maxitor/client/src/lib/erdKindFilter.test.ts`: a diagram missing kinds lists only its own; a switched-off kind stays; adversarial check by listing all kinds. Restore.
- [ ] T072 [US7] Acceptance on the local stand (quickstart "Kinds filter"); prepare commit 14: `feat(maxitor): the Kinds filter lists only the diagram's kinds (#282)`. Tick issue phase 11.

---

## Phase 15: Maxitor serves its own graph (commit 15) · US4

**Goal**: Maxitor's address opens Maxitor's diagram; `ETag` / `304` (FR-060, FR-061; R15).

- [ ] T073 [P] [US4] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/own_model_graph_resource.py`: `OwnModelGraphResource` holding Maxitor's coordinator, rendering `to_json()` once per process.
- [ ] T074 [P] [US4] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/get_own_graph_json_action.py`: `GetOwnGraphJsonAction` returning `{"coordinator_json": …}` through the resource (`@check_roles(GuestRole)`, `@meta` in Maxitor's core domain).
- [ ] T075 [US4] Route `GET /examples/model/graph-json` to it in `app.py` with the resource as its connection.
- [ ] T076 [US4] Tests `packages/aoa-maxitor/tests/test_own_graph_json.py`: `200` with Maxitor's own actions in the graph (e.g. `JoinRoomAction`); an `ETag`; `304` with no body on `If-None-Match`; no `source` needed; loading Maxitor's own address through `load_aoa_service_action` builds a graph.
- [ ] T077 [US4] Adversarial check: make the resource render a body with a timestamp on every call → only the `304` test fails; remove the route → only the route tests fail. Restore.
- [ ] T078 [US4] Acceptance on the local stand (quickstart "Maxitor's own graph"); prepare commit 15: `feat(maxitor): Maxitor serves and shows its own graph (#282)`. Tick issue phase 14.

---

## Phase 16: The demo on the fresh adapter (commit 16) · US4

- [ ] T079 [US4] In `packages/aoa-demo/pyproject.toml` require `aoa-fastapi-adapter>=1.3.0` and raise the version; `uv lock`; a test in `packages/aoa-demo/tests/` that `graph-json` answers with an `ETag` and `304` (FR-061, FR-062; R16).
- [ ] T080 [US4] Acceptance: `curl` the local stand's demo (`http://127.0.0.1:8100/examples/model/graph-json`) twice → `304`; prepare commit 16: `chore(demo): serve graph-json with an ETag through the fresh adapter (#282)`. Tick issue phase 15. Publishing `aoa-demo` and redeploying `demo.aoa.run` wait for the maintainer's command (T086).

---

## Phase 17: The check run (commit 17)

- [ ] T081 Run `bash scripts/run_checks_with_log.sh` and take it to zero — only the two accepted remarks stay; prepare commit 17: `chore: take the check run to zero (#282)`. Tick issue phase 16.

---

## Phase 18: Documentation (commit 18)

- [ ] T082 Update `docs/tutorials/step-26-maxitor.md` and `packages/aoa-maxitor/README.md` for every case this feature introduces (constitution VI.4): the room's picture on open, following what the followed person sees and its smoothness, pointers that stay, Maxitor's own graph and `ETag`/`304`, clean field types, ERD line ends, hover, role labels, the *Kinds* list; each runnable case as a script and an executed notebook under `examples/step_26_maxitor/`; the Russian draft beside the page (`step-26-maxitor.ru_draft.md`, not committed). Prepare commit 18: `docs(maxitor): rooms polish, with runnable examples (#282)`. Tick issue phase 17.

---

## Phase 19: Changelog (commit 19)

- [ ] T083 Write one article at the top of `docs/CHANGELOG.md` about what this work changed for people in a room and readers of the ERD — plain words, no technical detail, no per-file account (constitution VI.3); its Russian version in `docs/CHANGELOG.ru_draft.md`. Prepare commit 19: `docs(changelog): rooms that show one picture (#282)`. Tick issue phase 18.

---

## Phase 20: Release preparation (commit 20, on command)

- [ ] T084 Raise versions and package changelogs: `aoa-action-machine` (new `field_annotation`, `optional`), `aoa-maxitor` (requires the new `aoa-action-machine`), `aoa-demo`; root README table; `uv lock`. Prepare commit 20: `chore(release): … (#282)`.
- [ ] T085 After merge, on the maintainer's command only: tags in dependency order (`aoa-action-machine`, then `aoa-demo` and `aoa-maxitor`), check each on PyPI.
- [ ] T086 On the maintainer's command only: redeploy `maxitor.aoa.run` and `demo.aoa.run`, and the dev stand from `main`; verify version, own graph, `ETag`/`304` and a room from outside.

---

## Dependencies & Execution Order

- Phase 1 first. Phases 2–16 each depend only on Phase 1, except: Phase 5 (smooth follow) and Phase 6 (Firefox) build on Phase 4's follow code; Phase 13 (role labels while following) uses Phase 4's focus surfaces; Phase 9 builds on Phase 8's card; Phase 11 changes `aoa-action-machine` like Phase 10 (do them in this order to keep one schema change per commit).
- Phases 17 → 18 → 19 → 20 strictly last, in this order (constitution VI).
- Within a phase: server and client tasks marked [P] run in parallel; the adversarial check and the acceptance task close the phase.

## Parallel Opportunities

- Phase 2: T003 + T005 (server) beside T006 + T008 (client).
- Phase 4: T017, T018 and T021 are independent files.
- Phase 7: T034, T035, T037.
- Phase 10: T049 + T051 (action machine) beside T053 + T054 (client).
- Phase 15: T073 + T074.

## Implementation Strategy

- **MVP**: Phases 2–4 (US1 + US2) — one picture and faithful following are the promise of a room.
- Then smoothness and Firefox (US3), the ERD look (US6, US7), Maxitor's own graph (US4), the room controls (US5) — each accepted on the local stand before the next.
- The tail (check run, documentation, changelog) and the release close the work.
