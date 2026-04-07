# Реализованная архитектура ActionMachine: Entity Model (v1.0)

## Полная преамбула: архитектурные принципы и решения

Этот документ фиксирует не только порядок разработки, но и **почему** каждое решение принято. Любой разработчик, открывший документ через полгода, должен понять логику, не читая переписку.

### Что мы построили

Декларативную модель предметной области на Python. Модель описывает сущности, их поля, связи между ними и жизненные циклы — и больше ничего. Она не знает про базы данных, HTTP, файлы или любой другой внешний мир. Это чистое ядро в терминах гексагональной архитектуры.

Из этой модели автоматически извлекается вся информация, необходимая для построения ArchiMate‑диаграмм с правильными типами связей (Composition, Aggregation, Association), для генерации OCEL 2.0 метаданных (типы объектов, типы связей, жизненные циклы), и для статической проверки целостности архитектуры до запуска приложения.

Сущности регистрируются через **тот же `GateCoordinator`**, что и Action, Plugin, ResourceManager — один координатор, один граф rustworkx, один `MetadataBuilder.build()`. Никакого отдельного `EntityCoordinator` не существует.

### Почему не ORM

ORM привязывает модель к хранилищу. Наша модель — это спецификация, а не маппинг таблиц. Один и тот же `OrderEntity` может читаться из PostgreSQL, MongoDB, REST API или мока — это забота ресурсного менеджера (адаптера), а не модели. Модель не содержит ни одного импорта, связанного с хранилищем.

### Почему не DTO

`BaseEntity` — внутреннее представление бизнес-сущности, а не объект для передачи через API. Для внешнего API используются отдельные `Params` и `Result` (как в Action). Причины:
- Частичная загрузка через `partial()` может вызвать `FieldNotLoadedError` при сериализации.
- Контейнеры связей (`AssociationOne`, `CompositeMany`) сериализуются со внутренней структурой (`id` + `entity`), а не как плоские ключи.
- Глубина вложенности связей не контролируется — API обычно хочет плоский ответ или контролируемую глубину.

В простых случаях `model_dump()` работает, но для production API — создавайте DTO или используйте адаптер маппинга.

### Почему не отдельный язык (TLA+, Alloy, DSL)

Потому что модель — это одновременно и спецификация, и исполняемый Python‑код. Разработчик не переключается между двумя мирами. IDE подсказывает поля, mypy проверяет типы, координатор проверяет целостность графа — всё в одном месте.

### Почему frozen‑объекты без двусторонних ссылок в рантайме

Модель декларирует связи (Order → Customer, Customer → Orders), но в рантайме объекты не держат живых циклических ссылок друг на друга. `OrderEntity` хранит ссылку на `CustomerEntity` через контейнер связи, который содержит `id` и опционально загруженный объект. Обратная связь `Customer.orders` — это метаданные для координатора и ArchiMate, а не список в памяти. Это исключает циклические зависимости, проблемы с сериализацией и скрытые побочные эффекты. Если action нужен клиент заказа — он просит менеджер явно.

### Почему описания обязательны

Каждое поле и каждая связь обязаны иметь текстовое описание. Это не комментарий — это структурное метаданное, которое попадёт в ArchiMate‑диаграмму, в OCEL‑схему, в автогенерированную документацию. Модель без описаний — это код, а не спецификация. Поэтому отсутствие описания — ошибка сборки, а не предупреждение.

### Почему свой автомат, а не python‑statemachine

Наш автомат выполняет две роли: (1) декларативный шаблон графа состояний для координатора и (2) runtime‑хранилище текущего состояния экземпляра сущности. Библиотека `python-statemachine` — это runtime‑движок с колбэками, observers и async‑переходами. Нам нужен иммутабельный граф состояний, проверки целостности при старте и метод `transition()`, возвращающий **новый** экземпляр (frozen-совместимость). Это ~200 строк кода без внешних зависимостей, которые мы полностью контролируем.

### Почему Lifecycle — pydantic‑поле, а не атрибут класса

