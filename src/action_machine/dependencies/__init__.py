# src/action_machine/dependencies/__init__.py
"""
ActionMachine dependencies package public exports.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the dependency declaration and resolution surface used by actions.
Dependencies are declared with ``@depends`` on classes that implement
``DependencyIntent``. The framework validates declarations and provides a
stateless ``DependencyFactory`` to ``ToolsBox`` for runtime resolution.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Action class declaration
    @depends(PaymentService)
         │
         ▼  writes scratch on cls
    cls._depends_info = [DependencyInfo(cls=PaymentService, ...)]
         │
         ▼  DependencyIntentInspector reads _depends_info
    coordinator.get_snapshot(cls, "depends") → tuple[DependencyInfo, ...]
         │
         ▼  cached_dependency_factory(coordinator, cls)
    DependencyFactory(dependencies) created and cached on coordinator
         │
         ▼  ToolsBox.resolve(PaymentService)
    factory.resolve(PaymentService) -> new instance (or singleton via lambda)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``@depends`` can only be applied to classes inheriting ``DependencyIntent``.
- ``DependencyInfo`` is immutable and stores the dependency class, an optional
  factory, and a human-readable description.
- ``DependencyFactory`` is stateless: each ``resolve()`` creates a new instance.
  Singletons must be implemented by the user via a lambda factory.
- The factory cache is keyed by action class and stored on the ``GraphCoordinator``
  instance dictionary.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Declare dependencies on an action
    @depends(PaymentService, description="Payment processing service")
    @depends(NotificationService, factory=lambda: shared_notifier)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        @regular_aspect("Process payment")
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

    # Resolve with runtime arguments (passed to factory or constructor)
    client = box.resolve(BankClient, environment="production")

    # Rollup-aware resolve (checks BaseResourceManager support)
    db = box.resolve(DbService, rollup=True)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``@depends`` is applied to a class missing ``DependencyIntent``,
  if the dependency class is not a subclass of the bound defined in
  ``DependencyIntent[T]``, or if duplicate declarations are found.
- ``ValueError`` if a dependency is not found during resolution.
- ``RollupNotSupportedError`` when ``resolve(..., rollup=True)`` is called on a
  ``BaseResourceManager`` that does not support transactional rollback.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public API surface for dependency declarations and runtime resolution.
CONTRACT: Export dependency decorator, intent marker, factory, and cache helpers.
INVARIANTS: intent-based declaration; stateless factory; snapshot-backed metadata.
FLOW: @depends → inspector → coordinator snapshot → cached factory → ToolsBox resolution.
FAILURES: Declaration‑time TypeError/ValueError; resolution‑time ValueError/RollupNotSupportedError.
EXTENSION POINTS: Custom factory implementations can replace the default resolution logic.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.runtime.dependency_factory import (
    DependencyFactory,
    DependencyInfo,
    cached_dependency_factory,
    clear_dependency_factory_cache,
)
from action_machine.legacy.dependency_intent import DependencyIntent
from action_machine.intents.depends import depends

__all__ = [
    "DependencyFactory",
    "DependencyInfo",
    "DependencyIntent",
    "cached_dependency_factory",
    "clear_dependency_factory_cache",
    "depends",
]
