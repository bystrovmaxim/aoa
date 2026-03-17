25_choosing_action_aspect_resource.md

# Алгоритм выбора между Action, Aspect и Resource

Разработчик в AOA постоянно принимает одно из трёх решений: оформить логику аспектом внутри действия, вынести её в отдельное действие или изолировать как ресурсный менеджер. Этот документ даёт практический алгоритм выбора, работающий в реальных проектах [1].

---

## Три типа логики в AOA

Первый тип — временная логика процесса. Это шаг внутри одного сценария, живущий только в рамках текущего действия. Правильный выбор — аспект [1].

Второй тип — самостоятельная бизнес-операция. Это логика которая имеет ценность вне одного сценария, может вызываться из нескольких мест и меняться независимо. Правильный выбор — отдельное действие [1].

Третий тип — работа с внешним миром. Это логика завязанная на состояние, соединения и транспорт. Правильный выбор — ресурсный менеджер [1].

Если мыслить через этот критерий практически всё раскладывается автоматически.

---

## Когда выбирать аспект

Аспект — это часть конвейера одного конкретного действия.

Выбирай аспект если логика:

Относится только к этому сценарию и нигде больше не нужна. Является простым шагом в последовательности. Не живёт сама по себе вне контекста текущего действия. Может использовать state предыдущих аспектов. Исчезнет вместе с действием если его выпилить.

Примеры:

```python
@aspect("Проверка входных данных")
async def validate(self, params, state, deps):
    if params.quantity <= 0:
        raise ValueError("Количество должно быть положительным")
    return state

@aspect("Подготовка данных")
async def prepare(self, params, state, deps):
    state["prepared_items"] = [i for i in params.items if i.active]
    return state
```

Практика AOA: всегда начинай с аспекта. Если логика начинает повторяться — выделяй в действие [1].

---

## Когда выбирать действие

Действие — это самостоятельная бизнес-операция.

Выбирай действие если логика:

Начинает использоваться в двух и более местах — это главный сигнал. Представляет самостоятельную бизнес-операцию с ценностью вне текущего сценария. Требует собственных Params и Result. Может эволюционировать независимо от остального кода. Должна тестироваться отдельно без запуска родительского действия [1].

Примеры:

```python
@CheckRoles(CheckRoles.ANY, desc="Расчёт скидки")
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

Использование из другого действия:

```python
@aspect("Применение скидки")
async def apply_discount(self, params, state, deps):
    result = await deps.run_action(
        CalculateDiscountAction,
        CalculateDiscountAction.Params(
            total=state["total"],
            is_vip=params.is_vip
        )
    )
    state["discount"] = result.discount
    state["final_total"] = result.final_total
    return state
```

---

## Когда выбирать ресурсный менеджер

Ресурс — это адаптер внешней системы с долгоживущим состоянием.

Выбирай ресурс если:

Класс содержит долгоживущее состояние — соединение, сессию, кеш, статистику. Состояние нельзя безопасно пересоздавать на каждый вызов. Логика транспортная — выполнить SQL, вызвать API, записать в файл. Внутри нет бизнес-правил — только маппинг данных и транспорт [1].

Примеры:

```python
class IOrderRepository(ABC):

    @abstractmethod
    async def create(self, user_id: int, total: float) -> int: ...

    @abstractmethod
    async def get(self, order_id: int) -> Order: ...


class PostgresOrderRepository(IOrderRepository):

    def __init__(self, pool):
        self._pool = pool

    async def create(self, user_id: int, total: float) -> int:
        try:
            return await self._pool.fetchval(
                "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
                user_id, total
            )
        except Exception as e:
            raise HandleException(f"Ошибка создания заказа: {e}") from e
