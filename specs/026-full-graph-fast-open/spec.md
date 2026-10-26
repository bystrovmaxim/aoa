# Feature Specification: The Full Graph Opens Fast and Never Freezes the Tab

**Feature Branch**: `feature/issue-245-compressed-graph-transfer`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "https://github.com/bystrovmaxim/aoa/issues/245 — Maxitor: send the full graph compressed and draw it without freezing the tab. Use the issue body (problem, measurements, words, what must not change, phases 1–7, acceptance criteria, out of scope) as the feature description."

## Context: what is true today, checked on 2026-10-26

- **The graph has grown since the issue was measured.** The issue's figures were taken on 351 nodes and 426 edges. On 2026-10-26 the same production page answers `GET /api/v1/full-graph` with **440 nodes, 545 edges, 19 node types and 4 domains**, in 237 101 bytes uncompressed (15 926 bytes with gzip level 6). The issue's timings (536 ms longest task, 16.2 s on Slow 4G) were taken on the smaller graph and are not re-measured here: re-measuring is phase 1's job.
- **Nothing is compressed and nothing carries a cache lifetime.** Re-checked on production: `index.html`, the app bundle (`/assets/index-*.js`, 1 320 738 bytes) and the full-graph answer all come back without `Content-Encoding` and without `Cache-Control`, even when the request asks for gzip. `index.html` does carry an `etag` and a `last-modified`.
- **A reverse proxy sits in front of Maxitor in production.** The answers carry `Server: nginx/1.31.3`. That proxy is the host's own configuration (`/root/nginx/default.conf`, extended by `scripts/deploy_demonstrator_stand.sh`), not a file in this repository. It forwards the browser's request headers and passes the answer through, so compression and cache headers set by Maxitor reach the browser — this is checked on the stand after deploy, not assumed.
- **Maxitor serves its own static files.** `create_app` mounts `StaticFiles(directory=_STATIC_DIR, html=True)` at `/` (`packages/aoa-maxitor/src/aoa/maxitor/api/app.py`), after the graph routes. No compression middleware is installed today.
- **The layout runs on the main thread inside the first draw.** `FullGraphViewer.tsx` builds the graph with `layout: { type: "d3-force", iterations: 220, alphaDecay: 0.012, … }`, and `link.distance` and `link.strength` are written as functions of the two ends' node types (the next point shows that they never see those types). The viewer already copies `style.x` / `style.y` into a node's position when the payload carries them.
- **The library's worker option cannot move this layout off the main thread.** The locked versions are `@antv/g6` 5.1.1 and `@antv/layout` 2.0.0. `@antv/layout` catches a worker failure and logs `Layout in worker failed, fallback to main thread layout.`, as the issue says. But for a layout that runs in steps, as `d3-force` does, G6 does not wait for the worker: it calls the layout, stops it and runs the 220 steps itself, synchronously (`graphLayout` in `@antv/g6/lib/runtime/layout.js`). G6 also adds a `nodeSize` function of its own, which a worker cannot receive, and `@antv/layout` looks for its worker script next to a script named `index.js`, which a Vite build does not produce. Research R2 records what this means for phase 4.
- **Every edge gets the same distance and strength today.** The `link.distance` and `link.strength` functions read `edge.source` and `edge.target` as node ids, but d3 calls them after it has replaced both with node objects. `String(edge.source)` is then `[object Object]`, the node-type lookup finds nothing for either end, both types are the empty string, and every edge gets distance 72 and strength 0.82. The per-type rule (200 / 0.11 between different types, the entity-to-field link) has never applied. Confirmed on 2026-10-26 by running `@antv/layout`'s `D3ForceLayout` with a probing function: it receives `object:[object Object]`.
- **The domain hulls are built in the browser.** `fullGraph()` in `client/src/api/fullGraph.ts` computes one bubble-set plugin per domain from the payload, and `buildGraph` passes them to the graph's constructor, so they are drawn in the same task as the nodes.
- **Nodes can be dragged today.** The graph is built with the `drag-element` behaviour beside `zoom-canvas` and `drag-canvas`, every node shows a `grab` cursor, and the hover labels are re-placed on `node:dragend`.
- **The node glyph is rebuilt for every node.** The node style function calls `svgDataUriForGraphNodeGlyphOnly(nodeType)` for each node; the helper builds the SVG string from scratch every time and keeps nothing.
- **G6 is prefetched only on hover.** `prefetchInterchangeG6()` is called from the sidebar when the pointer is over the full-graph entry. A page opened straight on `?view=full-graph` starts loading G6 only when the viewer mounts.
- **The client's unit tests are in the check run; a browser is not.** `scripts/run_checks_with_log.sh` runs `npm ci && npm run build` and then `npm test` for the client (a step added with #214), so every new vitest test is a gate and must be fast and deterministic under jsdom. No browser is available to the run, so a check that needs a real browser (a worker, a canvas) can live only in a tool run by hand.
- **The issue's out-of-scope note about #214 is settled.** #214 is closed: Maxitor already keeps one built graph per source (`GraphStore`) and every read names its source with `?source=`. Nothing in this work touches that store.
- **The node-type filter (#246) is still open.** The rule "filtering changes visibility, never positions" is a constraint this work must not break, not something it builds.
- **A frozen copy of the reference graph exists.** `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz` is the reference service's `graph-json` saved on 2026-10-26 (SHA-256 of the uncompressed bytes `a9d73e90b8c486fc18a3304b3eacf024a229a9642b71709af8bb919ebf0f84cf`), the same 440 nodes the production page draws today.

## Clarifications

### Session 2026-10-26

- Q: What happens if, after every phase, a target is still missed — for example the 150 ms freeze on the 440-node graph, when creating the shapes alone took 164 ms on 351 nodes? → A: Everything that improves the page ships; the pull request states, for each missed target, how far it is and what stood in the way (FR-025). The same rule as #268.
- Q: What are "before" and "after" measured on? → A: On the frozen 440-node copy of the reference graph, served to a local production build of Maxitor. The headers are also checked through the production proxy on the stand after deploy, but that check is not the acceptance (FR-004, FR-026).
- Q: Are positions the user drags a node to remembered? → A: Superseded by the maintainer the same day: nodes can no longer be dragged at all (FR-024). The picture is always the layout's arrangement, so there is no dragged position to remember (FR-014).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Knowing what opening the full graph costs (Priority: P1)

The maintainer wants every speed-up in this work proven by numbers taken the same way before and after. They run one tool and get, for the full-graph page: the bytes of every resource, whether each was compressed and how long the browser may keep it, the longest stretch during which the tab was frozen, and the time until the graph's first pixel — on a fast machine, on a slow one, and on a slow mobile network.

**Why this priority**: Every other story claims a speed-up; without one way of measuring, none of the claims can be checked, and the acceptance table of the issue cannot be filled in.

**Independent Test**: Run the tool against the page on `main`; it prints the figures for all three conditions, and a second run gives byte figures that are identical and time figures close enough to tell a real change from noise.

**Acceptance Scenarios**:

1. **Given** the full-graph page and a graph source, **When** the maintainer runs the tool, **Then** it reports per resource the bytes transferred, the compression and the cache lifetime, plus the longest frozen stretch and the time to the first graph pixel, under each of the three conditions.
2. **Given** the tool has run on `main`, **When** the maintainer looks for the baseline, **Then** the figures are recorded in this feature's folder and in the pull request.
3. **Given** the page is opened a second time in the same browser, **When** the tool measures that open, **Then** it reports the bytes and time of the repeat open separately from the first.

---

### User Story 2 - The page downloads several times less (Priority: P1)

A user opening the full graph, especially on a slow network, waits several times less for it, and on the next visit downloads almost nothing again — while a new release of Maxitor still reaches them on their next open.

**Why this priority**: The download is the largest part of the wait on a slow network (16 s, of which the code alone takes most), and compression is the cheapest change with the largest effect.

**Independent Test**: Open the page with an empty cache and with a warm one, and read the bytes; deploy a new build and open again, and see the new build.

**Acceptance Scenarios**:

1. **Given** a browser that accepts compressed answers, **When** it opens the full-graph page, **Then** the code, the styles and the graph's data arrive compressed, and the total is at most 1 300 000 bytes. The page itself (`index.html`, under 400 bytes) is below the threshold of scenario 4 and arrives as it is.
2. **Given** the user has opened the page before, **When** they open it again, **Then** the code and styles come from the browser's cache and the open downloads at most 50 000 bytes.
3. **Given** a new release with new code files, **When** the user opens the page after it, **Then** they get the new release, not the cached old one.
4. **Given** a very small answer, **When** it is sent, **Then** it is sent uncompressed (compression would not make it smaller).
5. **Given** a graph read that is refused (missing source, a source that cannot be built, a busy store), **When** the refusal is sent, **Then** its status, its message and its headers (including `Retry-After` and the cross-origin headers) are what they are today.

---

### User Story 3 - The tab never freezes while the graph is drawn (Priority: P1)

While the full graph is being laid out and drawn, the user can still scroll, click the sidebar and switch views. The heavy work happens off the part of the browser that reacts to the user.

**Why this priority**: A half-second freeze on a fast machine is two seconds on a slow one. It is the most visible defect of the page, and it gets worse as services grow.

**Independent Test**: Open the page under the tool and read the longest frozen stretch; check that the layout ran in the background and not as a silent fallback.

**Acceptance Scenarios**:

1. **Given** the full-graph page is opened, **When** the layout runs, **Then** it runs in the background, and the tool fails the run if the browser reports that it fell back to the main thread.
2. **Given** the layout runs in the background, **When** the picture appears, **Then** it is the same picture as today: for the same graph and the same canvas size, every node stands where today's page puts it.
3. **Given** the user leaves the page before the layout finishes, **When** they come back or open another view, **Then** nothing from the abandoned layout is drawn or stored, and no background work is left running.
4. **Given** a browser where the background layout cannot start, **When** the page opens, **Then** the graph is still drawn, as today, on the main thread.

---

### User Story 4 - A graph seen once opens at once (Priority: P2)

A user who has already opened a service's full graph opens it again and sees it almost immediately, in the same arrangement, because the arrangement was remembered. When the service changes, the graph is arranged afresh.

**Why this priority**: The layout is half of the drawing time, and most opens are repeat opens of a graph that has not changed.

**Independent Test**: Open the same graph twice and compare the time to the first pixel; change one edge of the graph and see that a new arrangement is computed.

**Acceptance Scenarios**:

1. **Given** a graph laid out once in this browser, **When** it is opened again unchanged, **Then** no layout runs, the nodes stand where they stood at the end of the first layout, and the first pixel appears in under 0.5 s on a fast machine.
2. **Given** a graph whose nodes or edges have changed, **When** it is opened, **Then** a fresh layout runs and its result replaces nothing of the old graph's.
3. **Given** a browser where saving is impossible (a private window, a full quota, saving disabled), **When** the page opens, **Then** it works as it does without this story: the layout runs every time and no error is shown.
4. **Given** a later Maxitor release changes the layout settings, **When** a graph remembered under the old settings is opened, **Then** it is laid out again under the new settings.

---

### User Story 5 - Less work before the first picture (Priority: P3)

The first picture of the graph appears before the work that is not needed for it: the domain hulls are added just after, the 19 node glyphs are prepared once instead of once per node, and the fastest way of drawing that gives the same picture is used.

**Why this priority**: It trims what remains after Stories 2–4. Each part is kept only if the measurement shows it helps.

**Independent Test**: Measure with the tool with and without each part, and keep the parts that shorten the longest frozen stretch or the time to the first pixel.

**Acceptance Scenarios**:

1. **Given** the page is opened, **When** the first frame is painted, **Then** the domain hulls appear right after it, the same hulls as today, and they still do not block hovering over nodes.
2. **Given** a part of this story that the measurement shows makes no difference, **When** the work ends, **Then** that part is not kept, and the pull request says so with the figures.
3. **Given** two ways of drawing are compared, **When** one is kept, **Then** it is the faster one of those that give the same picture, and the pull request carries both sets of figures.

---

### User Story 6 - Other pages stay as light as they are (Priority: P2)

A user who opens Maxitor on any other view (an ERD, a lifecycle, a use-case diagram) does not download the graph engine of the full-graph page, while a link straight to the full graph starts downloading it as early as the page allows.

**Why this priority**: Starting the graph engine early helps the full graph only if it costs the other pages nothing.

**Independent Test**: Open the page once with `view=full-graph` and once with another view, and list what was downloaded.

**Acceptance Scenarios**:

1. **Given** a link straight to `view=full-graph`, **When** the page opens, **Then** the graph engine starts downloading before the application has drawn its first screen.
2. **Given** a link to any other view, **When** the page opens, **Then** the graph engine is not downloaded.

### Edge Cases

- **The same graph opened from two tabs at once.** Both lay it out; whichever finishes last is remembered. Neither tab shows an error.
- **Two sources that serve the same graph.** They have the same fingerprint and share one remembered arrangement, which is correct: the arrangement depends only on the graph.
- **A user who tries to drag a node.** The node stays where it is; the view still pans when dragged on empty space and still zooms, and hovering a node still shows its card and its neighbours.
- **Many different graphs over time.** The remembered arrangements are bounded in number; the oldest are dropped first, and dropping one only means it is laid out again.
- **A remembered arrangement that is unreadable or incomplete** (a node missing a position, damaged data). It is ignored and the graph is laid out afresh.
- **A graph with no nodes.** The page opens empty as today; nothing is remembered.
- **A browser where the background layout cannot start.** The graph is drawn by today's path (G6's own layout) and nothing is remembered from it, so the next open lays it out again the same way; the picture and the first-open speed are today's (FR-012, FR-014).
- **The same graph opened in a window of another size.** The remembered arrangement is used: a different canvas size would only have moved the whole layout, so the arrangement is the same; the view is fitted to the graph, so the scale follows the window, as it does today.
- **A tab left open across a deploy.** The page it already has keeps working with the code it loaded; on the next open it loads the new release (User Story 2, scenario 3).
- **A proxy in front of Maxitor that compresses or strips headers itself.** The stand's figures are taken through the real proxy after deploy; a proxy that undoes the change is reported, not worked around in this repository.
- **The layout result differs a little between runs** (as it does today). Remembering the arrangement makes repeat opens of one graph identical; first opens may still differ slightly.

