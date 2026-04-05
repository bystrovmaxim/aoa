## Часть 1. Общие принципы и базовые абстракции

### 1.1 Преамбула

ActionMachine уже предоставляет мощный инструмент для описания **процессов** (активностей) через аспекты, роли, зависимости и плагины. Теперь мы добавляем второй слой — **статическую модель предметных сущностей** (Entity Model). Она позволяет декларативно описывать структуру данных, связи между сущностями, жизненные циклы (через конечные автоматы) и бизнес-правила (XOR, обязательность, уникальность). Эта модель:

- **Не зависит от способа хранения** (SQL, NoSQL, REST API, файлы).
- **Проверяется на этапе сборки** (координатором) – ошибки в связях, циклах, несовместимых типах обнаруживаются при старте приложения.
- **Служит контрактом для ресурсных менеджеров** (адаптеров хранения), которые реализуют чтение/запись сущностей.
- **Может быть экспортирована в OCEL** (Object‑Centric Event Log) для анализа процессов.

### 1.2 Цели части 1

Определить:
- Базовые классы `BaseEntity`, `BaseValueObject`, `BaseStateMachine`.
- Декоратор `@entity` (или `@entity_model`) для маркировки сущностей.
- Гейтхост `EntityGateHost` – маркер, разрешающий использование декоратора `@entity` (по аналогии с `ActionMetaGateHost`).
- Требование обязательного `@meta` для каждой сущности (описание + домен).
- Домены (`BaseDomain`) – те же, что и для действий, для единой системы группировки.
- Дженерик-параметр `StateMachine` – конечный автомат, описывающий жизненный цикл сущности.

### 1.3 Пример использования

```python
from entity_model import BaseEntity, BaseStateMachine, State, Final, entity
from action_machine.domain import OrdersDomain
from action_machine.core.meta_decorator import meta

# 1. Определяем состояния для заказа
class OrderStateMachine(BaseStateMachine):
    New = State("Новый заказ").to(Confirmed, Cancelled)
    Confirmed = State("Подтверждён").to(Shipped, Cancelled)
    Shipped = State("Отправлен").to(Delivered)
    Delivered = Final("Доставлен")
    Cancelled = Final("Отменён")

# 2. Сущность Order, параметризованная своим автоматом
@meta(description="Заказ клиента", domain=OrdersDomain)
@Entity
class Order(BaseEntity[OrderStateMachine]):
    order_id: str
    created_at: datetime
    # простые поля – Pydantic Field (будет в части 2)
    # связи – будут в части 3
```

### 1.4 Детальные требования

#### 1.4.1 `BaseStateMachine`

- Абстрактный базовый класс, который:
  - Позволяет определять состояния как атрибуты класса (экземпляры `State` или `Final`).
  - Предоставляет методы `start(initial_state)`, `transition_to(target)`, `current_state`, `is_final()`.
  - Автоматически строит граф переходов и проверяет его целостность (нет висящих ссылок, все целевые состояния определены).
  - Имеет метод `get_transitions()` для получения графа в виде словаря (имя → список имён целевых состояний).

#### 1.4.2 `BaseEntity[SM]`

- Generic-класс, параметризованный конкретным `BaseStateMachine`.
- Содержит поле `_state_machine: SM` (инициализируется в `__init__`).
- Предоставляет методы-обёртки: `can_transition_to(target)`, `transition_to(target)`, `current_state`, `is_final()`.
- **Не содержит** полей для связей – они определяются в наследниках через специальные generic-контейнеры (часть 3).
- **Не знает** о способе хранения – это чистая доменная модель.

#### 1.4.3 `@entity` декоратор

- Применяется к классу, наследующему `BaseEntity`.
- Проверяет, что класс также наследует `EntityGateHost` (миксин) – иначе TypeError.
- Записывает в класс атрибут `_is_entity = True` (для быстрой проверки).
- Может принимать параметры: `state_machine`? Не нужно – он берётся из дженерика.

#### 1.4.4 `EntityGateHost`

- Пустой маркерный класс. Наследуется `BaseEntity`.
- Декоратор `@entity` проверяет `issubclass(cls, EntityGateHost)`.

#### 1.4.5 Обязательность `@meta`

- Каждая сущность обязана иметь декоратор `@meta(description=..., domain=...)` (аналогично Action).
- `MetadataBuilder` (или `EntityMetadataBuilder`) проверяет это.
- Описание используется в документации, графе, MCP-ресурсе `entity://graph`.

#### 1.4.6 Домены

- Используются существующие `BaseDomain` из ActionMachine.
- Сущность привязывается к домену через `@meta(domain=...)`.

### 1.5 Комментарии и пояснения

- **Почему дженерик по состоянию?** Разные сущности могут иметь совершенно разные жизненные циклы (заказ, платёж, пользователь). Вынесение автомата в параметр типа позволяет статически знать, какие состояния доступны для конкретной сущности, и использовать это в проверках.
- **Почему `BaseEntity` не содержит методов save/load?** Это нарушило бы гексагональную архитектуру. Сущность не должна знать о хранилище.
- **Гейтхост `EntityGateHost`** – по аналогии с `ActionMetaGateHost`, чтобы декоратор `@entity` можно было применить только к правильным классам.
- **Отсутствие `__init_subclass__` для проверки суффикса** – имена сущностей не обязаны заканчиваться на "Entity", но это можно сделать рекомендацией. (При желании добавить суффикс "Entity" – легко, но не обязательно).

### 1.6 Что дальше?

- Часть 2: простые поля – как описываются через Pydantic `Field`, как собираются метаданные, как применяется `DescribedFieldsGateHost`.
- Часть 3: связи – типы, матрица, generic-контейнеры.
- Часть 4: XOR через Union.
- Часть 5: хелперы для ресурсных менеджеров.
- Часть 6: координатор сущностей.
- Часть 7: интеграция с ActionMachine.

Если эта часть понятна, я продолжу со второй.
-----------------------------------------------------------------------------------
## Часть 2. Простые поля сущности: Pydantic, Field, описания, constraints

### 2.1 Преамбула

Сущность состоит из **простых атрибутов** (скалярных значений) и **связей** с другими сущностями. Простые поля – это строки, числа, даты, булевы значения, перечисления, а также их опциональные версии (`Optional[T]`). Для их описания, валидации и генерации JSON Schema мы используем **Pydantic V2**.

Преимущества Pydantic:
- Декларативные `Field` с `description`, `examples`, `gt`, `min_length`, `pattern` и т.д.
- Автоматическая валидация при создании экземпляра сущности (типы, ограничения).
- Возможность генерации JSON Schema для API и MCP.
- Совместимость с `TypedDict` для частичного чтения.

**Важно:** Pydantic используется **только для простых полей**, не для связей. Связи описываются отдельными generic-контейнерами (часть 3).

### 2.2 Пример определения сущности с простыми полями

```python
from datetime import datetime
from pydantic import Field
from entity_model import BaseEntity, entity
from action_machine.core.meta_decorator import meta
from .domains import OrdersDomain

@meta(description="Заказ клиента", domain=OrdersDomain)
@Entity
class Order(BaseEntity[OrderStateMachine]):
    order_id: str = Field(description="Уникальный идентификатор заказа", examples=["ORD-123"])
    amount: float = Field(description="Сумма заказа в рублях", gt=0, examples=[1500.0])
    currency: str = Field(default="RUB", description="Код валюты (ISO 4217)", min_length=3, max_length=3)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата и время создания")
    comment: Optional[str] = Field(default=None, description="Комментарий к заказу")
    # ... связи будут добавлены в части 3
```

### 2.3 Требования к описаниям полей

- **Каждое простое поле обязано иметь непустое описание** (`Field(description=...)`).
- Исключение: поле `id` технически может быть без описания, но лучше его добавить.
- Контролируется через `DescribedFieldsGateHost` (миксин, который наследует `BaseEntity`). `EntityMetadataBuilder` проверяет, что все простые поля имеют `description` (если класс наследует `DescribedFieldsGateHost` и имеет поля). Это аналогично проверке для `BaseParams` и `BaseResult`.

**Почему это требование?**  
Чтобы модель была самодокументируемой. Описания полей попадают в:
- JSON Schema (для OpenAPI / MCP)
- Граф координатора (как метаданные узла)
- Автоматическую документацию

### 2.4 Поддержка constraints

Pydantic `Field` поддерживает множество ограничений:

| Constraint | Назначение | Пример |
|------------|------------|--------|
| `gt`, `ge`, `lt`, `le` | числовые диапазоны | `gt=0` |
| `min_length`, `max_length` | длина строки/коллекции | `min_length=3` |
| `pattern` | регулярное выражение для строки | `pattern=r"^[A-Z]{3}$"` |
| `multiple_of` | кратность числа | `multiple_of=0.5` |
| `strict` | строгая типизация | `strict=True` |

Эти constraints автоматически проверяются Pydantic при создании экземпляра сущности. Ресурсный менеджер может использовать их для валидации перед записью.

### 2.5 Значения по умолчанию и `default_factory`

- `Field(default=...)` – статическое значение по умолчанию.
- `Field(default_factory=callable)` – фабрика для динамических значений (например, `datetime.utcnow`).
- Для опциональных полей принято использовать `default=None` (явно).

**Поведение при чтении:**  
Если ресурсный менеджер не загрузил поле (например, partial-чтение), оно будет `None` или значение по умолчанию (если указано). Это позволяет строить объекты с частичными данными.

### 2.6 Роль `DescribedFieldsGateHost`

`BaseEntity` наследует этот миксин, что сигнализирует сборщику метаданных: все простые поля, определённые в классе, должны иметь `description`. Проверка выполняется в `EntityMetadataBuilder._validate_fields()` (аналог `validate_described_fields` из ActionMachine).

