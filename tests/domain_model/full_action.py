# tests/domain/full_action.py
"""
FullAction — полнофункциональное действие с зависимостями и connections.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Самое сложное действие в тестовой доменной модели. Содержит два
regular-аспекта с чекерами, summary-аспект, две зависимости
(PaymentService, NotificationService) и одно connection ("db").
Требует роль "manager".

Покрывает максимальное количество сценариев: ролевые ограничения,
валидация connections, резолв зависимостей через box.resolve(),
чекеры на каждом аспекте, формирование result из state.

═══════════════════════════════════════════════════════════════════════════════
КОНВЕЙЕР АСПЕКТОВ
═══════════════════════════════════════════════════════════════════════════════

    1. process_payment (regular)
       - Резолвит PaymentService через box.resolve().
       - Вызывает payment.charge(amount, currency).
       - Записывает txn_id в state.
       - Чекер: result_string("txn_id", required=True, min_length=1).

    2. calc_total (regular)
       - Вычисляет итоговую сумму.
       - Записывает total в state.
       - Чекер: result_float("total", required=True, min_value=0.0).

    3. build_result (summary)
       - Резолвит NotificationService через box.resolve().
       - Отправляет уведомление пользователю.
       - Формирует Result из state (txn_id, total).

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

- Тесты ролей: только "manager" проходит, "user" — AuthorizationError.
- Тесты connections: "db" обязателен, лишние/недостающие ключи — ошибка.
- Тесты depends: PaymentService и NotificationService подменяются моками.
- Тесты чекеров: txn_id (string), total (float) проверяются.
- Тесты run_aspect: process_payment и calc_total по отдельности.
- Тесты run_summary: state с txn_id и total → Result.
- Тесты rollup: прокидывание rollup через resolve и connections.

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-001"
    mock_notification = AsyncMock(spec=NotificationService)
    mock_db = AsyncMock(spec=TestDbManager)

    bench = TestBench(
        mocks={PaymentService: mock_payment, NotificationService: mock_notification},
    ).with_user(user_id="mgr_1", roles=["manager"])

    result = await bench.run(
        FullAction(),
        FullAction.Params(user_id="user_123", amount=1500.0),
        rollup=False,
        connections={"db": mock_db},
    )
    assert result.order_id == "ORD-user_123"
    assert result.txn_id == "TXN-001"
"""

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import check_roles
from action_machine.checkers import result_float, result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.depends import depends
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection

from .domains import OrdersDomain
from .services import NotificationService, PaymentService
from .test_db_manager import TestDbManager


@meta(description="Создание заказа с оплатой и уведомлением", domain=OrdersDomain)
@check_roles("manager")
@depends(PaymentService, description="Сервис обработки платежей")
@depends(NotificationService, description="Сервис уведомлений")
@connection(TestDbManager, key="db", description="Основная БД")
class FullAction(BaseAction["FullAction.Params", "FullAction.Result"]):
    """
    Полнофункциональное действие: 2 regular + summary, depends, connection.

    Требует роль "manager". Зависимости: PaymentService, NotificationService.
    Connection: "db" (TestDbManager).
    """

    class Params(BaseParams):
        """Параметры создания заказа."""
        user_id: str = Field(
            description="Идентификатор пользователя",
            min_length=1,
            examples=["user_123"],
        )
        amount: float = Field(
            description="Сумма заказа",
            gt=0,
            examples=[1500.0],
        )
        currency: str = Field(
            default="RUB",
            description="Код валюты ISO 4217",
            pattern=r"^[A-Z]{3}$",
            examples=["RUB", "USD"],
        )

    class Result(BaseResult):
        """Результат создания заказа."""
        order_id: str = Field(description="Идентификатор созданного заказа")
        txn_id: str = Field(description="Идентификатор транзакции оплаты")
        total: float = Field(description="Итоговая сумма заказа")
        status: str = Field(description="Статус заказа")

    @regular_aspect("Обработка платежа")
    @result_string("txn_id", required=True, min_length=1)
    async def process_payment_aspect(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Списывает средства через PaymentService.

        Резолвит PaymentService из box, вызывает charge() с суммой
        и валютой из params. Записывает полученный txn_id в state.

        Возвращает:
            dict с ключом txn_id — идентификатор транзакции.
        """
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    @regular_aspect("Расчёт итоговой суммы")
    @result_float("total", required=True, min_value=0.0)
    async def calc_total_aspect(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Вычисляет итоговую сумму заказа.

        В текущей реализации итог равен сумме из params.
        В реальном проекте здесь может быть логика скидок, налогов и т.д.

        Возвращает:
            dict с ключом total — итоговая сумма.
        """
        return {"total": params.amount}

    @summary_aspect("Формирование результата заказа")
    async def build_result_summary(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "FullAction.Result":
        """
        Формирует итоговый результат из данных state.

        Резолвит NotificationService и отправляет уведомление
        пользователю о создании заказа. Собирает Result из
        txn_id и total, накопленных regular-аспектами.

        Возвращает:
            FullAction.Result с order_id, txn_id, total, status.
        """
        notification = box.resolve(NotificationService)
        await notification.send(params.user_id, f"Заказ создан: {state['txn_id']}")

        return FullAction.Result(
            order_id=f"ORD-{params.user_id}",
            txn_id=state["txn_id"],
            total=state["total"],
            status="created",
        )
