# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_decorators.py
"""
@cache_key, @cache_read, @cache_write, @cache_invalidate — what an operation caches, declared.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The cache keeps an operation's Result so that a repeated call returns it without
running the operation. What to cache is declared, as the object check is:

- ``@cache_key`` — the key of this call, or ``None`` when the call is not cached;
- ``@cache_read`` — on a hit, the Result to return, or ``None`` to drop the entry and run;
- ``@cache_write`` — after a clean run, the tags to store the Result under, or ``None`` to skip;
- ``@cache_invalidate`` — after every clean run, the tags of the entries to drop.

Each takes a non-empty description, sits on an ``async`` method whose name ends with
its kind (``…_cache_key``, ``…_cache_read``, ``…_cache_write``, ``…_cache_invalidate``),
and has a fixed signature (``cache_signature``). An operation declares at most one of
each kind in its own body; a subclass caches only what it declares itself.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    decoration   ──▶ description, tag types, suffix, async, names in order, annotations;
                     ``_cache_meta`` {kind, description, tags} written on the method
    class creation ─▶ BaseAction checks one of a kind and the old hook names
    assembly     ──▶ the annotations' types (the graph's Cache node)
    runtime      ──▶ the machine calls each declaration it finds on the operation's own class
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.description_contract_error import DescriptionContractError
from aoa.action_machine.exceptions.description_type_error import DescriptionTypeError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.intents.cache.cache_signature import (
    CacheKind,
    decorator_name,
    validate_annotated,
    validate_names,
)

CACHE_META_ATTR = "_cache_meta"
"""Attribute each cache decorator writes on its method: ``{"kind", "description", "tags"}``."""


def _is_entity(candidate: Any) -> bool:
    """An entity class: what ``@entity`` declared, which the graph holds as a node."""
    return isinstance(candidate, type) and getattr(candidate, "_entity_info", None) is not None


def _checked_tags(name: str, tags: Any, *, required: bool) -> tuple[type, ...]:
    """The declared tag types: a tuple of distinct entity classes, non-empty when ``required``."""
    if not isinstance(tags, tuple):
        raise DeclarationStructureError(f"{name}: tags must be a tuple of entity classes, got {type(tags).__name__}.")
    if required and not tags:
        raise DeclarationStructureError(
            f"{name}: declare the entity types it drops in tags=(...); an invalidation without a type drops nothing."
        )
    not_entities = [getattr(tag, "__name__", repr(tag)) for tag in tags if not _is_entity(tag)]
    if not_entities:
        raise DeclarationStructureError(
            f"{name}: tags name entity classes, and {not_entities} are not; the graph links an action to each tag type."
        )
    if len(set(tags)) != len(tags):
        raise DeclarationStructureError(f"{name}: tags list a type more than once.")
    return tags


def _declaration(
    kind: CacheKind, description: str, tags: tuple[type, ...] = ()
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Build the decorator of one kind after checking its description and its tag types."""
    name = decorator_name(kind)
    if not isinstance(description, str):
        raise DescriptionTypeError(f"{name} expects a string description, got {type(description).__name__}.")
    if not description.strip():
        raise DescriptionContractError(f"{name}: description cannot be empty or whitespace. Say what it decides.")
    suffix = f"_cache_{kind}"

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not callable(func):
            raise DeclarationStructureError(f"{name} can only be applied to methods. Got {type(func).__name__}: {func!r}.")
        if not func.__name__.endswith(suffix):
            raise NamingSuffixError(
                f"{name}: method '{func.__name__}' must end with '{suffix}'. "
                f"Rename it to '{func.__name__}{suffix}' or another name with the '{suffix}' suffix."
            )
        if not asyncio.iscoroutinefunction(func):
            raise DeclarationStructureError(f"{name}: method '{func.__name__}' must be async (async def).")
        validate_names(kind, func)
        validate_annotated(kind, func)
        setattr(func, CACHE_META_ATTR, {"kind": kind, "description": description, "tags": tags})
        return func

    return decorator


def cache_key(description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Declare the key of a call: a non-empty string, or ``None`` when this call is not cached.

    The key is computed on every call, hits included, so it should be cheap; a freshness
    check belongs in ``@cache_read``.

    Example:
        @cache_key("Order by tenant and id")
        @context_requires("tenant_id")
        async def order_cache_key(self, params: Params, box: ToolsBox, connections: Connections,
                                  ctx: ContextView) -> str | None:
            return f"{ctx['tenant_id']}:order:{params.order_id}"
    """
    return _declaration("key", description)


def cache_read(description: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare the read of a hit: the Result to return, or ``None`` to drop the entry and run."""
    return _declaration("read", description)


def cache_write(description: str, *, tags: tuple[type, ...] = ()) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Declare the write after a clean run: the tags to store the Result under, or ``None`` to skip.

    ``tags`` are the entity types the returned tags may name; the method returns the keys.

    Example:
        @cache_write("Keep every order", tags=(OrderCoreEntity,))
        async def order_cache_write(self, params: Params, box: ToolsBox, connections: Connections,
                                    result: Result, duration_ms: float) -> list[CacheTag] | None:
            return [CacheTag(type=OrderCoreEntity, key=params.order_id)]
    """
    return _declaration("write", description, _checked_tags("@cache_write", tags, required=False))


def cache_invalidate(description: str, *, tags: tuple[type, ...]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Declare the invalidation after every clean run: the tags of the entries to drop, or ``None``.

    ``tags`` are the entity types it drops, at least one; the method returns which ones.
    """
    return _declaration("invalidate", description, _checked_tags("@cache_invalidate", tags, required=True))


__all__ = ["CACHE_META_ATTR", "cache_invalidate", "cache_key", "cache_read", "cache_write"]
