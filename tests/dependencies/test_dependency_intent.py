# tests/dependencies/test_dependency_intent.py
"""
Tests for ``DependencyIntent`` — marker mixin for ``@depends``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DependencyIntent[T]`` does two jobs:

1. **Marker:** ``@depends`` requires the target class to inherit ``DependencyIntent``.
   Otherwise ``TypeError``.

2. **Bound:** type parameter ``T`` limits which dependency classes are allowed.
   ``@depends`` checks ``issubclass(klass, bound)`` on every use.

The bound is taken from generic ``DependencyIntent[T]`` in ``__init_subclass__``
via ``_extract_bound``. If ``T`` is a concrete type, it wins; if ``T`` is a
``TypeVar`` or missing, the bound is inherited from the parent or falls back to
``object``.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

``_extract_bound``:
    - Class with ``DependencyIntent[object]`` -> bound = ``object``.
    - Class with ``DependencyIntent[SomeType]`` -> bound = ``SomeType``.
    - Subclass without its own generic -> bound inherited from parent.
    - Class without ``__orig_bases__`` and no bound-bearing parent -> ``object``.

``get_depends_bound``:
    - Returns the bound set in ``__init_subclass__``.
    - On a class without ``_depends_bound``, falls back to ``object`` (via ``getattr``).

Integration with ``BaseAction``:
    - ``BaseAction`` extends ``DependencyIntent[object]``, so bound = ``object``.
    - Domain actions inherit that bound from ``BaseAction``.
"""


from action_machine.dependencies.dependency_intent import (
    DependencyIntent,
    _extract_bound,
)
from action_machine.resources.base_resource_manager import BaseResourceManager
from tests.scenarios.domain_model import FullAction, PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — test-only classes, not part of the production domain.
# Defined here to exercise bound extraction.
# ─────────────────────────────────────────────────────────────────────────────


class _AnyDepsHost(DependencyIntent[object]):
    """Host with bound ``object`` — any dependency type allowed."""
    pass


class _ResourceOnlyHost(DependencyIntent[BaseResourceManager]):
    """Host with bound ``BaseResourceManager`` — resource managers only."""
    pass


class _ChildOfResourceHost(_ResourceOnlyHost):
    """Subclass without its own generic — bound inherited from parent."""
    pass


class _GrandchildOfResourceHost(_ChildOfResourceHost):
    """Grandchild — bound inherited through the MRO chain."""
    pass


class _PlainClass:
    """Plain class with no ``DependencyIntent`` in the MRO."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# _extract_bound — read bound from generic parameter
# ═════════════════════════════════════════════════════════════════════════════


class TestExtractBound:
    """Covers all branches of ``_extract_bound``."""

    def test_object_bound(self) -> None:
        """``DependencyIntent[object]`` -> bound is ``object``."""
        bound = _extract_bound(_AnyDepsHost)

        assert bound is object

    def test_specific_bound(self) -> None:
        """``DependencyIntent[BaseResourceManager]`` -> bound is ``BaseResourceManager``."""
        bound = _extract_bound(_ResourceOnlyHost)

        assert bound is BaseResourceManager

    def test_inherited_bound(self) -> None:
        """Subclass without its own generic inherits the parent's bound."""
        bound = _extract_bound(_ChildOfResourceHost)

        assert bound is BaseResourceManager

    def test_grandchild_inherited_bound(self) -> None:
        """Grandchild inherits bound through the MRO chain."""
        bound = _extract_bound(_GrandchildOfResourceHost)

        assert bound is BaseResourceManager

    def test_plain_class_returns_object(self) -> None:
        """Class without ``DependencyIntent`` ancestors -> ``object``."""
        bound = _extract_bound(_PlainClass)

        assert bound is object


# ═════════════════════════════════════════════════════════════════════════════
# get_depends_bound — classmethod
# ═════════════════════════════════════════════════════════════════════════════


class TestGetDependsBound:
    """Covers ``get_depends_bound``."""

    def test_returns_bound_for_host(self) -> None:
        """Returns the bound installed in ``__init_subclass__``."""
        bound = _ResourceOnlyHost.get_depends_bound()

        assert bound is BaseResourceManager

    def test_returns_object_for_any_host(self) -> None:
        """``DependencyIntent[object]`` -> ``get_depends_bound()`` is ``object``."""
        bound = _AnyDepsHost.get_depends_bound()

        assert bound is object

    def test_returns_object_for_class_without_attr(self) -> None:
        """Plain class: no ``_depends_bound`` — emulate fallback with ``getattr``."""
        bound = getattr(_PlainClass, "_depends_bound", object)

        assert bound is object


# ═════════════════════════════════════════════════════════════════════════════
# BaseAction integration
# ═════════════════════════════════════════════════════════════════════════════


class TestBaseActionIntegration:
    """Bound inheritance from ``BaseAction`` to domain actions."""

    def test_ping_action_bound_is_object(self) -> None:
        """``PingAction`` gets ``DependencyIntent[object]`` through ``BaseAction``."""
        bound = PingAction.get_depends_bound()

        assert bound is object

    def test_full_action_bound_is_object(self) -> None:
        """``FullAction`` with ``@depends`` still has bound ``object``."""
        bound = FullAction.get_depends_bound()

        assert bound is object

    def test_ping_action_is_dependency_intent(self) -> None:
        """``PingAction`` is a subclass of ``DependencyIntent``."""
        assert issubclass(PingAction, DependencyIntent)

    def test_plain_class_is_not_dependency_intent(self) -> None:
        """A plain class is not a ``DependencyIntent`` subclass."""
        assert not issubclass(_PlainClass, DependencyIntent)
