# packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py
"""
The declaration machinery shared by the kinds that declare their own values.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two kinds declare a closed set of values in their own class body: the state kind
declares its statuses, the dictionary kind declares its reference values. The
form is one, and it is explicit: ::

    class OrderStateEntity(BaseStateEntity):
        DRAFT = value(code="draft", display_name="Draft")

    class CurrencyEnumEntity(BaseEnumEntity):
        USD = value(code="usd", display_name="US dollar")

:func:`value` returns a :class:`ValueSpec` placeholder; the Pydantic hook
:meth:`_DeclaredValues.__pydantic_init_subclass__` turns every placeholder into a
real instance after the model is built and fills the catalogue. That conversion
is the one automatic step that remains, and it reads only the class body.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The ``value`` factory, the placeholder, the conversion hook, the catalogue
    (``members``, ``codes()``, ``by_code()``, ``entity_type``), the duplicate
    refusal, and the two per-kind switches: whether a class without its own
    values inherits the parent's catalogue, and what the duplicate message calls
    the values.

**Out of scope**
    Which fields a value carries — the kind supplies them. The hierarchy rules —
    :class:`~aoa.action_machine.domain.entity.BaseEntity` owns them. The graph —
    a kind decides whether its values travel.

═══════════════════════════════════════════════════════════════════════════════
WHY A MIXIN AND NOT A COMMON ANCESTOR
═══════════════════════════════════════════════════════════════════════════════

``BaseEntity.__init_subclass__`` recognises a kind base as a class that inherits
the entity base directly and overrides the subclass hook; two such classes in one
MRO are refused. A shared ancestor that inherited ``BaseEntity`` would therefore
be read as a seventh kind base. The mixin inherits nothing, so the state and the
dictionary kinds stay siblings and the hierarchy sees exactly one kind per entity.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class body            conversion hook                consumers
    DRAFT = value(...)  ──►  OrderStateEntity(**kwargs)  ──►  members,
    (ValueSpec placeholder)  full instance, validated        codes(), by_code(),
                                                             entity_type
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any, ClassVar, Literal, Union, get_args, get_origin
from uuid import UUID


class ValueSpec:
    """Hold the keyword arguments of one declared value until the class exists."""

    def __init__(self, kwargs: dict[str, Any]) -> None:
        """Store the declaration's arguments verbatim."""
        self.kwargs = kwargs


def value(**kwargs: Any) -> Any:
    """
    Declare a value inside a kind's class body; the class turns it into an instance.

    AI-CORE-BEGIN
        ROLE: The one declaration form for a dictionary value and a lifecycle status — the line inside a kind's class body that names the fields of one value.
        CONTRACT: Returns a ``ValueSpec`` placeholder that the class's ``__pydantic_init_subclass__`` converts into a validated instance after the model exists; ``code`` and ``display_name`` are the kind's required fields and the rest are the model's own; the value is reachable as the declared attribute and through ``by_code()``.
        INVARIANTS: Usable only inside a declaring class body for its effect; the placeholder is never a model field and never reaches a consumer; a returned object is annotated ``Any`` because the declaring class does not exist at the call site.
    AI-CORE-END
    """
    return ValueSpec(kwargs)


_SUPPORTED_LEAVES: tuple[type[Any], ...] = (str, int, float, bool, Decimal, date, datetime, time, UUID)
_SUPPORTED_SUMMARY = (
    "str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, "
    "Optional of a supported type, or a tuple of supported types"
)


def _refused_property_type(annotation: Any) -> str | None:
    """Return what to call ``annotation`` when it is unsupported, or ``None`` when it is supported."""
    refused: str | None = None
    origin = get_origin(annotation)
    if annotation is Any:
        refused = "Any"
    elif isinstance(annotation, type):
        supported = annotation is type(None) or annotation in _SUPPORTED_LEAVES or issubclass(annotation, Enum)
        refused = None if supported else annotation.__name__
    elif annotation is not None and origin is not Literal:
        if origin in (Union, UnionType) or origin is tuple:
            for argument in get_args(annotation):
                candidate = None if argument is Ellipsis else _refused_property_type(argument)
                if candidate is not None:
                    refused = candidate
                    break
        else:
            refused = getattr(origin, "__name__", None) or str(annotation)
    return refused


def _type_name(value: Any) -> str:
    """Return the short type name of a runtime value."""
    return type(value).__name__


def _annotation_name(annotation: Any) -> str:
    """Return a readable name for an annotation, keeping a subscripted form subscripted."""
    if get_origin(annotation) is not None:
        return str(annotation).replace("typing.", "")
    name = getattr(annotation, "__name__", None)
    return str(name) if isinstance(name, str) else str(annotation)


def _enum_value_refusal(enum_cls: type[Enum], value: Any, path: str) -> tuple[str, str] | None:
    """Return the refusal for a declared value whose own ``Enum`` value is mutable."""
    declared = value.value
    if declared is None or isinstance(declared, _SUPPORTED_LEAVES):
        return None
    if isinstance(declared, tuple):
        for item in declared:
            if item is not None and not isinstance(item, _SUPPORTED_LEAVES):
                return (path, f"holds {enum_cls.__name__}, whose value holds {_type_name(item)}")
        return None
    return (path, f"holds {enum_cls.__name__}, whose value is {_type_name(declared)}")


