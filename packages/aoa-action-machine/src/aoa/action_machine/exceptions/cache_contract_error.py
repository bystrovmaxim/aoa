# packages/aoa-action-machine/src/aoa/action_machine/exceptions/cache_contract_error.py
"""
``CacheContractError`` — raised when a cache declaration's **return value** breaks the engine contract.

This is distinct from arbitrary exceptions raised **inside** a declaration's body: those
propagate as-is. ``CacheContractError`` is a :class:`TypeError` subclass used when the
machine validates what a declaration returned (a non-``str`` or blank key, a read that
returns something other than the action's Result, a tag of an undeclared type), and,
through :class:`~aoa.action_machine.exceptions.cache_serialization_error.CacheSerializationError`,
a Result whose JSON does not read back. In v1, if any declaration or coordinator call
raises after ``GlobalStartEvent``, ``GlobalFinishEvent`` is not emitted.
"""

from __future__ import annotations


class CacheContractError(TypeError):
    """
    Raised when a cache declaration returns a value that violates the typed contract.

    Covers: a key that is not a non-empty ``str``, ``@cache_read`` returning a non-``None``
    value that is not the action's Result, ``@cache_write`` / ``@cache_invalidate`` returning
    something other than ``list[CacheTag] | None`` or a tag of an undeclared type, and a
    Result that cannot be cached (:class:`CacheSerializationError`).

    Arbitrary exceptions from inside declarations are **not** wrapped in this type;
    they propagate unchanged.
    """
