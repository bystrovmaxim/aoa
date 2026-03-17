16_transactions.md

# Управление транзакциями в AOA

Управление транзакциями в ActionEngine построено на принципе явности без магии. Разработчик всегда видит где транзакция открывается, где фиксируется, где откатывается и какие соединения передаются в дочерние действия. В отличие от большинства фреймворков где транзакции навязываются автоматически через декораторы или middleware, AOA делает транзакцию частью бизнес-логики — явной, контролируемой и тестируемой [1].

---

## Три принципа управления транзакциями

Первый принцип — явное создание и управление. Действие-владелец само создаёт соединение, открывает его, начинает транзакцию, фиксирует или откатывает. Никакого автоматического begin при входе в действие.

Второй принцип — явная передача в дочерние действия. Разработчик сам решает какие connections передать в дочернее действие через словарь connections. Никакого неявного контекста транзакции.

Третий принцип — автоматическая защита вложенных уровней. При передаче в дочернее действие каждый connection автоматически оборачивается в прокси который запрещает open, commit, rollback но разрешает execute [1].

---

## Объявление соединения в Action

Ресурсный менеджер объявляется через @depends. Поскольку менеджер соединения обычно требует параметров подключения используется параметр factory:

```python
from dataclasses import dataclass
from typing import TypedDict
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends, connection
from ActionMachine.Auth.CheckRoles import CheckRoles
from ActionMachine.ResourceManagers.IConnectionManager import IConnectionManager
from ActionMachine.ResourceManagers.PostgresConnectionManager import PostgresConnectionManager
from ActionMachine.Checkers import IntFieldChecker
```

TypedDict для state и connections:

```python
class CreateOrderState(TypedDict, total=False):
    order_id: int

class CreateOrderConnections(TypedDict, total=False):
    connection: IConnectionManager
```

Объявление действия:

```python
@depends(
    PostgresConnectionManager,
    factory=lambda: PostgresConnectionManager({
        "host": "localhost",
        "port": 5432,
        "user": "app",
        "password": "secret",
        "database": "shop"
    })
)
@connection("connection", PostgresConnectionManager,
            description="Основное соединение с БД")
@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
class CreateOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        product_id: int
        quantity: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int
        notification_sent: bool
```

---

## Аспект открытия соединения

Первый аспект отвечает за открытие соединения и начало транзакции:

```python
@aspect("Открыть соединение")
async def open_connection(
    self, params, state: CreateOrderState,
    deps, connections: CreateOrderConnections
) -> CreateOrderState:
    db = connections["connection"]
    await db.open()
    return CreateOrderState()
```

Действие-владелец имеет полный доступ к open, commit, rollback. Соединение доступно через connections по ключу совпадающему с именем указанным в декораторе @connection [1].

---

## Аспект бизнес-логики

Следующие аспекты выполняют бизнес-операции используя соединение:

```python
@aspect("Создать заказ")
@IntFieldChecker("order_id", desc="ID созданного заказа", required=True)
async def insert_order(
    self, params, state: CreateOrderState,
    deps, connections: CreateOrderConnections
) -> CreateOrderState:
    db = connections["connection"]
    result = await db.execute(
        "INSERT INTO orders (user_id, product_id, quantity) "
        "VALUES ($1, $2, $3) RETURNING id",
        (params.user_id, params.product_id, params.quantity)
    )
    return CreateOrderState(order_id=result)
```

---

## Передача соединения в дочернее действие

Разработчик явно решает какие connections передать в дочернее действие. При передаче каждый connection автоматически оборачивается в прокси:

```python
@aspect("Отправить уведомление")
async def send_notification(
    self, params, state: CreateOrderState,
    deps, connections: CreateOrderConnections
) -> CreateOrderState:
    await deps.run_action(
        SendNotificationAction,
        SendNotificationAction.Params(
            user_id=params.user_id,
            order_id=state["order_id"],
        ),
        connections={"connection": connections["connection"]}
    )
    return state
```

DependencyFactory автоматически оборачивает переданное соединение в прокси. Дочернее действие может вызывать execute но не может вызывать commit, rollback или open [1].

---

## Summary-аспект — фиксация транзакции

```python
@summary_aspect("Завершить транзакцию")
async def finish(
    self, params, state: CreateOrderState,
    deps, connections: CreateOrderConnections
) -> Result:
    db = connections["connection"]
    await db.commit()
    return CreateOrderAction.Result(
        order_id=state["order_id"],
        notification_sent=True
    )
```

Если на любом предыдущем шаге произошло исключение — этот аспект не будет вызван и транзакция останется незафиксированной.

---

## Дочернее действие с прокси

Дочернее действие не создаёт соединение. Оно получает его через connections и работает только с execute:

```python
class SendNotificationState(TypedDict, total=False):
    pass

@connection("connection", IConnectionManager,
            description="Соединение от родителя")
@CheckRoles(CheckRoles.ANY, desc="Доступно аутентифицированным пользователям")
class SendNotificationAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        order_id: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        sent: bool

    @summary_aspect("Записать уведомление")
    async def handle(
        self, params, state: SendNotificationState,
        deps, connections
    ) -> Result:
        db = connections["connection"]
        await db.execute(
            "INSERT INTO notifications (user_id, order_id, type) "
            "VALUES ($1, $2, $3)",
            (params.user_id, params.order_id, "order_created")
        )
        return SendNotificationAction.Result(sent=True)
```