Lifecycle хранит **текущее состояние конкретного экземпляра** сущности (`current_state`). Каждый заказ находится в своём состоянии — `"new"`, `"confirmed"`, `"delivered"`. Поэтому Lifecycle — обычное pydantic‑поле (`OrderLifecycle | None`), а не `ClassVar`. Поле без `default` — обязательное при полном создании. При `partial()` без lifecycle → `FieldNotLoadedError`. Граф допустимых состояний определяется в специализированном классе через `_template` (при import-time) и проверяется координатором при старте.

### Почему специализированные классы Lifecycle, а не один Lifecycle с description

Каждый конечный автомат — отдельный класс-наследник `Lifecycle` (например, `OrderLifecycle`, `PaymentLifecycle`). Граф состояний фиксируется в `_template` при определении класса (import-time). Координатор при старте находит подклассы Lifecycle в `model_fields` сущности, читает `_template` и проверяет 8 правил целостности. Описание автомата живёт в `Field(description="...")`, а не внутри Lifecycle — единообразно со всеми остальными полями. У `Lifecycle.__init__()` нет параметра `description`.

### Почему переход состояния = новый экземпляр

Сущность frozen после создания (`frozen=True`). Метод `transition("confirmed")` возвращает **новый** экземпляр `OrderLifecycle` с `current_state="confirmed"`, не мутируя старый. Новый экземпляр сущности создаётся через `order.model_copy(update={"lifecycle": new_lc})`. Старый объект не изменяется — предсказуемость, безопасность, консистентность.

### Почему gate‑host паттерн

Каждый декоратор (`@entity`) требует, чтобы класс наследовал соответствующий gate‑host — маркерный миксин, подтверждающий осознанное подключение функциональности. `BaseEntity` предоставляет `EntityGateHost` автоматически. Попытка повесить `@entity` на голый класс → `EntityDecoratorError`.

### Почему типы владения, а не просто «связь»

В ArchiMate существует три структурных отношения: Composition, Aggregation, Association. Они несут разную семантику: при удалении родителя композитные дети удаляются, агрегатные — отвязываются, ассоциированные — не затрагиваются. Шесть контейнеров (три типа × две кардинальности) — минимально необходимый набор.

### Почему Inverse обязателен

Автоматический поиск обратных связей ломается при дублировании типов. Если у сущности `CustomerEntity` есть два поля `orders` и `invoices`, оба типа `AssociationMany[OrderEntity]`, координатор не сможет определить пару. Явный `Inverse` — одна строка, которая делает связь однозначной. Каждая связь обязана иметь `Inverse(TargetClass, "field_name")` или `NoInverse()`. Иначе ошибка сборки.

### Контейнер связи: id всегда, объект — опционально

Контейнеры One (`CompositeOne`, `AggregateOne`, `AssociationOne`) хранят `id` и опционально `entity: T | None`. Контейнеры Many (`CompositeMany`, `AggregateMany`, `AssociationMany`) хранят `ids: tuple` и опционально `entities: tuple`. Обращение к атрибутам контейнера проксируется на `entity`. Если объект не загружен — `RelationNotLoadedError`. Тип `id` не фиксирован — `str`, `int`, `UUID`, любой.

### Почему единый GateCoordinator, а не отдельный EntityCoordinator

Сущности регистрируются через тот же `GateCoordinator.get()` и `MetadataBuilder.build()`, что и Action, Plugin, ResourceManager. Один координатор, один граф rustworkx, один кеш `ClassMetadata`. Декоратор `@entity` записывает `_entity_info` — точно так же как `@meta` записывает `_meta_info`. Коллекторы `collect_entity_info()`, `collect_entity_fields()`, `collect_entity_relations()`, `collect_entity_lifecycles()` встроены в `collectors.py` рядом с `collect_meta()`, `collect_aspects()`, `collect_checkers()`. `ClassMetadata` расширен полями `entity_info`, `entity_fields`, `entity_relations`, `entity_lifecycles`. Граф содержит узлы `entity`, `entity_field`, `entity_relation`, `entity_lifecycle` с leaf-рёбрами `has_field`, `has_relation`, `has_lifecycle`, `belongs_to`.

