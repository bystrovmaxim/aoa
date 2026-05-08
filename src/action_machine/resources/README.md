# Adding a Resource Manager (SQL Stack Pattern)

Reference layout: `sql/` – protocol → concrete manager → wrapper.

## 1. Protocol

Define a `typing.Protocol` (e.g. `ProtocolSqlResource`) with the surface that aspects need: lifecycle methods, `execute`, `rollup`, `check_rollup_support`. One module, no imports of concrete managers.

```python
from typing import Any, Protocol


class ProtocolSqlResource(Protocol):
    @property
    def rollup(self) -> bool: ...

    def check_rollup_support(self) -> bool: ...

    async def open(self) -> None: ...

    async def begin(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any: ...
```

## 2. Concrete Manager

Subclass `BaseResource` and implement the protocol (e.g. `SqlResource`). Provide real behaviour (connect, transactions, queries). Implement `get_wrapper_class()` → returns the wrapper class used for nested actions.

```python
class SqlResource(BaseResource, ProtocolSqlResource):
    def __init__(self, rollup: bool = False):
        self._rollup = rollup

    @property
    def rollup(self) -> bool:
        return self._rollup

    def check_rollup_support(self) -> bool:
        return True

    def get_wrapper_class(self) -> type["BaseResource"] | None:
        return WrapperSqlResource

    async def open(self) -> None: ...

    async def begin(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def execute(self, query: str, params=None) -> Any: ...
```

## 3. Wrapper

Subclass `BaseResource` and implement the same protocol. **Do not subclass the concrete manager**. Hold an inner `Protocol…` instance; `rollup` and `check_rollup_support` delegate to it; `execute` delegates; `open` / `begin` / `commit` / `rollback` raise `TransactionProhibitedError`. `get_wrapper_class()` returns the wrapper class again for deeper nesting.

```python
class WrapperSqlResource(BaseResource, ProtocolSqlResource):
    def __init__(self, inner: ProtocolSqlResource):
        self._inner = inner

    @property
    def rollup(self) -> bool:
        return self._inner.rollup

    def check_rollup_support(self) -> bool:
        return self._inner.check_rollup_support()

    async def execute(self, query: str, params=None):
        return await self._inner.execute(query, params)

    async def open(self):
        raise TransactionProhibitedError("Opening not allowed in nested action")

    async def begin(self):
        raise TransactionProhibitedError("Begin not allowed in nested action")

    async def commit(self):
        raise TransactionProhibitedError("Commit not allowed in nested action")

    async def rollback(self):
        raise TransactionProhibitedError("Rollback not allowed in nested action")

    def get_wrapper_class(self):
        return WrapperSqlResource
```

## Why a Wrapper?

Child actions receive connections via `ToolsBox.run(..., connections)`. The runtime wraps each manager so nested code cannot start or finish transactions on the owner connection – it may only run statements. The root action owns the transaction; otherwise nested actions could commit or roll back data they do not own.

## Why Protocol + Separate Wrapper?

- **Protocol** provides a shared typed contract for both “real” and “nested” managers without inheritance between them.
- **Wrapper** is a thin proxy – no duplicated domain logic; delegation keeps rollup and execution policy on the inner manager.

## Interaction Diagram

```text
Root action:
    manager = SqlResource(rollup=False)
    connections = {"db": manager}
    await run(...)   # passes connections to child action

       │
       ▼
ToolsBox.run() wraps each manager:
    wrapped = WrapperSqlResource(manager)
    connections = {"db": wrapped}
    calls child action

       │
       ▼
Child action:
    receives connections["db"] → wrapped
    can only call wrapped.execute(...)
    wrapped.commit() → TransactionProhibitedError
    wrapped.rollup → delegated to inner manager (returns False)

       │
       ▼
If child action itself runs a deeper action:
    wrapped.get_wrapper_class() → WrapperSqlResource
    new action gets WrapperSqlResource(wrapped)
    and so on – transaction control always blocked, rollup propagated through the chain.
```

