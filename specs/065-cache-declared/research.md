# Research: The cache is declared like an access check

Measured on `main` at `c83f0b8fd` (after #409); the cache code (`base_action.py`, `cache_coordinator.py`, `cache_tag.py`, the cache block of `action_product_machine.py`) is unchanged since `d584bbba4`, where #412's Before outputs were produced, so they stand. Re-measured: the four methods' signatures, exactly as 11.1 shows them.

## R1. The four declarations

**Decision**: a package `intents/cache/` beside `intents/access_decide/`:

- `cache_decorators.py` — `cache_key(description)`, `cache_read(description)`, `cache_write(description, *, tags=())`, `cache_invalidate(description, *, tags)`; each checks the description (`DescriptionTypeError`, `DescriptionContractError`), the suffix (`NamingSuffixError`: `_cache_key`, `_cache_read`, `_cache_write`, `_cache_invalidate`), `async` (`DeclarationStructureError`), the names in order and the annotations (`AspectSignatureError`), and writes `_cache_meta = {"kind", "description", "tags"}` on the method;
- `cache_signature.py` — the contract per kind: `self, params, box, connections`, then `entry` (read), `result, duration_ms` (write), `result` (invalidate), then `ctx` with `@context_requires`; types at assembly: `BaseParams`, `ToolsBox`, `Connections`, `CacheEntry`, `BaseResult`, `float`, `ContextView`; returns `str | None`, `BaseResult | None`, `list[CacheTag] | None`;
- `cache_intent_resolver.py` — `CacheIntentResolver.declarations(action_cls) -> CacheDeclarations(key, read, write, invalidate)`, read from the class's own namespace, memoized per class;
- `cache_intent.py` — the marker `CacheIntent` on `BaseAction`, as `AccessDecideIntent`.

**Rationale**: the issue asks for the rules of `@access_decide`; its decorator, signature module and resolver are the template, and the messages read the same.

## R2. When each rule is checked

| Rule | When |
| --- | --- |
| description, suffix, `async`, names and order, annotations, tag tuple | decoration |
| types of the annotations | assembly (graph node), as `@access_decide` |
| one of a kind (naming both), pairing (11.2), old names (11.6) | class creation: `BaseAction.__init_subclass__` calls `validate_cache_declarations(cls)` |
| tag types of returned tags (11.4) | each call |
| dead invalidation, dead tag (11.3) | graph build |

## R3. The machine

`ActionProductMachine` resolves the declarations once per action class and calls each as the object check is called: `declared(action, params, box, connections, *own, ctx?)`, with a box from `method_box` named after the method, so its log lines carry its graph node id. Order unchanged: key → entry → read (default: the stored Result) → run → invalidate → write when the key was not `None`. A Result from `@on_error` is neither invalidated nor written, as today.

## R4. Tag types

`tags=` is a tuple of entity classes (a class with `_entity_info`), without repeats; `@cache_invalidate` needs at least one. A returned tag is checked on each call: `type` set and among the declared ones, else `CacheContractError: <Action>.<method> returned CacheTag(...), whose type is not among its declared tags (<names>)` / `… has no type`. `CacheTag` itself is unchanged.

## R5. The graph

- one node type `Cache` (`CacheGraphNode`): id `<action>:<method>`, label the method, properties `kind` and `description`, required-context edges as the object check;
- composition edges from the action named `@cache_key`, `@cache_read`, `@cache_write`, `@cache_invalidate`;
- association edges from the action to each tag type: `caches` (write) and `invalidates` (invalidate);
- `graph/validators/cache_tags_validator.py`, called by the build: an invalidated type no action caches → `CacheTagsError: DropInvoiceAction drops InvoiceCoreEntity, but no action caches it`; a cached type no action invalidates → `GetOrderAction caches OrderCoreEntity, but no action invalidates it; nothing will tell its entries they are stale`.

## R6. The protocol and Maxitor

Open Gnomon Protocol 1.4 adds the node type `Cache` and the edge types `@cache_key`, `@cache_read`, `@cache_write`, `@cache_invalidate`, `caches`, `invalidates`, the way 1.3 added events (#334): `packages/open-gnomon-protocol/graph/1.4.json`, its copies in AOA (`graph_json_schema.json`) and in the graph builder (`schemas/1.4.json`), a 1.4 fixture, and the schema-copies test. Maxitor's DuckDB store gets a `cache` table, a `cache_edges` table for the four composition edges and `caches_edges` / `invalidates_edges`, and lists `Cache` among its node types.

## R7. Repository impact

| Where | What |
| --- | --- |
| `aoa-action-machine` tests | `test_base_action_cache_hooks.py`, `test_action_product_machine_cache.py`, `test_action_product_machine_cache_invalidation.py`, `test_emission_rules.py` override the old methods |
| examples | `step_08_cache/01_cache.py`, `step_11_object_events/07_masking_filters_cache.py`, `how_to/05_custom_cache_adapter.py`, with notebooks |
| docs | tutorial step 8, the reference of intents and invariants, the how-to on a cache adapter, the glossary, step 12 |

A module-level caching action in a test is in every graph a test builds in that process, so each test module keeps its write and invalidate tags balanced, or declares its actions inside the test.
