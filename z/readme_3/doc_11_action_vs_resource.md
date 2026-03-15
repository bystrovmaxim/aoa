11_action_vs_resource.md

# Когда Action, когда Resource

Одно из ключевых решений в AOA — понять правильно ли оформлена логика. Это действие или ресурсный менеджер? Этот документ даёт чёткий алгоритм, практические примеры и золотое правило которое работает в реальных проектах [1].

---

## Основная идея

Action — это бизнес-операция без состояния.

Resource — это адаптер который управляет долгоживущим состоянием внешнего мира.

Если логика привязана к данным процесса — это Action. Если логика привязана к внешнему ресурсу и его состоянию — это Resource [1].

---

## Когда логика — Action

Action следует выбирать если:

Класс или функция не хранит долгоживущего состояния. Все данные приходят в Params и живут только в рамках одного вызова.

Логика — бизнес-правило, а не транспорт. Рассчитать скидку, создать заказ, проверить разрешения, сформировать отчёт.

Логику можно выразить в виде последовательности этапов — аспектов.

Код можно безопасно пересоздавать для каждого вызова.

Логику можно переиспользовать из других действий через deps.run_action().

Action — это принятие решений. Он ничего не знает о внешнем мире, потому что внешним миром управляют ресурсы.

Примеры логики которая правильно становится Action:

Рассчитать итоговую стоимость заказа. Определить доступ пользователя. Валидировать набор данных. Выполнить бизнес-правило на основе входных параметров. Нормализовать данные перед сохранением.

```python
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
```

Это Action потому что он принимает решение на основе входных данных, не хранит состояния и может быть вызван из любого другого действия.

---

## Когда логика — Resource

Resource выбирается если:

Класс содержит долгоживущее состояние: соединения с БД, пулы HTTP-клиентов, кэши, внутренние статистики, авторизационные или файловые сессии.

Состояние нельзя безопасно пересоздавать каждый раз: открытое соединение с БД, внешний HTTP-клиент с Keep-Alive, метрики накапливающиеся внутри объекта, файловый дескриптор.

Логика транспортная: выполнить SQL, вызвать API, записать строку в файл, прочитать записи.

Внутри нет бизнес-правил — только маппинг данных и транспорт.

Примеры логики которая правильно становится Resource:

PostgresConnectionManager — управление соединением с БД. HTTP-клиент внешнего сервиса с авторизацией. Репозиторий данных без бизнес-правил. Легаси-класс с внутренними кэшами и соединениями.

```python
class IOrderRepository(ABC):

    @abstractmethod
    async def create(self, user_id: int, total: float) -> int: ...

    @abstractmethod
    async def get(self, order_id: int) -> Order: ...

    @abstractmethod
    async def update_status(self, order_id: int, status: str) -> None: ...


class PostgresOrderRepository(IOrderRepository):

    def __init__(self, connection_string: str):
        self._conn_string = connection_string
        self._pool = None

    async def create(self, user_id: int, total: float) -> int:
        try:
            result = await self._pool.fetchval(
                "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
                user_id, total
            )
            return result
        except Exception as e:
            raise HandleException(f"Ошибка создания заказа: {e}") from e
```

Это Resource потому что он управляет соединением с БД, хранит пул соединений между вызовами и занимается только транспортом — никаких бизнес-решений.

---

## Золотое правило AOA

Если состояние должно жить дольше одного вызова — это Resource. Если состояние живёт только внутри одного вызова — это Action [1].

Этот критерий практически всегда даёт правильный ответ.

---

## Примеры правильного выбора

Первый пример. Временное состояние — Action.

```python
class TaxCalculator:
    def __init__(self, region):
        self.region = region
        self.total = 0

    def add(self, price):
        self.total += price

    def calculate(self):
        rates = {"EU": 0.2, "US": 0.07}
        return self.total * rates.get(self.region, 0.15)
```

Состояние временное, создаётся каждый раз заново, внутри чистая бизнес-логика. Это Action:

```python
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CalculateTaxAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        region: str
        prices: list

    @dataclass(frozen=True)
    class Result(BaseResult):
        tax: float

    @summary_aspect("Расчёт налога")
    async def handle(self, params, state, deps):
        rates = {"EU": 0.2, "US": 0.07}
        total = sum(params.prices)
        rate = rates.get(params.region, 0.15)
        return CalculateTaxAction.Result(tax=total * rate)
```

Второй пример. Долгоживущее состояние — Resource.

```python
class PaymentStatsMonster:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.total = 0
        return cls._instance

    def record(self, amount):
        self.total += amount
```

Накапливает статистику, является синглтоном, состояние нельзя терять. Это Resource:

```python
class IPaymentStats(ABC):

    @abstractmethod
    def record(self, amount: float) -> None: ...

    @abstractmethod
    def get_total(self) -> float: ...


class LegacyPaymentStatsAdapter(IPaymentStats):

    def __init__(self):
        self._legacy = PaymentStatsMonster()

    def record(self, amount: float) -> None:
        self._legacy.record(amount)

    def get_total(self) -> float:
        return self._legacy.total
```

---

## Смешанный случай — монстр с логикой и состоянием

Типичная ситуация в легаси: класс одновременно хранит состояние, содержит бизнес-логику и общается с внешним миром. Это самый сложный случай.

