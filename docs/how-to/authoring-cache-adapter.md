<!-- translated-from: authoring-cache-adapter_draft.md @ 2026-06-23T00:00:00Z · sha256:0b76f288401b -->
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
- [The store contract: four methods](#the-store-contract-four-methods)
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

- **Policy — on the operation.** Four overridable `BaseAction` hooks decide *what* and *when* to cache. By default the cache is off (`cache_key` → `None`).
- **Storage — a coordinator injected on the machine.** This is the extension point: where the entries physically live. Your own store replaces the shipped `CacheCoordinator`.

The adapter answers only the question "where to store" — no business decisions; *what* to cache is decided by the operation.

## The store contract: four methods

There is **no** base class to subclass — the machine talks to the store by a duck-typed contract. Per run it calls exactly four async methods:

```python
async def get_entry(self, action_cls, user_key) -> CacheEntry | None
async def invalidate(self, action_cls, user_key) -> bool
async def put(self, action_cls, user_key, result, pipeline_duration_ms,
              tags: list[CacheTag] | None = None) -> None
async def evict_by_tags(self, directive_tags: frozenset[CacheTag]) -> int
```

`CacheEntry` (`from aoa.action_machine.runtime.cache_entry import CacheEntry`) carries `result` and `pipeline_duration_ms` (+ access metadata). `CacheTag` (`from aoa.action_machine.runtime.cache_tag import CacheTag`) is a typed tag for indexing and invalidation. **Keys must be namespaced by the operation class** (`module.qualname`), otherwise two operations with the same short name will collide.

## Step 1. Implement the adapter

Here a plain `dict` stands in for Redis, but the interface is the same:

```python
from collections import defaultdict
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag

class DictCacheAdapter:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._tag_to_keys: defaultdict[CacheTag, set[str]] = defaultdict(set)
        self._key_to_tags: dict[str, set[CacheTag]] = {}

    @staticmethod
    def _key(action_cls, user_key) -> str:
        return f"{action_cls.__module__}.{action_cls.__qualname__}:{user_key}"

    async def get_entry(self, action_cls, user_key):
        return self._store.get(self._key(action_cls, user_key))

    async def put(self, action_cls, user_key, result, pipeline_duration_ms,
                  tags=None) -> None:
        k = self._key(action_cls, user_key)
        self._store[k] = CacheEntry(result=result, pipeline_duration_ms=pipeline_duration_ms)
        if tags:
            self._key_to_tags[k] = set(tags)
            for tag in tags:
                self._tag_to_keys[tag].add(k)

    async def invalidate(self, action_cls, user_key) -> bool:
        k = self._key(action_cls, user_key)
        if k in self._store:
            del self._store[k]
            for tag in self._key_to_tags.pop(k, set()):
                self._tag_to_keys[tag].discard(k)
            return True
        return False

    async def evict_by_tags(self, directive_tags) -> int:
        # Wildcard matching: CacheTag(type=T) matches any stored tag with type T.
        candidates: set[str] = set()
        for stored_tag, keys in list(self._tag_to_keys.items()):
            for d in directive_tags:
                type_ok = d.type is None or d.type is stored_tag.type
                key_ok = d.key is None or d.key == stored_tag.key
                if type_ok and key_ok:
                    candidates.update(keys)
                    break
        for k in candidates:
            del self._store[k]
            for tag in self._key_to_tags.pop(k, set()):
                self._tag_to_keys[tag].discard(k)
        return len(candidates)
```

For Redis the body of the same methods is `GET` / `DEL` / `SET` with a tag index (for example, Redis Sets: tag → set of keys).

## Step 2. Policy on the operation side

The store caches nothing on its own until the operation allows it. Four `BaseAction` hooks:

```python
from aoa.action_machine.runtime.cache_tag import CacheTag

class QuoteAction(BaseAction[QuoteParams, QuoteResult]):
    def cache_key(self, params) -> str | None:
        return params.sku                        # None -> skip the cache for this call

    async def read_cache(self, params, entry):   # by default returns entry.result
        return entry.result                      # None -> entry is stale, machine drops it

    async def on_cache_write(self, result, params, duration_ms) -> list[CacheTag] | None:
        return [CacheTag(type=Quote, key=params.sku)]  # None -> do not store

    async def on_cache_invalidate(self, params, result) -> list[CacheTag] | None:
        return None                              # by default — invalidate nothing
```

The `on_cache_write` hook returns **tags** (not a `bool`): `None` — do not write; a list of `CacheTag` — store the result and index it under those tags. The `on_cache_invalidate` hook is called after **every** clean pipeline regardless of `cache_key` — including write operations that do not cache themselves but must evict the cache of read operations.

Machine flow: with a coordinator present — `cache_key(params)`; if not `None` → `get_entry`; on a hit → `read_cache`; on a miss — the pipeline → `on_cache_invalidate` → `evict_by_tags` → `on_cache_write` → `put`. **Results from `@on_error` are not cached.**

## Step 3. Wiring

The adapter is injected on the machine — the cache is **opt-in**, without a coordinator the machine does not touch the store:

```python
machine = ActionProductMachine(cache_coordinator=DictCacheAdapter())
```

## What is important to know

- **A duck-typed contract, no inheritance.** Four async methods with the right signatures are enough; the shipped `CacheCoordinator`'s `clear`/`size` are management, not needed during a run.
- **Key namespacing is mandatory** (`module.qualname`) — otherwise collisions between operations.
- **Returns are validated.** `cache_key` → `str | None` (non-empty); `read_cache` → `Result | None`; `on_cache_write` → `list[CacheTag] | None`; `on_cache_invalidate` → `list[CacheTag] | None`; a violation → `CacheContractError`. An exception from a hook or a store method surfaces outward, it is not swallowed.
- **Tags are a domain contract.** `evict_by_tags` removes only entries that were indexed under the relevant tags when `put` was called. If a tag was not passed at write time — it cannot be found at invalidation time.
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