### Почему entity-связи — leaf‑рёбра в графе

Связи между сущностями (Order ↔ Customer) — циклические по бизнес-природе. Структурные рёбра (`depends`, `connection`) проверяются на ацикличность через `_add_edge_checked()`. Entity-рёбра (`has_field`, `has_relation`, `has_lifecycle`) добавляются через `_add_leaf_edge()` без проверки — цикл невозможен по конструкции (ведут к терминальным узлам).

### Как модель используется в ресурсных менеджерах

Менеджер — адаптер. Его работа: взять данные из внешнего мира, преобразовать в типизированные frozen‑сущности и вернуть. Action не знает, откуда данные. Модель не знает про форматы.

### Порядок декораторов не имеет значения

Декораторы `@entity` и любые другие записывают атрибуты на класс независимо. MetadataBuilder читает все атрибуты при сборке.

### Deprecated‑поля для плавной миграции

Для простых полей — `Field(deprecated=True)`. Для связей — `Annotated[..., deprecated("причина")]` по PEP 702. IDE зачёркивает имя, mypy выдаёт предупреждение.

### Домены: обязательные name и description

Домены описываются через `BaseDomain` с двумя обязательными атрибутами: `name` и `description`. Оба проверяются в `__init_subclass__()` при определении класса — fail-fast на import-time [4].

### Частичная загрузка сущности через partial()

`BaseEntity.partial()` создаёт экземпляр без Pydantic-валидации (через `model_construct()`). При обращении к незагруженному полю — `FieldNotLoadedError`. Это не lazy-loading — никаких скрытых запросов к базе.

### Сборка сущностей через build() с типизированным маппингом

Утилита `build()` собирает frozen-сущность из плоского словаря. Прокси `EntityProxy[T]` типизирован — IDE подсказывает поля, опечатка → `AttributeError`.

### Тестовая фабрика make()

`make(EntityClass, **overrides)` создаёт сущность с автогенерацией дефолтов по типам полей: `str` → `"test_{field_name}"`, `int` → `1`, `float` → `1.0`, `Optional[Lifecycle]` → `None`, подкласс Lifecycle → экземпляр с первым начальным состоянием из `_template`.

---

## Этап 1 — Конечные автоматы (Lifecycle)

**Зачем:** у большинства бизнес‑сущностей есть жизненный цикл. Автомат, описанный прямо внутри сущности, служит живой документацией и проверяется на целостность при старте.

**Как устроен:**

Lifecycle выполняет две роли:

1. **Шаблон** (`_template`) — граф состояний и переходов, определяется при определении специализированного класса (import-time). Координатор проверяет 8 правил целостности при старте.

2. **Экземпляр** — хранит `current_state` конкретного бизнес-объекта. Является обычным pydantic-полем сущности.

**StateType** — enum с тремя взаимоисключающими значениями (`INITIAL`, `INTERMEDIATE`, `FINAL`), исключающий невалидные комбинации на уровне типа.

**StateInfo** — frozen dataclass, содержащий всю информацию о состоянии в одном месте: `key`, `display_name`, `state_type`, `transitions`.

**Fluent API для построения шаблона:**

```python
Lifecycle()
    .state(key, display_name)       → _StateBuilder
        .to(*target_keys)           → _StateBuilder
        .initial()                  → Lifecycle
        .intermediate()             → Lifecycle
        .final()                    → Lifecycle
```

**Специализированный класс:**

```python
class OrderLifecycle(Lifecycle):
    _template = (
        Lifecycle()
        .state("new", "Новый заказ").to("confirmed", "cancelled").initial()
        .state("confirmed", "Подтверждён").to("shipped", "cancelled").intermediate()
        .state("shipped", "Отправлен").to("delivered").intermediate()
        .state("delivered", "Доставлен").final()
        .state("cancelled", "Отменён").final()
    )
```

**API экземпляра:**

