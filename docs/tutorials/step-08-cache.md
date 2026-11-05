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
- [Four declarations](#four-declarations)
- [The cache key](#the-cache-key)
- [A cache hit](#a-cache-hit)
- [To store or not — and under which tags](#to-store-or-not--and-under-which-tags)
- [Freshness instead of TTL](#freshness-instead-of-ttl)
- [Invalidation by tags](#invalidation-by-tags)
- [No declaration without an effect](#no-declaration-without-an-effect)
- [A collection, entity by entity](#a-collection-entity-by-entity)
- [The cache in the graph](#the-cache-in-the-graph)
- [Cache, errors, and include](#cache-errors-and-include)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

Cache is a strange entity. It is not business logic: the meaning of an operation does not change whether the result was taken from the cache or recomputed. But it is not passive infrastructure either: a cache changes the **execution path** — the result may return without running the pipeline at all. In ordinary code this contradiction is resolved in the worst way: the cache check, the key, the TTL, and the store access intrude right into the operation body, and the scenario gets overgrown with infrastructure.

AOA gives the cache its own place in the contract, splitting two concerns. **The operation is responsible for meaning**: which key to build, whether a particular result is worth storing, what to evict after writing. **The coordinator is responsible for policy**: where to store, how long to live, local or distributed, how to evict. The same technique as with [dependencies](step-06-dependencies.md): the operation says "what", the infrastructure — "how".

[▶ Try in Colab](https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/examples/step_08_cache/01_cache.ipynb) · [Open in project](../../examples/step_08_cache/01_cache.py)

---

## A layer over the pipeline

The cache in AOA is built **around** the pipeline, not inside the aspect loop — so as not to mix with the saga and `@on_error`. And it is **optional**: until a coordinator is passed to the machine, there is no cache, and the operation's declarations are simply not called.

```python
# Fragment: its imports are left out.
machine = ActionProductMachine(cache_coordinator=CacheCoordinator())
```

## Four declarations

An operation says what it caches with up to four declarations, built like its [object check](step-03-authorization-and-roles.md): `@cache_key`, `@cache_write`, `@cache_invalidate` and, more rarely, `@cache_read`. The operation itself does not go to the coordinator; it only returns decisions, while reading, writing and invalidating the cache is the machine's job.

Each declaration follows the same rules:

- its first argument is a non-empty description of what it decides;
- it sits on an `async def` whose name ends with its kind: `…_cache_key`, `…_cache_read`, `…_cache_write`, `…_cache_invalidate`;
- its parameters start as every declaration's do — `self, params, box, connections` — then take what only this kind has, then `ctx` when `@context_requires` sits under it:

| Declaration | Parameters, in this order | Returns |
| --- | --- | --- |
| `@cache_key` | `self, params, box, connections` (+ `ctx`) | `str \| None` |
| `@cache_read` | `self, params, box, connections, entry` (+ `ctx`) | `Result \| None` |
| `@cache_write` | `self, params, box, connections, result, duration_ms` (+ `ctx`) | `list[CacheTag] \| None` |
| `@cache_invalidate` | `self, params, box, connections, result` (+ `ctx`) | `list[CacheTag] \| None` |

- names, order and annotations are checked when the class body runs, their types when the graph is assembled;
- an operation declares at most one of each kind, and declarations are not inherited: a subclass caches only what it declares itself.

`BaseAction` has no cache methods. A method under an old hook name — `cache_key`, `read_cache`, `on_cache_write`, `on_cache_invalidate` — would never be called, so it is refused when the class is created, with the declaration that replaces it:

```text
DeclarationStructureError: GetConfigAction.cache_key is a cache hook the machine no longer calls. Declare it with @cache_key("...") on an async method whose name ends with '_cache_key'.
```

## The cache key

`@cache_key` builds a key from the input data:

```python
# Fragment: its imports are left out.
class GetConfigAction(BaseAction[ConfigParams, ConfigResult]):
    @cache_key("Config by tenant and name")
    async def config_cache_key(self, params: ConfigParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"{params.tenant_id}:{params.name}"
```

Return `None` — this call does not use the cache, the pipeline runs as usual. Return a string — it becomes the **user segment** of the key (the class prefix is added by the coordinator so that different operations with identical keys do not collide). The key must be a non-empty string — a contract violation → `CacheContractError`.

> **Key safety.** For data bound to a subject, the key **must** include the corresponding scope — `user_id`, `tenant_id`, and so on. Forgetting this means serving one client another's cached answer. When the scope lives in the context, ask for it: `@context_requires("user.user_id")` under `@cache_key` hands the key a `ctx` view with exactly that value.

The key is computed on **every** call, hits included, so whatever it does through `connections` every hit pays for. Keep it cheap; a freshness check belongs in `@cache_read`.

## A cache hit

If there is an entry for the key — that is a **cache hit**, and the pipeline **does not run at all**: not a single aspect executes. This is visible in the example, where a "heavy" request is cached, its repeat is served from the cache, and an update drops it:

**Run:**

```bash
uv run python examples/step_08_cache/01_cache.py
```

**Output:**

```text
Sample 06 cache — heavy request

  heavy request: tenant=acme, name=feature-flags
  config_cache_write: duration_ms=82.4, write=yes

Sample 06 cache — heavy again (cached)


Sample 06 cache — light request

  light request: tenant=acme, name=ping
  config_cache_write: duration_ms=0.2, write=no (too light)

Sample 06 cache — light again (not in cache)

  light request: tenant=acme, name=ping
  config_cache_write: duration_ms=0.2, write=no (too light)

Sample 06 cache — set the heavy value (drops it)

  config_cache_invalidate: drop acme:feature-flags

Sample 06 cache — heavy again (runs, cached anew)

  heavy request: tenant=acme, name=feature-flags
  config_cache_write: duration_ms=83.0, write=yes
```

The second block — "heavy again" — is empty: not a line of log, not a write. That is the hit: the machine read the stored result without executing a single aspect (events for regular and summary aspects are not emitted on a hit; `global_start`/`global_finish` are always emitted). The last two blocks are the invalidation: `SetConfigAction` drops the entry, and the next read runs and stores it again. *(The `duration_ms` numbers depend on the run.)*

### What the store keeps

The store keeps the Result's **JSON**, not the Result: on a write the machine hands it `model_dump_json()` in UTF-8, and on every hit it reads those bytes back into a **new** Result with the operation's Result type. So a caller that changes the Result it received changes nothing another caller gets, and a store that keeps bytes, such as Redis, can be plugged in ([your own store](../how-to/authoring-cache-adapter.md)). `@cache_read` receives that new Result in `entry.result`, with the stored entry's metadata.

Because a hit must return what the miss returned, a write first reads the Result back from its own JSON and compares the two — values, loaded fields, loaded relations, declared objects. A Result that cannot survive that is refused at the write, and nothing is stored:

```text
CacheSerializationError: FloorAction.Result cannot be cached: field 'count' reads back as 20, but was 29.
```

The same error names a field with no JSON form (`field 'data' has no JSON form (...)`) and a field whose JSON its own type refuses (`field 'count' does not read back from its own JSON ('2 items': int_parsing)`). It is a `CacheContractError`. And an entry whose bytes the current Result type no longer reads — written by an earlier version of the code into a store that outlived a deploy — is treated as stale: the key is dropped and the pipeline runs.

## To store or not — and under which tags

After a **clean** pass through the pipeline the machine asks the operation whether to store the result. `@cache_write` returns **tags** or `None`, and names in `tags=(...)` the entity types its tags may carry:

```python
# Fragment: its imports are left out.
from aoa.action_machine.runtime.cache_tag import CacheTag

class GetConfigAction(BaseAction[ConfigParams, ConfigResult]):
    @cache_write("Keep only heavy runs", tags=(ConfigCoreEntity,))
    async def config_cache_write(
        self, params: ConfigParams, box: ToolsBox, connections: Connections, result: ConfigResult, duration_ms: float
    ) -> list[CacheTag] | None:
        if duration_ms < 50.0:
            return None  # too fast — do not cache
        return [CacheTag(type=ConfigCoreEntity, key=f"{params.tenant_id}:{params.name}")]
```

`None` — do not write to the cache. A list of `CacheTag` — store the result **and index it** under those tags. The operation decides (what is worthy of the cache and how to label it), while the `put` itself is performed by the machine. In the example the "heavy" request (≈80 ms) is stored, while the "light" one (a fraction of a ms) is not.

`@cache_write` is called **only** when the key was not `None`.

### What is CacheTag

`CacheTag` is a pair `(type, key)` that describes the entry's domain membership: the **type** is an entity class, declared in the decorator; the **key** is known only during the call, so the method returns it.

| Constructor | Meaning |
|-------------|---------|
| `CacheTag(type=Order, key=42)` | A specific order #42 |
| `CacheTag(type=Order)` | Any order (wildcard on key) |

A declaration may return only tags of the types it declared. A tag of another type, or a tag without a type — which used to match entries of every type — fails the call, naming the action, the method and the tag. Here the write of `GetConfigAction` forgot the type:

```text
CacheContractError: GetConfigAction.config_cache_write returned CacheTag(type=None, key='acme:feature-flags'), which has no type; a tag names one of its declared types (ConfigCoreEntity), so the graph can show what it touches.
```

## Freshness instead of TTL

The rarer declaration is `@cache_read`, which receives the stored `entry`. Without it, a hit returns `entry.result`. If it returns `None`, the entry is considered stale: the machine invalidates the key and runs the pipeline anew. There is **no TTL** in the coordinator — "freshness" is expressed here, by checking the entry against the current `params`, or cheaply asking a resource through `connections` whether the data changed after the write. There is no single-flight either: parallel misses on one key may both run the pipeline (coalescing is a separate task).

## Invalidation by tags

Tags solve a problem that `@cache_read` does not cover: **one write operation must evict the cache of several read operations**. While the cache is read and written by key, invalidation works through tags — via a reverse index inside the coordinator.

`@cache_invalidate` is called after **every** successful pipeline pass (not on a cache hit, not on `@on_error`). It names the entity types it drops — at least one — and returns a list of `CacheTag` matchers or `None`:

```python
# Fragment: its imports are left out.
class SetConfigAction(BaseAction[ConfigParams, ConfigResult]):
    @cache_invalidate("Drop the changed value", tags=(ConfigCoreEntity,))
    async def config_cache_invalidate(
        self, params: ConfigParams, box: ToolsBox, connections: Connections, result: ConfigResult
    ) -> list[CacheTag] | None:
        # Removes the entries of GetConfigAction and of any other operation
        # that indexed an entry with type=ConfigCoreEntity and this key.
        return [CacheTag(type=ConfigCoreEntity, key=f"{params.tenant_id}:{params.name}")]
```

Matching is **wildcard-aware**: a `None` key in a matcher matches any stored key:

| Matcher | Evicts |
|---------|--------|
| `CacheTag(type=Order, key=42)` | Only entries tagged `(Order, 42)` |
| `CacheTag(type=Order)` | All entries tagged `type=Order`, regardless of key |

**Ordering: invalidation before write.** `@cache_invalidate` always runs before `@cache_write` within the same run. If an operation simultaneously evicts a tag and writes a fresh entry under that same tag, "write first, then evict" would immediately remove the just-stored entry. The reversed order — "evict the stale, then write the fresh" — guarantees the new entry always survives the cycle.

> **Tags are a domain contract.** Invalidation only works for entries that were indexed under the relevant tags at write time: if `GetConfigAction`'s write did not tag its entry with `ConfigCoreEntity`, `SetConfigAction` would not find it even with the same matcher. The graph build checks the types (see below); the keys are yours.

## No declaration without an effect

A declaration that can never do anything is refused, at the earliest moment that can see it.

**A key and a write come together.** A key without a write never stores anything — the author thinks the cache is on, and the operation runs every time. A write without a key is never called; a read without both never has anything to read. Each is refused when the class is created:

```text
DeclarationStructureError: KeyOnlyAction declares @cache_key without @cache_write; a key without a write never stores anything.
```

`@cache_invalidate` may stand alone: `SetConfigAction` drops what others cached and caches nothing itself.

**Every type cached is one some action drops, and the other way round.** The graph build compares the tag types of every operation:

- a **dead invalidation** — a type in an `@cache_invalidate` that no `@cache_write` names — is refused: `DropInvoiceAction drops InvoiceCoreEntity, but no action caches it.`
- a **dead tag** — a type in an `@cache_write` that no `@cache_invalidate` names — is refused too: nothing will ever tell its entries they are stale.

The check sees one graph, which is one service. While a cache store belongs to one service, as it does today, it is exact; a store shared by several services could be invalidated from outside, and these rules would then need the graph of all of them.

## A collection, entity by entity

[▶ Try in Colab](https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/examples/step_08_cache/02_entity_by_entity.ipynb) · [Open in project](../../examples/step_08_cache/02_entity_by_entity.py)

A whole entry keeps full copies of the entities inside it. Two operations that return the same order keep two copies, and changing that order drops both entries — the whole list too, although the other orders did not change. A write can instead store its Result **entity by entity**: every entity once, under a key of its own, and an entry for the call that lists the keys — like a card in a library catalogue that lists shelf numbers, not books.

```python
# Fragment: its imports are left out.
class ListOrdersAction(BaseAction[CustomerIdParams, OrderListResult]):
    @cache_key("Orders of a customer")
    async def orders_cache_key(self, params: CustomerIdParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"a:customer:{params.customer_id}"

    @cache_entity_key("One order of the list, as a row")
    async def order_cache_entity_key(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, entity: OrderCoreEntity
    ) -> str:
        return f"a:order:{entity.id}:row"

    @cache_write("Keep the list order by order", tags=(CustomerCoreEntity,), layout=CacheLayout.ENTITIES)
    async def orders_cache_write(
        self, params: CustomerIdParams, box: ToolsBox, connections: Connections, result: OrderListResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=CustomerCoreEntity, key=params.customer_id)]
```

The key still names the **question** — "the orders of customer `c1`" — and reads nothing. On a miss the pipeline runs; the machine calls `@cache_entity_key` for every entity of the Result, stores each under its key, tagged with its type and id, and stores under the call's key those keys and the Result's other fields. On a hit it reads the entries — all of them in one call to the store — and assembles the Result; the pipeline does not run. `GetOrderAction` builds the same key for an order, so the two operations share one entry of it:

```bash
uv run python examples/step_08_cache/02_entity_by_entity.py
```

```text
1) The list and both orders
   list: [('o1', 10.0), ('o2', 20.0)] | o1: 10.0 | o2: 20.0
   entries: 5 | runs: {'ListOrdersAction': 1, 'GetOrderAction': 2}
   a:customer:c1 -> {'fields': {'total_count': 2}, 'entities': {'orders': ['a:order:o1:row', 'a:order:o2:row']}}
   a:order:o1:row -> {'id': 'o1', 'total': 10.0}
2) UpdateOrderAction(o1) drops the entry of o1 alone
   o2: 20.0 | runs: {'ListOrdersAction': 1, 'GetOrderAction': 2}
   list: [('o1', 11.0), ('o2', 20.0)] | o1: 11.0 | runs: {'ListOrdersAction': 2, 'GetOrderAction': 2}
3) CreateOrderAction drops the customer's list
   list: [('o1', 11.0), ('o2', 20.0), ('o3', 30.0)] | runs: {'ListOrdersAction': 3, 'GetOrderAction': 2}
```

Five entries, not six: `o1` is one entry for both operations. Changing `o1` drops `(OrderCoreEntity, "o1")` — that entry alone — so `GetOrderAction(o2)` keeps hitting. The list misses once and writes `o1` again, and `GetOrderAction(o1)` then hits on what the list wrote.

**A missing entity is a miss.** When an entity the list names is gone, the list entry is dropped and the pipeline runs whole: never a shorter list, never part of a cached Result, and `@cache_read` is called only when every entity is present. An entity entry of a form the reader cannot accept — a partial order where a full one is required — does not read back, and is a miss too.

**The members of a list change too.** A new order breaks no entity entry; it changes the card. That is what the write's own tags are for: here `(CustomerCoreEntity, "c1")`, "this list belongs to customer `c1`", which `CreateOrderAction` drops. If nobody dropped it, the graph build would refuse the tag as dead — nothing would ever tell this list a new order exists.

**The key is the action's code.** Two operations that build the same key share an entry, different keys keep different ones; the machine neither builds nor checks keys. So the key of an entity must tell apart everything that changes what a reader sees: the loaded fields (`…:row` for a partial order, `…:full` for a full one), **the loaded relations** — an order with its customer loaded and one with only the customer's id must not share a key, or a reader may get `RelationNotLoadedError` — the tenant, and a role that hides a value. An invalidation by `(OrderCoreEntity, "o1")` also drops `o1` of another tenant with the same id: one extra miss there, never a leak.

The rules of the mode: `layout=CacheLayout.ENTITIES` and `@cache_entity_key` come together or not at all (refused when the class is created); the Result needs a field typed by an entity — bare, `| None` or `list[...]` — and each such entity an `id` (refused when the graph is built); `@cache_entity_key` takes `self, params, box, connections, entity` (+ `ctx`) and returns a `str`. The entity types a write stores this way count as types it caches, for the graph and for the dead-tag check.

## The cache in the graph

Each declaration is a `Cache` node of its operation, with its kind and description, reached by an edge named after it (`@cache_key`, …, `@cache_entity_key`). Two more edges go from the operation to entities: `caches` for every type its write caches — its tags and, entity by entity, the entity types it stores — and `invalidates` for every tag type of its invalidation. So [Maxitor](https://github.com/bystrovmaxim/gnomon/blob/main/packages/maxitor/README.md) can show that `SetConfigAction` drops what `GetConfigAction` caches. These words are versions 1.4 and 1.5 of the graph protocol.

## Cache, errors, and include

The cache coexists neatly with the neighboring layers, and this is visible in two rules.

**With `@on_error`.** A result returned from an [error handler](../index.md#iii-business-logic) is **not cached** and triggers no invalidation. It is semantically not equal to a clean summary pass: on a repeat call the pipeline should run again (or hit the handler again), not return a "workaround" answer.

**With the include contract.** On a cache hit the pipeline does not run — and so neither do the nested operations declared with `UseCase.include`. Therefore, for a call served from the cache the include contract is **not checked**: the included dependencies ran in the materialization that landed in the cache, not in this call (see [Intents and invariants](../reference/intents-and-invariants.md)).

## Invariants

- **Optional.** Without a `cache_coordinator` there is no cache, the declarations are not called.
- **Declared, like the object check.** A description, a suffixed `async` method, a fixed signature starting with `self, params, box, connections`; at most one of each kind; never inherited. An old hook name is refused at class creation.
- **`@cache_key`.** Returns `str | None`. `None` — the cache is not used. The key must be a non-empty string. A contract violation → `CacheContractError`. It runs on every call, hits included.
- **A scoped key.** For subject-dependent data the key must include `user_id`/`tenant_id` — otherwise a leak between clients.
- **A key and a write together.** Each alone is refused at class creation; a read only with both; an invalidation may stand alone.
- **A hit bypasses the pipeline.** On a hit the aspects do not run; their events are not emitted.
- **The store keeps JSON.** A write stores the Result's JSON after reading it back to the same observable state (`CacheSerializationError` otherwise); every hit is a new Result read from it; an entry that no longer reads is stale.
- **`@cache_write` — only with a non-None key.** Returns `list[CacheTag] | None`: `None` — do not write; a list of tags — write and index.
- **Tag types are declared.** `tags=(...)` names entity classes; a returned tag of another type, or without a type, → `CacheContractError`.
- **A result from `@on_error` is not cached.** Only a clean summary pass.
- **Freshness through `@cache_read`.** There is no TTL in the coordinator; `None` from it → invalidation and a re-run.
- **Invalidation through tags.** `@cache_invalidate` is called after every clean pipeline (not on a hit, not on `@on_error`), before the write. Matching is wildcard-aware on the key.
- **No dead invalidation, no dead tag.** The graph build refuses a type dropped and never cached, and a type cached and never dropped.
- **Entity by entity on request.** `layout=CacheLayout.ENTITIES` with `@cache_entity_key` stores each entity once under the operation's key for it; a missing or unreadable entity is a miss; the keys are the operation's, and must tell apart loaded fields, loaded relations, the tenant and the role.
- **Meaning and policy are separated.** The operation decides the key, the write tags, the invalidation; the store, the size, the eviction are the coordinator's.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Your own store (for example, Redis) is wired as a [custom cache coordinator](../how-to/authoring-cache-adapter.md).

## Summary

The cache is a separate layer over the pipeline, changing the execution path but not the meaning of the operation. The operation declares only the meaning: `@cache_key` (a string key, necessarily with scope), `@cache_write` (tags of declared entity types, or `None`), `@cache_invalidate` (the entity types it drops), and, when needed, `@cache_read` (freshness). A declaration that can have no effect is refused — at class creation or at graph build — and the graph shows what each operation caches and drops. Everything else — the store, the tag index, the eviction — is carried by the coordinator, and there is no cache until it is wired in.

Next — **[Plugins](../index.md#iii-business-logic)**: lifecycle observers that see all these events — start, aspects, errors, rollbacks — but do not interfere.

---

## Review questions

1. Why is the cache "neither business logic nor passive infrastructure"? What does it change?
2. How are meaning and policy split? What does the operation decide, and what the coordinator?
3. Which rules do the four cache declarations share with `@access_decide`? Why is a declaration not inherited?
4. What happens on a cache hit to the aspects and their events? Why is the second "heavy" block in the output empty?
5. Why must the key include `user_id`/`tenant_id` for subject-dependent data, and how does `@context_requires` help?
6. Why is a key without a write refused, while an invalidation may stand alone?
7. Why is a result returned from `@on_error` not cached? Why does every hit return a new Result, and what does a write check before it stores one?
8. How is "freshness" expressed without a TTL? What happens when `@cache_read` returns `None`?
9. Why is the include contract not checked on a cache hit?
10. Why must a tag name a declared entity type? What did a tag without a type do before?
11. What are a dead invalidation and a dead tag, and why does the graph build refuse them?
12. In what order do `@cache_invalidate` and `@cache_write` run? Why that order?
13. What does an entity-by-entity entry keep, and what happens on a hit when one of its entities is gone?
14. Why must the key of an entity tell apart the loaded relations, and what tag tells a list its members changed?

> **Exercise.** Make `GetConfigAction` cache different tenants' results independently (it already does — verify by changing `tenant_id`), then deliberately "break" key safety by removing `tenant_id` from the key, and explain exactly which cross-client leak scenario this creates. Then make `SetConfigAction` return `[CacheTag(type=ConfigCoreEntity)]` and verify that it evicts all config entries for all tenants at once. Finally remove `SetConfigAction` and read the error the graph build gives.

---

<table width="100%"><tr>
  <td align="left"><a href="step-07-context.md">← Step 07 — Context</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-09-plugins.md">Step 09 — Plugins →</a></td>
</tr></table>
