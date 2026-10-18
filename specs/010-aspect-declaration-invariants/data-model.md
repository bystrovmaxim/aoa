# Phase 1 — Data model: the declaration contract

**Feature**: `specs/010-aspect-declaration-invariants` | **Date**: 2026-10-18

This feature has no stored data and no persisted schema. The model below is the **declaration contract**: the small vocabulary the feature judges, and the tables the implementation reads. It is written as data because the four decorators differ only in their values, not in their behaviour.

## The three entities of the specification

| Entity | What it is | Where it lives in code |
| --- | --- | --- |
| **Declaration** | a method an operation marks with one of the four decorators: its name, its description, its signature, and the class that hosts it | the decorated callable; its metadata is `_new_aspect_meta`, `_on_error_meta`, `_compensate_meta`, `_access_decide_meta` |
| **Operation** | the `BaseAction[Params, Result]` subclass that owns declarations; it has exactly one exit point and the two types every declaration is checked against | `graph/nodes/action_graph_node.py` and the intent resolvers |
| **Refusal** | the answer to a declaration that does not meet the contract: which rule, which declaration, what was written, what is required, and — for the signature rule — at which moment it was refused | the two new exception modules and the revived `ActionResultTypeError` |

## `AspectContract` — the table the four decorators share

One instance per decorator. Fields:

- `kind` — `summary` / `regular` / `on_error` / `compensate`; used in the refusal text and for the return rule.
- `parameters` — the parameter names in order, **without** `ctx`.
- `parameters_with_ctx` — the same plus the trailing `ctx`; chosen when the callable carries `_required_context_keys`.
- `expected_types` — parameter name → the type an annotation must resolve to (a class, `dict[str, BaseResource]`, or a union for `state_after`).
- `return_rule` — one of `operation_result`, `state_fragment`, `none`.

| `kind` | `parameters` | `expected_types` (beyond `self`) | `return_rule` |
| --- | --- | --- | --- |
| `summary` | `params, state, box, connections` | `BaseParams` (or subclass), `BaseState`, `ToolsBox`, `dict[str, BaseResource]`; `ctx`: `ContextView` | `operation_result` |
| `regular` | the same | the same | `state_fragment` (`dict[str, Any]`) |
| `on_error` | the same + `error` | the same; `error`: `Exception` or the class the handler was declared for | `operation_result` |
| `compensate` | `params, state_before, state_after, box, connections, error` | `BaseParams`, `BaseState`, `BaseState \| None`, `ToolsBox`, `dict[str, BaseResource]`, `Exception`; `ctx`: `ContextView` | `none` |

`return_rule` is enforced at assembly for all four kinds; `summary` and `on_error` need the operation's `Result` to do it, which is why it cannot happen while the class body runs. Only `summary` is enforced **again** at run time, on the returned value — the other three are not read as an answer by anything.

**Validation rules for the table itself** (checked by a test, not at run time): every contract's `parameters` starts with `self`; `parameters_with_ctx` is `parameters + ("ctx",)`; every entry of `expected_types` names a parameter that exists in the contract.

## The moment a declaration passes through

A declaration is judged at two moments, and the same declaration object travels through both only if the first passes:

```text
class body executes
        │
        ├─ the decorator reads the callable
        │     ├─ description, async, suffix          (unchanged, refusals keep their names)
        │     ├─ parameters in order                 → AspectSignatureError  ┐
        │     ├─ every non-self parameter annotated  → AspectSignatureError  ├─ moment 1: declaration
        │     └─ callable positionally               → AspectSignatureError  ┘
        │
        ▼
capability assembled (the operation's Params and Result exist)
        │
        ├─ annotations resolve                        → AspectSignatureError (moment 2)
        ├─ annotations name the contract types        → AspectSignatureError (moment 2)
        ├─ a summary's return names its Result         → AspectSignatureError (moment 2)
        ├─ at most one summary                        → DuplicateSummaryAspectError
        │
        ▼
the operation runs
        │
        └─ a summary's answer is its Result           → ActionResultTypeError
```

## Refusal taxonomy

| Rule | Error | Moment | Names in the message |
| --- | --- | --- | --- |
| parameters renamed / reordered | `AspectSignatureError` | declaration | the method, the expected order, the written order, why the order is fixed |
| trailing `ctx` disagrees with `@context_requires` | `AspectSignatureError` | declaration | the method and which decorator order is correct |
| keyword-only / `*args` / `**kwargs` | `AspectSignatureError` | declaration | the method, the parameters the engine passes |
| a parameter or the return is unannotated | `AspectSignatureError` | declaration | the method and the parameters that are bare |
| annotations do not resolve | `AspectSignatureError` | assembly | the operation, the method, the failing name |
| annotations resolve to the wrong types | `AspectSignatureError` | assembly | the operation, the parameter, what was declared, what is handed over |
| a summary's return is not its `Result` | `AspectSignatureError` | assembly | the operation, the method, what was declared, what the operation's `Result` is |
| a second summary | `DuplicateSummaryAspectError` | assembly | the operation and both methods |
| a summary's answer is not a `Result` | `ActionResultTypeError` | run time | the operation, the declared `Result`, the actual type |
| a wrong description / a sync method / a wrong suffix / no summary | the existing errors | unchanged | unchanged |

## State transitions

A **declaration** is stateless once created; what changes is the operation's **assembly status**, and it must change exactly once per operation per machine:

| From | Event | To |
| --- | --- | --- |
| declared | the decorator accepts the callable | declared (metadata written) |
| declared | the decorator refuses it | the class body fails; the class does not exist |
| declared | assembly resolves the types | assembled |
| declared | assembly refuses the types | assembly fails; no half-built node is left, and a second `ActionGraphNode(...)` raises the same refusal |
| assembled | a run | assembled (the run-time answer check does not change assembly) |

The last row of the assembly step is the one worth testing twice: the failure must be repeatable and identical, because a test fixture that builds the same operation twice would otherwise see a silently degraded graph on the second attempt.
