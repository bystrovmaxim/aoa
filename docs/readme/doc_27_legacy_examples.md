27_legacy_examples.md

# Примеры трансформации легаси-кода в AOA

Этот документ содержит практические пошаговые примеры превращения реального легаси-кода в чистую архитектуру AOA. Каждый пример показывает конкретный безопасный шаг после которого система остаётся рабочей и тестируемой [1].

---

## Пример 1. Монолитный класс — ресурс плюс действие

### Исходный код

```python
class PaymentManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.db = connect_db()
        self.http = create_http_client()
        self.stats = {}

    def process(self, user_id, card_token, amount):
        user = self.db.fetch(
            "SELECT * FROM users WHERE id=%s", (user_id,)
        )
        if not user:
            raise ValueError("User not found")
        if not self._validate_card(card_token, amount):
            raise ValueError("Invalid card")
        txn = self._charge(card_token, amount)
        self.db.execute("INSERT INTO payments ...")
        self.stats["total"] = self.stats.get("total", 0) + amount
        return {"success": True, "txn": txn}

    def _validate_card(self, card_token, amount):
        return self.http.post("/validate", json={
            "token": card_token, "amount": amount
        })

    def _charge(self, card_token, amount):
        return self.http.post("/charge", json={
            "token": card_token, "amount": amount
        })
```

Проблемы: синглтон, хранит состояние, смешивает транспорт и логику, нет изоляции, невозможно тестировать [1].

---

### Шаг 1. Создаём порт

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):

    @abstractmethod
    def validate_card(self, token: str, amount: float) -> bool: ...

    @abstractmethod
    def charge(self, token: str, amount: float) -> str: ...
```

Порт описывает только то что реально нужно домену. Не копируем весь легаси-класс [1].

---

### Шаг 2. Создаём адаптер

```python
class LegacyPaymentAdapter(PaymentGateway):

    def __init__(self):
        self._legacy = PaymentManager()

    def validate_card(self, token: str, amount: float) -> bool:
        return self._legacy._validate_card(token, amount)

    def charge(self, token: str, amount: float) -> str:
        return self._legacy._charge(token, amount)
```

Монстр спрятан за интерфейсом. Это anti-corruption layer [1].

---

### Шаг 3. Первое действие-обёртка

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import summary_aspect, depends
from ActionMachine.Auth.CheckRoles import CheckRoles

@depends(PaymentGateway)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному")
class ProcessPaymentAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
        card_token: str
        amount: float

    @dataclass(frozen=True)
    class Result(BaseResult):
        success: bool
        txn: str

    @summary_aspect("Временная обёртка")
    async def handle(self, params, state, deps):
        gateway = deps.get(PaymentGateway)
        if not gateway.validate_card(params.card_token, params.amount):
            return ProcessPaymentAction.Result(success=False, txn="")
        txn = gateway.charge(params.card_token, params.amount)
        return ProcessPaymentAction.Result(success=True, txn=txn)
```

Теперь есть единая точка входа, DI и возможность писать тесты. Логика монстра не тронута [1].

---

### Шаг 4. Выносим проверку пользователя в аспект

```python
@depends(PaymentGateway)
@depends(UserRepository)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному")
class ProcessPaymentAction(BaseAction):

    @aspect("Проверка пользователя")
    async def check_user(self, params, state, deps):
        user_repo = deps.get(UserRepository)
        user = await user_repo.get(params.user_id)
        if not user:
            raise ValueError("User not found")
        state["user"] = user
        return state

    @summary_aspect("Проведение платежа")
    async def charge(self, params, state, deps):
        gateway = deps.get(PaymentGateway)
        if not gateway.validate_card(params.card_token, params.amount):
            return ProcessPaymentAction.Result(success=False, txn="")
        txn = gateway.charge(params.card_token, params.amount)
        return ProcessPaymentAction.Result(success=True, txn=txn)
```

Один шаг — одна итерация. Старый код вызывает меньше логики. Новое действие вызывает больше [1].

---

### Шаг 5. Выносим валидацию карты в отдельное действие

Валидация карты нужна в нескольких сценариях — это сигнал к выделению отдельного действия [1]:

```python
@depends(PaymentGateway)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ValidateCardAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        card_token: str
        amount: float

    @dataclass(frozen=True)
    class Result(BaseResult):
        valid: bool

    @summary_aspect("Валидация карты")
    async def validate(self, params, state, deps):
        gateway = deps.get(PaymentGateway)
        valid = gateway.validate_card(params.card_token, params.amount)
        return ValidateCardAction.Result(valid=valid)
```

Подключаем в основное действие:

```python
@aspect("Валидация карты")
async def validate_card(self, params, state, deps):
    result = await deps.run_action(
        ValidateCardAction,
        ValidateCardAction.Params(
            card_token=params.card_token,
            amount=params.amount
        )
    )
    if not result.valid:
        raise ValueError("Invalid card")
    return state
```

---

### Шаг 6. Изолируем статистику как ресурс

Монстр хранит статистику — это долгоживущее состояние которое нельзя потерять [1]:

