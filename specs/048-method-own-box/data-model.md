# Data Model: Every method of an action gets its own box

Nothing is stored and no public type changes. There is one new internal function.

## `method_box`

| Input | Meaning |
|---|---|
| `box` | The box to derive from. Supplies `run_child`, `factory`, `resources`, `nested_level`, `rollup`. |
| `coordinator` | The log coordinator. |
| `action` | The running action. Supplies the action name and the domain. |
| `method_name` | The name of the method about to be called. |
| `context` | The call's context, kept inside the logger. |
| `state` | What the method's log sees. |
| `params` | The call's params. |

**Output**: a new `ToolsBox`. It differs from `box` only in its logger.

**Rules**:
- Called once per call of a method, immediately before it.
- Everything it copies from `box` is copied unchanged (FR-006).
- `{action}:{method_name}` is the id of the method's graph node (FR-005).

## Who calls it, and with what

| Kind | Called from | `method_name` | `state` |
|---|---|---|---|
| `@regular_aspect` | `AspectExecutor.call_aspect` | `aspect_node.label` | current |
| `@summary_aspect` | `AspectExecutor.call_aspect` | `aspect_node.label` | current |
| `@compensate` | `SagaCoordinator` | the compensator's name | snapshot before the step |
| `@on_error` | `ErrorHandlerExecutor.handle`, once a handler is chosen | `handler_node.label` | the handler's `state` |
| `@access_decide` | `ActionProductMachine._decide`, when it receives `check_name` | the check node's `label` | empty `BaseState()` |
