# src/action_machine/intents/depends/depends_decorator.py
"""
``@depends`` decorator — declare class-level dependency requirements.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Attach dependency declarations to a class. At runtime, the dependency list is
read from the ``depends`` snapshot, converted into ``DependencyFactory``, and
exposed through ``ToolsBox``. Aspects then resolve dependencies via
``box.resolve(PaymentService)``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @depends(PaymentService, description="Payment service")
         │
         ▼  writes scratch on cls
    DependencyInfo(cls=PaymentService, description="Payment service")
         │
         ▼  DependencyIntentInspector reads _depends_info
    coordinator snapshot → tuple[DependencyInfo, ...]
         │
         ▼  cached_dependency_factory(coordinator, cls)
    DependencyFactory built from snapshot
         │
         ▼  ToolsBox.resolve(PaymentService)
    factory.resolve(PaymentService) -> PaymentService()

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to classes (``type``).
- The ``klass`` argument must be a class (type) and a subclass of the bound
  defined in ``DependencyIntent[T]``.
- Duplicate dependency declarations on the same class are forbidden.
- When first applied to a subclass, the decorator copies the parent's
  ``_depends_info`` list so that adding new dependencies does not mutate the
  parent.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Basic usage
    @depends(PaymentService, description="Payment processing service")
    @depends(NotificationService, description="Notification service")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        @regular_aspect("Process payment")
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

    # Singleton via lambda
    _shared_payment = PaymentService(gateway="production")

    @depends(PaymentService, factory=lambda: _shared_payment, description="Singleton")
    class OrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    # Parameterized factory
    @depends(BankClient, factory=lambda env: BankClient(env), description="Bank client")
    class PayAction(BaseAction[PayParams, PayResult]):
        @regular_aspect("Pay")
        async def pay(self, params, state, box, connections):
            client = box.resolve(BankClient, "production")
            ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``TypeError`` if ``klass`` is not a class, does not satisfy the bound, the
  decorator is applied to a non-class, or ``description`` is not a string.
- ``ValueError`` if the same dependency is declared multiple times on the same
  class.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Dependency declaration decorator.
CONTRACT: @depends(klass, *, factory=None, description="") writes DependencyInfo to cls._depends_info.
INVARIANTS: Intent marker required; bound check; duplicate prevention.
FLOW: validate args → validate target → copy parent list if needed → append DependencyInfo.
FAILURES: TypeError / ValueError as described.
EXTENSION POINTS: Custom factory callables allow arbitrary instantiation policies.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.runtime.dependency_factory import DependencyInfo


def depends(
    klass: Any,
    *,
    factory: Callable[..., Any] | None = None,
    description: str = "",
) -> Callable[[type], type]:
    """
    Class decorator that declares a dependency on an external service.

    Writes a ``DependencyInfo`` record into the target class's ``_depends_info``
    list. When first applied to a subclass, copies the parent list to avoid
    mutation.

    Args:
        klass: Dependency class (must be a type and satisfy the bound).
        factory: Optional factory for creating the instance.
        description: Human‑readable description for documentation.

    Returns:
        A decorator that adds ``DependencyInfo`` to ``cls._depends_info``.

    Raises:
        TypeError: Invalid argument types, target not a class, or missing intent.
        ValueError: Duplicate dependency declaration.

    AI-CORE-BEGIN
    PURPOSE: Entry point for dependency declaration grammar on classes.
    INPUT/OUTPUT: Accepts dependency class metadata and returns a class decorator.
    SIDE EFFECTS: Writes ``DependencyInfo`` entries into ``cls._depends_info``.
    FAILURES: Raises ``TypeError``/``ValueError`` on contract violations.
    ORDER: Applied at class definition time before coordinator graph build.
    AI-CORE-END
    """
    # ── Validate decorator arguments ──

    if not isinstance(klass, type):
        raise TypeError(
            f"@depends expects a class, got {type(klass).__name__}: {klass!r}. "
            f"Pass a class, not an instance or string."
        )

    if not isinstance(description, str):
        raise TypeError(
            f"@depends: parameter 'description' must be a string, "
            f"got {type(description).__name__}."
        )

    def decorator(cls: type) -> type:
        """
        Inner decorator applied to the target class.

        Validates:
        1. ``cls`` is a class.
        2. ``klass`` is a subclass of the dependency bound (``object`` if the
           class does not define ``get_depends_bound``, e.g. without
           ``DependencyIntent`` in the MRO).
        3. No duplicate declarations.

        Then appends ``DependencyInfo`` to ``cls._depends_info``.
        """
        # ── Validate target ──
        if not isinstance(cls, type):
            raise TypeError(
                f"@depends can only be applied to a class. "
                f"Got object of type {type(cls).__name__}: {cls!r}."
            )

        bound = (
            cls.get_depends_bound()
            if hasattr(cls, "get_depends_bound")
            else object
        )
        if not issubclass(klass, bound):
            raise TypeError(
                f"@depends({klass.__name__}): class {klass.__name__} "
                f"is not a subclass of {bound.__name__}. "
                f"For {cls.__name__}, only subclasses of {bound.__name__} are allowed."
            )

        # ── Create own dependency list ──
        if '_depends_info' not in cls.__dict__:
            cls._depends_info = list(getattr(cls, '_depends_info', []))

        # ── Check for duplicates ──
        if any(info.cls is klass for info in cls._depends_info):
            raise ValueError(
                f"@depends({klass.__name__}) already declared for class {cls.__name__}. "
                f"Remove the duplicate decorator."
            )

        # ── Register dependency ──
        cls._depends_info.append(
            DependencyInfo(cls=klass, factory=factory, description=description)
        )

        return cls

    return decorator
