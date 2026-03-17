15_di.md

# Dependency Injection в AOA

DI в ActionEngine построен вокруг одного принципа: действие не знает как создавать зависимости — оно только объявляет что ему нужно. Фабрика зависимостей создаёт и передаёт эти объекты автоматически. Нет контейнеров, нет модулей, нет сложной конфигурации. Только декларация и фабрика [1].

---

## Зачем нужен DI в AOA

Action в AOA не знает о контексте, не знает о ресурсах и адаптерах, не хранит состояние и не создаёт объектов напрямую. Это позволяет тестировать действие изолированно, подменять зависимости моками, использовать разные реализации одного интерфейса и легко рефакторить инфраструктуру не трогая бизнес-код [1].

DI — это мост между миром Actions и миром Resources.

---

## @depends — объявление зависимостей

Зависимость объявляется декларативно через декоратор @depends на уровне класса:

```python
from ActionMachine.Core.AspectMethod import depends

@depends(UserRepository)
@depends(EmailService)
class NotifyUserAction(BaseAction):
    ...
```

Что происходит при объявлении:

@depends добавляет описание зависимости в атрибут _dependencies класса. Сам Action не знает как создаются эти зависимости. ActionMachine на этапе выполнения создаёт DependencyFactory и подставляет нужные объекты.

Это принципиально отличается от DI-контейнеров — в AOA зависимость принадлежит действию а не внешнему контейнеру [1].

---

## DependencyFactory — сердце DI

DependencyFactory создаётся ActionMachine автоматически для каждого вызова run. Она живёт ровно столько сколько живёт этот вызов.

При обращении к deps.get(SomeClass) происходит следующее:

Первое. Проверяется кеш _instances — если объект уже создавался возвращается он же. Второе. Проверяется что SomeClass объявлен через @depends — если не объявлен ошибка. Третье. Если указана factory — вызывается она. Иначе вызывается конструктор SomeClass(). Четвёртое. Результат сохраняется в кеш [1].

Один вызов run — одна фабрика — одно кеш-хранилище. Все аспекты получают один и тот же экземпляр каждой зависимости.

---

## Параметр factory — кастомная фабрика

Если зависимость требует параметров при создании или логики инициализации — используется параметр factory:

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
class CreateOrderAction(BaseAction):
    ...
```

factory — это функция без аргументов которая возвращает готовый экземпляр зависимости. Фабрика вызывается при первом обращении и результат кешируется на всё время выполнения действия [1].

Параметр factory открывает возможность интеграции с любым внешним DI-контейнером:

```python
@depends(DatabaseService, factory=lambda: inject.instance(DatabaseService))
class QueryAction(BaseAction):
    ...
```

---

## Получение зависимости в аспекте

Зависимость получается через deps.get() с указанием класса интерфейса:

```python
@aspect("Загрузка пользователя")
async def load_user(self, params, state, deps):
    repo = deps.get(UserRepository)
    user = await repo.get(params.user_id)
    state["user"] = user
    return state

@summary_aspect("Отправка уведомления")
async def notify(self, params, state, deps):
    email = deps.get(EmailService)
    await email.send(state["user"].email, params.message)
    return NotifyAction.Result(sent=True)
```

Нельзя использовать зависимость не объявленную через @depends. Попытка вызвать deps.get() для необъявленной зависимости вызовет ошибку [1].

---

## Вложенные действия через run_action

DependencyFactory умеет запускать другие действия через run_action:

```python
@aspect("Расчёт скидки")
async def calculate_discount(self, params, state, deps):
    result = await deps.run_action(
        CalculateDiscountAction,
        CalculateDiscountAction.Params(
            total=state["total"],
            is_vip=params.is_vip
        )
    )
    state["discount"] = result.discount
    return state
```

Что происходит при вызове run_action:

Первое. Создаётся экземпляр CalculateDiscountAction. Второе. Вызывается machine.run() с тем же контекстом и плагинами. Третье. nest_level увеличивается. Четвёртое. Плагины получают все события вложенного действия. Пятое. После завершения nest_level уменьшается и возвращается Result [1].

Это мощнейший механизм композиции бизнес-операций.

---

## Кеширование зависимостей

Важное свойство: один запуск Action — одна фабрика — одна копия каждой зависимости.

Это гарантирует что:

Все аспекты работают с одним и тем же экземпляром репозитория. Если EmailService записывает отправленные письма в список — все аспекты увидят один и тот же список. Вложенные действия используют одни и те же ресурсы если зависимость общая. Тесты ведут себя детерминированно [1].

---

## DI ресурсов и DI действий

Ресурсы и вложенные действия объявляются через @depends одинаково. Разница в характере зависимости.

Ресурсы имеют состояние — соединение, сессию, кеш. Действия stateless. Ресурсы создаются через DI и передаются действиям. Действия могут быть вложенными через run_action. Ресурсы не должны вызывать действия — обратной зависимости быть не должно [1].

---

## DI и тестирование

ActionTestMachine переопределяет фабрику зависимостей и позволяет подменять любые зависимости через словарь моков:

```python
from ActionMachine.Core.ActionTestMachine import ActionTestMachine

