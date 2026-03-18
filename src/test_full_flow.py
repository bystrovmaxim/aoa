"""
Интеграционный тест, демонстрирующий полный цикл работы ActionMachine:
- создание контекста,
- определение действий с аспектами и логером,
- использование зависимостей (@depends),
- проверка ролей (@CheckRoles),
- плагин, подсчитывающий вызовы,
- логирование через ConsoleLogger.

Тест проверяет, что все компоненты работают вместе и результаты корректны.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Checkers.StringFieldChecker import StringFieldChecker
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import aspect, depends, summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Plugins.Decorators import on
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginEvent import PluginEvent
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


# ----------------------------------------------------------------------
# Вспомогательные классы: параметры, результаты, зависимости
# ----------------------------------------------------------------------

@dataclass
class OrderParams(BaseParams):
    """Параметры для создания заказа."""
    user_id: str
    amount: float
    currency: str = "RUB"


@dataclass
class OrderResult(BaseResult):
    """Результат создания заказа."""
    order_id: str
    status: str
    total: float


class PaymentService:
    """Сервис для обработки платежей (зависимость)."""

    def __init__(self, gateway: str = "default"):
        self.gateway = gateway
        self.processed = []

    async def charge(self, amount: float, currency: str) -> str:
        """Списание средств (имитация)."""
        self.processed.append((amount, currency))
        return f"txn_{len(self.processed)}"


class NotificationService:
    """Сервис уведомлений (зависимость)."""

    def __init__(self):
        self.sent = []

    async def notify(self, user_id: str, message: str) -> None:
        """Отправка уведомления (имитация)."""
        self.sent.append((user_id, message))


# ----------------------------------------------------------------------
# Плагин-счётчик вызовов
# ----------------------------------------------------------------------

class CounterPlugin(Plugin):
    """Плагин, подсчитывающий количество вызовов каждого действия."""

    def get_initial_state(self) -> dict[str, int]:
        """Начальное состояние — пустой счётчик."""
        return {}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count_call(self, state: dict[str, int], event: PluginEvent) -> dict[str, int]:
        """Увеличивает счётчик для данного действия."""
        action_name = event.action_name
        state[action_name] = state.get(action_name, 0) + 1
        return state


# ----------------------------------------------------------------------
# Действия
# ----------------------------------------------------------------------

@CheckRoles("user", desc="Пользователь может создавать заказы")
@depends(PaymentService, description="Сервис платежей")
@depends(NotificationService, description="Сервис уведомлений")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    """Действие создания заказа."""

    @aspect("Валидация суммы")
    async def validate_amount(
        self,
        params: OrderParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,  # ActionBoundLogger
    ) -> dict:
        """Проверяет, что сумма положительная."""
        await log.info("Validating amount -  sum:{%var.amount} user: {%context.user.user_id}", amount=params.amount)
        if params.amount <= 0:
            raise ValueError("Amount must be positive")
        # Возвращаем пустой словарь, так как ничего не добавляем в state
        return {}

    @aspect("Обработка платежа")
    @StringFieldChecker("txn_id", "Идентификатор транзакции", required=True)
    async def process_payment(
        self,
        params: OrderParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,
    ) -> dict:
        """Вызывает PaymentService для списания средств."""
        payment = deps.get(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        await log.info("Payment processed", txn_id=txn_id)
        # Возвращаем словарь с полем txn_id, для которого есть чекер
        return {"txn_id": txn_id}

    @summary_aspect("Формирование результата")
    async def build_result(
        self,
        params: OrderParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,
    ) -> OrderResult:
        """Создаёт результат и отправляет уведомление."""
        # Получаем данные из состояния
        txn_id = state.get("txn_id")
        # Отправляем уведомление
        notifier = deps.get(NotificationService)
        await notifier.notify(params.user_id, f"Order created, txn: {txn_id}")
        await log.info("Notification sent", user=params.user_id)
        return OrderResult(
            order_id=f"ORD_{params.user_id}_{id(params)}",
            status="created",
            total=params.amount,
        )


@CheckRoles(CheckRoles.NONE, desc="Проверка без аутентификации")
class PingAction(BaseAction[BaseParams, BaseResult]):
    """Простое действие без зависимостей."""

    @summary_aspect("Ответить pong")
    async def summary(
        self,
        params: BaseParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,
    ) -> BaseResult:
        await log.info("Ping received")
        result = BaseResult()
        result["message"] = "pong"
        return result


# ----------------------------------------------------------------------
# Интеграционный тест
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_full_flow():
    """Полный тест, запускающий действия с машиной, плагинами и логером."""

    # Создаём экземпляры действий для получения имён
    create_order_action = CreateOrderAction()
    ping_action = PingAction()

    # 1. Создаём контекст с пользователем
    user = UserInfo(user_id="bystrov.maxim", roles=["user"])
    context = Context(user=user)

    # 2. Настраиваем логер (консольный, с цветами)
    console_logger = ConsoleLogger(use_colors=True)
    log_coordinator = LogCoordinator(loggers=[console_logger])

    # 3. Создаём плагин-счётчик
    counter_plugin = CounterPlugin()

    # 4. Создаём машину
    machine = ActionProductMachine(
        context=context,
        mode="integration-test-01",
        plugins=[counter_plugin],
        log_coordinator=log_coordinator,
    )

    # 5. Создаём экземпляры зависимостей (внешние ресурсы)
    payment_service = PaymentService(gateway="stripe")
    notification_service = NotificationService()

    # 6. Формируем параметры для первого действия
    params1 = OrderParams(user_id="bystrov.maxim", amount=1500.0)

    # 7. Запускаем действие
    result1 = await machine.run(
        action=CreateOrderAction(),
        params=params1,
        resources={
            PaymentService: payment_service,
            NotificationService: notification_service,
        },
    )

    # 8. Проверки
    assert isinstance(result1, OrderResult)
    assert result1.status == "created"
    assert result1.total == 1500.0
    assert result1.order_id.startswith("ORD_bystrov.maxim_")

    # Проверяем, что зависимости были вызваны
    assert len(payment_service.processed) == 1
    assert payment_service.processed[0] == (1500.0, "RUB")
    assert len(notification_service.sent) == 1
    assert notification_service.sent[0] == ("bystrov.maxim", "Order created, txn: txn_1")

    # 9. Запускаем PingAction (без аутентификации)
    params2 = BaseParams()
    result2 = await machine.run(PingAction(), params2)

    assert result2["message"] == "pong"

    # 10. Проверяем состояние плагина-счётчика
    plugin_state = machine._plugin_coordinator._plugin_states[id(counter_plugin)]
    create_order_name = create_order_action.get_full_class_name()
    ping_name = ping_action.get_full_class_name()
    assert plugin_state.get(create_order_name) == 1
    assert plugin_state.get(ping_name) == 1

    # 11. Проверяем, что в логере были вызовы (опционально, можно проверить через захват stdout)
    # В данном тесте мы просто смотрим, что код выполнился без ошибок.
    # При запуске с флагом -s увидим цветной вывод логов.


if __name__ == "__main__":
    asyncio.run(test_full_flow())
    print("✅ Интеграционный тест пройден")