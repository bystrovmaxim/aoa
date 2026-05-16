# packages/aoa-action-machine/src/aoa/action_machine/exceptions/cache_contract_error.py
"""
``CacheContractError`` — raised when cache hook **return values** break the engine contract.

This is distinct from arbitrary exceptions raised **inside** user hook bodies: those
propagate as-is. ``CacheContractError`` is a :class:`TypeError` subclass used when the
machine validates hook outputs (for example non-``str`` ``cache_key``, blank key,
``read_cache`` value not matching the declared result type, or ``on_cache_write`` not
returning ``bool``). In v1, if any hook or coordinator call raises after
``GlobalStartEvent``, ``GlobalFinishEvent`` is not emitted.
"""

from __future__ import annotations


class CacheContractError(TypeError):
    """
    Raised when cache-related hooks return values that violate the typed contract.

    Covers: invalid ``cache_key`` type, empty/whitespace-only ``cache_key``,
    ``read_cache`` returning a non-``None`` value that is not an instance of the
    action's declared result type, and ``on_cache_write`` returning a non-boolean.

    Arbitrary exceptions from inside hook implementations are **not** wrapped in
    this type; they propagate unchanged.
    """
