# Quickstart: validating #289

## Prerequisites

`uv sync --extra all`; `npm ci` in `packages/maxitor/front/client`; `git`.

## Automated

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run pytest packages/maxitor/front/tests packages/maxitor/tools/repo_graph_port/tests -q
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/maxitor/front/client && npx vitest run
```

Expected: every mode M1–M7 of [contracts/ui.md](contracts/ui.md#modes) has a server test and a client test; no test log contains the test key.

## By hand, locally

1. Make a history on disk: run the example `examples/step_26_maxitor/<n>_maxitor_history.py`; it builds a git repository with three merged versions (one refused), a histories config with a `local` history `demo` and one with `live`, issues a key, and starts the port and Maxitor.
2. Open Maxitor, paste `http://127.0.0.1:8102/api/v1/history/demo#key=<key>`.
3. Walk the modes:

| Step | Expect |
|---|---|
| a running service address | M1: no version button |
| `demo` (no `live`, 3 versions) | M2: opens on the newest; ← → step; the refused one shows its reason |
| `demo-one` (1 version) | M3: one point, keys do nothing |
| `demo-live` (3 versions, `live`) | M4: opens on Live; dashed gap; Live's closing line |
| `demo-live-one` | M5: one point and Live |
| `demo-live-empty` | M6: Live alone, "0 versions and Live" |
| `demo-empty` | M7: "This history has no version yet." |

4. In M4, commit a fourth version to the example repository: within 30 s of the port listing it, the track shows it without a reload; the chosen version stays.
5. Open a room in M4, join it from a private window by the room link, pick a version in one tab: both move.
6. Grep Maxitor's terminal output and log for the key: no match.

7. Start Maxitor's own port with an empty histories config on `127.0.0.1:8103` and set `MAXITOR_PUBLIC_PORT=http://127.0.0.1:8103`; paste `https://github.com/<owner>/<public repo>/blob/main/graph.json`: M2 or M3, no key asked. Unset the variable: the same link is refused with "Public histories are not set up on this Maxitor".

## On the stand (after the merge, by the maintainer)

Add `live` to one history in the stand's histories config; open its address in the stand's Maxitor (`https://dev.maxitor.aoa.run`): M4 or M5 as the history is.