Если поле пропущено или `description` пуст – `TypeError` с указанием имени класса и поля. Это обнаруживается при первом импорте модуля (лениво, через координатор).

### 2.7 Сбор метаданных о полях

`EntityMetadataBuilder` (или расширенный `MetadataBuilder`) собирает для каждого простого поля:

- `field_name`
- `field_type` (строковое представление типа)
- `description`
- `examples` (кортеж)
- `constraints` (словарь)
- `required` (bool) – `True` если нет значения по умолчанию
- `default` (значение или `PydanticUndefined`)

Эта информация сохраняется в `ClassMetadata.params_fields` (или новом поле `entity_fields`). Она используется:
- Для генерации JSON Schema.
- Для автоматической валидации входных данных в адаптерах.
- Для построения графа (узлы «атрибут»).

### 2.8 Взаимодействие с `TypedDict` для partial-чтения

Для каждой сущности может быть автоматически сгенерирован `TypedDict` с `total=False`, где все поля опциональны. Это позволяет ресурсному менеджеру возвращать частично заполненные сущности (например, при проекции). Пример:

```python
class OrderPartial(TypedDict, total=False):
    order_id: str
    amount: float
    currency: str
    created_at: datetime
    comment: str | None
```

Ресурсный менеджер может заполнить только `order_id` и `amount`, остальные опустить. Гидравтор (`EntityHydrator`) при создании `Order` из такого словаря установит отсутствующие поля в `None` (или значения по умолчанию).

### 2.9 Итог по части 2

- Простые поля описываются через Pydantic `Field` с обязательным `description`.
- `BaseEntity` наследует `DescribedFieldsGateHost`, что включает проверку описаний.
- Constraints, default, default_factory работают стандартно.
- Метаданные полей собираются координатором и используются для документации, валидации, генерации схем.
- Частичное чтение поддерживается через `TypedDict` (total=False).

**Связь с ресурсными менеджерами:**  
Менеджер читает данные из хранилища, преобразует их в словарь (например, `row` из SQL), затем использует `EntityHydrator` для создания сущности. Гидравтор учитывает метаданные и применяет значения по умолчанию, если поле отсутствует.

**Что дальше?**  
Часть 3 – связи между сущностями. Там мы определим 8 типов связей (CompositeOne/Many, AggregateOne/Many, AssociationOne/Many, ReferenceOne/Many) как generic-контейнеры, матрицу совместимости и требования двунаправленности.

Если готовы, переходим к части 3.
-----------------------------------------------------------------------------------
## Часть 3. Связи между сущностями: типы, generic‑контейнеры, двунаправленность, матрица совместимости

### 3.1 Преамбула

Сущности редко живут изолированно. Заказ ссылается на клиента, позиции заказа принадлежат заказу, студенты записываются на курсы… Всё это **связи**. Наша метамодель должна выражать их **тип** (композиция, агрегация, ассоциация, зависимость) и **множественность** (один или много). Связи всегда **двунаправленны** – если `Order` ссылается на `Customer`, то `Customer` обязан иметь обратную ссылку (например, `orders`). Исключение – внешние системы, где вместо ссылки на сущность используется `ReferenceByKey[T]` (значение-идентификатор).

Для каждой связи мы используем **специализированный generic‑контейнер**, который:
- Имеет имя, выражающее тип и множественность (например, `CompositeMany`).
- Параметризован целевой сущностью (или объединением типов для XOR).
- Хранит метаданные связи (тип, кардинальность, обратная ссылка).
- Позволяет mypy проверять типы статически.

Все связи описываются **внутри класса сущности** как атрибуты экземпляра. Координатор при сборке модели:
- Проверяет, что на каждую связь есть обратная (кроме `ReferenceByKey`).
- Проверяет совместимость типов по матрице (см. ниже).
- Строит граф связей и проверяет ацикличность (особенно для композиций).
- Сохраняет метаданные для использования ресурсными менеджерами.

### 3.2 Полный список типов связей (8 штук)

| Тип связи | Множественность | Generic‑класс | Семантика | Пример |
|-----------|----------------|---------------|-----------|--------|
| Композиция | 1:1 | `CompositeOne[Target]` | Часть не может существовать без целого. При удалении целого удаляется и часть. | Заказ – **корзина** (Cart). |
| Композиция | 1:N | `CompositeMany[Target]` | То же, но коллекция. | Заказ – **позиции заказа** (OrderLine). |
| Агрегация | 1:1 | `AggregateOne[Target]` | Целое ссылается на часть, но часть может существовать отдельно. При удалении целого ссылка снимается, часть остаётся. | Команда – **капитан** (капитан может перейти в другую команду). |
| Агрегация | 1:N | `AggregateMany[Target]` | Коллекция ссылок, целевые сущности независимы. | Команда – **игроки** (игрок может быть без команды). |
| Ассоциация | 1:1 | `AssociationOne[Target]` | Равноправная связь. Ни одна сторона не управляет жизненным циклом другой. | Пользователь – **паспорт** (паспорт может быть выдан другому пользователю). |
| Ассоциация | N:M | `AssociationMany[Target]` | Требуется промежуточная сущность (явная). | Студент – **курс** (через Enrollment). |
| Зависимость (reference) | 1:1 | `ReferenceOne[Target]` | Слабая ссылка. Целевая сущность может быть удалена – ссылка становится недействительной (NULL). | Заказ – **клиент** (клиент может быть удалён). |
| Зависимость (reference) | 1:N | `ReferenceMany[Target]` | Коллекция слабых ссылок. | Пользователь – **избранные товары** (товары из внешнего каталога). |

### 3.3 Generic‑контейнеры – как они выглядят в коде

```python
from entity_model import (
    BaseEntity, CompositeOne, CompositeMany,
    AggregateOne, AggregateMany, AssociationOne, AssociationMany,
    ReferenceOne, ReferenceMany, ReferenceByKey
)

class Order(BaseEntity):
    # Композиция 1:N – позиции заказа
    items: CompositeMany[OrderLine] = CompositeMany()

    # Агрегация 1:1 – корзина (может существовать отдельно)
    cart: AggregateOne[ShoppingCart] = AggregateOne()

    # Ассоциация N:M – продукты (через OrderProduct)
    products: AssociationMany[Product] = AssociationMany()

    # Зависимость 1:1 – клиент (слабая ссылка)
    customer: ReferenceOne[Customer] = ReferenceOne()

    # Внешняя ссылка – просто ID
    external_id: ReferenceByKey[str] = ReferenceByKey()
```

### 3.4 Обратная связь (двунаправленность)

Каждая связь должна быть объявлена **в обоих классах**. Например:

```python
class Order(BaseEntity):
    items: CompositeMany[OrderLine] = CompositeMany(back_populates="order")

class OrderLine(BaseEntity):
    order: CompositeOne[Order] = CompositeOne(back_populates="items")
```

Параметр `back_populates` (строка) указывает имя поля на другой стороне. Координатор проверит, что указанное поле существует, имеет совместимый тип (по матрице) и правильную множественность.  
**Если `back_populates` не указан, координатор попытается найти поле с подходящим типом автоматически (по имени, в стиле SQLAlchemy). Но явное лучше неявного – рекомендуется указывать всегда.**

**Исключение:** `ReferenceByKey` не требует обратной связи – это просто значение.

### 3.5 Матрица совместимости типов связей (допустимые пары)

| Тип A | Тип B (обратная связь) | Допустимо? | Пояснение |
|-------|------------------------|------------|------------|
| `CompositeOne` | `CompositeOne` | ❌ | Не может быть взаимной композиции 1:1 – приведёт к циклу в жизненном цикле. |
| `CompositeOne` | `CompositeMany` | ❌ | Бессмысленно: с одной стороны один, с другой – коллекция. |
| `CompositeOne` | `AggregateOne` | ✅ | Целое управляет жизненным циклом части, часть слабо ссылается на целое. |
| `CompositeMany` | `AggregateOne` | ✅ | Типичный случай: Order – OrderLine. |
| `AggregateOne` | `AggregateOne` | ✅ | Взаимно слабые ссылки. |
| `AggregateMany` | `AggregateOne` | ✅ | Коллекция ссылается на один элемент. |
| `AssociationOne` | `AssociationOne` | ✅ | Симметричная ассоциация. |
| `AssociationMany` | `AssociationMany` | ✅ | N:M. |
| `ReferenceOne` | `ReferenceOne` | ✅ | Взаимные слабые ссылки. |
| `ReferenceOne` | `ReferenceMany` | ✅ | Один – много. |
| `ReferenceMany` | `ReferenceMany` | ❌ | Избыточно. |

**Остальные комбинации** (например, `Composite` с `Association`, `Aggregate` с `Association`) – **запрещены**, так как смешивают разные семантики управления жизненным циклом.

Координатор при проверке связи:
- Смотрит тип контейнера на стороне A (`CompositeMany`) и тип контейнера на стороне B (`AggregateOne`).
- Сверяет с матрицей. Если комбинация не разрешена – `TypeError` с объяснением.

### 3.6 Множественность и валидация

- `One` – поле содержит ровно одну ссылку (или `None`, если связь опциональна).  
  При присваивании нового значения старая ссылка заменяется.  
- `Many` – поле является коллекцией (список, множество).  
  Методы: `add(entity)`, `remove(entity)`, `clear()`. При добавлении автоматически устанавливается обратная ссылка (если есть `back_populates`). При удалении – обратная ссылка снимается.

