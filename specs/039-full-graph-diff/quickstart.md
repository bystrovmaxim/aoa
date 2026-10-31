# Quickstart: validating #291

## Automated

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run pytest packages/maxitor/front/tests -q
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa/packages/maxitor/front/client && npx vitest run
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```

Expected: every edge id equals the document's; the union's order and golden hash hold; the same layout in three engines, the union included.

## By hand: the acceptance stand

Start `design-preview`, `maxitor` and `maxitor-client` from `.claude/launch.json`, and the port with `MAXITOR_HISTORIES=.demo-history/histories.toml MAXITOR_HISTORY_CACHE=.demo-history/cache REPO_GRAPH_PORT_PORT=8102 uv run repo-graph-port`, and open the link in `.demo-history/erd-full.url`, then the full graph in the left panel.

| Step | Expect |
|---|---|
| a pair with changes in several domains | rings, dashed circle, edges, the rest faded |
| the button | equals the drawn marks of each kind |
| a retargeted relation | one amber edge, a thin dashed one to the old target |
| a pair where only an edge changed | `+0 −0 ~0`, the edge marked |
| a pair with nothing drawn changed | "no changes", nothing faded |
| click a changed, an added, a removed, an unchanged node | the card; the card; the card; as in One |
| a domain only in A, one only in B | hull and marks; listed in the panel |
| switch a type, a domain, a change off | gone, nothing moves, the button follows |
| a filter that leaves no change | "no changes", nothing faded |
| reload the address; a second tab of a room | same filters |
| open the pair twice | the second time no layout runs |
| B on Live, change the live file | marks and counts follow within 30 s |
| Diff → One | B in its own layout, unmarked |
| phone width | the button, the Filter pill, the card by tap |

## On the real stand, after the merge, by the maintainer

gameoffer 0.8.0 → 0.9.0, full graph: `+23 −1 ~5`.
