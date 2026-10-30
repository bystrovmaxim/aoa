# Research: Maxitor Opens a History and Shows Any Version

Every decision below was checked against the code on 2026-10-29 (`packages/maxitor/front/`, `packages/maxitor/tools/repo_graph_port/`).

## R1. What a history's address looks like

**Decision**: a private history's address is the port's describe URL with the key in the fragment: `https://repo-graph-port.aoa.run/api/v1/history/orders#key=<key>`. A public history's address is the GitHub link to its graph file, `https://github.com/<owner>/<repo>/blob/<branch>/<path>`, with no port and no key (how it is read: R16). A running service with no history is its own address, as today.

**Rationale**: a browser never sends a fragment to any server and never puts it in `Referer`. So the key cannot reach Maxitor's request log, the stand's HTTPS front end, or a page a link opens, however the address travels: pasted, in the address bar, in a room link. The rest of the address is the port's own URL, so it names the port and the history `id` with no new syntax.

**Alternatives considered**: `?key=` in the query — every request log on the way writes it down. A separate key field — the spec says the address carries the key (FR-001), and Recent and room links would need two values. A Maxitor-made short handle that stands for the key on the server — it makes Maxitor a key store, which #288 keeps out of Maxitor.

## R2. How the key travels inside Maxitor

**Decision**: the browser keeps the key and sends it to Maxitor only in the header `X-Maxitor-History-Key`, on every read that concerns a private history: opening it, its versions list, and every diagram read of one of its versions. Maxitor's server passes it on to the port in the same header and never puts it in a URL, a source string, a log line, an error text or a file. A link Maxitor makes — **Copy link**, the room's link — is `?history=<address without key>&b=<version>#key=<key>`. A page opened by such a link reads the key from the fragment, keeps it in `sessionStorage` for the tab (and in Recent), and removes the fragment with `history.replaceState`, so the browser's address bar, history and synced history never hold it (FR-010a). The room's WebSocket carries the history's address without the key.

**Rationale**: Maxitor already names every graph read by `?source=` (`graph_source_middleware.py`), and uvicorn writes each request line, query included, to its access log. A header is never logged. The fragment keeps the page's own address safe (R1).