## Requirements *(mandatory)*

### Functional Requirements

**Measurement (phase 1)**

- **FR-001**: The repository MUST provide a measurement tool, kept with the client as a development tool outside the check run, that opens the full-graph page in a real browser and reports: bytes transferred per resource, compression and cache lifetime per resource, the longest frozen stretch (any main-thread task over 50 ms counts), and the time to the first graph pixel. "While the page opens" — the window the frozen stretches are taken from — runs from the start of navigation until 3 seconds after the first graph pixel, so the work drawn just after the first frame (FR-020) is counted.
- **FR-002**: The tool MUST measure under three conditions: a fast machine, a machine four times slower, and a slow mobile network (1.6 Mbit/s, 150 ms round trip); and it MUST measure a first open and a repeat open separately.
- **FR-003**: The tool MUST fail the run when the browser reports that the layout fell back from the background to the main thread, unless the run disabled background work on purpose (FR-012).
- **FR-003a**: The tool MUST be able to point at a node, confirm that its hover card appears, drag it, and confirm that the picture did not change (FR-023, FR-024).
- **FR-004**: The baseline MUST be recorded on `main` before any other phase changes the code, on the frozen reference graph served to a local production build of Maxitor, and kept in this feature's folder. Every later figure in this work is taken the same way.

**Compression and cache (phase 2)**

