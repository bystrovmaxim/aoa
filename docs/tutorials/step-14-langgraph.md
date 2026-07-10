<!-- translated-from: step-14-langgraph_draft.md @ 2026-06-26T22:34:45Z (filesystem mtime; draft is gitignored, no git history) · sha256:a5cf7160bfc2 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 14b — LangGraph

<table width="100%"><tr>
  <td align="left"><a href="step-14-mcp.md">← Step 14 — MCP</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-15-schema-results.md">Step 15 — Schema Results →</a></td>
</tr></table>

- [A minimal graph](#a-minimal-graph)
- [State fields: inp, mid, out](#state-fields-inp-mid-out)
- [Nodes: an Action class and an async function](#nodes-an-action-class-and-an-async-function)
- [Topology](#topology)
- [Field mapping](#field-mapping)
- [Testing without a machine](#testing-without-a-machine)
- [Running through the machine](#running-through-the-machine)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In AOA, LangGraph is just another transport: a way to deliver a call to an Action node without touching the Action's own business logic. It's organized through `LangGraphController` — a fluent builder that:

1. **Declares the state schema** through `.inp()` / `.mid()` / `.out()` — it automatically creates an `AgentState` with the right types and defaults.
2. **Assembles the graph** through `.node()`, `.start()`, `.edge()`, `.route()`, `.finish()`.
3. **Validates the topology and the data contract** at `.build()` — before the first run.
4. **Runs** through `ctrl.ainvoke(data, box)` — `box` carries the resource pool, and every `machine.run()` call inside the graph goes through it.

Install: `pip install "aoa-langgraph" langgraph`.

[▶ Example: 01_external_connection.py](../../examples/step_14_langgraph/01_external_connection.py) · [Notebook](../../examples/step_14_langgraph/01_external_connection.ipynb)

---

## A minimal graph

```python
from aoa.langgraph import LangGraphController

ctrl = (
    LangGraphController()
    .mid("message", str, "Response message")   # one intermediate field
    .out("message")                            # returned from ainvoke()
    .node(PingAction)                          # the Action class, not an instance
    .start(PingAction)
    .finish(PingAction)
    .build()                                   # topology and contract validation
)

result = await ctrl.ainvoke({}, box)           # box = the resource pool
print(result["message"])                       # → "pong"
```

Three differences from `LangGraphAdapter`:
- `LangGraphController()` is created with no `machine`, no `context`, and no explicit `AgentState` — the schema is built from the field declarations.
- `.node()` takes an Action **class**, not an instance.
- Instead of `.compile()` you get `.build()` (validation) + `.ainvoke(data, box)` (running).

---

## State fields: inp, mid, out

Three kinds of declarations form the `AgentState` — the internal Pydantic model LangGraph uses as its state schema:

| Method | Field type | Default | Purpose |
|---|---|---|---|
| `.inp(name, type, desc)` | `T` (required) | — | Mandatory input data; supplied through `ainvoke(data, ...)` |
| `.mid(name, type, desc)` | `T \| UnsetType` | `UNSET` | Intermediate fields; a node reads and writes them |
| `.out(name, ...)` | — | — | Which fields to return from `ainvoke()` |

**`inp` fields** must be supplied in `ainvoke(data, box)` — if a field is missing from `data`, `MissingInputFieldError` is raised.

**`mid` fields** aren't available to an Action node until some earlier node has written them: reading an UNSET field raises `FieldNotReadyError`. During automatic mapping (`_extract_params`), an optional Params field that's UNSET is skipped — Pydantic applies the default.

**`.out()` has two modes:**
- Called before `.finish()` → a global out: the result is taken from the final state by these names.
- Called after `.finish(X)` → a per-finish out: `ainvoke()` returns the fields declared for the node X where the graph ended.

```python
# Global out — both finish nodes return the same fields:
ctrl = (
    LangGraphController()
    .inp("ticket_id", str, "Ticket ID")
    .inp("note", str, "Ticket text")
    .mid("category", str, "Category")
    .mid("resolved", bool, "Resolution flag")
    .mid("resolution_note", str, "Resolution note")
    .out("category")
    .out("resolved")
    .out("resolution_note")
    .node(ClassifyTicketAction)
    .node(EngineeringAction)
    .node(BillingAction)
    ...
    .finish(EngineeringAction)
    .finish(BillingAction)
    .build()
)
```

[▶ Example: 02_inline_graph.py](../../examples/step_14_langgraph/02_inline_graph.py) · [Notebook](../../examples/step_14_langgraph/02_inline_graph.ipynb)

---

## Nodes: an Action class and an async function

`.node()` accepts two kinds.

### An Action class

```python
ctrl.node(ClassifyTicketAction)   # node name = "ClassifyTicketAction"
```

When `ainvoke()` is called, the controller:
1. Automatically extracts `Params` from AgentState by field name (`_extract_params`).
2. Runs the Action through `box.run(ActionClass, params, connections=...)`.
3. Calls `result.model_dump()` and merges it into AgentState.

The Action doesn't know about LangGraph; it works as usual, through `box.run`.

### An async function

```python
async def enrich_ticket(state: Any) -> dict:
    """Add a system prefix to the note before classification."""
    raw_note: str = getattr(state, "note", "")
    return {"note": f"[SYSTEM] {raw_note}"}

ctrl.node(enrich_ticket, name="enrich")   # name= is mandatory for functions
```

The function receives the current `AgentState` as an object (fields are attributes) and returns a dict update. Functions **don't go through `box.run()`** — they work with state directly. `@on_error`, sagas, and aspects have no effect on them.

A graph with a function as the starting node:

```python
ctrl = (
    LangGraphController()
    .inp("note", str, "Ticket text")
    ...
    .node(enrich_ticket, name="enrich")       # register the function
    .node(ClassifyTicketAction)
    .start("enrich")                           # start from the function by name
    .edge("enrich", ClassifyTicketAction)      # an explicit edge, function → Action
    ...
    .build()
)
```

[▶ Example: 03_function_node.py](../../examples/step_14_langgraph/03_function_node.py) · [Notebook](../../examples/step_14_langgraph/03_function_node.ipynb)

---

## Topology

### .start(), .edge(), .finish()

`.start(node)` is the entry point. `.edge(src, dst)` is an unconditional edge. `.finish(node)` is a terminal node (replaces a manual `.edge(X, END)`).

```python
ctrl.start(ClassifyTicketAction).edge(ClassifyTicketAction, ResolveAction).finish(ResolveAction)
```

### .route()

A multi-way branch. `on` is a function from state to a key; `paths` maps a key to a target node. It's called after the source node has finished updating the state.

```python
ctrl.route(
    ClassifyTicketAction,
    on=lambda s: s.category,          # read from an AgentState attribute
    paths={
        "bug":     EngineeringAction,
        "feature": EngineeringAction, # several keys → one node
        "billing": BillingAction,
    },
)
```

If `on()` returns a key that's not in `paths`, `RouteKeyError` is raised at runtime, carrying the source node's name, the key that was returned, and the list of available keys.

### Build-time errors

`.build()` checks the topology and the data contract:

| Error | Cause |
|---|---|
| `NoStartNodeError` | `.start()` was never called |
| `DeadEndNodeError` | A node has no outgoing edges and isn't marked `.finish()` |
| `UnreachableNodeError` | A registered node is unreachable from start |
| `FinishUnreachableError` | There's no path from start to `.finish()` |
| `InconsistentFinishOutputError` | Per-finish mode: not every finish node has out-fields declared |
| `FieldHasNoProducerError` | A required Params field of an Action is neither an inp nor written by an earlier Action |
| `OutputHasNoProducerError` | An out field is written by no Action (only when there are no nodes with a mapper) |
| `UnexpectedResultFieldError` | An Action's Result field isn't declared in the inp/mid schema |

---

## Field mapping

By default the controller maps State → Params fields **by name**: if `Params` has a field `order_id`, it's looked up as `state.order_id`. If the names in the state differ from the names in the Action, use `params_mapper` and `response_mapper`.

### params_mapper

```python
.node(
    ClassifyTicketAction,
    params_mapper=lambda s: ClassifyParams(
        ticket_id=s.ticket_id,
        note=s.user_query,   # state.user_query → params.note
    ),
)
```

Replaces automatic extraction by name. Receives the AgentState, returns a Params instance.

### response_mapper

```python
.node(
    ClassifyTicketAction,
    response_mapper=lambda r: {"ticket_class": r.category},  # result.category → state.ticket_class
)
```

Replaces `result.model_dump()`. Receives the Result object, returns a dict or a Pydantic model.

### response_mapper=lambda r: {}

The node runs purely for a side effect and writes nothing to the state:

```python
.node(
    AuditLogAction,
    params_mapper=lambda s: AuditParams(ticket_id=s.ticket_id),
    response_mapper=lambda r: {},   # a zero update
)
```

Nodes with `params_mapper` or `response_mapper` are **excluded from static contract validation** (`FieldHasNoProducerError`, `OutputHasNoProducerError`) — you take responsibility for the mapping's correctness.

[▶ Example: 04_field_mapping.py](../../examples/step_14_langgraph/04_field_mapping.py) · [Notebook](../../examples/step_14_langgraph/04_field_mapping.ipynb)
[▶ Example: 06_field_mapping.py](../../examples/step_14_langgraph/06_field_mapping.py) · [Notebook](../../examples/step_14_langgraph/06_field_mapping.ipynb)

---

## Testing without a machine

`LangGraphController` can be tested without a running `ActionProductMachine`.

**Pattern 1 — a structural test:** `.build()` with no runtime.

```python
def test_build_validates_topology():
    ctrl = _build_graph()
    assert ctrl._built is True
```

**Pattern 2 — a stub Action:** replace the real Action with a stub carrying the same Params/Result contract.

```python
ctrl = _build_graph(classify_cls=StubClassifyAction, engineering_cls=StubEngineeringAction)
result = await ctrl.ainvoke({"ticket_id": "T-9", "note": "..."}, mock_box)
assert result["category"] == "bug"   # StubClassifyAction always → "bug"
```

**Pattern 3 — a mock box:** simulate `box.run` with an `AsyncMock`.

```python
from unittest.mock import AsyncMock, MagicMock

mock_result = MagicMock()
mock_result.model_dump.return_value = {"category": "billing"}
box = MagicMock()
box.run = AsyncMock(return_value=mock_result)

result = await ctrl.ainvoke({"ticket_id": "T-1", "note": "invoice"}, box)
assert result["category"] == "billing"
```

[▶ Example: 05_testing.py](../../examples/step_14_langgraph/05_testing.py) · [Notebook](../../examples/step_14_langgraph/05_testing.ipynb)

---

## Running through the machine

The graph runs inside a `@summary_aspect` of a host Action. The box comes from the machine.

**Option 1 — an external graph through `@connection`** (one graph for every call):

```python
ticket_graph = (
    LangGraphController()
    .inp("ticket_id", str, "Ticket ID")
    ...
    .build()
)

@meta(description="Process ticket via graph", domain=SupportDomain)
@check_roles(GuestRole)
@connection(LangGraphController, key="graph", description="Ticket graph")
class ProcessTicketAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run ticket graph")
    async def run_summary(self, params, state, box, connections):
        result = await connections["graph"].ainvoke(
            {"ticket_id": params.ticket_id, "note": params.note},
            box,
        )
        return ProcessResult(**result)

# Running it:
await machine.run(
    Context(),
    ProcessTicketAction(),
    ProcessParams(ticket_id="T-1", note="crash"),
    connections={"graph": ticket_graph},
)
```

**Option 2 — the graph is built inline** (every call rebuilds it):

```python
@summary_aspect("Run inline graph")
async def run_summary(self, params, state, box, connections):
    ctrl = (
        LangGraphController()
        .inp(...)
        ...
        .build()
    )
    result = await ctrl.ainvoke({"ticket_id": params.ticket_id, ...}, box)
    return ProcessResult(**result)
```

`.build()` and compilation are cheap — building inline is fine for most cases. Use `@connection` when one graph is needed by several Actions, or when you want the dependency declared explicitly in the class header.

[▶ Example: 01_external_connection.py](../../examples/step_14_langgraph/01_external_connection.py) · [Notebook](../../examples/step_14_langgraph/01_external_connection.ipynb)
[▶ Example: 02_inline_graph.py](../../examples/step_14_langgraph/02_inline_graph.py) · [Notebook](../../examples/step_14_langgraph/02_inline_graph.ipynb)

---

## Invariants

- **Same Action, different transport.** The Action doesn't know about LangGraph; the controller wraps it in a node through `box.run()`.
- **The state schema comes from declarations.** `AgentState` is created automatically from `.inp()/.mid()/.out()`; no manual declaration is needed.
- **Validation happens at `.build()`.** Topology and the data contract are checked statically. `MissingInputFieldError` is raised at `ainvoke()` if an inp field isn't supplied in `data`.
- **Box compiles the graph.** `.compile(box)` builds a fresh `CompiledGraph` on every `ainvoke()`; the box isn't stored on the controller.
- **A mapper opts a node out of auto-validation.** A node with `params_mapper` or `response_mapper` is excluded from the `FieldHasNoProducerError` / `OutputHasNoProducerError` checks.
- **`response_mapper=lambda r: {}`** is the explicit way to say "this node runs for a side effect."
- **Functions bypass AOA's machinery.** Async functions don't go through `box.run()`; aspects, `@on_error`, and sagas have no effect on them.
- **`ainvoke()` returns a dict.** The keys are the declared `.out()` fields.

---

## Review questions

1. How does `LangGraphController` differ from `LangGraphAdapter`? Why doesn't `AgentState` need to be declared by hand anymore?
2. How does `.inp()` differ from `.mid()`? What happens if an Action tries to read a mid field before an earlier node has written it?
3. When is `.route()`'s `on` function called — before or after the source node finishes updating the state?
4. Why is a node with `response_mapper` excluded from static validation? When does that create a risk?
5. Which testing pattern should you use if you only need to check the topology and the data contract, without running any Actions?
6. What's the difference between an external graph through `@connection` and building it inline? When should you prefer each?

> **Exercise.** In [03_function_node.py](../../examples/step_14_langgraph/03_function_node.py), replace the `enrich_ticket` function with an `EnrichAction` Action class. Confirm that `.build()` still passes. What changes in the system's behavior — which AOA mechanisms are now available for this node?

---

<table width="100%"><tr>
  <td align="left"><a href="step-14-mcp.md">← Step 14 — MCP</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-15-schema-results.md">Step 15 — Schema Results →</a></td>
</tr></table>
