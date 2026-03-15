07_actions.md

# Как писать Actions в AOA

Action — это атомарная бизнес-операция. Он не хранит состояния, не знает об инфраструктуре, не зависит от транспорта. Он принимает Params, выполняет серию аспектов и возвращает Result. Это всё что он делает. Этого достаточно.

Этот документ объясняет как правильно писать Actions, из чего они состоят и какие правила нужно соблюдать [1].

---

## Минимальная структура Action

Каждый Action состоит из четырёх обязательных элементов: Params, Result, хотя бы одного аспекта и декоратора CheckRoles.

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import summary_aspect
from ActionMachine.Auth.CheckRoles import CheckRoles

@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class CreateOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        product_id: int
        quantity: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int

    @summary_aspect("Создание заказа")
    async def handle(self, params, state, deps):
        return CreateOrderAction.Result(order_id=42)
```

Params и Result объявляются внутри класса Action. Это делает код самодокументируемым — всё что нужно для понимания Action находится в одном месте.

---

## Params — входные данные

Params — это неизменяемый dataclass. Он содержит только бизнес-данные. Никаких данных запроса, никаких заголовков, никакого контекста.

```python
@dataclass(frozen=True)
class Params(BaseParams):
    user_id: int
    product_id: int
    quantity: int
    promo_code: str = ""
```

Правила Params:

Обязателен frozen=True — это гарантирует неизменяемость. Содержит только данные которые нужны бизнес-логике. Не содержит объектов сервисов, соединений или контекста. Может содержать значения по умолчанию для опциональных полей.

---

## Result — результат работы

Result — это тоже неизменяемый dataclass. Он описывает итог выполнения операции.

```python
@dataclass(frozen=True)
class Result(BaseResult):
    order_id: int
    total: float
    status: str
```

Правила Result:

Обязателен frozen=True. Содержит только итоговые данные. Не содержит промежуточных значений или внутренних деталей реализации. Является контрактом между Action и его вызывающей стороной.

---

## Аспекты — шаги конвейера

Аспекты — это методы Action помеченные декораторами @aspect или @summary_aspect. Они вызываются строго в порядке объявления сверху вниз.

```python
from ActionMachine.Core.AspectMethod import aspect, summary_aspect

@aspect("Проверка наличия товара")
async def check_stock(self, params, state, deps):
    repo = deps.get(ProductRepository)
    product = await repo.get(params.product_id)
    if product.stock < params.quantity:
        raise ValueError("Недостаточно товара на складе")
    state["product"] = product
    return state

@aspect("Расчёт стоимости")
async def calculate_total(self, params, state, deps):
    product = state["product"]
    state["total"] = product.price * params.quantity
    return state

@summary_aspect("Создание заказа")
async def create_order(self, params, state, deps):
    return CreateOrderAction.Result(
        order_id=42,
        total=state["total"],
        status="created"
    )
```

Правила аспектов:

Каждый regular-аспект обязан вернуть dict. Summary-аспект обязан вернуть Result. Аспект не должен менять params. Аспект не должен хранить данные в self. Аспект должен делать одно дело.

---

## Зависимости через @depends

Action не создаёт сервисы сам. Он объявляет что ему нужно через декоратор @depends и получает готовые объекты через deps.

```python
from ActionMachine.Core.AspectMethod import depends

@depends(ProductRepository)
@depends(OrderRepository)
@depends(EmailService)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CreateOrderAction(BaseAction):

    @aspect("Загрузка продукта")
    async def load_product(self, params, state, deps):
        repo = deps.get(ProductRepository)
        product = await repo.get(params.product_id)
        state["product"] = product
        return state

    @summary_aspect("Создание заказа")
    async def create(self, params, state, deps):
        order_repo = deps.get(OrderRepository)
        email = deps.get(EmailService)
        order_id = await order_repo.create(params.user_id, state["product"])
        await email.send_confirmation(params.user_id, order_id)
        return CreateOrderAction.Result(order_id=order_id)
```

Правила зависимостей:

Нельзя использовать зависимость не объявленную через @depends. Зависимости объявляются на уровне класса а не метода. DependencyFactory создаёт объекты один раз за вызов и кеширует их. В тестах любая зависимость подменяется через ActionTestMachine.

---

## CheckRoles — обязательная авторизация

Каждый Action обязан иметь декоратор CheckRoles. Это не опционально. ActionMachine выбросит ошибку если декоратор отсутствует [1].

```python
from ActionMachine.Auth.CheckRoles import CheckRoles

# Доступно только определённым ролям
@CheckRoles(["admin", "manager"], desc="Только для администраторов и менеджеров")
class DeleteOrderAction(BaseAction):
    ...

