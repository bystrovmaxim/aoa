30_examples.md

# Подборка рабочих примеров AOA

Этот документ содержит законченные рабочие примеры от простого к сложному. Каждый пример можно взять и запустить как есть. Вместе они показывают как выглядит AOA на практике — от минимального действия до полноценного бизнес-процесса с ресурсами, вложенностью и плагинами [1].

---

## Пример 1. Минимальное действие

Самое простое действие — принимает число и возвращает удвоенное значение.

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import summary_aspect
from ActionMachine.Auth.CheckRoles import CheckRoles

@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class DoubleNumberAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        value: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        doubled: int

    @summary_aspect("Удвоение числа")
    async def handle(self, params, state, deps):
        return DoubleNumberAction.Result(doubled=params.value * 2)
```

Запуск:

```python
from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Context.Context import Context

machine = ActionProductMachine(context=Context())
result = await machine.run(
    DoubleNumberAction(),
    DoubleNumberAction.Params(value=21)
)
print(result.doubled)  # 42
```

---

## Пример 2. Действие с несколькими аспектами

Аспекты разбивают бизнес-логику на явные шаги. Каждый шаг виден и тестируется отдельно.

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect
from ActionMachine.Auth.CheckRoles import CheckRoles

@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ProcessValueAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        value: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        output: int

    @aspect("Проверка входных данных")
    async def validate(self, params, state, deps):
        if params.value < 0:
            raise ValueError("Значение не может быть отрицательным")
        return state

    @aspect("Преобразование")
    async def transform(self, params, state, deps):
        state["result"] = params.value * 3
        return state

    @summary_aspect("Финализация")
    async def finish(self, params, state, deps):
        return ProcessValueAction.Result(output=state["result"])
```

---

## Пример 3. Действие с зависимостями через DI

Действие объявляет что ему нужно. Фабрика создаёт зависимости автоматически.

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

class EmailService:
    async def send(self, to: str, message: str) -> None:
        print(f"Email → {to}: {message}")

@depends(EmailService)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class SendNotificationAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        recipient: str
        message: str

    @dataclass(frozen=True)
    class Result(BaseResult):
        sent: bool

    @aspect("Подготовка сообщения")
    async def prepare(self, params, state, deps):
        state["formatted"] = f"[NOTIFY] {params.message}"
        return state

    @summary_aspect("Отправка")
    async def send(self, params, state, deps):
        email = deps.get(EmailService)
        await email.send(params.recipient, state["formatted"])
        return SendNotificationAction.Result(sent=True)
```

---

## Пример 4. Вложенные действия

Одно действие вызывает другое через deps.run_action. Это основной механизм композиции в AOA [1].

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect
from ActionMachine.Auth.CheckRoles import CheckRoles

@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CalculateDiscountAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        total: float
        is_vip: bool

    @dataclass(frozen=True)
    class Result(BaseResult):
        discount: float
        final_total: float

    @summary_aspect("Расчёт скидки")
    async def handle(self, params, state, deps):
        discount = params.total * 0.1 if params.is_vip else 0.0
        return CalculateDiscountAction.Result(
            discount=discount,
            final_total=params.total - discount
        )


@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CreateOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        total: float
        is_vip: bool

    @dataclass(frozen=True)
    class Result(BaseResult):
        final_total: float
        discount: float

    @aspect("Расчёт скидки")
    async def apply_discount(self, params, state, deps):
        result = await deps.run_action(
            CalculateDiscountAction,
            CalculateDiscountAction.Params(
                total=params.total,
                is_vip=params.is_vip
            )
        )
        state["discount"] = result.discount
        state["final_total"] = result.final_total
        return state

    @summary_aspect("Создание заказа")
    async def create(self, params, state, deps):
        return CreateOrderAction.Result(
            final_total=state["final_total"],
            discount=state["discount"]
        )
```

---

## Пример 5. Плагин для логирования

Плагин наблюдает за выполнением и не влияет на результат [1].

```python
from ActionMachine.Plugins.Plugin import Plugin
from ActionMachine.Plugins.Decorators import on

class ConsoleLoggingPlugin(Plugin):

    def get_initial_state(self):
        return {}

    @on("global_start", ".*", ignore_exceptions=True)
    async def on_start(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}→ START {action_name} params={params}")
        return state_plugin

    @on("after:.*", ".*", ignore_exceptions=True)
    async def on_after(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}  AFTER {event_name} duration={duration:.4f}s")
        return state_plugin

    @on("global_finish", ".*", ignore_exceptions=True)
    async def on_finish(self, state_plugin, event_name, action_name,
                        params, state_aspect, is_summary,
                        deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}← FINISH {action_name} result={result} time={duration:.4f}s")
        return state_plugin
```

Подключение:

```python
machine = ActionProductMachine(
    context=Context(),
    plugins=[ConsoleLoggingPlugin()]
)
result = await machine.run(
    CreateOrderAction(),
    CreateOrderAction.Params(user_id=1, total=100.0, is_vip=True)
)
```

---

## Пример 6. Тестирование действия

ActionTestMachine позволяет тестировать без инфраструктуры [1].

