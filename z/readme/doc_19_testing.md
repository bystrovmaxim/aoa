19_testing.md

# Тестирование в AOA и ActionEngine

Тестирование — центральная часть архитектуры AOA. Вся модель действий, аспектов, зависимостей и машин специально спроектирована так, чтобы любой фрагмент бизнес-логики был тестируем изолированно, без подъёма инфраструктуры, без веб-фреймворков, без БД, без сложного окружения [1].

---

## Три принципа тестируемости

Первый принцип — Actions stateless. Действие не хранит состояния между вызовами. Это означает что каждый тест получает предсказуемое начальное состояние.

Второй принцип — Params и Result неизменяемы и чисты. Входные и выходные данные это замороженные dataclass. Их легко создавать, сравнивать и инспектировать в тестах.

Третий принцип — DI полностью подменяемый через ActionTestMachine. Любая зависимость заменяется моком без изменения кода действия [1].

---

## ActionTestMachine — главный инструмент тестов

ActionTestMachine — это тестовая реализация ActionMachine. Она полностью повторяет логику production-машины но позволяет подменять любые зависимости через словарь моков [1].

```python
from ActionMachine.Core.ActionTestMachine import ActionTestMachine

machine = ActionTestMachine({
    UserRepository: FakeUserRepo(),
    EmailService: FakeEmailService()
})

result = await machine.run(
    NotifyUserAction(),
    NotifyUserAction.Params(user_id=1, message="Hello")
)

assert result.sent is True
```

Механизм подмены зависимостей:

Если мок — экземпляр класса, он используется как есть. Если мок — экземпляр BaseResult, он автоматически оборачивается в MockAction с фиксированным результатом. Если мок — функция, она оборачивается в MockAction с side_effect [1].

---

## Тестирование отдельного аспекта

Каждый аспект — обычный метод класса. Его можно тестировать напрямую без запуска всего конвейера. Это даёт максимально быстрые и изолированные тесты.

```python
import pytest

@pytest.mark.asyncio
async def test_validate_aspect():
    machine = ActionTestMachine()
    factory = machine.build_factory(CreateOrderAction)
    action = CreateOrderAction()

    params = CreateOrderAction.Params(user_id=1, product_id=10, quantity=2)
    state = {}

    new_state = await action.validate_params(params, state, factory)

    assert "validated" in new_state
    assert new_state["validated"] is True
```

Этот подход позволяет тестировать конвейер по частям — один аспект за раз. Особенно полезен когда аспект содержит сложную бизнес-логику которую хочется проверить независимо от остальных шагов.

---

## Тестирование целого действия

Для проверки что все аспекты работают корректно вместе используется machine.run:

```python
@pytest.mark.asyncio
async def test_create_order():
    fake_product_repo = FakeProductRepository()
    fake_order_repo = FakeOrderRepository()
    fake_email = FakeEmailService()

    machine = ActionTestMachine({
        ProductRepository: fake_product_repo,
        OrderRepository: fake_order_repo,
        EmailService: fake_email
    })

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, product_id=10, quantity=2)
    )

    assert result.order_id is not None
    assert fake_order_repo.created_count == 1
    assert fake_email.sent_count == 1
```

Запускаются все аспекты по порядку, зависимости подставляются из словаря моков, state проходит по конвейеру, summary-аспект возвращает Result.

---

## Мокирование вложенных действий

Вложенные действия подменяются так же как обычные зависимости. ActionTestMachine автоматически распознаёт тип мока и оборачивает его правильно [1].

Первый способ — фиксированный результат через BaseResult:

```python
machine = ActionTestMachine({
    CalculateDiscountAction: CalculateDiscountAction.Result(discount=10.0)
})

result = await machine.run(
    CreateOrderAction(),
    CreateOrderAction.Params(user_id=1, product_id=10, quantity=1)
)
```

Второй способ — динамический результат через функцию:

```python
machine = ActionTestMachine({
    CalculateDiscountAction: lambda params: CalculateDiscountAction.Result(
        discount=params.total * 0.1
    )
})
```

Третий способ — полный мок через MockAction:

