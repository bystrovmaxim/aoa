# Feature Specification: Maxitor Opens a History and Shows Any Version

**Feature Branch**: `feature/issue-289-open-history-any-version`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Issue #289 (Graph history 4/9): Maxitor opens a history and shows any version. Source: https://github.com/bystrovmaxim/aoa/issues/289, mockup specs/030-graph-history/mockup/index.html. Branch already created: feature/issue-289-open-history-any-version."

## Context: what is true today, checked on 2026-10-29

- **Maxitor shows one graph per address.** The address field takes a running service (`host:8001`, `https://host`) or a graph-json address; the graph is built once per address on Maxitor's server and held for every reader. Every diagram read names its address as `?source=<address>`, and the browser's address bar carries `source`, `view`, `domain`, `node`, `host` and `room`.
- **Only the envelope is accepted.** `load_aoa_service_action.py` requires the service's answer to carry `coordinator_json`; a bare graph file — what a repository keeps and what a history's version is — is refused.
- **Every held graph is checked for freshness** (`freshness.py`): every 30 seconds when its source gives `ETag` or `Last-Modified`, every 2 minutes when it gives neither.
- **Whole addresses reach the log.** `check_source_action.py` writes the full source at every check ("Source … unchanged", "… rebuilt", "… unreachable").
- **A history can be read, but nothing shows it.** `repo-graph-port` (#288) serves `describe`, `history` (versions oldest first, each with its commit, date, pull request or commit message, tags with their releases, node and edge counts, and a refusal reason when its graph fails the protocol's schema) and `version` (one version's graph, byte for byte). A configured history is named by its `id` and opened with a read key in the header `X-Maxitor-History-Key`; a public repository's history is opened by a link to its graph file, with no key. It runs on the stand at `https://repo-graph-port.aoa.run`.
- **A room shows one source.** A room is opened on one address; its link carries that address.
- **The mockup and the issue differ in three places; the issue, revised on 2026-10-29, wins:** a version's message is its pull request's title and body (or its commit's message), not the merge commit's message; a release is a version carrying a release's tag, not a point where a version label changed; a history is read through `repo-graph-port`, not from an index file.

## Clarifications

### Session 2026-10-29

- Q: What happens when a room's participant picks another version of the history? → A: The version is a setting of the whole room: whoever picks it, it changes for everyone in the room, the last pick wins; the room link carries the version, and a newcomer gets the room's current version.
- Q: How does Maxitor learn that an open history got a new version, a new tag or an edited pull request description? → A: The history's list of versions is checked on the freshness schedule, like Live (every 30 s, through `ETag`/`304`); a new version, tag or description shows by itself, in a room for everyone.
- Q: Is a version's message shown as plain text or rendered as Markdown? → A: Plain text, except that `http`/`https` addresses and `#123` references to the same repository's pull requests become links.
- Q: How do Diff and Side by side look in the mode switch before they exist? → A: The switch is shown: One active, Diff and Side by side greyed out and disabled, with the hint "comes later".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a history and pick one version (Priority: P1)

A developer pastes a history's address into Maxitor — a private one, which carries its read key, or a link to a graph file on a public GitHub repository. Maxitor opens it; a button in the top row says which version is shown. The developer opens the picker, sees every version on one time track, clicks one, and every diagram — ERD, full graph, use cases, lifecycles — now shows the system as it was at that version. A running service opens as today, with no version button.

**Why this priority**: This is the step's whole point: until now Maxitor can only show what a service serves today.

**Independent Test**: Open a private history by its address, a public one by its link, and a running service; in each history pick an older version and compare the diagram's node and edge counts with that version's own.

**Acceptance Scenarios**:

1. **Given** a running service's address, **When** it is opened, **Then** the top row has no version button and Maxitor works as before.
2. **Given** a private history's address with a valid key, **When** it is opened, **Then** it opens in its mode (FR-009a): with the version button showing Live in M4–M6 and its newest version in M2–M3, and with no button and "This history has no version yet." in M7.
3. **Given** a link to a graph file on a public GitHub repository, **When** it is opened, **Then** its history opens with no key.
4. **Given** an open history, **When** the button is clicked, **Then** the picker opens over the diagram with the service's name, the count ("12 versions and Live"), the mode switch with One active and Diff and Side by side greyed out with the hint "comes later", and one track — oldest left, newest right, Live last after a dashed gap.
5. **Given** the open picker, **When** a point is clicked, the handle dragged, ← or → pressed, or Home or End pressed, **Then** that version is chosen, the button names it (`◷ v0.11.0 · #147 ▾`), and every diagram shows its graph.
6. **Given** the open picker, **When** the user clicks outside it, **Then** it closes and the chosen version stays.
7. **Given** a chosen version, **When** the link made by **Copy link** is opened in another browser, **Then** the same history opens on the same version (the link carries `history`, `b` and the key after `#key=`). The browser's own address bar carries `history` and `b` but not the key: opened elsewhere, it opens only where Recent already holds that history's key, and otherwise asks for the history's address.
8. **Given** a version whose graph fails the protocol's schema, **When** it is chosen, **Then** Maxitor refuses it with the reason the port reports, and the other versions still open.
9. **Given** a bare graph file at a graph-json address, **When** it is opened, **Then** it is shown like a service's graph.
10. **Given** a room opened on a history, **When** one participant picks another version, **Then** every participant's button and diagrams move to that version, whatever page each is on.
11. **Given** a room on a version, **When** someone joins it by a link that names another version, **Then** they get the room's current version.

---

### User Story 2 - A read key is never given away (Priority: P1)

A developer works with a private history on a shared screen, in a screenshot, or by sending a room link to a colleague. The key never shows in full unless they reveal it with the eye, and it never lands in Maxitor's log.

**Why this priority**: The key opens a private repository's history; one leak in a log or on a screen gives that history away.

**Independent Test**: Open a private history, look at the field, Recent and the room link; reveal with the eye; run every check and read the log; search the log for the key.

**Acceptance Scenarios**:

1. **Given** a history's address in the field while it is not being edited, **When** it is shown, **Then** the key is eight dots, whatever its length; the rest of the address is readable.
2. **Given** Recent and a room link, **When** they show an address with a key, **Then** the key is dots there too.
3. **Given** dots, **When** the eye is clicked, **Then** the key is shown until the eye is clicked again or the field loses focus.
4. **Given** any source opened and checked, **When** Maxitor's log is read, **Then** each source appears as its origin and a short hash of its address, a history as its `id` and the key's `name`, and no read key appears anywhere.
5. **Given** a history page opened by a link with `#key=`, **When** it has loaded, **Then** the browser's address bar, and so its history, no longer shows the key.
6. **Given** a link to a private history's room whose `#key=` was lost on the way, **When** it is opened, **Then** Maxitor says the history was not found and shows nothing of the room — no pages, no participants.
7. **Given** Recent, **When** it lists past addresses, **Then** each says what it turned out to be, by the table of modes (FR-009a), and each entry can be removed, its key with it.

---

### User Story 3 - A long history stays usable (Priority: P2)

A service with 64 merged pull requests opens with a track that does not cram them together: it scrolls sideways, shows where more is hidden, and never loses the chosen version.

**Why this priority**: Real services have long histories; without this the picker works only for small ones.

**Independent Test**: Open a history of 64 versions; scroll the track by swipe, wheel and drag; scroll the handle out of view and click its pinned mark.

**Acceptance Scenarios**:

1. **Given** a history of 64 versions, **When** the picker opens, **Then** points stand at least 24 px apart, the track scrolls sideways, and the chosen version is in view.
2. **Given** a scrolled track, **When** it is looked at, **Then** there is no scrollbar, the edges fade where more is hidden, and the right edge says how many newer versions are out of view.
3. **Given** the handle scrolled out of view, **When** the track is looked at, **Then** the handle is pinned to its edge, and clicking it scrolls back to it.
4. **Given** many releases close together, **When** they are drawn, **Then** their names thin out before they collide.
5. **Given** a point, **When** it is hovered, **Then** its tooltip gives the pull request's number and title, its date, its size and its tags; tags that are not releases show as small flags.

---

### User Story 4 - The chosen version says what changed (Priority: P2)

Under the track, the developer reads why this version exists: its pull request's title and description, whole, as its author wrote it.

**Why this priority**: A version without its reason is a number; the message is what tells versions apart.

**Independent Test**: Choose a version made by a pull request with a long description, one made by a direct commit, and Live.

**Acceptance Scenarios**:

1. **Given** a version made by a pull request, **When** it is chosen, **Then** the box under the track shows its title and body, whole, with line breaks kept and long lines wrapped by words, and nothing above them.
2. **Given** a version made by a direct commit, **When** it is chosen, **Then** the box shows the commit's message.
3. **Given** a message of several screens, **When** it is shown, **Then** the box stops at nine lines and scrolls inside, with a thin visible scrollbar, its lower edge fading while more is below; the text can be selected.
4. **Given** Live, **When** it is chosen, **Then** there is no message; a closing line says when Live was last checked.
5. **Given** a message with `## Heading`, `**bold**`, `<script>`, a `javascript:` address, an `https://` address and `#142`, **When** it is shown, **Then** the first four appear as typed text, the address links to itself, and `#142` links to pull request 142 of the history's repository, each opening in a new tab.

---

### User Story 5 - The same on a phone (Priority: P3)

On a phone, the version button sits in the phone bar and the picker opens as a sheet from the bottom, with the same track and message.

**Why this priority**: Maxitor already works on a phone; a history must not break that, but the desktop comes first.

**Independent Test**: Open a history at a phone's width; open the sheet; pick a version by touch.

**Acceptance Scenarios**:

1. **Given** a phone's width, **When** a history is open, **Then** the version button is in the phone bar.
2. **Given** the button tapped, **When** the sheet opens, **Then** it holds the track and the message, and every point is a touch target of at least 44 px.

### Edge Cases

- **A history with no versions** (its repository has no graph file yet) — M6 or M7 (FR-009a).
- **A history without Live** (its config entry names none, or it is a public link) — the track ends at its newest version; there is no dashed gap.
- **Live unreachable** — when the history opens or later: it still opens on Live, which shows the unreachable state a running service shows today, with the notice "Live cannot be reached; pick a version"; the versions open as usual; in M6 there is nothing else to show. In a room, everyone on Live sees the same state, and anyone may move the room to a version.
- **A history of one version** — M3 or M5 (FR-009a).
- **`live` added to or removed from the port's config while a history is open** — the next check of the list (FR-006a) moves the history between modes; whoever is on Live when it goes is moved to the newest version, told "Live is no longer part of this history".
- **A version disappears from the list** (the branch rewritten, the graph file moved) — whoever is on it is moved to the history's default version (FR-021), told "<name> is no longer in the history"; a room moves as one.
- **The version moved to lacks the page one is on** — the page falls back as a link naming a page the graph does not offer falls back today; in a room, as on joining (spec 028, FR-010).
- **The newest version refused, no Live** — the history opens on the newest version that is not refused; when every version is refused, on the newest, showing its reason.
- **A wrong, revoked or expired key** — Maxitor says the history was not found, the same answer the port gives for each case, with the key still dots, and writes a security warning (FR-011e).
- **A port that blocks for too many wrong keys** — Maxitor says "Too many wrong keys for this history; try again in a minute" and does not retry; the port writes a critical security event (FR-011f).
- **An address naming a port that does not exist or does not answer** — Maxitor says the history cannot be read now; no port is reached.
- **The port unreachable** — Maxitor says the history cannot be read now; versions already built still show.
- **A version shown to many readers** — it is built once and shared, as any graph is.
- **A version is never rebuilt** — a version's graph is not in the freshness checks; Live and the list of versions are.
- **A pull request is merged while the history is open** — within one check the new point appears on the track and the count grows ("13 versions and Live"); whoever is on a version stays on it, even if it was the newest.
- **A history open but no tab watching it** — its list stops being checked when no tab is open, as a held graph does today.
- **A public history whose link is not a graph file on a GitHub repository** (another host, a folder, a branch page) — refused with the reason, before anything is fetched.
- **An address bar naming a version the history does not have** — the history opens on its default version, and the address bar is corrected.
- **A version before the first release** — named by its pull request's number (or its short commit) alone.
- **A key in a pasted address with surrounding spaces** — trimmed like any address; the key is everything after `#key=` to the end, so the one held and the one masked are the same string; a second `#` in the address is refused with the reason.
- **The key that the room's server read with is revoked** — the room goes on with the key of any participant the port still accepts; when none is left, every tab is told "not found".
- **A `#123` in a private repository's message** — the link opens the code host, where only readers with access to the repository see it; Maxitor grants nothing.
- **Two participants of a room pick versions at once** — the last pick wins for everyone, as with a page's settings.
- **A participant following another in a room** — both are always on the room's version, so following never lands on a graph the follower does not hold.

## Requirements *(mandatory)*

### Functional Requirements

**Reading a history**

- **FR-001**: The address field MUST accept, besides a running service and a graph-json address, a history: a private history's address — the port's history URL with the read key after `#key=` (`https://repo-graph-port.aoa.run/api/v1/history/orders#key=<key>`) — or a public history's address: the link to a graph file on a public GitHub repository (`https://github.com/<owner>/<repo>/blob/<branch>/<path>`), with no port and no key. A running service — Live with no history — is given by the service's own address, as today. Each is one full URL. The key sits after `#`, the one part of an address a browser never sends to any server.
- **FR-002**: Maxitor MUST tell a history from a graph by the form of its address alone — a port's history URL (`…/api/v1/history/<id>`) or a GitHub link to a file (`https://github.com/…/blob/…`) — and a running service from a graph-json address by what it answers, never by any other host name.
- **FR-003**: Every history MUST be read through a `repo-graph-port`; Maxitor MUST NOT read a repository or a code host itself. A private history MUST be read through the port its address names; a public history (a bare GitHub link) MUST be read through Maxitor's own port (FR-003b).
- **FR-003a**: Maxitor MUST NOT keep a list of other owners' ports: a private history's port is whatever port its address names. An owner of repositories may run their own port — one port for all of their repositories and histories — with their own keys, and give its address to no one; Maxitor then reaches that port only for a user who was given its address and key, and an address naming a wrong port reaches no port at all.
- **FR-003b**: Maxitor MUST have a port of its own, used only for public GitHub links: a `repo-graph-port` with no histories, no keys and no GitHub App of a private owner, reachable only by Maxitor's server (its own container on Maxitor's internal network, never published), named to Maxitor by `MAXITOR_PUBLIC_PORT`. A private history MUST never be read through it, and its address MUST never be shown to a user. Without `MAXITOR_PUBLIC_PORT`, a public link MUST be refused with "Public histories are not set up on this Maxitor".
- **FR-004**: A bare graph file MUST be accepted wherever a graph is read, not only the envelope with `coordinator_json`.
- **FR-005**: Each version MUST be built once per commit and held like any other graph, shared by every reader.
- **FR-006**: A version's graph MUST be left out of the freshness checks; Live MUST be checked as today.
- **FR-006a**: An open history's list of versions MUST be checked on the same freshness schedule as a source with validators (every 30 seconds), using the port's `ETag` so an unchanged list costs a `304`; a new version, a new tag or an edited pull request description MUST then show on the track, in the tooltip and in the message without a reload, in a room for every participant. A new version MUST NOT move anyone off the version they are on. What is checked follows the mode: the graph alone in M1, the list alone in M2, M3 and M7, the list and Live in M4–M6.
- **FR-007**: A history MUST have Live exactly when its entry in the port's histories config names a running service (an optional `live` address), and `describe` MUST return that address; a history without one, and every public link, MUST have no Live. Maxitor MUST open Live as it opens a running service today, and the user MUST NOT have to type a second address.
- **FR-008**: A version whose graph fails the protocol's schema MUST be refused with the reason the port reports; the history and its other versions MUST still open.
- **FR-009**: A wrong, revoked or expired key, an unknown history and a missing version MUST all be answered by Maxitor as "not found", as the port answers them — on a read, on opening a history and in a room alike. A revoked or expired key MUST stop opening versions Maxitor already holds within 30 seconds.
- **FR-009a**: Maxitor MUST work in each of the seven modes below, every one tested. The mode follows from the list of versions (not from `describe`'s count) and whether Live exists; a public history is only ever M2, M3 or M7.

  | Mode | What is open | Version button | Opens on | Picker says | Track | ← → / Home End | Recent says |
  |---|---|---|---|---|---|---|---|
  | M1 | a running service or a graph-json address: Live without a history | none | its graph | — | — | — | "Live service · one graph" |
  | M2 | a history without Live, ≥ 2 versions | `◷ <newest> ▾` | newest (FR-021) | "12 versions" | points | step / oldest, newest | "History · <name> · 12 versions" |
  | M3 | a history without Live, 1 version | `◷ <it> ▾` | it | "1 version" | one point | nothing | "History · <name> · 1 version" |
  | M4 | Live and a history of ≥ 2 versions | `◷ Live ▾` | Live | "12 versions and Live" | points ┆ Live | step, Live last / oldest, Live | "History · <name> · 12 versions and Live" |
  | M5 | Live and a history of 1 version | `◷ Live ▾` | Live | "1 version and Live" | one point ┆ Live | between the two | "History · <name> · 1 version and Live" |
  | M6 | Live and a history of no version yet | `◷ Live ▾` | Live | "0 versions and Live" | Live alone | nothing | "History · <name> · 0 versions and Live" |
  | M7 | a history with no version and no Live | none | — | — | — | — | "History · <name> · no version yet" |

  In M7 the workspace MUST say "This history has no version yet." — words distinct from "not found" and from "cannot be read now". A history MUST move between modes as its list changes (M7 → M3 → M2 and M6 → M5 → M4 as versions are merged; M2 ↔ M4, M3 ↔ M5, M7 ↔ M6 as `live` is added or removed) without a reload, in a room for everyone.

**Keys and logs**

- **FR-010**: A read key MUST be shown as eight dots, whatever its length, wherever Maxitor shows an address — the field while not being edited, Recent, the room link; the rest of the address MUST stay readable; an eye MUST reveal the key until it is clicked again or the field loses focus. A copied link MUST carry the real key, since it is what opens the history elsewhere: **Copy link**, a button in the picker's head that copies `?history=…&b=…#key=…` for the shown version, and the room's link, which also carries `b`.
- **FR-010a**: Once a page has read the key from `#key=`, it MUST remove it from the browser's address bar without adding a history entry, and keep it in that tab's `sessionStorage` only, where it ends when the tab is closed; leaving a room MUST NOT touch it; beyond the tab, the key MUST remain only in Recent (FR-012). The browser's address bar, its history and history synced between devices MUST therefore never hold a key.
- **FR-010b**: The key MUST travel only from the browser to Maxitor's server in a request header and from Maxitor's server to the port in a request header. It MUST NOT be in any URL Maxitor requests or serves — its page addresses, its API reads, the room's WebSocket — nor in the source a graph is held under, so no server on the way (Maxitor's, the stand's HTTPS front end, a proxy) receives it in a request line.
- **FR-011**: No log MAY contain a whole address or a read key: Maxitor's actions' log, its request log (method, path and status only, never a query), error tracebacks, and telemetry if any is sent. A source MUST be logged as its origin and the first 8 hex characters of the SHA-256 of its whole address (`https://dev.demo.aoa.run#3f9a1c2b`); a history as `history <id> by <key name>`, the name being the port's `reader`, or `history public <owner>/<repo>`.
- **FR-011a**: No error Maxitor answers or shows — a refusal's text, a reason on screen — MAY contain a key or a whole address; a source MUST be named there as in the log.
- **FR-011b**: On Maxitor's server a key MUST live only in memory, for as long as a history is held, and MUST NOT appear in a representation of an object, an exception, a debug dump or a test's failure output.
- **FR-011c**: The page's title (`<name> · <version name> — Maxitor`), tooltips and notices MUST name a history by its name — its `id`, or `owner/repo` for a public one — never by its address.
- **FR-011d**: A private history's room MUST admit only a tab whose key the port accepts for that history; any other tab MUST be told "not found" and learn nothing of the room — its pages, its participants, its version. The room's server MUST read with the key of a participant the port still accepts.
- **FR-011e**: Maxitor MUST write `box.warning` on the `security` channel for every failed attempt to open or read a private history — a key the port refused, a port that answered `429` — naming the port's origin, the history `id` and the browser's address, never the key. When the port answers `429`, Maxitor MUST tell the user "Too many wrong keys for this history; try again in a minute", and MUST NOT retry on its own.
- **FR-011f**: The port MUST write `box.warning` on the `security` channel for every wrong key and every webhook with a wrong signature, naming the client's address and the history `id` (never the key or the signature), and `box.critical` on the `security` channel each time it blocks a client for too many wrong keys. The block itself stays as #288 made it: more than 10 wrong keys from one address in a minute.
- **FR-012**: Recent MUST say what each address turned out to be, by the table of FR-009a, show keys as dots, and let each entry be removed with its key. It MAY keep the whole address, key included, in the browser's own storage (see Assumptions).

**The version button and the picker**

- **FR-013**: In M2–M6 the top row MUST have one version button naming the shown version by FR-018 (`◷ Live ▾`, `◷ v0.11.0 ▾`, `◷ v0.11.0 · #147 ▾`, `◷ #12 ▾`, `◷ 3be81c6 ▾`); in M1 and M7 it MUST be absent.
- **FR-014**: The button MUST open the picker over the diagram; a click outside or Escape MUST close it; it MUST start closed when a history opens and stay closed until the button is used, and choosing a version MUST leave it open.
- **FR-015**: The picker MUST show the service's name, the number of versions and whether Live follows, worded as in FR-009a ("1 version", "12 versions and Live", "0 versions and Live"), the mode switch, and one track. In the switch One MUST be active, and Diff and Side by side MUST be shown greyed out and disabled, with the hint "comes later" on hover, focus or touch; choosing them MUST do nothing.
- **FR-016**: The track MUST be a time axis, oldest left, newest right, with Live last after a dashed gap; every point MUST be one version from the port.
- **FR-017**: A release — a version carrying a tag that has a release — MUST be named on the track by its tag; versions between releases MUST be small dots; other tags MUST be small flags.
- **FR-018**: A version MUST be named `<release> · #<pull request>` when it follows a release, by its release alone when it carries one, and by its pull request's number (or short commit) when no release comes before it.
- **FR-019**: A point's tooltip MUST give its pull request's number and title, its date, its size (nodes and edges) and its tags; a refused version's tooltip MUST end with "refused: <reason>".
- **FR-019a**: A refused version MUST stay on the track, drawn hollow — a refused release keeps its name, a refused merge its dot — and choosing it MUST show its reason in the workspace instead of a diagram, the button naming it.
- **FR-020**: A version MUST be chosen by clicking its point or dragging the handle; ← and → MUST step, Home and End MUST jump to the ends; where there is nothing to step to (M3, M6) they MUST do nothing, and the handle MUST still announce the version it is on to assistive technology.
- **FR-021**: A history MUST open on Live when it has one (M4–M6), even when Live cannot be reached at that moment; otherwise (M2, M3) on its newest version that is not refused, or, when every version is refused, on its newest. M7 has nothing to open on.
- **FR-022**: The address bar MUST carry the history as `history` and the chosen version as `b` (the first 12 hex characters of its commit, or `live` — the same form in the room's messages; no `b` in M7, `live` only in M4–M6), never the key (FR-010a); opening such an address MUST restore both; a `b` the history does not have MUST fall back to the default version (FR-021).
- **FR-022a**: Inside a room, the chosen version MUST belong to the room, like a page's filters and layout mode (spec 028, FR-030, FR-031): a pick by any participant MUST change it for everyone, sent as "set to", the last pick winning; the room link MUST carry it; a participant who joins MUST get the room's current version, whatever version their link names. A pick of a version the history does not have, of a refused one, or of Live where there is none MUST be refused to the participant who made it, with the reason, and MUST NOT move the room. When the room's version disappears from the list or Live is removed, the room MUST move as one, by the rules of the edge cases.

**A long history**

- **FR-023**: Points MUST stand at least 24 px apart; the track MUST scroll sideways by a sideways swipe, the mouse wheel over it, or dragging its empty part.
- **FR-024**: The track MUST have no scrollbar: its edges MUST fade where more is hidden, and the right edge MUST say how many newer versions are out of view, counting versions only and adding "and Live" when Live is out of view too ("+5 newer and Live").
- **FR-025**: A handle scrolled out of view MUST be pinned to its edge; clicking it MUST scroll back to it.
- **FR-026**: Release names MUST thin out before they collide; the chosen version's name, the oldest and newest versions' names and Live's name MUST never thin out.
- **FR-027**: The picker MUST open with the chosen version in view.

**The message**

- **FR-028**: Under the track MUST be the chosen version's message — its pull request's title and body, or its commit's message when it had none — whole, with nothing above it, line breaks kept, long lines wrapped by words.
- **FR-028a**: The message MUST be plain text: Markdown and HTML MUST NOT be rendered. Only two things MUST become links: `http://` and `https://` addresses (trailing punctuation left out), and `#<number>`, which MUST point at that pull request of the history's own repository; every other scheme and `owner/repo#<number>` MUST stay text. Links MUST open in a new tab and MUST NOT pass Maxitor's address on to the page they open. The same MUST hold for every other link Maxitor shows for a history — the Live service, the repository, a pull request.
- **FR-029**: The message box MUST stop at nine lines of its text and scroll inside with a thin visible scrollbar; its lower edge MUST fade while more is below; its text MUST be selectable.
- **FR-030**: Live MUST have no message; a closing line MUST say "Live · checked <time> ago · newest version <name>, <date>" — without its last part in M6 — and, while Live cannot be reached, "Live · cannot be reached since <time>".

**Phone**

- **FR-031**: On a phone, the version button MUST sit in the phone bar, and the picker MUST open as a sheet from the bottom with the same track and message in every mode M2–M6 — a single point or Live alone included — every point a touch target of at least 44 px.

**The tail**

- **FR-032**: The change MUST end with the check run taken to zero, then the documentation — every case of this step shown, each as a script and a notebook that were run, with the page's Russian draft beside it — then the changelog, one article (Principle VI).

### Key Entities

- **Source**: what the address field opened — a running service, a graph-json address, or a history; held graphs belong to it.
- **History**: a service's versions, read through the port; named by one full URL — the port's history URL with `id` and read key for a private one, the GitHub link to its graph file for a public one (read through Maxitor's own port); has a name, versions, and maybe Live.
- **Version**: one merged change of the graph file; has its commit, date, pull request (or commit message), tags, size, a refusal reason if its graph fails the schema, and its graph, which never changes.
- **Live**: what the service runs now, not yet merged; named by the history's entry in the port's config; checked for freshness; has no message.
- **Release**: a version carrying a tag that has a release; names the versions after it.
- **Read key**: opens one history; shown as dots, never logged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of the seven modes M1–M7, opening it shows the button, the opening version, the picker's wording, the track, the keys' effect and Recent's text that FR-009a gives it, in 100% of opens; and each of the ten moves between modes FR-009a lists happens without a reload.
- **SC-002**: For every version of a test history, the shown graph's node and edge counts equal that version's own.
- **SC-003**: A version whose graph fails the schema is refused with its reason, and the other versions still open.
- **SC-004**: After a session that opened private histories in every mode, joined a room, revoked a key and ran every check, the key is found 0 times in: Maxitor's log file and standard output, its request log, every error body it answered, every request line Maxitor's server and the stand's front end received, the browser's history; and 0 times in full in the field, Recent and a room link until the eye is used.
- **SC-005**: A history of 64 versions, with Live (M4) and without (M2), scrolls on the track with points at least 24 px apart, and a handle out of view is pinned to its edge.
- **SC-006**: A message of several screens stops at nine lines and scrolls inside its box.
- **SC-007**: A version opened by a second reader, or again by the same one, is not built again.
- **SC-008**: A link made by **Copy link** reopens the same history on the same version in another browser in 100% of tries.
- **SC-009**: On a phone's width, every point on the track is at least 44 px wide as a touch target.
- **SC-010**: The check run passes, every step.
- **SC-011**: In a room of three participants on different pages, one pick of a version moves all three to it; after two picks at once, all three end on the same version.
- **SC-012**: A version the port starts listing while a history is open appears on the track within 30 seconds, with no reload; a check of an unchanged list is answered `304`, with no full read of the history.
- **SC-013**: A key revoked at the port opens 0 versions through Maxitor more than 30 seconds later, including versions Maxitor already holds.
- **SC-014**: The key reaches 0 servers other than Maxitor's and the port, and reaches those two only in a request header: no request line and no `Referer` carries it.

## Assumptions

- The port is `repo-graph-port` as #288 left it, with three additions: a history's config entry may name its Live service (`live`), `describe` returns it and the key's name (Q1, 2026-10-29), and the port writes the security events of FR-011f.
- There is no shared port to protect: a port belongs to one owner and serves that owner's repositories, as many as they configure (the maintainer's own at `https://repo-graph-port.aoa.run` serves only the maintainer's projects, and its address is not published). A client blocked by a port for wrong keys is blocked by that port alone, which is that owner protecting their repositories; Maxitor does not work around it.
- Maxitor's own port reads public repositories anonymously, so GitHub's limit on anonymous API reads (60 an hour per address) bounds how many pull requests and releases it can look up; versions and graphs come from git and are not counted. Giving that port a token or an App of its own, for a higher limit, is configuration, not part of this step.
- Maxitor signing its requests to a port is still out of scope, as in #288; so there is no "wrong signature of Maxitor" to log yet. The wrong signature the port logs is a webhook's.
- Recent keeps a private history's whole address, key included, in the browser's own storage, so that a history reopens without asking for the key again. This is an accepted risk: that storage is the user's own and is never sent anywhere; the entry can be removed (FR-012).
- A release is a tag with a release on the code host, as the port reports it; a tag with no release is a flag.
- A room is opened on a history; its version is one more setting the room shares (FR-022a), so the room's server learns versions in this step. The room link carries `history` and `b`, the key shown as dots.
- Comparing two versions (Diff, Side by side) is #290 and later; here the switch shows them greyed out with "comes later" (FR-015).
- A version's digest (#303) is not used here.
- Tests use a stand-in port; the stand reads `https://repo-graph-port.aoa.run`.
- How fast the port itself learns of a merge is #288's: at once by webhook, or within its fallback interval (ten minutes on the stand today, where webhooks do not arrive). Maxitor's 30 seconds count from when the port lists it.
