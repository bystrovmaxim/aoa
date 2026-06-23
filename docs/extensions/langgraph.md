<!-- translated-from: langgraph_draft.md @ 2026-06-23T17:06:01Z · sha256:8ae095db733f -->
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

`LangGraphAdapter` embeds AOA Actions into a LangGraph graph — without rewriting business logic. Build the graph through a fluent builder and get a standard `CompiledGraph` with `ainvoke()`, `astream()`, and `get_graph().draw_mermaid()`.

Installation: `pip install "aoa-langgraph-adapter"`.

## Why AOA + LangGraph together

LangGraph answers **«how to route»** — it manages flow, branching, and memory in an agent graph. AOA answers a different question: **«what it means»** — the semantics of each step (roles, checkers, connections, context).

Without AOA a LangGraph node is just a function: the graph runs it but does not know who is allowed to call it or what resources it needs. With AOA every node carries a full metadata contract: role, checker, `@connection`, `@context_requires`. Graphs are built quickly; nodes stay readable and verifiable.

## The essentials

```python
from aoa.langgraph import LangGraphAdapter
from langgraph.graph import END

compiled = (
    LangGraphAdapter(machine=machine, context=context, agentstate=AgentState)
    .node(ValidateOrderAction())        # AOA Action — name derived from class
    .node(ConfirmOrderAction())
    .node(reject_order, name="reject")  # plain async function
    .start(ValidateOrderAction)
    .conditional_edge(
        ValidateOrderAction,
        when=lambda s: s.get("valid"),
        if_true=ConfirmOrderAction,
        if_false="reject",
    )
    .edge(ConfirmOrderAction, END)
    .edge("reject", END)
    .compile()                          # → standard LangGraph CompiledGraph
)

result = await compiled.ainvoke({"order_id": "ORD-001", "valid": False, "status": ""})
```

- Node name is derived automatically: `ValidateOrderAction` → `"validate_order"`.
- `.node()` accepts an **Action instance** or a **plain `async` function** (`name=` argument required for functions).
- `.edge()`, `.conditional_edge()`, `.route()` accept an Action class, instance, or string — no magic string names.
- Referencing an unregistered node in `.edge()` / `.start()` raises `UnregisteredNodeError` immediately — topology errors surface at graph build time, not inside `ainvoke()`.
- Missing connections are caught at `.compile()` via `MissingConnectionError`: if an Action declares `@connection(DbManager, key="db")` and the pool does not contain `"db"`, the error is raised before the first run.
- The connection pool is filtered per node by declared `@connection` keys — no manual plumbing needed.
- `Params` fields are extracted from `agentstate` by name (strict: `KeyError` if a field is absent and has no default).
- `machine.run()` result is serialised via `result.model_dump()` and merged back into `agentstate`.
- `.build_graph()` returns an uncompiled `StateGraph` — add more nodes and edges with the native LangGraph API and compile yourself.

Example: [02_langgraph.py](../../examples/extensions/02_langgraph.py).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