```python
mock_discount = MockAction(
    result=CalculateDiscountAction.Result(discount=5.0)
)

machine = ActionTestMachine({
    CalculateDiscountAction: mock_discount
})

result = await machine.run(
    CreateOrderAction(),
    CreateOrderAction.Params(user_id=1, product_id=10, quantity=1)
)

assert mock_discount.call_count == 1
assert mock_discount.last_params.total == 100.0
```

---

## MockAction — специализированный мок

MockAction запоминает все вызовы и параметры. Это позволяет проверять не только результат но и то как именно действие вызывалось [1].

```python
from ActionMachine.Core.MockAction import MockAction

mock = MockAction(result=ChildAction.Result(doubled=42))

machine = ActionTestMachine({ChildAction: mock})

result = await machine.run(
    ParentAction(),
    ParentAction.Params(num=5)
)

assert mock.call_count == 1
assert mock.last_params.value == 5
assert result.result == 42
```

MockAction поддерживает:

call_count — количество вызовов. last_params — параметры последнего вызова. all_params — список параметров всех вызовов. side_effect — функция вычисляющая результат динамически.

---

## Тестирование чекеров

Чекеры можно тестировать отдельно от действий — они являются самостоятельными объектами:

```python
from ActionMachine.Checkers import IntFieldChecker, FloatFieldChecker

def test_int_checker_passes():
    checker = IntFieldChecker("order_id", desc="ID заказа", required=True)
    checker.check({"order_id": 42})  # не бросает исключение

def test_int_checker_fails_on_missing():
    checker = IntFieldChecker("order_id", desc="ID заказа", required=True)
    with pytest.raises(ValidationFieldException):
        checker.check({})

def test_float_checker_fails_on_wrong_type():
    checker = FloatFieldChecker("total", desc="Сумма")
    with pytest.raises(ValidationFieldException):
        checker.check({"total": "not_a_float"})
```

---

## Тестирование обработки ошибок

Тесты должны проверять как действие реагирует на ошибки ресурсов и исключения бизнес-логики:

```python
@pytest.mark.asyncio
async def test_product_not_found():
    class FakeRepo(IProductRepository):
        async def get(self, product_id: int):
            raise ValueError(f"Продукт {product_id} не найден")

        async def update_stock(self, product_id: int, quantity: int):
            pass

    machine = ActionTestMachine({IProductRepository: FakeRepo()})

    with pytest.raises(ValueError, match="не найден"):
        await machine.run(
            LoadProductAction(),
            LoadProductAction.Params(product_id=999)
        )


@pytest.mark.asyncio
async def test_db_unavailable():
    from ActionMachine.Core.Exceptions import HandleException

    class BrokenRepo(IProductRepository):
        async def get(self, product_id: int):
            raise HandleException("База данных недоступна")

        async def update_stock(self, product_id: int, quantity: int):
            pass

    machine = ActionTestMachine({IProductRepository: BrokenRepo()})

    with pytest.raises(HandleException, match="недоступна"):
        await machine.run(
            LoadProductAction(),
            LoadProductAction.Params(product_id=1)
        )
```

---

## Тестирование транзакций

Для тестирования действий с транзакциями используется FakeConnectionManager:

```python
class FakeConnectionManager(IConnectionManager):

    def __init__(self):
        self.executed_queries = []
        self.committed = False
        self.rolled_back = False
        self.opened = False

    async def open(self) -> None:
        self.opened = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def execute(self, query, params=None):
        self.executed_queries.append((query, params))
        return 42

    def get_wrapper_class(self):
        return None


@pytest.mark.asyncio
async def test_create_order_commits():
    fake_db = FakeConnectionManager()

    machine = ActionTestMachine({
        PostgresConnectionManager: fake_db
    })

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, product_id=10, quantity=2)
    )

    assert result.order_id == 42
    assert fake_db.opened is True
    assert fake_db.committed is True
    assert len(fake_db.executed_queries) == 1
```

---

## Тестирование авторизации

ActionMachine проверяет роли до запуска аспектов. Это можно проверять в тестах через Context:

