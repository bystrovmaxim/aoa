<!-- translated-from: authoring-action_draft.md @ 2026-06-24T16:11:21Z (filesystem mtime; draft is gitignored, no git history) · sha256:47d151dfefcf -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# How to write an operation

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [The skeleton of an operation](#the-skeleton-of-an-operation)
- [Params and Result — Pydantic at the boundary](#params-and-result--pydantic-at-the-boundary)
- [The aspect pipeline and the flow of state](#the-aspect-pipeline-and-the-flow-of-state)
- [Checkers — the contract for return values](#checkers--the-contract-for-return-values)
- [Connections — external resources inside aspects](#connections--external-resources-inside-aspects)
- [ParamsStub — an operation with no parameters](#paramsstub--an-operation-with-no-parameters)
- [Naming](#naming)
- [Testing aspects directly](#testing-aspects-directly)
- [What matters](#what-matters)

---

## The skeleton of an operation

A minimal operation with a single summary aspect:

```python
from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox


class GreetParams(BaseParams):
    name: str


class GreetResult(BaseResult):
    message: str


@meta(description="Say hello.", domain=MyDomain)
@check_roles(GuestRole)
class GreetAction(BaseAction[GreetParams, GreetResult]):
    Params = GreetParams
    Result = GreetResult

    @summary_aspect("Build greeting message.")
    async def build_greeting_summary(
        self,
        params: GreetParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GreetResult:
        _ = (state, box, connections)
        return GreetResult(message=f"Hello, {params.name}!")
```

Three annotations on the class are mandatory: `@meta`, `@check_roles`, `BaseAction[P, R]`.

## Params and Result — Pydantic at the boundary

`BaseParams` and `BaseResult` are Pydantic models. All input validation lives here, not in the aspects:

```python
from pydantic import ConfigDict, Field

class LoadParams(BaseParams):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(min_length=1, description="Service URL.")

class LoadResult(BaseResult):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_count: int = Field(ge=0)
    resource: SomeResource = Field(...)
```

**Rule:** if a value can be rejected through Pydantic (`min_length`, `ge`, `pattern`, a validator), do it there. An aspect should receive data that's already correct.

The `Params = ...` and `Result = ...` aliases inside the class are an optional convenience: they let you reference the types as `MyAction.Params` instead of a string.

## The aspect pipeline and the flow of state

When logic breaks down into steps, each step is a separate regular aspect. Aspects run **in declaration order**. Each one receives the accumulated `state` and returns a **dict with every key** the later aspects and the summary need.

```python
from typing import Any, cast
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect

@meta(description="Validate and load remote graph.", domain=MyDomain)
@check_roles(GuestRole)
class LoadGraphAction(BaseAction[LoadParams, LoadResult]):

    @regular_aspect("Validate that the URL is reachable and returns a graph.")
    async def validate_url_aspect(self, params, state, box, connections) -> dict[str, Any]:
        _ = (state, box, connections)
        # ... validation logic ...
        return {"graph_url": params.url}

    @regular_aspect("Fetch raw graph data from the service.")
    async def fetch_graph_aspect(self, params, state, box, connections) -> dict[str, Any]:
        _ = (params, box, connections)
        url = cast(str, state["graph_url"])
        # ... fetch logic ...
        return {"graph_url": url, "graph_data": data}

    @summary_aspect("Build result from fetched graph data.")
    async def build_result_summary(self, params, state, box, connections) -> LoadResult:
        _ = (params, box, connections)
        data = cast(dict, state["graph_data"])
        return LoadResult(node_count=len(data["nodes"]))
```

**Key invariant:** every `@regular_aspect` returns a dict, and `BaseState(**dict)` builds the next state from it. Keys not included in the return value are unavailable in the next aspect. Forward every key needed further down the pipeline.

## Checkers — the contract for return values

Checkers verify that an aspect returned the expected key with the expected type/non-empty value. A checker decorator goes **above** `@regular_aspect`:

```python
from aoa.action_machine.intents.checkers import result_instance, result_string, result_int

@result_string("graph_url", required=True, not_empty=True)
@regular_aspect("Validate the URL.")
async def validate_url_aspect(self, params, state, box, connections) -> dict[str, Any]:
    ...
    return {"graph_url": url}

@result_string("graph_url", required=True, not_empty=True)
@result_instance("graph_data", dict, required=True)
@regular_aspect("Fetch graph data.")
async def fetch_graph_aspect(self, params, state, box, connections) -> dict[str, Any]:
    ...
    return {"graph_url": url, "graph_data": data}
```

Available checkers:

| Decorator | What it checks |
|---|---|
| `result_string(field, required, not_empty, min_length, max_length, opaque)` | a string |
| `result_instance(field, expected_class, required, no_none, value_check, opaque)` | an instance of a class |
| `result_int(field, required, min_value, max_value, opaque)` | an integer |

Checkers **don't** have a `description` parameter.

## Connections — external resources inside aspects

If an operation needs an external resource (a DB, an HTTP client), declare it through `@connection` on the class. Aspects read the resource from `connections[key]`:

```python
from aoa.action_machine.intents.connection import connection

@meta(description="Query sidebar data from DuckDB.", domain=MyDomain)
@check_roles(GuestRole)
@connection(DuckDBResource, key="db", description="DuckDB graph connection")
class GetSidebarAction(BaseAction[ParamsStub, GetSidebarResult]):

    @regular_aspect("Load nodes from DuckDB.")
    async def load_nodes_aspect(self, params, state, box, connections) -> dict[str, Any]:
        duck = cast(DuckDBResource, connections["db"])
        rows = duck.execute_fetch_dicts("SELECT id, label FROM nodes")
        return {"nodes": rows}

    @summary_aspect("Build result.")
    async def build_result_summary(self, params, state, box, connections) -> GetSidebarResult:
        _ = (params, box, connections)
        return GetSidebarResult(nodes=cast(list, state["nodes"]))
```

`@connection` is a declaration for the graph and for the runtime; the resource itself is supplied when calling `machine.run(..., connections={"db": resource})`.

## ParamsStub — an operation with no parameters

When an operation takes no user parameters (all data arrives through `connections`), use `ParamsStub`:

```python
from aoa.action_machine.model import ParamsStub

@meta(...)
@check_roles(GuestRole)
@connection(DuckDBResource, key="db", description="...")
class GetSidebarAction(BaseAction[ParamsStub, GetSidebarResult]):

    @summary_aspect("Build sidebar.")
    async def build_sidebar_summary(
        self,
        _params: ParamsStub,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetSidebarResult:
        ...
```

## Naming

| What | Rule | Example |
|---|---|---|
| The operation class | suffix `Action` | `LoadGraphAction` |
| A `@regular_aspect` method | suffix `_aspect` | `validate_url_aspect` |
| A `@summary_aspect` method | suffix `_summary` | `build_result_summary` |
| `Params` / `Result` | separate classes ahead of the operation class | `LoadGraphParams`, `LoadGraphResult` |

Breaking the suffix convention raises `NamingSuffixError` when the graph is built.

## Testing aspects directly

Every aspect is an ordinary async method. Test them one at a time, passing the accumulated state through `BaseState(**kwargs)`:

```python
from aoa.action_machine.model import BaseState

_ACTION = LoadGraphAction()

async def test_validate_url_aspect_rejects_ftp() -> None:
    params = LoadParams(url="http://placeholder")
    object.__setattr__(params, "url", "ftp://host")   # bypass Pydantic for the edge case
    with pytest.raises(ValueError, match="HTTP"):
        await _ACTION.validate_url_aspect(params, BaseState(), None, {})

async def test_fetch_graph_aspect_returns_data() -> None:
    state = BaseState(graph_url="http://localhost:8001/graph")
    result = await _ACTION.fetch_graph_aspect(None, state, None, {})
    assert "graph_data" in result
```

For aspects with `connections`, pass a real resource or a test double:

```python
async def test_load_nodes_aspect() -> None:
    duck = DuckDBResource.build_from_json(MINIMAL_GRAPH)
    result = await _ACTION.load_nodes_aspect(None, BaseState(), None, {"db": duck})
    assert isinstance(result["nodes"], list)
```

For the full pipeline, accumulate state sequentially:

```python
async def test_full_pipeline() -> None:
    conn = {"db": DuckDBResource.build_from_json(GRAPH)}
    r1 = await _ACTION.validate_url_aspect(params, BaseState(), None, conn)
    r2 = await _ACTION.fetch_graph_aspect(params, BaseState(**r1), None, conn)
    result = await _ACTION.build_result_summary(params, BaseState(**r2), None, conn)
    assert isinstance(result, LoadResult)
```

## What matters

- **`@meta` and `@check_roles` are mandatory.** Without them the graph build fails.
- **Decorator order matters.** `@result_*` checkers go above `@regular_aspect`; `@meta` and `@check_roles` go above the class.
- **Exactly one summary aspect.** It's the only one that returns a `Result`, not a `dict`.
- **Validation at the boundary.** An aspect shouldn't check what Pydantic can already check in `Params`/`Result`.
- **State is an immutable snapshot.** An aspect doesn't mutate `state` — it returns a new dict, from which the runtime builds the next `BaseState`.
- **Unused parameters.** Suppress the warning with a single assignment: `_ = (state, box, connections)`.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
