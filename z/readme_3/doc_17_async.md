17_async.md

# Асинхронность в ActionEngine

ActionEngine построен на основе asyncio — современной модели асинхронного программирования в Python. Все аспекты действий объявляются как async def, и ActionMachine также полностью асинхронна. Это позволяет эффективно обрабатывать большое количество конкурентных запросов без лишних потоков. Этот документ объясняет как правильно запускать машину, как вызывать другие действия, как работать с ресурсами и как не заблокировать event loop при выполнении тяжёлых операций [1].

---

## Запуск ActionMachine

ActionMachine предоставляет асинхронный метод run. Его поведение зависит от контекста в котором выполняется код.

Асинхронный запуск из корутины — наиболее естественный способ. Если код находится внутри асинхронного контекста например в FastAPI-эндпоинте достаточно просто await:

```python
from ActionMachine.Core import ActionProductMachine
from ActionMachine.Context import Context

machine = ActionProductMachine(context=Context())
params = MyAction.Params(value=42)
result = await machine.run(MyAction(), params)
```

Синхронный запуск из обычной функции подходит для консольных скриптов и тестов без asyncio:

```python
import asyncio

def sync_run():
    params = MyAction.Params(value=42)
    result = asyncio.run(machine.run(MyAction(), params))
    return result
```

При этом asyncio.run создаёт новый event loop, выполняет корутину и закрывает loop. Для высоконагруженных сервисов предпочтительнее использовать асинхронный подход.

---

## Все аспекты асинхронны

Каждый аспект в ActionEngine объявляется как async def. Это единый стиль для всего кода действий — не нужно различать синхронные и асинхронные методы внутри одного действия [1]:

```python
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.AspectMethod import aspect, summary_aspect
from ActionMachine.Auth.CheckRoles import CheckRoles
from dataclasses import dataclass

@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ProcessDataAction(BaseAction):

    @dataclass(frozen=True)
    class Params:
        value: int

    @dataclass(frozen=True)
    class Result:
        output: int

    @aspect("Подготовка данных")
    async def prepare(self, params, state, deps):
        state["prepared"] = params.value * 2
        return state

    @summary_aspect("Финализация")
    async def finish(self, params, state, deps):
        return ProcessDataAction.Result(output=state["prepared"])
```

---

## Вызов других действий — композиция

Из аспекта можно вызвать другое действие через deps.run_action. Этот метод асинхронный и используется с await [1]:

```python
@aspect("Вызов дочернего действия")
async def call_child(self, params, state, deps):
    child_result = await deps.run_action(
        ChildAction,
        ChildAction.Params(value=params.num)
    )
    state["child_value"] = child_result.value
    return state
```

Метод run_action создаёт экземпляр указанного действия через DI, запускает его через ту же ActionMachine и возвращает результат. Плагины получают все события вложенного действия с корректным nest_level.

---

## Работа с ресурсами

Ресурсные менеджеры получаются через deps.get. Сам вызов get синхронный, но методы ресурса могут быть как синхронными так и асинхронными.

Синхронный ресурс — методы вызываются без await:

```python
@aspect("Запись в CSV")
async def write_csv(self, params, state, deps):
    csv_mgr = deps.get(CsvConnectionManager)
    csv_mgr.open()
    csv_mgr.write_rows(headers, rows)
    csv_mgr.commit()
    return state
```

Асинхронный ресурс — методы вызываются с await:

```python
@aspect("Запрос к API")
async def fetch_data(self, params, state, deps):
    http_client = deps.get(HttpClient)
    response = await http_client.get("/api/data")
    state["data"] = response.json()
    return state
```

Если ресурс асинхронный используем await. Если синхронный вызываем как обычно. Машина не накладывает ограничений на тип ресурса.

---

## Тяжёлые вычисления и блокировки event loop

Основная проблема асинхронного кода — случайная блокировка event loop. Если внутри корутины выполняется длительная CPU-intensive операция или синхронный I/O весь цикл событий останавливается и другие запросы перестают обрабатываться.

Никогда не делай так внутри аспекта:

```python
@aspect("Плохой пример")
async def bad_example(self, params, state, deps):
    time.sleep(5)          # блокирует весь event loop
    return state
```

Правильно использовать асинхронный аналог:

```python
@aspect("Хороший пример")
async def good_example(self, params, state, deps):
    await asyncio.sleep(5)  # не блокирует event loop
    return state
```

---

## CoreHelper — вынос тяжёлых операций в поток

ActionEngine предоставляет модуль CoreHelper с утилитами для безопасного выполнения синхронного кода в отдельных потоках [1].

Структура CoreHelper:

