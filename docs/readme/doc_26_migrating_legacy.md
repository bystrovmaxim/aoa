26_migrating_legacy.md

# Пошаговая миграция легаси-кода на AOA

Легаси-код почти всегда представляет собой смесь транспорта, бизнес-логики, долгоживущего состояния и процессов которые пытаются делать всё сразу. AOA предоставляет безопасный итеративный путь миграции который не требует переписывания всего с нуля и сохраняет работоспособность системы на каждом шаге [1].

---

## Основная идея

Миграция начинается с изоляции монстра за интерфейсом. Затем логика постепенно переносится в аспекты и действия. Монстр умирает сам собой по мере того как его функции заменяются чистым кодом [1].

AOA разделяет роли которые в легаси смешаны:

Ресурсы управляют долгоживущим состоянием. Действия представляют бизнес-операции. Аспекты — линейные шаги внутри действий. ActionMachine — единая точка входа вокруг которой строится исполнение.

---

## Этап 0. Исходная точка — легаси-монстр

Типичный легаси-класс:

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
        user = self.db.fetch("SELECT * FROM users WHERE id=%s", (user_id,))
        if not user:
            raise ValueError("User not found")
        if not self._validate_card(card_token, amount):
            raise ValueError("Invalid card")
        txn = self._charge(card_token, amount)
        self.db.execute("INSERT INTO payments ...")
        self.stats["total"] = self.stats.get("total", 0) + amount
        return {"success": True, "txn": txn}
```

Проблемы этого кода: синглтон, хранит состояние, смешивает транспорт и логику, невозможно тестировать изолированно, нельзя заменить API или БД без переписывания.

---

## Этап 1. Изоляция монстра в ресурсный менеджер

Первый шаг — обернуть легаси-класс в адаптер который реализует строго определённый интерфейс [1].

Если у легаси-класса есть долгоживущее состояние — соединение, внутренние кэши, статистика, клиент API — его обязательно нужно изолировать как ресурс.

Создаём порт:

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):

    @abstractmethod
    def validate_card(self, token: str, amount: float) -> bool: ...

    @abstractmethod
    def charge(self, token: str, amount: float) -> str: ...
```

Порт описывает только то что реально требуется домену. Он не копирует весь легаси-класс.

Создаём адаптер-обёртку:

```python
class LegacyPaymentAdapter(PaymentGateway):

    def __init__(self):
        self._legacy = PaymentManager()

    def validate_card(self, token: str, amount: float) -> bool:
        return self._legacy._validate_card(token, amount)

    def charge(self, token: str, amount: float) -> str:
        return self._legacy._charge(token, amount)
```

Теперь монстр спрятан за интерфейсом. Это anti-corruption layer [1].

---

## Этап 2. Создание первого действия-обёртки

Создаём действие с одним summary-аспектом которое просто вызывает легаси-код через адаптер. Мы ничего не изменили в логике — это просто новая точка входа [1]:

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

    @summary_aspect("Временная обёртка легаси")
    async def handle(self, params, state, deps):
        gateway = deps.get(PaymentGateway)
        if not gateway.validate_card(params.card_token, params.amount):
            return ProcessPaymentAction.Result(success=False, txn="")
        txn = gateway.charge(params.card_token, params.amount)
        return ProcessPaymentAction.Result(success=True, txn=txn)
```

Теперь есть Action, одна точка входа, возможность мокировать ресурсы и писать тесты.

---

## Этап 3. Начинаем вытаскивать логику в аспекты

После обёртки постепенно переносим части легаси-кода в аспекты. Переносим один шаг за итерацию [1].

Переносим проверку пользователя:

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

Переносим валидацию карты в отдельное действие:

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

На каждом шаге: старый код вызывает меньше логики, новое действие вызывает больше логики, тесты покрывают новые аспекты [1].

---

## Этап 4. Изоляция статистики как ресурса

Монстр хранит статистику — значит это состояние которое нельзя потерять. Создаём порт и адаптер:

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

## Этап 5. Удаление легаси-кода

Когда все бизнес-шаги вынесены в аспекты:

Легаси-класс больше не нужен. Адаптер можно заменить на новую реализацию. Summary-аспект теперь только возвращает Result. Легаси-код полностью удаляется [1].

---

## Этап 6. Выделение повторяемой логики в отдельные действия

Когда аспекты начинают повторяться в разных процессах их нужно вынести в отдельные действия:

```python
@depends(PaymentGateway)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ValidateCardAction(BaseAction): ...

