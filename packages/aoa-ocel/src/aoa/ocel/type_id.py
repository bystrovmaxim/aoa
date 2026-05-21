# packages/aoa-ocel/src/aoa/ocel/type_id.py
"""Short OCEL type prefixes and object IDs."""

from __future__ import annotations

from typing import Any

import xxhash

_prefix_cache: dict[str, str] = {}


def make_oid(obj: Any, original_id: str | int | None = None) -> str:
    """Short OCEL type id, or object id when ``original_id`` is set.

    Without ``original_id``: ``orde_a1b`` (type prefix for ``event.type`` / ``object.type``).
    With ``original_id``: ``orde_a1b_123`` (full ``object.id``).
    """
    cls = obj if isinstance(obj, type) else type(obj)
    full_name = f"{cls.__module__}.{cls.__qualname__}"

    prefix = _prefix_cache.get(full_name)
    if prefix is None:
        base = cls.__name__[:4].lower()
        suffix = xxhash.xxh32(full_name.encode()).hexdigest()[:3]
        prefix = f"{base}_{suffix}"
        _prefix_cache[full_name] = prefix

    if original_id is None:
        return prefix
    return f"{prefix}_{original_id}"