def _runtime_refusal(value: Any, annotation: Any, path: str) -> tuple[str, str] | None:
    """Return the first property path and reason a runtime value breaks, or ``None`` when it holds."""
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        if value is None:
            return None
        for argument in get_args(annotation):
            if argument is type(None):
                continue
            if _runtime_refusal(value, argument, path) is None:
                return None
        return (path, f"holds {_type_name(value)} (expected {_annotation_name(annotation)})")
    if origin is Literal:
        return None if isinstance(value, _SUPPORTED_LEAVES) or value is None else (path, f"holds {_type_name(value)}")
    if origin is tuple:
        if not isinstance(value, tuple):
            return (path, f"holds {_type_name(value)} (expected {_annotation_name(annotation)})")
        arguments = get_args(annotation)
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            for index, item in enumerate(value):
                found = _runtime_refusal(item, arguments[0], f"{path}[{index}]")
                if found is not None:
                    return found
            return None
        if len(arguments) != len(value):
            return (path, f"holds {_type_name(value)} (expected {_annotation_name(annotation)})")
        for index, (item, argument) in enumerate(zip(value, arguments, strict=True)):
            found = _runtime_refusal(item, argument, f"{path}[{index}]")
            if found is not None:
                return found
        return None
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        if not isinstance(value, annotation):
            return (path, f"holds {_type_name(value)} (expected {annotation.__name__})")
        return _enum_value_refusal(annotation, value, path)
    if isinstance(annotation, type):
        if not isinstance(value, annotation):
            return (path, f"holds {_type_name(value)} (expected {annotation.__name__})")
        return None if annotation in _SUPPORTED_LEAVES else (path, f"holds {_type_name(value)}")
    return None


class _DeclaredValues:
    """
    Mixin: the declaration factory, the catalogue and the conversion of placeholders.

    A kind inheriting this mixin states four things about its own values:
    whether a class without values of its own inherits the parent's catalogue
    (``__declared_values_inherit__``), whether a decorated class must declare at
    least one value (``__declared_values_require_any__``), what the duplicate
    refusal calls the values (``__declared_values_noun__``), and whether a value
    may carry only immutable property types (``__declared_values_immutable__``).
    The last one is off by default and on for the dictionary kind: a dictionary
    value is exported to every consumer, a status is not. It is enforced twice —
    on the annotation when the class is created, and on the completed member after
    the model's own validators have run — because a validator can replace a tuple
    with a list, and the catalogue must never publish such a value.
    """

    __declared_values_inherit__: ClassVar[bool] = True
    __declared_values_require_any__: ClassVar[bool] = False
    __declared_values_immutable__: ClassVar[bool] = False
    __declared_values_noun__: ClassVar[str] = "declared"
    __declared_values_noun_plural__: ClassVar[str] = "values"
    __declared_values_empty_refusal__: ClassVar[str] = "declare them in the class body."

    members: ClassVar[tuple[Any, ...]] = ()
    _by_code: ClassVar[dict[str, Any]] = {}
    entity_type: ClassVar[type[Any] | None] = None

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Turn this class's placeholders into instances and fill its catalogue."""
        parent_hook = getattr(super(), "__pydantic_init_subclass__", None)
        if parent_hook is not None:
            parent_hook(**kwargs)
        if cls.__declared_values_immutable__:
            cls._require_immutable_properties()
        cls.entity_type = cls
        specs = {name: spec for name, spec in cls.__dict__.items() if isinstance(spec, ValueSpec)}

        if not specs:
            if not cls.__declared_values_inherit__:
                cls.members = ()
                cls._by_code = {}
            return

        for name, spec in specs.items():
            member = cls(**spec.kwargs)
            if cls.__declared_values_immutable__:
                cls._require_immutable_runtime(member, name)
            setattr(cls, name, member)
        members = tuple(getattr(cls, name) for name in specs)
        codes = [member.code for member in members]
        if len(codes) != len(set(codes)):
            duplicates = sorted({code for code in codes if codes.count(code) > 1})
            raise ValueError(f"{cls.__name__}: duplicate {cls.__declared_values_noun__} code(s) in {duplicates}.")
        cls.members = members
        cls._by_code = {member.code: member for member in members}

    @classmethod
    def _require_immutable_properties(cls) -> None:
        """Refuse a property type a shared value cannot promise to keep immutable."""
        for name, field in getattr(cls, "model_fields", {}).items():
            refused = _refused_property_type(field.annotation)
            if refused is not None:
                raise ValueError(
                    f"{cls.__name__}: field '{name}' is {refused}, which a dictionary value cannot carry; "
                    f"supported: {_SUPPORTED_SUMMARY}."
                )

    @classmethod
    def _require_immutable_runtime(cls, member: Any, attribute: str) -> None:
        """Refuse a completed member whose runtime value breaks the immutable contract."""
        for field_name, field in getattr(cls, "model_fields", {}).items():
            found = _runtime_refusal(getattr(member, field_name), field.annotation, field_name)
            if found is not None:
                path, reason = found
                raise ValueError(
                    f"{cls.__name__}: the property '{path}' of member '{attribute}' {reason}; "
                    f"supported: {_SUPPORTED_SUMMARY}."
                )

    @classmethod
    def _require_declared_values(cls) -> None:
        """Refuse a concrete class of a kind that must declare values but declares none."""
        if cls.__declared_values_require_any__ and not cls.members:
            raise ValueError(
                f"{cls.__name__} declares no {cls.__declared_values_noun_plural__}; "
                f"{cls.__declared_values_empty_refusal__}"
            )

    @classmethod
    def codes(cls) -> list[str]:
        """Return the declared codes in declaration order."""
        return [member.code for member in cls.members]

    @classmethod
    def by_code(cls, code: str) -> Any:
        """Return the value declared under ``code``; raise ``KeyError`` otherwise."""
        return cls._by_code[code]