```python
order.lifecycle.current_state              # → "new"
order.lifecycle.can_transition("confirmed") # → True
order.lifecycle.available_transitions       # → {"confirmed", "cancelled"}
order.lifecycle.is_initial                  # → True
order.lifecycle.is_final                    # → False

# Переход (frozen-сущность):
new_lc = order.lifecycle.transition("confirmed")
confirmed_order = order.model_copy(update={"lifecycle": new_lc})
```

**Ошибки:**
- `InvalidStateError` — неизвестное состояние при создании (`OrderLifecycle("unknown")`).
- `InvalidTransitionError` — недопустимый переход (`order.lifecycle.transition("delivered")` из "new").

**Проверки целостности (координатор при старте):**
1. Каждое состояние завершено флагом.
2. Есть хотя бы одно начальное состояние.
3. Есть хотя бы одно финальное состояние.
4. Финальные состояния не имеют переходов.
5. Все цели переходов существуют.
6. Каждое не-финальное состояние имеет хотя бы один переход.
7. Из каждого начального достижимо хотя бы одно финальное.
8. Каждое не-initial состояние является целью хотя бы одного перехода.

**Размещение:** `src/action_machine/domain/lifecycle.py`

---

## Этап 2 — Базовая сущность (BaseEntity)

**Зачем:** единый стандарт для всех сущностей домена. Иммутабельность, обязательные описания, поддержка автоматов, частичная загрузка.

`BaseEntity` наследует `BaseSchema` (`frozen=True`, `extra="forbid"`), `ABC`, `EntityGateHost`, `DescribedFieldsGateHost`.

**Поля Lifecycle:** любое количество pydantic-полей типа `OrderLifecycle | None`, или ни одного. Описание в `Field(description="...")`. Без `default` — обязательное при полном создании. При `partial()` без lifecycle → `FieldNotLoadedError`.

**Декоратор `@entity(description, domain)`** — проверяет `EntityGateHost`, записывает `_entity_info`. Аналог `@meta` для Action.

**Суффикс "Entity"** обязателен в имени класса — проверяется в `__init_subclass__()`.

**Пример:**

```python
@entity(description="Заказ клиента", domain=ShopDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Идентификатор заказа")
    amount: float = Field(description="Сумма заказа", ge=0)
    lifecycle: OrderLifecycle | None = Field(description="Жизненный цикл заказа")
    payment: PaymentLifecycle | None = Field(description="Статус оплаты")
```

**Доступ:**

```python
order.id                        # → "ORD-001" (dot-доступ)
order["id"]                     # → "ORD-001" (dict-доступ)
order.lifecycle.current_state   # → "new"
order.model_dump()              # → сериализация
```

**Частичная загрузка:**

```python
order = OrderEntity.partial(id="ORD-001", amount=100.0)
order.id         # → "ORD-001" ✅
order.lifecycle  # → FieldNotLoadedError
```

**Размещение:** `src/action_machine/domain/entity.py`

---

## Этап 3 — Связи между сущностями

**Три типа владения:** Composition, Aggregation, Association.

**Шесть контейнеров:** `CompositeOne[T]`, `CompositeMany[T]`, `AggregateOne[T]`, `AggregateMany[T]`, `AssociationOne[T]`, `AssociationMany[T]`.

**RelationType** — enum: `COMPOSITION`, `AGGREGATION`, `ASSOCIATION`.

**Объявление связи:**

```python
customer: Annotated[
    AssociationOne[CustomerEntity] | None,
    Inverse(CustomerEntity, "orders"),
] = Rel(description="Клиент, оформивший заказ")
```

- `Rel(description)` — обязательное описание, используется как default-значение поля.
- `Inverse(TargetClass, "field_name")` или `NoInverse()` — обязательны в `Annotated`.
- Контейнеры One хранят `id` + `entity: T | None`, проксируют атрибуты.
- Контейнеры Many хранят `ids: tuple` + `entities: tuple`.
- Frozen — запись и удаление атрибутов запрещены.
- `RelationNotLoadedError` — при обращении к атрибуту незагруженного entity.

