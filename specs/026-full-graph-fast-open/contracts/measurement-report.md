# Contract: the measurement tool

`packages/aoa-maxitor/client/scripts/measure-full-graph.ts` — a development tool, outside the check run.

## Command line

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && node scripts/measure-full-graph.ts --maxitor http://127.0.0.1:8101 --source http://127.0.0.1:8765/graph-json --out ../../../specs/026-full-graph-fast-open/data/run.json --canvas ../../../specs/026-full-graph-fast-open/data/canvas-run.png
```

| Option | Default | Meaning |
|---|---|---|
| `--maxitor` | required | base URL of a Maxitor serving its built client |
| `--source` | required | the graph-json URL put into `?source=` |
| `--view` | `full-graph` | another value measures another view (used for SC-008); the first graph pixel is sampled on the full graph only, and another view's window ends at `load` + 3 s |
| `--conditions` | `cpu1x,cpu4x,slow4g` | which conditions to run |
| `--runs` | 3 | runs per condition; times are reported as the median, bytes must be equal across runs |
| `--out` | stdout | where the JSON report goes |
| `--canvas` | none | where to save the canvas PNG of `cpu1x/first` |
| `--compare-canvas` | none | a reference PNG; the run fails if any pixel of the settled frame differs |
| `--no-pixel-probe` | off | turns the first-pixel sampler off (`firstGraphPixelMs` is then `null`, and the long-task window ends at `load` + 3 s); used only to check what the sampler costs |
| `--interaction-probe` | off | moves the pointer across non-transparent canvas pixels until a `.graph-hover-label` appears (a node is under it), fails if no card appears; then drags 80 px from that point, moves the pointer out of the canvas, and fails if the settled canvas changed (FR-023, FR-024) |
| `--no-worker` | off | deletes `window.Worker` before the page loads; the run then **expects** the viewer's fallback warning and fails without it, and still requires a drawn graph (FR-012) |
| `--no-storage` | off | deletes `window.indexedDB` before the page loads; the repeat open must then lay out again (a layout worker appears) and show no error (FR-017) |

Exit code `0` when the run succeeded; `1` when a console failure was seen, bytes differed between runs, or `--compare-canvas`, `--interaction-probe`, `--no-worker` or `--no-storage` found what they fail on.

**The window**: long tasks are counted from navigation start until 3 s after the first graph pixel (spec FR-001). Without the sampler there is no first pixel, so the window ends at the `load` event plus 3 s; runs with different windows are compared only on the tasks that start before the shorter window ends.

**The bytes**: a run's bytes are read only after every request the open started has finished — half a second with nothing in flight, at most 30 s — so a late answer cannot change the total. A body's decoded size is read from the response body when it did not come from the cache.

**The first pixel**: once per animation frame, the G6 canvas is drawn into a 16×16 offscreen canvas created with `willReadFrequently: true` and those 256 pixels are read; the first frame with any alpha > 0 is the first graph pixel, and sampling stops there. The full canvas is never read on the page's main thread. A higher threshold would not help: G6 paints the whole graph in one frame (research R9).

**The settled frame**: `--canvas` and `--compare-canvas` use a screenshot of the canvas element taken with the pointer outside it, from the canvas layer that carries the drawing (G6 paints several canvases and the empty ones are ignored). After the first graph pixel, the tool waits for two animation frames inside the page, takes a screenshot, and repeats every 200 ms; the frame is settled when five consecutive screenshots are identical (nothing changed for at least 800 ms). The run fails if the canvas has not settled within 10 s.

## Report

```json
{
  "tool": "measure-full-graph/1",
  "commit": "<git rev-parse --short HEAD of the measured build>",
  "maxitor": "http://127.0.0.1:8101",
  "source": "http://127.0.0.1:8765/graph-json",
  "viewport": [1600, 900],
  "canvasSize": [0, 0],
  "conditions": {
    "cpu1x": {
      "first": {
        "totalBytes": 0,
        "longestTaskMs": 0,
        "firstGraphPixelMs": 0,
        "mainScriptingMs": 0,
        "workers": [{ "url": "…", "cpuMs": 0 }],
        "longTasks": [{ "startMs": 0, "durationMs": 0 }],
        "resources": [
          { "url": "…", "type": "script", "encodedBytes": 0, "decodedBytes": 0,
            "contentEncoding": "gzip", "cacheControl": "public, max-age=31536000, immutable",
            "status": 200, "fromCache": false }
        ]
      },
      "repeat": { "…": "same shape" }
    },
    "cpu4x": { "…": "same shape" },
    "slow4g": { "…": "same shape" }
  },
  "consoleFailures": [],
  "canvas": "data/canvas-run.png"
}
```

The acceptance table of the spec maps to: SC-001 `cpu1x.first.totalBytes`; SC-002 `cpu1x.repeat.totalBytes`; SC-003 `slow4g.first.firstGraphPixelMs`; SC-004 `cpu1x.first.longestTaskMs`; SC-005 `cpu4x.first.longestTaskMs`; SC-006 `cpu1x.repeat.firstGraphPixelMs`; SC-008 a run with `--view` of another view, compared with the same view's baseline `data/baseline-main-erd.json`: its `totalBytes` is not higher, its `resources` hold no G6 chunk, and the `decodedBytes` of the run's largest `/assets/index-*.js` — the app chunk every view loads — is at most 5 000 above its baseline — the guard that catches layout code landing there (`D3ForceLayout` alone is 47 422 bytes minified).
