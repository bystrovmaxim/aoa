# Tasks: Maxitor Opens a History and Shows Any Version

**Input**: Design documents from `specs/037-history-one-version/`

**Prerequisites**: plan.md, spec.md (US1–US5, FR-001 – FR-032, modes M1–M7 in FR-009a), research.md (R1–R19), data-model.md, contracts/ (maxitor-api.md, port.md, room-protocol.md, ui.md), quickstart.md, checklists/ (requirements.md, key-secrecy.md, modes.md)

**Tests**: Required. Every new test is verified adversarially: break the code the way the test must catch, confirm that test fails and no other does, restore. Every mode M1–M7 has a server test and a client test.

**Organization**: one phase = one commit. Commit 1 holds the design documents; commits 2–7 are #289's phases 1–6; #289's phase 7 is three commits (check run, documentation, changelog), commits 8–10. A commit is made only on the maintainer's word (constitution I). The full check run is run after code changes only, not after documentation edits.

**Issue checkboxes**: commit 2 → phase 1; 3 → 2; 4 → 3; 5 → 4; 6 → 5; 7 → 6; commits 8–10 → phase 7 (ticked after commit 10). Every tick carries its sha (`gh issue edit 289`, the body fetched and checked for length before it is written back).

**Paths**: `F` = `packages/maxitor/front`, `FS` = `F/src/maxitor/front`, `FT` = `F/tests`, `FC` = `F/client/src`, `P` = `packages/maxitor/tools/repo_graph_port`, `PS` = `P/src/maxitor/repo_graph_port`, `PT` = `P/tests`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story of spec.md (US1–US5)
- Every new Python module opens with its path, a title line and `PURPOSE` / `ARCHITECTURE / DATA FLOW` (constitution III); every public action, resource, store and coordinator carries an AI-CORE block (IV); every class, function and method a one-line docstring (V), TypeScript included. Every new client component folder has `index.ts` and a `README.md` beside it (the check run's README step). Every endpoint is an action; the port is reached only through a resource. The key is never in a URL, a log, an error, a `repr` or a source string (FR-010b, FR-011 – FR-011b).

---

## Phase 1: Setup — design documents (commit 1)

- [X] T001 Prepare commit 1 with `specs/037-history-one-version/` only (spec, plan, research, data model, contracts, quickstart, `checklists/requirements.md`, `checklists/key-secrecy.md`, `checklists/modes.md`, tasks; `tasks.ru_draft.md` stays out): `docs(spec): specify opening a history in Maxitor (#289)`.

---

## Phase 2: Reading a history (commit 2) · US1, US2 (server) — #289 phase 1

**Goal**: Maxitor's server opens a history through a port, holds each version once, keeps the list fresh, keeps keys out of every log, and rooms carry a version (FR-001 – FR-011f, FR-022a, research R1–R9, R16, R18, R19; contracts maxitor-api.md, port.md, room-protocol.md).

**Independent test**: quickstart steps 1–6; server tests for M1–M7.

- [ ] T002 Baseline: `bash scripts/run_checks_with_log.sh` on the branch at `84718546`; record the `OK` count and wall time here.
- [ ] T003 [US1] The port (contracts/port.md, research R5): `PS/history.py` — `History` gains `live: str | None = None`; `PS/resources/histories_config.py` `_history` reads the optional `live` and refuses the file when it is not an `http`/`https` URL with a host ("history <id> has live <value>; an http(s) URL is needed"); `PS/actions/describe_history_action.py` — `DescribeHistoryResult` gains `live: str | None` (from the history; always `None` for a public link) and `reader: str | None` (the key's name from the context; `None` for a public link).
- [ ] T004 [US2] The port's security events (FR-011f, research R19): every wrong key → `box.warning` on `Channel.security`, `Wrong key for history <id> from <client>`; every webhook with a wrong signature → `box.warning`, `Webhook with a wrong signature from <client>`; every block (the eleventh wrong key within a minute, `PS/auth/history_key_auth_coordinator.py`) → `box.critical`, `Blocked <client> for a minute: <n> wrong keys`. The coordinator and `PS/webhook_signature_middleware.py` run outside an action, so each hands a typed event to an action of the port that logs it through its `box`; never the key, its hash or the signature.
- [ ] T005 [P] [US1] `PT/test_live_and_reader.py`: `live` in the config comes back from `describe`, absent when not configured and for a public link; a `live` that is not an http(s) URL refuses the file (`history check` exits 2); `reader` is the key's name. `PT/test_security_events.py`: a wrong key, a bad webhook signature, the block each write their line on `security` at their level (`caplog`), and none contains the key, its hash or the signature. Adversarial: return `live` for a public link → only the public test fails; log the block at `warning` → only the block test fails. Restore. Record here.
- [ ] T006 [P] [US1] `FS/model/core/history_address.py` (pure, no I/O): parse what the field holds into `PrivateHistory(port, id, key)` (`<port>/api/v1/history/<id>#key=<key>`; the key is everything after `#key=`, trimmed; a second `#` refused with the reason), `PublicHistory(link)` (`https://github.com/<owner>/<repo>/blob/<branch>/<path>`; another host, a folder or a branch page refused with the reason) or `None` (a service or graph-json address, M1); `name_of(...)` — the address without the key; `title_of(...)` — `id` or `owner/repo`. `FS/model/core/source_label.py`: `label(address)` → `<origin>#<first 8 hex of SHA-256 of the whole address>`.
- [ ] T007 [US1] `FS/model/core/resources/repo_graph_port_gateway.py` — `RepoGraphPortGateway(BaseGateway)`: `describe(port, id | link, key)`, `versions(port, id | link, key, etag)` → `Versions | NotModified | NotFound | TooManyWrongKeys | Unreachable`, `version_url(port, id | link, sha)` (research R4, keyless); the key sent only as `X-Maxitor-History-Key`; `__repr__` names nothing; one `httpx.AsyncClient`, closed by `aclose`. `FS/model/core/resources/graph_source_gateway.py` — `fetch` and `fetch_if_changed` take an optional `key`, sent as the same header.
- [ ] T008 [US1] `FS/api/history_store.py` — `HistoryStore` and `HistoryEntry` (data-model "HistoryEntry": `name, port, id|link, title, repository, host, live, reader, versions, etag, last_checked, checking, keys`; `keys` in memory only, newest first, never in `repr`); single flight per history name; `max_histories = 50`, least recently read leaves. `FS/model/core/resources/history_access.py` — `HistoryAccess`: `(history name, SHA-256 of key) → accepted_at`, valid 30 s (research R6); room tickets — 128 random bits, 60 s, one use, bound to `(history name, SHA-256 of key)` (research R18); never holds a key.
- [ ] T009 [US1] Public links through Maxitor's own port (FR-003b, research R16): `MAXITOR_PUBLIC_PORT` read where the app is built (`FS/api/app.py`), never in an action; unset → a public link is refused with "Public histories are not set up on this Maxitor"; the port's address is never in an answer.
- [ ] T010 [US1] `FS/model/core/actions/open_history_action.py` — `OpenHistoryAction` and `FS/model/core/actions/history_versions_action.py` — `HistoryVersionsAction` (contracts/maxitor-api.md): frozen `Params`/`Result`, logic in aspects, the gateway, `HistoryStore` and `HistoryAccess` through connections; the answer `{name, title, host, repository, live, versions, count, room_ticket}` (`room_ticket` only for a private history), `ETag`, `304`; refusals `400` (address out of shape, the address not echoed), `404 not found` (FR-009), `429` "Too many wrong keys for this history; try again in a minute" with no retry, `503` "The history cannot be read now." with `Retry-After: 5`. Every failed attempt → `box.warning` on `Channel.security` naming the port's origin, the history `id` and the client's address (FR-011e).
- [ ] T011 [US1] `FS/api/app.py`: the sub-app `/api/history` (outside `GraphSourceMiddleware`) over the two actions, with an auth coordinator that extracts `X-Maxitor-History-Key` into the request's context as a sensitive value (the front's other sub-apps keep `NoAuthCoordinator`); `HistoryStore`, `HistoryAccess` and the gateway built and closed in the lifespan. `FS/api/main.py`: uvicorn's access log as method, path and status, never the query (research R3).
- [ ] T012 [US1] `FS/api/graph_source_middleware.py` — for a version source (`<port>/api/v1/history/…/versions/<sha>…`): read the key header; `HistoryAccess` accepted within 30 s, else ask the port (`304` → accepted, `404` → `404 {"detail": "not found"}`); a version the held list marks `refused` → `422` with the port's reason; then `store.acquire(source, key=…)`. `FS/api/graph_store.py` — `acquire`/`reload` take an optional `key` handed to the builder on a first build only; `GraphEntry.immutable` (true for a version). `FS/model/core/freshness.py` — `is_due` never picks an immutable entry.
- [ ] T013 [US1] `FS/model/core/actions/load_aoa_service_action.py` — `validate_service_aspect` accepts the envelope (`coordinator_json`, a string) or a bare graph (an object with `nodes` and `edges` at the top); the parse aspect takes whichever came; every error names the source by `label()`, never `{url!r}` (FR-011a).
- [ ] T014 [US1] `FS/model/core/actions/check_history_action.py` — `CheckHistoryAction`: `If-None-Match` with the held `ETag`; `304` → `last_checked` only; `200` → the entry replaced, and every room of that history gets `{"type": "history_changed"}`; a version gone from the list or `live` removed → the rooms on it move by the edge cases (spec). `FS/model/core/actions/check_due_sources_action.py` — also picks held histories that a tab or a room looks at and whose last check is 30 s old. `FS/model/core/actions/check_source_action.py` and every other log line naming a source: `label()`, never the address.
- [ ] T015 [US1] Rooms (contracts/room-protocol.md, research R9, R18): `FS/model/rooms/resources/room_registry.py` — `Room.history`, `Room.version`, `snapshot()` carries both; `FS/model/rooms/actions/join_room_action.py` — opens a room on `history` + `version`; for a private history requires `ticket` (missing, used, expired, foreign → the "not found" close code before `welcome`); the room's pages read with a remembered key `HistoryAccess` still accepts; `FS/model/rooms/actions/set_room_version_action.py` — `SetRoomVersionAction` for `{"type": "version", "b"}`: refuses a version the list lacks, a refused one, or `live` where there is none, to the sender alone; else sets `room.version`, broadcasts `{"type": "version", "b", "by"}`; the last wins. Register the message in `FS/api/app.py`'s room route.
- [ ] T016 [P] [US1] `FT/fixtures/stand_in_port.py` — a stand-in port over `httpx.MockTransport` serving histories for every mode (M2: 3 versions, one refused; M3: 1; M4: 3 + `live`; M5: 1 + `live`; M6: 0 + `live`; M7: 0; a public link), `ETag`/`304`, `404` for a wrong key, `429` after ten wrong keys, and an M1 service.
- [ ] T017 [US1] `FT/test_history_modes.py`: each of M1–M7 opens with the answer FR-009a gives it (count, `live`, versions); a bare graph-json address and a service are M1; a public link through `MAXITOR_PUBLIC_PORT` (M2, M3, M7), and refused when unset; a refused version → `422` with its reason; `b` of a missing version is the client's to correct (the server answers the list). `FT/test_history_access.py`: wrong key → `404`; `429` passed through with its text and no retry; a version built once for two keys; a key revoked at the stand-in port opens no held version after 30 s (SC-013); a room join without a valid ticket closes before `welcome`. `FT/test_history_freshness.py`: an unchanged list → `304`, no full read; a new version appears after one check; a version's entry is never due; `history_changed` reaches the room; a version gone moves the room. `FT/test_room_version.py`: one pick moves every participant; two picks at once end on one; a refused pick is refused to its sender only. `FT/test_load_bare_graph.py`: envelope and bare graph both load. Every version of the M2 and M4 histories, opened, has the node and edge counts the port lists for it (SC-002).
- [ ] T018 [US2] `FT/test_history_key_secrecy.py` (SC-004, SC-014): a session over every mode, a room join, a revoked key and the checks; the key searched in `caplog` of every channel, uvicorn's access log, every error body, every request URL the stand-in port and Maxitor received, every `repr` of the store, entry, access, gateway and coordinator — 0 matches; the security warnings present (FR-011e). Adversarial, full check run each: (1) log the whole source in `check_source_action.py` → only the secrecy test fails; (2) skip the `HistoryAccess` check → only the revoked-key test fails; (3) let `is_due` pick immutable entries → only the freshness test fails; (4) put the key in the version source → the secrecy test and the shared-build test fail, no other. Restore. Record here.
- [ ] T019 [US1] The stand (research R16): `deploy/stand/docker-compose.yml` — `maxitor-public-port` from `P/Dockerfile`, an empty histories config (`deploy/stand/maxitor-public-port/histories.toml`, no tables), its own cache volume, on Maxitor's internal network, no published port, health on `/health`; the `maxitor` service gets `MAXITOR_PUBLIC_PORT=http://maxitor-public-port:8102`; `docker-compose.local.yml` likewise; `deploy/stand/README.md` says what it is and that it serves public links only.
- [ ] T020 Check run green; prepare commit 2: `feat(maxitor): open a history through its port (#289)`; tick #289 phase 1.

---

## Phase 3: Read keys as dots (commit 3) · US2 — #289 phase 2

**Goal**: the key is never shown in full and never left in the browser's address bar (FR-010, FR-010a, FR-011c, FR-012).

**Independent test**: US2 scenarios 1–7.

- [ ] T021 [P] [US2] `FC/lib/historyAddress.ts`: parse as T006 does; `mask(address)` — the key as `••••••••` (eight dots, whatever its length), the rest readable; `withKey(link, key)` for **Copy link**.
- [ ] T022 [US2] `FC/lib/historyKey.ts`: on load, a `#key=` in `location.hash` is moved to `sessionStorage` under the history's name and removed with `history.replaceState` (no new entry); `keyFor(name)` reads `sessionStorage`, then Recent. `FC/api/history.ts`: `openHistory(name)`, `historyVersions(name, etag)` — the key only as `X-Maxitor-History-Key`; graph reads of a version source add the same header (`FC/api/client.ts` `graphFetch`).
- [ ] T023 [US2] `FC/components/navigation/LeftSidebar/ServiceUrlInput.tsx`: the field shows `mask()` while not edited; an eye button reveals the key until clicked again or the field loses focus (`aria-pressed`). `FC/lib/serviceUrlHistory.ts`: records `{address, kind, name?, versions?, live?}` (up to 10; an old string record reads as `kind: "service"`), shown by `mask()` with what each turned out to be (FR-009a's "Recent says"), each removable with its key. The room's link (`FC/rooms/RoomBar/`) shows `mask()`, copies the real key and carries `history` and `b`.
- [ ] T024 [US2] `FC/lib/historyAddress.test.ts`, `FC/lib/historyKey.test.ts`, `FC/components/navigation/LeftSidebar/ServiceUrlInput.test.tsx`: eight dots for keys of 8, 43 and 100 characters; the eye shows and hides, and hides on blur; Recent masks and removes; after load `location.href` holds no key and `history.length` did not grow; the copied link carries the key; page title and notices name the history, never its address (FR-011c). Adversarial: render the raw address in Recent → only the Recent test fails; `pushState` instead of `replaceState` → only the history test fails. Restore. Record here.
- [ ] T025 Check run green; prepare commit 3: `feat(maxitor): read keys shown as dots (#289)`; tick #289 phase 2.

---

## Phase 4: The version button and the picker (commit 4) · US1 (client) — #289 phase 3

**Goal**: the button, the picker with one track, the modes M1–M7 on screen, the address bar's `history`/`b`, rooms on the client (FR-009a, FR-013 – FR-022a, contracts/ui.md).

**Independent test**: quickstart step 3, every row.

- [ ] T026 [P] [US1] `FC/model/historyMode.ts`: `modeOf(history | null)` → `M1 … M7` from the list's length and `live` (never `describe`'s count). `FC/lib/versionNames.ts` (research R10): release = a tag with `release`; name = its tag, `<release> · #<pr>`, `#<pr>`, the first 7 of the commit, or `Live`; flags = tags without a release; tooltip = `#<pr> <title>`, date, `<nodes> nodes · <edges> edges`, tags, and "refused: <reason>".
- [ ] T027 [US1] `FC/components/history/VersionButton/` — `◷ <name> ▾` in M2–M6, nothing in M1 and M7; `aria-haspopup="dialog"`, `aria-expanded`. `FC/components/history/VersionPicker/` — over the diagram under the button; starts closed; closed by a click outside or Escape; choosing a version leaves it open; the head: name, the subtitle worded by FR-009a, **Copy link** (copies `withKey(?history=…&b=…, key)` for the shown version, "Link copied" confirms), the mode switch (One active; Diff and Side by side `aria-disabled="true"`, tooltip "comes later" on hover, focus and touch, a click does nothing). `FC/components/history/VersionTrack/` — the axis, oldest left, Live after a dashed gap; releases named and larger, merges as dots, flags above; refused points hollow; the handle `role="slider"`, `aria-valuetext` = the version's name; click, drag, ← → Home End by the mode table (nothing in M3 and M6). Each folder with `index.ts` and `README.md`.
- [ ] T028 [US1] `FC/app/App.tsx` and `FC/lib/urlState.ts`: a history's state (opened by `history` or the field), its mode, the chosen version; opens on Live (M4–M6, even when Live is unreachable, with the notice "Live cannot be reached; pick a version"), otherwise on the newest version not refused, or the newest when all are (FR-021); the page's title `<name> · <version name> — Maxitor` (FR-011c); the address bar `?history=…&b=<first 12 hex of the commit>` (no `b` in M7, `live` only in M4–M6), a wrong `b` corrected with `replaceState`; M7's workspace "This history has no version yet."; the button in the top row (`MainLayout` `topRow(false)`); the history list polled every 30 s with `If-None-Match` outside a room; moves between modes without a reload; `live` removed while on Live → the newest version, "Live is no longer part of this history"; the version gone → the default, "<name> is no longer in the history"; a missing page falls back as a link to a missing page does today; every link for a history `target="_blank" rel="noopener noreferrer"`.
- [ ] T029 [US1] Rooms on the client: `FC/rooms/protocol.ts` (`version`, `history_changed`, `welcome.room.history`/`version`), `FC/rooms/roomStore.ts`, `FC/rooms/useRoomSession.ts`, `FC/rooms/connection.ts` (`history`, `version`, `ticket` on the socket; never the key): a pick sends `{"type": "version", "b"}`; a `version` event moves the tab; `history_changed` reads the list again; a refusal is shown to the sender; the room's link carries the room's `b`.
- [ ] T030 [US1] `FC/model/historyMode.test.ts`, `FC/lib/versionNames.test.ts`, `FC/components/history/VersionTrack/VersionTrack.test.tsx`, `FC/components/history/VersionPicker/VersionPicker.test.tsx`, `FC/app/App.history.test.tsx`: every row of FR-009a's table for M1–M7 (button, opening version, subtitle, track, keys, workspace text); the ten moves between modes; names per R10 including before the first release; refused points hollow and their tooltip; unreachable Live; the switch's disabled modes; `history`/`b` restored and a wrong `b` corrected; a room's `version` event moves the tab. Adversarial: treat `live` as present when absent → only the M2/M3 tests fail; derive the mode from `describe`'s count → only the count-mismatch test fails. Restore. Record here.
- [ ] T031 Check run green; prepare commit 4: `feat(maxitor): the version button and the picker (#289)`; tick #289 phase 3.

---

## Phase 5: A long history (commit 5) · US3 — #289 phase 4

**Goal**: the track scrolls sideways without a scrollbar and never loses the chosen version (FR-023 – FR-027).

**Independent test**: US3 scenarios 1–5 with 64 versions, with Live (M4) and without (M2).

- [ ] T032 [US3] `FC/components/history/VersionTrack/`: points `max(24 px, width / count)` apart; scrolled by `scrollLeft` — horizontal wheel or swipe, vertical wheel over the track turned sideways, drag on empty track; no scrollbar; CSS-mask fades where more is hidden; the right edge "+N newer", "+N newer and Live" when Live is hidden too; a handle out of view pinned to its edge, a click scrolls back; opens with the chosen version in view.
- [ ] T033 [US3] `FC/components/history/VersionTrack/thinLabels.ts`: greedy — the chosen version, the oldest, the newest and Live always kept; then releases newest first, each kept only when it does not overlap one kept before.
- [ ] T034 [US3] `FC/components/history/VersionTrack/longHistory.test.tsx` and `thinLabels.test.ts`: 64 and 500 points (M2 and M4): spacing ≥ 24 px, no scrollbar, "+N newer" and "+N newer and Live", pinned handle and its click, the chosen version in view on opening, labels never overlap and the four kept ones never thin out. Adversarial: drop the 24 px minimum → only the spacing test fails; let Live thin out → only the kept-labels test fails. Restore. Record here.
- [ ] T035 Check run green; prepare commit 5: `feat(maxitor): a long history scrolls on its track (#289)`; tick #289 phase 4.

---

## Phase 6: The message (commit 6) · US4 — #289 phase 5

**Goal**: the chosen version's message, as plain text with two kinds of links (FR-028 – FR-030).

**Independent test**: US4 scenarios 1–5.

- [ ] T036 [P] [US4] `FC/lib/linkify.ts` (research R12): `linkify(text, repository | null)` → parts; `https?://` + non-space, trailing `.,;:!?'"` and unbalanced closing brackets dropped; `#<digits>` not after a word character or `/`, linked to `https://github.com/<repository>/pull/<n>` only for a GitHub history; every other scheme and `owner/repo#<n>` stay text.
- [ ] T037 [US4] `FC/components/history/VersionMessage/`: `pr.title + "\n\n" + pr.body`, or `message`; text nodes and `<a target="_blank" rel="noopener noreferrer">`, never HTML; `white-space: pre-wrap`, words wrap; at most nine lines, then a thin visible scrollbar and a lower-edge fade while more is below; selectable; Live's closing line "Live · checked <time> ago · newest version <name>, <date>" (no last part in M6), "Live · cannot be reached since <time>" while unreachable. `index.ts`, `README.md`.
- [ ] T038 [US4] `FC/lib/linkify.test.ts` and `FC/components/history/VersionMessage/VersionMessage.test.tsx`: `## Heading`, `**bold**`, `<script>`, `javascript:alert(1)` stay text; `https://example.com/a).` links to `https://example.com/a`; `#142` links to pull 142; `owner/repo#5` stays text; a local history links no `#n`; a commit message when there is no PR; the nine-line cap and the fade; Live's lines in M4, M6 and unreachable. Adversarial: set the message as HTML → only the `<script>` test fails; link `javascript:` → only the scheme test fails. Restore. Record here.
- [ ] T039 Check run green; prepare commit 6: `feat(maxitor): the chosen version's message (#289)`; tick #289 phase 5.

---

## Phase 7: Phone (commit 7) · US5 — #289 phase 6

**Goal**: the button in the phone bar, the picker as a sheet (FR-031).

**Independent test**: US5 scenarios 1–2 at 375 px, in M2–M6.

- [ ] T040 [US5] `FC/app/App.tsx` (`topRow(true)`) and `FC/components/history/VersionPicker/`: on a phone the button sits in the 44 px phone bar; the picker is a bottom sheet with the same head, track and message in every mode M2–M6; every point a touch target ≥ 44 px.
- [ ] T041 [US5] `FC/components/history/VersionPicker/VersionPicker.phone.test.tsx`: at a phone's width the button is in the phone bar; the sheet holds the track and the message in M2, M3, M5 and M6; every point's target ≥ 44 px. Adversarial: 24 px targets on a phone → only the touch-target test fails. Restore. Record here.
- [ ] T042 [US5] Run Maxitor with the stand-in histories (quickstart) in the browser pane at desktop and phone width; walk M1–M7, a room of two tabs, a long history and a long message; screenshot each mode for the report. Then bring up the local stand (`docker compose -f deploy/stand/docker-compose.yml -f deploy/stand/docker-compose.local.yml up`), open a private history and a public link through it, and search every container's log for the key: 0 matches (SC-004, SC-014). Deploying to the live stand is the maintainer's, after the merge (quickstart "On the stand").
- [ ] T043 Check run green; prepare commit 7: `feat(maxitor): the version picker on a phone (#289)`; tick #289 phase 6.

---

## Phase 8: Closing — check run, documentation, changelog (commits 8–10) — #289 phase 7

- [ ] T044 Closing check run to zero; record against T002. Commit 8 only if the run changed files: `chore(checks): the closing check run of #289 (#289)`.
- [ ] T045 Documentation (Principle VI): `docs/how-to/open-a-graph-history.md` and its `.ru_draft.md` — the three address forms (private with `#key=`, public GitHub link, a service), every mode M1–M7 with what the screen shows, every refusal (not found, too many wrong keys, cannot be read now, public histories not set up, a refused version), rooms on a history, keys as dots and out of the address bar; `examples/step_26_maxitor/15_open_a_history.py` and `.ipynb` — a port over a repository the example builds (local histories for M2–M7, one with `live`), Maxitor's history actions called for every mode and refusal, a version opened, a revoked key refused after 30 s, the log searched for the key — every case executed, the notebook's output equal to the script's; `F/README.md` and its draft (histories, `MAXITOR_PUBLIC_PORT`); `P/README.md` and its draft (`live`, `reader`, the security events); `docs/how-to/run-the-repo-graph-port.md` and its draft (`live`; Maxitor's own port); the docs index; the tutorial's step 26 points at the new page. Commit 9: `docs(maxitor): opening a graph's history (#289)`.
- [ ] T046 Changelog: one article in `docs/CHANGELOG.md` — Maxitor opens a history and shows any version: the three address forms, the version button and the picker, what each combination of Live and versions looks like, keys never shown or logged, a room moving together, a port's `live`; the package's `CHANGELOG.md` entry. Commit 10: `docs(changelog): Maxitor opens a graph's history (#289)`; tick #289 phase 7.

---

## Dependencies & Execution Order

- Commit order is fixed: 1 → 2 → … → 10; each leaves the check run green.
- Commit 2 (server) before every client commit: the client reads `/api/history` and the room's `version`.
- Commit 3 (keys) before 4: the picker reads keys through `historyKey.ts`.
- Commit 4 (picker, track) before 5 (long track) and 6 (message lives in the picker); 7 (phone) after 4–6.
- Inside commit 2: T003–T004 (port) and T006 (address parsing) first; T007–T009 before T010–T012; T013–T015 after T012; tests T016–T018 once their interfaces exist; T019 any time after T009.

## Parallel Opportunities

- T005 (port tests) beside T006–T009.
- T006 (`history_address.py`, `source_label.py`) beside T003–T004.
- T016 (stand-in port) beside T007–T015.
- T021 beside T022; T026 beside T027; T036 beside T037.

## Implementation Strategy

No MVP cut: the issue ships whole, commit by commit; between any two commits the repository works and the check run is green. Commit 2 alone already lets an API caller open every mode; commits 3–7 add the screen.
