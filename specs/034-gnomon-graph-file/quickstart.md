# Quickstart: Checking the Graph Files

Validation scenarios for [spec.md](spec.md). From the repository root, with its own environment.

## 1. Write the repository's graphs, twice

```bash
uv run gnomon write
git status --short packages/aoa-demo/graph.json packages/aoa-maxitor/graph.json
uv run gnomon write
git status --short packages/aoa-demo/graph.json packages/aoa-maxitor/graph.json
```

**Expected**: the first run writes both files (`ok demo (written)`, `ok maxitor (written)`); the second prints `(unchanged)` for both and `git status` shows nothing new (US3, SC-002).

## 2. The check finds a stale file

Change one field of a demo entity, then:

```bash
uv run gnomon check; echo "exit $?"
```

**Expected**: `stale demo: packages/aoa-demo/graph.json`, the differences by id, `gnomon write` as the fix, `exit 1`. Restore the field; `gnomon check` exits 0 (US2, SC-003).

## 3. Only the formatting differs

Re-indent `packages/aoa-demo/graph.json` with four spaces; `gnomon check` says only the formatting differs and exits 1. Restore with `gnomon write`.

## 4. The two graphs stay apart

```bash
uv run python -c "import json; d=json.load(open('packages/aoa-demo/graph.json')); m=json.load(open('packages/aoa-maxitor/graph.json')); print(len(d['nodes']), len(d['edges'])); print(sum(n['id'].startswith('aoa.maxitor') for n in d['nodes']), sum(n['id'].startswith('aoa.demo') for n in m['nodes']))"
```

**Expected**: `3213 4841`, then `0 0` — no Maxitor node in the demo's graph and no demo node in Maxitor's (SC-004).

## 5. Schema versions

A 1.1 export passes `check_graph`; the same export with one edge's `id` removed is refused naming the path; gameoffer's snapshot 006 (format 1.0) passes against 1.0; a document declaring `9.9` is refused naming the version (US4).

## 6. The package imports nothing from AOA

Add `import aoa.action_machine` to a module of `maxitor_gnomon`, run `uv run python scripts/check_package_boundaries.py`: it fails naming the file. Restore.

## 7. The check run

```bash
bash scripts/run_checks_with_log.sh
```

**Expected**: green; its last block is `Graph files (gnomon write)`, `OK`, and the graph files are unchanged. Break one other step (a failing test), run again: the graph step's block says `SKIPPED … 1 step(s) failed`.

## 8. Get started on gameoffer (after the feature, by the maintainer)

Follow only the README's Get started on gameoffer's two services. **Expected**: both graph files committed, CI runs `gnomon check`; every stop is fixed in the README (SC-001).
