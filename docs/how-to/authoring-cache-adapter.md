<!-- translated-from: authoring-cache-adapter_draft.md @ 2026-06-17T11:24:41Z · sha256:b25f0042c319 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own cache adapter

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [Two sides of the cache](#two-sides-of-the-cache)
- [The store contract: three methods](#the-store-contract-three-methods)
- [Step 1. Implement the adapter](#step-1-implement-the-adapter)
- [Step 2. Policy on the operation side](#step-2-policy-on-the-operation-side)
- [Step 3. Wiring](#step-3-wiring)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

The shipped operation cache is **in-memory** (`CacheCoordinator`, living in one machine process). To move it to Redis, Memcached, or another external store, you write your own adapter. The whole cache concept — [Step 8 — Cache](../tutorials/step-08-cache.md); here is how to wire your own store.

The full example: [05_custom_cache_adapter.py](../../examples/how_to/05_custom_cache_adapter.py).

## Two sides of the cache

The cache in AOA is split into **policy** and **storage**:

- **Policy — on the operation.** Three overridable `BaseAction` hooks decide *what* and *when* to cache. By default the cache is off (`cache_key` → `None`).
- **Storage — a coordinator injected on the machine.** This is the extension point: where the entries physically live. Your own store replaces the shipped `CacheCoordinator`.

The adapter answers only the question "where to store" — no business decisions; *what* to cache is decided by the operation.

## The store contract: three methods

There is **no** base class to subclass — the machine talks to the store by a duck-typed contract. Per run it calls exactly three async methods:

```python
async def get_entry(self, action_cls, user_key) -> CacheEntry | None    # miss -> None
async def invalidate(self, action_cls, user_key) -> bool                # drop a stale entry
async def put(self, action_cls, user_key, result, pipeline_duration_ms) -> None  # store
```

`CacheEntry` (`from aoa.action_machine.runtime.cache_entry import CacheEntry`) carries `result` and `pipeline_duration_ms` (+ access metadata). **Keys must be namespaced by the operation class** (`module.qualname`), otherwise two operations with the same short name will collide.

## Step 1. Implement the adapter

Here a plain `dict` stands in for Redis, but the interface is the same:

```python
from aoa.action_machine.runtime.cache_entry import CacheEntry

class DictCacheAdapter:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    @staticmethod
    def _key(action_cls, user_key) -> str:
        return f"{action_cls.__module__}.{action_cls.__qualname__}:{user_key}"   # namespace

    async def get_entry(self, action_cls, user_key):
        return self._store.get(self._key(action_cls, user_key))

    async def put(self, action_cls, user_key, result, pipeline_duration_ms) -> None:
        self._store[self._key(action_cls, user_key)] = CacheEntry(
            result=result, pipeline_duration_ms=pipeline_duration_ms)

    async def invalidate(self, action_cls, user_key) -> bool:
        return self._store.pop(self._key(action_cls, user_key), None) is not None
```

For Redis the body of the same three methods is `GET` / `DEL` / `SET` with serialization of `result` (for example, into JSON by the `Result` schema).

## Step 2. Policy on the operation side

The store caches nothing on its own until the operation allows it. Three `BaseAction` hooks:

```python
class QuoteAction(BaseAction[QuoteParams, QuoteResult]):
    def cache_key(self, params) -> str | None:
        return params.sku                       # None -> skip the cache for this call

    async def read_cache(self, params, entry):  # by default returns entry.result
        return entry.result                      # return None -> the entry is stale, the machine drops it

    async def on_cache_write(self, result, params, duration_ms) -> bool:
        return True                              # False by default -> do not store
```

The machine flow: with a coordinator present — `cache_key(params)`; if not `None` → `get_entry`; on a hit → `read_cache` (returns the result or `None`, then `invalidate` and a re-run); on a miss — the pipeline, then `on_cache_write` → on `True` — `put`. **Results from `@on_error` are not cached** even on `on_cache_write → True`.

## Step 3. Wiring

The adapter is injected on the machine — the cache is **opt-in**, without a coordinator the machine does not touch the store:

```python
machine = ActionProductMachine(cache_coordinator=DictCacheAdapter())
```

## What is important to know

- **A duck-typed contract, no inheritance.** Three async methods with the right signatures are enough; the shipped `CacheCoordinator`'s `clear`/`size` are management, not needed during a run.
- **Key namespacing is mandatory** (`module.qualname`) — otherwise collisions between operations.
- **Returns are validated.** `cache_key` must return `str | None` (non-empty), `read_cache` — `Result | None`, `on_cache_write` — `bool`; a violation → `CacheContractError`. An exception from a hook or a store method surfaces outward, it is not swallowed.
- **v1 has no TTL and no single-flight.** Staleness is expressed via `read_cache → None`; simultaneous misses on one key may run the pipeline several times. TTL is the logic of *your* adapter (Redis `EX`).

## Verification

```bash
uv run python examples/how_to/05_custom_cache_adapter.py
```

```text
quote('ABC') -> 30.0
quote('ABC') -> 30.0
quote('XYZW') -> 40.0
pipeline executions: ['ABC', 'XYZW']
cache size: 2
```

The second `quote('ABC')` is a hit: the machine took the result from the adapter and **did not run the pipeline** (there is no second `ABC` in `executions`). The whole cache concept, with review questions — [Step 8 — Cache](../tutorials/step-08-cache.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
