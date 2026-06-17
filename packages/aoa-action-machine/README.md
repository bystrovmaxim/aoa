<!-- translated-from: README_draft.md @ 2026-06-16T20:27:18Z · sha256:ec21e89dbb83 -->
<p align="center">
  <img src="../../docs/assets/aoa-logo.png" alt="AOA" width="540"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <img src="https://img.shields.io/badge/pip-aoa--action--machine-blue?logo=pypi&logoColor=white" alt="aoa-action-machine">
</p>

# aoa-action-machine

The core of AOA — a framework where a business operation is described as an **executable contract**. Every operation is an `Action` class with a typed input, output, and a straight chain of steps; the machine reads this description and executes it literally.

This README is a quick start: from installation to an operation published over HTTP and as an AI-agent tool. It deliberately does not cover everything — the full picture is in the **[tutorial](../../docs/index.md)**, with links to individual topics placed along the way.

---

## Installation

```bash
pip install aoa-action-machine
```

Optional extensions are installed as needed:

```bash
pip install "aoa-action-machine[fastapi]"   # HTTP API
pip install "aoa-action-machine[mcp]"        # tools for AI agents
pip install "aoa-action-machine[postgres]"   # asyncpg connections
pip install "aoa-action-machine[ocel]"       # OCEL 2.0 event log
```

---

## Your first action

An operation is an atomic business operation. Let us assemble the simplest one: it takes a name and returns a greeting. Three declarations are mandatory: the domain (`@meta`), access (`@check_roles`), and a single exit point (`@summary_aspect`).

```python
from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from pydantic import Field


class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greeting domain"


class GreetParams(BaseParams):
    name: str = Field(description="Recipient name")


class GreetResult(BaseResult):
    message: str = Field(description="The assembled greeting")


@meta(description="Greet by name", domain=GreetingDomain)
@check_roles(NoneRole)            # NoneRole — the operation is open to everyone (declared explicitly)
class GreetAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Assemble the greeting")
    async def greet_summary(self, params, state, box, connections):
        return GreetResult(message=f"Hello, {params.name}!")
```

`BaseParams` and `BaseResult` are Pydantic models; field descriptions go into the external schema. Inside the operation there is no state — everything arrives through `params`.

---

## Running it

The single entry point is `ActionProductMachine`. It reads the declarations and guides the operation along the pipeline.

```python
import asyncio

async def main() -> None:
    machine = ActionProductMachine()
    result = await machine.run(Context(), GreetAction(), GreetParams(name="Alice"))
    print(result.message)   # Hello, Alice!

asyncio.run(main())
```

`Context()` is the call environment (user, roles, metadata); here it is empty.

---

## Several steps and the `state` contract

Usually an operation consists of several steps. An intermediate step — `@regular_aspect` — returns a `dict` that becomes the new `state`. A checker `@result_*` declares the contract: what must appear in `state` after the step.

```python
from aoa.action_machine.intents.aspects import regular_aspect
from aoa.action_machine.intents.checkers import result_string

@meta(description="Greet by name", domain=GreetingDomain)
@check_roles(NoneRole)
class GreetAction(BaseAction[GreetParams, GreetResult]):

    @regular_aspect("Normalise the name")
    @result_string("name", required=True, min_length=1)
    async def normalise_aspect(self, params, state, box, connections):
        return {"name": params.name.strip().title()}

    @summary_aspect("Assemble the greeting")
    async def greet_summary(self, params, state, box, connections):
        return GreetResult(message=f"Hello, {state['name']}!")
```

Aspects run strictly top to bottom. If a step does not fulfil the checker's contract, the machine stops the pipeline at its boundary — the next step does not run. In detail — in the tutorial: **[Action and pipeline](../../docs/tutorials/step-01-action-and-pipeline.md)** and **[State: an x-ray of the operation](../../docs/tutorials/step-02-state-as-x-ray.md)**.

---

## Dependencies and logs

Everything external is declared by the operation in its header via `@depends` and obtained through `box.resolve(...)`; the machine will not hand out an undeclared dependency. Business events are written through `box`, not `print`:

```python
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.logging import Channel

@meta(description="Greet by name", domain=GreetingDomain)
@check_roles(NoneRole)
@depends(GreeterService)
class GreetAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Assemble the greeting")
    async def greet_summary(self, params, state, box, connections):
        greeter = await box.resolve(GreeterService)
        await box.info(Channel.business, "greeting name={%var.name|cyan}", name=params.name)
        return GreetResult(message=greeter.greet(params.name))
```

Where to deliver events — console, queue, Telegram — is decided by the machine's logger, not by the operation code.

---

## Service: FastAPI and MCP

The operation knows nothing about transport, so the same `GreetAction` can be exposed both over HTTP and as an AI-agent tool — by adding an adapter. The business code does not change.

**HTTP (FastAPI):**

```python
from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.auth import NoAuthCoordinator

machine = ActionProductMachine()

app = (
    FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(), title="Greetings API")
    .post("/greet", GreetAction, tags=["greetings"])
    .build()
)
# uvicorn app:app
```

`FastApiAdapter` publishes the operation as a REST endpoint with a ready-made OpenAPI schema derived from `Params`/`Result`.

**MCP (AI agents):**

```python
from aoa.action_machine.adapters.mcp import McpAdapter
from aoa.action_machine.auth import NoAuthCoordinator

server = (
    McpAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(), server_name="Greetings MCP")
    .tool("greetings.greet", GreetAction)
    .build()
)
# python mcp_server.py
```

The detailed chapters: **[Step 13 — FastAPI adapter](../../docs/tutorials/step-13-fastapi.md)** · **[Step 14 — MCP adapter](../../docs/tutorials/step-14-mcp.md)**.

---

## What's next

That was the quick start. **The full tutorial is on the [Contents](../../docs/index.md) page:** it leads from the first operation to the service layer and the domain model, with examples and review questions.

Useful by topic:

- **[Action and pipeline](../../docs/tutorials/step-01-action-and-pipeline.md)** · **[State: an x-ray of the operation](../../docs/tutorials/step-02-state-as-x-ray.md)** — the core of the model.
- Sagas and compensations, error handling, context, cache, plugins — [the «Business logic» part](../../docs/index.md#ii-business-logic) *(in progress)*.
- **[Action, aspect, or resource](../../docs/how-to/choosing-action-aspect-resource.md)** · **[Migrating a legacy codebase to AOA](../../docs/how-to/migrating-legacy.md)** — practical decisions.
- **[Glossary](../../docs/reference/glossary.md)** · **[Comparison with other frameworks](../../docs/explanation/comparison.md)** · **[FAQ](../../docs/reference/faq.md)**.

---

## License

[MIT](../../LICENSE)