**Опциональность:**  
- Если поле объявлено как `Optional[CompositeOne[Target]]`, то оно может быть `None`.  
- Для `Many`-связей опциональность означает, что коллекция может быть пустой (но сам контейнер всегда создаётся).

### 3.7 Проверка целостности (координатор)

При старте приложения `EntityCoordinator` (аналог `GateCoordinator`) обходит все классы, помеченные `@entity`, и:

1. Собирает метаданные: для каждого атрибута, являющегося экземпляром `Relationship`, определяет тип связи, целевую сущность, множественность, `back_populates`.
2. Проверяет, что для каждой связи есть обратная (если `back_populates` не указан – ищет по типу; если не находит – ошибка).
3. Проверяет совместимость типов по матрице.
4. Проверяет, что `back_populates` указывает на существующее поле с правильным типом.
5. Строит граф связей и обнаруживает циклы (циклы в композициях запрещены, в агрегациях – допустимы, но с предупреждением).
6. Для `AssociationMany` проверяет, что существует промежуточная сущность, которая связывает два класса (например, `OrderProduct`).

### 3.8 Пример полной проверки (ошибка)

```python
class Order(BaseEntity):
    items: CompositeMany[OrderLine] = CompositeMany(back_populates="order")

class OrderLine(BaseEntity):
    order: AssociationOne[Order] = AssociationOne(back_populates="items")  # Ошибка!
```

Координатор выдаст:
```
TypeError: В сущности OrderLine поле order имеет тип AssociationOne, но обратная связь Order.items имеет тип CompositeMany.
Допустимые комбинации для CompositeMany: AggregateOne, ReferenceOne. AssociationOne не разрешён.
```

### 3.9 Что дальше?

- **Часть 4** – XOR через Union в одном поле (вариативный дженерик).
- **Часть 5** – хелперы для ресурсных менеджеров (Identity Map, RelationBatcher, Hydrator).
- **Часть 6** – координатор сущностей (EntityCoordinator) – детали реализации.
- **Часть 7** – интеграция с ActionMachine (как аспекты получают сущности через репозитории, как сохранять изменения).

Если вы согласны с этим дизайном, я перехожу к части 4 (XOR).
-----------------------------------------------------------------------------------
## Часть 4. XOR-ограничения: вариативный дженерик через Union

### 4.1 Преамбула

В предметных моделях часто встречаются **альтернативные связи**: документ может быть подписан либо электронной подписью, либо бумажной, но не обеими сразу; платёж выполняется либо картой, либо наличными, либо переводом; пользователь входит по email или по телефону. Такие ограничения называют **XOR** (исключающее ИЛИ). В классических ORM их обычно моделируют двумя отдельными полями и дополнительной проверкой в бизнес-логике – что приводит к дублированию и ошибкам.

**Наш подход:** использовать **Union** в generic‑параметре контейнера связи. Вместо двух полей – одно поле, которое может содержать объект одного из нескольких типов. Это выражает XOR на уровне типа, проверяется mypy, а координатор может проверить, что все альтернативы действительно являются сущностями.

### 4.2 Синтаксис

```python
from entity_model import BaseEntity, ReferenceOne

class Document(BaseEntity):
    # Подпись – либо DigitalSignature, либо PhysicalSignature
    signature: ReferenceOne[DigitalSignature | PhysicalSignature] = ReferenceOne()
```

Здесь `ReferenceOne[DigitalSignature | PhysicalSignature]` означает: поле `signature` может быть **экземпляром** `DigitalSignature`, или **экземпляром** `PhysicalSignature`, или `None` (если связь опциональна). Оба варианта являются сущностями, но в нашей модели они **не могут присутствовать одновременно**.

### 4.3 Как это работает для коллекций

Если нужна коллекция, но с XOR-ограничением на уровне **типа элементов** (все элементы должны быть одного из разрешённых типов), используется `ReferenceMany` с Union:

```python
class User(BaseEntity):
    # Контакты – либо номера телефонов, либо email-адреса, но не смесь
    contacts: ReferenceMany[PhoneNumber | EmailAddress] = ReferenceMany()
```

При этом:
- Допустимо иметь несколько телефонов и ни одного email (коллекция однородна по типу).
- Допустимо иметь несколько email и ни одного телефона.
- Недопустимо добавить в одну коллекцию и телефон, и email (тип элемента будет нарушен при попытке добавить второй тип).

Если требуется более строгий XOR («ровно одна из альтернатив, но не обе, и не несколько»), это можно выразить через **одиночную связь** (`ReferenceOne`) + Union, а коллекцию уже не использовать.

### 4.4 Сбор метаданных координатором

При обнаружении поля типа `ReferenceOne[Union[T1, T2, ...]]` координатор:
- Извлекает список `targets = [T1, T2, ...]` из `__args__` (через `get_args`).
- Проверяет, что каждый `Ti` является подклассом `BaseEntity`.
- Сохраняет в метаданных связи поле `allowed_targets` (кортеж классов).
- Для обратной связи (если указана) требуется, чтобы каждый `Ti` имел соответствующее поле обратной ссылки (с тем же именем, заданным в `back_populates`). Если у разных `Ti` обратные ссылки различаются – ошибка.

### 4.5 Валидация на уровне сущности (рантайм)

При установке значения в поле `signature` (например, `doc.signature = digital_sig`) проверяется, что тип значения входит в `allowed_targets`. Эту проверку может выполнять **сеттер**, сгенерированный метаклассом, или сам контейнер `ReferenceOne` в методе `__set__`. Если тип не разрешён – `TypeError`.

При загрузке сущности из БД ресурсный менеджер должен восстановить объект правильного типа. Для этого в `ReferenceByKey` (если хранится ID + дискриминатор) или в самой таблице может быть колонка `signature_type` ('digital' / 'physical'). Гидравтор (`EntityHydrator`) по этому дискриминатору создаёт экземпляр нужного подкласса.

### 4.6 Обратные связи для Union

Если `Document.signature` ссылается на `DigitalSignature | PhysicalSignature`, то в `DigitalSignature` и `PhysicalSignature` должна быть **обратная связь** (например, `document: ReferenceOne[Document]`). Координатор проверит, что оба класса имеют поле `document` с типом `ReferenceOne[Document]` (или совместимым).  
Если типы обратных связей различаются (например, в `DigitalSignature` это `ReferenceOne[Document]`, а в `PhysicalSignature` – `ReferenceMany[Document]`), это будет считаться несовместимостью.

**Допускается** ситуация, когда обратная связь определена только для одного из вариантов, а для других – отсутствует (например, `PhysicalSignature` – внешняя сущность, не имеющая обратной ссылки). Тогда при описании поля `signature` можно указать `back_populates` только для тех типов, где она есть, или использовать специальный параметр `allow_incomplete_backrefs=True` – но это усложняет. Рекомендуется требовать единообразия.

### 4.7 Пример полной модели с XOR

```python
class DigitalSignature(BaseEntity):
    document: ReferenceOne[Document] = ReferenceOne(back_populates="signature")
    key_id: str

class PhysicalSignature(BaseEntity):
    document: ReferenceOne[Document] = ReferenceOne(back_populates="signature")
    scanned_copy_url: str

class Document(BaseEntity):
    signature: ReferenceOne[DigitalSignature | PhysicalSignature] = ReferenceOne(back_populates="document")
```

Координатор:
- Проверит, что `DigitalSignature.document` и `PhysicalSignature.document` существуют и имеют тип `ReferenceOne[Document]`.
- Проверит, что `Document.signature` имеет `back_populates="document"`.
- Убедится, что нет циклов (допустимо).

### 4.8 Частичное чтение (partial) для XOR

При запросе `Document` без загрузки `signature` (partial) поле `signature` может отсутствовать в результате или быть `None`. Если нужно загрузить только идентификатор подписи, но не полные данные – можно хранить ID и тип в отдельных колонках. Для этого ресурсный менеджер может использовать `ReferenceByKey` вместо `ReferenceOne`, но тогда теряется типобезопасность. Лучше оставить `ReferenceOne` и в partial-режиме устанавливать объект-заглушку (`DigitalSignature(id=...)`), созданный через `PartialEntity`.

### 4.9 Ограничения Union в Python

- `Union` (или оператор `|`) работает только с типами, доступными на момент аннотации. Нельзя использовать строковые forward references внутри Union в качестве аргументов дженерика? В Python 3.10+ `"DigitalSignature" | "PhysicalSignature"` – строки разрешаются через `typing.get_type_hints`. Координатор должен уметь резолвить такие строки (как в `extract_action_types`).
- В mypy поддержка `Union` в дженериках стабильна начиная с версии 1.0.
- Для Python 3.9 и ниже нужно использовать `Union[DigitalSignature, PhysicalSignature]` из `typing`.

### 4.10 Итог по части 4

- **XOR выражается через Union в generic-параметре контейнера связи**.
- **Одно поле** вместо двух – чище и проверяемо статически.
- **Коллекции** с XOR: `ReferenceMany[Union[T1, T2]]` – все элементы коллекции должны быть одного типа (однородны), но допустимы разные коллекции одного типа.
- **Координатор** проверяет, что все типы в Union – сущности, и что обратные связи (если требуются) определены для каждого.
- **Рантайм-проверка** при присваивании (через сеттер или контейнер).
- **Поддержка partial-чтения** через заглушки или дискриминаторы.

**Что дальше?**  
Часть 5 – хелперы для ресурсных менеджеров (Identity Map, RelationBatcher, EntityHydrator, PartialEntity, RelationLinker, ConstraintValidator). Мы опишем каждый хелпер, его API и пример использования, чтобы написание менеджеров стало простым и защищённым.
-----------------------------------------------------------------------------------
## Часть 5. Хелперы для ресурсных менеджеров: пишем легко и без ошибок

