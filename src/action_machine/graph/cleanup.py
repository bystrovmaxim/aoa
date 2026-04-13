# src/action_machine/graph/cleanup.py
"""
Remove decorator scratch attributes from a class after metadata assembly.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

After ``MetadataBuilder.build()`` reads the temporary attributes left by
decorators and produces immutable runtime metadata, those attributes are no
longer needed. Leaving them attached pollutes ``getattr``/``dir``, suggests
false public API, and could be read or mutated accidentally.

``cleanup_temporary_attributes()`` deletes every temporary attribute from the
class and from methods declared on that class.

═══════════════════════════════════════════════════════════════════════════════
DELETION RULES
═══════════════════════════════════════════════════════════════════════════════

Class-level scratch (``_role_info``, ``_depends_info``, ``_connection_info``):
    Removed only when present in the **current** ``cls.__dict__``. If the value
    is inherited and the subclass never defined its own copy, we **do not**
    delete — ``delattr`` on a child for an inherited attribute would walk up the
    MRO and erase parent metadata.

Method-level scratch (``_new_aspect_meta``, ``_checker_meta``,
``_on_subscriptions``, ``_sensitive_config``, ``_on_error_meta``):
    Removed only for entries in ``vars(cls)`` for the current class (not the
    entire MRO). For ``property`` objects the attribute is removed from the
    getter function (``fget``).

═══════════════════════════════════════════════════════════════════════════════
IDEMPOTENCY
═══════════════════════════════════════════════════════════════════════════════

Calling ``cleanup_temporary_attributes()`` again on a scrubbed class is safe —
``delattr`` runs only when ``cls.__dict__`` or ``hasattr`` on the underlying
function confirms the attribute exists.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

Invoked solely from ``MetadataBuilder.build()`` after metadata assembly and
validation. Not part of the package's public API.

    from action_machine.graph.cleanup import cleanup_temporary_attributes

    cleanup_temporary_attributes(cls)
"""

from __future__ import annotations

# Scratch attributes written by decorators at class scope.
# Each is removed from cls.__dict__ only (never from inherited dicts).
_CLASS_LEVEL_ATTRS: tuple[str, ...] = (
    "_role_info",
    "_depends_info",
    "_connection_info",
)

# Scratch attributes on methods / callables.
_METHOD_LEVEL_ATTRS: tuple[str, ...] = (
    "_new_aspect_meta",
    "_checker_meta",
    "_on_subscriptions",
    "_sensitive_config",
    "_on_error_meta",
)


def _cleanup_class_attrs(cls: type) -> None:
    """
    Drop class-level scratch keys present in ``cls.__dict__`` only.

    Args:
        cls: Class being cleaned.
    """
    for attr_name in _CLASS_LEVEL_ATTRS:
        if attr_name in cls.__dict__:
            delattr(cls, attr_name)


def _get_underlying_function(attr_value: object) -> object | None:
    """
    Return the callable backing a descriptor, if any.

    ``property`` → ``fget``. Plain callables pass through. Everything else
    yields ``None``.

    Args:
        attr_value: Entry from ``vars(cls)``.

    Returns:
        Callable that may carry method scratch, or ``None``.
    """
    if isinstance(attr_value, property):
        return attr_value.fget
    if callable(attr_value):
        return attr_value
    return None


def _cleanup_method_attrs(cls: type) -> None:
    """
    Drop method-level scratch for declarations owned by ``cls`` only.

    Args:
        cls: Class whose direct attributes are inspected.
    """
    for _attr_name, attr_value in vars(cls).items():
        func = _get_underlying_function(attr_value)
        if func is None:
            continue

        for method_attr in _METHOD_LEVEL_ATTRS:
            if hasattr(func, method_attr):
                try:
                    delattr(func, method_attr)
                except AttributeError:
                    # builtins / C extensions may forbid deletions — safe to skip.
                    pass


def cleanup_temporary_attributes(cls: type) -> None:
    """
    Remove decorator scratch from ``cls`` and from methods defined on ``cls``.

    Called from ``MetadataBuilder.build()`` after runtime metadata is ready.
    Subsequent rebuilds for the same class return empty metadata unless
    decorators run again — usually fine because ``GateCoordinator`` caches the
    first successful build.

    Idempotent: repeated calls on an already cleaned class do nothing harmful.

    Steps:
        1. Class-level keys (``_role_info``, ``_depends_info``, ``_connection_info``)
           — only if they live in ``cls.__dict__``.
        2. Method-level keys (``_new_aspect_meta``, ``_checker_meta``, …) — only
           for attributes from ``vars(cls)``.

    Args:
        cls: Class whose scratch attributes should be removed.
    """
    _cleanup_class_attrs(cls)
    _cleanup_method_attrs(cls)