```python
from ActionMachine.Context.Context import Context
from ActionMachine.Context.UserInfo import UserInfo
from ActionMachine.Core.Exceptions import AuthorizationException

@pytest.mark.asyncio
async def test_admin_only_action_rejects_user():
    user_context = Context(
        user=UserInfo(user_id="123", roles=["user"], extra={})
    )

    machine = ActionTestMachine(context=user_context)

    with pytest.raises(AuthorizationException):
        await machine.run(
            AdminOnlyAction(),
            AdminOnlyAction.Params()
        )


@pytest.mark.asyncio
async def test_admin_only_action_allows_admin():
    admin_context = Context(
        user=UserInfo(user_id="456", roles=["admin"], extra={})
    )

    machine = ActionTestMachine(context=admin_context)

    result = await machine.run(
        AdminOnlyAction(),
        AdminOnlyAction.Params()
    )

    assert result.success is True
```

---

## Тестирование плагинов

Плагины тестируются через ActionTestMachine с передачей плагина в список:

```python
@pytest.mark.asyncio
async def test_logging_plugin_receives_events():
    events = []

    class CapturingPlugin(Plugin):
        def get_initial_state(self):
            return []

        @on("global_start", ".*", ignore_exceptions=True)
        async def on_start(self, state_plugin, event_name, action_name,
                           params, state_aspect, is_summary,
                           deps, context, result, duration, nest_level, **kwargs):
            state_plugin.append(f"start:{action_name}")
            return state_plugin

        @on("global_finish", ".*", ignore_exceptions=True)
        async def on_finish(self, state_plugin, event_name, action_name,
                            params, state_aspect, is_summary,
                            deps, context, result, duration, nest_level, **kwargs):
            state_plugin.append(f"finish:{action_name}")
            events.extend(state_plugin)
            return state_plugin

    plugin = CapturingPlugin()
    machine = ActionTestMachine(plugins=[plugin])

    await machine.run(DoubleAction(), DoubleAction.Params(value=5))

    assert any("start" in e for e in events)
    assert any("finish" in e for e in events)
```

---

## Стратегия написания тестов

Рекомендуемый порядок написания тестов при разработке нового действия:

Первый шаг — тесты Params. Проверка что входные данные принимаются корректно.

Второй шаг — тесты каждого аспекта изолированно. Быстрые юнит-тесты бизнес-логики отдельных шагов.

Третий шаг — тест полного действия. Проверка что все аспекты работают вместе правильно.

Четвёртый шаг — тесты вложенных вызовов. Проверка что композиция действий корректна.

Пятый шаг — тесты граничных случаев. Ошибки, недоступные ресурсы, пустые данные.

Шестой шаг — интеграционные тесты ресурсов. Только если нужно проверить реальный API или БД.

---

## Полный пример комплексного теста

```python
@pytest.mark.asyncio
async def test_process_payment_full():
    fake_user_repo = FakeUserRepository()
    fake_gateway = FakePaymentGateway()
    fake_email = FakeEmailService()

    machine = ActionTestMachine({
        UserRepository: fake_user_repo,
        PaymentGateway: fake_gateway,
        EmailService: fake_email
    })

    result = await machine.run(
        ProcessPaymentAction(),
        ProcessPaymentAction.Params(
            user_id=1,
            card_token="tok_test",
            amount=100.0
        )
    )

    assert result.transaction_id == "txn_fake_123"
    assert result.amount == 102.0  # с комиссией 2%
    assert fake_gateway.charged_amount == 102.0
    assert fake_email.sent_count == 1
    assert fake_email.last_recipient == "user@test.com"
```

---

## Итог

Тестирование в AOA — это быстро, просто, предсказуемо и изолировано [1].

ActionTestMachine полностью воспроизводит поведение production-машины. MockAction позволяет контролировать вложенные действия. Fake-реализации портов дают полный контроль над ресурсами. Чекеры, роли и ошибки тестируются так же легко как сама логика.

Тестируемость в AOA — это не дополнительный инструмент. Это встроенное свойство архитектуры [1].

---

## Что изучать дальше

20_auth_architecture.md — аутентификация и сборка Context.

21_fastapi_integration.md — интеграция с FastAPI.

22_mcp_integration.md — интеграция с MCP для LLM-агентов.

14_machine.md — жизненный цикл ActionMachine.

16_transactions.md — тестирование транзакций.

25_choosing_action_aspect_resource.md — алгоритм выбора абстракций.