machine = ActionTestMachine({
    UserRepository: FakeUserRepo(),
    EmailService: MockEmail(),
    ChildAction: ChildAction.Result(doubled=42)
})
```

Механизм подмены:

Если мок — экземпляр класса, он используется как есть. Если мок — экземпляр BaseResult, он оборачивается в MockAction с фиксированным результатом. Если мок — функция, она оборачивается в MockAction с side_effect [1].

Это позволяет тестировать действие без инфраструктуры даже если оно вызывает вложенные действия:

```python
machine = ActionTestMachine({
    ChildAction: lambda params: ChildAction.Result(value=params.num * 3)
})
result = await machine.run(ParentAction(), ParentAction.Params(num=5))
assert result.value == 15
```

---

## Когда объявлять зависимость

Зависимость нужна если действие:

Взаимодействует с внешним миром через ресурс. Вызывает другое действие через run_action. Требует инфраструктурного сервиса.

Зависимость не нужна если:

Логика работает только через Params и state. Код не зависит от внешних эффектов.

Логирование должно быть в плагинах а не в действиях. Объявлять зависимость от Logger в Action — неправильно [1].

---

## Интеграция с внешними DI-контейнерами

Параметр factory позволяет интегрировать AOA с любым внешним DI-контейнером без переписывания кода. Пример с библиотекой inject:

```python
import inject

def configure(binder):
    binder.bind(DatabaseService, DatabaseService("postgresql://localhost/mydb"))

inject.configure(configure)

@depends(DatabaseService, factory=lambda: inject.instance(DatabaseService))
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class QueryAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        sql: str

    @dataclass(frozen=True)
    class Result(BaseResult):
        output: str

    @summary_aspect("Выполнить запрос")
    async def execute(self, params, state, deps):
        db = deps.get(DatabaseService)
        output = await db.query(params.sql)
        return QueryAction.Result(output=output)
```

В тестах зависимость подменяется через ActionTestMachine без изменения кода действия — мок просто перекрывает factory [1].

---

## Альтернативные способы интеграции с внешним DI

Первый способ — параметр factory в @depends. Простой и прозрачный. Подходит для большинства случаев.

Второй способ — ресурс-адаптер который внутри обращается к контейнеру:

```python
class InjectDatabaseAdapter:
    def get(self) -> DatabaseService:
        return inject.instance(DatabaseService)

@depends(InjectDatabaseAdapter)
class QueryAction(BaseAction):
    @summary_aspect("Запрос")
    async def execute(self, params, state, deps):
        db = deps.get(InjectDatabaseAdapter).get()
        ...
```

Этот способ предпочтительнее если логика доступа к контейнеру сложна [1].

---

## DI и чистота архитектуры

DI в AOA решает фундаментальную задачу: ядро Actions не зависит от инфраструктуры Resources. Зависимости инъецируются сверху через ActionMachine.

Это совпадает с принципом Dependency Rule из Clean Architecture: внутренние слои не должны знать о внешних. Action знает только интерфейс — порт. Конкретный адаптер подставляется через DI и может быть заменён без изменения бизнес-логики [1].

---

## Полный пример Action с DI

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

@depends(UserRepository)
@depends(PaymentGateway)
@depends(EmailService)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class ProcessPaymentAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        card_token: str
        amount: float

    @dataclass(frozen=True)
    class Result(BaseResult):
        transaction_id: str
        amount: float

    @aspect("Загрузка пользователя")
    async def load_user(self, params, state, deps):
        repo = deps.get(UserRepository)
        user = await repo.get(params.user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        state["user"] = user
        return state

    @aspect("Проведение платежа")
    async def charge(self, params, state, deps):
        gateway = deps.get(PaymentGateway)
        txn_id = await gateway.charge(params.card_token, params.amount)
        state["txn_id"] = txn_id
        return state

    @summary_aspect("Уведомление и результат")
    async def finish(self, params, state, deps):
        email = deps.get(EmailService)
        await email.send_confirmation(state["user"].email, state["txn_id"])
        return ProcessPaymentAction.Result(
            transaction_id=state["txn_id"],
            amount=params.amount
        )
```

---

## Что изучать дальше

16_transactions.md — управление транзакциями и connections.

17_async.md — асинхронность и работа с asyncio.

18_plugins.md — плагины и наблюдение.

19_testing.md — полное руководство по тестированию.

23_external_di_integration.md — интеграция с внешними DI-контейнерами.

14_machine.md — жизненный цикл ActionMachine.
