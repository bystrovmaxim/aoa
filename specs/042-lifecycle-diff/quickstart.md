# Quickstart: Checking Lifecycle Comparison

## Setup

Run `.demo-history/build_erd_full.py`, then start from `.claude/launch.json`: `design-preview` (8899), `repo-graph-port-demo` (8102), `maxitor` (8000), `maxitor-client` (5173). The link is in `.demo-history/erd-full.url`.

## Walk on `erd-full`

1. In Diff, a domain with changed lifecycles shows `~` on their rows only.
2. Open a `+` row: all green, dots too; the button counts states plus transitions. Open a `−` row: all red and dashed.
3. Open a `~` row: compare each mark with the comparison and the counts with the marks.
4. Find two transitions into one state, one new: one green, one grey, each with its own card and step.
5. Find a moved transition: one red, one green.
6. Click states changed in name, kind, colour, order: each card says what changed.
7. Step through all changes both ways; check the total, Shift + ↑ ↓ and the list.
8. Switch a change kind and a state kind off: counts and stepper follow; 1-hop brings neighbours back.
9. Hover a state in One and in Diff; repeat in a room.
10. Try both directions, B on Live with a changed live graph, Live as A with a pull request as B, a phone width.
11. Diff → One on a `−` page: the message and the way back.

## Automatic

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/run_checks_with_log.sh
```

Expected: every step passes; One's DOT text matches its recorded text.

## After the merge

The maintainer opens gameoffer's 0.8.0 → 0.9.0: the lifecycle of `OfferRequestCoreEntity`, all green, +7.
