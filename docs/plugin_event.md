# Полный план трансформации плагинной системы ActionMachine

## Содержание

1. [Обзор текущей реализации](#1-обзор-текущей-реализации)
2. [Архитектурные решения и обоснования](#2-архитектурные-решения-и-обоснования)
3. [Иерархия классов событий](#3-иерархия-классов-событий)
4. [Новый декоратор @on](#4-новый-декоратор-on)
5. [Порядок проверки фильтров при эмиссии события](#5-порядок-проверки-фильтров-при-эмиссии-события)
6. [План изменений по файлам](#6-план-изменений-по-файлам)
7. [План тестирования](#7-план-тестирования)
8. [Порядок реализации](#8-порядок-реализации)

---

## 1. Обзор текущей реализации

Текущая плагинная система построена на строковых фильтрах [15]:

- Декоратор `@on(event_type: str, action_filter: str, ignore_exceptions: bool)` [15]
- Единый `PluginEvent` с Optional-полями для всех типов событий [13]
- `Plugin.get_handlers(event_name: str, class_name: str)` — поиск по строковому совпадению `event_type` и regex `action_filter` [14]
- `PluginRunContext.emit_event()` — создаёт `PluginEvent` и рассылает обработчикам [17]
- `PluginCoordinator` — stateless-координатор с `create_run_context()` [18]
- Сигнатура обработчика: `async def handler(self, state, event: PluginEvent, log) -> state` [14]

Типы событий определяются строками: `"global_start"`, `"global_finish"`, `"before:validate"`, `"after:process_payment"`, `"on_error"` [1].

### Проблемы текущей реализации

1. **Строковые фильтры** — опечатки в `event_type` и `action_filter` не обнаруживаются до рантайма [15].
2. **Единый PluginEvent** — содержит все поля для всех типов событий, большинство из которых `None` для конкретного события [13].
3. **Нет фильтрации по типу действия** — `action_filter` сравнивает строковое имя через regex, а не тип через `isinstance` [14].
4. **Нет фильтрации по типу аспекта** — нельзя подписаться только на summary-аспекты или только на on_error.
5. **Нет фильтрации по имени аспекта** — нельзя подписаться на конкретный аспект `validate_amount`.
6. **Нет фильтрации по уровню вложенности** — нельзя игнорировать вложенные `box.run()`.

---

## 2. Архитектурные решения и обоснования

### 2.1. Почему уникальные классы событий вместо единого PluginEvent?

Текущий `PluginEvent` содержит поля `result`, `duration`, `error`, `has_action_handler`, `is_summary` [13]. Для `global_start` поля `result`, `duration`, `error` всегда `None`. Для `on_error` поле `result` всегда `None`. Это нарушает принцип «объект содержит ровно те данные, которые ему принадлежат».

Уникальные классы событий решают это: `GlobalStartEvent` не имеет `result` и `duration`, а `GlobalFinishEvent` — имеет. Mypy проверяет, что обработчик не обращается к несуществующему полю. `isinstance` в обработчике нужен только при подписке на групповой класс.

### 2.2. Почему AND-логика фильтров, а не OR?

AND-логика означает: **все** указанные фильтры в одном `@on` должны пройти одновременно. Неуказанные фильтры (`None`) пропускаются.

**Почему AND:** каждый фильтр **сужает** выборку. Разработчик говорит: «вызови меня для GlobalFinishEvent И только для OrderAction И только на корневом уровне». С OR-логикой `nest_level=0` вызвал бы обработчик для **всех** корневых вызовов любых действий — не то, что нужно.

**OR-логика** реализуется **между** несколькими `@on` на одном методе:

```python
@on(GlobalStartEvent)    # ИЛИ start
@on(GlobalFinishEvent)   # ИЛИ finish
async def on_lifecycle(self, state, event: GlobalLifecycleEvent, log):
    ...
```

Или через групповой класс: `@on(GlobalLifecycleEvent)` покрывает и start, и finish через иерархию наследования.

**Итого:** AND внутри одного `@on`, OR между несколькими `@on` на одном методе.

### 2.3. Почему конкретная аннотация event, а не BasePluginEvent?

Исходный план предлагал `event: BasePluginEvent` в сигнатуре, что вынуждало писать `isinstance` в каждом обработчике. Доработанный план разрешает конкретную аннотацию:

```python
@on(GlobalFinishEvent)
async def on_finish(self, state, event: GlobalFinishEvent, log):
    duration = event.duration_ms  # mypy ok, без isinstance
```

`MetadataBuilder` при сборке проверяет совместимость: `event_class` из декоратора должен быть подклассом аннотации `event`. Если декоратор подписан на `GlobalFinishEvent`, а аннотация — `GlobalLifecycleEvent`, это корректно (GlobalFinishEvent ⊂ GlobalLifecycleEvent). Обратное — ошибка сборки.

### 2.4. Почему action_class и action_name_pattern сосуществуют?

`action_class` фильтрует по **типу** — типобезопасно, покрывает иерархию наследования. `action_name_pattern` фильтрует по **строковому имени** — гибко, покрывает фильтрацию по модулю (`r"orders\..*"`). Это два разных юзкейса, и оба нужны.

### 2.5. Почему aspect_type реализован через классы событий, а не строковое поле?

Типы аспектов (`regular`, `summary`, `on_error`, `compensate`) имеют **разные параметры**: summary возвращает `BaseResult` [2], regular возвращает `dict`, on_error получает `Exception`. Объединять их в один класс с Optional-полями — та же проблема, от которой уходим. Каждый тип аспекта — свой класс события со своими полями.

### 2.6. Почему action_class и action_name хранятся вместе в событии?

`action_class: type[BaseAction]` — для типобезопасной фильтрации через `isinstance`. `action_name: str` — для шаблонов логирования `{%event.action_name}` [4], чтобы в логах было `"orders.CreateOrderAction"`, а не `"<class 'orders.CreateOrderAction'>"`.

### 2.7. Что такое predicate и какой тип event он получает?

`predicate` — произвольная функция фильтрации. Формальная аннотация — `Callable[[BasePluginEvent], bool]`. Фактический тип `event` в рантайме **гарантированно соответствует `event_class`** из того же декоратора, потому что `predicate` вызывается **после** проверки `isinstance(event, sub.event_class)`. Поэтому обращение к специфичным полям `event_class` в лямбде безопасно:

```python
@on(
    GlobalFinishEvent,
    predicate=lambda e: e.duration_ms > 1000,  # e — GlobalFinishEvent в рантайме
)
```

### 2.8. Проверка совместимости типов — когда выполняется?

Все проверки выполняются в `MetadataBuilder` при сборке метаданных плагина, **до обработки первого запроса** [18]. Это тот же паттерн, что используется для аспектов, чекеров, gate-hosts [5]. Нарушение любого правила — ошибка, приложение не запускается.

---

## 3. Иерархия классов событий

```
BasePluginEvent                              — корень, общие поля
├── GlobalLifecycleEvent                     — группа: start + finish
│   ├── GlobalStartEvent                     — старт конвейера
│   └── GlobalFinishEvent                    — финиш (+ result, duration_ms)
├── AspectEvent                              — группа: все аспектные события
│   ├── RegularAspectEvent                   — группа: regular-аспекты
│   │   ├── BeforeRegularAspectEvent         — перед regular
│   │   └── AfterRegularAspectEvent          — после regular (+ aspect_result)
│   ├── SummaryAspectEvent                   — группа: summary-аспекты
│   │   ├── BeforeSummaryAspectEvent         — перед summary
│   │   └── AfterSummaryAspectEvent          — после summary (+ result)
│   ├── OnErrorAspectEvent                   — группа: on_error аспекты
│   │   ├── BeforeOnErrorAspectEvent         — перед on_error (+ error)
│   │   └── AfterOnErrorAspectEvent          — после on_error (+ error, handler_result)
│   └── CompensateAspectEvent                — группа: compensate (будущее)
│       ├── BeforeCompensateAspectEvent      — перед compensate
│       └── AfterCompensateAspectEvent       — после compensate
├── ErrorEvent                               — группа: ошибки
│   └── UnhandledErrorEvent                  — ошибка без @on_error обработчика
└── (будущие группы)
```

### Что даёт иерархия

```python
@on(BasePluginEvent)           # все события
@on(AspectEvent)               # все before + after всех типов аспектов
@on(RegularAspectEvent)        # только before + after regular-аспектов
@on(AfterRegularAspectEvent)   # только after regular-аспектов
@on(GlobalLifecycleEvent)      # global_start + global_finish
@on(GlobalFinishEvent)         # только global_finish
```

### Базовые классы событий

`BasePluginEvent` содержит поля, общие для ВСЕХ событий:
- `action_class: type[BaseAction]` — тип действия (для фильтрации)
- `action_name: str` — строковое имя (для логирования [4])
- `nest_level: int` — уровень вложенности
- `context: Context` — контекст выполнения [2]
- `params: BaseSchema` — параметры действия [2]

`AspectEvent` добавляет:
- `aspect_name: str` — имя метода-аспекта

Каждый конкретный класс добавляет **только свои** поля.

---

## 4. Новый декоратор @on

### Полная сигнатура

```python
@on(
    event_class: type[BasePluginEvent],                            # обязательный
    *,
    action_class: type[BaseAction] | tuple[type[BaseAction], ...] | None = None,
    action_name_pattern: str | None = None,
    aspect_name_pattern: str | None = None,
    nest_level: int | tuple[int, ...] | None = None,
    domain: type | None = None,
    predicate: Callable[[BasePluginEvent], bool] | None = None,
    ignore_exceptions: bool = True,
)
```

### Параметры с примерами

```python
@on(
    GlobalFinishEvent,

    # action_class: фильтр по типу действия
    #   Путь: type(action) → isinstance(action, action_class)
    #   Варианты:
    #     action_class=OrderAction               — конкретный класс
    #     action_class=BaseOrderAction            — ветка иерархии (все наследники)
    #     action_class=(OrderAction, PaymentAction)  — любой из перечисленных
    #     None (по умолчанию)                     — любое действие
    action_class=OrderAction,

    # action_name_pattern: regex по полному имени действия
    #   Путь: action.get_full_class_name() → "orders.actions.CreateOrderAction"
    #   Варианты:
    #     r"orders\..*"                           — все действия модуля orders
    #     r".*Payment.*"                          — все с Payment в имени
    #     r"orders\.Create.*Action"               — Create*Action в orders
    #     None (по умолчанию)                     — без фильтрации по имени
    action_name_pattern=r"orders\..*",

    # aspect_name_pattern: regex по имени аспекта (только для AspectEvent)
    #   Путь: event.aspect_name → "validate_amount"
    #   Варианты:
    #     r"validate_.*"                          — все аспекты валидации
    #     r"process_payment"                      — конкретный аспект
    #     None (по умолчанию)                     — без фильтрации
    #   Ограничение: применим ТОЛЬКО к AspectEvent и наследникам.
    #   Для не-аспектных событий — ошибка сборки в MetadataBuilder.
    aspect_name_pattern=None,

    # nest_level: фильтр по уровню вложенности
    #   Путь: event.nest_level → 0, 1, 2, ...
    #   Варианты:
    #     nest_level=0                            — только корневые вызовы
    #     nest_level=(0, 1)                       — корневые и первый уровень
    #     None (по умолчанию)                     — любой уровень
    nest_level=0,

    # domain: фильтр по домену действия
    #   Путь: coordinator.get_metadata(action_class).meta.domain
    #   Варианты:
    #     domain=OrdersDomain                     — все действия домена заказов
    #     None (по умолчанию)                     — без фильтрации по домену
    domain=None,

    # predicate: произвольный фильтр по содержимому события
    #   Тип event: гарантированно GlobalFinishEvent (или наследник),
    #   потому что predicate вызывается ПОСЛЕ проверки isinstance(event, event_class).
    #   Варианты:
    #     lambda e: e.duration_ms > 1000          — только медленные (>1с)
    #     lambda e: e.result is not None          — только успешные
    #     None (по умолчанию)                     — без доп. фильтрации
    predicate=lambda e: e.duration_ms > 1000,

    # ignore_exceptions: подавление ошибок в обработчике
    #   True  — ошибка логируется, не прерывает выполнение
    #   False — ошибка пробрасывается наружу
    ignore_exceptions=True,
)
async def on_slow_order_finish(self, state, event: GlobalFinishEvent, log):
    ...
```

---

## 5. Порядок проверки фильтров при эмиссии события

Когда `PluginRunContext.emit_event()` [17] получает событие, он обходит все подписки всех плагинов и для каждой подписки проверяет, нужно ли вызывать обработчик. Фильтры проверяются **последовательно**, от самого дешёвого к самому дорогому. Ранний выход на первом несовпадении — дорогие проверки не выполняются, если дешёвая уже отсекла подписку.

```
Событие приходит в emit_event()
         │
         ▼
Шаг 1: isinstance(event, sub.event_class)?
         │  Дешёвая проверка — одна инструкция isinstance.
         │  Отсекает ~90% подписок сразу, потому что большинство
         │  плагинов подписаны на конкретные типы событий.
         │  НЕТ → пропускаем обработчик
         │
         ▼
Шаг 2: action_class указан? → isinstance(action, sub.action_class)?
         │  Дешёвая проверка — isinstance.
         │  Отсекает подписки, ограниченные конкретными действиями.
         │  НЕТ → пропускаем
         │
         ▼
Шаг 3: action_name_pattern указан? → re.search(pattern, event.action_name)?
         │  Дороже — компиляция и выполнение regex.
         │  Фильтрация по модулю или паттерну имени.
         │  НЕТ → пропускаем
         │
         ▼
Шаг 4: aspect_name_pattern указан? → re.search(pattern, event.aspect_name)?
         │  Применяется только к AspectEvent и наследникам.
         │  Для не-аспектных событий пропускается.
         │  НЕТ → пропускаем
         │
         ▼
Шаг 5: nest_level указан? → event.nest_level in sub.nest_level?
         │  Дешёвая проверка — сравнение int или in tuple.
         │  НЕТ → пропускаем
         │
         ▼
Шаг 6: domain указан? → проверка через координатор метаданных
         │  Дороже — обращение к GateCoordinator.get_metadata().
         │  НЕТ → пропускаем
         │
         ▼
Шаг 7: predicate указан? → predicate(event)?
         │  Самая дорогая — произвольная пользовательская функция.
         │  К моменту вызова гарантировано: isinstance(event, event_class).
         │  Обращение к специфичным полям event_class безопасно.
         │  НЕТ → пропускаем
         │
         ▼
ВСЕ ФИЛЬТРЫ ПРОШЛИ → вызываем обработчик
```

---

## 6. План изменений по файлам

### Новые файлы

| Файл | Назначение |
|---|---|
| `plugins/events.py` | Иерархия классов событий (BasePluginEvent → конкретные) |
| `plugins/subscription_info.py` | Frozen dataclass SubscriptionInfo с новыми фильтрами |

### Изменяемые файлы

| Файл | Что меняется |
|---|---|
| `plugins/decorators.py` [15] | `@on` — новая сигнатура с `event_class`, `action_class`, `action_name_pattern`, `aspect_name_pattern`, `nest_level`, `domain`, `predicate` |
| `plugins/plugin.py` [14] | `get_handlers()` — работа с типами вместо строк |
| `plugins/plugin_run_context.py` [17] | `emit_event()` — принимает объект события вместо набора параметров, цепочка фильтров |
| `plugins/plugin_coordinator.py` [18] | Минимальные изменения — типы в сигнатурах |
| `plugins/on_gate_host.py` [16] | Обновление docstring |
| `plugins/__init__.py` [5] | Реэкспорт новых классов |
| `metadata/collectors.py` | Сбор SubscriptionInfo с новыми полями |
| `metadata/validators.py` | Проверки совместимости: event_class ↔ аннотация, aspect_name_pattern только для AspectEvent, regex-валидация |
| `core/action_product_machine.py` | Создание конкретных объектов событий вместо строк |

### Удаляемые файлы

| Файл | Причина |
|---|---|
| `plugins/plugin_event.py` [13] | Заменён иерархией в `plugins/events.py` |

---

## 7. План тестирования

### 7.1. Существующие тесты (обновление)

Все существующие тесты адаптируются к новому API. Строковые `event_type` и `action_filter` заменяются на классы событий и `action_class`.

| Файл | Что покрывает | Изменения |
|---|---|---|
| `tests/plugins/conftest.py` [19] | Тестовые плагины, фикстуры | Переписать плагины с `@on(EventClass)` вместо `@on("event_name")`, `emit_global_finish()` передаёт объект `GlobalFinishEvent` |
| `tests/plugins/test_find_plugin.py` [23] | `get_handlers()` — поиск обработчиков | Фильтрация по `isinstance` вместо строкового сравнения |
| `tests/plugins/test_handlers.py` [24] | Выполнение обработчиков, per-request state | Обработчики получают конкретные типы событий |
| `tests/plugins/test_emit.py` [21] | `emit_event()` — доставка событий | `emit_event()` принимает объект события |
| `tests/plugins/test_exceptions.py` [22] | `ignore_exceptions` True/False | Без существенных изменений, сигнатура сохраняется |
| `tests/plugins/test_concurrency.py` [20] | Параллельное/последовательное выполнение | Без существенных изменений |
| `tests/plugins/test_plugins_integration.py` [25] | Интеграция с полным конвейером | Плагины используют новый API, машина создаёт объекты событий |

### 7.2. Новые тесты

| Файл | Что покрывает |
|---|---|
| `tests/plugins/test_event_hierarchy.py` | Иерархия событий: isinstance-проверки, поля конкретных классов, frozen-семантика, наследование полей |
| `tests/plugins/test_filter_chain.py` | Цепочка фильтров: каждый фильтр отдельно, комбинации фильтров, AND-логика, ранний выход |
| `tests/plugins/test_action_class_filter.py` | `action_class`: конкретный класс, иерархия, кортеж, None |
| `tests/plugins/test_action_name_pattern.py` | `action_name_pattern`: regex по модулю, по имени, невалидный regex → ошибка сборки |
| `tests/plugins/test_aspect_name_pattern.py` | `aspect_name_pattern`: regex по имени аспекта, применение только к AspectEvent, ошибка для не-аспектных событий |
| `tests/plugins/test_nest_level_filter.py` | `nest_level`: конкретный уровень, кортеж, None |
| `tests/plugins/test_domain_filter.py` | `domain`: фильтрация по домену через координатор |
| `tests/plugins/test_predicate_filter.py` | `predicate`: лямбда-фильтр, типизация event, None |
| `tests/plugins/test_multiple_on.py` | Несколько `@on` на одном методе: OR-семантика |
| `tests/plugins/test_event_annotation_check.py` | Проверка MetadataBuilder: совместимость event_class ↔ аннотация, ошибки сборки |
| `tests/plugins/test_concrete_event_typing.py` | Конкретная аннотация event: доступ к специфичным полям без isinstance |

### 7.3. Детализация ключевых тестов

#### `test_event_hierarchy.py`

```python
class TestEventInheritance:
    """isinstance-проверки по иерархии."""
    def test_global_finish_is_lifecycle(self): ...
    def test_global_finish_is_base(self): ...
    def test_after_regular_is_aspect(self): ...
    def test_after_summary_is_not_regular(self): ...

class TestEventFields:
    """Каждый класс содержит ровно свои поля."""
    def test_global_start_no_result_field(self): ...
    def test_global_finish_has_result_and_duration(self): ...
    def test_after_regular_has_aspect_result(self): ...
    def test_after_summary_has_result(self): ...
    def test_on_error_has_error_field(self): ...

class TestEventFrozen:
    """Все события неизменяемы."""
    def test_cannot_modify_global_finish(self): ...
    def test_cannot_add_field(self): ...
```

#### `test_filter_chain.py`

```python
class TestFilterChainAND:
    """Все фильтры должны пройти одновременно."""
    def test_event_class_and_action_class(self): ...
    def test_event_class_and_action_name_pattern(self): ...
    def test_all_filters_pass(self): ...
    def test_one_filter_fails_blocks_handler(self): ...

class TestFilterChainEarlyExit:
    """Ранний выход: дорогие проверки не выполняются."""
    def test_event_class_mismatch_skips_predicate(self): ...
    def test_action_class_mismatch_skips_regex(self): ...

class TestORBetweenMultipleOn:
    """Несколько @on на одном методе — OR-семантика."""
    def test_handler_called_for_either_event(self): ...
    def test_handler_not_called_for_unsubscribed_event(self): ...
```

#### `test_event_annotation_check.py`

```python
class TestAnnotationCompatibility:
    """MetadataBuilder проверяет совместимость при сборке."""
    def test_concrete_annotation_matches_event_class(self): ...
    def test_parent_annotation_accepts_child_event_class(self): ...
    def test_child_annotation_rejects_parent_event_class(self): ...
    def test_missing_annotation_defaults_to_base(self): ...

class TestAspectPatternRestriction:
    """aspect_name_pattern только для AspectEvent."""
    def test_aspect_pattern_on_global_event_raises(self): ...
    def test_aspect_pattern_on_aspect_event_ok(self): ...

class TestRegexValidation:
    """Невалидные regex обнаруживаются при сборке."""
    def test_invalid_action_name_pattern_raises(self): ...
    def test_invalid_aspect_name_pattern_raises(self): ...
```

---

## 8. Порядок реализации

### Этап 1: Фундамент (без ломающих изменений)

| Шаг | Файл | Действие |
|---|---|---|
| 1.1 | `plugins/events.py` | Создать иерархию классов событий |
| 1.2 | `plugins/subscription_info.py` | Создать новый SubscriptionInfo с расширенными фильтрами |
| 1.3 | `tests/plugins/test_event_hierarchy.py` | Написать и прогнать тесты иерархии |

### Этап 2: Декоратор и MetadataBuilder

| Шаг | Файл | Действие |
|---|---|---|
| 2.1 | `plugins/decorators.py` | Переписать `@on` с новой сигнатурой |
| 2.2 | `metadata/validators.py` | Добавить проверки совместимости |
| 2.3 | `metadata/collectors.py` | Обновить сбор SubscriptionInfo |
| 2.4 | `tests/plugins/test_event_annotation_check.py` | Тесты проверок при сборке |

### Этап 3: Эмиссия и фильтрация

| Шаг | Файл | Действие |
|---|---|---|
| 3.1 | `plugins/plugin.py` | Обновить `get_handlers()` |
| 3.2 | `plugins/plugin_run_context.py` | Переписать `emit_event()` с цепочкой фильтров |
| 3.3 | `tests/plugins/test_filter_chain.py` | Тесты цепочки фильтров |
| 3.4 | `tests/plugins/test_action_class_filter.py` | Тесты action_class |
| 3.5 | `tests/plugins/test_action_name_pattern.py` | Тесты action_name_pattern |
| 3.6 | `tests/plugins/test_aspect_name_pattern.py` | Тесты aspect_name_pattern |
| 3.7 | `tests/plugins/test_nest_level_filter.py` | Тесты nest_level |
| 3.8 | `tests/plugins/test_domain_filter.py` | Тесты domain |
| 3.9 | `tests/plugins/test_predicate_filter.py` | Тесты predicate |

### Этап 4: Интеграция с машиной

| Шаг | Файл | Действие |
|---|---|---|
| 4.1 | `core/action_product_machine.py` | Создание конкретных объектов событий |
| 4.2 | Удалить `plugins/plugin_event.py` | Заменён на `events.py` |

### Этап 5: Обновление существующих тестов

| Шаг | Файл | Действие |
|---|---|---|
| 5.1 | `tests/plugins/conftest.py` | Обновить тестовые плагины и фикстуры |
| 5.2 | `tests/plugins/test_find_plugin.py` | Адаптировать к новому API |
| 5.3 | `tests/plugins/test_handlers.py` | Адаптировать |
| 5.4 | `tests/plugins/test_emit.py` | Адаптировать |
| 5.5 | `tests/plugins/test_exceptions.py` | Адаптировать |
| 5.6 | `tests/plugins/test_concurrency.py` | Адаптировать |
| 5.7 | `tests/plugins/test_plugins_integration.py` | Адаптировать |
| 5.8 | `tests/plugins/test_multiple_on.py` | Новый тест: несколько @on |
| 5.9 | `tests/plugins/test_concrete_event_typing.py` | Новый тест: конкретная аннотация |

### Этап 6: Финализация

| Шаг | Файл | Действие |
|---|---|---|
| 6.1 | `plugins/__init__.py` | Обновить реэкспорт |
| 6.2 | `plugins/on_gate_host.py` | Обновить docstring |
| 6.3 | Полный прогон тестов | `pytest tests/plugins/ -v` |
| 6.4 | Интеграционный прогон | `pytest tests/ -v` |