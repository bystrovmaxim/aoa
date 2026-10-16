# Contract: the shared graph resource

**Feature**: `specs/005-shared-graph-resource` · **Date**: 2026-10-16

The surface `DuckDBGraphHolder` fixes. A reader of this contract should be able to tell, without
reading the implementation, whether a proposed change breaks it.

Module: `packages/aoa-maxitor/src/aoa/maxitor/api/duckdb_graph_holder.py`
Base: `aoa.action_machine.resources.base_resource.BaseResource`

---

## 1. Identity and construction

```python
@meta(description=..., domain=DiagramsDomain)
class DuckDBGraphHolder(BaseResource):
    def __init__(self, app: FastAPI) -> None: ...
```

- **C-1.1** Construction takes the `FastAPI` application and keeps it. It resolves nothing, reads
  nothing and raises nothing — building the application with no graph loaded must not fail.
- **C-1.2** The instance is created **once per application**, while the application is being built,
  and the same instance is passed to all six diagram routes. No route builds its own.
- **C-1.3** The holder is bound to the application it was built with. It must not reach any
  module-level global, cache or singleton, so that two applications in one process are independent.
- **C-1.4** The holder is a `BaseResource`, so it is a legal value in a route's `connections`
  without any framework change.

## 2. The operations

| Member | Signature | Returns |
| --- | --- | --- |
| `service` | property | the loaded graph's `duckdb.DuckDBPyConnection` |
| `execute_fetch_dicts` | `(sql: str, parameters: list[Any] \| tuple[Any, ...] \| None = None) -> list[dict[str, Any]]` | the loaded graph's rows as column-name → value dictionaries |

- **C-2.1** Each operation resolves the slot **at the moment it is called**. Neither stores a graph
  from an earlier call.
- **C-2.2** The signature of `execute_fetch_dicts` matches the loaded graph's own, including the
  default for `parameters`, so a caller cannot tell the holder and the graph apart.
- **C-2.3** These two are the whole surface. `__getattr__`, `__getattribute__` overrides, or any
  other forwarding to the resolved graph are forbidden: an attribute the graph has but the six
  routes do not use must not be reachable through the holder.
- **C-2.4** Reading an operation twice with the same loaded graph returns what the same graph
  returns both times — the holder introduces no caching, no copying and no wrapping.

## 3. The unloaded answer

```python
raise HandleError("...")
```

- **C-3.1** When nothing is loaded, both operations raise `aoa.action_machine.exceptions.HandleError`.
- **C-3.2** The message names the **situation** — that no graph is loaded — and the **remedy** —
  that the load endpoint must be called first. It must not name a factory, a return type, a
  connection wrapper or any other framework plumbing.
- **C-3.3** An application whose lifespan has not run (the slot attribute does not exist) produces
  the **same** failure as an application that has started with nothing loaded. The two are not
  distinguishable to a caller.
- **C-3.4** The failure is a Python-level one. No FastAPI exception handler is registered for it, no
  HTTP status is chosen for it and no response body is shaped for it. A caller's HTTP experience is
  exactly what it was before this feature.

## 4. Lifecycle

- **C-4.1** The holder has no `open`, `close`, `begin`, `commit` or `rollback`, and none is
  inherited. Nothing opens it before a run and nothing closes it after — on success, on failure or
  on cancellation.
- **C-4.2** `get_wrapper_class()` returns `None`. When the machine propagates connections to a
  nested action, the holder is passed through **as itself**. It is never wrapped.
- **C-4.3** `check_rollup_support()` returns `False`. It does not raise.
- **C-4.4** The holder owns nothing that needs releasing: it holds one reference to an application
  object and no resource of its own.

## 5. What this contract is not allowed to change

- **C-5.1** The connection key (`"DuckDBGraph"`) and the actions' `@connection` declarations.
- **C-5.2** The behaviour of `POST /api/load`, which stays the only writer of the slot.
- **C-5.3** Anything under `packages/aoa-action-machine/`. The contract above is satisfied by
  existing framework behaviour; if it stops being satisfiable, that is a defect in this feature, not
  a licence to edit the framework.
