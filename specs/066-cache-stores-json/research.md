# Research: The cache stores JSON

## Before, re-measured

| Case | Output |
| --- | --- |
| 9.1 change the first Result, hit | `(['a', 'leak'], True)` — on `main` after #412, with the declared cache |
| 9.2 | as in #410: `Any` field holding a plain object, `field_serializer` to `"2 items"`, `field_serializer` floor; the cache keeps the object, so none of them fails |

## R1. What the store keeps

**Decision**: `runtime/cache_entry.py` gets `StoredCacheEntry(payload: bytes, pipeline_duration_ms, created_at, last_accessed_at, access_count)`, which the store returns from `get_entry`; `put(action_cls, user_key, payload: bytes, pipeline_duration_ms, tags)` takes bytes. `CacheEntry` stays what `@cache_read` receives: `result` plus the same metadata, built by `CacheEntry.from_stored(stored, result)`. `CacheCoordinator` keeps `StoredCacheEntry`; its size-based eviction reads `pipeline_duration_ms` as before.

**Rationale**: the store's contract becomes what Redis can do; the action's contract does not change shape.

## R2. The write

`ActionProductMachine._encode_for_cache(result, action)`:

1. `payload = result.model_dump_json().encode()`; on `PydanticSerializationError` the fields are dumped one at a time (`include={name}`) to name the first that fails: `field 'data' has no JSON form (<Pydantic's message>)`;
2. `back = result_type.model_validate_json(payload)`; on `ValidationError` the first error names the field (`loc[0]`), its input and its type: `field 'count' does not read back from its own JSON ('2 items': int_parsing)`;
3. `observable_difference(result, back)`; the first top-level field that differs is named: `field 'count' reads back as 20, but was 29` for a scalar, `field 'order' reads back different ($.order.lines: loaded True != False)` otherwise.

Each raises `CacheSerializationError(CacheContractError)`: `<Result qualname> cannot be cached: <reason>.` It runs only when `@cache_write` returned tags; nothing else is serialized.

## R3. The read

On a hit the machine reads `result_type.model_validate_json(stored.payload)`; a `ValidationError` (or a `ValueError` from a validator) invalidates the key and runs the pipeline; `@cache_read` is not called.

## R4. The real-hit test

A recording store (a subclass of `CacheCoordinator`) keeps every payload `put` receives; the test runs a Result with loaded and unloaded relations, a lifecycle and a dictionary value, hits it, and checks `observable_difference(first, hit) is None` and `first is not hit`. The adversarial break edits the stored JSON to drop `entities` before the hit.

## R5. Repository impact

`CacheCoordinator`, `CacheEntry` users in tests (`test_action_product_machine_cache*.py`, the cache declarations test), the how-to example store `examples/how_to/05_custom_cache_adapter.py` and its page, tutorial step 8. Versions: `aoa-action-machine`.