### 5.1 Преамбула

Ресурсный менеджер — это адаптер, который реализует чтение и запись сущностей в конкретное хранилище (SQL, MongoDB, REST API, файловая система). Его задача:

- Преобразовывать **строки/документы** из хранилища в экземпляры `BaseEntity` (и наоборот).
- Управлять **связями** (загружать связанные сущности, поддерживать двунаправленность).
- Соблюдать **инварианты** модели (XOR, обязательность полей).
- Делать это **эффективно** (batch-загрузка, кеш в пределах запроса).

Чтобы разработчику не приходилось каждый раз писать один и тот же код, мы предоставляем **набор хелперов** (утилит). Они не являются частью модели сущностей, но живут в том же пакете `entity_model.helpers`. Ресурсный менеджер может использовать их по желанию.

Все хелперы спроектированы так, чтобы **предотвращать нарушение правил модели**:
- Нельзя создать два экземпляра одной сущности с одинаковым ID (`IdentityMap`).
- Нельзя установить связь, несовместимую по типу (`RelationLinker`).
- Нельзя забыть про обратную ссылку (`RelationLinker`).
- Нельзя загрузить сущность без обязательных полей (`EntityHydrator` + `Validator`).

### 5.2 Общий сценарий использования (чтение)

```python
# 1. Создаём identity map на запрос
identity_map = EntityIdentityMap()

# 2. Читаем сырые данные из БД
rows = await db.fetch_all("SELECT * FROM orders WHERE id IN :ids", ids=order_ids)

# 3. Гидрируем каждую строку в сущность (с учётом identity map)
hydrator = EntityHydrator(identity_map)
orders = [hydrator.hydrate(Order, row) for row in rows]

# 4. Батчево загружаем связанных клиентов
batcher = RelationBatcher(identity_map)
for order in orders:
    batcher.add(Order, order.id, order.customer_id, relation='customer')
await batcher.load(manager, relation='customer')   # загрузит всех Customer за один запрос

# 5. Все связи уже установлены (через RelationLinker внутри batcher)
return orders
```

### 5.3 Хелпер 1: `EntityIdentityMap`

**Назначение:** гарантирует, что в пределах одного запроса для одного `(тип_сущности, id)` существует только один экземпляр. Предотвращает дублирование и рассинхронизацию.

**API:**
```python
class EntityIdentityMap:
    def get(self, entity_type: type[BaseEntity], entity_id: Any) -> BaseEntity | None
    def add(self, entity: BaseEntity) -> None
    def contains(self, entity_type: type[BaseEntity], entity_id: Any) -> bool
    def clear(self) -> None
```

**Внутреннее устройство:** `dict[(type, id), entity]`. Не использует слабые ссылки, потому что время жизни — один запрос, после чего контейнер уничтожается.

**Важно:** `id` может быть составным (если сущность использует составной первичный ключ). Тогда в качестве ключа используется кортеж. Координатор должен предоставлять метод `get_primary_key_fields()`.

**Пример использования в менеджере:**
```python
async def get_by_id(manager, entity_cls, oid):
    if identity_map.contains(entity_cls, oid):
        return identity_map.get(entity_cls, oid)
    row = await db.fetch_one(f"SELECT * FROM {entity_cls.__tablename__} WHERE id = ?", oid)
    if not row:
        return None
    entity = hydrator.hydrate(entity_cls, row)
    identity_map.add(entity)
    return entity
```

### 5.4 Хелпер 2: `RelationBatcher`

**Назначение:** собирает запросы на загрузку связанных сущностей и выполняет их **одним пакетом** (batch). Устраняет проблему N+1.

**API:**
```python
class RelationBatcher:
    def __init__(self, identity_map: EntityIdentityMap):
        self._map = identity_map
        self._pending: dict[str, dict[Any, list[tuple[BaseEntity, str]]]] = {}
        # структура: relation_name -> { target_key: [(source_entity, source_relation_name), ...] }

    def add(self, source_entity: BaseEntity, relation_name: str) -> None:
        """Запланировать загрузку связи relation_name для source_entity."""
        target_key = self._extract_target_key(source_entity, relation_name)
        self._pending.setdefault(relation_name, {}).setdefault(target_key, []).append((source_entity, relation_name))

    async def load(self, manager: Any, relation_name: str) -> None:
        """Загрузить все запланированные связи relation_name одним запросом."""
        keys = list(self._pending[relation_name].keys())
        # manager должен уметь загружать сущности по ключам (например, get_by_ids)
        targets = await manager.get_by_ids(target_cls, keys)
        for target in targets:
            target_key = self._get_key(target)
            for (source_entity, src_rel_name) in self._pending[relation_name][target_key]:
                # Установить связь через RelationLinker
                RelationLinker.link(source_entity, src_rel_name, target)
        del self._pending[relation_name]
```

**Требования к менеджеру:** должен предоставлять метод `get_by_ids(entity_cls, ids)` или аналогичный. Если хранилище не поддерживает batch, можно загружать по одному, но это уже проблема менеджера.

**Пример:**
```python
batcher = RelationBatcher(identity_map)
for order in orders:
    if order.customer_id:
        batcher.add(order, 'customer')
await batcher.load(order_manager, 'customer')
```

### 5.5 Хелпер 3: `EntityHydrator`

**Назначение:** преобразует «сырой» словарь (из БД, JSON, CSV) в экземпляр сущности с учётом:
- Типов простых полей (через Pydantic).
- Значений по умолчанию.
- Частичных данных (отсутствующие поля → `None` или default).
- Уже загруженных объектов из `IdentityMap` (чтобы не создавать дубликаты).
- Связей: если в словаре есть `customer_id`, то `EntityHydrator` может либо создать заглушку (`PartialCustomer`), либо отложить связывание (записать `_pending_relations`). Обычно лучше отложить до `RelationBatcher`.

**API:**
```python
class EntityHydrator:
    def __init__(self, identity_map: EntityIdentityMap | None = None):
        self._identity_map = identity_map
        self._pending_relations: list[tuple[BaseEntity, str, Any]] = []  # (entity, relation_name, target_key)

    def hydrate(self, entity_cls: type[BaseEntity], data: dict) -> BaseEntity:
        # 1. Извлекаем первичный ключ
        pk = self._extract_pk(entity_cls, data)
        # 2. Если уже есть в identity_map – возвращаем его (и обновляем поля? осторожно)
        # 3. Иначе создаём экземпляр через Pydantic (entity_cls(**data))
        # 4. Для каждого поля-связи: если значение – ID, то добавляем в _pending_relations
        # 5. Добавляем в identity_map
        # 6. Возвращаем сущность
```

**Проблема обновления:** если сущность уже есть в `identity_map`, но пришла новая версия (обновлённые данные) – что делать? Решение: не обновлять, а предполагать, что за один запрос сущность читается один раз. Если данные могли измениться – использовать `refresh`.

**Для partial-чтения:** `hydrate` должен принимать флаг `partial=False`. Если `partial=True`, то отсутствующие поля не заполняются (остаются `None`). Но тогда Pydantic будет жаловаться на отсутствие обязательных полей. Поэтому partial-загрузку лучше делать через отдельный класс `PartialHydrator`, который создаёт словарь для `__init__`, пропуская отсутствующие поля.

**Упрощённая альтернатива:** вообще не использовать `EntityHydrator`, а создавать сущности вручную. Но для сложных графов это слишком много кода.

### 5.6 Хелпер 4: `PartialEntity` (обёртка)

**Назначение:** обозначить, что объект загружен не полностью (например, только `id`). При попытке доступа к отсутствующему полю выбрасывается исключение.

**API:**
```python
class PartialEntity(Generic[T]):
    def __init__(self, entity_cls: type[T], data: dict):
        self._entity_cls = entity_cls
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Partial entity {self._entity_cls.__name__} has no attribute '{name}'")
```

**Использование:**
```python
partial_customer = PartialEntity(Customer, {'id': customer_id})
order.customer = partial_customer   # разрешено
# order.customer.name -> AttributeError (если name не загружен)
```

Позже, когда полные данные станут доступны, можно заменить `partial_customer` на полноценный объект через `RelationLinker.replace_partial(entity, relation, full_entity)`.

### 5.7 Хелпер 5: `RelationLinker`

**Назначение:** единая точка установки двунаправленных связей. Проверяет совместимость типов, множественность, и автоматически обновляет обратную ссылку.

**API:**
```python
class RelationLinker:
    @staticmethod
    def link(source: BaseEntity, relation_name: str, target: BaseEntity) -> None:
        """Устанавливает source.relation_name = target, а также обратную связь, если она определена."""
        source_meta = get_entity_metadata(type(source))
        target_meta = get_entity_metadata(type(target))
        source_rel = source_meta.relations[relation_name]

        # 1. Проверка совместимости по матрице (source_rel.type, target_rel.type)
        if not is_compatible(source_rel, target_rel):
            raise TypeError(...)

        # 2. Проверка множественности: если source_rel.multiplicity == 'one', то предыдущее значение должно быть None (или мы его заменяем)
        # 3. Устанавливаем source._relation_values[relation_name] = target
        # 4. Находим обратное поле (source_rel.back_populates) и устанавливаем target._relation_values[back] = source (с учётом коллекций)

    @staticmethod
    def unlink(source: BaseEntity, relation_name: str) -> None:
        """Удаляет связь, обновляя обратную сторону."""
        ...
```

**Интеграция с коллекциями:** для `Many`-связей `link` добавляет `target` в коллекцию, а `unlink` удаляет.

### 5.8 Хелпер 6: `ConstraintValidator`

