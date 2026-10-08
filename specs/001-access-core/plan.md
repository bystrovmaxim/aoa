# Implementation Plan: Access decisions — three answers, one cascade, two events

**Branch**: `feature/issue-189-access-core` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-access-core/spec.md`

## Summary

One ordered cascade of four steps decides access for both the execution path and the question path, and every decision is exactly one of three answers: allowed, refused (naming the gate, and the reason a developer declared if any), or undecided (naming the gate that could not tell). A developer declares the reason a condition refuses with, beside the condition. Every decision and every failed gate publishes a new event, carrying the answer and the request identity the context already holds. The work lives inside `packages/aoa-action-machine`; the only touch outside it is the `except` clause in the two adapters, so that a refusal keeps leaving as a refusal (see [research.md](./research.md), D7).

## Technical Context

**Language/Version**: Python 3.12 (the repository's floor; the workspace is a `uv` monorepo)

**Primary Dependencies**: pydantic v2 (`BaseSchema`, already the engine's model base), the engine's own plugin bus and graph — no new dependency is introduced

**Storage**: none. The core stores nothing: it reads whatever a developer's gate reads and returns an answer (spec FR-016, Assumptions)

**Testing**: pytest, per package (`packages/aoa-action-machine/tests/action_machine/**`), plus the existing adapter tests that must keep seeing a refusal

**Target Platform**: the engine library itself; no endpoint, no status codes, no error bodies (spec Assumptions)

**Project Type**: library inside a monorepo (`packages/aoa-action-machine`), with the repository-wide check run as the closing gate

**Performance Goals**: the decision is in-process and bounded by the number of gates (four); no new measurable target, and the core adds no I/O of its own

**Constraints**: the request identity the events carry is `context.request.trace_id`, published by the OpenTelemetry plugin as `aoa.trace_id` — the only identity the context has today, and it is populated nowhere yet (#170), so an event carries it only when it is set and never invents one; no batch form of the question in the core; the reason vocabulary is additive; the two events are additions to the plugin contract; the existing adapter tests keep passing; `bash scripts/run_checks_with_log.sh` green at the end

**Scale/Scope**: 3 answer types, 5 gate words over 4 steps, 1 declared object check with its own graph node type, 1 decision matrix (4 points × 3 situations × 2 modes) fixed in the contracts, 1 new event type plus the check's own before/after events, 1 declared-reason validator, nine phases of work as ordered in issue #189

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
| --- | --- | --- |
| I. The maintainer decides | No commit, push, pull request or merge is part of executing this plan without an explicit instruction in the current turn | PASS — the plan produces files only |
| II. English in commits, in git and in code | Every new file: module header, docstrings, comments, commits — English | PASS — planned |
| III. Module headers | Each new module opens with its repository-relative path comment, a `Name — purpose.` first line, and the 79-column `═` sections the codebase uses | PASS — planned |
| IV. AI-CORE blocks | Every new public class carries `ROLE` and `CONTRACT`, with `INVARIANTS` where the type has invariants; no block in a module docstring or on a method | PASS — planned |
| V. Short docstrings | Every new class, function and method gets its one-line docstring, ending with a period, identifiers in double backticks | PASS — planned |
| Final step: the check run | `bash scripts/run_checks_with_log.sh` is the last step, and its errors are fixed before the work is called done | PASS — planned as the closing step of the last phase |

No violations, so **Complexity Tracking** stays empty.

**Re-check after Phase 1 design**: the design artifacts add no new module outside the structure above, no new dependency, and no new public surface beyond the two events and the answer types — so every gate above still passes, and no exception has to be justified.

## Project Structure

### Documentation (this feature)

```text
specs/001-access-core/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # The capability, clarified
├── research.md          # Phase 0 output: the decisions behind the design
├── data-model.md        # Phase 1 output: answers, gates, reasons, events
├── quickstart.md        # Phase 1 output: how to prove it works
├── checklists/
│   └── requirements.md  # Spec quality checklist (filled during /speckit-clarify)
├── contracts/           # Phase 1 output: the surfaces this capability fixes
│   ├── developer-surface.md
│   ├── answer-schema.md
│   └── plugin-events.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
packages/aoa-action-machine/
├── src/aoa/action_machine/
│   ├── intents/
│   │   ├── access_decide/                  # the declared object check (decorator, intent, resolver)
│   │   ├── access_control/                 # the answers and the cascade
│   │   │   ├── verdict.py                  # Verdict: the base answer, with kind
│   │   │   ├── allowed.py                  # Allowed
│   │   │   ├── refused.py                  # Refused, plus the shared FORBIDDEN_OBJECT
│   │   │   ├── undecided.py                # Undecided: the gate that could not tell, private cause
│   │   │   ├── gate.py                     # Gate: the five published words
│   │   │   ├── cascade.py                  # the four steps, GATES, decide()
│   │   │   └── access_verdict.py           # removed in phase 9
│   │   └── check_roles/
│   │       ├── reason_validation.py        # reason= beside when= and guard=
│   │       ├── grant.py                    # carries the declared when= reason
│   │       ├── check_roles_decorator.py    # carries the declared guard= reason
│   │       └── check_roles_intent_resolver.py
│   ├── graph/
│   │   ├── nodes/access_decide_graph_node.py   # AccessDecideGraphNode: the declared check
│   │   ├── edges/access_decide_graph_edge.py   # @access_decide composition edge
│   │   └── edges/role_graph_edge.py        # properties["reason"]
│   │   └── nodes/action_graph_node.py      # properties["guard_reason"]
│   ├── runtime/
│   │   ├── action_product_machine.py       # _decide_and_emit, both paths
│   │   └── role_checker.py                 # its refusals move into the gates
│   ├── exceptions/
│   │   ├── access_denied.py                # AccessDenied(verdict)
│   │   ├── access_undecided.py             # AccessUndecided(verdict)
│   │   └── authorization_error.py          # stays until the transport follow-up
│   └── plugin/core/
│       ├── events.py                       # AccessGateFailedEvent
│       └── plugin_coordinator.py           # emit_access_gate_failed
└── tests/action_machine/
    ├── intents/access_control/             # answers, reasons, the decision matrix
    ├── intents/check_roles/                # declared reasons and their validation
    ├── graph/{edges,nodes}/                # the declared reasons reach the graph
    ├── runtime/                            # both paths, ordering, events
    └── exceptions/                         # the new exceptions, and the old one's tests

packages/aoa-otel/src/aoa/otel/plugin/open_telemetry_plugin.py   # handler for the failed-gate event
packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/resources/duckdb_graph_resource.py   # the new node type
packages/aoa-maxitor/client/src/lib/icons/graph_node_disk_icons.ts                      # its icon
packages/aoa-fastapi-adapter/src/aoa/fastapi/adapter.py          # except clause only
packages/aoa-mcp-adapter/src/aoa/mcp/adapter.py                  # except clause only
docs/tutorials/, docs/reference/glossary.md, CHANGELOG.md        # phase 9
```

**Structure Decision**: the capability is one package's concern — `packages/aoa-action-machine` — so every new module stays inside the existing `intents/access_control` intent, and the plan touches only folders that already exist (intents, graph, runtime, exceptions, plugin). Nothing new appears at the repository level and no package is added. The OpenTelemetry plugin gains one handler because an event is observable only through a plugin; the two adapters change only where they catch the exception the core used to raise.

## Complexity Tracking

No constitution violations to justify.
