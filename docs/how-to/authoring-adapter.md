<!-- translated-from: authoring-adapter_draft.md @ 2026-06-17T10:52:07Z · sha256:1810195d7bea -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own transport adapter

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [Step 1. The route record](#step-1-the-route-record)
- [Step 2. The adapter: registration and build](#step-2-the-adapter-registration-and-build)
- [Step 3. A single per-request pipeline](#step-3-a-single-per-request-pipeline)
- [What the base guarantees](#what-the-base-guarantees)
- [Verification](#verification)

---

## When this is needed

The distribution ships [FastAPI](../tutorials/step-13-fastapi.md) and [MCP](../tutorials/step-14-mcp.md). If you need another transport — gRPC, Kafka, a CLI, a queue — it is added with **your own adapter**, without touching the operations: the same `Action` reaches one more channel. An adapter is two small additions on top of the base: a **route record** and **the adapter itself**. Inside is the same per-request pipeline as in the shipped adapters.

The full example: [01_custom_adapter.py](../../examples/how_to/01_custom_adapter.py).

## Step 1. The route record

Subclass `BaseRouteRecord` — this is one route's contract: which operation, optional external models and mappers, per-route connections. The record is **frozen**; in `__post_init__` first call the base one (it extracts the operation's `Params`/`Result` and checks the mapper rules), then your own invariants:

```python
from dataclasses import dataclass
from aoa.action_machine.adapters.base_route_record import BaseRouteRecord

@dataclass(frozen=True)
class CommandRouteRecord(BaseRouteRecord):
    command: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.command.strip():
            raise ValueError("command must be a non-empty string.")
```

The base gives the record ready properties: `params_type`/`result_type` and `effective_request_model`/`effective_response_model` (the external model if set, otherwise `Params`/`Result`).

## Step 2. The adapter: registration and build

Subclass `BaseAdapter[YourRecord]`. The base constructor takes `machine` and `auth_coordinator` (see [below](#what-the-base-guarantees)). Add a **registration method** (it creates a record and calls `self._add_route(...)`, which returns `self` — hence the fluency) and `build()`, turning `self._routes` into your transport:

```python
from aoa.action_machine.adapters.base_adapter import BaseAdapter

class DictAdapter(BaseAdapter[CommandRouteRecord]):
    def command(self, name, action_class, *, connections=None, **mapping):
        return self._add_route(CommandRouteRecord(
            action_class=action_class, connections=connections, command=name, **mapping,
        ))

    def build(self):
        handlers = {r.command: self._make_handler(r) for r in self._routes}
        async def call(command, payload):
            return await handlers[command](payload)
        return call
```

## Step 3. A single per-request pipeline

The main thing is the handler for one call. It repeats the same path as FastAPI and MCP: validate the input → bring it to `Params` → build `Context` through the **mandatory** `auth_coordinator` → resolve connections → run the **real** machine → return the result:

```python
def _make_handler(self, record):
    async def handler(payload: dict):
        body = record.effective_request_model.model_validate(payload)      # 1. validate input
        params = record.params_mapper(body) if record.params_mapper else body  # 2. -> Params
        ensure_machine_params(params, record.params_type, adapter="Dict", route_label=record.command)
        context = await self._auth_coordinator.process(None) or Context()  # 3. Context at the boundary
        connections = resolve_connections(record.connections)              # 4. per-route connections
        result = await self._machine.run(context, record.action_class(), params, connections)  # 5. the machine
        if record.response_mapper:                                         # 6. -> external response
            mapped = record.response_mapper(result)
            return mapped.model_dump() if hasattr(mapped, "model_dump") else mapped
        return result.model_dump()
    return handler
```

`ensure_machine_params` (and the paired `ensure_protocol_response`) from `base_route_record` verify that the machine's input is really the operation's `Params`, and that the mapper's output is its external model. So schema reconciliation (`request_model`/`response_model` + mappers, see [Schema converters](../tutorials/step-18-converters.md)) and supplying [connections](../tutorials/step-17-connections.md) work in your adapter "for free".

## What the base guarantees

`BaseAdapter[R]` at creation:

- checks that `machine` is an `ActionProductMachine` (otherwise `TypeError`);
- requires `auth_coordinator` (None → `TypeError`) — authentication cannot be forgotten;
- gives access to `self._machine`, `self._auth_coordinator`, `self._graph_coordinator` (the machine's graph), and `self._routes`;
- preserves the registration order of the routes.

An adapter is tested the same way as the shipped ones: on a real `ActionProductMachine`, stubbing only `machine.run` if needed (the seam at the execution boundary), rather than rewriting the adapter logic.

## Verification

```bash
uv run python examples/how_to/01_custom_adapter.py
```

```text
call("greet", {"name": "Alice"}) -> {'message': 'Hello, Alice!'}
```

The same `GreetAction` reached a new transport — the dispatcher `call(command, payload)` — without a single edit to the operation. The models to follow are `FastApiAdapter` and `McpAdapter`: they are built on exactly this scheme. Your own `Context` coordinator at the boundary is a separate topic: [«Your own authentication coordinator»](../index.md#how-to-write-your-own-extension).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
