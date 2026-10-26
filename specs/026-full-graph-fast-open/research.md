# Research: The Full Graph Opens Fast and Never Freezes the Tab

Every finding below was checked on 2026-10-26 against the locked versions in `packages/aoa-maxitor/client/package-lock.json` and `uv.lock`, not taken from the issue.

## R1 — Compression and cache headers on the server

**Decision**: Install Starlette's `GZipMiddleware(minimum_size=500, compresslevel=6)` as the outermost middleware in `create_app`, and replace the `StaticFiles` mount with a small subclass that sets `Cache-Control` in `file_response`: `public, max-age=31536000, immutable` for paths under `assets/`, `no-cache` for `index.html`, whether it is asked for by name or served as the index of `/`.

**Rationale**:
- `GZipMiddleware` (Starlette 1.10) wraps every answer of the app, the mounted static files and `/api/v1` included; it skips answers under `minimum_size`, answers that already carry `Content-Encoding`, partial answers and `text/event-stream`; it adds `Vary: Accept-Encoding`; bodies over 128 KiB are compressed in a thread.
- Outermost means refusals from `GraphSourceMiddleware` and the CORS headers pass through it unchanged apart from the encoding (FR-007).
- Level 6 instead of the default 9: the bundle (1.3 MB) and G6 (1.4 MB) are compressed per request; 9 costs noticeably more CPU for a few per cent of bytes. The tool measures the server's time to first byte, so the choice is visible.
- `StaticFiles.file_response(full_path, stat_result, scope, status_code)` is the one place every static answer goes through, including the `html=True` fallback to `index.html`; overriding it is smaller than a path-matching middleware.
- `index.html` keeps the `etag` that `FileResponse` already sets, so `no-cache` costs one conditional request (a 304) on a repeat open, not a download.

**Not done here — a validator on graph reads.** An `ETag` computed from the body of `GET /api/v1/full-graph` would turn the ~16 KB of a repeat open into a 304. It is left out: the issue's phase 2 covers compression and the static files' lifetime, the 50 KB target is met without it, and the same source URL can serve a different graph after the store rebuilds it, so the tag would have to come from the body on every read. The tests do not assert its absence, so it can be added later without rewriting them.

**Alternatives considered**: precompressed `.gz` files produced by the Vite build (no CPU per request, but `StaticFiles` does not serve them and a second serving path is more code than the CPU it saves at this traffic); brotli (smaller, but a new dependency, and the spec fixes gzip); setting headers in the stand's nginx (not in this repository, and the issue wants Maxitor to be right on its own).

## R2 — Why G6's `enableWorker` cannot move this layout

