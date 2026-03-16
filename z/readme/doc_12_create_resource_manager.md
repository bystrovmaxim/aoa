12_create_resource_manager.md

# Пошаговое создание собственного менеджера ресурсов

Этот документ объясняет как создать собственный ресурсный менеджер в AOA с нуля. Архитектура строится из трёх взаимосвязанных компонентов: интерфейса, конкретной реализации и прокси-обёртки. Каждый из них решает свою задачу и вместе они обеспечивают безопасную работу с внешними системами на любом уровне вложенности.

---

## Зачем три компонента

В традиционных подходах менеджер соединения — это один класс который делает всё: открывает соединение, выполняет запросы, управляет транзакциями. Это создаёт проблему: если передать такой объект в дочернее действие, оно может случайно вызвать commit или rollback и разрушить транзакцию родителя.

AOA решает это архитектурно через три отдельных класса.

Интерфейс описывает что умеет ресурс — набор методов доступных бизнес-логике.

Конкретный класс реализует как работает ресурс — реальные вызовы к библиотеке.

Прокси-обёртка контролирует кому разрешены какие операции — блокирует управление транзакциями на вложенных уровнях, но пропускает выполнение запросов.

Конкретный класс остаётся простым и сосредоточенным на своей задаче, а безопасность вложенных вызовов обеспечивается на уровне прокси [1].

---

## Иерархия классов

Все ресурсные менеджеры строятся по единой иерархии:

```
BaseResourceManager
↑
IConnectionManager         — интерфейс для конкретного типа ресурса
↑
PostgresConnectionManager  — конкретная реализация
WrapperConnectionManager   — прокси-обёртка
```

BaseResourceManager — абстрактный базовый класс для всех ресурсов. Содержит единственный абстрактный метод get_wrapper_class который должен вернуть класс прокси-обёртки [1].

Интерфейс наследует BaseResourceManager и определяет конкретные методы: open, commit, rollback, execute.

Конкретный класс реализует интерфейс используя реальную библиотеку. Метод get_wrapper_class возвращает класс прокси.

Прокси-обёртка реализует тот же интерфейс но блокирует опасные методы и делегирует безопасные.

---

## Шаг 1. Создание интерфейса

Интерфейс наследует BaseResourceManager и объявляет все методы которые будут доступны действиям. Включайте только те методы которые реально нужны бизнес-логике.

```python
# ResourceManagers/IMySQLConnectionManager.py

from abc import abstractmethod
from typing import Any, Optional, Tuple
from .BaseResourceManager import BaseResourceManager

class IMySQLConnectionManager(BaseResourceManager):
    """
    Интерфейс менеджера соединения с MySQL.
    Определяет контракт для всех реализаций.
    Действия работают с этим интерфейсом,
    а не с конкретными реализациями.
    """

    @abstractmethod
    async def open(self) -> None:
        """Открыть соединение с базой данных."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Зафиксировать транзакцию."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Откатить транзакцию."""
        pass

    @abstractmethod
    async def execute(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> Any:
        """Выполнить SQL-запрос и вернуть результат."""
        pass
```

---

## Шаг 2. Реализация конкретного менеджера

Конкретный класс реализует все методы интерфейса используя реальную библиотеку. Ошибки оборачиваются в HandleException — единообразное исключение ActionEngine для инфраструктурных ошибок.

Ключевой метод get_wrapper_class возвращает класс прокси-обёртки которая будет создана при передаче ресурса в дочернее действие.