**Матрица совместимости:** Composite ↔ Association ✅, Aggregate ↔ Association ✅, Association ↔ Association ✅. Composite ↔ Composite ❌, Composite ↔ Aggregate ❌, Aggregate ↔ Aggregate ❌.

**Размещение:** `src/action_machine/domain/relation_containers.py`, `src/action_machine/domain/relation_markers.py`

---

## Этап 4 — Единый координатор и метаданные

**Ключевое решение:** отдельного `EntityCoordinator` не существует. Сущности регистрируются через тот же `GateCoordinator.get()`, что и Action, Plugin, ResourceManager.

**Механизм — единообразный для всех типов классов:**

1. Декоратор записывает временный атрибут → `@entity` пишет `_entity_info`, `@meta` пишет `_meta_info`.
2. Коллектор читает атрибут → `collect_entity_info()` читает `_entity_info`, `collect_meta()` читает `_meta_info`.
3. `MetadataBuilder.build()` вызывает все коллекторы → конструирует `ClassMetadata`.
4. `GateCoordinator` кеширует `ClassMetadata` → заполняет граф.

**Расширения `ClassMetadata`:**
- `EntityInfo` — описание и домен из `@entity`.
- `EntityFieldInfo` — метаданные простого поля.
- `EntityRelationInfo` — метаданные связи.
- `EntityLifecycleInfo` — метаданные Lifecycle (ссылка на `_template`, количество состояний).

**Расширения `collectors.py`:**
- `collect_entity_info()` — аналог `collect_meta()`.
- `collect_entity_fields()` — простые поля (не связи, не Lifecycle).
- `collect_entity_relations()` — связи из `Annotated[Container | None, Inverse/NoInverse]`.
- `collect_entity_lifecycles()` — подклассы Lifecycle в `model_fields`.

**Обработка `Annotated` и `Union`:** коллекторы разворачивают `Annotated[X | None, ...]` — сначала извлекают `X | None` из `Annotated`, потом `X` из `Union`, используя `inspect.isclass()` для защиты от TypeError.

**Расширения `GateCoordinator._populate_graph()`:**

Узлы: `entity`, `entity_field`, `entity_relation`, `entity_lifecycle`.

Рёбра (все leaf, без проверки ацикличности):
- `has_field` — entity → entity_field
- `has_relation` — entity → entity_relation
- `has_lifecycle` — entity → entity_lifecycle
- `belongs_to` — entity → domain (переиспользует существующие domain-узлы)

**Пример дерева в графе:**

```
entity:OrderEntity
├── has_field → entity_field:OrderEntity.id
├── has_field → entity_field:OrderEntity.amount
├── has_relation → entity_relation:OrderEntity.customer
├── has_lifecycle → entity_lifecycle:OrderEntity.lifecycle
└── belongs_to → domain:orders
```

**API координатора (через ClassMetadata):**

```python
coordinator = GateCoordinator()
meta = coordinator.get(OrderEntity)

meta.is_entity()                    # → True
meta.entity_info.description        # → "Заказ клиента"
meta.get_entity_field_names()       # → ("id", "amount")
meta.get_entity_relation_names()    # → ("customer",)
meta.get_entity_lifecycle_names()   # → ("lifecycle",)

coordinator.get_nodes_by_type("entity")       # → узлы entity в графе
coordinator.get_nodes_by_type("entity_field")  # → узлы полей
```

**Размещение:** расширения в `src/action_machine/core/class_metadata.py`, `src/action_machine/metadata/collectors.py`, `src/action_machine/metadata/builder.py`, `src/action_machine/core/gate_coordinator.py`

---

## Этап 5 — Утилиты

**`build(data, EntityClass, mapper=None)`** — сборка frozen-сущности из плоского словаря с типизированным маппингом через лямбду:

```python
order = build(row, OrderEntity, lambda e, r: {
    e.id: r["order_id"],
    e.amount: r["order_amount"],
})
```

**`make(EntityClass, **overrides)`** — тестовая фабрика с автогенерацией дефолтов:

