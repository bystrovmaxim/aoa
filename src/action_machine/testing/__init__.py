# src/action_machine/testing/__init__.py
"""
Пакет тестовой инфраструктуры ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит всё необходимое для тестирования действий ActionMachine:
TestBench как единую точку входа, моки, стабы контекста, валидацию
state и сравнение результатов между машинами.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

Единая точка входа:

- **TestBench** — immutable fluent-объект для тестирования. Внутри
  создаёт async и sync production-машины с моками, прогоняет действие
  на обеих и сравнивает результаты. Каждый fluent-вызов (.with_user,
  .with_mocks и т.д.) возвращает НОВЫЙ экземпляр TestBench — оригинал
  не мутируется, безопасно для параллельного использования.

  Терминальные методы (обязательный rollup: bool без дефолта):
  - run(action, params, rollup) — полный прогон на всех машинах.
  - run_aspect(action, aspect_name, params, state, rollup) — один аспект.
  - run_summary(action, params, state, rollup) — только summary.

Моки:

- **MockAction** — мок-действие для подстановки в тестах. Поддерживает
  фиксированный результат (result) и вычисляемый через side_effect.
  Отслеживает call_count и last_params.

Стабы:

- **UserInfoStub** — стаб пользователя (user_id="test_user", roles=["tester"]).
- **RuntimeInfoStub** — стаб окружения (hostname="test-host").
- **RequestInfoStub** — стаб запроса (trace_id="test-trace-000").
- **ContextStub** — стаб полного контекста, объединяющий все три стаба.

Валидация:

- **validate_state_for_aspect** — проверяет, что state содержит все
  обязательные поля от предшествующих аспектов (по чекерам).
- **validate_state_for_summary** — проверяет полноту state перед
  summary-аспектом.

Сравнение:

- **compare_results** — сравнивает результаты двух машин с информативным
  сообщением при расхождении.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import TestBench, MockAction

    # Создаём bench с моками:
    bench = TestBench(mocks={PaymentService: mock_payment})

    # Fluent — каждый вызов создаёт новый объект:
    admin_bench = bench.with_user(user_id="admin", roles=["admin"])

    # Полный прогон на async + sync машинах с проверкой совпадения:
    result = admin_bench.run(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        rollup=False,
    )

    # Тест одного аспекта с валидацией state:
    result = bench.run_aspect(
        CreateOrderAction(), "process_payment",
        OrderParams(user_id="u1", amount=100.0),
        state={"validated_user": "u1"},
        rollup=False,
    )

    # Тест summary с валидацией полноты state:
    result = bench.run_summary(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        state={"validated_user": "u1", "txn_id": "TXN-1"},
        rollup=False,
    )
"""

from .bench import TestBench
from .comparison import compare_results
from .mock_action import MockAction
from .state_validator import validate_state_for_aspect, validate_state_for_summary
from .stubs import ContextStub, RequestInfoStub, RuntimeInfoStub, UserInfoStub

__all__ = [
    "ContextStub",
    "MockAction",
    "RequestInfoStub",
    "RuntimeInfoStub",
    "TestBench",
    "UserInfoStub",
    "compare_results",
    "validate_state_for_aspect",
    "validate_state_for_summary",
]
