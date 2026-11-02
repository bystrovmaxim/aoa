# Implementation Plan: Typed events, `@emits` and the domain vocabulary

**Branch**: `feature/issue-333-baseevent-core-typed-events-emits-and-the-domain-vocabulary` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/049-base-event-core/spec.md`

## Summary

`BaseEvent` is the tenth primitive: a typed fact that also declares the system fields of a log line. `box` takes one in place of `kwargs`, after the text, fills the system fields in a copy, and hands that copy to the logger as `var`. The logger, the coordinator, the templates and the subscriptions keep their logic. `@emits` on a method and `events` on a domain are the two switches: `ToolsBox` checks them before anything reaches a logger, so plugins and the machine are never touched. The build checks `@emits` against `events`. `aoa-demo` goes through the cascade, and the documentation shows every case.

## Technical Context

**Language/Version**: Python 3.12, also checked on 3.14

**Primary Dependencies**: none new; pydantic is already the base of `BaseSchema`

**Storage**: N/A

**Testing**: pytest, in `packages/aoa-action-machine/tests/action_machine/` and `packages/aoa-demo/tests/`; `tests/examples/test_examples_run.py` runs every script under `examples/`

**Target Platform**: the library, wherever it runs

**Project Type**: Python library in a monorepo of eight packages

**Performance Goals**: none new. With neither switch on, a method's `box` has no rules to check, and each logging call gains one `None` check. Reading the rules adds two attribute lookups per method call, next to the `resolve_domain` already made there.

**Constraints**: `ToolsBox` gains no public member (R5). `BaseLogger` keeps its methods and parameters (R9). Production code carries no linter pragma (R1). `BaseEvent` is imported from its own module, because importing it from `model/__init__` would close an import cycle (R1). No graph node or edge changes (R8).

**Scale/Scope**: `aoa-action-machine`: 7 new modules, about 9 changed, 7 new test files. `aoa-demo`: 1 new module, 3 changed, 1 new test file. Documentation: 1 new chapter, 5 new example pairs, 8 changed pages.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this work meets it | Status |
|---|---|---|
| I. The maintainer decides | Nothing is committed, pushed or opened without an instruction. | Pass |
| II. English | Code, docstrings and commits in English. | Pass |
| III. Module headers | Every new module starts with its path and a module docstring with `PURPOSE`. | Pass |
| IV. AI-CORE blocks | `BaseEvent`, `EmissionRules`, `EventContractError` and `emits` carry a block; methods do not. | Pass |
| V. Short docstrings | Every new class, function and method carries one. | Pass |
| VI. The last three steps | Three reserved tasks: check run, documentation, changelog. Every case appears as a script and as a notebook, executed while written. | Pass |
| Final check run | `check_before_commit.sh` before every commit; `check_before_pr.sh` before the pull request. | Pass |

No violations. Re-checked after design: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/049-base-event-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/typed-events.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
packages/aoa-action-machine/src/aoa/action_machine/
├── model/
│   └── base_event.py                  # new: BaseEvent, imported from here
├── domain/
│   ├── event_marker.py                # new: recognises an event class without a cycle
│   └── base_domain.py                 # validates events
├── intents/emits/
│   ├── __init__.py                    # new: exports emits
│   └── emits_decorator.py             # new
├── exceptions/
│   └── event_contract_error.py        # new
├── logging/
│   ├── log_var_payloads.py            # LogVar
│   ├── scoped_logger.py               # emit_event: fills the copy, sends it
│   └── base_logger.py, log_coordinator.py, subscription.py,
│       variable_substitutor.py, console_logger.py   # the declared type of var only
├── runtime/
│   ├── emission_rules.py              # new: EmissionRules, emission_rules_for
│   ├── tools_box.py                   # the three tools take an event and check the rules
│   └── method_box.py                  # passes the rules
├── graph/
│   ├── validators/emits_vocabulary_validator.py   # new
│   └── core/node_graph_coordinator.py # calls it
└── testing/bench.py                   # three entries pass the rules

packages/aoa-action-machine/tests/action_machine/
├── model/test_base_event.py                   # new
├── model/test_import_order.py                 # new: no first import closes a cycle
├── domain/test_domain_events.py               # new
├── intents/emits/test_emits_decorator.py      # new
├── intents/logging/test_event_line.py         # new
├── runtime/test_emission_rules.py             # new: modes, five kinds, parity
└── graph/test_emits_vocabulary_validator.py   # new

packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/
├── events.py                          # new
├── orders_domain.py                   # declares events
└── actions/get_order.py, create_order.py   # typed calls, same text
packages/aoa-demo/tests/                # new test of the cascade

docs/explanation/architectural-constitution.md, verification-must-be-independent.md
docs/tutorials/step-10-logs.md          # three small changes
docs/tutorials/step-11-object-events.md # new
examples/step_11_object_events/         # new: every case, script and notebook
docs/reference/intents-and-invariants.md, glossary.md
docs/how-to/authoring-logger.md
docs/index.md, README.md
docs/CHANGELOG.md                       # one article
```

**Structure Decision**: `BaseEvent` sits with the other data primitives in `model/`, and `@emits` gets its own intent package, as every method decorator has. The check goes in `runtime/` beside `method_box`, which is where a method's box is prepared. `step-11-machine.md` is not touched: its navigation belongs to #336.

## Phases

One phase is one commit, in the order of issue #333:

1. **`BaseEvent` and `box`.** `EventMarker`, `BaseEvent`, `EventContractError`, `LogVar`, `ScopedLogger.emit_event`, and the three tools with their new signature. `@emits` and `events` do not exist yet, so every event is delivered. Tests: the event, a line with an event, parity of templates and subscriptions, refused calls, the order of imports.
2. **`@emits`.** `intents/emits`, `EmissionRules` with its `declared` half, `method_box`, `TestBench`. Tests: the five kinds, each by its own path; both paths of `@access_decide`; a plugin and the machine around a typed method; the cache.
3. **`events`.** Validation in `BaseDomain`, the `vocabulary` half of `EmissionRules`, the build check. Tests: the runtime rows of the table, the build check for each kind, nested actions, inheritance, `()`.
4. **`aoa-demo`.** The two calls, `events.py`, `OrdersDomain.events`, and a test of the cascade on the product.
5. **Closing check run** taken to zero.
6. **Documentation.** The architectural constitution and its Russian draft, the Russian draft of the second page, chapter 11 with its examples, the reference pages.
7. **Changelog.** The plan stops here: no release, version bump or publishing.

The specification and the plan go into the first commit.

Each rule is asserted by one test, so each break in [quickstart.md](quickstart.md) fails exactly one test, as `AGENTS.md` requires.
