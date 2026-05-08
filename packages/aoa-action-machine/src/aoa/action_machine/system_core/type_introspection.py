# packages/aoa-action-machine/src/aoa/action_machine/system_core/type_introspection.py
"""
Small, dependency-light helpers for runtime introspection of types, objects, and callables (no intent scratch).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from types import MethodType
from typing import Any, cast

# ``builtins.property`` declares class-body members hiding the callable behind ``fget``.
# ``pydantic.BaseModel`` exposes these as public ``@property`` on the MRO; they are not host-declared members.
_SKIP_PYDANTIC_PLAIN_PROPERTY_NAMES: frozenset[str] = frozenset({"model_extra", "model_fields_set"})


class TypeIntrospection:
    """Runtime type/callable introspection helpers (mostly static; :meth:`full_qualname` is a classmethod)."""

    @staticmethod
    def unwrap_callable(func: Callable[..., Any]) -> Callable[..., Any]:
        """Strip :class:`types.MethodType` wrapper, then :func:`inspect.unwrap` through ``__wrapped__`` chains."""
        if isinstance(func, MethodType):
            func = func.__func__
        return cast(Callable[..., Any], inspect.unwrap(func))

    @staticmethod
    def unwrap_declaring_class_member(attr: Any) -> Any:
        """Prefer ``property.fget`` for class-body descriptors so decorators on methods stay visible."""
        if isinstance(attr, property) and attr.fget is not None:
            return attr.fget
        return attr

    @staticmethod
    def unwrapped_callable_name(func: Callable[..., Any]) -> str:
        """``__name__`` of the implementation after :meth:`unwrap_callable` (e.g. a method's Python name)."""
        return TypeIntrospection.unwrap_callable(func).__name__

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
    def collect_own_class_callables(
        owner_class: type,
        predicate: Callable[[Callable[..., Any]], bool],
    ) -> list[Callable[..., Any]]:
        """Own-class callables from ``vars(owner_class)`` that satisfy ``predicate``."""
        result: list[Callable[..., Any]] = []

        for _name, namespace_entry in vars(owner_class).items():
            candidate = TypeIntrospection.unwrap_declaring_class_member(namespace_entry)

            if not callable(candidate):
                continue

            if predicate(candidate):
                result.append(candidate)

        return result

    @staticmethod
    def property_members(host_cls: type) -> dict[str, property]:
        """Public ``property`` objects on ``host_cls`` MRO (subclass wins); skip ``_`` names and Pydantic extras."""
        found: dict[str, property] = {}
        for base in host_cls.__mro__:
            if base is object:
                break
            base_dict = getattr(base, "__dict__", None)
            if base_dict is None:
                continue
            for name, member in base_dict.items():
                if name.startswith("_") or not isinstance(member, property):
                    continue
                if name in _SKIP_PYDANTIC_PLAIN_PROPERTY_NAMES:
                    continue
                if name not in found:
                    found[name] = member
        return found

    @staticmethod
    def callable_parameter_names(fn: Callable[..., Any]) -> tuple[str, ...]:
        """Parameter names from :func:`inspect.signature` (``self``/``cls`` included when present)."""
        sig = inspect.signature(fn)
        return tuple(sig.parameters.keys())

    @staticmethod
    def callable_return_annotation(fn: Callable[..., Any]) -> Any:
        """Return annotation from the signature (may be ``inspect.Signature.empty``)."""
        return inspect.signature(fn).return_annotation
