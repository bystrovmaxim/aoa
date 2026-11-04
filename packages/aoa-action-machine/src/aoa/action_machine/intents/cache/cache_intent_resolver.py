# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_intent_resolver.py
"""
CacheIntentResolver — find the cache declarations an operation makes in its own body.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One place that answers "what does this operation cache, and through which methods".
It reads the operation's **own** namespace, so a subclass never inherits what its
parent caches, and it holds the rules checked when an action class is created:
at most one declaration of each kind, a key and a write together (a read only with
them; an invalidation may stand alone), and no method left under an old hook name
(``cache_key``, ``read_cache``, ``on_cache_write``, ``on_cache_invalidate``), which
the machine no longer calls.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @cache_<kind> ──▶ ``_cache_meta`` on the method
                            │
    BaseAction.__init_subclass__ ──▶ validate_cache_declarations(cls)
    the machine, the graph       ──▶ CacheIntentResolver.declarations(cls) → CacheDeclarations
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from weakref import WeakKeyDictionary

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.intents.cache.cache_decorators import CACHE_META_ATTR
from aoa.action_machine.intents.cache.cache_signature import decorator_name
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

_KINDS = ("key", "read", "write", "invalidate")

# Old hook name -> the kind that replaces it.
_OLD_HOOKS = {
    "cache_key": "key",
    "read_cache": "read",
    "on_cache_write": "write",
    "on_cache_invalidate": "invalidate",
}


@dataclass(frozen=True)
class CacheDeclarations:
    """
    AI-CORE-BEGIN
        ROLE: The cache declarations of one operation, each the declared method or ``None``.
        CONTRACT: ``key``, ``read``, ``write``, ``invalidate``; :attr:`declared` lists the present ones in that order.
    AI-CORE-END
    """

    key: Callable[..., Any] | None = None
    read: Callable[..., Any] | None = None
    write: Callable[..., Any] | None = None
    invalidate: Callable[..., Any] | None = None

    @property
    def declared(self) -> tuple[tuple[str, Callable[..., Any]], ...]:
        """``(kind, method)`` for each declaration present, in the order key, read, write, invalidate."""
        return tuple((kind, method) for kind in _KINDS if (method := getattr(self, kind)) is not None)


def kind_of(method: Callable[..., Any]) -> str:
    """The kind a declared method was declared with."""
    return str(getattr(method, CACHE_META_ATTR)["kind"])


def tags_of(method: Callable[..., Any]) -> tuple[type, ...]:
    """The entity types a declared write or invalidation names in ``tags=``."""
    return tuple(getattr(method, CACHE_META_ATTR).get("tags", ()))


def description_of(method: Callable[..., Any]) -> str:
    """What a declared method says it does."""
    return str(getattr(method, CACHE_META_ATTR)["description"])


def _own_by_kind(action_cls: type[Any]) -> dict[str, list[Callable[..., Any]]]:
    found: dict[str, list[Callable[..., Any]]] = {kind: [] for kind in _KINDS}
    for method in TypeIntrospection.collect_own_class_callables(
        action_cls, lambda func: getattr(func, CACHE_META_ATTR, None) is not None
    ):
        found[kind_of(method)].append(method)
    return found


def validate_cache_declarations(action_cls: type[Any]) -> None:
    """
    Refuse, when an action class is created, a method under an old hook name, two declarations of one kind,
    and a declaration that can never have an effect: a key without a write, a write without a key, a read
    without both.

    Raises:
        DeclarationStructureError: names the class, the methods and the declaration to use.
    """
    for old_name, kind in _OLD_HOOKS.items():
        if old_name in vars(action_cls):
            raise DeclarationStructureError(
                f"{action_cls.__name__}.{old_name} is a cache hook the machine no longer calls. "
                f"Declare it with {decorator_name(kind)}(\"...\") on an async method whose name ends with "
                f"'_cache_{kind}'."
            )
    by_kind = _own_by_kind(action_cls)
    for kind, methods in by_kind.items():
        if len(methods) > 1:
            names = ", ".join(sorted(method.__name__ for method in methods))
            raise DeclarationStructureError(
                f"{action_cls.__name__} declares {decorator_name(kind)} more than once ({names}); "
                "an operation declares each cache step once."
            )
    _refuse_without_effect(action_cls.__name__, {kind for kind, methods in by_kind.items() if methods})


def _refuse_without_effect(name: str, kinds: set[str]) -> None:
    """A key and a write come together, and a read only with them; an invalidation may stand alone."""
    if "key" in kinds and "write" not in kinds:
        raise DeclarationStructureError(
            f"{name} declares @cache_key without @cache_write; a key without a write never stores anything."
        )
    if "write" in kinds and "key" not in kinds:
        raise DeclarationStructureError(
            f"{name} declares @cache_write without @cache_key; the machine calls a write only for a key."
        )
    if "read" in kinds and "key" not in kinds:
        raise DeclarationStructureError(
            f"{name} declares @cache_read without @cache_key and @cache_write; nothing is ever stored for it to read."
        )


class CacheIntentResolver:
    """
    AI-CORE-BEGIN
        ROLE: Surface the cache declarations an operation makes in its own namespace.
        CONTRACT: :meth:`declarations` returns a :class:`CacheDeclarations`, computed once per class.
        INVARIANTS: Reads ``vars(action_cls)`` only, so a declaration is never inherited; the class-creation rules have already refused duplicates.
    AI-CORE-END
    """

    # Weak, so a class nobody holds any more leaves the graph walk, which lists live subclasses.
    _cache: WeakKeyDictionary[type[Any], CacheDeclarations] = WeakKeyDictionary()

    @staticmethod
    def declarations(action_cls: type[Any]) -> CacheDeclarations:
        """Return the operation's own cache declarations."""
        known = CacheIntentResolver._cache.get(action_cls)
        if known is None:
            by_kind = _own_by_kind(action_cls)
            known = CacheDeclarations(**{kind: methods[0] if methods else None for kind, methods in by_kind.items()})
            CacheIntentResolver._cache[action_cls] = known
        return known


__all__ = ["CacheDeclarations", "CacheIntentResolver", "description_of", "kind_of", "tags_of", "validate_cache_declarations"]