- **FR-005**: Every answer above a small size threshold — the page, the code, the styles and the JSON of the graph reads — MUST be sent compressed when the browser accepts it.
- **FR-006**: Code and style files whose names carry a content hash MUST be marked as cacheable for a year and never changing; the page itself (`index.html`) MUST be marked as revalidated on every open, so a new release is picked up on the next open.
- **FR-007**: Refusals of graph reads MUST keep their status, message and headers, including `Retry-After` and the cross-origin headers.
- **FR-008**: Tests MUST check the headers of one hashed file, of `index.html` and of one graph read, compressed and uncompressed.

**Early download of the graph engine (phase 3)**

- **FR-009**: When the page is opened on `view=full-graph`, the graph engine MUST start downloading before the application mounts. On any other view it MUST NOT be downloaded until the user moves to the full graph (the hover prefetch of today stays), and the code every view loads MUST NOT grow by the layout code this work adds.

**Background layout (phase 4)**

- **FR-010**: The layout MUST run in the background and MUST produce the same picture as today: for the same graph and the same canvas size, the same position for every node. That means the settings that are in effect today, not the ones the code appears to ask for: distance 72 and strength 0.82 on every edge (see Context), the same other forces, the same 220 steps and the same decay settings.
- **FR-011**: The proof that the layout ran in the background MUST be a check that fails on the fallback message (FR-003), together with a profile in which the layout's work no longer appears on the main thread.
- **FR-012**: If the background cannot start, the page MUST still draw the graph, as today — by today's path, so the code every view loads gains nothing for this case. The tool MUST be able to open the page in a browser with background work disabled, to show this case.
- **FR-013**: Leaving the page before the layout ends MUST stop the background work and MUST NOT draw or remember its result.

