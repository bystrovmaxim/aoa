# Implementation Plan: The Full Graph Opens Fast and Never Freezes the Tab

**Branch**: `feature/issue-245-compressed-graph-transfer` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/026-full-graph-fast-open/spec.md` (issue #245)

## Summary

Opening Maxitor's full graph downloads about 2.9 MB uncompressed and freezes the tab while 220 steps of `d3-force` and the drawing run on the main thread. The work goes in six steps, each a commit, each measured by one tool:

1. A measurement tool (Playwright, a dev-only script in the client) records bytes, headers, the longest main-thread task and the time to the first graph pixel, on the frozen 440-node reference graph served to a local production build, at 1× CPU, 4× CPU and Slow 4G, first and repeat open. It also saves a screenshot of the canvas, which is how "the same picture" is checked.
2. The server compresses every answer above 500 bytes with gzip and marks hashed assets `immutable` for a year and `index.html` `no-cache`.
3. A deep link to `view=full-graph` starts importing G6 from the entry module, before React mounts.
4. The layout moves to a worker of our own. Research R2 shows that G6's `enableWorker` cannot do it for `d3-force`: G6 runs the 220 steps itself, synchronously, whatever the option says. The worker runs the same `D3ForceLayout` of `@antv/layout` with the settings in effect today — and R3 shows those are distance 72 and strength 0.82 on **every** edge, because the per-type functions never see node ids. G6 then only draws the positions it is given.
5. The positions are remembered in IndexedDB under a SHA-256 fingerprint of the graph and the layout settings, and a repeat open draws them without any layout; a layout the fallback produced is not remembered (FR-014). Node dragging is removed, as the maintainer decided.
6. The domain hulls are added after the first frame, the 19 glyphs are cached, and the WebGL renderer is compared with the canvas one; each part stays only if the tool shows a gain.

The tail is the three steps of Principle VI.

## Technical Context

**Language/Version**: TypeScript 5.7 (client, React 19, Vite 6, Node 25 runs `.ts` scripts directly); Python 3.12 (server)

**Primary Dependencies**: `@antv/g6` 5.1.1 (locked); `@antv/layout` 2.0.0, today reached only through G6, becomes a **direct runtime dependency** pinned to exactly that version, because the worker imports `D3ForceLayout` itself; Starlette 1.10 / FastAPI 0.162 (`GZipMiddleware`, `StaticFiles`); new dev-only dependency `playwright` for the measurement tool; no `@antv/util` — the options are built as one explicit nested object (research R4); `@antv/g-webgl` only for the phase 6 comparison, kept only if WebGL wins

**Storage**: the browser's IndexedDB for remembered arrangements (bounded to 20, least recently used dropped first); nothing on the server

**Testing**: pytest for the headers (`packages/aoa-maxitor/tests`); vitest for the client's pure modules (fingerprint, arrangement store, layout equivalence) — the check run executes `npm test`, so these tests are a gate and must be fast and deterministic under jsdom (no timers, no network, no browser APIs beyond what jsdom has); the measurement tool, run by hand, for everything a real browser must show

**Target Platform**: evergreen browsers (module workers, IndexedDB, `crypto.subtle` in a secure context); the Maxitor container (`python:3.12-slim`) behind the stand's nginx

**Project Type**: web application — FastAPI backend serving a React SPA

**Performance Goals**: first open ≤ 1 300 000 B; repeat open ≤ 50 000 B; Slow 4G first pixel < 6 s; longest main-thread task < 150 ms at 1× CPU and < 600 ms at 4× CPU; repeat open first pixel < 0.5 s (SC-001 … SC-006)

**Constraints**: the same picture for the same graph and canvas size (FR-010, FR-023); no production code exists only for tests (the tool reads what any browser exposes: network events, long tasks, the canvas, worker targets); refusals keep their status and headers (FR-007)

**Scale/Scope**: the reference graph has 440 nodes, 545 edges, 19 node types, 4 domains. Server: `app.py` plus one small static-files class. Client: `FullGraphViewer.tsx`, `main.tsx`, four new modules beside the viewer, one script, `package.json`.

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1.*

| Principle | How this plan meets it | Status |
|---|---|---|
| I. The maintainer decides | Every phase ends in a commit **prepared and shown**, not made. The stand check of FR-026 waits for the maintainer's deploy; its result goes to the issue only when the maintainer asks. | Pass |
| II. English | Code, comments, docstrings, tests, the tool's output, commit messages: English. Russian only in `*.ru_draft.md`. | Pass |
| III. Module headers | The new Python test module and any new server module open with the path line and a `Name — purpose.` docstring with `PURPOSE` and `ARCHITECTURE / DATA FLOW`. `app.py`'s header gains the compression and cache step in its data flow. | Pass |
| IV. AI-CORE blocks | The new static-files class carries `ROLE` / `CONTRACT` / `INVARIANTS` ("a hashed asset is immutable; `index.html` is always revalidated"). No block on a method. | Pass |
| V. Short docstrings | Every new Python class, function and method has one line; the TypeScript modules follow the client's habit of a `/** … */` line on each export. | Pass |
| VI. Tail | Three last tasks, in order: check run to zero, documentation, one changelog article. Every case appears as a script and a notebook: the server's cases through `TestClient` (`04_full_graph_delivery`), the browser's cases — background layout, its fallback, the remembered arrangement, storage disabled, hover with dragging refused — by running the measurement tool once per case (`05_full_graph_in_the_browser`). | Pass |
| Check run | No new step. Playwright stays out of the run (FR-001); the README check beside `components/*/index.ts` covers the viewer's README, which is updated. The two accepted remarks stay — the Vite chunk-size advisory may name a new worker chunk; it is the same advisory. | Pass |

Post-design re-check: no new Python package or dependency; in the client one new runtime dependency, `@antv/layout` pinned to 2.0.0 (already installed through G6, so the lock file gains a direct entry, not a new package; the worker chunk carries its own copy of the layout code, whose bytes count against SC-001), and one dev dependency (`playwright`); `@antv/g-webgl` enters only if phase 6 keeps WebGL, and then it is a runtime dependency whose bytes count against SC-001. No cross-package import. **Pass.**

## Project Structure

### Documentation (this feature)

```text
specs/026-full-graph-fast-open/
├── spec.md
├── plan.md                  # this file
├── research.md              # R1–R9
├── data-model.md            # fingerprint, remembered arrangement, measurement report, layout input
├── quickstart.md            # end-to-end validation
├── contracts/
│   ├── http-headers.md      # what the server sends: compression, Cache-Control, refusals
│   ├── layout-worker.md     # the message the worker takes and the one it returns
│   └── measurement-report.md # the tool's command line and JSON output
├── data/
│   ├── baseline-main.json   # commit 2: the tool's report on main
│   ├── canvas-main.png      # commit 2: the reference picture at 1600×900
│   ├── baseline-main-erd.json # commit 2: the tool's report for `view=domain-erd` on main (SC-008)
│   ├── full-graph-ref.json  # commit 2: the full-graph answer for the frozen graph (input of the equivalence test)
│   └── final.json           # commit 7: the tool's report on the finished change
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks
```

### Source Code (repository root)

```text
packages/aoa-maxitor/src/aoa/maxitor/api/
├── app.py                         # GZipMiddleware outermost; StaticFiles → CachedStaticFiles
└── cached_static_files.py         # NEW: Cache-Control by path (hashed /assets/* immutable, index.html no-cache)

packages/aoa-maxitor/tests/
└── test_api_compression_and_cache.py   # NEW: headers of a hashed asset, index.html, a graph read, a refusal

packages/aoa-maxitor/client/
├── package.json                   # dependency: @antv/layout 2.0.0 (exact); devDependency: playwright; script "measure"
├── scripts/
│   └── measure-full-graph.ts      # NEW: the measurement tool (phase 1)
└── src/
    ├── main.tsx                   # phase 3: start import("@antv/g6") when view=full-graph
    ├── lib/icons/graph_node_disk_icons.ts   # phase 6: glyph cache (kept only if it helps)
    └── components/diagrams/FullGraphViewer/
        ├── FullGraphViewer.tsx    # no G6 layout; draws given positions; no drag-element; hulls after first frame
        ├── README.md              # Files table gains the four modules (three in issue phase 4, `arrangementStore.ts` in phase 5)
        ├── layoutSettings.ts      # NEW: today's effective d3-force settings, one object
        ├── forceLayout.ts         # NEW: runs D3ForceLayout like G6 does; imported only by the worker and the tests, never by the viewer
        ├── forceLayout.worker.ts  # NEW: module worker wrapping forceLayout
        ├── arrangementStore.ts    # NEW: fingerprint + IndexedDB, bounded LRU, every failure → "not remembered"
        └── *.test.ts              # NEW: equivalence with today's G6 call, fingerprint, store fallbacks

docs/tutorials/step-26-maxitor.md  # the full-graph page: what is sent, when it is cached, what is remembered
examples/step_26_maxitor/
├── 04_full_graph_delivery.py / .ipynb        # NEW: the server's cases through TestClient
└── 05_full_graph_in_the_browser.py / .ipynb  # NEW: the browser's cases, one run of the measurement tool each
docs/CHANGELOG.md                  # one article
```

**Structure Decision**: The existing web-application layout (`packages/aoa-maxitor` with its `client/`) is kept. New client modules live beside the only viewer that uses them, as the README rule of `components/*/` expects; nothing goes to `lib/` until a second viewer needs it.

## Phases (each one commit)

Numbers in the first column are the issue's phases; tasks.md numbers commits, which start with the specification itself (commit 1), so issue phase *n* is commit *n + 1* and the tail is commits 8–10.

| Issue phase | Phase | Main files | Proven by |
|---|---|---|---|
| 1 | Measurement tool and baseline | `scripts/measure-full-graph.ts`, `package.json`, `data/baseline-main.json`, `data/canvas-main.png` | two runs on `main` give equal bytes and an equal canvas |
| 2 | Compress and cache | `app.py`, `cached_static_files.py`, `test_api_compression_and_cache.py` | pytest; the tool's bytes (SC-001, SC-002) |
| 3 | G6 starts early | `main.tsx` | the tool's request order; other views without G6 and not heavier than `baseline-main-erd.json` (SC-008) |
| 4 | Layout in a worker | `layoutSettings.ts`, `forceLayout.ts`, `forceLayout.worker.ts`, `FullGraphViewer.tsx` | vitest equivalence; canvas equal to `canvas-main.png`; worker CPU time; longest task; `--no-worker` |
| 5 | Remembered arrangement, no dragging | `arrangementStore.ts`, `FullGraphViewer.tsx` | vitest; the tool's repeat open (SC-006); `--interaction-probe`, `--no-storage` |
| 6 | Less in the first frame | `FullGraphViewer.tsx`, `graph_node_disk_icons.ts`, maybe `package.json` | the tool, per part, with and without |
| 7a | Check run to zero | — | `bash scripts/run_checks_with_log.sh` |
| 7b | Documentation | `docs/tutorials/step-26-maxitor.md`, `examples/step_26_maxitor/04_*`, `05_*`, viewer README | the examples run |
| 7c | Changelog | `docs/CHANGELOG.md` | maintainer review |

## Risks

- **The picture is checked by pixels.** Research R4 expects the layout to be deterministic for one canvas size (`d3-force` seeds its own generator). Phase 1 confirms it by running twice on `main`; if two runs differ, the work stops there and the difference is recorded in research.md before any tolerance is chosen (T008). A snapshot is taken only from a settled frame (contracts/measurement-report.md), so fitting the view and late glyphs cannot make the comparison flaky.
- **The 150 ms and 600 ms targets may be out of reach.** G6 created the shapes of 351 nodes in 164 ms; at 440 nodes this alone may exceed 150 ms (SC-004). At 4× CPU the same work is about 164 × 4 ≈ 660 ms already at 351 nodes, so SC-005 (600 ms) is out of reach unless drawing gets cheaper: drawing stays on the main thread. FR-025 applies to both: what improves ships, the gap is reported. Phase 6's WebGL comparison is the one lever left.
- **SC-001 has little margin.** The issue measured the gzipped total at 1 214 331 B, about 7 % under the 1 300 000 B target; anything that adds weight (the layout worker's chunk, the WebGL renderer) can cross it, which is why T025 and T038 count bytes.
- **gzip on the fly costs server CPU.** Level 6 rather than Starlette's default 9: the assets are compressed once per new visitor and then cached for a year (R1).
- **The stand's proxy.** If nginx strips or re-encodes the headers, it is reported (FR-026), not fixed here.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `@antv/layout` becomes a direct dependency. | The worker runs `D3ForceLayout` outside G6 (research R2), so it must import the package itself. | Importing a package that is only a transitive dependency would break silently when G6 moves to another version; pinning it to the version G6 resolves keeps one copy in the lock file. |
| A second G6 renderer package (`@antv/g-webgl`) is added during phase 6. | FR-022 asks for the comparison with real figures. | Comparing without installing it would be a guess; it is removed in the same commit if canvas wins. |
