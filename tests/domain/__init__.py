# tests/domain/__init__.py
"""
Единая тестовая доменная модель ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все компоненты тестовой доменной модели: бизнес-домены,
сервисы-зависимости, ресурсные менеджеры, действия (Action) с вложенными
Params/Result и плагины-наблюдатели. Каждый компонент — в отдельном файле.

Эта модель используется ВСЕМИ тестами в пакете tests/. Если тесту
нужен рабочий Action — он импортирует его отсюда. Если тесту нужен
намеренно сломанный Action (без @meta, без summary, с неправильным
порядком обработчиков) — он создаёт его внутри тестового файла.

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

═══════════════════════════════════════════════════════════════════════════════
КАТАЛОГ ДЕЙСТВИЙ С ОБРАБОТЧИКАМИ ОШИБОК (@on_error)
═══════════════════════════════════════════════════════════════════════════════

ErrorHandledAction      — 1 regular + summary + @on_error(ValueError).
MultiErrorAction        — 1 regular + summary + 3 @on_error (специфичный → общий).
NoErrorHandlerAction    — 1 regular + summary, без @on_error.
HandlerRaisesAction     — 1 regular + summary + @on_error, обработчик бросает исключение.

═══════════════════════════════════════════════════════════════════════════════
КАТАЛОГ ДЕЙСТВИЙ С КОМПЕНСАТОРАМИ (@compensate)
═══════════════════════════════════════════════════════════════════════════════

CompensatedOrderAction      — 2 regular с компенсаторами + 1 regular без + summary.
                              Тестирует базовую размотку стека в обратном порядке.
PartialCompensateAction     — 3 regular, компенсатор только у первого + summary.
                              Тестирует skipped-фреймы при размотке.
CompensateErrorAction       — 2 regular с компенсаторами (первый бросает) + 1 regular + summary.
                              Тестирует молчаливое подавление ошибок компенсаторов.
CompensateAndOnErrorAction  — 2 regular с компенсаторами + 1 regular + summary + @on_error.
                              Тестирует порядок: компенсация → @on_error.
CompensateWithContextAction — 1 regular с компенсатором + @context_requires + 1 regular + summary.
                              Тестирует передачу ContextView в компенсатор.

═══════════════════════════════════════════════════════════════════════════════
ПОЛЬЗОВАТЕЛЬСКИЕ ИСКЛЮЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

InsufficientFundsError  — недостаточно средств на счёте.
PaymentGatewayError     — ошибка платёжного шлюза.

═══════════════════════════════════════════════════════════════════════════════
СЕРВИСЫ-ЗАВИСИМОСТИ
═══════════════════════════════════════════════════════════════════════════════

PaymentService          — сервис обработки платежей (charge, refund).
NotificationService     — сервис отправки уведомлений (send).
InventoryService        — сервис управления запасами (reserve, unreserve).

═══════════════════════════════════════════════════════════════════════════════
ПЛАГИНЫ-НАБЛЮДАТЕЛИ
═══════════════════════════════════════════════════════════════════════════════

ErrorObserverPlugin     — записывает события ошибок аспектов в state.
ErrorCounterPlugin      — считает количество обработанных/необработанных ошибок.
SagaObserverPlugin      — записывает все 5 типов событий компенсации в state.

═══════════════════════════════════════════════════════════════════════════════
РАСШИРЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Новый Action добавляется в отдельный файл в этой папке, затем
импортируется и реэкспортируется в этом __init__.py.
"""

from .admin_action import AdminAction
from .child_action import ChildAction
from .compensate_actions import (
    CompensateAndOnErrorAction,
    CompensateErrorAction,
    CompensatedOrderAction,
    CompensateTestParams,
    CompensateTestResult,
    CompensateWithContextAction,
    InventoryService,
    PartialCompensateAction,
)
from .compensate_plugins import SagaObserverPlugin
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
from .error_plugins import ErrorCounterPlugin, ErrorObserverPlugin
from .full_action import FullAction
from .ping_action import PingAction
from .services import NotificationService, PaymentService
from .simple_action import SimpleAction
from .test_db_manager import TestDbManager

__all__ = [
    # Домены
    "OrdersDomain",
    "SystemDomain",
    # Сервисы-зависимости
    "PaymentService",
    "NotificationService",
    "InventoryService",
    # Ресурсные менеджеры
    "TestDbManager",
    # Действия — базовые
    "PingAction",
    "SimpleAction",
    "FullAction",
    "ChildAction",
    "AdminAction",
    # Действия — обработка ошибок (@on_error)
    "ErrorHandledAction",
    "MultiErrorAction",
    "NoErrorHandlerAction",
    "HandlerRaisesAction",
    "ErrorTestParams",
    "ErrorTestResult",
    # Действия — компенсация (@compensate)
    "CompensatedOrderAction",
    "PartialCompensateAction",
    "CompensateErrorAction",
    "CompensateAndOnErrorAction",
    "CompensateWithContextAction",
    "CompensateTestParams",
    "CompensateTestResult",
    # Пользовательские исключения
    "InsufficientFundsError",
    "PaymentGatewayError",
    # Плагины-наблюдатели — ошибки
    "ErrorObserverPlugin",
    "ErrorCounterPlugin",
    # Плагины-наблюдатели — компенсация
    "SagaObserverPlugin",
]