**Remembered arrangement (phase 5)**

- **FR-014**: After a layout computed in the background worker finishes, the arrangement it produced MUST be remembered in the browser under the graph's fingerprint. A layout the fallback produced (FR-012) is not remembered: the next open tries the background again.
- **FR-015**: The fingerprint MUST change when any node id, any edge (its ends and its type), any node's type, or the layout settings change, and MUST NOT change otherwise. The canvas size is deliberately not part of it: it only moves the layout's centre, which shifts every node by the same amount, and the view is fitted to the graph after drawing.
- **FR-016**: Opening a graph whose fingerprint is remembered MUST draw it from the remembered arrangement without running the layout.
- **FR-017**: If saving or reading is impossible, or the remembered arrangement does not cover every node, the page MUST run the layout and work as without this phase, without showing an error. The tool MUST be able to open the page in a browser with storage disabled, to show this case.
- **FR-018**: The number of remembered arrangements MUST be bounded, dropping the least recently used first.
- **FR-019**: Positions MUST stay put while the user filters by node type (#246): a remembered or computed arrangement is never recomputed because nodes are hidden or shown. The filter does not exist yet, so in this work the requirement is a constraint checked by review (the arrangement is read and written only when a graph is opened); #246 proves it with its own test.

**First frame (phase 6)**

- **FR-020**: The domain hulls MUST be added after the first frame is painted, MUST be the same hulls as today, and MUST still let the pointer reach the nodes beneath them.
- **FR-021**: Each node type's glyph MAY be prepared once instead of once per node; this MUST be kept only if the measurement shows a gain.
- **FR-022**: The two ways of drawing the graph (the current one and the hardware-accelerated one) MUST be compared with the tool; the faster one of those that give the same picture MUST be kept, with both sets of figures in the pull request.

**What must not change, and the one thing that does**

- **FR-023**: The nodes, edges, colours, glyphs, hover cards and domain hulls MUST be what they are today.
- **FR-024**: Nodes MUST NOT be movable by dragging. Panning the view by dragging empty space, zooming, and the hover card with its neighbour highlight MUST work as today, and a node MUST no longer show a cursor that invites dragging. This is the one intended change in behaviour, decided by the maintainer on 2026-10-26.

**Missed targets and the stand**

- **FR-025**: If a Success Criterion is still missed after every phase, the changes that improve the page MUST still ship, and the pull request MUST state for each missed criterion the figure reached, the target and what stood in the way. A phase whose change improves nothing is not kept.
- **FR-026**: After the maintainer deploys the change to the stand, the compression and cache headers MUST be checked through the production proxy and the result recorded in the issue. A proxy that strips them is reported, not worked around in this repository.

**Tail (phase 7)**

- **FR-027**: The work MUST end with the three steps of Principle VI, in order: the check run taken to zero, the documentation of the full-graph page, one changelog article.

### Key Entities

- **Resource**: one file or answer the browser downloads to open the page: the page, the code, the styles, the graph engine, the graph's data.
- **Measurement**: one run of the tool under one condition, first or repeat open, with its bytes, its longest frozen stretch and its time to the first graph pixel.
- **Fingerprint**: a short value computed from the graph's node ids, node types and edges and from the layout settings; equal graphs under equal settings give equal fingerprints.
- **Remembered arrangement**: the position of every node of one graph, kept in the browser under the graph's fingerprint, with the time it was last used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

Measured with the tool of FR-001, on one machine and one graph, against the baseline of FR-004. A criterion still missed at the end is handled by FR-025.

- **SC-001**: A first open of the full-graph page downloads at most 1 300 000 bytes.
- **SC-002**: A repeat open downloads at most 50 000 bytes.
- **SC-003**: On a slow mobile network, the first graph pixel appears in under 6 seconds.
- **SC-004**: On a fast machine, the tab is never frozen for more than 150 ms while the page opens.
- **SC-005**: On a machine four times slower, the tab is never frozen for more than 600 ms while the page opens.
- **SC-006**: A repeat open of an unchanged graph shows its first pixel in under 0.5 s on a fast machine.
- **SC-007**: A user comparing the page before and after sees the same nodes, edges, colours, glyphs, hover cards and domain hulls; the only difference they can find is that a node no longer moves when dragged.
- **SC-008**: A deep link to any view other than the full graph downloads no more than it does today.

## Assumptions

- **The graph measured is the frozen reference copy.** Before and after are measured on `specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz`, served as the source to a local production build of Maxitor, so the comparison does not move when the live service changes. The issue's figures (351 nodes) are history; the targets of the Success Criteria are the issue's, applied to this graph (440 nodes).
- **Compression is gzip.** It needs no new dependency and every browser accepts it; brotli is not part of this work.
- **The background layout is Maxitor's own.** The graph library's worker option cannot move this layout (see Context), so the layout runs in a background worker of Maxitor's own with the same layout code and the settings in effect today, and the graph library only draws the positions it is given. When the background cannot start, the library's own path lays the graph out instead (FR-012), and that arrangement is not remembered (FR-014).
- **The remembered arrangements are kept per browser**, bounded to a small number of graphs (20 by default), and are not shared between users or machines.
- **The proxy in front of production passes the headers through.** It is checked on the stand after deploy (FR-026); the deploy itself is the maintainer's.
- **The measurement tool needs a browser engine** installed on the maintainer's machine; it is not added to the check run, which has none.

## Out of Scope

- Caching `POST /api/load`, or how built graphs are kept on the server — settled by #214, which is closed.
- Running the layout to convergence (about 540 steps instead of 220): it changes the picture.
- Making the per-type edge distances and strengths take effect (200 / 0.11 between different node types, the entity-to-field link): it changes the picture, so it needs its own decision and its own issue.
- A layout computed on the server: the server has no `d3-force`, so the picture would change.
- A server-rendered or rewritten client.
- Any visual redesign of the graph.
- The node-type filter itself (#246).
- The configuration of the production proxy, which lives on the host and not in this repository.