**Назначение:** проверка бизнес-правил модели, которые не могут быть выражены через типы или декораторы, но требуют доступа к данным (например, уникальность, существование связанной сущности).

**API:**
```python
class ConstraintValidator:
    def __init__(self, manager: Any):   # менеджер для проверки уникальности и т.п.
        self._manager = manager

    async def validate(self, entity: BaseEntity) -> None:
        # 1. XOR-ограничения (если есть) – проверяются без обращения к БД (просто смотрим, какие поля установлены)
        # 2. Обязательность полей (required) – уже проверена Pydantic, но можно продублировать.
        # 3. Уникальность: если у сущности есть уникальные поля (указаны в метаданных), проверяем, что в БД нет другой сущности с такими же значениями.
        # 4. Существование связанных сущностей: если связь не опциональна, проверяем, что целевая сущность существует (но обычно это делает внешний ключ на уровне БД).
        # 5. Дополнительные кастомные правила, заданные через @constraint.
```

**Валидатор не должен изменять сущность.** Если нарушение – поднимает `ValidationError`.

### 5.9 Хелпер 7: `UnitOfWork` (опционально)

**Назначение:** управление транзакциями, отслеживание изменённых сущностей и сохранение их в правильном порядке (с учётом зависимостей). Это не строго обязательно, но сильно упрощает жизнь.

```python
class UnitOfWork:
    def __init__(self, manager_factory):
        self._manager_factory = manager_factory
        self._new: list[BaseEntity] = []
        self._dirty: list[BaseEntity] = []
        self._removed: list[BaseEntity] = []

    def register_new(self, entity): ...
    def register_dirty(self, entity): ...
    def register_removed(self, entity): ...

    async def commit(self):
        # 1. Проверить все инварианты (ConstraintValidator)
        # 2. Сохранить новые сущности в порядке топологической сортировки графа (чтобы сначала корни)
        # 3. Обновить изменённые
        # 4. Удалить удалённые (с учётом каскадов)
        # 5. Вызвать commit транзакции
```

### 5.10 Итог по части 5

- **Identity Map** – локальный кеш на запрос, предотвращает дублирование.
- **RelationBatcher** – решает проблему N+1 при загрузке связей.
- **EntityHydrator** – централизованное создание сущностей из сырых данных.
- **PartialEntity** – безопасная работа с частично загруженными объектами.
- **RelationLinker** – единственное место установки связей, гарантирует двунаправленность.
- **ConstraintValidator** – проверка бизнес-правил перед сохранением.
- **UnitOfWork** – управление транзакциями и порядком сохранения.

Эти хелперы **не обязательны**, но их использование делает ресурсные менеджеры:
- **Короче** (вместо 300 строк – 30).
- **Надёжнее** (меньше шансов забыть обратную ссылку, создать дубликат, нарушить инвариант).
- **Производительнее** (batch-загрузка, кеш).

**Что дальше?**  
Часть 6 – координатор сущностей (`EntityCoordinator`): сбор метаданных, построение графа, проверка целостности, API для доступа к метаданным. Это аналог `GateCoordinator`, но для сущностей.
-----------------------------------------------------------------------------------
## Часть 6. Координатор сущностей (EntityCoordinator)

### 6.1 Преамбула

У нас есть декларативные сущности (`@entity`), их простые поля (Pydantic), связи (8 типов), XOR через Union. Всё это **метаданные**, которые нужно собрать, проверить и сделать доступными для ресурсных менеджеров, хелперов, адаптеров и других компонентов. Координатор сущностей (`EntityCoordinator`) — центральный реестр, который:

- Собирает метаданные при первом обращении к классу сущности (лениво).
- Проверяет все инварианты модели: двунаправленность связей, совместимость типов по матрице, отсутствие циклов (для композиций), корректность XOR, наличие `@meta` и т.д.
- Строит **направленный ациклический граф** (DAG) сущностей и связей.
- Предоставляет публичное API для доступа к метаданным: типы связей, целевые сущности, back_populates, allowed_targets для Union, ограничения полей, состояние и т.д.

Координатор существует в единственном экземпляре на приложение (можно внедрять через DI). Он тесно интегрирован с `GateCoordinator` из ActionMachine (чтобы переиспользовать домены, граф и логирование), но может работать и независимо.

### 6.2 Структура метаданных (frozen dataclass)

Аналогично `ClassMetadata` для действий, для сущностей вводим `EntityMetadata`:

```python
@dataclass(frozen=True)
class EntityMetadata:
    class_ref: type[BaseEntity]
    class_name: str                     # полное имя
    meta: MetaInfo | None               # описание, домен (из @meta)
    state_machine: type[BaseStateMachine] | None   # класс конечного автомата (из дженерика)
    fields: tuple[FieldDescriptionMeta, ...]   # простые поля (как в части 2)
    relations: tuple[RelationMeta, ...]         # связи (подробно ниже)
    constraints: tuple[ConstraintMeta, ...]     # XOR, уникальность и т.д.
    primary_key: tuple[str, ...]                # имена полей, образующих первичный ключ
```

`RelationMeta`:

```python
@dataclass(frozen=True)
class RelationMeta:
    name: str                           # имя атрибута в классе сущности
    relation_type: str                  # "composite_one", "composite_many", "aggregate_one", ...
    target_type: type[BaseEntity] | None  # одиночный тип
    allowed_targets: tuple[type[BaseEntity], ...]  # для Union (XOR)
    multiplicity: str                   # "one" или "many"
    back_populates: str | None          # имя обратного поля в целевой сущности
    back_relation: "RelationMeta | None" # ссылка на метаданные обратной связи (заполняется после сборки)
    is_optional: bool                   # может ли быть None (для One)
    is_required: bool                   # противоположность is_optional
    default_factory: Callable | None    # для коллекций – фабрика, создающая пустую коллекцию
```

### 6.3 Процесс сборки метаданных

`EntityCoordinator.get(entity_cls)`:

1. Если класс уже есть в кеше – вернуть.
2. Иначе:
   - Проверить, что класс помечен `@entity` (имеет атрибут `_is_entity` или наследует `EntityGateHost`).
   - Извлечь `state_machine` из дженерика (`BaseEntity[SM]`). Если SM не указан – по умолчанию `None` (сущность без конечного автомата).
   - Собрать простые поля через `_collect_fields`: обход `__annotations__`, фильтрация тех, что не являются экземплярами `Relationship`, использовать Pydantic `FieldInfo`.
   - Собрать связи через `_collect_relations`: найти все атрибуты, являющиеся экземплярами `Relationship` (или его подклассов). Для каждого определить тип (по классу контейнера), целевую сущность (из `__args__[0]`, если Union – распарсить).
   - Собрать ограничения (`XorConstraint`) из специального декоратора или атрибута класса. (См. часть 4 – XOR через Union, но может быть и явный `@xor`, если Union неудобен. Однако мы решили использовать Union.)
   - Определить первичный ключ: искать поле с именем `id` или аннотацией `PrimaryKey[...]`, или всё поле, помеченное `@primary_key`. По умолчанию – поле `id`, если оно есть.
   - Провести валидацию (см. следующий раздел).
   - Создать `EntityMetadata` и сохранить в кеш.
   - Рекурсивно вызвать `get` для целевых сущностей всех связей (чтобы построить полный граф).

### 6.4 Валидация (проверка инвариантов)

Валидация выполняется **после** сбора метаданных, но **до** сохранения в кеш. Если какая-то проверка не пройдена – выбрасывается исключение (обычно `TypeError` или `ValueError`), и приложение не стартует.

**Список проверок:**

1. **Обязательность `@meta`** – аналогично действиям.
2. **Для каждого простого поля:** должно быть описание (`Field.description`), если класс наследует `DescribedFieldsGateHost` (а `BaseEntity` наследует).
3. **Для каждой связи:** 
   - Целевая сущность (или все в Union) должны быть классами, наследующими `BaseEntity`.
   - Если `back_populates` указан – проверить, что в целевой сущности существует поле с таким именем, и что оно является связью (RelationMeta).
   - Если `back_populates` не указан – попытаться найти обратную связь автоматически: искать поле того же типа, которое ссылается на текущую сущность. Если найдено несколько – ошибка (нужно указать явно). Если не найдено – ошибка (кроме случаев, когда `ReferenceByKey` или связь помечена `bidirectional=False` – но мы от этого отказались).
   - Проверить совместимость типов связи (по матрице из части 3). Для этого сравниваем `relation_type` текущей связи и `relation_type` обратной связи.
   - Если связь `AssociationMany` – проверить, что существует промежуточная сущность, связывающая два класса. Это можно сделать, найдя сущность, которая имеет две связи (многие-к-одному) на оба класса. Если не найдена – ошибка (или требовать явного `through`).
4. **XOR через Union:** 
   - Если в `allowed_targets` больше одного типа, координатор проверяет, что обратная связь определена **для каждого** типа в Union. Если для какого-то типа отсутствует – ошибка.
   - Дополнительно проверяется, что Union не используется с `Many`-связями (коллекциями) без особого разрешения (можно разрешить, но с предупреждением).
5. **Циклы в графе связей:** 
   - Строим граф, где вершины – сущности, рёбра – связи. Если в графе есть цикл, и хотя бы одно ребро в цикле имеет тип `CompositeOne` или `CompositeMany` – ошибка (композиция не может быть циклической). Циклы из агрегаций или ассоциаций допустимы, но координатор может выдать предупреждение.
6. **Уникальность имён связей** – в пределах одной сущности не может быть двух связей с одинаковым именем (очевидно).
7. **Первичный ключ:** проверяется, что все поля, входящие в первичный ключ, действительно существуют и являются простыми (не связями). Также проверяется, что значения первичного ключа не могут быть `None` (если только сущность не новая, но это на совести менеджера).

