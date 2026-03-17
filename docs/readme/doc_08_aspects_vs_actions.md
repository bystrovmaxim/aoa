08_aspects_vs_actions.md

# Когда аспект, когда отдельное действие

Один из самых частых вопросов при работе с AOA: оставить логику аспектом или вынести в отдельное действие. Этот документ даёт практический алгоритм принятия решения, примеры трансформации и золотое правило которое работает в реальных проектах [1].

---

## Основная идея

Аспект — это шаг внутри одного бизнес-процесса.

Действие — это самостоятельная бизнес-операция.

Этого достаточно для принятия правильного решения в девяноста процентах случаев. Всё остальное — уточнения и признаки которые помогают в пограничных ситуациях.

---

## Когда логика остаётся аспектом

Оставляй логику аспектом если она:

Относится только к этому конкретному действию и нигде больше не нужна. Является одним шагом в последовательности, а не самостоятельной операцией. Не живёт вне контекста текущего процесса — если убрать действие, этот кусок логики тоже исчезнет. Тесно привязана к параметрам текущего процесса. Проста и локальна — один понятный шаг.

Примеры логики которая правильно остаётся аспектом:

Проверка входных данных перед расчётом. Загрузка связанных сущностей для текущего процесса. Подготовка временных данных в state. Промежуточные вычисления внутри одного сценария. Форматирование данных перед финальным шагом.

```python
@aspect("Проверка корзины")
async def validate_cart(self, params, state, deps):
    if not params.items:
        raise ValueError("Корзина пуста")
    if params.total <= 0:
        raise ValueError("Сумма должна быть положительной")
    return state
```

Эта логика живёт только в процессе оформления заказа. Ей нет смысла быть самостоятельным действием.

---

## Когда логика становится отдельным действием

Выноси логику в отдельное действие если она:

Начинает использоваться в двух и более местах — это главный сигнал. Представляет самостоятельную бизнес-операцию которая имеет ценность вне текущего сценария. Может эволюционировать независимо от остального кода. Требует собственной валидации, ролей или тестов. Достаточно сложна чтобы иметь свои собственные аспекты. Является концептуально важной операцией — валидация карты, расчёт скидки, проверка разрешений.

Примеры логики которая правильно становится отдельным действием:

Расчёт скидки — нужен в оформлении заказа и в предварительной оценке. Валидация карты — нужна при оплате и при сохранении карты. Проверка пользователя — нужна во многих сценариях. Нормализация данных — нужна при импорте и при ручном вводе.

```python
class CalculateDiscountAction(BaseAction):

    @dataclass(frozen=True)
    class Params(BaseParams):
        user_id: int
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

---

## Золотое правило AOA

Всегда начинай с аспекта. Если логика начинает повторяться — выноси в действие.

Это отражает реальную практику разработки. Аспекты быстро пишутся и легко рефакторятся. Из аспекта легко сделать действие когда придёт время. Преждевременное выделение действий перегружает архитектуру и создаёт сложность там где её не должно быть [1].

---

## Пример трансформации: аспект превращается в действие

Первый шаг — есть аспект внутри действия:

```python
@aspect("Расчёт скидки")
async def calc_discount(self, params, state, deps):
    if params.user.is_vip:
        state["discount"] = params.total * 0.1
    else:
        state["discount"] = 0.0
    return state
```

Через месяц появляется второе действие которому тоже нужен расчёт скидки. Это сигнал к трансформации.

Второй шаг — создаём отдельное действие:

```python
@CheckRoles(CheckRoles.ANY, desc="Внутренний расчёт")
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
        discount = params.total * 0.1 if params.is_vip else 0.0
        return CalculateDiscountAction.Result(discount=discount)
```

Третий шаг — заменяем аспект на вызов действия:

```python
@aspect("Расчёт скидки")
async def calc_discount(self, params, state, deps):
    result = await deps.run_action(
        CalculateDiscountAction,
        CalculateDiscountAction.Params(
            total=params.total,
            is_vip=params.user.is_vip
        )
    )
    state["discount"] = result.discount
    return state