Правильная стратегия миграции:

Первый шаг — изолировать монстра как Resource. Создать порт, адаптер и перенести туда весь транспортный слой.

Второй шаг — создать Action который вызывает ресурс как есть. Один summary-аспект, один вызов адаптера.

Третий шаг — постепенно выносить бизнес-логику из ресурса в аспекты Action.

Четвёртый шаг — когда логика собрана в Action, ресурс становится чистым адаптером без бизнес-правил.

```python
# Исходный монстр
class LegacyOrderProcessor:
    def __init__(self):
        self.db = connect_db()          # долгоживущее состояние
        self.stats = {}                 # долгоживущее состояние

    def process(self, user_id, items):
        # и транспорт, и бизнес-логика в одном месте
        total = sum(i.price for i in items)
        if total > 10000:
            total *= 0.9               # скидка — бизнес-правило
        order_id = self.db.insert(user_id, total)
        self.stats["total"] = self.stats.get("total", 0) + total
        return order_id


# Шаг 1 — порт
class IOrderProcessor(ABC):

    @abstractmethod
    def process(self, user_id: int, items: list) -> int: ...


# Шаг 1 — адаптер
class LegacyOrderAdapter(IOrderProcessor):

    def __init__(self):
        self._legacy = LegacyOrderProcessor()

    def process(self, user_id: int, items: list) -> int:
        return self._legacy.process(user_id, items)


# Шаг 2 — первое действие-обёртка
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

    @summary_aspect("Создание заказа")
    async def handle(self, params, state, deps):
        processor = deps.get(IOrderProcessor)
        order_id = processor.process(params.user_id, params.items)
        return ProcessOrderAction.Result(order_id=order_id)
```

Теперь у нас есть чистая точка входа и возможность писать тесты. Бизнес-логика будет постепенно переноситься в аспекты.

---

## Алгоритм выбора

Первый вопрос. Класс хранит состояние между вызовами? Да — Resource. Нет — следующий вопрос.

Второй вопрос. Логика транспортная — SQL, HTTP, файл? Да — Resource. Нет — следующий вопрос.

Третий вопрос. Это бизнес-правило или вычисление? Да — Action. Нет — уточни назначение.

Четвёртый вопрос. Можно пересоздавать на каждый вызов? Да — Action. Нет — Resource.

Пятый вопрос. Логика переиспользуется в нескольких местах? Да — Action. Нет — возможно аспект.

---

## Как Action и Resource работают вместе

Action принимает решение что делать. Resource знает как это сделать.

```python
@depends(IOrderRepository)
@depends(IPaymentGateway)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class CreateOrderAction(BaseAction):

    @aspect("Проверка наличия товаров")
    async def check_stock(self, params, state, deps):
        repo = deps.get(IOrderRepository)
        product = await repo.get_product(params.product_id)
        if product.stock < params.quantity:
            raise ValueError("Недостаточно товара")
        state["product"] = product
        return state

    @aspect("Списание оплаты")
    async def charge(self, params, state, deps):
        gateway = deps.get(IPaymentGateway)
        txn_id = await gateway.charge(params.card_token, state["product"].price)
        state["txn_id"] = txn_id
        return state

    @summary_aspect("Создание заказа")
    async def create(self, params, state, deps):
        repo = deps.get(IOrderRepository)
        order_id = await repo.create(params.user_id, state["product"].price)
        return CreateOrderAction.Result(order_id=order_id, txn_id=state["txn_id"])
```

Action работает только с портами IOrderRepository и IPaymentGateway. Конкретные реализации подставляются через DI и могут быть заменены без изменения логики.

---

## Тестирование

В тестах Resource подменяется фейком через ActionTestMachine:

```python
class FakeOrderRepository(IOrderRepository):

    def __init__(self):
        self.created_orders = []

    async def create(self, user_id: int, total: float) -> int:
        order = {"user_id": user_id, "total": total, "id": len(self.created_orders) + 1}
        self.created_orders.append(order)
        return order["id"]

    async def get_product(self, product_id: int):
        return Product(id=product_id, price=100.0, stock=10)


def test_create_order():
    fake_repo = FakeOrderRepository()
    fake_gateway = FakePaymentGateway()

    machine = ActionTestMachine({
        IOrderRepository: fake_repo,
        IPaymentGateway: fake_gateway
    })

    result = machine.run(
        CreateOrderAction(),
        CreateOrderAction.Params(user_id=1, product_id=10, quantity=2, card_token="tok_test")
    )

    assert result.order_id == 1
    assert len(fake_repo.created_orders) == 1
```

Тест не требует реальной БД или платёжного шлюза. Фейки реализуют те же порты и контролируют поведение.

---

## Что изучать дальше

12_create_resource_manager.md — пошаговое создание собственного менеджера ресурсов.

13_errors_in_resources.md — обработка ошибок в ресурсах.

14_machine.md — как ActionMachine работает с зависимостями.

15_di.md — декларативное внедрение зависимостей.

16_transactions.md — управление транзакциями через connections.

25_choosing_action_aspect_resource.md — полный алгоритм выбора между тремя вариантами.

26_migrating_legacy.md — пошаговая миграция легаси-монстров.