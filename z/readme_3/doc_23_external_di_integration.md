23_external_di_integration.md

# Интеграция с внешними DI-контейнерами

AOA предоставляет встроенный механизм внедрения зависимостей через декоратор @depends и фабрику DependencyFactory. Однако в реальных проектах часто уже используются сторонние DI-контейнеры — inject, FastAPI Depends, ручные контейнеры или специализированные библиотеки. Этот документ объясняет как задействовать существующий контейнер не переписывая весь код и не отказываясь от преимуществ AOA [1].

---

## Параметр factory — ключевой инструмент интеграции

Декоратор @depends принимает опциональный параметр factory — функцию без аргументов которая возвращает готовый экземпляр зависимости. Внутри этой функции можно обратиться к любому внешнему контейнеру [1].

Если factory не указана — DependencyFactory создаёт объект через конструктор klass(). Если factory передана — фабрика вызывает её при первом обращении и кеширует результат на всё время выполнения действия.

Это открывает три возможности:

Первая — использовать любой внешний DI-контейнер для получения уже сконфигурированных объектов. Вторая — реализовать сложную логику создания зависимости. Третья — подменять зависимости в тестах без изменения кода действия.

---

## Пример интеграции с библиотекой inject

### Установка

```bash
pip install inject
```

### Сервис требующий конфигурации

```python
class DatabaseService:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def query(self, sql: str) -> str:
        return f"Executing '{sql}' on {self.connection_string}"
```

### Настройка inject

```python
import inject

def configure_inject(binder: inject.Binder) -> None:
    binder.bind(
        DatabaseService,
        DatabaseService("postgresql://localhost:5432/mydb")
    )

inject.configure(configure_inject)
```

### Действие с factory

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

@depends(DatabaseService, factory=lambda: inject.instance(DatabaseService))
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному пользователю")
class QueryAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        sql: str

    @dataclass(frozen=True)
    class Result(BaseResult):
        output: str

    @summary_aspect("Выполнить запрос через inject")
    async def execute(self, params, state, deps):
        db = deps.get(DatabaseService)
        output = db.query(params.sql)
        return QueryAction.Result(output=output)
```

При первом вызове deps.get(DatabaseService) фабрика вызывает inject.instance(DatabaseService). inject возвращает экземпляр созданный при конфигурации. Результат кешируется на всё время выполнения [1].

### Запуск

```python
from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Context.Context import Context

machine = ActionProductMachine(context=Context())
params = QueryAction.Params(sql="SELECT * FROM users")
result = await machine.run(QueryAction(), params)
print(result.output)
```

---

## Тестирование с подменой

ActionTestMachine подменяет зависимости через свой словарь моков. При этом factory в @depends не вызывается — мок перекрывает её автоматически [1]:

```python
from ActionMachine.Core.ActionTestMachine import ActionTestMachine

mock_db = DatabaseService("test_connection")
machine = ActionTestMachine({DatabaseService: mock_db})
result = await machine.run(QueryAction(), QueryAction.Params(sql="SELECT 1"))
assert result.output == "Executing 'SELECT 1' on test_connection"
```

Код действия не меняется. Только источник зависимости переключается.

---

## Альтернативные способы интеграции

### Адаптер-ресурс

Если логика доступа к контейнеру сложна или требуется состояние — создаётся ресурсный менеджер который внутри обращается к контейнеру:

```python
class InjectDatabaseAdapter:

    def get(self) -> DatabaseService:
        return inject.instance(DatabaseService)


@depends(InjectDatabaseAdapter)
class QueryAction(BaseAction):

    @summary_aspect("Запрос")
    async def execute(self, params, state, deps):
        db = deps.get(InjectDatabaseAdapter).get()
        output = db.query(params.sql)
        return QueryAction.Result(output=output)
```

Этот способ предпочтительнее когда логика доступа к контейнеру нетривиальна [1].

### Кастомизация DependencyFactory

Можно передать кастомную фабрику зависимостей для всей машины. Это даёт полный контроль но требует модификации машины и менее прозрачно:

```python
def custom_factory(dep_class):
    if dep_class in external_container:
        return external_container[dep_class]
    return dep_class()

machine = ActionProductMachine(
    context=Context(),
    dependency_factory=custom_factory
)
```

---

## Когда использовать factory

Используй параметр factory если:

Первое — идёт миграция легаси и уже есть готовый контейнер с конфигурацией.

Второе — объект требует сложной логики инициализации которую удобно вынести в отдельную функцию.

Третье — нужна интеграция с inject, dependency-injector, FastAPI Depends и другими популярными библиотеками.

Не используй factory если зависимость создаётся простым конструктором без параметров — это добавляет лишнюю сложность без пользы [1].

---

## Предостережения

Первое — фабрика вызывается один раз за выполнение действия и результат кешируется. Убедитесь что фабрика не имеет нежелательных побочных эффектов.

Второе — не злоупотребляйте factory. Слишком частое использование может запутать архитектуру. Зависимости должны быть явными и легко заменяемыми.

Третье — factory должна возвращать объект совместимый с klass. Mypy не проверит это автоматически.

---

## Полный пример с двумя контейнерами

```python
import inject
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import aspect, summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

def configure(binder):
    binder.bind(UserService, UserService("users_db"))
    binder.bind(OrderService, OrderService("orders_db"))

inject.configure(configure)

@depends(UserService, factory=lambda: inject.instance(UserService))
@depends(OrderService, factory=lambda: inject.instance(OrderService))
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CreateOrderAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        product_id: int

    @dataclass(frozen=True)
    class Result(BaseResult):
        order_id: int

    @aspect("Проверка пользователя")
    async def validate_user(self, params, state, deps):
        user_svc = deps.get(UserService)
        user = user_svc.get(params.user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        state["user"] = user
        return state

    @summary_aspect("Создание заказа")
    async def create(self, params, state, deps):
        order_svc = deps.get(OrderService)
        order_id = order_svc.create(
            state["user"].id,
            params.product_id
        )
        return CreateOrderAction.Result(order_id=order_id)
```

---

## Итог

Параметр factory в декораторе @depends — мощный инструмент который позволяет интегрировать AOA с любым внешним DI-контейнером практически без усилий. Это делает ActionEngine гибким и открытым для использования в существующих проектах сохраняя все преимущества чистой архитектуры: тестируемость, прозрачность и предсказуемость [1].

Встроенный DI через @depends и внешний контейнер через factory не противоречат друг другу. Они работают на разных уровнях и легко комбинируются в зависимости от нужд проекта.

---

## Что изучать дальше

24_architecture_overview.md — слои и поток данных в AOA.

25_choosing_action_aspect_resource.md — алгоритм выбора между абстракциями.

15_di.md — встроенный DI через @depends.

14_machine.md — жизненный цикл ActionMachine.

19_testing.md — тестирование с подменой зависимостей.