```python
# ResourceManagers/MySQLConnectionManager.py

import aiomysql
from typing import Any, Dict, Optional, Tuple, Type
from ActionMachine.Core.Exceptions import HandleException
from .IMySQLConnectionManager import IMySQLConnectionManager

class MySQLConnectionManager(IMySQLConnectionManager):
    """
    Реальный менеджер соединения с MySQL.
    Выполняет непосредственную работу с aiomysql.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self._params = connection_params
        self._conn: Optional[aiomysql.Connection] = None

    async def open(self) -> None:
        try:
            self._conn = await aiomysql.connect(**self._params)
        except Exception as e:
            raise HandleException(f"Ошибка подключения к MySQL: {e}") from e

    async def commit(self) -> None:
        if self._conn is None:
            raise HandleException("Соединение не открыто")
        try:
            await self._conn.commit()
        except Exception as e:
            raise HandleException(f"Ошибка при commit: {e}") from e

    async def rollback(self) -> None:
        if self._conn is None:
            raise HandleException("Соединение не открыто")
        try:
            await self._conn.rollback()
        except Exception as e:
            raise HandleException(f"Ошибка при rollback: {e}") from e

    async def execute(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> Any:
        if self._conn is None:
            raise HandleException("Соединение не открыто")
        try:
            async with self._conn.cursor() as cur:
                await cur.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    return await cur.fetchall()
                return cur.rowcount
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}") from e

    def get_wrapper_class(self) -> Optional[Type['IMySQLConnectionManager']]:
        """
        Возвращает класс прокси-обёртки для передачи в дочерние действия.
        DependencyFactory автоматически создаст её экземпляр
        при передаче через connections.
        """
        from .MySQLConnectionWrapper import MySQLConnectionWrapper
        return MySQLConnectionWrapper
```

---

## Шаг 3. Создание прокси-обёртки

Прокси реализует тот же интерфейс но блокирует методы управления транзакциями выбрасывая TransactionProhibitedError. Метод execute делегируется оригинальному объекту — дочернее действие может выполнять запросы но не может управлять транзакцией.

```python
# ResourceManagers/MySQLConnectionWrapper.py

from typing import Any, Optional, Tuple, Type
from ActionMachine.Core.Exceptions import TransactionProhibitedError, HandleException
from .IMySQLConnectionManager import IMySQLConnectionManager

class MySQLConnectionWrapper(IMySQLConnectionManager):
    """
    Прокси-обёртка для менеджера соединения с MySQL.
    Запрещает управление транзакциями на вложенных уровнях,
    но разрешает выполнение запросов.
    """

    def __init__(self, connection_manager: IMySQLConnectionManager):
        self._connection_manager = connection_manager

    async def open(self) -> None:
        raise TransactionProhibitedError(
            "Открытие соединения разрешено только в действии-владельце. "
            "Текущее действие получило ресурс через прокси."
        )

    async def commit(self) -> None:
        raise TransactionProhibitedError(
            "Фиксация транзакции разрешена только в действии-владельце. "
            "Текущее действие получило ресурс через прокси."
        )

    async def rollback(self) -> None:
        raise TransactionProhibitedError(
            "Откат транзакции разрешён только в действии-владельце. "
            "Текущее действие получило ресурс через прокси."
        )

    async def execute(
        self, query: str, params: Optional[Tuple[Any, ...]] = None
    ) -> Any:
        """Делегирует выполнение запроса оригинальному менеджеру."""
        try:
            return await self._connection_manager.execute(query, params)
        except Exception as e:
            raise HandleException(f"Ошибка выполнения SQL: {e}") from e

    def get_wrapper_class(self) -> Optional[Type['IMySQLConnectionManager']]:
        """
        Прокси возвращает свой же класс.
        При глубокой вложенности прокси оборачивается снова —
        управление транзакциями остаётся запрещённым на любом уровне.
        """
        return MySQLConnectionWrapper
```

---

## Как работает автоматическое оборачивание

Когда действие передаёт connections в дочернее через deps.run_action происходит следующее [1]:

Первое. DependencyFactory проходит по каждому connection в словаре.

Второе. Для каждого connection вызывается get_wrapper_class.

Третье. Если класс-обёртка возвращён создаётся экземпляр обёртки с оригинальным connection в конструкторе.

Четвёртое. Новый словарь с обёрнутыми connections передаётся в machine.run дочернего действия.

Пятое. Машина передаёт обёрнутый словарь во все аспекты дочернего действия.

При дальнейшей вложенности обёртка оборачивается снова. execute по-прежнему делегируется к реальному соединению через цепочку проксей, а commit, rollback, open запрещены на любом уровне.

