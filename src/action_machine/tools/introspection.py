# src/action_machine/tools/introspection.py
"""
Small, dependency-light helpers for runtime introspection of objects and callables.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any


class Introspection:
    """Runtime introspection helpers (mostly static; :meth:`full_qualname` is a classmethod)."""

    @classmethod
    def full_qualname(cls, owner: type) -> str:
        """``module.qualname`` for a type, or bare ``qualname`` in ``__main__`` / missing module."""
        module = cls.module_name_of(owner)
        qual = owner.__qualname__
        if module and module != "__main__":
            return f"{module}.{qual}"
        return qual

    @staticmethod
    def qualname_of(obj: Any) -> str:
        """Best-effort ``__qualname__`` / ``__name__`` string for ``obj``."""
        qual = getattr(obj, "__qualname__", None)
        if isinstance(qual, str) and qual:
            return qual
        name = getattr(obj, "__name__", None)
        if isinstance(name, str) and name:
            return name
        return type(obj).__name__

    @staticmethod
    def module_name_of(obj: Any) -> str | None:
        """``__module__`` when present and a non-empty string."""
        mod = getattr(obj, "__module__", None)
        return mod if isinstance(mod, str) and mod else None

    @staticmethod
    def own_namespace_keys(owner: type) -> tuple[str, ...]:
        """Insertion-order keys of ``vars(owner)`` (own dict, no MRO walk)."""
        return tuple(vars(owner).keys())

    @staticmethod
    def callable_parameter_names(fn: Callable[..., Any]) -> tuple[str, ...]:
        """Parameter names from :func:`inspect.signature` (``self``/``cls`` included when present)."""
        sig = inspect.signature(fn)
        return tuple(sig.parameters.keys())

    @staticmethod
    def callable_return_annotation(fn: Callable[..., Any]) -> Any:
        """Return annotation from the signature (may be ``inspect.Signature.empty``)."""
        return inspect.signature(fn).return_annotation