**Decision**: Do not use `enableWorker`. Run the layout in a module worker of our own (`new Worker(new URL("./forceLayout.worker.ts", import.meta.url), { type: "module" })`, which Vite bundles), and give G6 the finished positions with no `layout` option. If the worker cannot run, the viewer falls back to today's path — G6's own `layout` option with the same settings — rather than to `forceLayout.ts` on the main thread: the viewer sits in the chunk every view loads (no `lazy` import anywhere in the client), and importing `@antv/layout` there would add `D3ForceLayout` to every view, 47 422 bytes minified and 16 378 gzipped (esbuild, measured 2026-10-26), while that code already ships inside the G6 chunk the full graph loads. Today the layout code is only in the G6 chunk (`forceInABox` and the worker's fallback message appear there and not in the app chunk).

**Rationale** — three independent reasons, each enough:
1. **G6 runs the steps itself.** For a layout that has `tick` and `stop` (`d3-force` has both), `LayoutController.graphLayout` in `@antv/g6/lib/runtime/layout.js` does `layout.execute(data); layout.stop(); return layout.tick(iterations);` — it does not await `execute`. With `enableWorker`, `execute` goes to the worker asynchronously, no simulation exists on the main thread, `tick` does nothing, and G6 draws positions that were never computed. Without it, the 220 steps run synchronously inside G6's render.
2. **G6 adds a function to the options.** `initGraphLayout` passes `nodeSize` as a closure over G6's element controller; a worker cannot receive a function, so the message fails and `@antv/layout` falls back (the logged `Layout in worker failed…`).
3. **The worker script is not found in a Vite build.** `Supervisor.resolveWorkerPath` looks for a `<script>` whose `src` contains `index.js` and loads `worker.js` beside it. Vite emits `index-<hash>.js`, so the path falls back to `./worker.js`, which does not exist.

**Alternatives considered**: patching G6's layout controller (fragile across upgrades); `@antv/layout`'s own `Supervisor` with a corrected path (still blocked by reason 1); computing the layout on the server (out of scope: no `d3-force` in Python, the picture would change).

## R3 — The settings that are in effect today

**Decision**: The worker uses distance **72** and strength **0.82** for every edge, and otherwise the options of today's `FullGraphViewer.tsx` unchanged (`manyBody { strength: -360, distanceMax: 1200 }`, `collide { radius: node_visual_px * 0.5 + 7, strength: 0.95, iterations: 4 }`, `center { strength: 0.012 }`, `alphaDecay 0.012`, `alphaMin 0.0015`, `velocityDecay 0.42`, 220 steps), plus what G6 adds: `center {x: width/2, y: height/2, z: 0}`, `width`, `height`. They live in one exported object, `layoutSettings.ts`, which the fingerprint also reads (R6).

**Rationale**: d3's `forceLink.initialize` replaces `link.source` and `link.target` with node objects **before** it calls the distance and strength accessors. Today's accessors do `nodeTypeMap[String(edge.source)]`, which looks up `"[object Object]"`, finds nothing, makes both types `""`, and returns the "same type" values 72 and 0.82 for every edge. A probe running `D3ForceLayout` from the locked `@antv/layout` with a recording accessor received `object:[object Object]`. Copying the visible rule into per-edge values, as the issue's phase 4 suggests, would therefore change the picture.

**Alternatives considered**: making the rule work (a visual change — out of scope, a follow-up issue); keeping functions inside the worker (possible there, but they would encode a rule that does not apply; constants say what happens).

## R4 — Proving "the same picture"

**Decision**: The tool saves a PNG of the graph canvas at a fixed 1600×900 viewport from a **settled frame**: after the first graph pixel, with the pointer outside the canvas, it waits for two animation frames inside the page (so a busy main thread cannot hand back a stale frame), takes a screenshot of the canvas element, and repeats every 200 ms; the frame is settled when five consecutive screenshots are identical, that is, nothing changed for at least 800 ms; the run fails if that has not happened within 10 s. Two identical screenshots 100 ms apart are not enough: glyph images decode asynchronously and the hulls are added a frame after the graph (Phase 6), and a busy main thread produces no new frames, so the comparison could freeze an early frame. Phase 1 records `data/canvas-main.png` on `main` and checks that a second run on `main` is pixel-identical. Every later phase compares against it. A vitest test additionally runs today's G6 configuration and the new `forceLayout` on the reference graph and asserts equal positions to 1e-9. The test is not tautological only if its two sides are built differently: the reference copies today's viewer `layout` object **literally** (the accessor functions included), drops `type`, `animation` and `iterations` as G6 does, and lets the library merge it — `new D3ForceLayout(rest)` then `execute(data, {nodeSize, width, height, center: {x, y, z: 0}})`, which runs the layout's own `deepMix`; `forceLayout` instead passes one explicit nested object built from `LAYOUT_SETTINGS` (`center: {x, y, z: 0, strength: 0.012}`, constant distance and strength). The merge matters: `D3ForceLayout` takes the centre's `x` and `y` from `width` and `height` anyway (`getCenterOptions`), but a shallow merge that drops `center.strength` leaves d3's default strength of 1, and the picture moves. Measured on 2026-10-26 on the production 440-node payload at 1300×800, 220 ticks: G6's exact merge (`deepMix(layout.options, config, rest)` from `@antv/util`) and the library's own merge give identical positions (largest difference 0); the explicit object with 72 / 0.82 gives identical positions too (0); a shallow spread moves nodes by up to 1 387 px. G6's argument order (config before the viewer's options) does not matter here because the two objects share no leaf keys. So neither side needs `@antv/util`. The canvas comparison in a real browser remains the stronger proof, because it runs G6 itself.

**Rationale**: `d3-force` 3 seeds its own linear congruential generator (`simulation.js`, `random = lcg()`), so for the same node order, options and canvas size the result is deterministic; the "slight differences between runs" in the issue come from the canvas size. Pixels catch everything a user could see, the hulls and glyphs included; the position test pins the layout alone and runs without a browser.

**Alternatives considered**: reading node positions from the page (needs a hook in production code, which this repository does not add for tests); visual inspection (not repeatable).

## R5 — Early G6 download

**Decision**: In `main.tsx`, before `createRoot`, `if (new URLSearchParams(location.search).get("view") === "full-graph") void import("@antv/g6");`.

**Rationale**: the dynamic import resolves to the same hashed chunk the viewer imports later, so the module is fetched once; the browser starts the request before React renders. A `modulepreload` link would need a Vite plugin to learn the chunk's hashed name. Other views never evaluate the branch (SC-008). The hover prefetch in the sidebar stays.

## R6 — Fingerprint and remembered arrangement

**Decision**: Fingerprint = hex SHA-256 (`crypto.subtle.digest`) of a canonical JSON of `{settings: layoutSettings, nodes: [[id, node_type]…] sorted, edges: [[source, target, edge_type]…] sorted}`. Store = IndexedDB database `maxitor-full-graph`, object store `arrangements`, key = fingerprint, value `{positions: {id: [x, y]}, lastUsed}`; after each write, entries beyond 20 are deleted oldest `lastUsed` first. Any failure — no `indexedDB`, no `crypto.subtle` (an insecure origin), a quota error, an entry missing a node — means "not remembered", and the layout runs.

**Canvas size is not in the fingerprint.** The layout's centre is half the canvas size, but d3's centre force shifts every node by the same amount on every tick and every other force depends only on distances between nodes, so another canvas size gives the same arrangement moved as a whole; the view is fitted after drawing. Remembering per window size would only multiply entries.

**Rationale**: including the settings object means any future change of the layout changes every fingerprint without a manual version number (FR-015, scenario 4 of User Story 4). Sorting makes the fingerprint independent of the server's row order. SHA-256 is built into every browser that has IndexedDB. Twenty arrangements of a 440-node graph are about 20 × 15 KB.

**Alternatives considered**: `localStorage` (synchronous, 5 MB, string-only); a hash of the raw response (changes when any label or colour changes, which does not affect positions).

## R7 — Removing node dragging

**Decision**: Drop `drag-element` from `behaviors`, set the node cursor to `default`, remove the `node:dragend` handler. `zoom-canvas` and `drag-canvas` stay.

**Rationale**: G6's `drag-canvas` is enabled by default only when `event.targetType === "canvas"` (`behaviors/drag-canvas.js`), so a drag that starts on a node does nothing: the node stays and the view stays. Hover cards and the neighbour highlight use pointer events, not drag events, and are unaffected.

## R8 — Hulls after the first frame, glyph cache, renderer

**Decision**: Build the graph without plugins, `await graph.render()`, wait one animation frame, then `graph.setPlugins(bubblePlugins)` (and draw). Cache `svgDataUriForGraphNodeGlyphOnly` results in a `Map` by node type. Compare the canvas renderer with `@antv/g-webgl` through the tool; keep WebGL only if it is faster **and** the canvas comparison of R4 still passes.

**Rationale**: each of the three is independent and cheap to try; FR-021 and FR-022 make keeping them conditional on the figures. `@antv/g-webgl` is not installed today, so the comparison adds it and removes it again if canvas wins.

## R9 — The measurement tool

**Decision**: `client/scripts/measure-full-graph.ts`, run with `node` (Node 25 strips types) after `npx playwright install chromium`. It starts nothing itself: it takes the Maxitor URL and the source URL. The quickstart serves the frozen graph with `python -m http.server` and runs `maxitor-api` with the built client. Per condition it opens a fresh context, then a second open in the same context (repeat open). It reads:

- bytes and headers from CDP `Network.responseReceived` / `Network.loadingFinished` (`encodedDataLength`);
- long tasks from a `PerformanceObserver({type: "longtask", buffered: true})` injected with `addInitScript`;
- the first graph pixel by sampling the G6 canvas once per animation frame, cheaply: `drawImage` of the canvas into a 16×16 offscreen canvas created with `willReadFrequently: true`, then `getImageData` of those 256 pixels, looking for alpha > 0 (the dot grid is CSS on the container, the canvas itself is transparent). Sampling stops at the first hit. A threshold above zero would not make this steadier: G6 paints the whole graph — 440 nodes and their edges — in one frame, so the first frame with any drawn pixel is the same frame at any threshold, while a higher threshold could only delay it. The tool can turn the sampler off (`--no-pixel-probe`); then the long-task window ends at the `load` event plus 3 s, and the sampler's cost is checked by comparing only the tasks that start before the end of the sampled run's window;
- worker CPU time by auto-attaching to worker targets (`Target.setAutoAttach`) and profiling them, and the main thread's scripting time from the page's profile;
- console messages: the run fails on `fallback to main thread` (FR-003) or on the viewer's own fallback warning;
- the canvas that carries the drawing: G6 paints several canvas layers, so the sampler checks every layer for the first pixel and the screenshots come from the layer with pixels;
- a run's bytes, read only after every request the open started has finished (half a second with nothing in flight), so a late `/api/load` answer cannot change the total;
- the picture probe, which hovers the densest opaque 5×5 patch — a node, not a hull or an edge — until `.graph-hover-label` appears, then drags 80 px, moves the pointer out of the canvas, and compares the settled canvas with the one taken before.

CPU throttling with `Emulation.setCPUThrottlingRate(4)`; Slow 4G with `Network.emulateNetworkConditions` (150 ms latency, 1.6 Mbit/s down, 750 kbit/s up).

**Rationale**: everything is read from what a browser exposes to any page, so production code gains no hooks. Playwright is a dev dependency, and the check run does not run it (it has no browser), as FR-001 requires.

## R10 — Baseline on main

**Decision**: every later figure is compared with this one. Measured on 2026-10-26 from the client at `da062321`, built into `packages/aoa-maxitor/src/aoa/maxitor/static/` and served by `maxitor-api` on `127.0.0.1:8102`, over the frozen reference graph on `127.0.0.1:8765` (the 440-node, 545-edge graph of #268). Three runs per condition; times are the median; bytes were equal across runs. Report: `data/baseline-main.json`. Canvas: `data/canvas-main.png`, 1345×900 CSS pixels.

| Condition | Open | Bytes | Longest task | First graph pixel | Main scripting |
|---|---|---|---|---|---|
| `cpu1x` | first | 3 056 128 | 596 ms | 750 ms | 691 ms |
| `cpu1x` | repeat | 311 515 | 597 ms | 727 ms | 893 ms |
| `cpu4x` | first | 3 056 128 | 2 759 ms | 3 340 ms | 1 402 ms |
| `cpu4x` | repeat | 311 515 | 2 651 ms | 3 152 ms | 1 362 ms |
| `slow4g` | first | 3 056 128 | 609 ms | 16 537 ms | 973 ms |
| `slow4g` | repeat | 311 515 | 631 ms | 2 437 ms | 916 ms |

The resources of `cpu1x/first`, largest first:

| Resource | Encoded | Decoded | `Content-Encoding` | `Cache-Control` | Status |
|---|---|---|---|---|---|
| `assets/index-CDX_0f6p.js` | 1 422 520 | 1 422 176 | — | — | 200 |
| `assets/index-Bc79Uius.js` | 1 321 082 | 1 320 738 | — | — | 200 |
| `GET /api/v1/full-graph` | 237 244 | 237 101 | — | — | 200 |
| `GET /api/sidebar` | 74 271 | 74 129 | — | — | 200 |
| `GET /` (`index.html`) | 650 | 392 | — | — | 200 |
| `assets/index-wUWjggHM.css` | 361 | 29 | — | — | 200 |

The 38 `data:image/svg+xml` glyph URLs carry no transferred bytes and are left out of the table.

**What the baseline says**
- Every gap the spec targets is open: SC-001 3 056 128 against 1 300 000; SC-002 311 515 against 50 000; SC-003 16 537 ms against 6 000; SC-004 596 ms against 150; SC-005 2 759 ms against 600; SC-006 727 ms against 500.
- No answer carries `Content-Encoding` or `Cache-Control`; the page has its `etag` but no lifetime, and the repeat open still transfers the graph (237 244) and the sidebar (74 271).
- The JavaScript is almost the whole first open: 2 743 602 of 3 056 128 bytes, 89.8 %.
- The picture is stable across invocations: a second full run gave identical bytes in every condition and passed `--compare-canvas data/canvas-main.png`.
- `workers[]` is empty and no console failure appears, as today.
- The sampler costs nothing measurable: the same long task is 593 ms with it and 605 ms without, measured on the tasks that start inside the shorter window (T005).
- The ERD baseline, the reference for SC-008, is `data/baseline-main-erd.json`: 1 556 878 bytes on the first open, 234 785 on the repeat, the app chunk `index-Bc79Uius.js` at 1 320 738 decoded bytes, and no G6 chunk.

**One race, found and fixed in the tool.** A first three-run attempt under slow4g gave 312 084, 312 084, 311 515: the 569-byte `/api/load` answer sometimes landed after the measurement window. The tool now waits until every request the open started has finished before it reads the bytes, and three runs give 311 515 every time.

## R11 — After compression

**Decision**: gzip and the cache lifetimes are in (commit 3). Measured on 2026-10-26 with the same tool, the same build, the same frozen graph and the same conditions as R10.

| Condition | Open | Bytes | Longest task | First graph pixel | Main scripting |
|---|---|---|---|---|---|
| `cpu1x` | first | 1 228 314 | 596 ms | 779 ms | 855 ms |
| `cpu1x` | repeat | 22 120 | 584 ms | 720 ms | 889 ms |
| `cpu4x` | first | 1 228 314 | 2 409 ms | 2 934 ms | 1 098 ms |
| `cpu4x` | repeat | 22 120 | 2 466 ms | 2 926 ms | 1 137 ms |
| `slow4g` | first | 1 228 314 | 606 ms | 7 387 ms | 944 ms |
| `slow4g` | repeat | 22 120 | 611 ms | 1 132 ms | 910 ms |

The resources of `cpu1x/first` (transferred bytes include the response headers):

| Resource | Transferred | Decoded | `Content-Encoding` | `Cache-Control` |
|---|---|---|---|---|
| `assets/index-Bc79Uius.js` | 793 547 | 1 320 738 | gzip | `public, max-age=31536000, immutable` |
| `assets/index-CDX_0f6p.js` | 411 723 | 1 422 176 | gzip | `public, max-age=31536000, immutable` |
| `GET /api/v1/full-graph` | 16 131 | 237 101 | gzip | — |
| `GET /api/sidebar` | 5 825 | 74 129 | gzip | — |
| `GET /` (`index.html`) | 675 | 392 | — | `no-cache` |
| `assets/index-wUWjggHM.css` | 413 | 29 | — | `public, max-age=31536000, immutable` |

**What R11 says**
- **SC-001 is met**: 1 228 314 against 1 300 000, 71 686 bytes to spare (5.5 %). The JavaScript is still almost everything: 1 205 270 of 1 228 314 bytes, 98.1 %.
- **SC-002 is met**: 22 120 against 50 000. The repeat open downloads the graph (16 131) and the sidebar (5 825); the assets come from the cache and the page is a 304 answered with 164 bytes of headers.
- **SC-003 is still missed**: 7 387 ms against 6 000 (it was 16 537). The download is 1.23 MB, about 6.1 s at 1.6 Mbit/s, so the network is the floor now; phase 4's early G6 download is the next lever.
- **The freeze has not moved**, as expected: 596 ms at 1× and 2 409 ms at 4× — phases 4 and 5 are the ones that move it.
- **gzip at level 6 costs almost nothing**: the two big scripts answer their first byte in 2.5–3 ms and complete in about 30 ms (792 935 and 411 102 gzip bytes on the wire).
- **A stale file is revalidated, not re-downloaded.** With `max-age=0` in place of `immutable` (T014b) the repeat open still transfers 22 867 bytes, because each asset comes back as a 304; only `no-store` would force the download the task expected.

## R12 — Early G6

**Decision**: `main.tsx` starts `import("@antv/g6")` when the deep link names the full graph, before React mounts (FR-009); the sidebar's hover prefetch stays. Measured on 2026-10-26 with the tool, on the same build, graph and conditions as R11.

| Condition | First graph pixel, R11 | With the change | Engine requested at | Entry requested at |
|---|---|---|---|---|
| `cpu1x` | 779 ms | 795 ms | 70 ms | 10 ms |
| `cpu4x` | 2 934 ms | 3 023 ms | 114 ms | 12 ms |
| `slow4g` | 7 387 ms | 7 372 ms | 4 328 ms | 161 ms |

Under the inverted condition of T018 the engine is requested at 81 ms and 4 364 ms, because the viewer then starts the import when it mounts.

**What R12 says**
- The change does what FR-009 asks: the engine's request begins about 40 ms before the viewer would start it (70 against ~110 ms on the fast machine, 4 328 against 4 364 ms on Slow 4G).
- It moves no figure: the first pixel is 795 against 779 ms, 3 023 against 2 934 ms and 7 372 against 7 387 ms — inside run-to-run noise. The reason is arithmetic: on Slow 4G the entry chunk alone takes 4.3 s, the browser cannot request the engine before that chunk has executed, and 1.23 MB at 1.6 Mbit/s is 6.1 s of transfer whatever starts first. Starting the engine earlier cannot lower the network floor.
- SC-008 still holds: the ERD view requests no engine chunk and transfers 813 212 bytes (the pre-change baseline is 1 556 878), and its app chunk is 1 320 811 decoded bytes — 73 bytes above the baseline's 1 320 738, inside the 5 000-byte guard.
- The break proves the comparison sees the difference: with `!==` the ERD view downloads the engine (1 224 934 bytes in total, the engine requested at 55 ms).

**The decision this leaves to the maintainer**: the phase delivers FR-009 and improves nothing measurable — at most about 40 ms on a 7.4 s figure. FR-025 says a phase whose change improves nothing is not kept. Keep the four lines for FR-009's sake, or drop them and record that FR-009 is not worth its bytes; either way SC-003 stays missed until the bytes shrink.

## R13 — Worker layout: built, measured, not kept

**Decision**: the layout was built as a worker (`layoutSettings.ts`, `forceLayout.ts`, `forceLayout.worker.ts`, committed as `4394a02d`) and **is not wired into the viewer**: on this graph and this machine it costs more than it saves. What did pay is the G6 adapter below, and the remembered arrangement uses it (R14).

**What was proven**
- `computeForceLayout` equals today's G6 configuration for all 440 nodes to 1e-9 (vitest), and in the page the worker's positions equal G6's: the largest difference over 440 nodes is 0.0 px.
- A registered G6 layout (`precomputedLayout.ts`) makes G6 draw given positions through its own pre-layout, so the camera and the element styles match today's picture: `--compare-canvas data/canvas-main.png` passes. The naive path did not — with positions in the node data, G6 wrote canvas coordinates into the element style and fitted 26 % instead of 27 %.
- The worker chunk is 49 106 bytes; with the worker wired the app chunk stayed at 1 322 621 and carried no `@antv/layout`.

**Why it is not kept**

| | G6 lays out (fallback) | Worker |
|---|---|---|
| longest task, 1× | 621 ms | 616 ms |
| longest task, 4× | 2 545 ms | 2 561 ms |
| first pixel, 1× | 814 ms | 1 186 ms |
| first pixel, 4× | 3 171 ms | 3 668 ms |

The layout is a small part of the render task here: taking it off the main thread changes the longest task by nothing measurable, while the worker's start-up, its chunk and the round trip add 350–450 ms to the first pixel. FR-025 says a phase whose change improves nothing is not kept, so the viewer does not use the worker; the module and its test stay as the record, unused.

**What stayed**: `precomputedLayout.ts`, the adapter that draws given positions through G6, because the remembered arrangement needs exactly it.

## R14 — Remembered arrangement

**Decision**: after G6 lays the graph out, the viewer computes the graph's fingerprint and stores the positions; on the next open of the same graph it reads them and gives them to G6 through the precomputed layout, so no layout runs. Node dragging is gone (FR-024).

**Measured** (cpu1x, one run, the same graph and build as R11):

| | First open | Repeat open |
|---|---|---|
| first pixel | 784 ms | 753 ms |
| longest task | 599 ms | 600 ms |
| layout run | yes (G6) | no (replayed) |
| canvas against `canvas-main.png` | identical | — |

The first open writes one entry of 440 positions (checked in the page), and the repeat open draws without a layout. The saving is about 30 ms because here the drawing, not the layout, is the 600 ms task; on a slower machine or a larger graph the layout's share grows.

**What does not hold yet**
- SC-006 (a repeat open under 500 ms) is missed: 753 ms.
- `--no-storage` no longer checks what the contract describes: it expects a layout worker on the repeat open, and there is no worker any more. The option and the contract need rewording.
- The interaction probe still reports a moved picture — not because the node moves (the positions do not change) but because the hover card stays after a drag; a click on empty canvas clears it.
