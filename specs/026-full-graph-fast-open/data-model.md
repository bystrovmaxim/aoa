# Data Model: The Full Graph Opens Fast and Never Freezes the Tab

Nothing changes in the server's data or in the `GET /api/v1/full-graph` payload. The entities below live in the browser or in the measurement tool.

## Layout settings

One exported constant in `FullGraphViewer/layoutSettings.ts`; the only source of the layout's numbers (research R3).

| Field | Value | Note |
|---|---|---|
| `iterations` | 220 | steps run before drawing |
| `linkDistance` | 72 | every edge — what today's accessor returns for every edge |
| `linkStrength` | 0.82 | every edge, same reason |
| `manyBody` | `{ strength: -360, distanceMax: 1200 }` | |
| `collide` | `{ radiusOffset: 7, strength: 0.95, iterations: 4 }` | radius = `node_visual_px * 0.5 + radiusOffset` |
| `centerStrength` | 0.012 | the centre point is half the canvas size |
| `alphaDecay` / `alphaMin` / `velocityDecay` | 0.012 / 0.0015 / 0.42 | |

**Rule**: any change to this object changes every fingerprint (below), so a remembered arrangement is never drawn under settings it was not computed with.

## Layout input and result

What the viewer sends to the worker and gets back; the wire format is in [contracts/layout-worker.md](contracts/layout-worker.md).

- **Input**: node ids in payload order, edges as `[source, target]` in payload order, `node_visual_px`, canvas `width` and `height`.
- **Result**: `positions`, a map from node id to `[x, y]`, covering every input node.

**Validation**: a result missing any node id, or holding a non-finite coordinate, is discarded, and the graph is laid out by G6 itself on the main thread instead (today's path; nothing is remembered from it).

## Fingerprint

A 64-character hex SHA-256 over the canonical JSON

```json
{"settings": <layout settings>, "nodes": [[id, node_type], …], "edges": [[source, target, edge_type], …]}
```

with `nodes` and `edges` sorted lexicographically.

- **Changes when**: a node is added or removed, a node's type changes, an edge is added, removed or retyped, or the layout settings change (FR-015).
- **Does not change when**: labels, colours, descriptions, the server's row order, the source URL or the canvas size change (the canvas size only moves the whole layout; research R6).
- **Unavailable when**: `crypto.subtle` is missing (an origin that is neither HTTPS nor localhost) — then nothing is remembered.

## Remembered arrangement

IndexedDB database `maxitor-full-graph`, version 1, object store `arrangements`, key path `fingerprint`, index on `lastUsed`.

| Field | Type | Note |
|---|---|---|
| `fingerprint` | string | key |
| `positions` | `Record<string, [number, number]>` | the layout's result, never a dragged position (there is none: FR-024) |
| `lastUsed` | number (ms since epoch) | set on write and on every read that is drawn |

**Lifecycle**:

```
open page ─► fingerprint ─► read ──hit, covers every node──► draw positions ─► touch lastUsed
                              │
                              └─miss / unreadable / incomplete / storage error─► background layout, then:
                              worker answered ──yes──► page still open? ──yes──► draw ─► write ─► prune to 20 by lastUsed
                                                       └─no──► discard (FR-013)
                              worker failed ──────────► draw by G6's own layout, nothing written (FR-014)
```

**Bound**: at most 20 entries; after each write the oldest by `lastUsed` are deleted (FR-018).

**Only the worker's layout is written**: a layout the fallback produced (G6's own path, FR-012) is never stored, so the next open tries the background again (FR-014).

**Only the full graph**: the arrangement is computed from, and remembered for, the whole payload. Hiding or showing nodes (#246) changes visibility only and never reads, writes or recomputes an arrangement (FR-019).

**Empty graph**: no layout runs and nothing is remembered.

## Measurement report

One JSON document per run of the tool; full shape in [contracts/measurement-report.md](contracts/measurement-report.md).

- **Run**: tool version, Maxitor URL, source URL, viewport, timestamp, git commit of the build being measured.
- **Condition** (`cpu1x`, `cpu4x`, `slow4g`) × **open** (`first`, `repeat`):
  - `resources[]`: url, type, encoded bytes, decoded bytes, `content-encoding`, `cache-control`, status, served from cache;
  - `totalBytes`, `longestTaskMs`, `longTasks[]`, `firstGraphPixelMs`, `mainScriptingMs`, `workers[]` (url, cpuMs);
  - `consoleFailures[]`: messages that fail the run.
- **Canvas**: path of the PNG taken on `cpu1x/first`, and `canvasSize`, the G6 canvas's CSS size, which the layout's centre is computed from.
