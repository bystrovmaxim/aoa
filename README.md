# ActionMachine (aoa)

Intent-first business logic with metadata-driven actions, role-based access control, and adapters (FastAPI, MCP). The codebase is a **monorepo** of four installable PyPI distributions that share the **`aoa.*`** import namespace (PEP 420 namespace packages).

## Install

Pick the smallest distribution that matches what you need:

| Goal | Command |
|------|---------|
| Graph primitives only (`aoa.graph`) | `pip install aoa-graph` |
| Core framework (`aoa.action_machine`, pulls graph) | `pip install aoa-action-machine` |
| Samples + HTML visualizers (`aoa.maxitor`) | `pip install aoa-maxitor` |
| Example FastAPI / MCP apps (`aoa.examples`) | `pip install aoa-examples` |

**Examples do not install Maxitor.** `aoa-examples` depends only on `aoa-graph` and `aoa-action-machine`. Use `aoa-maxitor` when you need sample domains or interchange HTML exports.

Optional extras (examples in each package’s `pyproject.toml`):

- `aoa-action-machine[fastapi]`, `[mcp]`, `[postgres]`
- `aoa-examples[fastapi]`, `[mcp]`

From a **git checkout**, use [uv](https://docs.astral.sh/uv/) at the repository root:

```bash
uv sync --extra dev --group dev
```

Then run checks: `bash scripts/run_checks_with_log.sh` or `uv run task check`.

## Imports

Use the shared namespace:

- `aoa.graph.*`
- `aoa.action_machine.*`
- `aoa.maxitor.*`
- `aoa.examples.*`

There are **no** backward-compatible top-level shims (`graph.*`, `action_machine.*`, …). See [docs/packages.md](docs/packages.md) for the dependency matrix and release/version policy.

## Documentation

- [docs/packages.md](docs/packages.md) — distributions, dependency matrix, versioning
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — release notes

## License

MIT — see `pyproject.toml` and package metadata.
