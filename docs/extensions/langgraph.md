<!-- translated-from: langgraph_draft.md @ 2026-06-27T01:40:22Z (filesystem mtime; draft is gitignored, no git history) · sha256:80c0695cc324 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# LangGraph — Actions as nodes in an agent graph

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [Why AOA + LangGraph together](#why-aoa--langgraph-together)
- [The essentials](#the-essentials)

---

`LangGraphController` embeds an AOA Action into a LangGraph graph — without rewriting business logic. Declare the state fields, register the nodes, describe the topology, and get `ainvoke(data, box)` with full static validation at `.build()`.

Installation: `pip install "aoa-langgraph" langgraph`.

## Why AOA + LangGraph together

LangGraph answers **«how to route»** — it manages flow, branching, and memory in an agent graph. AOA answers a different question: **«what it means»** — the semantics of each step (roles, checkers, connections, context).

Without AOA a LangGraph node is just a function: the graph runs it but does not know who is allowed to call it or what resources it needs. With AOA every node carries a full metadata contract: role, checker, `@connection`, `@context_requires`. Graphs are built quickly; nodes stay readable and verifiable.

## The essentials

```python
from aoa.action_machine.context import Context
from aoa.action_machine.intents.connection import connection
from aoa.langgraph import LangGraphController

# The graph is built once at startup — no machine or context needed here.
ticket_graph = (
    LangGraphController()
    .inp("ticket_id", str, "Ticket identifier")
    .inp("note",      str, "Ticket text")
    .mid("category",        str,  "Category: bug | feature | billing")
    .mid("resolved",        bool, "Resolution flag")
    .mid("resolution_note", str,  "Resolution note")
    .out("category")
    .out("resolved")
    .out("resolution_note")
    .node(ClassifyTicketAction)
    .node(EngineeringAction)
    .node(BillingAction)
    .start(ClassifyTicketAction)
    .route(
        ClassifyTicketAction,
        on=lambda s: s.category,
        paths={
            "bug":     EngineeringAction,
            "feature": EngineeringAction,
            "billing": BillingAction,
        },
    )
    .finish(EngineeringAction)
    .finish(BillingAction)
    .build()          # validates topology and the data contract before the first run
)

# Run inside a host Action, whose @summary_aspect receives box from the machine:
@meta(description="Process a support ticket", domain=SupportDomain)
@check_roles(GuestRole)
@connection(LangGraphController, key="graph", description="Ticket-processing graph")
class ProcessTicketAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run the ticket graph")
    async def run_summary(self, params, state, box, connections):
        result = await connections["graph"].ainvoke(
            {"ticket_id": params.ticket_id, "note": params.note},
            box,          # box carries the resource pool for all Action nodes in the graph
        )
        return ProcessResult(**result)

# Pass the graph to the machine as a connection:
result = await machine.run(
    Context(),
    ProcessTicketAction(),
    ProcessParams(ticket_id="T-1", note="The app crashes on login"),
    connections={"graph": ticket_graph},
)
```

**Key points:**

- `.inp()` / `.mid()` / `.out()` — declare the state fields; an `AgentState` subclass is built automatically.
- `.node(ActionClass)` — accepts an Action **class**, not an instance; the node name is the class name.
- `.node(async_fn, name="name")` — plain async functions are also allowed; `name=` is required.
- `.build()` — validates the topology and the data contract **before the first run**.
- `ctrl.ainvoke(data, box)` — compiles a fresh LangGraph on every call; `box` is not stored on the controller.
- `params_mapper` / `response_mapper` in `.node(...)` — field renaming, when the state's names differ from the Action's Params/Result.
- `response_mapper=lambda r: {}` — the node runs for a side effect and writes nothing to the state.
- Nodes with a mapper are excluded from static contract validation.

**Errors at `.build()`:**

| Error | Cause |
|---|---|
| `NoStartNodeError` | `.start()` was not called |
| `DeadEndNodeError` | A node with no outgoing edges, not marked `.finish()` |
| `UnreachableNodeError` | A node is unreachable from start |
| `FieldHasNoProducerError` | A required Params field is not an inp and is not written by any predecessor |
| `UnexpectedResultFieldError` | A Result field is not declared in the inp/mid schema |

**Three ways to test without a machine:**

```python
# 1. Structural — topology and data contract only:
assert ctrl.build()._built is True

# 2. Stub Action — replace the real Action with a stub:
ctrl = _build_graph(classify_cls=StubClassifyAction)
result = await ctrl.ainvoke({"ticket_id": "T-1", "note": "..."}, mock_box)

# 3. Mock box — full ainvoke with a mocked box.run:
box = MagicMock()
box.run = AsyncMock(return_value=mock_result)
result = await ctrl.ainvoke({"ticket_id": "T-1", "note": "crash"}, box)
```

Tutorial: [Step 14b — LangGraph](../tutorials/step-14-langgraph.md).

Examples:
- [01_external_connection.py](../../examples/step_14_langgraph/01_external_connection.py) · [Notebook](../../examples/step_14_langgraph/01_external_connection.ipynb)
- [02_inline_graph.py](../../examples/step_14_langgraph/02_inline_graph.py) · [Notebook](../../examples/step_14_langgraph/02_inline_graph.ipynb)
- [03_function_node.py](../../examples/step_14_langgraph/03_function_node.py) · [Notebook](../../examples/step_14_langgraph/03_function_node.ipynb)
- [04_field_mapping.py](../../examples/step_14_langgraph/04_field_mapping.py) · [Notebook](../../examples/step_14_langgraph/04_field_mapping.ipynb)
- [05_testing.py](../../examples/step_14_langgraph/05_testing.py) · [Notebook](../../examples/step_14_langgraph/05_testing.ipynb)
- [06_field_mapping.py](../../examples/step_14_langgraph/06_field_mapping.py) · [Notebook](../../examples/step_14_langgraph/06_field_mapping.ipynb)

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
