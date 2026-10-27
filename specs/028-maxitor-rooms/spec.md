# Feature Specification: Maxitor Rooms — Looking at One Service Together

**Feature Branch**: `feature/issue-271-maxitor-rooms`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/271 — Maxitor rooms, fresh graphs, graphs kept in memory, project link in the left panel, ERD table style. Use the issue body as the source of truth. The feature directory already exists: specs/028-maxitor-rooms (branch feature/issue-271-maxitor-rooms); the design mockup specs/028-maxitor-rooms/mockup/index.html is part of the specification and must be referenced from spec.md."

**Design mockup**: [mockup/index.html](mockup/index.html) — 21 screens in Maxitor's own sizes and colours, each with notes that name the section of the issue it shows. It is part of this specification: where this text and the mockup describe the same screen, they must agree; where the text is silent about a visual detail, the mockup decides.

## Context: what is true today, checked on 2026-10-27

- **Every viewer is alone.** Maxitor has no notion of other people looking at the same service. The address already describes a page completely: `source`, `view`, `domain`, `node`, `host` (`client/src/lib/urlState.ts`).
- **The full-graph layout depends on the canvas size.** On a first open G6 lays the graph out with `g6LayoutOptions` (`client/src/components/diagrams/FullGraphViewer/layoutSettings.ts`) and centres it at `width / 2, height / 2` itself, so a phone and a monitor lay the same graph out around different centres; a repeat open replays the remembered positions. `forceLayout.ts` reproduces that layout exactly but is used only by its test. The simulation's starting spiral uses `Math.cos` and `Math.sin` inside `d3-force`. The other settings (`alphaDecay` 0.012, `alphaMin` 0.0015, `velocityDecay` 0.42, 220 steps) are already explicit in `layoutSettings.ts`.
- **The arrangement is remembered per browser** (#245, merged): positions are stored in IndexedDB under a fingerprint of the graph and the layout settings. A change of the layout code that keeps the settings would reuse old positions.
- **Nodes can no longer be dragged.** #245 removed node dragging: the full graph is built with `drag-canvas` and `zoom-canvas` only. The issue's §4.4 (shared dragging) therefore has nothing to share and is not part of this specification.
- **The node-type filter of the full graph does not exist.** The issue names #246 for it; no issue or pull request #246 exists in this repository. The ERD's entity-kind filter (#239) is merged. The room shares every filter that exists when it is built, and a filter added later joins through the same rule.
- **Maxitor holds built graphs in memory with an idle timeout.** `GraphStore` (`packages/aoa-maxitor/src/aoa/maxitor/api/graph_store.py`) keeps at most 50 graphs (`MAXITOR_MAX_GRAPHS`), drops a graph unread for an hour (`MAXITOR_GRAPH_IDLE_SECONDS`, 3600), evicts the least recently read one beyond the limit, and never re-checks a source on a timer. After #268 one graph of the reference source costs about 22 MiB of the process.
- **A graph changes only through the Reload button.** Maxitor downloads `graph-json` with a plain `GET` (15 s timeout) and keeps the result; nothing compares a held graph with its service again.
- **Services do not say whether their graph changed.** The FastAPI adapter (`packages/aoa-fastapi-adapter`) sets no `ETag` and answers no conditional request. The demo service builds its `graph-json` once per process and caches it, so its graph changes only when it restarts.
- **No WebSocket can be accepted today.** `aoa-maxitor` depends on `uvicorn>=0.30` without `websockets` or `wsproto`. `GraphSourceMiddleware` already passes non-HTTP connections through untouched.
- **The left panel ends with the tree.** There is no footer, no project link and no version. The repository is `github.com/bystrovmaxim/aoa`. The `aoa-maxitor` package is at version 2.2.0 (`packages/aoa-maxitor/pyproject.toml`), and nothing in the page shows it. The `pyproject.toml` of `aoa-maxitor` still points its URLs at an older repository.

## Clarifications

### Session 2026-10-27

- Q: Does the tool that compares layouts in Chromium, Firefox and WebKit belong to the mandatory check run? → A: Yes — it runs in `scripts/run_checks_with_log.sh` on every check, three engines at both sizes.
- Q: What are the room server's limits on rooms per process, messages per second and message size? → A: 100 rooms per process, 40 messages per second per connection, 4 KB per message.
- Q: What happens when a room link names a different service (`source`) than the room belongs to? → A: The room wins — Maxitor opens the room's service, corrects the address and joins; the page from the link is kept if that service has it, otherwise the page of the person who opened the room.
- Q: How does the room server keep its log? → A: Room operations are AOA actions run on Maxitor's machine; they log through `box.info` / `box.warning` / `box.critical`; pointers and screen positions bypass the actions and are never logged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The same picture on every device (Priority: P1)

Two people open the same diagram of the same service — one on a phone, one on a wide monitor, in different browsers. Every node stands at the same point of the diagram for both of them; only the zoom and the scroll differ.

**Why this priority**: Pointers, "go to someone" and following all say "the same spot of the diagram". Without identical positions the room shows people pointing at the wrong things, which is worse than no room.

**Independent Test**: Lay out every page of the reference fixture, in every layout mode, in the three browser engines at phone and desktop size, and compare the layout hashes.

**Acceptance Scenarios**:

1. **Given** the reference fixture, **When** any page is laid out in any layout mode in Chromium, Firefox or WebKit at 375×812 or 1600×900, **Then** its layout hash is the same in all of them.
2. **Given** the full-graph layout, **When** it runs, **Then** it never calls `Math.cos`, `Math.sin`, `Math.pow` or `Math.random`, and its centre does not depend on the canvas size; a test fails when either comes back.
3. **Given** a change of the layout code that moves any node, **When** the tests run, **Then** the golden hash of the fixture fails until it is updated on purpose in the same commit.
4. **Given** positions remembered by an older version of the layout code, **When** the page opens, **Then** they are not reused.

---

### User Story 2 - Opening a room and joining it (Priority: P1)

Anna presses **Open room**, types her name and gets a link. Boris opens the link on his phone, types his name and lands on the same page with the same filters and layout mode. Both see two coloured circles at the top of the workspace.

**Why this priority**: The room is the feature; everything else happens inside one.

**Independent Test**: Open a room in one browser, join by the link in another, and check the address, the circles, the names and the page.

**Acceptance Scenarios**:

1. **Given** a page outside a room, **When** Anna presses **Open room** and confirms her name, **Then** a room is created, `room=<id>` is added to the address and a card offers the link with a note that anyone with it can join (mockup screens 1–3).
2. **Given** the link, **When** Boris opens it, **Then** he is asked for his name, sees who is already in the room, and after joining lands on the same page with the room's filters and layout mode (screen 4).
3. **Given** a room with two people, **When** either looks at the top row, **Then** both circles are there, their own first and ringed, each in a colour no one else in the room has.
4. **Given** a name typed before, **When** the name dialog opens, **Then** that name is filled in; a name is 1–40 characters after trimming.
5. **Given** a desktop, **When** someone in a room wants to leave it, **Then** the button says **Leave room**; on a phone the same action and **Copy room link** are in a menu behind one ⋮ button (screen 5).
6. **Given** a link to a room that no longer exists, **When** it is opened, **Then** the page opens without a room and says *"This room has ended"*, with **Open room** next to it (screen 18).
7. **Given** Anna has moved to another page, **When** she presses **Copy link**, **Then** the copied address names the page she is on now and the room; opened elsewhere, it lands on that page in that room. On a phone the button opens the system share sheet where there is one; where the clipboard is not available, the link is shown in a field, already selected; *Link copied* confirms a copy.
8. **Given** a person in a room, **When** they press **Leave room**, **Then** the page keeps its diagram, filters and layout mode, and `room` disappears from the address.
9. **Given** the name dialog, **When** it opens, **Then** it says under the input: *Everyone with the link sees your name and your pointer.*
10. **Given** a person in a room, **When** they click their own circle and choose **Change name**, **Then** the new name reaches everyone at once and the colour stays.
11. **Given** a room with 20 participants, **When** a 21st person opens its link, **Then** they see *This room is full (20 people)* instead of the name dialog, and the page opens without a room.
12. **Given** a person in a room, **When** they choose *Load a different service* in the left panel, **Then** Maxitor first asks *Leave the room and open another service?* and leaves the room only on yes; **Reload** in the left panel does not leave the room.

---

### User Story 3 - Seeing each other's pointers (Priority: P1)

Anna moves her mouse over a table; Boris sees her arrow with her name on the same table, although his screen is smaller and zoomed differently. Boris touches his screen; Anna sees a short-lived ring where his finger is.

**Why this priority**: Pointing is how people talk about a diagram together.

**Independent Test**: Two browsers in one room, one at phone size; place a pointer on the centre of a node in one and measure where it appears in the other, before and after zooming either.

**Acceptance Scenarios**:

1. **Given** two people on the same page, **When** one places a pointer on the centre of a node, **Then** the other sees it on the centre of the same node within 2 px of screen, before and after either of them zooms or scrolls (screen 6).
2. **Given** a touch screen, **When** a person touches it, **Then** the others see a ring in that person's colour that fades after about a second.
3. **Given** a pointer outside your view, **When** you look at the edge of the workspace, **Then** a small arrow in that person's colour with their initials points toward it, and a click on it centres your view on that pointer without changing your zoom (screen 8).
4. **Given** a tab in the background, **When** it is hidden, **Then** it stops sending its pointer.
5. **Given** a pointer that has not moved for 10 seconds, **When** the others look at it, **Then** it has faded out; it comes back when it moves. The circle of a participant whose active tab is in the background is drawn pale.
6. **Given** a person whose connection is lost, **When** Maxitor reconnects, **Then** the row shows *Reconnecting…*, other people's pointers are hidden until the connection is back, and a return within two minutes keeps the person's id, name and colour without anyone seeing a leave and a join.
7. **Given** a person who switches **Hide pointers** on, **When** others move, **Then** their pointers are not drawn on that screen; the circles stay, the person's own pointer is still shown to others, and the choice is kept in the browser.
8. **Given** a room, **When** someone joins or leaves, **Then** a short notice — *Boris joined*, *Anna left* — fades after a few seconds; a reconnect within two minutes shows nothing.

---

### User Story 4 - Shared filters and layout modes, without a host (Priority: P1)

Boris switches a domain off and the layout to top-to-bottom; Anna's page changes the same way. Nobody owns the room: whoever changes a setting, it changes for everyone.

**Why this priority**: If filters were personal, two people would be looking at different pictures and pointers would land on hidden or moved nodes.

**Independent Test**: Change a filter and a layout mode in one browser; check the second browser; open the page in a third browser later and check it gets the same settings.

**Acceptance Scenarios**:

1. **Given** a room, **When** anyone changes a filter or the layout mode of a page, **Then** it changes for everyone in the room on that page, and the person who opened the room has no extra rights (screen 7).
2. **Given** settings changed on one page, **When** someone looks at another page, **Then** that page's settings are untouched.
3. **Given** a page whose settings were changed, **When** a person opens it later, **Then** they get the room's current settings for it.
4. **Given** two people who switch the same filter at the same moment, **When** both changes arrive, **Then** the result does not depend on the order of arrival: a change says "set on" or "set off", never "toggle".
5. **Given** a room, **When** one person zooms or scrolls, **Then** nobody else's view moves.

---

### User Story 5 - Going to someone (Priority: P2)

Anna has gone to the full graph. Boris sees on her circle's card where she is and clicks the circle: his screen opens the full graph centred on Anna's pointer, at his own zoom.

**Why this priority**: Finding where a colleague is looking is the first thing people need once they move apart.

**Independent Test**: Put two people on different pages; click one's circle in the other's browser; check the page, the centre and the zoom.

**Acceptance Scenarios**:

1. **Given** a participant on another page, **When** you hover their circle (long-press on a touch screen), **Then** their card shows their full name, their page, **Go to** and **Follow** (screen 9).
2. **Given** a click on a circle or on **Go to**, **When** it is handled, **Then** your screen opens their active page and centres on their pointer, or on the centre of their screen when they have none, without changing your zoom (screen 10).
3. **Given** more people than fit (more than 5 circles on a desktop, 3 on a phone), **When** the row is drawn, **Then** the rest collapse into **+N**, which opens a list with the same actions (screen 14).

---

### User Story 6 - Following someone, switching, stopping, and never in a circle (Priority: P2)

Boris follows Anna: his screen goes wherever she goes, at his own zoom, inside a frame in her colour. He can switch to following Vera in one step or stop at any moment. Nobody can follow someone who already follows them, directly or through others.

**Why this priority**: Following turns a room into a walk-through; without the ban on circles two followers would chase each other forever.

**Independent Test**: Follow, switch, stop with the button and with Esc; try to follow a follower directly and through a third person; press Follow on each other at the same moment from two browsers.

**Acceptance Scenarios**:

1. **Given** Boris chooses **Follow** on Anna's card, **When** Anna scrolls or opens another page, **Then** Boris's screen goes there too, centred on the centre of Anna's screen, at Boris's own zoom; a frame in Anna's colour shows "Following Anna · Stop" (screen 11).
2. **Given** Boris follows Anna, **When** he zooms, **Then** his zoom changes and following goes on; **When** he pans, opens another page himself, presses **Stop** or Esc, or Anna leaves, **Then** following ends and the view stays where it is.
3. **Given** Boris follows Anna, **When** he opens Vera's card, **Then** it offers **Follow Vera instead**, which switches in one step (screen 12).
4. **Given** Anna follows Boris, or Vera follows Anna who follows Boris, **When** Boris opens Anna's or Vera's card, **Then** it says *following you* (or through whom), **Follow** is disabled with the reason under it, and **Go to** still works (screen 13).
5. **Given** two people press Follow on each other at the same moment, **When** both requests arrive, **Then** exactly one succeeds and the other is refused with the same reason.
6. **Given** Anna follows Vera, **When** Boris follows Anna, **Then** Boris sees what Anna sees.
7. **Given** Boris and Vera follow Anna, **When** Anna looks at her own circle, **Then** it carries a counter and her card says *2 following you*.
8. **Given** Boris has followed Anna through ten pages, **When** he stops and presses the browser's **Back**, **Then** he returns to the page he was on before following, not through Anna's pages.

---

### User Story 7 - A changed model reaches open pages by itself (Priority: P2)

A service is redeployed with a new model. Within a minute every open page of that source redraws with the new graph, on the same page, with the same filters, layout mode and zoom, and says briefly that the model was updated. Restarting a service with an unchanged model changes nothing.

**Why this priority**: Without it a room splits into people with old and new graphs, and today a viewer never sees a change without pressing Reload.

**Independent Test**: Serve a source, open it, change the served graph, and wait one check interval; then restart the source with the same content and see nothing rebuilt.

**Acceptance Scenarios**:

1. **Given** an open page of a source whose graph changed, **When** the next check runs, **Then** the graph is rebuilt in the background and the page redraws within one check interval, keeping its page, filters, layout mode, zoom and centre, with a short notice *"The model was updated"* (screen 16).
2. **Given** a source restarted with the same content, **When** it is checked, **Then** nothing is rebuilt and nothing redraws.
3. **Given** a filter that names something removed from the model, **When** the page redraws, **Then** that filter is dropped and the rest stay.
4. **Given** a room, **When** the graph changes, **Then** every participant gets the new graph at the same moment.
5. **Given** a service that sets `ETag` or `Last-Modified`, **When** Maxitor checks it, **Then** an unchanged graph costs a `304` answer with no body.
6. **Given** a source without those headers, **When** it changes, **Then** it is still noticed, by comparing a hash of the downloaded content.
7. **Given** a source that does not answer, or whose new build fails, **When** it is checked, **Then** the held graph stays and stays viewable, and the next check tries again.
8. **Given** the left panel's **Reload**, **When** it is pressed, **Then** it rebuilds at once, as today.

---

### User Story 8 - Graphs stay ready until the limit (Priority: P2)

The demo, or any source people come back to, stays built in memory, so the first visitor after a quiet hour does not wait for a download and a build.

**Why this priority**: It removes the slowest open — the first one after a quiet period — at a memory price the operator chooses.

**Independent Test**: Build a graph, leave it unread longer than an hour, read it again and check that no build ran; fill the store beyond its limit and check which graph left.

**Acceptance Scenarios**:

1. **Given** a held graph unread for any time, **When** the store is under its limit, **Then** the graph stays.
2. **Given** a full store, **When** a new source is built, **Then** the graph read longest ago is removed.
3. **Given** held graphs without open tabs, **When** time passes, **Then** none of their sources is checked until it is read again; on that read the held graph is answered at once and the check runs in the background.

---

### User Story 9 - An out-of-date tab looks after itself (Priority: P2)

A tab left open over a Maxitor deploy notices it, says so and reloads itself, coming back on the same page, room, zoom and centre. Only a genuine layout bug leaves a message, and then pointers on that page are off.

**Why this priority**: A stale tab is the realistic case of disagreement in a room, and asking people to read a technical warning and press Reload is avoidable.

**Independent Test**: Keep a tab open, deploy a new build, and watch it reload and restore its view; fake a layout-hash mismatch with the same build and graph and see the message, no reload, and no pointers.

**Acceptance Scenarios**:

1. **Given** a tab whose app build differs from the server's, **When** it joins or stays on a page in a room, **Then** it shows *"Maxitor was updated — reloading…"*, reloads itself and comes back on the same page, room, zoom and centre (screen 15).
2. **Given** a tab that reloaded itself in the last five minutes, **When** the build still differs, **Then** it does not reload again.
3. **Given** a tab whose graph fingerprint differs from the server's, **When** this is noticed, **Then** it re-reads the graph in place, without reloading the page.
4. **Given** a tab whose layout hash differs while its build and graph are the server's, **When** it is on that page, **Then** pointers are off in both directions on that page, the message *"Pointers are off on this page: your diagram is laid out differently from the room's."* is shown, and nothing reloads (screen 17).

---

### User Story 10 - The ERD in the mockup's style (Priority: P3)

Entity tables in every ERD view look as in the mockup: a header in the domain colour flush with the frame, every second row tinted in the domain colour, `PK` in rust-red.

**Why this priority**: It is a visual change the maintainer asked for together with the rooms; nothing else depends on it.

**Independent Test**: Open an ERD and compare a table with mockup screen 21.

**Acceptance Scenarios**:

1. **Given** any ERD view, **When** a table is drawn, **Then** it matches FR-110 to FR-115 and mockup screen 21.

---

### User Story 11 - A link to the project in the left panel (Priority: P3)

At the bottom of the left panel the user finds the GitHub mark linking to Maxitor, with the name and the running version, centred, when the panel is open.

**Why this priority**: A way to the source, and the version to quote when something looks wrong; independent of everything else.

**Independent Test**: Open the panel and collapse it; check the link and the version against the installed package.

**Acceptance Scenarios**:

1. **Given** an open left panel, **When** it is drawn, **Then** its bottom shows, centred and with no divider line above it, the GitHub mark, **Maxitor** and the running version (`2.2.0` today), and nothing else (every desktop screen of the mockup).
2. **Given** a new release of `aoa-maxitor`, **When** it is deployed, **Then** the footer shows the new version without anyone editing it.
3. **Given** a collapsed panel, **When** it is drawn, **Then** only the mark remains, still a link (screen 20).

---

### Edge Cases

- **A room is full or a limit is hit** (participants per room, rooms per process, message rate or size): the connection is refused with a reason the page shows in one sentence (screen 19).
- **A person has several tabs**: they are one participant; their page, pointer and screen are those of the tab they used last; when that tab closes, the most recently active remaining tab takes over.
- **A person leaves by closing the last tab**: their circle goes; their colour becomes free; anyone following them stops following.
- **The last person leaves**: the room ends two minutes later, so a reload does not end it.
- **The server restarts**: every room ends; links to them open without a room and say so.
- **The same name twice**: allowed; colours tell the two people apart. Names are never verified, and the dialog says so.
- **A name of spaces only or over 40 characters**: refused in the dialog before joining.
- **The person followed opens a page the follower cannot see the same way** (another layout hash): following goes on; pointers on that page are off for the one whose layout differs.
- **The person followed follows someone else**: you see what they see.
- **A follow request that would close a circle arrives while the card still showed Follow enabled**: the server refuses it with the reason; the card updates.
- **A check finds the graph changed while a rebuild of the same source is already running**: checks of one source never overlap; the next check sees the result.
- **The store is full of graphs nobody looks at**: none of them is checked on a timer.
- **The room's link is opened in a browser whose name was never asked**: the dialog asks; nothing is shown to others until the person joins.
- **A room link names another service than the room's** (edited or pasted in pieces): the room's service opens, the address is corrected, the person joins (FR-010).
- **A phone has no hover**: a circle's card opens on a long press.
- **The connection drops for longer than two minutes**: the person comes back as a newcomer — a leave and a join are shown, and the colour may change.
- **The clipboard is not available** (the page is served over plain HTTP from another host): **Copy link** shows the link in a field, already selected, to copy by hand.
- **The person you follow loses the connection**: following goes on through *Reconnecting…*; it stops only when they leave for good.
- **Someone presses Reload in a room**: the graph is rebuilt for everyone, and every tab redraws by FR-076; nobody leaves the room.

## Requirements *(mandatory)*

### Functional Requirements

**Identical positions (issue §4)**

- **FR-001**: The full-graph layout MUST be centred at the origin of the diagram, never at the canvas size; fitting the picture into the screen MUST remain a view operation that does not move nodes.
- **FR-002**: Starting positions of the full-graph layout MUST be computed by Maxitor with addition, subtraction, multiplication, division and square root only, keeping the character of today's golden-angle spiral.
- **FR-003**: Every simulation setting MUST be explicit, the number of steps fixed, and nodes and edges MUST enter the layout in the order of the server's answer.
- **FR-004**: A layout version MUST be part of the key under which arrangements are remembered, so arrangements of older code are never reused.
- **FR-005**: A guard test MUST fail when `Math.cos`, `Math.sin`, `Math.pow` or `Math.random` is called during the full-graph layout, or when its centre depends on the canvas size; a golden layout hash of the reference fixture MUST fail on any change that moves a node.
- **FR-006**: A tool MUST lay out every page of the fixture in every layout mode in Chromium, Firefox and WebKit, at 375×812 and 1600×900, and report whether all layout hashes are equal. It MUST be a step of the mandatory check run, and the step MUST fail when any hash differs.

**Rooms (issue §6, §9)**

- **FR-010**: Anyone on a page MUST be able to open a room; the room's id MUST be 128 random bits and appear in the address as `room`; the link is the only invitation. A room MUST belong to one source: when a room link names another `source`, the room's source MUST win — Maxitor opens it, corrects the address and joins; the page named in the link MUST be kept if the room's source has it, otherwise the active page of the person who opened the room (or, if they have left, of the participant active most recently) MUST open.
- **FR-011**: Opening and joining MUST ask for a name of 1–40 characters after trimming, offering the last name used in this browser.
- **FR-012**: Each participant MUST get a colour from a palette told apart on light and dark backgrounds, distinct from every other participant's in the room; a colour MUST be freed when its owner leaves.
- **FR-013**: All tabs of one browser in one room MUST be one participant; the tab where the participant last moved, touched, or arrived by link or navigation MUST be the active one, and only its page, pointer and screen are shown to others.
- **FR-014**: A participant MUST leave when their last tab closes; a room MUST end two minutes after its last participant leaves; a link to an ended room MUST open the page without a room and say *"This room has ended"*.
- **FR-015**: A room MUST hold at most 20 participants; the process MUST hold at most 100 rooms; each connection MUST send at most 40 messages a second and no message larger than 4 KB; a refusal MUST carry a reason the page shows in one sentence.
- **FR-016**: A connection from an origin other than the one Maxitor serves MUST be refused with code 4403 before it joins a room or receives anything about it.
- **FR-017**: A room MUST NOT hold a graph: every participant reads the graph by its source, as today.
- **FR-018**: A room MUST give the person who opened it no extra rights.
- **FR-019**: **Leave room** MUST keep the page as it is — diagram, filters and layout mode — without the room, and remove `room` from the address.

**Top row, circles and cards (issue §7)**

- **FR-020**: A row at the top of the workspace MUST be as high as the left panel's header row (38 px today), on the workspace surface, without shadow; its icons MUST be 14 px. On a phone the existing 44 px bar holds the room controls.
- **FR-021**: Outside a room the row MUST hold **Open room**; inside, the circles, **Copy link** and **Leave room**. On a phone, **Copy room link** and **Leave room** MUST be in a menu behind one ⋮ button.
- **FR-022**: A circle MUST be filled with the participant's colour and carry one or two initials (first letters of the first two words, or the first two letters of a one-word name) in a colour chosen for contrast; your own comes first and is ringed; beyond 5 circles on a desktop or 3 on a phone the rest MUST collapse into **+N**.
- **FR-023**: A participant's card MUST show the full name, the page, *following you* when they follow you (directly or through others), **Go to** and **Follow** (or **Follow <name> instead** while you follow someone else); on a touch screen it MUST open on a long press.
- **FR-024**: Dialogs, cards, lists and menus of the room MUST follow the form of the left panel's *AOA Service URL*: a white card with 8 px corners and a soft shadow, slate text, labels in small capitals, the same outlined input, quiet buttons like the zoom bar, no coloured primary button and no heavy backdrop — as in the mockup.
- **FR-025**: **Copy link** MUST copy the current address — the page the person is on now — with `room`; on a phone it MUST open the system share sheet where there is one; where the clipboard is not available it MUST show the link in a field, already selected; a copy MUST be confirmed with *Link copied*.
- **FR-026**: A **Hide pointers** switch in the row (in the ⋮ menu on a phone) MUST hide other people's pointers on that screen only, keep the circles, and be remembered in the browser.
- **FR-027**: Joins and leaves MUST be announced with a notice that fades after a few seconds; a reconnect within two minutes MUST NOT be announced.
- **FR-028**: Every circle, the +N list and every button of the row MUST be reachable with Tab and opened with Enter; each circle MUST be announced with the full name and the page; Esc MUST stop following and close a card.

**Shared settings (issue §5)**

- **FR-030**: Inside a room, every filter of every viewer that exists (ERD domains and entity kinds, use-case domains, one-hop, and any filter added later) and the layout mode MUST be read from and written to the room, per page.
- **FR-031**: A setting change MUST be sent as "set on" or "set off" (or "set to"), never as "toggle"; the last change MUST win.
- **FR-032**: Zoom, scroll, hover cards, highlights, collapsed panels and the left panel MUST stay personal. *(Changed by spec 029, FR-013: they stay personal except while following — a follower sees the followed person's hover, tooltip, selection and open panels.)*
- **FR-033**: A person who opens a page MUST get the room's current settings for it.

**Pointers (issue §8)**

- **FR-040**: Mouse and touch pointers MUST be sent in diagram coordinates and drawn re-projected on every pan and zoom, in all four viewers.
- **FR-041**: A mouse pointer MUST be drawn as an arrow with a name tag in the participant's colour; a touch as a ring that fades after about a second.
- **FR-042**: A pointer outside the view MUST be drawn as an arrow at the edge with the participant's initials; a click on it MUST centre the view on that pointer without changing the zoom.
- **FR-043**: A pointer MUST be sent at most 20 times a second and a screen position at most 10 times a second, each only when it changed, so a tab never exceeds 30 messages a second in normal use, under the limit of FR-015; a background tab MUST stop sending; a slow connection MUST receive the newest position, not a queue.
- **FR-044**: A pointer that has not moved for 10 seconds MUST fade out and come back when it moves; the circle of a participant whose active tab is in the background MUST be drawn pale.
- **FR-045**: While a tab's connection is lost, other people's pointers MUST be hidden on it.

**Going to someone and following (issue §8)**

- **FR-050**: A click on a circle or **Go to** MUST open that participant's active page and centre on their pointer, or on the centre of their screen when they have no pointer, without changing the zoom.
- **FR-051**: Following MUST keep the follower on the followed person's active page, centred on the centre of their screen, without copying their zoom; zooming MUST NOT stop following; panning, navigating, **Stop**, Esc or the followed person's leaving MUST stop it.
- **FR-052**: While following, a frame in the followed person's colour MUST surround the workspace with "Following <name> · Stop" (on a phone, above the zoom bar).
- **FR-053**: **Follow <name> instead** MUST switch in one step; a person MUST follow at most one other.
- **FR-054**: Following MUST never close a circle: a Follow whose target follows you, directly or through others, MUST be disabled in the card with its reason, and the server MUST refuse it atomically, so two crossing requests cannot both succeed.
- **FR-055**: Following MUST make nobody a leader: it changes only the follower's screen.
- **FR-056**: A person who is followed MUST see a counter on their own circle, and *N following you* in their card.
- **FR-057**: A page opened because the person follows someone MUST replace the current entry of the browser's history, not add one.

**Staying in the room (issue §6, §9)**

- **FR-060**: The name dialog MUST say *Everyone with the link sees your name and your pointer.*
- **FR-061**: A participant MUST be able to change their name from their own card; the new name MUST reach everyone at once and the colour MUST stay.
- **FR-062**: On a lost connection the row MUST show *Reconnecting…* and the tab MUST reconnect by itself with growing pauses; the server MUST keep the participant's id, name, colour and active page for two minutes, so a reconnect within that time is not a leave and a join; after two minutes they MUST come back as a newcomer.
- **FR-063**: A person refused by a full room MUST see *This room is full (20 people)* instead of the name dialog and get the page without a room.
- **FR-064**: Inside a room, *Load a different service* MUST ask *Leave the room and open another service?* and leave the room only on yes.
- **FR-065**: Inside a room, **Reload** MUST NOT leave the room: it rebuilds the graph for everyone, and every tab redraws by FR-076.
- **FR-066**: The WebSocket endpoint MUST be a thin adapter: every room operation — creating, joining, leaving, renaming, changing a page setting, following and stopping — MUST run as an AOA action on Maxitor's machine.
- **FR-067**: Room actions MUST log through `box`: room created and ended (with the room id and the number of participants), joins, leaves and reconnects with `box.info` on `Channel.business`; refusals (a limit with its name, a foreign `Origin`, a follow that would close a circle) with `box.warning` on `Channel.security`; internal failures are not logged by the action itself — the machine's `UnhandledErrorEvent` carries them to logging plugins and the connection closes `1011` (contracts/room-actions.md says why `box.critical` cannot be called there).
- **FR-068**: Pointer and screen-position messages MUST NOT run as actions and MUST NOT be logged: the adapter relays them directly, and a slow connection receives the newest position, not a backlog (FR-043).
- **FR-069**: A log record MUST name a room and a participant only by their ids, never by the participant's name.

**Fresh graphs (issue §10)**

- **FR-070**: Every successful `GET` answer of the FastAPI adapter MUST carry an `ETag` that is a hash of its content, and a request with a matching `If-None-Match` MUST get `304` with no body.
- **FR-071**: Maxitor MUST check every held source that has at least one open tab: every 30 seconds when the source gives `ETag` or `Last-Modified`, every 2 minutes when it does not.
- **FR-072**: Without those headers Maxitor MUST detect a change by comparing a SHA-256 of the downloaded content with the one the held graph was built from; the check MUST NOT be required of a source.
- **FR-073**: A held source without open tabs MUST NOT be checked on a timer; on its next read the held graph MUST be answered at once and the check run in the background.
- **FR-074**: Checks of one source MUST NOT overlap and MUST share the store's build slots.
- **FR-075**: A changed source MUST be rebuilt in the background; the new graph MUST replace the old one only after its build succeeded; a failed build or an unreachable source MUST keep the old graph.
- **FR-076**: Every open tab of a changed source MUST learn of it — through the room inside a room, through a request every 30 seconds that returns the graph fingerprint from memory outside one — and MUST re-read the left panel and the current diagram, keeping the page, filters, layout mode, zoom and centre, dropping filters that name things no longer in the model, and showing *"The model was updated"* for a few seconds.
- **FR-077**: The left panel's **Reload** MUST keep rebuilding at once.

**Graphs kept in memory (issue §11)**

- **FR-080**: A held graph MUST stay until the store's limit is reached; then the graph read longest ago MUST be removed; the idle timeout and `MAXITOR_GRAPH_IDLE_SECONDS` MUST be removed.
- **FR-081**: The limit MUST remain configurable as `MAXITOR_MAX_GRAPHS`; the stand's value is set in the plan from the machine's memory.

**Out-of-date tabs (issue §4.3)**

- **FR-090**: On joining a page in a room, a tab MUST report its app build, graph fingerprint and layout hash. The app build and the graph fingerprint MUST be compared with the server's own values, never with other participants'. The layout hash, which only a browser can compute, MUST be compared with the first hash reported in the room for the same page and the same settings.
- **FR-091**: A tab whose app build differs MUST show *"Maxitor was updated — reloading…"*, reload itself, and restore the page, room, zoom and centre; it MUST NOT reload itself more than once in five minutes.
- **FR-092**: A tab whose graph fingerprint differs MUST re-read the graph in place.
- **FR-093**: A tab whose layout hash differs, compared as FR-090 describes, while its build and graph match MUST have pointers off on that page in both directions and show *"Pointers are off on this page: your diagram is laid out differently from the room's."*, without reloading.

**Left panel footer (issue §12)**

- **FR-100**: The bottom of the left panel MUST hold the GitHub mark linking to `https://github.com/bystrovmaxim/aoa/tree/main/packages/aoa-maxitor` in a new tab, with no divider line above it.
- **FR-101**: With the panel open, the mark MUST be followed by **Maxitor** and the version of the running Maxitor, the three centred in the panel's width; the footer MUST show no copyright and no year. The version MUST come from the `aoa-maxitor` package, never be written by hand.
- **FR-102**: With the panel collapsed, only the mark MUST remain, as a link with the tooltip "Maxitor on GitHub".

**ERD table style (issue §13)**

- **FR-110**: An entity table's header MUST be filled with the domain colour and flush with the frame, sharing its rounded top corners, with the entity name white, semibold, left-aligned.
- **FR-111**: The frame MUST be drawn in the domain colour around a white body with rounded corners.
- **FR-112**: Every second row MUST be tinted with the domain colour at low opacity (6 % in the mockup).
- **FR-113**: `PK` MUST be bold rust-red (`#b45309`) and `FK` bold slate (`#475569`), in a column of their own before the field name.
- **FR-114**: The field name MUST be on the left and its type, smaller and grey, right-aligned.
- **FR-115**: Relation lines MUST be grey with a filled arrowhead; a generalization MUST be dashed. The mockup's sizes (header 30, row 20, frame 1.4, radius 9, in diagram units) are the target proportions.

### Key Entities

- **Room**: a group of people looking at one service together; identified by a random id; holds its participants and the settings of every page; lives in the memory of the process and ends two minutes after it empties.
- **Participant**: one person in a room — a name, a colour, one or more tabs, an active tab, and at most one person they follow.
- **Page**: one diagram with its parameters, as the address describes it.
- **Page settings**: the filters and the layout mode of one page in one room.
- **Pointer**: a participant's position in diagram coordinates, of a mouse or a touch, on their active page.
- **Follow link**: "A follows B"; the set of links never contains a circle.
- **Held graph**: a built graph of one source in Maxitor's memory, with the hash of the content it was built from, its validators (`ETag`, `Last-Modified`) if any, and when it was last read.
- **Layout hash, graph fingerprint, app build**: the three values a tab reports to show its picture is the server's.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every page of the reference fixture in every layout mode, the layout hash is identical in the three browser engines at phone and desktop size (issue criterion 1).
- **SC-002**: The guard test fails when any of the four forbidden functions is used during the full-graph layout, or the centre depends on the canvas size (criterion 2).
- **SC-003**: A pointer on the centre of a node in one browser appears within 2 px of the centre of the same node in a second browser at phone size, before and after either zooms (criterion 3).
- **SC-004**: A filter or layout mode changed in one browser is applied in a second, and a third that joins later gets it; the person who opened the room has no more rights than anyone else (criteria 4, 13).
- **SC-005**: A participant with two tabs appears once, with the page and pointer of the tab used last (criterion 5).
- **SC-006**: A click on a circle opens the right page centred on that participant's pointer, with the zoom unchanged (criterion 6).
- **SC-007**: Following follows pages and the screen centre, keeps the follower's zoom, stops on pan, navigation, Stop or Esc, switches to another person in one step, and no Follow that closes a circle succeeds — including two crossing requests (criteria 7, 11, 12).
- **SC-008**: A tab with an older build reloads itself once and returns to the same page, room, zoom and centre; a tab with a different layout hash but the same build and graph shows the pointers-off message and does not reload (criterion 8).
- **SC-009**: A link to an ended room opens without a room and says so; every limit refuses with a one-sentence reason (criteria 9, 10).
- **SC-010**: An adapter answer carries an `ETag`, and a repeated request with it gets `304` with no body (criterion 17).
- **SC-011**: After a service's graph changes, every open tab of that source redraws within one check interval and keeps its page, filters, layout mode, zoom and centre; restarting a service with the same content rebuilds nothing (criterion 18).
- **SC-012**: A source without validators is still updated by content hash; an unreachable source keeps its graph and stays viewable (criterion 19).
- **SC-013**: No graph is removed for being idle; beyond `MAXITOR_MAX_GRAPHS` the one read longest ago is removed; a source held without open tabs is not checked until it is read again (criteria 20, 21).
- **SC-014**: The leave action reads **Leave room** on a desktop and in the phone's room menu (criterion 14).
- **SC-015**: ERD tables match FR-110 to FR-115 and mockup screen 21 (criterion 15).
- **SC-016**: The left panel shows the link, the name and the installed package's version, centred, when open, and only the link when collapsed (criterion 16).
- **SC-017**: **Copy link** gives the address of the page the person is on now, with the room; opened elsewhere, it lands on that page in that room (criterion 22).
- **SC-018**: After **Leave room** the page keeps its diagram, filters and layout mode, and the address has no `room` (criterion 23).
- **SC-019**: A participant whose connection drops and returns within two minutes keeps their name and colour, and nobody sees a leave or a join; while the connection is lost, other people's pointers are hidden and *Reconnecting…* is shown (criterion 24).
- **SC-020**: The 21st person to open a room's link is told the room is full and gets the page without a room (criterion 25).
- **SC-021**: *Load a different service* inside a room asks first and leaves the room on yes (criterion 26).
- **SC-022**: **Hide pointers** hides other people's pointers on that screen only; **Change name** reaches everyone and keeps the colour (criterion 27).
- **SC-023**: Back after following returns to the page before following, not through the followed pages (criterion 28).
- **SC-024**: The row is usable with the keyboard alone, and each circle is announced with the name and the page (criterion 29).

## Assumptions

- **Maxitor runs as one process.** Rooms live in its memory; several processes, and rooms that survive a restart, are out of scope (issue §16).
- **No accounts.** Names are typed, never verified; the link is the only invitation; private rooms and passwords are out of scope.
- **Node dragging stays removed.** #245 removed it; the issue's shared dragging (§4.4) is not built. If dragging returns, sharing it is new work.
- **Filters that do not exist yet join later.** The full graph's node-type filter (the issue's #246) does not exist; when it is added, it is shared by the rule of FR-030 without changes to the room.
- **Graphviz is deterministic as it stands.** It runs as WebAssembly with its own maths and seeded randomness; the cross-engine tool (FR-006) proves this rather than changing it.
- **The mockup's ERD values are proportions.** Where Graphviz's units differ from the mockup's SVG units, the plan keeps the proportions of FR-110 to FR-115.
- **The mockup has no screens yet for the additions of FR-025 to FR-028, FR-044, FR-045, FR-056, FR-057 and FR-060 to FR-065** (copying the current page, Hide pointers, notices, reconnecting, renaming, a full room, leaving for another service, the follower counter). Their look follows FR-024 until the mockup shows them.
- **The project link points at the package folder** in `github.com/bystrovmaxim/aoa`; the stale URLs in `aoa-maxitor`'s `pyproject.toml` are not this feature's concern.
- **The footer carries no copyright.** It shows the name and the version only; the copyright stays in `NOTICE` and the licence files.
- **Dependencies**: #245 (merged — remembered arrangement; its worker exists but is not used: G6 lays the graph out on a first open), #239 (merged — entity kinds), #268 (merged — graph memory). A WebSocket implementation for the server (`websockets`, BSD-3-Clause) is added to `aoa-maxitor`.
- **Older code is not fixed here.** The hand-written `/api/load`, `/api/sidebar` and `/api/health` and `GraphSourceMiddleware` break the rules that an endpoint works only through an action and a store or a service only through a resource; fixing them is #278, except `httpx` inside `LoadAOAServiceAction`, which this feature replaces with a gateway resource (#278's phase 3) because the fresh-graph checks need its content hash and validators. The new code of this feature keeps both rules: every room operation and every source check runs as an action, and the room registry, the graph store and the sources are reached through resources.
- **The tail of the change** is the check run, the documentation with its Russian draft, and the changelog, in that order (constitution, principle VI).
