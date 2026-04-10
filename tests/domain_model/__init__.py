# tests/domain_model/__init__.py
"""
Shared test domain model for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Central export point for reusable test Actions, domains, services, and plugins.
Use these classes when tests need a working Action pipeline. Intentionally
broken edge-case Actions should stay local to the test module.

═══════════════════════════════════════════════════════════════════════════════
ACTIONS
═══════════════════════════════════════════════════════════════════════════════

PingAction              — summary only, ROLE_NONE.
SimpleAction            — regular + summary, ROLE_NONE.
FullAction              — two regular + summary, depends + connection("db"), role "manager".
ChildAction             — nested call target for box.run().
AdminAction             — admin-only Action.

═══════════════════════════════════════════════════════════════════════════════
ERROR-HANDLING ACTIONS (@on_error)
═══════════════════════════════════════════════════════════════════════════════

ErrorHandledAction      — catches ValueError.
MultiErrorAction        — three handlers (specific → general).
NoErrorHandlerAction    — no handler; errors propagate.
HandlerRaisesAction     — handler itself raises.

═══════════════════════════════════════════════════════════════════════════════
COMPENSATION ACTIONS (@compensate)
═══════════════════════════════════════════════════════════════════════════════

CompensatedOrderAction      — baseline reverse-order unwind.
PartialCompensateAction     — skipped frames (no compensator on some aspects).
CompensateErrorAction       — compensator failure suppression.
CompensateAndOnErrorAction  — order: compensate first, then @on_error.
CompensateWithContextAction — compensator receives ContextView.

═══════════════════════════════════════════════════════════════════════════════
CUSTOM EXCEPTIONS
═══════════════════════════════════════════════════════════════════════════════

InsufficientFundsError  — not enough balance.
PaymentGatewayError     — payment gateway failure.

═══════════════════════════════════════════════════════════════════════════════
DEPENDENCY SERVICES
═══════════════════════════════════════════════════════════════════════════════

PaymentService          — payments (charge, refund).
NotificationService     — notifications (send).
InventoryService        — inventory (reserve, unreserve).

═══════════════════════════════════════════════════════════════════════════════
OBSERVER PLUGINS
═══════════════════════════════════════════════════════════════════════════════

ErrorObserverPlugin     — records aspect error events into plugin state.
ErrorCounterPlugin      — counts handled vs unhandled aspect errors.
SagaObserverPlugin      — records all five compensation event types into state.

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This package is test-only. It does not define production behavior or adapter
contracts. Add new reusable test Actions in separate modules and re-export them
from this file.
"""

from .admin_action import AdminAction
from .child_action import ChildAction
from .compensate_actions import (
    CompensateAndOnErrorAction,
    CompensatedOrderAction,
    CompensateErrorAction,
    CompensateTestParams,
    CompensateTestResult,
    CompensateWithContextAction,
    PartialCompensateAction,
)
from .compensate_plugins import SagaObserverPlugin
from .domains import OrdersDomain, SystemDomain
from .error_actions import (
    ErrorHandledAction,
    ErrorTestParams,
    ErrorTestResult,
    HandlerRaisesAction,
    MultiErrorAction,
    NoErrorHandlerAction,
)
from .error_plugins import ErrorCounterPlugin, ErrorObserverPlugin
from .full_action import FullAction
from .ping_action import PingAction
from .services import InventoryService, NotificationService, PaymentService
from .simple_action import SimpleAction
from .test_db_manager import TestDbManager

__all__ = [
    # Base actions
    "PingAction",
    "SimpleAction",
    "FullAction",
    "ChildAction",
    "AdminAction",
    # Actions with @on_error
    "ErrorHandledAction",
    "MultiErrorAction",
    "NoErrorHandlerAction",
    "HandlerRaisesAction",
    # Actions with @compensate
    "CompensatedOrderAction",
    "CompensateAndOnErrorAction",
    "CompensateErrorAction",
    "CompensateWithContextAction",
    "PartialCompensateAction",
    # Params/Result
    "CompensateTestParams",
    "CompensateTestResult",
    "ErrorTestParams",
    "ErrorTestResult",
    # Plugins
    "ErrorCounterPlugin",
    "ErrorObserverPlugin",
    "SagaObserverPlugin",
    # Domains
    "OrdersDomain",
    "SystemDomain",
    # Services
    "InventoryService",
    "NotificationService",
    "PaymentService",
    "TestDbManager",
]
