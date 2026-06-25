# tests/scenarios/domain_model/__init__.py
"""
Shared test domain model for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Central export point for reusable test Actions, domains, and services.
Use these classes when tests need a working Action pipeline. Intentionally
broken edge-case Actions should stay local to the test module.

═══════════════════════════════════════════════════════════════════════════════
ACTIONS
═══════════════════════════════════════════════════════════════════════════════

PingAction              — summary only, GuestRole.
SimpleAction            — regular + summary, GuestRole.
FullAction              — two regular + summary, ``@depends``/``@connection`` on ``OrdersDbManager``, role "manager".
ChildAction             — nested call target for box.run().
AdminAction             — admin-only Action.

═══════════════════════════════════════════════════════════════════════════════
ERROR-HANDLING ACTIONS (@on_error)
═══════════════════════════════════════════════════════════════════════════════

ErrorHandledAction      — catches ValueError.
HandlerRaisesAction     — handler itself raises.

═══════════════════════════════════════════════════════════════════════════════
COMPENSATION ACTIONS (@compensate)
═══════════════════════════════════════════════════════════════════════════════

CompensatedOrderAction      — baseline reverse-order unwind.
CompensateAndOnErrorAction  — order: compensate first, then @on_error.
CompensateWithContextAction — compensator receives ContextView.

═══════════════════════════════════════════════════════════════════════════════
DEPENDENCY SERVICES
═══════════════════════════════════════════════════════════════════════════════

PaymentService          — payments (charge, refund).
NotificationService     — notifications (send).
InventoryService        — inventory (reserve, unreserve).

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
    CompensateTestParams,
    CompensateTestResult,
    CompensateWithContextAction,
)
from .domains import OrdersDomain, SystemDomain
from .error_actions import (
    ErrorHandledAction,
    ErrorTestParams,
    ErrorTestResult,
    HandlerRaisesAction,
)
from .full_action import FullAction
from .ping_action import PingAction
from .services import (
    InventoryService,
    InventoryServiceResource,
    NotificationService,
    NotificationServiceResource,
    PaymentService,
    PaymentServiceResource,
)
from .simple_action import SimpleAction
from .test_db_manager import OrdersDbManager

__all__ = [
    "AdminAction",
    "ChildAction",
    "CompensateAndOnErrorAction",
    "CompensateTestParams",
    "CompensateTestResult",
    "CompensateWithContextAction",
    "CompensatedOrderAction",
    "ErrorHandledAction",
    "ErrorTestParams",
    "ErrorTestResult",
    "FullAction",
    "HandlerRaisesAction",
    "InventoryService",
    "InventoryServiceResource",
    "NotificationService",
    "NotificationServiceResource",
    "OrdersDbManager",
    "OrdersDomain",
    "PaymentService",
    "PaymentServiceResource",
    "PingAction",
    "SimpleAction",
    "SystemDomain",
]
