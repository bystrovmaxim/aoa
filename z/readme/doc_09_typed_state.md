09_typed_state.md

# TypedDict и state в AOA

State — это единственный mutable-объект в AOA. Он передаётся от аспекта к аспекту и существует только внутри одного вызова run. Этот документ объясняет как типизировать state через TypedDict, зачем нужны чекеры и как они работают вместе для создания строгого контракта каждого аспекта.

---

## Как ActionMachine работает со state

ActionMachine передаёт текущее state в метод-аспект и затем полностью заменяет его на то что вернул аспект:

```python
new_state = aspect(params, state, deps)
state = new_state
```

Это означает что state не накапливается автоматически. Каждый аспект получает предыдущее state, но обязан явно вернуть только те поля которые нужны дальше. Если аспект вернул пустой словарь — следующий аспект получит пустой state.

Это осознанное решение. Оно делает поведение каждого аспекта предсказуемым и заставляет явно описывать что передаётся по конвейеру.

---

## Зачем нужен TypedDict

Без типизации state — это просто dict. IDE не подсказывает ключи, опечатки не ловятся, контракт аспекта нигде не описан.

TypedDict решает это на уровне разработки:

```python
from typing import TypedDict

class ProcessOrderState(TypedDict, total=False):
    user: object
    product: object
    total: float
    order_id: int
    discount: float
```

Почему total=False обязательно:

Каждый аспект работает только с частью полей. Если total=True — mypy требовал бы наличия всех ключей одновременно, что противоречит модели конвейера где каждый аспект возвращает только своё подмножество.

TypedDict описывает всё пространство возможных ключей для данного Action. Каждый конкретный аспект возвращает срез из этого пространства.

---

## Пример TypedDict для Action

```python
from typing import TypedDict

class CreateOrderState(TypedDict, total=False):
    user_id: int
    product: object
    total: float
    discount: float
    final_total: float
    order_id: int
```

Этот TypedDict описывает что может появиться в state на разных этапах выполнения CreateOrderAction. Ни один аспект не работает со всеми полями сразу — каждый работает только с теми что нужны ему.

---

## Соответствие TypedDict и аспектов

Рассмотрим полный пример:

```python
from typing import TypedDict
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.AspectMethod import aspect, summary_aspect
from ActionMachine.Auth.CheckRoles import CheckRoles

class OrderState(TypedDict, total=False):
    product: object
    total: float
    discount: float
    order_id: int

@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CreateOrderAction(BaseAction):

    @aspect("Загрузка товара")
    async def load_product(self, params, state: OrderState, deps):
        product = await deps.get(ProductRepository).get(params.product_id)
        return OrderState(product=product)

    @aspect("Расчёт суммы")
    async def calculate(self, params, state: OrderState, deps):
        total = state["product"].price * params.quantity
        return OrderState(total=total)

    @aspect("Расчёт скидки")
    async def apply_discount(self, params, state: OrderState, deps):
        discount = state["total"] * 0.1 if params.is_vip else 0.0
        return OrderState(
            total=state["total"],
            discount=discount
        )

    @summary_aspect("Создание заказа")
    async def create(self, params, state: OrderState, deps):
        final = state["total"] - state.get("discount", 0.0)
        order_id = await deps.get(OrderRepository).create(
            user_id=params.user_id,
            product_id=params.product_id,
            total=final
        )
        return CreateOrderAction.Result(order_id=order_id, total=final)
```

Каждый аспект явно возвращает только нужные поля. Аспект calculate не знает про discount — он просто возвращает total. Аспект apply_discount получает total из предыдущего state и добавляет discount.

---

## Чекеры — runtime-контракт аспекта

TypedDict работает на уровне разработки — IDE и mypy. Чекеры работают во время выполнения — они проверяют что аспект вернул именно то что обещал.

Если аспект вернул лишние поля или нарушил типы — ActionMachine выбросит ValidationFieldException немедленно.

Основные чекеры:

IntFieldChecker — проверяет что поле существует и является целым числом. FloatFieldChecker — проверяет что поле существует и является числом с плавающей точкой. InstanceOfChecker — проверяет что поле является экземпляром указанного класса.