```python
# ActionMachine/Core/CoreHelper.py
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

class CoreHelper:
    @staticmethod
    async def run_in_thread(func: Callable[..., T], *args) -> T:
        """Запускает синхронную функцию в отдельном потоке."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
```

Использование для CPU-intensive операций:

```python
from ActionMachine.Core.CoreHelper import CoreHelper

@aspect("Тяжёлый расчёт")
async def heavy_computation(self, params, state, deps):
    def calculate(data):
        return sum(x * x for x in range(data))

    result = await CoreHelper.run_in_thread(calculate, params.big_number)
    state["result"] = result
    return state
```

Этот подход позволяет не блокировать event loop даже если синхронная функция выполняется секунды. В отдельном потоке нет запущенного event loop поэтому синхронный код работает корректно.

---

## Синхронные библиотеки с asyncio внутри

Некоторые библиотеки внутри себя вызывают asyncio.run или loop.run_until_complete. Если такая библиотека вызвана внутри уже работающего event loop возникнет RuntimeError: This event loop is already running. Решение — вынести вызов в поток через CoreHelper.run_in_thread [1]:

```python
@aspect("Вызов легаси библиотеки")
async def call_legacy_lib(self, params, state, deps):
    def legacy_call():
        return legacy_module.do_something(params.data)

    result = await CoreHelper.run_in_thread(legacy_call)
    state["legacy_result"] = result
    return state
```

---

## Три типичные проблемы и решения

Первая проблема — блокирующий вызов типа time.sleep. Решение — заменить на await asyncio.sleep.

Вторая проблема — тяжёлые CPU-вычисления которые блокируют event loop. Решение — вынести в await CoreHelper.run_in_thread.

Третья проблема — синхронная библиотека с asyncio.run внутри. Решение — также вынести в await CoreHelper.run_in_thread поскольку в отдельном потоке нет запущенного event loop.

---

## Асинхронные ресурсы и транзакции

При работе с асинхронными соединениями транзакционная логика также асинхронна. Аспекты открытия соединения, выполнения запросов и фиксации транзакции используют await для каждой операции:

```python
@aspect("Открыть соединение")
async def open_connection(self, params, state, deps, connections):
    db = connections["connection"]
    await db.open()
    return state

@aspect("Выполнить запрос")
async def execute_query(self, params, state, deps, connections):
    db = connections["connection"]
    result = await db.execute(
        "INSERT INTO orders (user_id) VALUES ($1) RETURNING id",
        (params.user_id,)
    )
    state["order_id"] = result
    return state

@summary_aspect("Зафиксировать транзакцию")
async def commit(self, params, state, deps, connections):
    db = connections["connection"]
    await db.commit()
    return MyAction.Result(order_id=state["order_id"])
```

---

## Тестирование асинхронного кода

ActionTestMachine полностью поддерживает асинхронные действия. Тесты пишутся через pytest-asyncio:

```python
import pytest

@pytest.mark.asyncio
async def test_async_action():
    machine = ActionTestMachine({
        HttpClient: FakeHttpClient()
    })

    result = await machine.run(
        FetchDataAction(),
        FetchDataAction.Params(url="/api/test")
    )

    assert result.data is not None
```

Если тест использует синхронный запуск достаточно asyncio.run:

```python
def test_sync_runner():
    import asyncio
    machine = ActionTestMachine()
    result = asyncio.run(
        machine.run(DoubleAction(), DoubleAction.Params(value=5))
    )
    assert result.doubled == 10
```

---

## Почему хелпер вынесен в отдельный модуль

Все вспомогательные утилиты собраны в классе CoreHelper в модуле ActionMachine.Core.CoreHelper [1]. Это позволяет не перегружать DependencyFactory дополнительными методами, легко расширять набор утилит, импортировать только нужные функции там где они необходимы и тестировать утилиты независимо от основного DI.

---

## Итог

ActionEngine с самого начала спроектирован для асинхронного выполнения и при этом предоставляет гибкие механизмы для интеграции с синхронным кодом.

Все аспекты объявляются как async def — единообразный код без исключений. Вызов дочерних действий через await deps.run_action интуитивно понятен. Ресурсы могут быть синхронными и асинхронными — их методы вызываются обычным образом. Для тяжёлых операций используется CoreHelper.run_in_thread который надёжно изолирует синхронный код от event loop [1].

---

## Что изучать дальше

18_plugins.md — плагины и наблюдение за выполнением.

19_testing.md — полное руководство по тестированию.

16_transactions.md — управление транзакциями в асинхронном коде.

14_machine.md — жизненный цикл ActionMachine.

12_create_resource_manager.md — создание асинхронных ресурсных менеджеров.