```python
import pytest
from ActionMachine.Core.ActionTestMachine import ActionTestMachine

class FakeEmailService:
    def __init__(self):
        self.sent = []

    async def send(self, to: str, message: str) -> None:
        self.sent.append((to, message))


@pytest.mark.asyncio
async def test_send_notification():
    fake_email = FakeEmailService()

    machine = ActionTestMachine({EmailService: fake_email})

    result = await machine.run(
        SendNotificationAction(),
        SendNotificationAction.Params(
            recipient="user@example.com",
            message="Hello"
        )
    )

    assert result.sent is True
    assert len(fake_email.sent) == 1
    assert fake_email.sent[0][0] == "user@example.com"
```

---

## Пример 7. Тестирование вложенных действий

Вложенное действие подменяется фиксированным результатом [1].

```python
@pytest.mark.asyncio
async def test_create_order_with_mock_discount():
    machine = ActionTestMachine({
        CalculateDiscountAction: CalculateDiscountAction.Result(
            discount=15.0,
            final_total=85.0
        )
    })

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, total=100.0, is_vip=True)
    )

    assert result.final_total == 85.0
    assert result.discount == 15.0
```

---

## Пример 8. Тестирование с динамическим side_effect

Мок вычисляет результат динамически в зависимости от входных данных [1].

```python
@pytest.mark.asyncio
async def test_create_order_with_dynamic_discount():
    machine = ActionTestMachine({
        CalculateDiscountAction: lambda params: CalculateDiscountAction.Result(
            discount=params.total * 0.2,
            final_total=params.total * 0.8
        )
    })

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, total=200.0, is_vip=True)
    )

    assert result.final_total == 160.0
    assert result.discount == 40.0
```

---

## Пример 9. MockAction — отслеживание вызовов

MockAction запоминает параметры вызовов для проверки в тестах [1].

```python
from ActionMachine.Core.MockAction import MockAction

@pytest.mark.asyncio
async def test_mock_action_tracks_calls():
    mock = MockAction(
        result=CalculateDiscountAction.Result(discount=10.0, final_total=90.0)
    )

    machine = ActionTestMachine({CalculateDiscountAction: mock})

    await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, total=100.0, is_vip=True)
    )

    assert mock.call_count == 1
    assert mock.last_params.total == 100.0
    assert mock.last_params.is_vip is True
```

---

## Пример 10. Миграция легаси — первая обёртка

Первый шаг безопасной миграции — изолировать монстра и создать действие-обёртку [1].

```python
# Исходный легаси-класс
class LegacyOrderSystem:
    def process(self, user_id: int, items: list) -> dict:
        return {"order_id": 42, "status": "created"}


# Порт
from abc import ABC, abstractmethod

class IOrderProcessor(ABC):
    @abstractmethod
    def process(self, user_id: int, items: list) -> dict: ...


# Адаптер
class LegacyOrderAdapter(IOrderProcessor):
    def __init__(self):
        self._legacy = LegacyOrderSystem()

    def process(self, user_id: int, items: list) -> dict:
        return self._legacy.process(user_id, items)


# Действие-обёртка
from ActionMachine.Core.AspectMethod import depends

@depends(IOrderProcessor)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ProcessOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        items: list

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int
        status: str

    @summary_aspect("Вызов легаси")
    async def handle(self, params, state, deps):
        processor = deps.get(IOrderProcessor)
        raw = processor.process(params.user_id, params.items)
        return ProcessOrderAction.Result(
            order_id=raw["order_id"],
            status=raw["status"]
        )
```

Теперь есть единая точка входа, DI и возможность писать тесты без изменения легаси-кода [1].

---

## Пример 11. Полный бизнес-процесс

Все концепции AOA вместе — аспекты, DI, вложенные действия, ресурсы.

```python
from dataclasses import dataclass
from typing import TypedDict
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

class OrderState(TypedDict, total=False):
    product: object
    total: float
    discount: float
    order_id: int

@depends(ProductRepository)
@depends(OrderRepository)
@depends(EmailService)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному")
class FullOrderProcessAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        product_id: int
        quantity: int
        is_vip: bool

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int
        total: float
        discount: float

    @aspect("Загрузка товара")
    async def load_product(self, params, state: OrderState, deps):
        repo = deps.get(ProductRepository)
        product = await repo.get(params.product_id)
        if product.stock < params.quantity:
            raise ValueError("Недостаточно товара на складе")
        state["product"] = product
        state["total"] = product.price * params.quantity
        return state

    @aspect("Расчёт скидки")
    async def apply_discount(self, params, state: OrderState, deps):
        result = await deps.run_action(
            CalculateDiscountAction,
            CalculateDiscountAction.Params(
                total=state["total"],
                is_vip=params.is_vip
            )
        )
        state["discount"] = result.discount
        state["total"] = result.final_total
        return state

    @aspect("Сохранение заказа")
    async def save_order(self, params, state: OrderState, deps):
        repo = deps.get(OrderRepository)
        order_id = await repo.create(
            user_id=params.user_id,
            product_id=params.product_id,
            total=state["total"]
        )
        state["order_id"] = order_id
        return state

    @summary_aspect("Уведомление и результат")
    async def finish(self, params, state: OrderState, deps):
        email = deps.get(EmailService)
        await email.send_confirmation(params.user_id, state["order_id"])
        return FullOrderProcessAction.Result(
            order_id=state["order_id"],
            total=state["total"],
            discount=state["discount"]
        )
```

---

## Что изучать дальше

31_end_to_end_demo.md — полный пример от HTTP до результата в одном файле.

28_specification.md — полная формальная модель AOA.

19_testing.md — полное руководство по тестированию.

26_migrating_legacy.md — пошаговая миграция легаси-кода.

18_plugins.md — создание плагинов для наблюдения.