```python
order = make(OrderEntity, amount=100.0)
# id → "test_id", lifecycle → None (Optional), amount → 100.0
```

**Размещение:** `src/action_machine/domain/hydration.py`, `src/action_machine/domain/testing.py`

---

## Этап 6 — Публичный API и файлы

**Реэкспорт из `src/action_machine/domain/__init__.py`:**
- `BaseDomain`
- `BaseEntity`, `EntityGateHost`, `entity`
- `Lifecycle`, `StateType`, `StateInfo`
- `CompositeOne`, `CompositeMany`, `AggregateOne`, `AggregateMany`, `AssociationOne`, `AssociationMany`, `RelationType`
- `Inverse`, `NoInverse`, `Rel`
- `build`, `make`
- `FieldNotLoadedError`, `RelationNotLoadedError`, `EntityDecoratorError`, `LifecycleValidationError`

**Удалённые файлы:**
- `src/action_machine/domain/coordinator.py` — мёртвый дубликат.
- `src/action_machine/domain/entity_coordinator.py` — заменён расширением GateCoordinator.
- `src/action_machine/domain/entity_metadata.py` — заменён полями в ClassMetadata.
- `src/action_machine/domain/relations.py` — заменён `relation_containers.py` + `relation_markers.py`.

---

## Архитектурные вопросы и ответы (FAQ)

### Q: Lifecycle — это отдельный объект или часть сущности?
**A:** Lifecycle — и то, и другое. Специализированный класс (например `OrderLifecycle`) определяет граф состояний в `_template` — это метаданные. Экземпляр `OrderLifecycle("new")` хранит текущее состояние конкретного бизнес-объекта — это обычное pydantic-поле сущности.

### Q: Где хранится текущее состояние сущности?
**A:** В поле Lifecycle. `order.lifecycle.current_state` → `"new"`. Отдельного поля `status: str` не нужно — текущее состояние И есть позиция в конечном автомате.

### Q: Как сделать переход состояния если сущность frozen?
**A:** `transition()` возвращает **новый** экземпляр Lifecycle: `new_lc = order.lifecycle.transition("confirmed")`. Новая сущность: `order.model_copy(update={"lifecycle": new_lc})`. Старый объект не изменяется.

### Q: Lifecycle обязателен для сущности?
**A:** Нет. У сущности может быть ни одного поля Lifecycle. Координатор просто не выполняет проверки Lifecycle для таких сущностей.

### Q: Может ли у сущности быть несколько Lifecycle?
**A:** Да. Любое количество полей с разными специализированными классами и любыми именами: `lifecycle: OrderLifecycle | None`, `payment: PaymentLifecycle | None`.

### Q: @meta используется для сущностей?
**A:** Нет. `@entity(description, domain)` для сущностей. `@meta` для Action. Разные декораторы, разные gate-host, разные коллекторы — но один `MetadataBuilder.build()` и один `GateCoordinator`.

### Q: Есть ли отдельный EntityCoordinator?
**A:** Нет. Единый `GateCoordinator` обрабатывает все типы классов. `coordinator.get(OrderEntity)` — тот же метод, что и `coordinator.get(CreateOrderAction)`.

### Q: Порядок декораторов важен?
**A:** Нет. Все декораторы записывают атрибуты независимо.

### Q: Обе стороны связи должны иметь описание?
**A:** Да. Если связь двусторонняя (есть `Inverse`) — обе стороны обязаны иметь `Rel(description)`. Координатор проверяет при сборке.

### Q: Можно ли загрузить только часть полей?
**A:** Да. `OrderEntity.partial(id="ORD-001")`. Обращение к незагруженному полю → `FieldNotLoadedError`.

### Q: Как координатор проверяет Lifecycle при старте, если Lifecycle — pydantic-поле без default?
**A:** Специализированный класс (OrderLifecycle) содержит `_template` — объект Lifecycle с полным графом состояний, созданный при import-time. Коллектор `collect_entity_lifecycles()` находит подклассы Lifecycle в `model_fields`, вызывает `_get_template()` и проверяет 8 правил.

---

