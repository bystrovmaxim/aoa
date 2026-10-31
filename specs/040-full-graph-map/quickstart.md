# Quickstart: validating #319

## Prerequisites

`uv sync --extra all`; `npm ci` in `packages/maxitor/front/client`; Graphviz:

```bash
brew install graphviz
```

## Automated

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```

Expected: every step passes, the map's positions the same in three engines.

## The thresholds

Generate the graph 30 times the stand's size and run the measured session; both tools come with this work. Each line of SC-001 – SC-006 prints its number beside its threshold.

## By hand: the acceptance stand

Start `design-preview`, `repo-graph-port-demo`, `maxitor` and `maxitor-client` from `.claude/launch.json`, and open the link in `.demo-history/erd-full.url`, with `view=full-graph`.

| Step | Expect |
|---|---|
| open the graph | areas and bundles at once |
| zoom in to a field and out | things fade in and out; nothing moves |
| open a pair | counts on folded domains, the button equal to the comparison |
| a domain only in A, one only in B | areas of their own, marked |
| a pair where only a link changed | `+0 −0 ~0` |
| a pair with nothing drawn changed | "no changes", nothing faded |
| click a marked node | the card |
| click a folded domain's count | the map flies to its first change, card open |
| step through every change | each once, total equal to the button |
| switch a type, a domain, a change off | gone at once, nothing moves; outlines close around what is left and read `45 of 394 left`; at every level |
| move the gear shift, on the map and on the ERD | that section opens, the others fold |
| reload the address; a room of two browsers | same filters and paint, one picture |
| B on Live, change the live file | counts follow within 30 s |
| phone width | pinch, tap for the card, the Filter pill |
| real Safari | the same walk |

## The look

Show the map beside today's full graph on the stand; the maintainer approves it (SC-015).

## After the merge, by the maintainer

gameoffer 0.8.0 → 0.9.0, full graph: `+23 −1 ~5`.
