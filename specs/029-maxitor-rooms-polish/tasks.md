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
- [X] T010 [US1] Acceptance on the local stand (quickstart "Room picture on open"); prepare commit 2: `feat(maxitor): one room, one picture — the opener's settings seed the room (#282)`. Tick issue phase 1. Committed as `b8f1d2c3`; issue phase 1 ticked.

---

## Phase 3: Pointers stay (commit 3) · US2

**Goal**: a pointer shows while its person is in the room (FR-020 … FR-022; R5).

**Independent Test**: a still pointer is shown after a minute; it disappears on leave, away, other page, Hide pointers.

- [X] T011 [P] [US2] In `packages/aoa-maxitor/src/aoa/maxitor/model/rooms/resources/room_registry.py` remove `POINTER_SHOWN_SECONDS` and its window in `catch_up`: the last mouse pointer of every present participant on the page is sent whatever its age; taps (`kind == "touch"`) are still never caught up. Done: `POINTER_SHOWN_SECONDS` and `Tab.pointer_at` removed; away participants have no tab, so their pointer is never brought.
- [X] T012 [P] [US2] In `packages/aoa-maxitor/client/src/rooms/PointerLayer/PointerLayer.tsx` remove `POINTER_IDLE_MS` and the idle fade; keep hiding on left, away, other page and Hide pointers; taps keep their brief mark. Done; the README of `PointerLayer` says so.
- [X] T013 [US2] Tests: `packages/aoa-maxitor/tests/rooms/test_room_registry.py` (a pointer an hour old is caught up; a tap is not; an away participant's is not) and `packages/aoa-maxitor/client/src/rooms/PointerLayer/PointerLayer.test.tsx` (a pointer still after 10 minutes of fake time; gone on leave). Done in `tests/test_rooms_server.py` (an hour-old pointer is brought; a tap is not — collected up to a `follows` marker so a regression fails instead of hanging), `PointerLayer/PointerLayer.test.tsx` and `rooms/rooms.test.ts` (a pointer goes when its person leaves).
- [X] T014 [US2] Adversarial check: put back a 10 s window on either side → only its test fails. Restore. Done: a 10 s window on the server, taps brought, a 10 s fade on the client — each failed exactly its own test; restored, aoa-maxitor 307 passed / 1 skipped, client 159.
- [X] T015 [US2] Acceptance on the local stand (quickstart "Pointers stay"); prepare commit 3: `feat(maxitor): pointers stay while their person is in the room (#282)`. Tick issue phase 2. Committed as `859ea149`; issue phase 2 ticked.

---

## Phase 4: Follow mirrors focus (commit 4) · US2

**Goal**: the follower sees the followed person's hover, tooltip, selection and panels (FR-010 … FR-013; R2; contracts/room-protocol.md).

**Independent Test**: two browsers, one following: every hover, tooltip, selection, filter-panel section and sidebar branch change appears in the follower; nobody else sees it.

- [X] T016 [US2] In `room_registry.py` add `focus` to the relayed types with validation from data-model.md — "`kind` from the list, `id` a string ≤ 512 chars, `sidebar` ≤ 200 ids; anything else drops the message"; keep the last focus on the `Tab`; relay it only to tabs of participants whose follow link points at the sender (`send_volatile("focus:<id>")`); when a follow starts, send the target's last focus to the new follower. Add `focus` to `relay=` in `app.py`. Done: `focus_values` (module-level, with AI-CORE), `Tab.focus`, `_relay_focus` to followers only, `send_focus` from `FollowAction`; `filter` also accepts `"open"` (panel open, no section), recorded in data-model.md.
- [X] T017 [P] [US2] Server tests in `packages/aoa-maxitor/tests/rooms/test_focus_relay.py`: a follower gets focus, a non-follower on the same page does not; invalid fields are dropped; a new follower gets the last focus at once; nothing is logged. Done in `tests/test_rooms_focus.py`: eight validation cases, followers only and nothing logged, the last focus at once on follow; event reads have their own 3 s limit so a regression fails instead of hanging.
- [X] T018 [P] [US2] Create `packages/aoa-maxitor/client/src/rooms/focusSurface.ts`: `FocusState` (contracts), `registerFocusSurface(surface: { apply(focus: FocusState | null): void; onLocal(listener: (focus: FocusState) => void): () => void })`, and a sender throttled to 10/s; add `focus` to `protocol.ts`. Done as `rooms/focusStore.ts` (own focus, every participant's last focus, the follow target, `useShownPanel`) instead of a per-viewer registry; the sender lives in `useFollow` (`FOCUS_RATE` 10).
- [X] T019 [US2] Focus surfaces per viewer — ERD (`ErdGraphvizCanvas.tsx`: table/row/edge hover, tooltip, selection), full graph (`FullGraphViewer.tsx`: node hover, tooltip, selection), use case (`UseCaseDiagramViewer.tsx`), lifecycle (`LifecycleFsmViewer.tsx`); panels: `ErdFilterPanel.tsx` open section, `LeftSidebar.tsx` open branches, `CollapsibleLegendPanel.tsx` collapsed state. Each `apply` reuses the viewer's own hover/selection code. Done: `rooms/graphvizFocus.ts` serves the ERD, use-case and lifecycle viewers (names the hovered row/line/node, holds back the follower's own mouse, replays hover with `mouseenter`/`mouseleave`, shows the tooltip text in a label — a native tooltip cannot be opened); the full graph shows the followed node's hover card through one `showHover`; `ErdFilterPanel`, `LeftSidebar` and `CollapsibleLegendPanel` use `useShownPanel`. No viewer has a selection today, so `selection` travels and stays `null`.
- [X] T020 [US2] In `packages/aoa-maxitor/client/src/rooms/follow.ts`: while following, apply the target's focus and ignore the follower's own hover/clicks on the diagram; on stop, keep what was shown as the follower's own starting state; a focus that arrives while the follower's page is still drawing is applied once it is drawn, or dropped if a newer one replaced it; a tooltip that would fall outside the follower's screen is kept inside it. Done in `focusStore` / `graphvizFocus` / `useShownPanel` rather than `follow.ts`: a focus that arrives before the drawing is replayed when it appears, a tooltip is kept inside the window, and on stop the panels keep what was shown.
- [X] T021 [P] [US2] Client tests `packages/aoa-maxitor/client/src/rooms/focusSurface.test.ts` and in `rooms.test.ts`: local changes are sent at most 10/s; a received focus is applied while following and ignored otherwise; stop hands the state back; a focus received before the surface is ready is applied when it registers; a tooltip is clamped to the follower's screen; a touch-only follower still shows the mirrored hover. Done in `rooms/focus.test.tsx` (8 tests); `follow.test.ts` now counts only follow messages, since a tab in a room also sends its focus.
- [X] T022 [US2] Adversarial check: relay focus to the whole page → only the non-follower test fails; drop the catch-up on follow start → only that test fails. Restore. Done: six breaks (focus to the whole page, no focus on follow, replay from another page, own focus sent while following, no hand-back, no rate limit) — each failed exactly its own test; restored, aoa-maxitor 317 passed / 1 skipped, client 167.
- [X] T023 [US2] Update spec 028's rule in `specs/028-maxitor-rooms/spec.md` FR-032 with a pointer to 029 FR-013 (personal *except while following*). Done.
- [X] T024 [US2] Acceptance on the local stand (quickstart "Follow mirrors focus"); prepare commit 4: `feat(maxitor): the follower sees what the followed person sees (#282)`. Tick issue phase 3. Committed as `e6755a84`; issue phase 3 ticked.

---

## Phase 5: Smooth follow (commit 5) · US3

**Goal**: the follower glides and settles exactly (FR-014, FR-016; R3).

**Independent Test**: following a continuous pan moves the follower on every frame with no jump over a tenth of the screen; it settles to the pixel within 0.5 s.

- [X] T025 [US3] In `packages/aoa-maxitor/client/src/rooms/throttle.ts` raise `VIEWPORT_RATE` to 20; in `app.py` set the rooms route's `max_messages_per_second=80`. Done.
- [X] T026 [US3] In `follow.ts` add the playback: keep the last two viewport samples with arrival times; on every animation frame draw the view interpolated one sample interval behind (centre linear, zoom on a log scale); with no new sample for one interval, settle exactly on the last one; stop the loop when not following. Done as `createGlide` in `follow.ts`: the follower keeps its own zoom (spec 028), so only the centre glides — from where the screen is to each new centre over the time since the previous one (30–200 ms), ending exactly on it; the first centre is reached at once.
- [X] T027 [P] [US3] Tests `packages/aoa-maxitor/client/src/rooms/follow.test.ts` with fake timers and rAF: positions between two samples are interpolated and no frame moves the view by more than a tenth of the screen (SC-003); the view ends exactly on the last sample within 0.5 s of the last one (SC-003); a server test that 50 messages/s pass and 81 close with `4429`. Done: four glide tests in `follow.test.ts` (no frame over a tenth of the screen on a pan of 0.15 screen per report, exact stop within 0.5 s, the longest glide, the hook driving the screen with fake animation frames) and `test_fifty_messages_a_second_pass_and_more_than_eighty_close`; `throttle.test.ts` now allows 40 a second (pointer 20 + screen 20).
- [X] T028 [US3] Adversarial check: centre on each sample directly → the interpolation test fails; drop the settle → the "ends exactly" test fails. Restore. Done: centring on each screen directly, a glide that jumps, a glide that never arrives, the limit back at 40 — each failed its own tests; restored, aoa-maxitor 318 passed / 1 skipped, client 171. On the local stand, headless Chromium with two contexts (the leader dragging the ERD for 3.6 s): 296 frames moved, the biggest step 4.9 px (0.4 % of the screen), and after the drag both screens centred on the same diagram point (0.00 apart).
- [X] T029 [US3] Acceptance on the local stand (quickstart "Smooth follow"); prepare commit 5: `feat(maxitor): following glides with the followed person (#282)`. Tick issue phase 4. Committed as `c4c6bd8a`; issue phase 4 ticked.

---

## Phase 6: Following in Firefox (commit 6) · US3

**Goal**: following works in all six directed engine pairs (FR-015; R4).

**Independent Test**: the cross-engine script's follow case passes for every pair.

- [X] T030 [US3] In `packages/aoa-maxitor/client/scripts/check-layout-determinism.ts` add a follow case: two contexts per directed pair of Chromium, Firefox, WebKit; the leader pans and hovers, the follower's centre and hover must match within 2 px / the same element, and the follower must show the leader's hover within 0.5 s (SC-002); include the switch from one person to another (R7). Done: `followCase` in `check-layout-determinism.ts`, one directed pair at a time — the leader drags the ERD, the follower must stop centred on the same diagram point within 2 px, then light the leader's hovered table within 500 ms (a hover that never shows is reported after 2 s, not waited for). The switch between people moves to phase 7 with the overlap it belongs to (T036).
- [X] T031 [US3] Run it, record which pairs fail and why (here, with the evidence), fix the cause in `packages/aoa-maxitor/client/src/rooms/` (suspects in research R4), and re-run until all six pass. Done, nothing to fix: with the current build following works in all six pairs, started with the keyboard and with the mouse alone (hover the circle, reach Follow, click) — `screens apart 0.000 px, hover after 14–43 ms` everywhere. The failure reported on the live stand (2.3.0, before the glide of phase 5) did not reproduce in headless Firefox. A first measurement showed WebKit-led followers 151–302 units short: the probe read the follower before the leader's last screen had arrived (one 6 px drag step at 4 % zoom ≈ 151 units); waiting one second after the release, every pair agrees exactly.
- [X] T032 [US3] Adversarial check: reintroduce the cause → only the Firefox pairs fail. Restore. Done: a Firefox follower that does not move, then one that shows no hover — each time exactly the two Firefox-follower pairs printed DIFF; restored, all six ok.
- [X] T033 [US3] Acceptance on the local stand in Firefox and Chrome (quickstart "Firefox follow"); prepare commit 6: `fix(maxitor): following works in Firefox (#282)`. Tick issue phase 5. Committed as `77da106f`; issue phase 5 ticked.

---

## Phase 7: Room controls in Maxitor's style (commit 7) · US5

**Goal**: 16 px icons, 32 px icon buttons, 22 px circles that never touch; a clean switch (FR-050 … FR-052; R6, R7).

**Independent Test**: measured sizes; no ring touches a neighbour; switching whom you follow overlaps nothing.

- [X] T034 [P] [US5] `packages/aoa-maxitor/client/src/rooms/RoomBar/RoomBar.tsx`, `RoomBanner.tsx`: menu button 32 × 32 with an ~18 px glyph; banner and menu icons 16 px. Done: the compact menu button 32 × 32 (glyph 18); banner icon 16; the row buttons' icons 16 (`ROW_BUTTON_SX`, they were 14); the card's circle 24, the +N list's 20, the edge arrow's 22.
- [X] T035 [P] [US5] `packages/aoa-maxitor/client/src/rooms/Circles/Avatar.tsx`, `Circles.tsx`: room-bar circle 22 px inside a 29 px box that takes layout space; your ring is the box's border; the focus ring drawn inside the box; boxes 4 px apart. Done: `ringedBox(22) = 29` in `Avatar.tsx` — the ring is an inset 1.5 px shadow with a 2 px gap inside the box; the focus ring has `outlineOffset: -2`; the follower count sits at `right: 0`; the +N chip is 22 in the same box.
- [X] T036 [US5] Reproduce the overlap on switching (follow A, *Follow B instead* in B's card) in the browser, record it here, fix it in `ParticipantCard.tsx` / `FollowFrame` / `Circles.tsx`. Done: photographed in a three-person room on the local stand — Boris's card opened straight over the *Following Anna* pill. The pill now steps aside while a participant card or the +N list is open (`rooms/participantCardOpen.ts`); the card offers *Stop following* and *Follow … instead* itself.
- [X] T037 [P] [US5] Tests `packages/aoa-maxitor/client/src/rooms/Circles/Circles.test.tsx`: box sizes and gaps, rings inside the box; and a geometry check in the cross-engine script: no two circle boxes overlap with every ring combination. Done: `Circles/Circles.test.tsx` (sizes, inset ring, focus ring inside, count inside, the pill stepping aside) and `circleGap` in the cross-engine follow case — the leader's own ring, its follower count and a focus ring on the follower's circle at once: 4.0 px apart in all six pairs.
- [X] T038 [US5] Adversarial check: move the ring back to `box-shadow` outside → the overlap check fails. Restore. Done: the focus ring back at offset 3 → the unit test and `circles -1.0 px apart` DIFF in every pair; the pill always visible → its test; restored, client 175 passed.
- [X] T039 [US5] Acceptance on the local stand (quickstart "Room controls"); prepare commit 7: `style(maxitor): room controls in Maxitor's sizes, circles that never touch (#282)`. Tick issue phase 6. Committed as `af9166ad`; issue phase 6 ticked.

---

## Phase 8: ERD card as in the mockup (commit 8) · US6

**Goal**: header flush with the outline, the mockup's corner curve (FR-032; R8).

**Independent Test**: the ERD style check measures no gap and the radius within 0.5 px.

- [X] T040 [US6] In `packages/aoa-maxitor/client/src/lib/buildDotSource.ts` draw tables with no outline and no header fill (`BORDER="0"`), keeping cells, sizes and ports. Done differently, to keep every cell's place: the DOT is unchanged (a border-less table would move every cell by a unit and every layout with it); the post-pass replaces what Graphviz draws instead (T041).
- [X] T041 [US6] In `packages/aoa-maxitor/client/src/lib/erdPostPass.ts` draw each card beneath its cells from the table's bounding box: one rounded rectangle (radius 9 px at 100 %, stroke 1.4, the domain colour) and the header as a path with the same top radius filling to the outline; row tints stop 1 px inside the outline. Done as `drawErdCards` in `lib/erdPostPass.ts`, run after `containNodeFills` (which the use-case and lifecycle cards keep): Graphviz's backdrop and its rounded outline (radius 12, 1 wide) give way to `rect`s of radius 9 (`ERD_CARD_RADIUS`) with a 1.4 outline (`ERD_CARD_STROKE`); the fills that stopped one unit inside the outline now reach it, and every fill — header and rows — is clipped by the same rounded rectangle. A card ends where the next group of the drawing begins, so lines (`re<k>`) are never touched.
- [X] T042 [US6] In `packages/aoa-maxitor/client/scripts/check-erd-table-style.ts` add: no gap between header and outline; outline and header share the radius within 0.5 px; re-check the identical-layout hashes of spec 028 still match (`check-layout-determinism.ts`). Done: `check-erd-table-style.ts` asserts the header reaches the outline (side and top), the outline is radius 9 and 1.4 wide in the domain colour, the body is the card's own shape, the header's clip is the outline's rectangle (SC-007, within 0.5), every fill is clipped, Graphviz's outline is gone; the header height now counts the unit under the outline (31). `check-erd-kinds-and-lines.ts` runs the same pipeline. The cross-engine check shows no DIFF: layouts unchanged.
- [X] T043 [US6] Adversarial check: give the header a 2 px inset → the gap assertion fails. Restore. Done: fills stopping inside the outline, the clip keeping Graphviz's curve, the step reaching into lines — each failed its own assertion; restored, all pass.
- [X] T044 [US6] Acceptance on the local stand (quickstart "ERD card"); prepare commit 8: `style(maxitor): the ERD card drawn as in the mockup (#282)`. Tick issue phase 7. Committed as `67d41128`; issue phase 7 ticked.

---

## Phase 9: Kind icon on the name's axis (commit 9) · US6

**Goal**: the icon's centre on the name's visual centre line (FR-033; R9).

- [X] T045 [US6] In `placeKindIcons` (`erdPostPass.ts`) centre the icon at `baseline − 0.36 × fontSize` and centre the pair in the header band. Done: the axis is the middle of the header band; the glyph's centre is put on it and the name's baseline at `axis + CAP_HALF_EM × font size` (`CAP_HALF_EM` = 0.359, half Helvetica's 0.718 em cap height). Measured before: the name's capitals stood 1.2 units above the glyph's centre (the issue had the direction wrong; spec and issue corrected).
- [X] T046 [US6] In `check-erd-table-style.ts` measure the icon's centre against the name's bounding-box centre (≤ 0.5 px) for every table of the reference ERD. Done in `check-erd-table-style.ts`, for every table, within 0.1 (the placement is exact; 0.5 could not see the old glyph's 0.2 offset).
- [X] T047 [US6] Adversarial check: restore the top-of-cell placement → only the axis assertion fails. Restore. Done: the glyph from the top of its cell → `icon -101.50, name -101.30`; the name on Graphviz's baseline → `name -102.51` — each failed for both tables; restored, all pass.
- [X] T048 [US6] Acceptance on the local stand (quickstart "Icon axis"); prepare commit 9: `style(maxitor): the kind icon on the table name's axis (#282)`. Tick issue phase 13. Done — committed on the maintainer's standing instruction to go on phase after phase.

---

## Phase 10: Clean field types (commit 10) · US6

**Goal**: every field type reads as one clean name; the full annotation in the tooltip (FR-030, FR-031; R10; contracts/graph-interchange.md).

**Independent Test**: all 39 demo types follow the FR-030 table; an old-form string is cleaned by the client.

- [X] T049 [P] [US6] Create `packages/aoa-action-machine/src/aoa/action_machine/graph/field_type_label.py`: `field_type_label(annotation) -> str` by the FR-030 table, pure and idempotent ("`clean(clean(x)) == clean(x)`"), with the AI-CORE block moved from `EntityFieldGraphNode.pretty_annotation` (constitution IV debt). Done; the rule is written as two tables (forms by their arguments, containers by what they hold), and a parametrised pydantic model (`Generalization`, `Specialization`) is read through `__pydantic_generic_metadata__`, which `get_origin` does not see. A many-relation reads `X[]`.
- [X] T050 [US6] In `packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_field_graph_node.py`: `field_type` = `field_type_label(annotation)`, new property `field_annotation` = today's `pretty_annotation`; update the graph JSON schema if it lists node properties. Done; `to_dict` ships `field_annotation`, and the graph JSON schema lists it.
- [X] T051 [P] [US6] Tests `packages/aoa-action-machine/tests/graph/test_field_type_label.py`: one case per table row (including `Optional[str]`, `Union[str, None]`, `str | None` → `str | None`; `AssociationOne[X]` → `X`; `Specialization[A | B, K]` → `A | B`; `list[X]` → `X[]`; `Literal["a", "b"]` → `"a" | "b"`), idempotence, and every type of the demo model contains no `UnionType`, `NoneType`, `Union[`, `AssociationOne[` or `Generalization[`. Done in `tests/action_machine/graph/test_field_type_label.py`: 24 table rows, internals never leak, the vertex ships both (29 tests; the specialization fixtures come from `test_entity_specialization_graph.py`). On the demo model three types change: `AssociationOne[CurrencyEnumEntity]` (26 fields) → `CurrencyEnumEntity`, `Generalization[…]` → its head, `Specialization[Union[A, B], K]` → `A | B`.
- [X] T052 [US6] Maxitor: carry `field_annotation` in `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py` (column, nullable for older services) and `list_entities_action.py` (`fields[].annotation`). Done: a nullable `field_annotation` column, `fields[].annotation` in every branch of the query and in the response schema; two older tests now list the new key.
- [X] T053 [P] [US6] Create `packages/aoa-maxitor/client/src/lib/fieldTypeLabel.ts`: `cleanFieldType(raw: string): string` parsing the old forms, idempotent on clean labels; use it in `buildDotSource.ts` for the type cell; the tooltip shows `annotation`, else the raw string; long labels cut with `…`. Done, but in `lib/buildDotSource.ts` itself rather than a module of its own: the drawing checks run that file in plain Node, where it may import no value. `cleanFieldType` splits on top-level brackets; `fitFieldType` cuts at 40 characters.
- [X] T054 [P] [US6] Tests `packages/aoa-maxitor/client/src/lib/fieldTypeLabel.test.ts` (each old form → its clean label; idempotence) and `packages/aoa-maxitor/tests/` for `fields[].annotation`. Done: `src/lib/fieldTypeLabel.test.ts` (18 old forms, 6 clean names unchanged twice, the cut, the type cell and its tooltip — 26 tests) and `test_a_field_row_carries_its_clean_type_and_its_full_annotation`. `check-erd-kinds-and-lines.ts` needed a longer type to keep its wide table wide.
- [X] T055 [US6] Adversarial check: drop the `None`-last rule → only its cases fail; skip the client cleaning → only the old-form tests fail. Restore. Done: `None` not last, the client not cleaning unions, the type cell skipping the cleaning — each failed exactly its own tests; restored: aoa-action-machine 3072, aoa-maxitor 319 / 1 skipped, aoa-demo 79, client 201, every ERD drawing check passes.
- [X] T056 [US6] Acceptance on the local stand (quickstart "Clean field types"); prepare commit 10: `feat(aoa): field types as one clean name, the full annotation beside it (#282)`. Tick issue phase 12. Done — committed on the standing instruction; the stand is rebuilt with the next phases.

---

## Phase 11: ERD line ends and direction (commit 11) · US7

**Goal**: true cardinality with optionality; reference lines the right way (FR-043; R11).

- [X] T057 [US7] In `packages/aoa-action-machine/src/aoa/action_machine/intents/entity/` record a relation's optionality (annotation admits `None` or default `None`) and expose it as `optional` in `graph/edges/entity_graph_edge.py`; tests in `packages/aoa-action-machine/tests/`. Done: `EntityRelationIntentResolver.optional` = the field is nullable, or not required with a `None` default; the relation edge ships it (`optional`, default false) and the schema lists it. Test `tests/action_machine/graph/test_relation_optional.py` with an `Annotated[AssociationOne[…] | None, NoInverse()]` field. On the demo model all 278 relations are mandatory, so zero-or-one ends appear only where a model declares them.
- [X] T058 [US7] In `packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py` store `optional`; in `list_entities_action.py` return `one` / `zero_one` / `zero_many` / `one_many` and make reference lines `zero_many` at the referring table, `one` at the dictionary; update the example comment and `packages/aoa-maxitor/tests/`. Done: an `optional` column (default false, so an older service reads as mandatory); ends `one` / `zero_one` / `zero_many` (`one_many` stays reserved — no model declares a minimum); reference lines now `zero_many` at the referring table and `one` at the dictionary. `test_a_reference_field_is_a_relation_entry` pinned the old, reversed direction and now pins the right one; new `test_an_optional_relation_end_is_zero_or_one_and_a_mandatory_one_is_one`.
- [X] T059 [US7] In `buildDotSource.ts` map ends to Graphviz shapes (first nearest the table): `one` → `teetee`, `zero_one` → `teeodot`, `zero_many` → `crowodot`, `one_many` → `crowtee`; tune `arrowsize` / `penwidth` for readability; keep the UML field-label placement and generalization style. Done: `ERD_ENDS` maps the four values to `teetee`, `teeodot`, `crowtee`, `crowodot`; the existing `arrowsize=0.7` keeps a double end readable (photographed on the stand).
- [X] T060 [US7] In `check-erd-table-style.ts` assert on the reference ERD: each end's shape matches its relation; every reference line's crow's foot is at the referring table; refresh the golden of `check-erd-dictionary-values.ts` on purpose. Done in `check-erd-kinds-and-lines.ts` (where the line fixture lives): the paired line `crowodot`/`teetee`, an optional end `teeodot`, a reference `crowodot` at the referring table, and every end one of the four. `check-erd-dictionary-values.ts` passes unchanged — its golden holds no ends.
- [X] T061 [US7] Adversarial check: swap the reference ends back → only the direction assertion fails; map `zero_one` to `teetee` → only the optionality assertion fails. Restore. Done: references reversed, zero-or-one drawn as exactly one, optional never set, optional not read by Maxitor — each failed exactly its own test; restored: aoa-action-machine 3073, aoa-maxitor 320 / 1 skipped, aoa-demo 79, client 201.
- [X] T062 [US7] Acceptance on the local stand (quickstart "ERD line ends"); prepare commit 11: `fix(maxitor): ERD line ends show true cardinality, reference lines point the right way (#282)`. Tick issue phase 9. Done — committed on the standing instruction.

---

## Phase 12: ERD hover lights joined tables (commit 12) · US7

- [X] T063 [US7] In `bindLineHover` (`erdPostPass.ts`) give the tables at both ends of the hovered line, or of every line of the hovered row, the hovered-table class, so they stay bright while the rest dims (FR-040, FR-041; R12). Done: `focusTables(root, tables, lines?)` and `clearTableFocus` in `lib/erdPostPass.ts` are now the one rule for a hovered table (the canvas uses them instead of its own loop), a hovered key row (its table plus every table its lines join) and a hovered line (the two tables it joins; everything bright again on leave). A follower gets the same, since it replays the same `mouseenter`.
- [X] T064 [US7] Test in `packages/aoa-maxitor/client/src/lib/erdPostPass.test.ts`: hovering a PK row, an FK row and a line brightens exactly the joined tables; table hover unchanged. Done in `src/lib/erdPostPass.test.ts`: table, FK row, PK row and line — 4 tests.
- [X] T065 [US7] Adversarial check: brighten only the hovered table → the test fails. Restore. Done: a row lighting only its own table and a line dimming nothing — each failed exactly its own tests; restored, client 205, ERD checks pass.
- [X] T066 [US7] Acceptance on the local stand (quickstart "ERD hover"); prepare commit 12: `feat(maxitor): hovering a key or a line lights every table it joins (#282)`. Tick issue phase 8. Done — committed on the standing instruction.

---

## Phase 13: ERD line labels on hover (commit 13, redone) · US7

**Goal**: the field names at the ends of ERD relation lines show only while the line is hovered, on a plate that keeps them readable (FR-042). The first commit of this phase (`add4ba62`) hid the use-case diagram's actor names instead — a misreading of remark 10, corrected by the maintainer 2026-10-27; it is reverted here.

- [X] T067 [US7] Revert `add4ba62` (use-case actor names show again); in `packages/aoa-maxitor/client/src/lib/erdPostPass.ts` add `addEndLabelBadges` (a white, rounded plate under every line label) and `erdEndLabelSx` (labels and plates hidden unless the line has `is-hovered`), used by `ErdGraphvizCanvas.tsx`. A line's own hover, a key row's hover and a follower's replayed hover all set `is-hovered`, so all three show the labels. Done.
- [X] T068 [US7] Tests in `src/lib/erdPostPass.test.ts` (one plate per label, once; hidden until hovered); breaks: labels always shown, no plates — each failed exactly its own test; restored, client 209. On the stand: 0 of 281 labels visible with nothing hovered; a hovered line shows its `audit_log` label on its plate.
- [X] T069 [US7] Prepare commit 13: `style(maxitor): ERD line labels appear on hover, readable on a plate (#282)`. Done — committed on the standing instruction.

---

## Phase 14: *Kinds* lists the diagram's kinds (commit 14) · US7

- [X] T070 [US7] In `ErdGraphvizCanvas.tsx` / `ErdFilterPanel.tsx` build the *Kinds* list from the tables shown before the kind filter (after domain and one-hop), with names from `list-entity-kinds`; a kind switched off stays listed (FR-044; R14). Done: `ErdGraphvizCanvas` keeps the tables shown before the kind filter (`beforeKinds`: domains or qualifiers, one-hop) and filters kinds from it; the *Kinds* rows come from `kindsOnDiagram(list-entity-kinds, beforeKinds.entities)` in `lib/erdKindFilter.ts`, in the named order.
- [X] T071 [US7] Test in `packages/aoa-maxitor/client/src/lib/erdKindFilter.test.ts`: a diagram missing kinds lists only its own; a switched-off kind stays; adversarial check by listing all kinds. Restore. Done in `src/lib/erdKindFilter.test.ts` (2 tests); break: listing every kind → both fail; restored, client 210. The canvas wiring itself has no unit test (the component is not rendered in tests) — it is checked on the stand.
- [X] T072 [US7] Acceptance on the local stand (quickstart "Kinds filter"); prepare commit 14: `feat(maxitor): the Kinds filter lists only the diagram's kinds (#282)`. Tick issue phase 11. Done — committed on the standing instruction.

---

## Phase 15: Maxitor serves its own graph (commit 15) · US4

**Goal**: Maxitor's address opens Maxitor's diagram; `ETag` / `304` (FR-060, FR-061; R15).

- [X] T073 [P] [US4] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/own_model_graph_resource.py`: `OwnModelGraphResource` holding Maxitor's coordinator, rendering `to_json()` once per process. Done.
- [X] T074 [P] [US4] Create `packages/aoa-maxitor/src/aoa/maxitor/model/core/actions/get_own_graph_json_action.py`: `GetOwnGraphJsonAction` returning `{"coordinator_json": …}` through the resource (`@check_roles(GuestRole)`, `@meta` in Maxitor's core domain). Done.
- [X] T075 [US4] Route `GET /examples/model/graph-json` to it in `app.py` with the resource as its connection. Done: a third adapter app mounted at `/examples/model` (before the static bundle), with the resource built from `machine.graph_coordinator`.
- [X] T076 [US4] Tests `packages/aoa-maxitor/tests/test_own_graph_json.py`: `200` with Maxitor's own actions in the graph (e.g. `JoinRoomAction`); an `ETag`; `304` with no body on `If-None-Match`; no `source` needed; loading Maxitor's own address through `load_aoa_service_action` builds a graph. Done in `tests/test_own_graph_json.py`: no `source`, the room and diagram actions in the graph (26 actions), the `ETag` and `304`, and the answer builds as a DuckDB graph with `RoomsDomain` and `CoreDomain` — 3 tests.
- [X] T077 [US4] Adversarial check: make the resource render a body with a timestamp on every call → only the `304` test fails; remove the route → only the route tests fail. Restore. Done: a timestamp in every answer → only the `304` test fails; no route → the three route tests fail; restored, aoa-maxitor 323 / 1 skipped.
- [X] T078 [US4] Acceptance on the local stand (quickstart "Maxitor's own graph"); prepare commit 15: `feat(maxitor): Maxitor serves and shows its own graph (#282)`. Tick issue phase 14. Done — committed on the standing instruction; checked on the stand with the next rebuild.

---

## Phase 16: The demo on the fresh adapter (commit 16) · US4

- [X] T079 [US4] In `packages/aoa-demo/pyproject.toml` require `aoa-fastapi-adapter>=1.3.0` and raise the version; `uv lock`; a test in `packages/aoa-demo/tests/` that `graph-json` answers with an `ETag` and `304` (FR-061, FR-062; R16). Done: `aoa-fastapi-adapter>=1.3.0` in the demo's `fastapi` extra (the lock is unchanged — workspace packages carry no specifier there); the version rises with the other packages in T084, so the release raises all three at once. Test `tests/fastapi_mcp_services/test_graph_json_freshness.py`; break: the adapter without `ConditionalGetMiddleware` → it fails; restored, aoa-demo 80.
- [X] T080 [US4] Acceptance: `curl` the local stand's demo (`http://127.0.0.1:8100/examples/model/graph-json`) twice → `304`; prepare commit 16: `chore(demo): serve graph-json with an ETag through the fresh adapter (#282)`. Tick issue phase 15. Publishing `aoa-demo` and redeploying `demo.aoa.run` wait for the maintainer's command (T086). Done: the local stand's demo answers with an `ETag` and `304`; committed on the standing instruction. Publishing `aoa-demo` and redeploying `demo.aoa.run` wait for the maintainer (T085, T086).

---

## Phase 16a: The participant card's buttons never overlap (commit 16a) · US5

**Goal**: with a long name, *Go to …* and *Follow … instead* stand side by side when they fit and wrap to the next line when they do not; a name too long for one line ends with `…`, the whole in the button's tooltip (FR-052). Added 2026-10-27 from the maintainer's screenshot: phase 7 fixed the pill over the card, not the card's own buttons.

- [X] T087 [US5] In `packages/aoa-maxitor/client/src/rooms/ParticipantCard/ParticipantCard.tsx` let the button row wrap and each button shrink to the card's width with its label cut by `…` and the full label as `title`. Done: the button row wraps; each button may shrink to the card (`minWidth: 0`, `maxWidth: 100%`) and its label is one line cut with `…`, the full label as `title`.
- [X] T088 [US5] Geometry check in a real browser: in the cross-engine follow case the leader's name is 40 characters, and the follower's card buttons must stay inside the card and never overlap; plus a test that a long label keeps its full text as the tooltip. Adversarial check: the old non-wrapping row → the check fails. Restore. Done in the cross-engine follow case (the leader is named 40 characters; the follower's card is measured before Follow): `card buttons overrun 0.0 px` in all six pairs; the old non-wrapping row → `overrun 144.8 px`, DIFF. The tooltip is the `title` attribute in the markup; no separate unit test, since the card needs a live anchor to render.
- [X] T089 [US5] Prepare commit 16a: `fix(maxitor): the participant card's buttons never overlap (#282)`; record it in issue #282. Done — committed on the standing instruction.

---

## Phase 16b: Specialization tables of one block share one width (commit 16b) · US6

**Goal**: the tables of a specialization block (one Graphviz cluster, e.g. *kind (by EventKindEnumEntity)*) are all as wide as the widest of them, so the block reads as one column (maintainer's screenshot, 2026-10-27).

- [X] T090 [US6] In `packages/aoa-maxitor/client/src/lib/buildDotSource.ts` give every table of a specialization cluster the header width of the cluster's widest table — measured from the tables' text the way Graphviz sizes them, or by laying the cluster out once — so each card in the block has one width; tables outside clusters keep their own width. Done by laying the blocks' tables out once on their own: `buildBlockMeasureDot` (those tables alone, no lines, no blocks), `erdBlockWidths` (each block's widest header, from that drawing) and `buildErdDot(data, layout, measure)`, which the canvas and the drawing checks call; the widths go into each header cell's `WIDTH`. Graphviz sizes text the same in every engine, so layouts stay identical.
- [X] T091 [US6] In `packages/aoa-maxitor/client/scripts/check-erd-kinds-and-lines.ts` (the fixture with a specialization container) assert that every card of the block has the same width, equal to the widest; adversarial check: drop the shared width → the assertion fails. Re-check that layouts still agree across engines. Done: `BankSpecEntity` in the fixture is made wide (402 pt alone), and both cards of its block measure the same width, equal to it, while a table outside a block keeps its own; dropping the shared width → `Card 212, Bank 402.11`, FAIL. The cross-engine check: 0 DIFF, 56 page-modes.
- [X] T092 [US6] Prepare commit 16b: `style(maxitor): specialization tables of one block share one width (#282)`; record it in issue #282. Done — committed on the standing instruction.

---

## Phase 16c: ERD hover exactly as the maintainer specified (commit 16c) · US7

**Goal** (maintainer, 2026-10-27): **scenario 1** — the pointer on a table anywhere but a PK or FK field: every other table dims, and every line not connected to this table dims. **Scenario 2** — the pointer on a PK or FK field: that field's lines become bold; the tables they join stay bright; every other table dims; the hovered table's other lines stay as they are (neither bold nor dimmed); every line not connected to the hovered table dims. Phase 12 dimmed the hovered table's other lines in scenario 2.

- [ ] T093 [US7] In `packages/aoa-maxitor/client/src/lib/erdPostPass.ts` (`bindLineHover`, `focusTables`): on a key row, keep bright the joined tables and every line touching the hovered table, bold only the field's lines, dim the rest; leaving the row returns to scenario 1.
- [ ] T094 [US7] Tests in `src/lib/erdPostPass.test.ts` for both scenarios line by line (which tables and lines are bright, bold, dimmed); adversarial check: dimming the table's other lines → fails. Check on the stand.
- [ ] T095 [US7] Prepare commit 16c: `fix(maxitor): ERD hover as specified for tables and key fields (#282)`; record it in issue #282.

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
