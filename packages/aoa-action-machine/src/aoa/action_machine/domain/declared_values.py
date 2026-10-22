# packages/aoa-action-machine/src/aoa/action_machine/domain/declared_values.py
"""
The declaration machinery shared by the kinds that declare their own values.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two kinds declare a closed set of values in their own class body: the state kind
declares its statuses, the dictionary kind declares its reference values. The
form is one: ::

    class OrderStateEntity(BaseStateEntity):
        DRAFT = OrderStateEntity(code="draft", display_name="Draft")

    class CurrencyEnumEntity(BaseEnumEntity):
        USD = CurrencyEnumEntity(code="usd", display_name="US dollar")

The class does not exist while its body runs, so the type's own name resolves to
:func:`value` there. The factory returns a :class:`ValueSpec`; the Pydantic hook
:meth:`_DeclaredValues.__pydantic_init_subclass__` turns every placeholder into a
real instance after the model is built and fills the catalogue.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The namespace alias, the placeholder, the conversion hook, the catalogue
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

    class body                        conversion hook                consumers
    DRAFT = OrderStateEntity(...)  ──►  OrderStateEntity(**kwargs)  ──►  members,
    (ValueSpec placeholder)             full instance, validated         codes(), by_code(),
                                                                         entity_type
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic._internal._model_construction import ModelMetaclass


class ValueSpec:
    """Hold the keyword arguments of one declared value until the class exists."""

    def __init__(self, kwargs: dict[str, Any]) -> None:
        """Store the declaration's arguments verbatim."""
        self.kwargs = kwargs


def value(**kwargs: Any) -> ValueSpec:
    """Declare a value inside a kind's class body; the class turns it into an instance."""
    return ValueSpec(kwargs)


class _DeclaredValuesNamespace(dict[str, Any]):
    """The class namespace that answers the declaring type's own name with the factory."""

    def __init__(self, name: str, factory: Any) -> None:
        """Remember the class name and the factory this namespace answers with."""
        super().__init__()
        self._name = name
        self._factory = factory

    def __getitem__(self, key: str) -> Any:
        """Return the stored value, or the declaration factory for the class's own name."""
        try:
            return super().__getitem__(key)
        except KeyError:
            if key == self._name:
                return self._factory
            raise


class DeclaredValuesMeta(ModelMetaclass):
    """Metaclass of a declaring kind: the class's own name is the declaration factory."""

    @classmethod
    def __prepare__(mcs, *args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: N804
        """Give the class body the alias before the class itself exists."""
        _ = mcs  # the metaclass is bound by the class machinery; the name keeps the pylint contract
        name = args[0] if args else kwargs.get("name", "")
        return _DeclaredValuesNamespace(str(name), value)


class _DeclaredValues:
    """
    Mixin: the declaration factory, the catalogue and the conversion of placeholders.

    A kind inheriting this mixin states three things about its own values:
    whether a class without values of its own inherits the parent's catalogue
    (``__declared_values_inherit__``), whether a decorated class must declare at
    least one value (``__declared_values_require_any__``), and what the duplicate
    refusal calls the values (``__declared_values_noun__``).
    """

    __declared_values_inherit__: ClassVar[bool] = True
    __declared_values_require_any__: ClassVar[bool] = False
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
        cls.entity_type = cls
        specs = {name: spec for name, spec in cls.__dict__.items() if isinstance(spec, ValueSpec)}

        if not specs:
            if not cls.__declared_values_inherit__:
                cls.members = ()
                cls._by_code = {}
            return

        for name, spec in specs.items():
            setattr(cls, name, cls(**spec.kwargs))
        members = tuple(getattr(cls, name) for name in specs)
        codes = [member.code for member in members]
        if len(codes) != len(set(codes)):
            duplicates = sorted({code for code in codes if codes.count(code) > 1})
            raise ValueError(f"{cls.__name__}: duplicate {cls.__declared_values_noun__} code(s) in {duplicates}.")
        cls.members = members
        cls._by_code = {member.code: member for member in members}

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
