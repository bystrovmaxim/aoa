# tests/dependencies/__init__.py
"""
Tests for the ActionMachine dependency-injection subsystem.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers two dependency components:

1. **DependencyFactory** — stateless factory for instances of classes declared
   with ``@depends``. Supports default constructors and custom factory callables,
   rollup checks for ``BaseResourceManager``, and both ``DependencyInfo`` and
   legacy dict input shapes.

2. **DependencyIntent** — generic marker mixin enabling ``@depends``. Type
   parameter ``T`` is the **bound**: every declared dependency must be a subclass
   of that bound. ``_extract_bound`` reads ``T`` from ``DependencyIntent[T]`` in
   ``__init_subclass__``.

═══════════════════════════════════════════════════════════════════════════════
TEST MODULES
═══════════════════════════════════════════════════════════════════════════════

- ``test_dependency_factory.py`` — ``resolve()`` with constructor and factory,
  ``*args``/``**kwargs``, undeclared dependency -> ``ValueError``, rollup checks
  for ``BaseResourceManager``, ``has()``, ``get_all_classes()``, legacy dict
  format, ``DependencyInfo`` immutability.

- ``test_dependency_intent.py`` — ``_extract_bound`` for ``DependencyIntent[object]``,
  ``DependencyIntent[concrete_type]``, bound inheritance from parent, class
  without ``DependencyIntent`` -> ``object``, ``get_depends_bound()``,
  integration with ``BaseAction`` (``PingAction``, ``FullAction``).

- ``test_depends_decorator_validation.py`` — ``@depends`` argument and target validation.

- Scenario with ``CoreActionMachine``:
  ``tests/scenarios/dependencies/test_dependency_factory_core_machine.py``.

═══════════════════════════════════════════════════════════════════════════════
DOMAIN MODEL
═══════════════════════════════════════════════════════════════════════════════

Working actions (``PingAction``, ``FullAction``, …) are imported from
``tests/scenarios/domain_model/``. Deliberately broken helper classes
(``_SimpleService``, ``_FakeResourceManager``, ``_AnyDepsHost``,
``_ResourceOnlyHost``, …) live inside individual test modules and are not part
of the production domain.
"""