connections["connection"] здесь это прокси-обёртка. execute работает и делегирует запрос реальному соединению через цепочку проксей. commit, rollback, open выбросят TransactionProhibitedError [1].

---

## Как работает автоматическое оборачивание

Когда действие передаёт connections в deps.run_action происходит следующее:

Первое. DependencyFactory проходит по каждому connection в словаре.

Второе. Для каждого connection вызывается get_wrapper_class.

Третье. Если класс-обёртка возвращён создаётся экземпляр обёртки с оригинальным connection в конструкторе.

Четвёртое. Новый словарь с обёрнутыми connections передаётся в machine.run дочернего действия.

Пятое. При дальнейшей вложенности обёртка оборачивается снова. execute делегируется к реальному соединению через всю цепочку [1].

---

## Валидация connections

ActionMachine выполняет строгую проверку соответствия переданных connections и объявленных через @connection до выполнения аспектов [1]:

Действие объявило @connection и connections передан правильно — всё в порядке.

Действие объявило @connection но connections не передан — ConnectionValidationError.

Действие не объявило @connection но connections передан — ConnectionValidationError.

Передан лишний ключ которого нет в @connection — ConnectionValidationError.

---

## Откат транзакции при ошибке

AOA не навязывает автоматических откатов. Разработчик полностью контролирует этот процесс:

```python
@summary_aspect("Выполнить и зафиксировать")
async def handle(
    self, params, state,
    deps, connections
) -> Result:
    db = connections["connection"]
    try:
        await db.execute("INSERT INTO orders ...")
        await db.execute("UPDATE inventory ...")
        await db.commit()
        return OrderResult(success=True)
    except Exception:
        await db.rollback()
        raise
```

Явный try/except с rollback — не магия, а прозрачный контроль. Разработчик всегда видит что происходит с транзакцией.

---

## Несколько соединений в одном действии

Если действию нужно работать с несколькими базами данных создаётся расширенный TypedDict для connections:

```python
class MultiDbConnections(TypedDict, total=False):
    connection: IConnectionManager
    analytics_db: IConnectionManager

@connection("connection", PostgresConnectionManager,
            description="Основная БД")
@connection("analytics_db", ClickHouseConnectionManager,
            description="Аналитика")
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class DualDbAction(BaseAction):

    @aspect("Записать в обе БД")
    async def write(
        self, params, state, deps,
        connections: MultiDbConnections
    ):
        main_db = connections["connection"]
        analytics = connections["analytics_db"]
        await main_db.execute("INSERT INTO orders ...")
        await analytics.execute("INSERT INTO events ...")
        return state
```

При передаче в дочернее действие разработчик выбирает какие из них прокинуть:

```python
await deps.run_action(
    ChildAction, params,
    connections={"connection": connections["connection"]}
)
```

---

## Тестирование транзакций

В тестах соединение подменяется фейком через ActionTestMachine:

```python
class FakeConnectionManager(IConnectionManager):

    def __init__(self):
        self.executed_queries = []
        self.committed = False
        self.rolled_back = False

    async def open(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def execute(self, query, params=None):
        self.executed_queries.append((query, params))
        return 42

    def get_wrapper_class(self):
        return None


async def test_create_order():
    fake_db = FakeConnectionManager()

    machine = ActionTestMachine({
        PostgresConnectionManager: fake_db
    })

    result = await machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, product_id=10, quantity=2)
    )

    assert result.order_id == 42
    assert fake_db.committed is True
    assert len(fake_db.executed_queries) == 1
```

---

## Сравнение с традиционными подходами

Традиционный фреймворк начинает транзакцию автоматически через декоратор или middleware. AOA начинает явно через await db.open().

Традиционный фреймворк фиксирует автоматически при успехе. AOA фиксирует явно через await db.commit().

Традиционный фреймворк откатывает автоматически при ошибке. AOA откатывает явно через await db.rollback().

Традиционный фреймворк скрывает всё за магией. AOA делает всё видимым в коде аспекта.

При вложенных вызовах традиционный фреймворк использует неявный savepoint или создаёт новую транзакцию. AOA автоматически блокирует управление транзакцией через прокси.

Тестирование в традиционном фреймворке требует реальной БД или сложных моков. AOA тестируется просто через MockAction и ActionTestMachine.

---

## Итог

Управление транзакциями в AOA основано на трёх принципах.

Явность — разработчик сам открывает, фиксирует и откатывает транзакции.

Безопасность — при передаче соединения в дочернее действие оно автоматически оборачивается в прокси запрещающий управление транзакцией. Это гарантировано архитектурой а не соглашением [1].

Прозрачность — всегда видно какое соединение куда передаётся, кто им владеет и кто может управлять транзакцией.

Такой подход даёт полный контроль без boilerplate-кода и особенно ценен для систем со сложными сценариями согласованности данных и глубокой вложенностью действий.

---

## Что изучать дальше

17_async.md — асинхронность и работа с asyncio.

18_plugins.md — плагины и наблюдение за выполнением.

19_testing.md — полное руководство по тестированию.

12_create_resource_manager.md — создание собственного менеджера ресурсов.

06_guarantees.md — формальные гарантии архитектуры.
