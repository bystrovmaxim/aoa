# Quickstart: validating issue #245

Every command is self-contained and starts from an absolute path. The figures to compare against are the spec's Success Criteria and `data/baseline-main.json`.

## 1. One-time setup

The measurement tool needs a browser engine:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && npm ci && npx playwright install chromium
```

## 2. Serve the frozen reference graph

The graph is the copy committed for #268 (440 nodes). Check it, then serve it as `graph-json` on port 8765:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && gunzip -c specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz | shasum -a 256
```

Expected: `a9d73e90b8c486fc18a3304b3eacf024a229a9642b71709af8bb919ebf0f84cf`.

```bash
mkdir -p /tmp/aoa-ref-graph && gunzip -c /Users/bystrovmaxim/PythonDev/aoa/specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz > /tmp/aoa-ref-graph/graph-json && cd /tmp/aoa-ref-graph && python3 -m http.server 8765 --bind 127.0.0.1
```

## 3. Run a production build of Maxitor

Build the client into the directory Maxitor serves (`static/` is ignored by Git), then start the API on port 8101:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && npm run build && rm -rf ../src/aoa/maxitor/static && cp -R dist ../src/aoa/maxitor/static
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && MAXITOR_API_PORT=8101 uv run maxitor-api
```

## 4. Measure

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && node scripts/measure-full-graph.ts --maxitor http://127.0.0.1:8101 --source http://127.0.0.1:8765/graph-json --out ../../../specs/026-full-graph-fast-open/data/run.json --canvas ../../../specs/026-full-graph-fast-open/data/canvas-run.png --compare-canvas ../../../specs/026-full-graph-fast-open/data/canvas-main.png
```

Expected after all phases (the report's fields are listed in [contracts/measurement-report.md](contracts/measurement-report.md)):

| Field | Target |
|---|---|
| `cpu1x.first.totalBytes` | ≤ 1 300 000 |
| `cpu1x.repeat.totalBytes` | ≤ 50 000 |
| `slow4g.first.firstGraphPixelMs` | < 6 000 |
| `cpu1x.first.longestTaskMs` | < 150 |
| `cpu4x.first.longestTaskMs` | < 600 |
| `cpu1x.repeat.firstGraphPixelMs` | < 500 |
| `consoleFailures` | empty |
| canvas comparison | identical |

`run.json` is any validation run; the final measurement of the change is saved by T039 as `data/final.json` with the same command and `--out ../../../specs/026-full-graph-fast-open/data/final.json`.

Add `--interaction-probe` to prove that hover cards still appear and that a node no longer moves (FR-023, FR-024); `--no-worker` to see the main-thread fallback draw the graph (FR-012); `--no-storage` to see a repeat open lay out again without an error (FR-017). Run once more with `--view domain-erd` and compare with `data/baseline-main-erd.json`: no G6 chunk in `resources`, `totalBytes` not higher, and the app chunk's `decodedBytes` at most 5 000 above the baseline (SC-008).

## 5. Tests

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run pytest packages/aoa-maxitor/tests/test_api_compression_and_cache.py -q
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/aoa-maxitor/client && npm test
```

Expected: the header tests pass (compressed and uncompressed asset, `index.html`, a graph read, a refusal); vitest passes the layout equivalence, fingerprint and arrangement-store tests.

## 6. Adversarial checks

Each break must make exactly the named check fail, and nothing else; then restore.

| Break | Must fail |
|---|---|
| Remove `GZipMiddleware` | the compression test; the tool's `totalBytes` |
| Set `max-age=0` on `/assets/*` | the cache test; the tool's `repeat.totalBytes` |
| Change `linkDistance` to 200 | the vitest equivalence test; `--compare-canvas` |
| Make the worker post `ok: false` | the tool (console failure) |
| Leave `node_type` out of the fingerprint | the fingerprint test for a retyped node |
| Put `drag-element` back | `--interaction-probe` |

## 7. On the stand (after the maintainer deploys)

```bash
curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip' https://maxitor.aoa.run/ | grep -i '^\(content-encoding\|cache-control\|vary\)'
```

Expected through the stand's nginx: `cache-control: no-cache` for the page; the same command on one `/assets/…js` shows `content-encoding: gzip` and `cache-control: public, max-age=31536000, immutable` (FR-026).
