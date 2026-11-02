# Research: Every method of an action gets its own box

No clarification was open. Five design questions were settled by reading the code on `main` at 60ff7a43.

## R1. Where the preparation of a method's box lives

**Decision**: one internal function, `method_box(...)`, in a new module `runtime/method_box.py`, not exported from the package. All four call sites use it: `AspectExecutor`, `SagaCoordinator`, `ErrorHandlerExecutor`, `ActionProductMachine`.

**Rationale**: the gap in issue #331 exists because each kind of method prepares its `box` by hand, and two kinds were never written. One function makes the rule a single piece of code. It also replaces two copies of the same fifteen lines instead of adding two more.

**Alternatives considered**:
- `ToolsBox.for_method(name, state)`: the shortest call, because the shared `box` already knows nearly everything. Rejected: `ToolsBox` is what an action's author holds, so an action could rename itself, and #95 needs that name to be trustworthy. It would also change the public interface (FR-007).
- Two more hand-written blocks in the new places: the smallest diff, and it leaves the cause of the gap in place.

## R2. Where `@access_decide` gets its box

**Decision**: in `ActionProductMachine._decide`, which gains a keyword `check_name: str | None = None`. Both paths already hold that name: `_announce_object_check` returns the check node's label just before the object step. With a name, `_decide` prepares the method's `box`; without one, it passes the shared `box` on.

**Rationale**: `_decide` is the one spot both paths go through, and the machine owns the log coordinator. Early gates receive the shared `box` but no method: neither `auth_gate` nor `roles_gate` calls anything that writes to it.

**Alternatives considered**:
- Prepare it in `cascade.py`, beside `_call_declared`, where the method is actually called: the closest spot. Rejected: the cascade would need the log coordinator, and its contract is that it decides and publishes nothing. `decide(...)` is also public to its tests, so its signature would change.
- Prepare it in `_run_internal` and `check_access_decide` separately: two call sites for one rule.

## R3. The name, the action name and the graph

**Decision**: the method name comes from the graph node's `label` (`handler_node.label`, the check node's `label`); the action name from `action.get_full_class_name()`, as the two named kinds do today.

**Rationale**: every method node's id is `TypeIntrospection.full_qualname(action) + ":" + method_name`, and `get_full_class_name()` is that same `full_qualname`. So `f"{scope.action}:{scope.aspect}"` is the node id for all five kinds, including `AccessDecideGraphNode` and `ErrorHandlerGraphNode`.

## R4. Does anyone rely on the empty name

**Decision**: no. The assumption in the spec holds.

**Rationale**: searched all eight packages, `docs/` and `examples/`. Nothing in source reads `scope.aspect`; `{%scope.aspect}` appears in no shipped template or example; tests build `LogScope` by hand and none asserts an empty aspect from a real run. `ConsoleLogger` does not print it.

## R5. Existing tests that pass stand-ins

**Decision**: `method_box` reads only `run_child`, `factory`, `resources`, `nested_level` and `rollup` from the incoming `box`, exactly as the two existing copies do.

**Rationale**: `test_aspect_executor.py` passes a `SimpleNamespace` and `test_error_handler_executor.py` a `MagicMock`. Keeping to these five fields means neither needs a change. `TestBench` builds its own boxes for the three kinds it runs and has no entry for the other two, so it stays as it is.

## What stays deliberately unnamed

`_log_rollback_failure` writes the machine's own critical line with an empty method name. No method wrote it and no `box` is involved, so the rule does not reach it.