```

---

## Полный алгоритм выбора

Первый вопрос. Есть долгоживущее состояние? Да — ресурс. Нет — следующий вопрос.

Второй вопрос. Логика транспортная — SQL, HTTP, файл, очередь? Да — ресурс. Нет — следующий вопрос.

Третий вопрос. Логика живёт только в рамках одного процесса? Да — аспект. Нет — следующий вопрос.

Четвёртый вопрос. Логика используется в нескольких местах? Да — действие. Нет — аспект.

Пятый вопрос. Нужен отдельный Result и Params? Да — действие. Нет — аспект.

Шестой вопрос. Нужно тестировать отдельно без окружения? Да — действие. Нет — аспект.

Седьмой вопрос. Появилось повторение аспекта в двух местах? Да — действие. Нет — оставить аспектом.

---

## Практические примеры принятия решений

Первый пример — расчёт налога:

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

Состояние временное, создаётся заново каждый раз, внутри чистая бизнес-логика. Правильный выбор — действие [1].

Второй пример — менеджер платёжной статистики:

```python
class PaymentStatsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.total = 0
        return cls._instance

    def record(self, amount):
        self.total += amount
```

Синглтон, накапливает статистику, состояние нельзя терять. Правильный выбор — ресурс [1].

Третий пример — проверка входных данных заказа:

```python
# Логика живёт только в ProcessOrderAction
# Нигде больше не нужна
# Является одним шагом конвейера
# Правильный выбор — аспект
@aspect("Проверка заказа")
async def validate_order(self, params, state, deps):
    if not params.items:
        raise ValueError("Список товаров пуст")
    if params.total <= 0:
        raise ValueError("Сумма должна быть положительной")
    return state
```

---

## Рефакторинг легаси через алгоритм

При работе с легаси-кодом алгоритм применяется пошагово [1].

Первый шаг. Применяем первый вопрос — есть ли долгоживущее состояние? Если да — оборачиваем монстра в ресурсный адаптер.

Второй шаг. Создаём действие с одним summary-аспектом которое вызывает адаптер. Логика не меняется — только появляется точка входа.

Третий шаг. Начинаем вытаскивать логику из легаси в аспекты. По одному шагу за итерацию.

Четвёртый шаг. Если аспект начинает повторяться в двух местах — выделяем в отдельное действие.

Пятый шаг. Когда весь бизнес перенесён — удаляем легаси-код.

```python
# Шаг 1 — монстр упакован в ресурс
class LegacyPaymentAdapter(IPaymentGateway):
    def __init__(self):
        self._legacy = LegacyPaymentManager()

    def charge(self, token: str, amount: float) -> str:
        return self._legacy._charge(token, amount)

# Шаг 2 — первое действие-обёртка
@depends(IPaymentGateway)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ProcessPaymentAction(BaseAction):

    @summary_aspect("Временная обёртка")
    async def handle(self, params, state, deps):
        gateway = deps.get(IPaymentGateway)
        txn = gateway.charge(params.card_token, params.amount)
        return ProcessPaymentAction.Result(transaction_id=txn)

# Шаг 3 — начинаем выносить логику в аспекты
@depends(IPaymentGateway)
@depends(IUserRepository)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ProcessPaymentAction(BaseAction):

    @aspect("Проверка пользователя")
    async def check_user(self, params, state, deps):
        user_repo = deps.get(IUserRepository)
        user = await user_repo.get(params.user_id)
        if not user:
            raise ValueError("Пользователь не найден")
        state["user"] = user
        return state

    @summary_aspect("Проведение платежа")
    async def charge(self, params, state, deps):
        gateway = deps.get(IPaymentGateway)
        txn = gateway.charge(params.card_token, params.amount)
        return ProcessPaymentAction.Result(transaction_id=txn)
```

---

## Короткий вывод

Аспект — это шаг внутри одного действия. Живёт и умирает вместе с ним.

Действие — это самостоятельная бизнес-операция. Может вызываться из нескольких мест.

Ресурс — это адаптер внешнего мира с долгоживущим состоянием.

Если сомневаешься — начни с аспекта. Если код начинает повторяться — сделай действие. Если есть долгоживущее состояние — сделай ресурс [1].

---

## Что изучать дальше

26_migrating_legacy.md — пошаговая миграция легаси-кода на AOA.

27_legacy_examples.md — конкретные примеры трансформации монстров.

07_actions.md — как правильно писать действия.

08_aspects_vs_actions.md — детальные критерии выбора между аспектом и действием.

11_action_vs_resource.md — детальные критерии выбора между действием и ресурсом.

28_specification.md — полная формальная модель AOA.
