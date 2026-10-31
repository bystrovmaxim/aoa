# Quickstart: Validate Comparison on Use-Case Diagrams

## Stand

Extend `.demo-history/build_erd_full.py` as the spec's stand section says, run it, then start `design-preview`, `repo-graph-port-demo`, `maxitor` and `maxitor-client` from `.claude/launch.json`. The link is in `.demo-history/erd-full.url`.

## Checks

1. `uv run pytest packages/maxitor/core/graph_compare packages/maxitor/front/tests` passes.
2. `npm test --prefix packages/maxitor/front/client` passes.
3. In Diff open each new version pair on a domain's use cases: walk User Stories 1–4.
4. On a pair where only a result field changed: one action amber, the button `+0 −0 ~1`, its card lists the field.
5. The same pair on the ERD and the map: marks as before.
6. Break the walk (ignore `generic:result`): the new test fails, no other; restore.
7. `bash scripts/run_checks_with_log.sh` is clean.

After the merge the maintainer checks gameoffer's 0.8.0 → 0.9.0 (SC-002).