---

## Использование ресурса в Action

```python
from dataclasses import dataclass
from typing import TypedDict
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends, connection
from ActionMachine.Auth.CheckRoles import CheckRoles
from .IMySQLConnectionManager import IMySQLConnectionManager
from .MySQLConnectionManager import MySQLConnectionManager

class OrderConnections(TypedDict, total=False):
    connection: IMySQLConnectionManager

class OrderState(TypedDict, total=False):
    order_id: int

@depends(
    MySQLConnectionManager,
    factory=lambda: MySQLConnectionManager({
        "host": "localhost",
        "port": 3306,
        "user": "app",
        "password": "secret",
        "db": "shop"
    })
)
@connection("connection", MySQLConnectionManager,
            description="Основное соединение с БД")
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному")
class CreateOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        product_id: int
        quantity: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int

    @aspect("Открыть соединение")
    async def open_connection(self, params, state: OrderState, deps,
                               connections: OrderConnections) -> OrderState:
        await connections["connection"].open()
        return OrderState()

    @aspect("Создать заказ")
    async def insert_order(self, params, state: OrderState, deps,
                            connections: OrderConnections) -> OrderState:
        result = await connections["connection"].execute(
            "INSERT INTO orders (user_id, product_id, quantity) "
            "VALUES (%s, %s, %s)",
            (params.user_id, params.product_id, params.quantity)
        )
        return OrderState(order_id=result)

    @summary_aspect("Зафиксировать транзакцию")
    async def finish(self, params, state: OrderState, deps,
                     connections: OrderConnections) -> Result:
        await connections["connection"].commit()
        return CreateOrderAction.Result(order_id=state["order_id"])
```

---

## Ресурс без транзакций

Не все ресурсы управляют транзакциями. Для HTTP-клиентов, кешей и файловых хранилищ прокси может разрешать все методы или блокировать только часть. Если передача в дочернее действие не нужна — get_wrapper_class возвращает None.

```python
class SimpleHttpClient(BaseResourceManager):

    def __init__(self, base_url: str):
        self._base_url = base_url
        self._client = httpx.AsyncClient()

    async def get(self, path: str) -> dict:
        try:
            response = await self._client.get(f"{self._base_url}{path}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HandleException(f"Ошибка HTTP запроса: {e}") from e

    def get_wrapper_class(self):
        return None  # передача в дочерние действия не нужна
```

---

## Контрольный список для создания нового ресурса

Первый шаг. Создать интерфейс наследующий BaseResourceManager. Это определит контракт для бизнес-логики.

Второй шаг. Реализовать конкретный класс. Это инкапсулирует реальную работу с внешней системой.

Третий шаг. Реализовать get_wrapper_class в конкретном классе. Это указывает какой прокси использовать для дочерних действий.

Четвёртый шаг. Создать прокси-обёртку с тем же интерфейсом. Это заблокирует опасные методы и делегирует безопасные.

Пятый шаг. В прокси реализовать get_wrapper_class возвращая свой же класс или None. Это обеспечивает корректное поведение при глубокой вложенности.

---

## Тестирование ресурса

В тестах ресурс подменяется фейком через ActionTestMachine:

```python
class FakeMySQLManager(IMySQLConnectionManager):

    def __init__(self):
        self.executed_queries = []
        self.committed = False

    async def open(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def execute(self, query, params=None):
        self.executed_queries.append((query, params))
        return 42

    def get_wrapper_class(self):
        return None


async def test_create_order():
    fake_db = FakeMySQLManager()

    machine = ActionTestMachine({
        MySQLConnectionManager: fake_db
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

## Что изучать дальше

13_errors_in_resources.md — обработка ошибок в ресурсных менеджерах.

14_machine.md — как ActionMachine работает с зависимостями и connections.

15_di.md — декларативное внедрение зависимостей.

16_transactions.md — полное руководство по управлению транзакциями.

19_testing.md — тестирование Actions с фейковыми ресурсами.