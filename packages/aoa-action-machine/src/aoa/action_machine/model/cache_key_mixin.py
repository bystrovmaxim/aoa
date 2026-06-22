# packages/aoa-action-machine/src/aoa/action_machine/model/cache_key_mixin.py
"""CacheKeyMixin — automatic hash-based cache key and write policy for BaseAction subclasses."""

from __future__ import annotations

import hashlib
import json

from aoa.action_machine.model.base_schema import BaseSchema

# Scalar Python types that are safe to serialize and include in the cache key.
_SCALAR_TYPES: tuple[type, ...] = (str, int, float, bool)


class CacheKeyMixin:
    """Mixin that enables full result caching for a ``BaseAction`` subclass.

    Apply before ``BaseAction`` in the MRO::

        class MyAction(CacheKeyMixin, BaseAction[MyParams, MyResult]): ...

    Overrides two hooks:

    ``cache_key(params) -> str``
        Returns a stable SHA-256 hex digest of all scalar fields
        (``str``, ``int``, ``float``, ``bool``, ``None``) found in ``params``.
        Fields are sorted by name before hashing so the key is order-independent.

    ``on_cache_write(result, params, duration_ms) -> bool``
        Always returns ``True`` — every clean result is written to the cache.
        Override per-action to add opt-out logic.

    AI-CORE-BEGIN
    ROLE: Opt-in mixin that wires hash-based cache keying and unconditional write policy onto a BaseAction subclass.
    CONTRACT: Placed before BaseAction in MRO; overrides cache_key to return str (never None); overrides on_cache_write to return True.
    INVARIANTS: cache_key is deterministic for the same scalar field values; non-scalar fields are excluded; empty/complex-only params hash to a stable constant.
    AI-CORE-END
    """

    def cache_key(self, params: object) -> str:
        """Return SHA-256 hex digest of all scalar fields (str, int, float, bool, None) in params.
        Non-scalar fields (list, dict, etc.) are excluded; empty params hash to a stable constant."""
        scalars: dict[str, object] = {}
        if isinstance(params, BaseSchema):
            for k, v in params.model_dump().items():
                if isinstance(v, _SCALAR_TYPES) or v is None:
                    scalars[k] = v
        payload = json.dumps(scalars, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    async def on_cache_write(self, result: object, params: object, duration_ms: float) -> bool:
        """Always return True — every clean pipeline result is written to the cache.
        Override per-action to add opt-out logic."""
        return True