**Alternatives considered**: the key in `?source=`, with the log scrubbed — one forgotten log (the stand's front end, a proxy) gives the key away. Cookies — they would be sent to every Maxitor request and tie a key to a browser, not to a history.

## R3. What Maxitor logs

**Decision**: a source is logged as `<origin>#<first 8 hex of SHA-256 of the whole address>` (`https://dev.demo.aoa.run#3f9a1c2b`), through one helper used by `check_source_action.py` and every other log line that names a source. A history is logged as `history <id> by <key name>`, or `history public <owner>/<repo>` for a public link. The port tells Maxitor the key's name in `describe` (R5). Maxitor's request log (uvicorn's access log) is started without query strings: method, path, status.

**Rationale**: FR-011. The origin says which service a line is about; the hash tells two addresses of one origin apart without showing either.

**Alternatives considered**: turning the access log off — it is how an operator sees that the server serves at all. Hashing the whole line — then the origin is lost too.

## R4. What names a version's graph

**Decision**: a version's source, the key under which `GraphStore` holds its graph, is the port's version URL without a key: `<port>/api/v1/history/<id>/versions/<sha>`, or `<port>/api/v1/history/public/versions/<sha>?link=<link>`. Live is its service's address, an ordinary source. `GraphSourceGateway.fetch` gets an optional key, sent as `X-Maxitor-History-Key`.

**Rationale**: the store, its single-flight build and its eviction work unchanged (FR-005). The source says what is built; the key only says who may read it (R6). Two readers with different keys share one build.

**Alternatives considered**: a source that includes the key — every reader with another key builds the same graph again, and the key sits in a dictionary that is logged and inspected.

## R5. What the port adds

**Decision**: two optional fields. The histories config takes `live = "<service address>"` per `[[history]]`, checked like the other fields (an `http(s)` URL), and `describe` returns `live` (absent when not configured, always absent for a public link) and `reader`: the name of the key that opened it, absent for a public link.

**Rationale**: Q1 of the spec (2026-10-29): Live comes from the port's config. `reader` lets Maxitor log a history by the key's name (R3) without knowing the config.

**Alternatives considered**: Maxitor guessing Live from the repository — impossible; a service's address is not in git. Logging the key's hash instead of its name — #288 already chose names for logs.

## R6. Who may read a version Maxitor already holds

**Decision**: a new resource, `HistoryAccess`, remembers for each private history which keys the port accepted, by the key's SHA-256 and the time. A read of a held version is answered only when its key was accepted for that history within the last 30 seconds; otherwise Maxitor first asks the port (`GET …/versions` with the held `ETag`: a `304` means accepted, a `404` means refused). A refused key gets Maxitor's `404 {"detail": "not found"}`, the same for every reason (FR-009). Public links need no key.

**Rationale**: FR-005 shares one build between readers; without this, a reader with a revoked key, or none, would get a version someone else opened. 30 seconds is the freshness interval, so a revoked key stops working within one check.

**Alternatives considered**: asking the port on every read — a diagram page makes several reads, each would cost a round trip. Keying graphs by key — R4.

## R7. Keeping the history's list fresh

**Decision**: an open history is held as a `HistoryEntry` in a new `HistoryStore` beside `GraphStore`: its describe answer, its versions, the port's `ETag`, when it was checked, and, in memory only, the last key that opened it. The clock that already runs `CheckDueSourcesAction` every ten seconds also picks histories that someone looks at and whose last check is 30 seconds old, and runs `CheckHistoryAction` for each: `If-None-Match`, `304` → nothing, `200` → the entry is replaced, and every room of that history gets `{"type": "history_changed"}`. A tab outside a room asks for the list with its own `If-None-Match` on the same 30-second poll it already makes for the fingerprint. A version's `GraphEntry` is marked `immutable`, and `is_due` never picks it (FR-006). Live is checked as today.

**Rationale**: FR-006a and Q2 of the spec. The port answers an unchanged list with a `304` (#288), so a check costs a header.

**Alternatives considered**: putting histories in `GraphStore` — a history is not a graph, has no sidebar and no DuckDB, and would break the store's invariants.

## R8. A bare graph

**Decision**: `LoadAOAServiceAction`'s `validate_service_aspect` accepts either the envelope (`coordinator_json`, a string) or a bare graph: an object with `nodes` and `edges` at the top, as `graph.json` is (`{"schema_version", "nodes", "edges"}`). The parse aspect takes whichever came. The protocol's schema is not checked here: for a version the port checked it (`refused`), and a graph-json address keeps today's checks.

**Rationale**: FR-004, the smallest change to the five-aspect pipeline.

## R9. Rooms on a history

**Decision**: a `Room` gets `history` (the address without the key) and `version` (`<sha>` or `live`). The room's graph is the current version's source. A new client message `{"type": "version", "b": "<sha>|live"}` runs `SetRoomVersionAction`: it checks that the history has that version and is not refused, sets `room.version`, and broadcasts `{"type": "version", "b", "by"}`; the last message wins (FR-022a). `welcome` carries `history` and `version`; a joiner gets the room's version, whatever their link said. A page that the new version's left panel does not offer falls back as on joining (spec 028, FR-010). Page settings stay per page key. Server-side reads for a room (the joiner's start page, a page check) use a remembered key the port still accepts (R18); every tab's diagram reads use its own key (R2).

**Rationale**: Q1 of the clarification session: the version belongs to the room, like a page's settings (spec 028, FR-030, FR-031).

**Alternatives considered**: one room per version — following would cross graphs, which the clarification rules out.

## R10. Names on the track

**Decision**: a release is a version with a tag whose `release` is not null, or a tag that is a version number (`v0.8.0`, `0.8.0`), since a local repository has tags but no releases (the maintainer, 2026-10-30). A version's name: its release's tag without the `v` before a number when it carries one (`0.11.0`); `<last release before it> · #<pr>` (`0.11.0 · #147`); `#<pr>` when no release comes before it; a version with no pull request — a direct commit — by its place in the history, the oldest being 1 (`0.11.0 · #57`), a number easy to say aloud in a room; `Live` for Live. A commit's hash is never a name: it means nothing to a reader (the maintainer, 2026-10-30); it stays only the id in the address and the room. Tags without a release are flags.

**Rationale**: FR-017 and FR-018; the mockup's names (`0.11.0 · #147`) with the release defined by the issue, not by a label change.

## R11. The track

**Decision**: one React component, `VersionTrack`, draws an SVG time axis in a container with hidden overflow, scrolled by its own `scrollLeft`: a horizontal wheel or swipe, the vertical wheel over the track turned sideways, and a drag on empty track. Points stand at `max(24 px, width / count)`. Fades are CSS masks on the edges; the right edge shows "+N newer" when N versions are out of view, and "+N newer and Live" when Live is too. A handle out of view is drawn pinned to its edge and scrolls back on click. Labels are the mockup's: the oldest version, releases and Live, none under the chosen chip; the oldest and Live never thin out; then releases newest first, each kept only when it does not overlap a label already kept. The keyboard: ← → Home End on the handle, which has `role="slider"` with `aria-valuetext` set to the version's name.

**Rationale**: FR-016 … FR-027. The client uses MUI and its own SVG diagrams; no chart library is in the bundle, and a track does not need one.

## R12. The message

**Decision**: the message is split into text and links by one function, `linkify(text, repository)`, which returns a list of parts that React renders as text nodes and `<a target="_blank" rel="noopener noreferrer">`. It matches `https?://` followed by non-space characters, with trailing `.,;:!?'"` and unbalanced closing brackets dropped, and `#<digits>` not preceded by a word character or `/`, linked to `https://github.com/<repository>/pull/<n>`, only when the history's host is GitHub. Nothing is ever set as HTML. The box: `white-space: pre-wrap`, `overflow-wrap: anywhere`, `max-height` of nine lines, `overflow-y: auto` with a thin scrollbar, a fade on its lower edge while it is not at the bottom.

**Rationale**: FR-028, FR-028a, FR-029; Q3 of the clarification session.

**Alternatives considered**: a Markdown renderer with a sanitizer — Q3 chose plain text.

## R13. Every combination of Live and versions

**Decision**: the client derives one mode from what it opened, and every screen is specified per mode in [contracts/ui.md](contracts/ui.md):

| Mode | What was opened | Version button | Track |
|---|---|---|---|
| M1 Live only | a running service or a graph-json address | none | none |
| M2 History, several versions, no Live | a history without `live`, versions ≥ 2 | `◷ <newest> ▾` | points, no dashed gap |
| M3 History, one version, no Live | a history without `live`, 1 version | `◷ <it> ▾` | one point; ← → do nothing |
| M4 Live and several versions | a history with `live`, versions ≥ 2 | `◷ Live ▾` | points, dashed gap, Live |
| M5 Live and one version | a history with `live`, 1 version | `◷ Live ▾` | one point, dashed gap, Live |
| M6 Live and no version | a history with `live`, 0 versions | `◷ Live ▾` | Live alone, "0 versions and Live" |
| M7 Nothing | a history without `live`, 0 versions | none | none; the workspace says the history has no version yet |

A refused version can occur in M2–M5: it stays on the track, marked, and choosing it shows its reason instead of a diagram. Live unreachable in M4–M6 shows as a running service's unreachable state does today, and the versions still open.

**Rationale**: the maintainer's instruction of 2026-10-29: Maxitor must be ready for Live without history, history without Live, and Live with a history of one or of several versions. M6 and M7 are the remaining combinations of the same two facts, so they are specified too rather than left to chance.

## R18. Who may enter a private history's room

**Decision**: `OpenHistoryAction`, called with the tab's key in the header, answers besides the history a `room_ticket`: 128 random bits, valid 60 seconds, for one use, bound to that history and to the key's SHA-256. A tab opening or joining a private history's room passes `ticket=` on the WebSocket; `JoinRoomAction` refuses a missing, used, expired or foreign ticket with the "not found" close code before it reveals anything of the room (FR-011d). The `HistoryEntry` remembers, in memory only, every key the port accepted for it while a tab of it is open; the room's server reads with the newest of them that `HistoryAccess` still accepts, and when none is left, every tab of the room is told "not found".

**Rationale**: a browser cannot set a header on a WebSocket, and the key must never be in a URL (FR-010b). A ticket in the URL is safe because it is not the key, opens nothing but one join, and is dead a minute later — and the request log carries no query (R3).

**Alternatives considered**: sending the key as the socket's first message — the room's server would have to hold a half-open connection that has not proved anything, and every room action would need a "not yet admitted" state. Admitting anyone with the room's id — FR-011d forbids it.

## R19. Security events, and no shared port

**Decision**: Maxitor keeps no port of its own for private histories (FR-003a); a port's block for wrong keys is left as #288 made it. Each failed attempt is a `box.warning` on the `security` channel in Maxitor (FR-011e); in the port, each wrong key and each webhook with a wrong signature is a `box.warning`, and each block a `box.critical`, on the same channel (FR-011f). The port's wrong-key count lives in its auth coordinator, outside an action, so the coordinator raises a typed event that an action of the port logs through its `box` — the port's rule that logging goes through `box`.

**Rationale**: the maintainer, 2026-10-29: a port belongs to one owner of repositories and serves all of that owner's repositories; its owner runs it and does not publish its address; a wrong port address reaches no port; a block protects that one owner. What was missing is that an attempt leaves a trace.

**Alternatives considered**: the port trusting a client address Maxitor passes on, or Maxitor limiting keys itself — both solve a shared-port problem that this design does not have.

## R14. Recent

**Decision**: Recent (`lib/serviceUrlHistory.ts`, `localStorage`) keeps up to ten records `{address, kind, name?, versions?, live?}`, where `kind` is `service` or `history`; old string records read as `{address, kind: "service"}`. The address is kept whole, key included, since Recent is the user's own browser storage; it is shown with the key as dots.

**Rationale**: FR-012 (Recent says what each address turned out to be).

## R15. Testing

**Decision**: server — pytest, against a stand-in port (an `httpx.MockTransport` that answers `describe`, `versions` with `ETag`/`304`, `version`, and `404` for a wrong key), for every mode of R13, the key in no log (`caplog` and uvicorn's access logger), access per key (R6), freshness (R7), rooms (R9). Client — vitest with Testing Library: the mode table, naming (R10), thinning, pinned handle, keyboard, `linkify`, dots and the eye, the address bar's `history`/`b`/`#key`. The port — its existing pytest suite gets `live` and `reader`. Adversarial breaks are named per task.

**Rationale**: the repository's existing test stacks; the front must not import the port (`scripts/package_boundaries.toml`), so the port is stood in by its contract.

## R16. The port Maxitor reads public links through

**Decision**: a private history is read through the port its address names. A public history — a bare GitHub link — is read through Maxitor's own port: the same `repo-graph-port` image run as its own container beside Maxitor's, with an empty histories config (no `[github]`, no `[[history]]`), on Maxitor's internal Docker network only, no published port, named by `MAXITOR_PUBLIC_PORT` (`http://maxitor-public-port:8102` on the stand; locally `http://127.0.0.1:8103`). Maxitor calls its `public` routes with the link. Without the variable, public links are refused.

**Rationale**: the maintainer, 2026-10-29: Maxitor reading GitHub itself would give it the port's job and mix the two; a port of Maxitor's own keeps the port the only part of Maxitor that talks to a host. A separate container rather than a process inside Maxitor's image: the port's image already carries `git`; Maxitor's image stays without it; the front still never imports the port (`scripts/package_boundaries.toml`). The port runs with an empty config today (`load_histories` accepts a file with no tables).

**Alternatives considered**: Maxitor reading public repositories itself — mixes duties, needs the port's code in the front. Passing public links through an owner's port — would make the maintainer's unpublished port Maxitor's default. A process inside Maxitor's container — two servers in one image, and `git` in Maxitor's image.

## R17. Documentation

**Decision**: a how-to page, `docs/how-to/open-a-graph-history.md` (+ `.ru_draft.md`), shows every mode of R13 and every refusal; an example under `examples/step_26_maxitor/` as a script and a notebook runs Maxitor's history actions against a local history (`host = "local"`) built in a temporary git repository, prints each mode's answer, and is executed while written. The front's README and the port's README get the new fields and the address form. The changelog is one article.

**Rationale**: Principle VI.