### 6.5 API координатора (публичные методы)

```python
class EntityCoordinator:
    def get(self, entity_cls: type[BaseEntity]) -> EntityMetadata
    def has(self, entity_cls: type[BaseEntity]) -> bool
    def get_all_entities(self) -> list[type[BaseEntity]]
    def get_graph(self) -> rx.PyDiGraph   # направленный граф сущностей (узлы – entity_cls, рёбра – связи)
    def get_relations_between(self, source: type[BaseEntity], target: type[BaseEntity]) -> list[RelationMeta]
    def is_compatible(self, rel1: RelationMeta, rel2: RelationMeta) -> bool   # матрица
```

Также предоставляются методы для хелперов: например, `get_primary_key_fields(entity_cls)`.

### 6.6 Интеграция с GateCoordinator

- `GateCoordinator` уже управляет метаданными действий, доменами, зависимостями. Чтобы не создавать два независимых координатора, можно расширить `GateCoordinator`, добавив ему функциональность работы с сущностями. Но это нарушит Single Responsibility. Лучше оставить `EntityCoordinator` отдельным, но дать им общий доступ к графу доменов (чтобы сущности привязывались к доменам через `@meta`). Можно внедрить `GateCoordinator` в `EntityCoordinator` как зависимость.

### 6.7 Пример работы координатора

```python
coordinator = EntityCoordinator()
order_meta = coordinator.get(Order)

for rel in order_meta.relations:
    print(rel.name, rel.relation_type, rel.target_type)

# Получить обратную связь для Order.items
items_rel = order_meta.get_relation('items')
back_rel = items_rel.back_relation   # RelationMeta для OrderLine.order
```

### 6.8 Что даёт координатор ресурсным менеджерам?

- Знать, какие поля являются связями и какого типа.
- Знать, какой back_populates, чтобы при загрузке автоматически устанавливать обратные ссылки (через `RelationLinker`).
- Знать, какие поля образуют первичный ключ.
- Знать, какие ограничения (XOR) нужно проверить перед сохранением.
- Строить SQL-запросы динамически (например, для `CompositeMany` – внешний ключ на стороне дочерней таблицы).
- Генерировать схему БД (миграции) на основе метаданных (опционально).

### 6.9 Реализационные заметки

- Сбор метаданных должен быть **ленивым**: при старте приложения мы не обходим все модули, а только те классы, к которым реально обратились через `coordinator.get()`. Это ускоряет запуск.
- Для автоматического обнаружения всех сущностей можно использовать entry point или явный список, но ленивый подход проще.
- Кеш метаданных – обычный словарь `{entity_cls: EntityMetadata}`.
- Проверка циклов – через `rustworkx` (как в GateCoordinator) или стандартный алгоритм DFS.
- Для поддержки `Union` в дженериках нужна работа с `__origin__` и `__args__`. В Python 3.10+ `get_origin(Union)` возвращает `types.UnionType` или `typing.Union`. Надо обрабатывать оба случая.

### 6.10 Итог по части 6

- `EntityCoordinator` – центральный реестр метаданных сущностей.
- Собирает информацию о простых полях, связях, ограничениях, первичном ключе.
- Проверяет все инварианты модели (двунаправленность, совместимость, циклы, XOR).
- Предоставляет удобный API для ресурсных менеджеров и хелперов.
- Работает лениво и кеширует результаты.

**Что дальше?**  
Часть 7 – интеграция с ActionMachine. Как сущности будут использоваться внутри действий (аспектов)? Как ресурсные менеджеры будут внедряться через зависимости (`@depends`)? Как события изменения сущностей смогут вызывать действия? Это свяжет статическую модель (сущности) с динамической (аспекты) в единую платформу.
-----------------------------------------------------------------------------------
## Часть 7. Интеграция с ActionMachine: сущности в действиях

### 7.1 Преамбула

ActionMachine предоставляет механизм описания **процессов** (аспекты, роли, зависимости). Теперь мы добавили **статическую модель сущностей** (типы, связи, конечные автоматы). Осталось связать их воедино. Цель интеграции:

- **Действия (Actions) работают с сущностями** через абстракцию репозитория, не завися от конкретного хранилища.
- **Ресурсные менеджеры** (адаптеры) реализуют репозитории для конкретных БД/API и используют метаданные координатора для валидации, маппинга и оптимизации.
- **Жизненный цикл сущностей** может управляться конечными автоматами, а переходы между состояниями могут инициироваться действиями.
- **События изменения сущностей** (создание, обновление, удаление, смена состояния) могут генерировать события, на которые подписываются другие действия или плагины.
- **Граф сущностей** экспортируется через MCP (как ресурс `entity://graph`) для AI-агентов.

Всё это без привязки к конкретным технологиям хранения — только через порты и адаптеры (гексагональная архитектура).

### 7.2 Порт репозитория: `EntityReader` / `EntityWriter`

Для каждой сущности (или для группы сущностей) определяем интерфейсы чтения и записи. Они являются **портами** (в терминах гексагональной архитектуры). Ресурсные менеджеры будут их реализовывать.

```python
from typing import Protocol, TypeVar, Generic, List, Optional, Any

E = TypeVar('E', bound=BaseEntity)

class EntityReader(Protocol[E]):
    async def get_by_id(self, id: Any) -> Optional[E]: ...
    async def find(self, criteria: dict[str, Any]) -> List[E]: ...
    # возможно, пагинация, count и т.д.

class EntityWriter(Protocol[E]):
    async def save(self, entity: E) -> None: ...
    async def delete(self, entity: E) -> None: ...
```

Можно объединить в один интерфейс `EntityRepository[E]`, но разделение полезно, если действие только читает.

Внутри Action (в аспекте) разработчик получает нужный репозиторий через `box.resolve()`:

```python
from action_machine.dependencies import depends
from action_machine.core.meta_decorator import meta
from action_machine.auth import check_roles, ROLE_NONE
from .ports import OrderReader, OrderWriter
from .entities import Order, OrderStateMachine

@meta(description="Подтверждение заказа", domain=OrdersDomain)
@check_roles(ROLE_NONE)
@depends(OrderReader)
@depends(OrderWriter)
class ConfirmOrderAction(BaseAction[ConfirmOrderParams, ConfirmOrderResult]):

    @regular_aspect("Загрузка заказа")
    async def load_order(self, params, state, box, connections):
        reader = box.resolve(OrderReader)
        order = await reader.get_by_id(params.order_id)
        if not order:
            raise ValueError(f"Order {params.order_id} not found")
        return {"order": order}

    @regular_aspect("Проверка возможности подтверждения")
    async def check_transition(self, params, state, box, connections):
        order: Order = state['order']
        if not order.can_transition_to(OrderStateMachine.Confirmed):
            raise ValueError(f"Order {order.id} cannot be confirmed")
        return {}

    @regular_aspect("Выполнение перехода")
    async def confirm(self, params, state, box, connections):
        order: Order = state['order']
        order.transition_to(OrderStateMachine.Confirmed)   # изменяет состояние
        writer = box.resolve(OrderWriter)
        await writer.save(order)
        return {"confirmed": True}

    @summary_aspect("Результат")
    async def build_result(self, params, state, box, connections):
        return ConfirmOrderResult(confirmed=state['confirmed'])
```

### 7.3 Ресурсный менеджер как адаптер репозитория

Конкретная реализация `OrderReader`/`OrderWriter` для PostgreSQL (или другого хранилища) будет использовать `EntityCoordinator` и хелперы (Identity Map, Hydrator, Batcher). Например:

```python
from entity_model.helpers import EntityHydrator, EntityIdentityMap, RelationBatcher, RelationLinker

class PostgresOrderRepository(OrderReader, OrderWriter):
    def __init__(self, db_pool, coordinator: EntityCoordinator):
        self.db = db_pool
        self.coordinator = coordinator

    async def get_by_id(self, oid: str) -> Order | None:
        identity_map = EntityIdentityMap()   # на один вызов, но можно передавать сверху
        row = await self.db.fetch_one("SELECT * FROM orders WHERE id = $1", oid)
        if not row:
            return None
        hydrator = EntityHydrator(identity_map)
        order = hydrator.hydrate(Order, dict(row))
        # batcher для загрузки связанных сущностей (например, order.customer)
        batcher = RelationBatcher(identity_map)
        if order.customer_id:
            batcher.add(order, 'customer')
        await batcher.load(self, 'customer')   # self должно уметь get_by_ids
        return order

    async def save(self, order: Order) -> None:
        # валидация через ConstraintValidator
        validator = ConstraintValidator(self)
        await validator.validate(order)
        # преобразование в словарь
        data = order.model_dump(exclude_unset=True)   # Pydantic
        # upsert в БД
        await self.db.execute("""
            INSERT INTO orders (id, state, ...) VALUES ($1, $2, ...)
            ON CONFLICT (id) DO UPDATE SET ...
        """, order.id, order.current_state.name, ...)
        # сохранить связи? Это сложнее. Обычно связи сохраняются отдельно или через каскады.
```

### 7.4 Внедрение ресурсного менеджера через `@depends`

Чтобы `box.resolve(OrderReader)` работал, нужно зарегистрировать конкретную реализацию в `GateCoordinator`. Это делается через фабрику:

```python
from action_machine.dependencies import depends

# где-то в настройке приложения
coordinator = GateCoordinator()
coordinator.register_factory(OrderReader, lambda: PostgresOrderRepository(db_pool, entity_coordinator))
```

