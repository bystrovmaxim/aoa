# src/action_machine/system_core/type_introspection.py
"""
Small, dependency-light helpers for runtime introspection of types, objects, and callables (no intent scratch).
"""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Mapping
from types import MethodType
from typing import Any, cast

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
    def unwrapped_callable_name(func: Callable[..., Any]) -> str:
        """``__name__`` of the implementation after :meth:`unwrap_callable` (e.g. a method's Python name)."""
        return TypeIntrospection.unwrap_callable(func).__name__

    @staticmethod
    def owner_type_for_method(func: Callable[..., Any]) -> type:
        """Owning class for a bound/unbound method (:meth:`unwrap_callable`, then ``__qualname__`` walk from ``__module__``)."""
        raw = TypeIntrospection.unwrap_callable(func)
        qual = getattr(raw, "__qualname__", "") or ""
        parts = qual.split(".")
        if len(parts) < 2:
            msg = (
                "Cannot resolve owning class: expected a method "
                f"(``__qualname__`` like 'MyClass.method'), got {qual!r}"
            )
            raise TypeError(msg)

        mod_name = TypeIntrospection.module_name_of(raw)
        if not mod_name:
            msg = "Cannot resolve owning class: callable has no __module__"
            raise TypeError(msg)

        mod = sys.modules.get(mod_name)
        if mod is None:
            msg = f"Cannot resolve owning class: module {mod_name!r} is not loaded"
            raise TypeError(msg)

        obj: Any = mod
        for name_segment in parts[:-1]:
            try:
                obj = getattr(obj, name_segment)
            except AttributeError as exc:
                msg = (
                    f"Cannot resolve owning class: "
                    f"no attribute {name_segment!r} while walking {parts!r} from module {mod_name!r}"
                )
                raise TypeError(msg) from exc

        if not isinstance(obj, type):
            msg = f"Cannot resolve owning class: expected a type, got {type(obj).__name__}"
            raise TypeError(msg)

        return obj

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
    def description_from_meta(meta: Any) -> str | None:
        """Return strip-trimmed ``description`` from metadata mapping."""
        if not isinstance(meta, Mapping):
            return None
        raw = meta.get("description")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

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
            candidate = (
                namespace_entry.fget
                if isinstance(namespace_entry, property) and namespace_entry.fget is not None
                else namespace_entry
            )

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
