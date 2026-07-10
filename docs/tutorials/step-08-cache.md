<!-- translated-from: step-08-cache_draft.md @ 2026-06-23T00:00:00Z · sha256:d555a63f9ea0 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 08 — Cache

<table width="100%"><tr>
  <td align="left"><a href="step-07-context.md">← Step 07 — Context</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-09-plugins.md">Step 09 — Plugins →</a></td>
</tr></table>

- [A layer over the pipeline](#a-layer-over-the-pipeline)
- [The cache key](#the-cache-key)
- [A cache hit](#a-cache-hit)
- [To store or not — and under which tags](#to-store-or-not--and-under-which-tags)
- [Freshness instead of TTL](#freshness-instead-of-ttl)
- [Invalidation by tags](#invalidation-by-tags)
- [Cache, errors, and include](#cache-errors-and-include)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

Cache is a strange entity. It is not business logic: the meaning of an operation does not change whether the result was taken from the cache or recomputed. But it is not passive infrastructure either: a cache changes the **execution path** — the result may return without running the pipeline at all. In ordinary code this contradiction is resolved in the worst way: the cache check, the key, the TTL, and the store access intrude right into the operation body, and the scenario gets overgrown with infrastructure.

AOA gives the cache its own place in the contract, splitting two concerns. **The operation is responsible for meaning**: which key to build, whether a particular result is worth storing, what to evict after writing. **The coordinator is responsible for policy**: where to store, how long to live, local or distributed, how to evict. The same technique as with [dependencies](step-06-dependencies.md): the operation says "what", the infrastructure — "how".

[▶ Try in Colab](https://drive.google.com/file/d/1New2yib1SQTKrnyioeI9bUJTI13xnJqN/view?usp=drive_link) · [Open in project](../../examples/step_08_cache/01_cache.py)

---

## A layer over the pipeline

The cache in AOA is built **around** the pipeline, not inside the aspect loop — so as not to mix with the saga and `@on_error`. And it is **optional**: until a coordinator is passed to the machine, there is no cache, and the operation's hooks are simply not called.

```python
machine = ActionProductMachine(cache_coordinator=CacheCoordinator())
```

An operation declares up to four hooks (all optional): `cache_key`, `on_cache_write`, `on_cache_invalidate`, and — more rarely — `read_cache`. The operation itself does not go to the coordinator; it only returns decisions, while reading, writing, and invalidating the cache is the machine's job.

## The cache key

`cache_key(params)` builds a key from the input data:

```python
class GetOrderAction(BaseAction[OrderParams, OrderResult]):

    def cache_key(self, params: OrderParams) -> str | None:
        return f"{params.order_id}"
```

Return `None` — this call does not use the cache, the pipeline runs as usual. Return a string — it becomes the **user segment** of the key (the class prefix is added by the coordinator so that different operations with identical keys do not collide). The key must be a non-empty string — a contract violation → `CacheContractError`.

> **Key safety.** For data bound to a subject, the key **must** include the corresponding scope — `user_id`, `tenant_id`, and so on. Forgetting this means serving one client another's cached answer.

## A cache hit

If there is an entry for the key — that is a **cache hit**, and the pipeline **does not run at all**: not a single aspect executes. This is visible in the example, where a "heavy" request is cached and its repeat is served from the cache:

**Run:**

```bash
uv run python examples/step_08_cache/01_cache.py
```

**Output:**

```text
Sample 06 cache — heavy request

  heavy request: tenant=acme, name=feature-flags
  on_cache_write: duration_ms=81.5, write=yes

Sample 06 cache — heavy again (cached)


Sample 06 cache — light request

  light request: tenant=acme, name=ping
  on_cache_write: duration_ms=0.2, write=no (too light)

Sample 06 cache — light again (not in cache)

  light request: tenant=acme, name=ping
  on_cache_write: duration_ms=0.1, write=no (too light)
```

The second block — "heavy again" — is empty: not a line of log, not a write hook. That is the hit: the machine returned the ready result without executing a single aspect (events for regular and summary aspects are not emitted on a hit; `global_start`/`global_finish` are always emitted). *(The `duration_ms` numbers depend on the run.)*

## To store or not — and under which tags

After a **clean** pass through the pipeline the machine asks the operation whether to store the result. The `on_cache_write` hook returns **tags** or `None`:

```python
from aoa.action_machine.runtime.cache_tag import CacheTag

class GetConfigAction(BaseAction[ConfigParams, ConfigResult]):

    async def on_cache_write(
        self, result: ConfigResult, params: ConfigParams, duration_ms: float
    ) -> list[CacheTag] | None:
        if duration_ms < 50.0:
            return None  # too fast — do not cache
        return [CacheTag(type=Config, key=params.name)]
```

`None` — do not write to the cache. A list of `CacheTag` — store the result **and index it** under those tags. The operation decides (what is worthy of the cache and how to label it), while the `put` itself is performed by the machine. In the example the "heavy" request (≈80 ms) is stored, while the "light" one (a fraction of a ms) is not.

`on_cache_write` is called **only** when `cache_key` returned a non-None key.

### What is CacheTag

`CacheTag` is a pair `(type, key)` that describes the entry's domain membership:

```python
@dataclass(frozen=True)
class CacheTag:
    type: type[Any] | None = None
    key: str | int | None = None
```

At least one field must be non-`None`. Examples:

| Constructor | Meaning |
|-------------|---------|
| `CacheTag(type=Order, key=42)` | A specific order #42 |
| `CacheTag(type=Order)` | Any order (wildcard on key) |
| `CacheTag(key=42)` | Any entity with id=42 |

## Freshness instead of TTL

The rarer hook is `read_cache(params, entry)`. By default it returns `entry.result`. But if you return `None`, the entry is considered stale: the machine invalidates the key and runs the pipeline anew. There is **no TTL** in the coordinator — "freshness" is expressed here, through `read_cache`, checking the entry's data against the current `params`. There is no single-flight either: parallel misses on one key may both run the pipeline (coalescing is a separate task).

## Invalidation by tags

Tags solve a problem that `read_cache` does not cover: **one write operation must evict the cache of several read operations**. While the cache is read and written by key, invalidation works through tags — via a reverse index inside the coordinator.

The `on_cache_invalidate(params, result)` hook is called after **every** successful pipeline pass (not on a cache hit, not on `@on_error`). It returns a list of `CacheTag` matchers or `None`:

```python
from aoa.action_machine.runtime.cache_tag import CacheTag

class UpdateOrderAction(BaseAction[UpdateOrderParams, UpdateOrderResult]):

    async def on_cache_invalidate(
        self, params: UpdateOrderParams, result: UpdateOrderResult
    ) -> list[CacheTag] | None:
        return [
            # Evict the cache for this specific order.
            # Removes entries from GetOrderAction and any other operations
            # that indexed an entry with type=Order, key=params.order_id.
            CacheTag(type=Order, key=params.order_id),
        ]
```

Matching is **wildcard-aware**: a `None` field in a matcher matches any stored value:

| Matcher | Evicts |
|---------|--------|
| `CacheTag(type=Order, key=42)` | Only entries tagged `(Order, 42)` |
| `CacheTag(type=Order)` | All entries tagged `type=Order`, regardless of key |
| `CacheTag(key=42)` | All entries tagged `key=42`, regardless of type |

The list may contain any combination of matchers.

**Ordering: invalidation before write.** `on_cache_invalidate` always runs before `on_cache_write` within the same run. This is intentional: if an operation simultaneously evicts a tag and writes a fresh entry under that same tag, "write first, then evict" would immediately remove the just-stored entry. The reversed order — "evict the stale, then write the fresh" — guarantees the new entry always survives the cycle.

> **Tags are a domain contract, not an automatic.** Invalidation only works for entries that were indexed under the relevant tags at write time. If `GetOrderAction.on_cache_write` did not include `CacheTag(type=Order, key=id)` in the tag list, `UpdateOrderAction.on_cache_invalidate` will not find that entry even if it specifies the same matcher.

## Cache, errors, and include

The cache coexists neatly with the neighboring layers, and this is visible in two rules.

**With `@on_error`.** A result returned from an [error handler](../index.md#iii-business-logic) is **not cached**. It is semantically not equal to a clean summary pass: on a repeat call the pipeline should run again (or hit the handler again), not return a "workaround" answer. The machine distinguishes these cases and writes to the cache only after a clean summary.

**With the include contract.** On a cache hit the pipeline does not run — and so neither do the nested operations declared with `UseCase.include`. Therefore, for a call served from the cache the include contract is **not checked**: the included dependencies ran in the materialization that landed in the cache, not in this call (see [Intents and invariants](../reference/intents-and-invariants.md)).

## Invariants

- **Optional.** Without a `cache_coordinator` there is no cache, the hooks are not called.
- **`cache_key`.** Returns `str | None`. `None` — the cache is not used. The key must be a non-empty string. A contract violation → `CacheContractError`.
- **A scoped key.** For subject-dependent data the key must include `user_id`/`tenant_id` — otherwise a leak between clients.
- **A hit bypasses the pipeline.** On a hit the aspects do not run; their events are not emitted.
- **`on_cache_write` — only with a non-None key.** If `cache_key` returned `None`, the hook is not called. Returns `list[CacheTag] | None`: `None` — do not write; a list of tags — write and index.
- **A result from `@on_error` is not cached.** Only a clean summary pass.
- **Freshness through `read_cache`.** There is no TTL in the coordinator; `None` from `read_cache` → invalidation and a re-run.
- **Invalidation through tags.** `on_cache_invalidate` is called after every clean pipeline (not on a hit, not on `@on_error`). Returns `list[CacheTag] | None`. Matching is wildcard-aware. Works only for entries indexed under the relevant tags at write time. Invalidation happens before the new result is written.
- **Meaning and policy are separated.** The operation decides the key, the write tags, the invalidation; the store, the size, the eviction are the coordinator's.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Your own store (for example, Redis) is wired as a [custom cache coordinator](../index.md#how-to-write-your-own-extension).

## Summary

The cache is a separate layer over the pipeline, changing the execution path but not the meaning of the operation. The operation declares only the meaning: `cache_key` (a string key, necessarily with scope), `on_cache_write` (a list of tags for indexing, or `None`), `on_cache_invalidate` (a list of `CacheTag` matchers for wildcard invalidation, or `None`), and, when needed, `read_cache` (freshness). Everything else — the store, the tag index, the eviction — is carried by the coordinator, and there is no cache until it is wired in. On a hit the pipeline does not run; the result from `@on_error` and the include contract behave predictably meanwhile.

Next — **[Plugins](../index.md#iii-business-logic)**: lifecycle observers that see all these events — start, aspects, errors, rollbacks — but do not interfere.

---

## Review questions

1. Why is the cache "neither business logic nor passive infrastructure"? What does it change?
2. How are meaning and policy split? What does the operation decide, and what the coordinator?
3. What happens on a cache hit to the aspects and their events? Why is the second "heavy" block in the output empty?
4. Why must `cache_key` include `user_id`/`tenant_id` for subject-dependent data?
5. Why is a result returned from `@on_error` not cached?
6. How is "freshness" expressed without a TTL? What does `read_cache` do when it returns `None`?
7. Why is the include contract not checked on a cache hit?
8. How does `CacheTag(type=Order)` differ from `CacheTag(type=Order, key=42)` during invalidation?
9. Why is `on_cache_invalidate` not called on a cache hit or on a result from `@on_error`?
10. What happens if `GetOrderAction.on_cache_write` did not include the tag `CacheTag(type=Order, key=id)`, but `UpdateOrderAction.on_cache_invalidate` returned the matcher `CacheTag(type=Order)`?
11. In what order do `on_cache_invalidate` and `on_cache_write` run? Why that order?

> **Exercise.** Make `GetConfigAction` cache different tenants' results independently (it already does — verify by changing `tenant_id`), then deliberately "break" key safety by removing `tenant_id` from `cache_key`, and explain exactly which cross-client leak scenario this creates. Add `UpdateConfigAction` with an `on_cache_invalidate` hook returning `[CacheTag(type=Config)]`, and verify that it evicts all config entries for all tenants at once.

---

<table width="100%"><tr>
  <td align="left"><a href="step-07-context.md">← Step 07 — Context</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-09-plugins.md">Step 09 — Plugins →</a></td>
</tr></table>