@depends(UserRepository)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class LoadUserAction(BaseAction): ...

@depends(PaymentStats)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class RecordPaymentStatsAction(BaseAction): ...
```

Теперь действия переиспользуются:

```python
result = await deps.run_action(ValidateCardAction, params)
```

---

## Алгоритм принятия решений при миграции

Первый вопрос. У монстра есть долгоживущее состояние? Да — упаковать в ресурс, создать порт и адаптер.

Второй вопрос. Состояние временное? Да — сразу разбивать на действие с аспектами.

Третий вопрос. Монстр смешанный — и состояние и логика? Двухэтапная миграция: сначала ресурсный слой, затем действия вытягивают бизнес-логику наружу.

---

## Пример полной трансформации класса с несколькими методами

Исходный класс:

```python
class OrderService:
    def validate_user(self, user_id): ...
    def validate_cart(self, items): ...
    def calculate_total(self, items): ...
    def charge_card(self, token, amount): ...
    def save_order(self, user_id, items, total): ...
    def send_email(self, user_id, order_id): ...
```

Каждый метод становится отдельным действием [1]:

```python
class ValidateUserAction(BaseAction): ...
class ValidateCartAction(BaseAction): ...
class CalculateTotalAction(BaseAction): ...
class ChargeCardAction(BaseAction): ...
class SaveOrderAction(BaseAction): ...
class SendOrderEmailAction(BaseAction): ...
```

Составное действие которое их объединяет:

```python
@depends(UserRepository)
@depends(PaymentGateway)
@depends(OrderRepository)
@depends(EmailService)
@CheckRoles(CheckRoles.ANY, desc="Доступно любому")
class ProcessOrderAction(BaseAction):

    @aspect("Валидация пользователя")
    async def validate_user(self, params, state, deps):
        await deps.run_action(ValidateUserAction, ...)
        return state

    @aspect("Валидация корзины")
    async def validate_cart(self, params, state, deps):
        await deps.run_action(ValidateCartAction, ...)
        return state

    @aspect("Расчёт суммы")
    async def calculate(self, params, state, deps):
        result = await deps.run_action(CalculateTotalAction, ...)
        state["total"] = result.total
        return state

    @aspect("Списание оплаты")
    async def charge(self, params, state, deps):
        result = await deps.run_action(ChargeCardAction, ...)
        state["txn_id"] = result.txn_id
        return state

    @summary_aspect("Сохранение заказа и уведомление")
    async def finish(self, params, state, deps):
        result = await deps.run_action(SaveOrderAction, ...)
        await deps.run_action(SendOrderEmailAction, ...)
        return ProcessOrderAction.Result(order_id=result.order_id)
```

---

## Итоговый алгоритм миграции

Первый шаг. Изолировать инфраструктуру через порт и адаптер.

Второй шаг. Создать действие-обёртку с одним summary-аспектом.

Третий шаг. Постепенно вытаскивать аспекты — по одному шагу за итерацию.

Четвёртый шаг. Убрать легаси-код когда он стал ненужен.

Пятый шаг. Выделять общую логику в отдельные действия по мере накопления повторений.

Шестой шаг. Чистая архитектура: Actions плюс Resources плюс Machine [1].

Этот путь безопасен, повторяем, тестируем и отлично работает в реальных проектах.

---

## Что изучать дальше

27_legacy_examples.md — конкретные примеры трансформации монстров.

25_choosing_action_aspect_resource.md — алгоритм выбора между action, aspect и resource.

11_action_vs_resource.md — детальные критерии выбора.

08_aspects_vs_actions.md — когда аспект, когда отдельное действие.

19_testing.md — тестирование на каждом этапе миграции.

28_specification.md — полная формальная модель AOA.
