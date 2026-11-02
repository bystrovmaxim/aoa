# Quickstart: validating typed events

How to prove the feature works. The types are in [data-model.md](data-model.md), and the public surface in [contracts/typed-events.md](contracts/typed-events.md).

## Prerequisites

From the repository root, with the development extras:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv sync --extra dev
```

## Scenarios

| # | Do | Expect |
|---|---|---|
| 1 | Emit an event through `info`, `warning`, `critical` with a recording logger | the rendered line; `var` is the event with level, channels, domain filled |
| 2 | Render the same templates with `kwargs` and with an event | the same lines |
| 3 | Subscribe loggers by channel, level and domain | the same filtering for both forms |
| 4 | Break `@emits` from each of the five kinds of method | each fails by its own path; no logger receives the line |
| 5 | Break `@emits` under `TestBench.run_aspect`, `run_summary`, `run_compensator` | `EventContractError` reaches the test |
| 6 | Declare `@emits(B)` in a domain with `events = (A,)` | the build fails, naming the method, the event and the domain |
| 7 | Log with no event in a domain with `events`, with and without `@emits` | refused at runtime |
| 8 | Run a nested action from an untyped domain inside a typed one | its `kwargs` line is delivered |
| 9 | Serve a result from the cache | no event |
| 10 | Emit from `@access_decide`, by a run and by `check_access_decide` | delivered both times |
| 11 | Let a plugin and the machine write around a typed method | both delivered |

## `aoa-demo`

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev pytest packages/aoa-demo/tests -q
```

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && uv run --extra dev graph-builder check
```

The tests pass and `graph.json` of the demo has not changed.

## Adversarial breaks

Each break must fail its own test and no other. Restore after each.

| # | Break | The test that must fail |
|---|---|---|
| 1 | `box` skips the system fields | an event's line has its level, channels and domain |
| 2 | `box` passes the author's instance as `var` | the author's instance stays unchanged |
| 3 | Remove the check on `kwargs` beside an event | an event with `kwargs` is refused |
| 4 | Remove the check of the object's type | an object in the event's place is refused |
| 5 | Remove the suffix check | a name without `Event` is refused |
| 6 | Remove the reserved names check | a reserved field name is refused |
| 7 | Remove the author's check | an author setting a system field is refused |
| 8 | Drop `exclude=True` from the system fields | a dump holds the fact's own fields only |
| 9 | `emission_rules_for` ignores `@emits` | a method with `@emits` refuses an unlisted event |
| 10 | `emission_rules_for` ignores `events` | a domain with `events` refuses a line with no event |
| 11 | Treat `events = ()` as absent | an empty vocabulary refuses everything |
| 12 | Remove the rules from one `TestBench` entry, in turn | the refusal under that entry |
| 13 | Move the check into `ScopedLogger` | a plugin's line is delivered around a typed method |
| 14 | Remove the build check | `@emits` outside `events` fails the build |
| 15 | The build check skips one kind of method, in turn | the build check names that kind |
| 17 | Remove the argument checks of `@emits` | invalid `@emits` arguments are refused |
| 18 | Remove the second-application check | `@emits` applied twice is refused |
| 19 | Remove the validation of `events` in `BaseDomain` | invalid `events` are refused |
| 20 | Accept an instance of `BaseEvent` itself | a bare `BaseEvent` is refused |
| 21 | Drop the `/` from the tools | a keyword named `event=` stays a variable |
| 22 | Check the rules after rendering the text | a refusal comes before a template error |
| 23 | Read the domain of the outer action in a nested run | a nested action answers to its own domain |
| 24 | Export `BaseEvent` from `model/__init__.py` | no first import closes a cycle |
| 25 | Lose `kwargs` in a line with no event | a line with `kwargs` keeps its dictionary `var` |
| 26 | Refuse a line with no event when no switch is on | a line with no event is delivered with no switch on |

## The end

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/check_before_commit.sh
```

Before a pull request, on the pushed commit:

```bash
cd /Users/bystrovmaxim/PythonDev/aoa && bash scripts/check_before_pr.sh
```
