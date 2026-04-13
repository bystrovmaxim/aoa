# src/action_machine/testing/mock_action.py
"""
MockAction — мок-действие для использования в тестах.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

MockAction позволяет заменять реальные действия в тестах, предоставляя
фиксированный результат или вычисляемый через side_effect. Используется
в TestBench для подстановки зависимостей.

MockAction — полноценное действие, наследующее BaseAction[BaseParams, BaseResult].
Содержит summary-аспект (_mock_result_summary), что позволяет выполнять его
через полный конвейер машины. Однако TestBench при обнаружении MockAction
вызывает метод run() напрямую, минуя конвейер аспектов — это быстрее
и не требует @meta и @check_roles.

═══════════════════════════════════════════════════════════════════════════════
РЕЖИМЫ РАБОТЫ
═══════════════════════════════════════════════════════════════════════════════

1. Фиксированный результат (result):
   MockAction(result=MyResult(...)) — каждый вызов run() возвращает
   один и тот же объект результата.

2. Вычисляемый результат (side_effect):
   MockAction(side_effect=lambda p: MyResult(...)) — при каждом вызове
   run() вызывается функция side_effect с параметрами, и её результат
   возвращается как результат действия.

3. Если задан side_effect, параметр result игнорируется.

4. Если ни result, ни side_effect не заданы — run() выбрасывает ValueError.

═══════════════════════════════════════════════════════════════════════════════
СЧЁТЧИК ВЫЗОВОВ И ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

MockAction отслеживает количество вызовов (call_count) и сохраняет
параметры последнего вызова (last_params). Это позволяет в тестах
проверять, что действие было вызвано нужное количество раз с нужными
параметрами.

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТ ИМЕНОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

MockAction имеет суффикс "Action" — инвариант именования BaseAction
соблюдён. Summary-аспект имеет суффикс "_summary" — инвариант
именования @summary_aspect соблюдён. Description обязателен.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import MockAction, TestBench

    # Фиксированный результат:
    mock = MockAction(result=OrderResult(order_id="ORD-1", status="ok"))
    result = mock.run(OrderParams(user_id="u1"))
    assert result.order_id == "ORD-1"
    assert mock.call_count == 1

    # Вычисляемый результат:
    mock = MockAction(side_effect=lambda p: OrderResult(order_id=f"ORD-{p.user_id}"))
    result = mock.run(OrderParams(user_id="u42"))
    assert result.order_id == "ORD-u42"

    # В TestBench:
    bench = TestBench(mocks={
        PaymentService: MockAction(result=PayResult(txn_id="TXN-1")),
    })
"""

from collections.abc import Callable

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox


class MockAction(BaseAction[BaseParams, BaseResult]):  # pylint: disable=too-many-ancestors
    """
    Мок-действие для использования в тестах.

    Заменяет реальное действие, позволяя задать фиксированный результат
    или функцию-генератор результата (side_effect). Отслеживает количество
    вызовов и сохраняет параметры последнего вызова.

    TestBench при обнаружении MockAction вызывает run() напрямую,
    минуя конвейер аспектов — это не требует @meta и @check_roles.

    Атрибуты:
        result : BaseResult | None
            Фиксированный результат, возвращаемый при каждом вызове run().
            Игнорируется, если задан side_effect.

        side_effect : Callable[[BaseParams], BaseResult] | None
            Функция, вызываемая с параметрами для вычисления результата.
            Если задана, имеет приоритет над result.

        call_count : int
            Количество вызовов run(). Инкрементируется при каждом вызове.

        last_params : BaseParams | None
            Параметры последнего вызова run(). None до первого вызова.
    """

    def __init__(
        self,
        result: BaseResult | None = None,
        side_effect: Callable[[BaseParams], BaseResult] | None = None,
    ) -> None:
        """
        Инициализирует мок-действие.

        Аргументы:
            result: фиксированный результат, возвращаемый при каждом вызове.
            side_effect: функция, вызываемая с параметрами для получения
                         результата. Если задана, result игнорируется.
        """
        self.result = result
        self.side_effect = side_effect
        self.call_count: int = 0
        self.last_params: BaseParams | None = None

    def run(self, params: BaseParams) -> BaseResult:
        """
        Выполняет мок-действие.

        Инкрементирует call_count, сохраняет params в last_params,
        затем возвращает результат: через side_effect (если задан)
        или через result (если задан). Если ни один не задан —
        выбрасывает ValueError.

        Аргументы:
            params: входные параметры действия.

        Возвращает:
            BaseResult — результат (фиксированный или вычисленный).

        Исключения:
            ValueError: если ни result, ни side_effect не заданы.
        """
        self.call_count += 1
        self.last_params = params

        if self.side_effect:
            return self.side_effect(params)

        if self.result is None:
            raise ValueError("MockAction: neither result nor side_effect provided")

        return self.result

    @summary_aspect("Заглушка summary-аспекта для MockAction")
    async def _mock_result_summary(
        self,
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> BaseResult:
        """
        Заглушка summary-аспекта для выполнения через полный конвейер.

        Вызывается машиной при выполнении MockAction через конвейер
        аспектов (если TestBench решит не обрабатывать MockAction
        напрямую). Делегирует в метод run(), который возвращает
        фиксированный или вычисленный результат.

        Аргументы:
            params: входные параметры действия.
            state: текущее состояние конвейера (не используется).
            box: ToolsBox с инструментами (не используется).
            connections: словарь соединений (не используется).

        Возвращает:
            BaseResult — результат выполнения run(params).
        """
        return self.run(params)
