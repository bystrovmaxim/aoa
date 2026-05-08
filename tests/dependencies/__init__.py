# tests/dependencies/__init__.py
"""
Tests for the ActionMachine dependency-injection subsystem.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers two dependency components:

1. **DependencyFactory** — stateless factory for instances of classes declared
   with ``@depends``. Supports default constructors and custom factory callables,
   rollup checks for ``BaseResource``, and both ``DependencyInfo`` and
   legacy dict input shapes.

2. **DependsIntent** — generic marker mixin enabling ``@depends``. Type
   parameter ``T`` (or ``T1 | T2 | ...``) is the **bound**: every declared
   dependency must be a subclass of at least one allowed type.
   ``DependsIntent._extract_bound`` reads that parameter from ``DependsIntent[...]``
   in ``__init_subclass__``. ``BaseAction`` uses ``DependsIntent[DependsEligible]``.

═══════════════════════════════════════════════════════════════════════════════
TEST MODULES
═══════════════════════════════════════════════════════════════════════════════

- ``test_depends_intent.py`` — ``DependsIntent._extract_bound`` for ``DependsIntent[object]``,
  ``DependsIntent[concrete_type]``, unions, bound inheritance from parent, class
  without ``DependsIntent`` -> ``object``, ``get_depends_bound()`` /
  ``get_depends_bounds()``, integration with ``BaseAction`` (``PingAction``,
  ``FullAction``).

- ``test_depends_decorator_validation.py`` — ``@depends`` argument and target validation.

- Scenarios under ``tests/scenarios/dependencies/`` — ``DependencyFactory`` unit tests
  (``test_dependency_factory.py``, ``test_dependency_factory_core_machine.py``). Scenarios live
  separately so imports may use ``action_machine.runtime`` without violating the
  ``tests/dependencies`` layer rule.

═══════════════════════════════════════════════════════════════════════════════
DOMAIN MODEL
═══════════════════════════════════════════════════════════════════════════════

Working actions (``PingAction``, ``FullAction``, …) are imported from
``tests/scenarios/domain_model/``. Deliberately broken helper classes
(``_SimpleService``, ``_FakeResourceManager``, ``_AnyDepsHost``,
``_ResourceOnlyHost``, …) live inside individual test modules and are not part
of the production domain.
"""
