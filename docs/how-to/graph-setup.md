# Set up versions and graphs

The `aoa-graph-builder-setup` wizard sets up two independent things: a version check and saved model graphs. Choose either, both or neither. Run it again at any moment: it audits the project and proposes only the difference.

## Start it

Ask your coding agent to set up versions and graphs, after saving the skill where the agent finds it:

```bash
graph-builder skill > .claude/skills/aoa-graph-builder-setup/SKILL.md
```

The wizard asks one question at a time, in four stages: Discover, Services, Updates and checks, Review. Nothing is written to the project until you approve the reviewed plan.

## What it does not do

- It never raises a version number. It only asks for the first number of a new file.
- It requires no release tags. Existing tags stay yours, and Maxitor still shows them as release flags.
- It never changes repository rules. It names the check to make required, and says that `main` must require a branch to be up to date before merging.

## Where decisions are kept

Each part has its own file, so either can be set up alone.

| Part | File | Items |
|---|---|---|
| Versions | `[setup]` in the root `version.toml` | `version-files`, `ci-version-check` |
| Graphs | `[setup]` in `graph-builder.toml` | `config`, `graph:<name>`, `exporter:<service>`, `local-update`, `ci-graph-check` |

```toml
[setup]
skill = "3"
decided = ["config", "graph:orders", "exporter:orders", "local-update", "ci-graph-check"]
deferred = ["local-update"]
```

`skill` is the revision of the wizard, not a release. Only `local-update` and `ci-graph-check` may be deferred, and a deferred item is also decided. An older file that lists `version-tags` keeps working; the wizard proposes removing it.

The [script](../../examples/step_26_maxitor/15_setup_decisions.py) and [notebook](../../examples/step_26_maxitor/15_setup_decisions.ipynb) show which records are accepted:

```bash
uv run --extra dev python examples/step_26_maxitor/15_setup_decisions.py
```

```text
Optional update deferred:
ok tiny
Setup decisions preserved: True
A green graph check says nothing about version checks.
Deferred mandatory config: refused setup.deferred.0
Undecided local update: refused setup.decided
```

## How a version check is proved

A workflow file proves nothing, so the wizard checks a real failure in a disposable Git copy: it commits the setup, commits one counted change without raising a number, and requires the tool to fail.

```text
version-gate: component svc (svc/version.toml): version 1.0.0 did not grow; main has 1.0.0, raise it above that
```

## Retiring something

A folder can outlive its separate version or map. The wizard raises this only on evidence, such as a service folded into its package, or when you ask. It shows what stays covered, and which CI checks stay. Removing the last graph also retires `graph-builder.toml`, because an empty one is refused. If a required check would disappear, you release that requirement first.

Skipping a part on one visit changes nothing that is already in force.
