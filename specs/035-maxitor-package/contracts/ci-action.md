# Contract: the CI action `packages/maxitor/tools/gnomon/action.yml`

A composite GitHub Action. A project adds it with one step:

```yaml
- uses: bystrovmaxim/aoa/packages/maxitor/tools/gnomon@<ref>
```

| Input | Default | Meaning |
|---|---|---|
| `config` | `gnomon.toml` | the config to check |
| `sync` | `uv sync --all-extras` | installs the project's environment, in which the graph builds run; empty to skip |
| `gnomon` | `uvx --from "maxitor==<version of the action's ref>" gnomon` | how to run the command; this repository passes `uv run --extra dev gnomon` to use its own workspace |

Steps: check out is the caller's; `astral-sh/setup-uv`; the `sync` command; `<gnomon> check --config <config>`.

Outcome: the step fails exactly when `gnomon check` fails — a stale or missing graph file, a failing build, a refused document or config — and its log is `gnomon check`'s output, naming the differences and the command that fixes them.

This repository's `.github/workflows/ci.yml` replaces its hand-written `gnomon check` step with the action, from the same checkout (`uses: ./packages/maxitor`).