# Доступно любому аутентифицированному пользователю
@CheckRoles(CheckRoles.ANY, desc="Любой аутентифицированный")
class GetOrderAction(BaseAction):
    ...

# Не требует аутентификации
@CheckRoles(CheckRoles.NONE, desc="Публичный доступ")
class GetPublicCatalogAction(BaseAction):
    ...
```

Проверка ролей происходит до запуска первого аспекта. Нарушение вызывает AuthorizationException.

---

## State — передача данных между аспектами

State — это обычный Python dict. Он передаётся от аспекта к аспекту и существует только внутри одного вызова.

```python
@aspect("Загрузка пользователя")
async def load_user(self, params, state, deps):
    user = await deps.get(UserRepository).get(params.user_id)
    state["user"] = user
    return state

@aspect("Проверка пользователя")
async def check_user(self, params, state, deps):
    user = state["user"]  # данные из предыдущего аспекта
    if not user.is_active:
        raise ValueError("Пользователь заблокирован")
    return state
```

Важное правило: state не накапливается автоматически. Каждый аспект явно возвращает только нужные поля. ActionMachine полностью заменяет state на то что вернул аспект [1].

---

## Вложенные действия

Action может вызвать другой Action через deps.run_action. Это основной механизм композиции бизнес-логики в AOA.

```python
@aspect("Расчёт скидки")
async def calculate_discount(self, params, state, deps):
    result = await deps.run_action(
        CalculateDiscountAction,
        CalculateDiscountAction.Params(
            user_id=params.user_id,
            total=state["total"]
        )
    )
    state["discount"] = result.discount
    state["final_total"] = state["total"] - result.discount
    return state
```

При вложенном вызове ActionMachine запускает полный конвейер дочернего действия включая плагины и чекеры [1].

---

## Типизация state через TypedDict

Для улучшения подсказок IDE и обнаружения ошибок рекомендуется использовать TypedDict для описания state.

```python
from typing import TypedDict

class CreateOrderState(TypedDict, total=False):
    product: object
    total: float
    discount: float
    final_total: float
```

TypedDict с total=False означает что ни одно поле не обязательно одновременно. Это правильно потому что каждый аспект работает только с частью полей [1].

---

## Чекеры — контракт аспекта

Чекеры проверяют результат аспекта во время выполнения. Они гарантируют что аспект вернул именно то что ожидалось.

```python
from ActionMachine.Checkers import IntFieldChecker, InstanceOfChecker

@aspect("Загрузка продукта")
@IntFieldChecker("product_id", desc="ID продукта", required=True)
@InstanceOfChecker("product", Product, desc="Объект продукта")
async def load_product(self, params, state, deps):
    product = await deps.get(ProductRepository).get(params.product_id)
    return {"product_id": product.id, "product": product}
```

Если аспект вернул лишние поля или нарушил типы — машина выбросит ValidationFieldException [1].

---

## Что запрещено в Actions

В Action нельзя:

Хранить данные в атрибутах экземпляра self. Менять объект params. Напрямую создавать соединения с БД или HTTP-клиенты. Читать переменные окружения или конфигурационные файлы. Вызывать плагины напрямую. Использовать глобальное состояние. Зависеть от контекста запроса.

Всё это нарушает принцип stateless Action и разрушает предсказуемость конвейера.

---

## Полный пример Action

```python
from dataclasses import dataclass
from typing import TypedDict
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

class ProcessOrderState(TypedDict, total=False):
    product: object
    total: float

@depends(ProductRepository)
@depends(OrderRepository)
@depends(EmailService)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ProcessOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        product_id: int
        quantity: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int
        total: float

    @aspect("Загрузка и проверка товара")
    async def load_product(self, params, state: ProcessOrderState, deps):
        product = await deps.get(ProductRepository).get(params.product_id)
        if product.stock < params.quantity:
            raise ValueError("Недостаточно товара")
        state["product"] = product
        state["total"] = product.price * params.quantity
        return state

    @summary_aspect("Создание заказа и уведомление")
    async def create_order(self, params, state: ProcessOrderState, deps):
        order_id = await deps.get(OrderRepository).create(
            user_id=params.user_id,
            product_id=params.product_id,
            total=state["total"]
        )
        await deps.get(EmailService).send_confirmation(params.user_id, order_id)
        return ProcessOrderAction.Result(
            order_id=order_id,
            total=state["total"]
        )
```

---

## Что изучать дальше

08_aspects_vs_actions.md — когда оставить аспект, когда выделить отдельное действие.

09_typed_state.md — TypedDict и чекеры для строгого контракта аспектов.

15_di.md — декларативное внедрение зависимостей.

16_transactions.md — управление транзакциями в Actions.

19_testing.md — как тестировать Actions.

25_choosing_action_aspect_resource.md — алгоритм выбора между action, aspect и resource.