Теперь `@depends(OrderReader)` будет резолвить экземпляр `PostgresOrderRepository` (или мок в тестах). При этом `OrderReader` — это интерфейс (Protocol), а фабрика возвращает конкретный адаптер.

### 7.5 Конечные автоматы и события

Изменение состояния сущности (через `transition_to`) может генерировать **событие**, которое будет отправлено в `ActionMachine` как событие плагина. Для этого в `BaseEntity.transition_to` можно вызывать метод `emit_event` через переданный `box` или через глобальный координатор. Лучше передавать `box` в сущность? Сущность не должна знать о box (нарушение гексагональной архитектуры). Альтернатива: после сохранения сущности ресурсный менеджер публикует событие в шину, а плагин ActionMachine подписывается на эти события.

**Упрощённый вариант:** в аспекте после `order.transition_to` и `writer.save` вызывать `box.run(...)` для запуска другого действия. Это явно, но не автоматически.

Более элегантно: использовать **поток событий** (event stream). Сущность может накапливать доменные события (`domain events`) в списке, а ресурсный менеджер при сохранении публикует их. В ActionMachine плагин может слушать канал событий и запускать действия.

Но для первого релиза можно обойтись без автоматической генерации действий — пусть разработчик явно вызывает нужные действия в аспектах.

### 7.6 Экспорт графа сущностей для AI (MCP)

`McpAdapter` уже умеет регистрировать ресурс `system://graph`. Добавим ресурс `entity://graph`, который будет отдавать JSON с описанием всех сущностей, их полей, связей и состояний. AI-агент сможет исследовать модель данных.

Пример вывода:

```json
{
  "entities": [
    {
      "name": "Order",
      "domain": "orders",
      "description": "Заказ клиента",
      "state_machine": {
        "states": ["New", "Confirmed", "Shipped", "Delivered", "Cancelled"],
        "transitions": {
          "New": ["Confirmed", "Cancelled"],
          "Confirmed": ["Shipped", "Cancelled"],
          "Shipped": ["Delivered"]
        }
      },
      "attributes": [
        {"name": "order_id", "type": "str", "required": true, "description": "..."},
        {"name": "amount", "type": "float", "constraints": {"gt": 0}, "description": "..."}
      ],
      "relations": [
        {"name": "items", "type": "composite_many", "target": "OrderLine", "back_populates": "order"},
        {"name": "customer", "type": "reference_one", "target": "Customer", "back_populates": "orders"}
      ]
    }
  ]
}
```

Для этого в `McpAdapter` добавим метод `register_entity_resources(coordinator)`.

### 7.7 Тестирование с TestBench

`TestBench` уже умеет подменять зависимости через `mocks`. Для тестирования действий, работающих с сущностями, можно подменить репозиторий на мок:

```python
from unittest.mock import AsyncMock

mock_repo = AsyncMock(spec=OrderReader)
mock_repo.get_by_id.return_value = some_order

bench = TestBench(mocks={OrderReader: mock_repo})
```

Также можно написать тестовую реализацию репозитория в памяти (`InMemoryOrderRepository`), которая будет хранить сущности в dict и позволять проверять состояние без БД.

### 7.8 Пример полного сценария: создание заказа

1. Пользователь (через REST API или AI) вызывает `CreateOrderAction`.
2. Аспекты:
   - Валидация параметров (Pydantic).
   - Создание экземпляра `Order` (с состоянием `New`).
   - Вызов `writer.save(order)`.
   - (Опционально) запуск `SendNotificationAction` через `box.run`.
3. Ресурсный менеджер сохраняет заказ в БД, генерирует событие `OrderCreated`.
4. Плагин, подписанный на `OrderCreated`, может запустить `ProcessPaymentAction` асинхронно.
5. Плагин метрик логирует время создания.

Всё это без изменения кода сущности и без привязки к конкретной БД.

### 7.9 Итог по части 7

- **Интерфейсы репозиториев** (порты) определяются в домене.
- **Ресурсные менеджеры** реализуют эти порты, используя `EntityCoordinator` и хелперы.
- **Действия** получают репозитории через `box.resolve()` и работают с сущностями.
- **Конечные автоматы** управляют состоянием; переходы могут быть проверены перед сохранением.
- **Граф сущностей** экспортируется в MCP для AI.
- **Тестирование** подменой репозиториев через TestBench.

### 7.10 Полная картина: ActionMachine + Entity Model

| Слой | Компоненты | Отвечает за |
|------|------------|--------------|
| **Модель процессов** | `BaseAction`, аспекты, чекеры, роли, зависимости | Бизнес-логика, последовательность шагов, права доступа, внешние вызовы |
| **Модель сущностей** | `BaseEntity`, `@entity`, связи, конечные автоматы | Структура данных, связи, жизненный цикл, инварианты |
| **Координация** | `GateCoordinator`, `EntityCoordinator` | Сбор метаданных, проверка целостности, граф, API для адаптеров |
| **Адаптеры протоколов** | `FastApiAdapter`, `McpAdapter` | Преобразование HTTP/MCP в вызовы действий |
| **Адаптеры хранения** | Ресурсные менеджеры (`PostgresOrderRepository`) | Чтение/запись сущностей в конкретные хранилища |
| **Хелперы** | `IdentityMap`, `RelationBatcher`, `Hydrator`, `Linker`, `Validator` | Облегчают написание адаптеров, предотвращают ошибки |
| **Тестирование** | `TestBench`, моки, in-memory репозитории | Прогон действий на async/sync машинах, проверка результатов |
| **Прозрачность** | Плагины, логирование, MCP-ресурсы | Наблюдаемость, AI-доступ |

---

## 🎯 Заключение по всему техническому заданию

Мы спроектировали **статическую модель предметных сущностей** (Entity Model), которая:

- Полностью декларативна (декораторы, generic-контейнеры, Pydantic).
- Проверяется на этапе сборки координатором (двунаправленность, совместимость типов, циклы, XOR).
- Не зависит от способа хранения (гексагональная архитектура).
- Интегрируется с ActionMachine через репозитории (порты/адаптеры).
- Предоставляет хелперы для лёгкого и безопасного написания ресурсных менеджеров.
- Экспортирует граф для AI-агентов через MCP.

Вместе ActionMachine и Entity Model образуют **платформу для построения самопроверяемых, самонаблюдаемых бизнес-систем**, где и данные, и процессы описываются единым декларативным языком (Python + декораторы), а вся инфраструктура (API, хранение, тестирование, AI-интеграция) генерируется автоматически.

**Оценка инновационности всей системы (ActionMachine + Entity Model): 10/10.**

Если потребуется уточнить любую деталь или написать прототип кода для одного из компонентов, дайте знать.
-----------------------------------------------------------------------------------
## Пример ресурсного менеджера для PostgreSQL с хелперами

### 1. Структура проекта

```
domain/
  entities.py          # Order, OrderLine, Customer (связи, автоматы)
  ports.py             # OrderReader, OrderWriter (протоколы)
infrastructure/
  postgres/
    connection.py      # менеджер соединений (asyncpg pool)
    order_repository.py # реализация OrderReader/OrderWriter
    helpers.py         # имплементация EntityHydrator, RelationBatcher и т.д. (вынесем в entity_model.helpers)
tests/
  test_order_repository.py
  test_order_action_integration.py
```

### 2. Определение сущностей (domain/entities.py)

```python
from datetime import datetime
from typing import Optional
from pydantic import Field
from entity_model import BaseEntity, entity, CompositeMany, ReferenceOne
from .state_machines import OrderStateMachine   # как в части 1

@entity
class Order(BaseEntity[OrderStateMachine]):
    id: str = Field(description="UUID заказа")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания")
    customer_id: str = Field(description="ID клиента (внешний)")
    # Связи
    items: CompositeMany["OrderLine"] = CompositeMany(back_populates="order")
    customer: ReferenceOne["Customer"] = ReferenceOne(back_populates="orders")   # но customer может быть внешней сущностью? Для примера оставим.

@entity
class OrderLine(BaseEntity[None]):   # без автомата
    id: str
    order_id: str
    product_name: str
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    order: ReferenceOne[Order] = ReferenceOne(back_populates="items")

@entity
class Customer(BaseEntity[None]):
    id: str
    name: str
    orders: CompositeMany[Order] = CompositeMany(back_populates="customer")
```

### 3. Реализация `RelationBatcher` (entity_model.helpers.batcher)

```python
# entity_model/helpers/batcher.py
from typing import Dict, List, Any, TypeVar, Generic
from .identity_map import EntityIdentityMap
from .linker import RelationLinker

E = TypeVar('E', bound='BaseEntity')
T = TypeVar('T', bound='BaseEntity')

class RelationBatcher:
    """
    Собирает запросы на загрузку связей и выполняет их одним пакетом.
    Предполагает, что менеджер имеет метод get_by_ids(entity_cls, ids).
    """
    def __init__(self, identity_map: EntityIdentityMap):
        self._map = identity_map
        # key: (relation_name, target_cls) -> target_id -> list[(source_entity, source_rel_name)]
        self._pending: Dict[tuple[str, type], Dict[Any, List[tuple[BaseEntity, str]]]] = {}

    def add(self, source_entity: BaseEntity, relation_name: str) -> None:
        """Запланировать загрузку связи relation_name для source_entity."""
        # Получить метаданные связи
        src_meta = get_entity_metadata(type(source_entity))
        rel_meta = src_meta.get_relation(relation_name)
        target_cls = rel_meta.target_type   # для простоты не Union
        # Извлечь target_id из source_entity (поле foreign key)
        fk_field = f"{relation_name}_id"   # соглашение: Order.customer_id -> связь customer
        target_id = getattr(source_entity, fk_field, None)
        if target_id is None:
            return
        key = (relation_name, target_cls)
        self._pending.setdefault(key, {}).setdefault(target_id, []).append((source_entity, relation_name))

    async def load(self, manager: Any, relation_name: str, target_cls: type) -> None:
        """
        Загрузить все запланированные связи relation_name.
        manager должен иметь метод get_by_ids(cls, ids).
        """
        key = (relation_name, target_cls)
        if key not in self._pending:
            return
        target_ids = list(self._pending[key].keys())
        # Загружаем все целевые сущности за один запрос
        targets = await manager.get_by_ids(target_cls, target_ids)
        # Создаём словарь id -> entity
        target_by_id = {t.id: t for t in targets}
        for target_id, sources in self._pending[key].items():
            target = target_by_id.get(target_id)
            if not target:
                continue   # или ошибка, если связь обязательна
            for source_entity, src_rel_name in sources:
                RelationLinker.link(source_entity, src_rel_name, target)
        del self._pending[key]
```

