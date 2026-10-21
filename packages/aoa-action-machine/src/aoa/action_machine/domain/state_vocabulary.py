# packages/aoa-action-machine/src/aoa/action_machine/domain/state_vocabulary.py
"""
StateVocabulary — the status attributes of one lifecycle axis.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collect the status objects declared as class attributes of a lifecycle axis,
validate them at class creation, and expose them by code. Applied as a mixin on
the same class declaration as ``Lifecycle``::

    class SalesOrderLifecycle(Lifecycle, StateVocabulary):
        NEW = OrderStateEntity(code="new", display_name="New")
        _template = Lifecycle().state(NEW).initial()

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Member collection in declaration order, the shared status type, lookup by
    code, and the checks that a mistyped axis fails at class creation: duplicate
    codes, mixed status types, an axis without statuses, and a status used in
    the template but not declared on the class.

**Out of scope**
    Classification and transitions — they belong to the lifecycle template.
    The graph and the diagrams — they read the template, not this mixin.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class body                  __init_subclass__                  consumers
    NEW = OrderStateEntity…  ──► collect status attributes     ──► members, entity_type,
    _template = Lifecycle()… ──► check template membership     ──► by_code(code), codes()

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

    The members share one status type; codes are unique; the API is plain
    methods, so lifecycle instances inherit nothing from this mixin; a subclass
    that declares no statuses inherits its parent's members.
"""

from __future__ import annotations

from typing import Any, ClassVar

from aoa.action_machine.domain.lifecycle import Lifecycle
from aoa.action_machine.domain.state_entity import BaseStateEntity


class StateVocabulary:
    """
    AI-CORE-BEGIN
        ROLE: Mixin for a lifecycle axis — collects its status attributes and checks them at class creation.
        CONTRACT: Applied next to ``Lifecycle``; members are plain ``BaseStateEntity`` class attributes; the template in the same class may name only members.
        INVARIANTS: Members share one type; codes are unique; the API is plain methods only; a subclass with no statuses inherits the parent's members.
    AI-CORE-END
    """

    members: ClassVar[tuple[BaseStateEntity, ...]] = ()
    entity_type: ClassVar[type[BaseStateEntity]] = BaseStateEntity
    _by_code: ClassVar[dict[str, BaseStateEntity]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect and validate the status attributes of the axis class."""
        super().__init_subclass__(**kwargs)
        if not issubclass(cls, Lifecycle):
            raise TypeError(f"{cls.__name__}: StateVocabulary must be applied to a Lifecycle subclass.")

        declared = tuple(value for value in cls.__dict__.values() if isinstance(value, BaseStateEntity))
        if not declared:
            if "_template" not in cls.__dict__:
                return
            raise ValueError(f"{cls.__name__}: an axis must declare at least one status.")

        codes = [member.code for member in declared]
        if len(codes) != len(set(codes)):
            duplicates = sorted({code for code in codes if codes.count(code) > 1})
            raise ValueError(f"{cls.__name__}: duplicate status code(s) in {duplicates}.")

        types = {type(member) for member in declared}
        if len(types) != 1:
            names = sorted(kind.__name__ for kind in types)
            raise TypeError(f"{cls.__name__}: statuses of different types {names}.")

        cls.members = declared
        cls.entity_type = types.pop()
        cls._by_code = {member.code: member for member in declared}

        template = cls.__dict__.get("_template")
        if template is not None:
            referenced = [
                *template.get_state_entities().values(),
                *template.get_transition_entities().values(),
            ]
            unknown = [entity for entity in referenced if entity not in declared]
            if unknown:
                raise TypeError(f"{cls.__name__}: {unknown[0]!r} is not a status of this lifecycle.")

    @classmethod
    def by_code(cls, code: str) -> BaseStateEntity:
        """Return the status declared under ``code``."""
        return cls._by_code[code]

    @classmethod
    def codes(cls) -> list[str]:
        """Return the status codes in declaration order."""
        return [member.code for member in cls.members]
