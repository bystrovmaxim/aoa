# Quickstart: validating #290

## Prerequisites

`uv sync --extra all`; `npm ci` in `packages/maxitor/front/client`; `git`.

## Automated

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run pytest packages/maxitor/core/graph_compare/tests packages/maxitor/tools/graph_builder/tests packages/maxitor/front/tests -q
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/maxitor/front/client && npx vitest run
```

Expected: the comparison's cases of [contracts/graph-compare.md](contracts/graph-compare.md) each have a test, the demo pair under 1 s; `graph_builder`'s `differences` tests unchanged and green; the range rules of [data-model.md](data-model.md#state-transitions-of-the-range) each have a client test.

## The comparison alone

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run python examples/step_26_maxitor/17_compare_two_versions.py
```

Prints the counts and the differences of two small graphs, then of a `1.0` graph against a `1.1` one, then the demo's graph against itself with a few edits, with the time taken.

## By hand, locally

1. Start a port on a history with versions and Live, and Maxitor. Locally the maintainer's test histories in `.demo-history/` (out of git) serve: `MAXITOR_HISTORIES=.demo-history/histories.toml MAXITOR_HISTORY_CACHE=.demo-history/cache REPO_GRAPH_PORT_PORT=8102 uv run repo-graph-port`, then `uv run maxitor`; `forecast-admin` has twelve versions and Live.
2. Open the history, open the picker, choose **Diff**.

| Step | Expect |
|---|---|
| One on V → Diff | B = V, A = the one before; address bar `mode=diff&a=…&b=…` |
| drag A past B | they swap: the left handle is A |
| drop a handle on the other | it goes one further in its direction |
| drag a handle onto Live | it is B; Live is never A |
| Shift + → | both move, distance kept |
| open the link with `a` and `b` reversed | opens swapped |
| ERD of a domain that changed | marks, counts on the button |
| ERD of a domain that did not | "no changes", nothing faded |
| click an amber row | the card: each changed property, before → after |
| a domain added in B | `+` in the left panel; all green |
| "N versions between" | the rows, newest first; one opens whole |
| phone width | the button in the phone bar with counts; the sheet stacks the messages |

3. In a room, move a handle in one tab: every tab moves.
4. With B on Live, change the live service's graph: within 30 s the marks follow.

## On the stand (after the merge, by the maintainer)

`https://dev.maxitor.aoa.run`, gameoffer's history, A = 0.8.0, B = 0.9.0, the offers domain's ERD: the two new tables, the new fields and links, `is_activated` removed, `OfferRequestItemDetailEntity` changed, counted on the button (acceptance criterion 2).