Пример применения чекеров:

```python
from ActionMachine.Checkers import IntFieldChecker, InstanceOfChecker, FloatFieldChecker

@aspect("Загрузка товара")
@InstanceOfChecker("product", Product, desc="Объект товара")
async def load_product(self, params, state, deps):
    product = await deps.get(ProductRepository).get(params.product_id)
    return {"product": product}

@aspect("Расчёт суммы")
@FloatFieldChecker("total", desc="Итоговая сумма")
async def calculate(self, params, state, deps):
    return {"total": state["product"].price * params.quantity}

@aspect("Создание заказа в БД")
@IntFieldChecker("order_id", desc="ID заказа", required=True)
async def save_order(self, params, state, deps):
    order_id = await deps.get(OrderRepository).create(params.user_id, state["total"])
    return {"order_id": order_id}
```

---

## Как TypedDict и чекеры дополняют друг друга

TypedDict — статический контракт:

Описывает возможные ключи. IDE подсказывает при написании кода. mypy ловит опечатки и несоответствия типов. Не влияет на поведение во время выполнения.

Чекеры — динамический контракт:

Проверяют точный состав state после каждого аспекта. Бросают ValidationFieldException при лишних ключах. Гарантируют строгость результата каждого шага. Работают независимо от IDE и mypy.

Вместе они создают двухуровневую защиту:

Первый уровень — разработка. Второй уровень — выполнение.

---

## Лишние поля как ошибка

Если аспект вернул ключи которые не объявлены в чекерах — машина выбросит исключение:

```python
extra_fields = set(new_state.keys()) - allowed_fields
if extra_fields:
    raise ValidationFieldException(
        f"Аспект вернул незадекларированные поля: {extra_fields}"
    )
```

Это защищает конвейер от случайной передачи неожиданных данных между аспектами.

---

## Когда использовать TypedDict

Рекомендуется если:

Action содержит больше двух аспектов. State включает несколько ключей. Код пишется в команде и нужен явный контракт. Важна подсказка IDE при работе с state.

Можно не использовать если:

Action маленький и содержит один-два аспекта. Структура state очевидна и проста. Быстрый прототип.

TypedDict не обязателен — ActionMachine работает одинаково с обычным dict и с TypedDict. Разница только в удобстве разработки.

---

## Полный пример с TypedDict и чекерами

```python
from dataclasses import dataclass
from typing import TypedDict
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles
from ActionMachine.Checkers import IntFieldChecker, FloatFieldChecker, InstanceOfChecker

class ProcessPaymentState(TypedDict, total=False):
    user: object
    total: float
    transaction_id: str

@depends(UserRepository)
@depends(PaymentGateway)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ProcessPaymentAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        amount: float
        card_token: str

    @dataclass(frozen=True)
    class Result(BaseResult):
        transaction_id: str
        amount: float

    @aspect("Загрузка пользователя")
    @InstanceOfChecker("user", object, desc="Объект пользователя")
    async def load_user(self, params, state: ProcessPaymentState, deps):
        user = await deps.get(UserRepository).get(params.user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        return ProcessPaymentState(user=user)

    @aspect("Расчёт суммы с комиссией")
    @FloatFieldChecker("total", desc="Итоговая сумма с комиссией")
    async def calculate_total(self, params, state: ProcessPaymentState, deps):
        commission = params.amount * 0.02
        total = params.amount + commission
        return ProcessPaymentState(
            user=state["user"],
            total=total
        )

    @summary_aspect("Проведение платежа")
    async def charge(self, params, state: ProcessPaymentState, deps):
        gateway = deps.get(PaymentGateway)
        txn_id = await gateway.charge(params.card_token, state["total"])
        return ProcessPaymentAction.Result(
            transaction_id=txn_id,
            amount=state["total"]
        )
```

---

## Что изучать дальше

10_resource_managers.md — адаптеры к внешним системам.

11_action_vs_resource.md — когда action, когда resource.

14_machine.md — жизненный цикл и пайплайн ActionMachine.

16_transactions.md — управление транзакциями.

19_testing.md — как тестировать аспекты и state.