```

Теперь одна и та же логика используется в нескольких действиях без дублирования.

---

## Пример трансформации: аспект распадается на несколько действий

Иногда один аспект держит слишком много обязанностей:

```python
@aspect("Проверка пользователя")
async def validate_user(self, params, state, deps):
    user = await deps.get(UserRepo).get(params.user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    if not user.is_active:
        raise ValueError("Пользователь заблокирован")
    if user.needs_2fa and not params.tfa_code:
        raise ValueError("Требуется двухфакторная аутентификация")
    if user.region == "EU" and not user.gdpr_confirmed:
        raise ValueError("Требуется подтверждение GDPR")
    state["user"] = user
    return state
```

Признаки что пора разбивать: много веток, разные причины завершения, логика которая может понадобиться в других местах.

Трансформация:

```python
class LoadUserAction(BaseAction): ...
class CheckUserActiveAction(BaseAction): ...
class CheckUser2FAAction(BaseAction): ...
class CheckUserGDPRAction(BaseAction): ...
```

Исходный аспект превращается в композицию:

```python
@aspect("Проверка пользователя")
async def validate_user(self, params, state, deps):
    user_result = await deps.run_action(
        LoadUserAction,
        LoadUserAction.Params(user_id=params.user_id)
    )
    await deps.run_action(
        CheckUserActiveAction,
        CheckUserActiveAction.Params(user_id=params.user_id)
    )
    state["user"] = user_result.user
    return state
```

---

## Алгоритм выбора

Первый вопрос. Эта логика — шаг процесса или самостоятельная операция? Если шаг — аспект. Если самостоятельная операция — действие.

Второй вопрос. Эта логика используется в нескольких местах или будет использоваться? Если да — действие. Если только здесь — аспект.

Третий вопрос. Хочется иметь собственный Result и Params? Если да — действие. Если нет — аспект.

Четвёртый вопрос. Логику нужно тестировать отдельно от остального процесса? Если да — действие. Если нет — аспект.

Пятый вопрос. Логика может эволюционировать независимо? Если да — действие. Если нет — аспект.

---

## Особый случай: класс с несколькими методами

Если легаси-класс содержит несколько разных бизнес-операций, каждый публичный метод становится отдельным действием [1]:

Исходный класс:

```python
class OrderService:
    def validate_order(self, ...): ...
    def calculate_total(self, ...): ...
    def apply_discount(self, ...): ...
    def create_order(self, ...): ...
    def send_confirmation(self, ...): ...
```

Трансформация:

```python
class ValidateOrderAction(BaseAction): ...
class CalculateTotalAction(BaseAction): ...
class ApplyDiscountAction(BaseAction): ...
class CreateOrderAction(BaseAction): ...
class SendOrderConfirmationAction(BaseAction): ...
```

И составное действие которое их объединяет:

```python
class ProcessOrderAction(BaseAction):

    @aspect("Валидация")
    async def validate(self, params, state, deps):
        await deps.run_action(ValidateOrderAction, ...)
        return state

    @aspect("Расчёт")
    async def calculate(self, params, state, deps):
        result = await deps.run_action(CalculateTotalAction, ...)
        state["total"] = result.total
        return state

    @summary_aspect("Создание заказа")
    async def create(self, params, state, deps):
        result = await deps.run_action(CreateOrderAction, ...)
        return ProcessOrderAction.Result(order_id=result.order_id)
```

---

## Что запрещено при выборе

Нельзя делать действие из каждого небольшого шага только потому что хочется большей структуры. Это ведёт к избыточному количеству классов и сложности без пользы.

Нельзя оставлять аспект когда он повторяется в двух местах. Дублирование логики — прямой сигнал к выделению действия.

Нельзя принимать решение только на основе размера кода. Маленький кусок может быть действием если он концептуально самостоятелен. Большой кусок может быть аспектом если он тесно связан с текущим процессом.

---

## Что изучать дальше

09_typed_state.md — TypedDict и чекеры для строгого контракта аспектов.

10_resource_managers.md — когда логика должна стать ресурсным менеджером.

11_action_vs_resource.md — различие между действием и ресурсом.

25_choosing_action_aspect_resource.md — полный алгоритм выбора между тремя вариантами.

26_migrating_legacy.md — как применять эти принципы при миграции легаси-кода.
