# tests/dependencies/test_depends_intent.py
"""
Tests for ``DependsIntent`` — marker mixin for ``@depends``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DependsIntent[T]`` does two jobs:

1. **Marker (optional):** Subclasses get ``get_depends_bound()`` from ``DependsIntent``;
   ``@depends`` still works on plain classes with bound ``object``.
   Otherwise ``TypeError``.

2. **Bound:** type parameter ``T`` (or ``T1 | T2 | ...``) limits which dependency
   classes are allowed. ``@depends`` checks ``klass`` against each allowed type.

The bound is taken from generic ``DependsIntent[T]`` in ``__init_subclass__``
via ``DependsIntent._extract_bound``. If ``T`` is a concrete type, it wins; if ``T`` is a
``TypeVar`` or missing, the bound is inherited from the parent or falls back to
``object``.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

``DependsIntent._extract_bound``:
    - Class with ``DependsIntent[object]`` -> bound = ``object``.
    - Class with ``DependsIntent[SomeType]`` -> bound = ``SomeType``.
    - Subclass without its own generic -> bound inherited from parent.
    - Class without ``__orig_bases__`` and no bound-bearing parent -> ``object``.

``get_depends_bound``:
    - Returns the bound set in ``__init_subclass__``.
    - On a class without ``_depends_bound``, falls back to ``object`` (via ``getattr``).

Integration with ``BaseAction``:
    - ``BaseAction`` extends ``DependsIntent[DependsEligible]``, so bound is ``DependsEligible``.
    - Domain actions inherit that bound from ``BaseAction``.
"""


from action_machine.intents.depends.depends_eligible import DependsEligible
from action_machine.intents.depends.depends_intent import DependsIntent
from action_machine.resources.base_resource import BaseResource
from tests.scenarios.domain_model import FullAction, PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — test-only classes, not part of the production domain.
# Defined here to exercise bound extraction.
# ─────────────────────────────────────────────────────────────────────────────


class _AnyDepsHost(DependsIntent[object]):
    """Host with bound ``object`` — any dependency type allowed."""
    pass


class _ResourceOnlyHost(DependsIntent[BaseResource]):
    """Host with bound ``BaseResource`` — resource managers only."""
    pass


class _ChildOfResourceHost(_ResourceOnlyHost):
    """Subclass without its own generic — bound inherited from parent."""
    pass


class _GrandchildOfResourceHost(_ChildOfResourceHost):
    """Grandchild — bound inherited through the MRO chain."""
    pass


class _BranchA:
    """First branch for union-bound tests."""
    pass


class _BranchB:
    """Second branch for union-bound tests."""
    pass


class _UnionABHost(DependsIntent[_BranchA | _BranchB]):
    """Host allowing dependencies that subclass either branch type."""
    pass


class _PlainClass:
    """Plain class with no ``DependsIntent`` in the MRO."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# DependsIntent._extract_bound — read bound from generic parameter
# ═════════════════════════════════════════════════════════════════════════════


class TestExtractBound:
    """Covers all branches of ``DependsIntent._extract_bound``."""

    def test_object_bound(self) -> None:
        """``DependsIntent[object]`` -> bound is ``object``."""
        bound = DependsIntent._extract_bound(_AnyDepsHost)

        assert bound is object

    def test_specific_bound(self) -> None:
        """``DependsIntent[BaseResource]`` -> bound is ``BaseResource``."""
        bound = DependsIntent._extract_bound(_ResourceOnlyHost)

        assert bound is BaseResource

    def test_inherited_bound(self) -> None:
        """Subclass without its own generic inherits the parent's bound."""
        bound = DependsIntent._extract_bound(_ChildOfResourceHost)

        assert bound is BaseResource

    def test_grandchild_inherited_bound(self) -> None:
        """Grandchild inherits bound through the MRO chain."""
        bound = DependsIntent._extract_bound(_GrandchildOfResourceHost)

        assert bound is BaseResource

    def test_plain_class_returns_object(self) -> None:
        """Class without ``DependsIntent`` ancestors -> ``object``."""
        bound = DependsIntent._extract_bound(_PlainClass)

        assert bound is object

    def test_union_bound(self) -> None:
        """``DependsIntent[A | B]`` -> PEP 604 union of ``A`` and ``B``."""
        bound = DependsIntent._extract_bound(_UnionABHost)

        assert bound == _BranchA | _BranchB


# ═════════════════════════════════════════════════════════════════════════════
# get_depends_bound — classmethod
# ═════════════════════════════════════════════════════════════════════════════


class TestGetDependsBound:
    """Covers ``get_depends_bound``."""

    def test_returns_bound_for_host(self) -> None:
        """Returns the bound installed in ``__init_subclass__``."""
        bound = _ResourceOnlyHost.get_depends_bound()

        assert bound is BaseResource

    def test_returns_object_for_any_host(self) -> None:
        """``DependsIntent[object]`` -> ``get_depends_bound()`` is ``object``."""
        bound = _AnyDepsHost.get_depends_bound()

        assert bound is object

    def test_returns_object_for_class_without_attr(self) -> None:
        """Plain class: no ``_depends_bound`` — emulate fallback with ``getattr``."""
        bound = getattr(_PlainClass, "_depends_bound", object)

        assert bound is object


# ═════════════════════════════════════════════════════════════════════════════
# get_depends_bounds — union flattening
# ═════════════════════════════════════════════════════════════════════════════


class TestGetDependsBounds:
    """Covers ``get_depends_bounds``."""

    def test_single_type_tuple(self) -> None:
        """Single-type bound flattens to a one-element tuple."""
        bounds = _ResourceOnlyHost.get_depends_bounds()

        assert bounds == (BaseResource,)

    def test_union_flattens_to_tuple(self) -> None:
        """Union bound becomes an ordered tuple of member types."""
        bounds = _UnionABHost.get_depends_bounds()

        assert bounds == (_BranchA, _BranchB)


class TestFlattenUnionMembers:
    """Covers ``DependsIntent._flatten_union_members``."""

    def test_nested_union_dedupes(self) -> None:
        """Nested unions flatten without duplicate types."""
        flat = DependsIntent._flatten_union_members(_BranchA | (_BranchB | _BranchA))

        assert flat == (_BranchA, _BranchB)


# ═════════════════════════════════════════════════════════════════════════════
# BaseAction integration
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseActionIntegration:
    """Bound inheritance from ``BaseAction`` to domain actions."""

    def test_ping_action_bound_is_depends_eligible(self) -> None:
        """``PingAction`` inherits ``DependsIntent[DependsEligible]`` through ``BaseAction``."""
        bound = PingAction.get_depends_bound()

        assert bound is DependsEligible

    def test_full_action_bound_is_depends_eligible(self) -> None:
        """``FullAction`` with ``@depends`` keeps the same ``DependsEligible`` bound."""
        bound = FullAction.get_depends_bound()

        assert bound is DependsEligible

    def test_ping_action_is_depends_intent(self) -> None:
        """``PingAction`` is a subclass of ``DependsIntent``."""
        assert issubclass(PingAction, DependsIntent)

    def test_plain_class_is_not_depends_intent(self) -> None:
        """A plain class is not a ``DependsIntent`` subclass."""
        assert not issubclass(_PlainClass, DependsIntent)