```python
class PaymentStats(ABC):

    @abstractmethod
    def record(self, amount: float) -> None: ...


class LegacyStatsAdapter(PaymentStats):

    def __init__(self):
        self._legacy = PaymentManager()

    def record(self, amount: float) -> None:
        self._legacy.stats["total"] = (
            self._legacy.stats.get("total", 0) + amount
        )
```

Добавляем аспект:

```python
@aspect("Запись статистики")
async def record_stats(self, params, state, deps):
    deps.get(PaymentStats).record(params.amount)
    return state
```

---

### Финальное состояние

Монстр умер. Осталось:

```python
@depends(UserRepository)
@depends(PaymentGateway)
@depends(PaymentStats)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому аутентифицированному")
class ProcessPaymentAction(BaseAction):

    @aspect("Проверка пользователя")
    async def check_user(self, params, state, deps): ...

    @aspect("Валидация карты")
    async def validate_card(self, params, state, deps): ...

    @aspect("Запись статистики")
    async def record_stats(self, params, state, deps): ...

    @summary_aspect("Проведение платежа")
    async def charge(self, params, state, deps): ...
```

Чистые действия. Ресурс хранит только состояние. Actions тестируются как функции [1].

---

## Пример 2. Класс с временным состоянием — сразу Action

### Исходный код

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

Состояние временное, создаётся заново каждый раз, внутри чистая бизнес-логика. Сразу делаем Action [1]:

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

---

## Пример 3. Класс с несколькими точками входа — набор Actions

### Исходный код

```python
class ReportsGenerator:

    def load(self): ...
    def process(self): ...
    def aggregate(self): ...
    def export_pdf(self): ...
    def export_csv(self): ...
```

Несколько точек входа и несколько обязанностей. Каждый публичный метод становится отдельным действием [1]:

```python
class LoadReportAction(BaseAction): ...
class ProcessReportAction(BaseAction): ...
class AggregateReportAction(BaseAction): ...
class ExportReportAsPdfAction(BaseAction): ...
class ExportReportAsCsvAction(BaseAction): ...
```

Составное действие объединяет их:

```python
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class GenerateFullReportAction(BaseAction):

    @aspect("Загрузка данных")
    async def load(self, params, state, deps):
        result = await deps.run_action(LoadReportAction, ...)
        state["report_data"] = result.data
        return state

    @aspect("Обработка")
    async def process(self, params, state, deps):
        result = await deps.run_action(ProcessReportAction, ...)
        state["processed"] = result.processed
        return state

    @aspect("Агрегация")
    async def aggregate(self, params, state, deps):
        result = await deps.run_action(AggregateReportAction, ...)
        state["aggregated"] = result.aggregated
        return state

    @summary_aspect("Экспорт")
    async def export(self, params, state, deps):
        if params.format == "pdf":
            result = await deps.run_action(ExportReportAsPdfAction, ...)
        else:
            result = await deps.run_action(ExportReportAsCsvAction, ...)
        return GenerateFullReportAction.Result(file_path=result.file_path)
```

---

## Пример 4. Аспект превращается в действие

### Исходный аспект

```python
@aspect("Расчёт скидки")
async def calc_discount(self, params, state, deps):
    if params.user.is_vip:
        state["discount"] = 0.1
    else:
        state["discount"] = 0.0
    return state
```

Через месяц тот же код нужен в EstimateOrderAction. Это главный сигнал к выделению [1].

### Новое действие

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

    @summary_aspect("Скидка")
    async def handle(self, params, state, deps):
        discount = 0.1 if params.is_vip else 0.0
        return CalculateDiscountAction.Result(discount=discount)
```

### Обновлённый аспект

```python
@aspect("Расчёт скидки")
async def calc_discount(self, params, state, deps):
    result = await deps.run_action(
        CalculateDiscountAction,
        CalculateDiscountAction.Params(
            total=state["total"],
            is_vip=params.user.is_vip
        )
    )
    state["discount"] = result.discount
    return state
```

Теперь логика в одном месте и переиспользуется без дублирования [1].

---

## Итоговые правила трансформации

Когда превращать монстра в ресурс:

Есть синглтон. Есть долгоживущее состояние. Есть соединения, кэши, статистика. Есть транспорт. Нельзя пересоздавать при каждом вызове [1].

Когда превращать в Action:

Состояние временное. Есть последовательность шагов. Есть бизнес-правила. Живёт один вызов [1].

Когда монстр превращается в несколько Actions:

Несколько точек входа. Несколько сценариев. Множество обязанностей. Каждый сценарий становится отдельным действием [1].

---

## Путь трансформации

Монстр — порт — адаптер — первое действие — аспекты — чистая архитектура AOA.

Шаг за шагом, безопасно, с тестами — без революций и полной переписки [1].

---

## Что изучать дальше

28_specification.md — полная формальная спецификация AOA.

29_comparison.md — сравнение с MVC, Clean Architecture, CQRS.

26_migrating_legacy.md — пошаговая стратегия миграции.

25_choosing_action_aspect_resource.md — алгоритм выбора абстракций.

19_testing.md — тестирование на каждом этапе трансформации.