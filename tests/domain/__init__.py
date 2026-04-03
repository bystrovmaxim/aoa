# tests/domain/__init__.py
"""
Единая тестовая доменная модель ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все компоненты тестовой доменной модели: бизнес-домены,
сервисы-зависимости, ресурсные менеджеры и действия (Action)
с вложенными Params/Result. Каждый компонент — в отдельном файле.

Эта модель используется ВСЕМИ тестами в пакете tests/. Если тесту
нужен рабочий Action — он импортирует его отсюда. Если тесту нужен
намеренно сломанный Action (без @meta, без summary) — он создаёт
его внутри тестового файла.

═══════════════════════════════════════════════════════════════════════════════
КАТАЛОГ ДЕЙСТВИЙ
═══════════════════════════════════════════════════════════════════════════════

PingAction              — только summary, ROLE_NONE, без зависимостей.
SimpleAction            — 1 regular (чекер string) + summary, ROLE_NONE.
FullAction              — 2 regular (чекеры string + float) + summary,
                          depends (PaymentService, NotificationService),
                          connection ("db"), роль "manager".
ChildAction             — 1 regular + summary, ROLE_NONE, для box.run().
AdminAction             — 1 regular + summary, роль "admin".
ErrorHandledAction      — 1 regular + summary + @on_error(ValueError).
MultiErrorAction        — 1 regular + summary + 3 @on_error (специфичный → общий).
NoErrorHandlerAction    — 1 regular + summary, без @on_error.
HandlerRaisesAction     — 1 regular + summary + @on_error, обработчик бросает исключение.

═══════════════════════════════════════════════════════════════════════════════
ПОЛЬЗОВАТЕЛЬСКИЕ ИСКЛЮЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

InsufficientFundsError  — недостаточно средств на счёте.
PaymentGatewayError     — ошибка платёжного шлюза.

═══════════════════════════════════════════════════════════════════════════════
РАСШИРЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Новый Action добавляется в отдельный файл в этой папке, затем
импортируется и реэкспортируется в этом __init__.py.
"""

from .admin_action import AdminAction
from .child_action import ChildAction
from .domains import OrdersDomain, SystemDomain
from .error_actions import (
    ErrorHandledAction,
    ErrorTestParams,
    ErrorTestResult,
    HandlerRaisesAction,
    InsufficientFundsError,
    MultiErrorAction,
    NoErrorHandlerAction,
    PaymentGatewayError,
)
from .full_action import FullAction
from .ping_action import PingAction
from .services import NotificationService, PaymentService
from .simple_action import SimpleAction
from .test_db_manager import TestDbManager

__all__ = [
    "AdminAction",
    "ChildAction",
    "ErrorHandledAction",
    "ErrorTestParams",
    "ErrorTestResult",
    "FullAction",
    "HandlerRaisesAction",
    "InsufficientFundsError",
    "MultiErrorAction",
    "NoErrorHandlerAction",
    "NotificationService",
    "OrdersDomain",
    "PaymentGatewayError",
    "PaymentService",
    "PingAction",
    "SimpleAction",
    "SystemDomain",
    "TestDbManager",
]
