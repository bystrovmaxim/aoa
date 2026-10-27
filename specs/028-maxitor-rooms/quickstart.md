# Quickstart: seeing Maxitor rooms work

How to check each part of the feature end to end. Details of messages, actions and hashes are in [contracts/](contracts/) and [data-model.md](data-model.md); this page only says what to run and what must be seen.

## Prerequisites

- The repository's environment: `uv sync --all-extras` at the root, `npm ci` in `packages/aoa-maxitor/client`.
- A built client: `cd packages/aoa-maxitor/client && npm run build`.
- Playwright browsers for the cross-engine step: `npx playwright install chromium firefox webkit`.
- Two services to point Maxitor at: the demo (`aoa-demo`) and, for fresh graphs, any local service whose `graph-json` you can change and restart.

Start Maxitor:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run maxitor-api
```

## 1. The same picture everywhere (US1)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && npm test
```

Expected: the guard, golden and spiral tests pass (contracts/layout-determinism.md).

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && node scripts/check-layout-determinism.ts
```

Expected: one line per page and layout mode with a single hash, and exit code 0. Break it on purpose — put `Math.cos` into `initialPositions.ts` or let the centre depend on the canvas width — and the guard test fails; restore.

## 2. A room with two people (US2, US3, US4)

1. Open the demo's ERD in browser A, press **Open room**, type "Anna". The address gains `room=…`; the invite card shows the link and *anyone with this link can join*.
2. Open the link in browser B at phone size (devtools 375×812), type "Boris". Both top rows show two circles; B lands on the same ERD with the same filters and layout mode.
3. Move the mouse over a table in A: B shows Anna's arrow on the same table. Zoom in B: the arrow stays on the table.
4. Switch a domain off and the layout to top-to-bottom in B: A changes the same way. Open the page in a third browser: it has the same settings.
5. Close B's tab and reopen the link within two minutes: no "left" or "joined" notice; the colour is the same.

## 3. Going to someone and following (US5, US6)

1. In A open the full graph. In B click Anna's circle: B opens the full graph centred on Anna's pointer, B's zoom unchanged.
2. In B choose **Follow** on Anna's card: a frame in Anna's colour appears. Scroll and change pages in A: B follows. Zoom in B: following goes on. Press Esc in B: it stops.
3. Make A follow B, then open A's card in B: **Follow** is disabled with the reason; **Go to** works.

## 4. Refusals and limits

- Open a link to a room id that does not exist: the page opens without a room and says *This room has ended*.
- Join a room with 20 participants (the room tests in `packages/aoa-maxitor/tests` drive this with 21 connections): the 21st sees *This room is full (20 people)*.
- The server log shows each refusal as a `security` warning with the room id and no name.

## 5. Fresh graphs (US7, US8)

```bash
curl -si 'http://127.0.0.1:8001/examples/model/graph-json' | grep -i etag
curl -si -H 'If-None-Match: "<tag from above>"' 'http://127.0.0.1:8001/examples/model/graph-json' | head -1
```

Expected: an `ETag` header, then `HTTP/1.1 304 Not Modified` (the demo's port may differ).

Open a page of your local service in Maxitor, change its model, restart it, and wait up to 30 s: the page redraws, keeps its page, filters, zoom and centre, and shows *The model was updated*. Restart it again without a change: nothing is rebuilt (the log says the source was unchanged). Stop the service: the page keeps working on the held graph.

## 6. Out-of-date tab (US9)

Keep a room tab open, rebuild the client (`npm run build`) and restart Maxitor: the tab shows *Maxitor was updated — reloading…*, reloads once and returns to the same page, room, zoom and centre.

## 7. ERD style and the footer (US10, US11)

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && node scripts/check-erd-table-style.ts
```

Expected: pass. Open an ERD and compare a table with mockup screen 21. Open the left panel: the GitHub mark, **Maxitor** and the installed version, centred; collapse it: only the mark with its tooltip.

## 8. The closing check run

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```

Expected: green, with only the two accepted remarks in the log (constitution, "Final step").
