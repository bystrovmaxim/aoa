# Contract — what an aspect declaration must look like

**Feature**: `specs/010-aspect-declaration-invariants` | **Version**: 1 | **Date**: 2026-10-18

This is the user-facing contract of the four declaration decorators: what a developer writes, what the framework accepts, and what it refuses. It is the source for the documentation page updated in phase 5 and for the tests written in phase 1.

## 1. The four signatures

```python
@summary_aspect("Assemble the answer")
async def create_order_summary(
    self,
    params: CreateOrder.Params,
    state: BaseState,
    box: ToolsBox,
    connections: dict[str, BaseResource],
) -> CreateOrder.Result: ...
```

| Decorator | Required parameters, in this order |
| --- | --- |
| `@summary_aspect` | `self, params, state, box, connections` |
| `@regular_aspect` | `self, params, state, box, connections` |
| `@on_error` | `self, params, state, box, connections, error` |
| `@compensate` | `self, params, state_before, state_after, box, connections, error` |

`ctx` is appended **last** when, and only when, `@context_requires(...)` sits **under** the declaration:

```python
@summary_aspect("Assemble the answer")
@context_requires("user.id")
async def create_order_summary(
    self,
    params: CreateOrder.Params,
    state: BaseState,
    box: ToolsBox,
    connections: dict[str, BaseResource],
    ctx: ContextView,
) -> CreateOrder.Result: ...
```

## 2. The types each annotation must resolve to

| Parameter | Required type | Notes |
| --- | --- | --- |
| `params` | `BaseParams` or a subclass | the operation's own `Params` is the useful case; `BaseParams` is accepted |
| `state` | `BaseState` | |
| `box` | `ToolsBox` | |
| `connections` | `dict[str, BaseResource]` | a bare `dict` or `dict[str, Any]` is refused |
| `ctx` | `ContextView` | only when context was declared |
| `error` | `Exception` or the class the handler declares | the executor dispatches per declared type, so a `ValueError` handler never receives a `TypeError`; a non-exception annotation is refused |
| `state_before` (`@compensate` only) | `BaseState` | |
| `state_after` (`@compensate` only) | `BaseState \| None` | `None` when the compensated aspect did not finish |

The returns:

| Decorator | Required return |
| --- | --- |
| `@summary_aspect` | the operation's `Result`, or a supertype of it — `BaseResult` is accepted; `Any` and another operation's `Result` are refused |
| `@regular_aspect` | `dict[str, Any]` (the state fragment the engine already requires at run time) |
| `@on_error` | the operation's `Result`, as for a summary |
| `@compensate` | `None` |

## 3. What remains true from before

Unchanged, and still refused with their own errors: a non-empty description; `async def`; the name suffixes `_summary`, `_aspect`, `_on_error`, `_compensate` (with `summary` allowed as the bare name for a summary); a compensator naming a `@regular_aspect` that exists; exactly one summary per operation.

## 4. Where the two moments fall

| Check | When | Why then |
| --- | --- | --- |
| count, names, order, `ctx` placement, positional callability, annotations present | while the class body executes | nothing needs resolving, and the mistake is cheapest to fix where it was written |
| the types, and a summary's return type | when the capability is assembled | `params` is annotated with the operation's own `Params`, which does not exist while its class body runs |
| a second summary | when the capability is assembled | it is a property of the finished operation, not of one method |
| a summary's answer | after the method returns | the value does not exist before then |

## 5. Compatibility

- A declaration that meets this contract keeps its behaviour exactly: the same answer, the same pipeline order, the same events, the same logs.
- `AspectSignatureError` is a `SignatureContractError`, so a handler that catches the existing shape error (or `TypeError`) keeps catching these refusals.
- `DuplicateSummaryAspectError` is a `TypeError`, like `DuplicateAccessDecideError`.
- No decorator gains a parameter, no new option appears, and no existing error is renamed.