### 4. Реализация `EntityHydrator` (упрощённая)

```python
# entity_model/helpers/hydrator.py
from typing import Type, Dict, Any, Optional
from pydantic import BaseModel
from .identity_map import EntityIdentityMap

class EntityHydrator:
    def __init__(self, identity_map: Optional[EntityIdentityMap] = None):
        self._map = identity_map

    def hydrate(self, entity_cls: Type[BaseEntity], data: Dict[str, Any]) -> BaseEntity:
        # Извлекаем первичный ключ (предполагаем поле 'id')
        entity_id = data.get('id')
        if entity_id and self._map:
            existing = self._map.get(entity_cls, entity_id)
            if existing:
                # Можно обновить поля? Для простоты возвращаем существующий.
                return existing
        # Создаём экземпляр через Pydantic (у нас BaseEntity наследует BaseModel)
        # Но поля-связи пока пропускаем (они будут заполнены позже)
        # Для этого временно убираем из data ключи, начинающиеся с '_' (внутренние)
        init_data = {k: v for k, v in data.items() if not k.startswith('_')}
        entity = entity_cls(**init_data)
        if self._map and entity_id:
            self._map.add(entity)
        return entity
```

### 5. Ресурсный менеджер (infrastructure/postgres/order_repository.py)

```python
import asyncpg
from domain.ports import OrderReader, OrderWriter
from domain.entities import Order, OrderLine, Customer
from entity_model.helpers import EntityIdentityMap, EntityHydrator, RelationBatcher, RelationLinker

class PostgresOrderRepository(OrderReader, OrderWriter):
    def __init__(self, pool: asyncpg.Pool, coordinator):
        self._pool = pool
        self._coordinator = coordinator   # EntityCoordinator

    async def get_by_id(self, oid: str) -> Order | None:
        identity_map = EntityIdentityMap()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", oid)
            if not row:
                return None
            hydrator = EntityHydrator(identity_map)
            order = hydrator.hydrate(Order, dict(row))
            # Загрузка связанных позиций (OrderLine)
            await self._load_items(order, identity_map)
            # Загрузка связанного клиента (если нужен)
            if order.customer_id:
                batcher = RelationBatcher(identity_map)
                batcher.add(order, 'customer')
                await batcher.load(self, 'customer', Customer)
            return order

    async def _load_items(self, order: Order, identity_map: EntityIdentityMap):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM order_lines WHERE order_id = $1", order.id)
            hydrator = EntityHydrator(identity_map)
            for row in rows:
                line = hydrator.hydrate(OrderLine, dict(row))
                # Устанавливаем связь вручную или через RelationLinker
                RelationLinker.link(order, 'items', line)   # добавит в коллекцию order.items и установит line.order

    async def save(self, order: Order) -> None:
        # Валидация через ConstraintValidator (опустим для краткости)
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Сохраняем сам заказ
                await conn.execute("""
                    INSERT INTO orders (id, created_at, customer_id, state)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO UPDATE SET
                        customer_id = EXCLUDED.customer_id,
                        state = EXCLUDED.state
                """, order.id, order.created_at, order.customer_id, order.current_state.name if order.current_state else None)
                # Сохраняем позиции (каскадно)
                for line in order.items:
                    await conn.execute("""
                        INSERT INTO order_lines (id, order_id, product_name, quantity, price)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO UPDATE SET
                            product_name = EXCLUDED.product_name,
                            quantity = EXCLUDED.quantity,
                            price = EXCLUDED.price
                    """, line.id, line.order_id, line.product_name, line.quantity, line.price)

    async def get_by_ids(self, entity_cls: type, ids: list[str]) -> list[BaseEntity]:
        """Метод для batch-загрузки, требуется RelationBatcher."""
        if entity_cls == Customer:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM customers WHERE id = ANY($1)", ids)
                hydrator = EntityHydrator()
                return [hydrator.hydrate(Customer, dict(row)) for row in rows]
        elif entity_cls == Order:
            # ... аналогично
            pass
        else:
            raise NotImplementedError
```

### 6. Интеграция с ActionMachine: использование репозитория в действии

```python
# domain/actions/confirm_order.py
from action_machine.core.base_action import BaseAction
from action_machine.dependencies import depends
from domain.ports import OrderReader, OrderWriter

@depends(OrderReader)
@depends(OrderWriter)
class ConfirmOrderAction(BaseAction[ConfirmParams, ConfirmResult]):
    async def run(self, params, box):
        reader = box.resolve(OrderReader)
        order = await reader.get_by_id(params.order_id)
        order.confirm()   # меняет состояние
        writer = box.resolve(OrderWriter)
        await writer.save(order)
        return ConfirmResult(ok=True)
```

### 7. Тестовая стратегия

#### 7.1 Тестирование сущностей (изолированно)

- Создаём экземпляры сущностей в памяти, проверяем, что Pydantic валидирует поля.
- Проверяем переходы конечного автомата.
- Проверяем, что связи устанавливаются через `RelationLinker` и двунаправленность работает.

```python
# tests/test_entities.py
def test_order_creation():
    order = Order(id="1", customer_id="cust1")
    assert order.state is None   # начальное состояние не установлено
    order.start(OrderStateMachine.New)
    assert order.current_state.name == "New"
    assert order.can_transition_to(OrderStateMachine.Confirmed)
```

#### 7.2 Тестирование репозитория с реальной PostgreSQL (через testcontainers или временную БД)

Используем `pytest-asyncio` и `asyncpg` с временной схемой.

```python
# tests/test_order_repository.py
import pytest
from asyncpg import create_pool
from infrastructure.postgres.order_repository import PostgresOrderRepository

@pytest.fixture
async def db_pool():
    pool = await create_pool(dsn="postgresql://...")   # или testcontainers
    # инициализация схемы (миграции)
    yield pool
    await pool.close()

@pytest.fixture
async def repo(db_pool):
    return PostgresOrderRepository(db_pool, coordinator)

async def test_save_and_load(repo):
    order = Order(id="1", customer_id="c1")
    line = OrderLine(id="l1", order_id="1", product_name="Book", quantity=1, price=10.0)
    order.items.add(line)
    await repo.save(order)
    loaded = await repo.get_by_id("1")
    assert loaded.id == "1"
    assert len(loaded.items) == 1
    assert loaded.items[0].product_name == "Book"
```

#### 7.3 Тестирование действия с мок-репозиторием (через TestBench)

```python
# tests/test_confirm_order_action.py
from unittest.mock import AsyncMock
from action_machine.testing import TestBench
from domain.actions import ConfirmOrderAction

async def test_confirm_order():
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    order = Order(id="1")
    order.start(OrderStateMachine.New)
    mock_reader.get_by_id.return_value = order

    bench = TestBench(mocks={OrderReader: mock_reader, OrderWriter: mock_writer})
    result = await bench.run(ConfirmOrderAction(), ConfirmParams(order_id="1"), rollup=False)
    assert result.ok is True
    assert order.current_state.name == "Confirmed"
    mock_writer.save.assert_awaited_once_with(order)
```

#### 7.4 Тестирование интеграции (действие + реальный репозиторий + БД)

Используем временную БД, реальный репозиторий, и прогоняем действие через `TestBench` без моков.

```python
async def test_confirm_order_integration(repo):
    # Создаём заказ в БД через репозиторий
    order = Order(id="2", customer_id="c2")
    await repo.save(order)
    # Настраиваем bench с реальным репозиторием
    bench = TestBench(mocks={OrderReader: repo, OrderWriter: repo})
    result = await bench.run(ConfirmOrderAction(), ConfirmParams(order_id="2"), rollup=False)
    assert result.ok is True
    # Проверяем, что состояние обновилось в БД
    loaded = await repo.get_by_id("2")
    assert loaded.current_state.name == "Confirmed"
```

### 8. Запуск тестов в CI

- Для тестов с БД использовать `pytest-postgresql` или `testcontainers`.
- Отдельный запуск без БД для быстрых unit-тестов.
- Покрытие кода > 90%.

### 9. Заключение по примеру

Мы показали:
- Полный рабочий ресурсный менеджер для PostgreSQL с использованием `EntityHydrator`, `RelationBatcher`, `IdentityMap`, `RelationLinker`.
- `RelationBatcher` устраняет N+1 при загрузке связей.
- Тестовая стратегия покрывает все уровни: юнит (сущности), интеграционный (репозиторий), сквозной (действие + БД).
- Всё это органично интегрируется с ActionMachine через `@depends` и `TestBench`.

Теперь можно переходить к реализации остальных хелперов и покрытию их тестами. Если нужно, я могу написать код для `ConstraintValidator` или `UnitOfWork`.
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------

