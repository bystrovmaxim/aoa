# Research: A collection is cached entity by entity

## R1. Declarations

`CacheLayout` (`WHOLE`, `ENTITIES`) in `intents/cache/cache_layout.py`; `cache_write(..., layout=CacheLayout.WHOLE)` keeps it in `_cache_meta`. `@cache_entity_key` is a fifth kind, `entity_key`: suffix `_cache_entity_key`, own parameter `entity`, return `str`; its types at assembly (`entity: BaseEntity`). Class creation: `layout=ENTITIES` and `@cache_entity_key` together, or refused. Assembly (the write's `Cache` node): the Result has at least one field typed by an entity — bare, `| None`, `list[...]` — and each such entity declares `id`; else `DeclarationStructureError`.

## R2. Where the entries live

Entity entries live under one namespace class, `runtime.cache_entity.CachedEntity`, through the store's existing `put` / `get_entry` / `invalidate`, so two actions building one key share it; their tag is `CacheTag(type=entity_cls, key=entity.id)`. The collection entry lives under the action, as a whole entry does. Its payload is JSON `{"fields": <the Result in JSON without the entity fields>, "entities": {<field>: <key> | [<keys>] | null}}`.

## R3. Write and hit

Write (after `@cache_write` returned tags): the whole Result passes the read-back of #410 first; then each entity is dumped (`model_dump_json`) under its key, then the collection entry. Hit: read the collection entry; `get_entries(CachedEntity, keys)` in one call; any `None` → drop the collection entry, miss; assemble the Result's JSON (`fields` with each entity field filled from its entries' JSON) and read it with `result_type.model_validate_json`; a `ValueError` → miss (12.5); then `@cache_read` as for a whole entry.

## R4. The store

`get_entries(action_cls, user_keys) -> list[StoredCacheEntry | None]`, in the given order: `CacheCoordinator` under one lock; the how-to's dict store. A store without it is not usable for this layout; the machine calls it only for `ENTITIES`.

## R5. Graph and protocol

Protocol 1.5: the `Cache` node's `kind` adds `entity_key`, the declaration edges add `@cache_entity_key`. `caches` edges go to the write's tag types and, for `ENTITIES`, the entity types of its Result's entity fields; `cache_tags_validator` counts the same set. Copies, builder fixture, comparison, Maxitor's `cache_entity_key_edges` table, as for 1.4.
