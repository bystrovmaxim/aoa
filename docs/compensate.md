````markdown
# Полный подробный план внедрения компенсации (Sagas) в ActionMachine — v5
> **Цель документа:** служить одновременно планом реализации и источником для документации в комментариях кода. Каждое архитектурное решение содержит обоснование, которое должно быть перенесено в docstring или комментарий соответствующего модуля.
---
## Преамбула
### Что такое компенсация
В распределённых транзакциях и длительных бизнес-процессах часто невозможно использовать двухфазный коммит. Вместо этого применяется паттерн **Saga**: каждая операция имеет компенсирующую операцию, которая отменяет её эффекты. При сбое на любом шаге выполняются компенсации уже выполненных операций **в обратном порядке**.
ActionMachine изначально поддерживает конвейер регулярных аспектов. Если на каком-то шаге возникает ошибка, вся предыдущая работа не откатывается. Компенсация заполняет этот пробел.
### Цель
Добавить в ActionMachine механизм, позволяющий объявить для каждого регулярного аспекта метод-компенсатор. При возникновении ошибки в любом аспекте все успешно выполненные аспекты будут откачены в обратном порядке. После отката вызывается штатный обработчик `@on_error`.
### Область действия
- Компенсаторы определяются только для **регулярных аспектов** (не для summary).
- Компенсаторы могут использовать `@context_requires`.
- Каждый уровень вложенности имеет **свой стек** — глобального стека нет.
- Компенсаторы **не наследуются** — собираются из `vars(cls)`.
- Ошибки в компенсаторах **молчаливые** — не прерывают размотку и не пробрасываются.
- При `rollup=True` компенсаторы **не вызываются**.
---
## Архитектурное решение №1: Почему ошибки компенсаторов молчаливые
```
# ── Архитектурное решение: молчаливые ошибки компенсаторов ──
#
# Компенсатор — это код отката, выполняющийся в аварийной ситуации.
# Если ошибка компенсатора пробрасывается, возникают два последствия:
#
# 1. ЛОМАЕТСЯ РАЗМОТКА СТЕКА.
#    Если rollback_payment_compensate бросил исключение, то
#    rollback_inventory_compensate (следующий в стеке) НИКОГДА не вызовется.
#    Товар зарезервирован, деньги не списаны — система в неконсистентном
#    состоянии, хуже, чем без компенсации вообще.
#
# 2. НАРУШАЕТСЯ ЛОГИКА @on_error.
#    Обработчики ошибок спроектированы для бизнес-ошибок аспектов —
#    ValueError из валидации, PaymentDeclinedError из платёжного шлюза.
#    Если вместо бизнес-ошибки @on_error получит CompensationFailedError,
#    он не будет знать, что с ней делать. Смешивание ошибок компенсации
#    с ошибками бизнес-логики разрушает контракт @on_error.
#
# РЕШЕНИЕ: ошибки компенсаторов полностью подавляются внутри _rollback_saga().
# Вместо проброса используется типизированное событие плагинов
# CompensateFailedEvent, на которое плагин мониторинга может подписаться.
# Это тот же паттерн, что ignore_exceptions=True в плагинах — ошибка
# не ломает основной поток, но информация о ней доступна наблюдателям.
```
### Ответственность разработчика: устойчивый компенсатор
```
# ── Ответственность разработчика ──
#
# Фреймворк гарантирует, что ошибка компенсатора не сломает размотку.
# Но фреймворк НЕ гарантирует, что откат произойдёт успешно — это
# ответственность разработчика.
#
# Компенсатор работает в аварийной ситуации: внешние сервисы могут быть
# недоступны, база может не отвечать, сеть может быть нестабильна.
#
# Рекомендации:
# 1. Оборачивать тело компенсатора в try/except
# 2. Делать компенсатор идемпотентным (безопасным для повторного вызова)
# 3. Логировать через box.log, а не полагаться только на плагины
# 4. Не рассчитывать на успешность отката — это best-effort механизм
```
**Пример правильного компенсатора:**
```python
@compensate("process_payment_aspect", "Откат платежа")
async def rollback_payment_compensate(self, params, state_before, state_after, box, connections, error):
    """
    Компенсатор для process_payment_aspect.
    Архитектурное решение: тело обёрнуто в try/except, потому что
    компенсатор выполняется в аварийной ситуации — внешний сервис
    может быть недоступен. Фреймворк подавит ошибку в любом случае,
    но детальное логирование с бизнес-контекстом (txn_id) возможно
    только здесь, внутри компенсатора.
    """
    try:
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])
    except PaymentServiceUnavailable:
        await box.log.error(
            "Не удалось откатить платёж {%var.txn}: сервис недоступен",
            txn=state_after["txn_id"],
        )
    except Exception as e:
        await box.log.error(
            "Неожиданная ошибка отката платежа: {%var.err}",
            err=str(e),
        )
```
---
## Архитектурное решение №2: Вложенные вызовы и `try/catch`
```
# ── Архитектурное решение: локальные стеки вложенных вызовов ──
#
# Каждый _run_internal создаёт СВОЙ локальный стек. Глобального стека нет.
#
# Если аспект родительского Action вызывает box.run(ChildAction)
# и оборачивает вызов в try/except:
#
#   - Дочерний _run_internal(ExternalAction) разматывает СВОЙ стек
#     и пробрасывает исключение.
#   - Родительский аспект ПЕРЕХВАТЫВАЕТ исключение — для родителя
#     аспект ЗАВЕРШИЛСЯ УСПЕШНО (вернул dict).
#   - Родительский аспект ДОБАВЛЯЕТСЯ в стек родителя.
#   - Если позже другой аспект родителя упадёт — этот аспект будет
#     откачен компенсатором.
#
# Это корректное поведение: разработчик, написавший try/except, взял
# ответственность за обработку ошибки дочернего действия. Компенсация
# дочернего стека уже произошла внутри дочернего _run_internal.
# Родительский стек откатывает только то, что успешно выполнилось
# на уровне родителя.
```
---
## Архитектурное решение №3: Проверка при инициализации системы
```
# ── Архитектурное решение: fail-fast при сборке метаданных ──
#
# Все инварианты компенсаторов проверяются координатором ПРИ СБОРКЕ
# МЕТАДАННЫХ, до обработки первого запроса.
#
# MetadataBuilder.build() вызывается из GateCoordinator.get() при
# первом обращении к классу. Все валидации (привязка к аспекту,
# уникальность, сигнатура, суффикс) выполняются в этой фазе —
# аналогично validate_aspects(), validate_checkers_belong_to_aspects(),
# validate_subscriptions().
#
# Приложение НЕ ЗАПУСТИТСЯ при нарушении любого инварианта.
# Это исключает класс ошибок "компенсатор привязан к несуществующему
# аспекту" в runtime.
```
---
## 1. Датакласс `CompensatorMeta`
В `core/class_metadata.py`:
```python
@dataclass(frozen=True)
class CompensatorMeta:
    """
    Метаданные компенсатора.
    Архитектурное решение: паттерн повторяет AspectMeta и OnErrorMeta —
    frozen-датакласс с method_ref для вызова и context_keys для
    интеграции с @context_requires. Единообразие структур метаданных
    упрощает код коллекторов и валидаторов.
    """
    method_name: str                    # имя метода-компенсатора
    target_aspect_name: str             # имя целевого regular-аспекта
    description: str                    # текстовое описание
    method_ref: Callable                # ссылка на метод
    context_keys: frozenset[str]        # из @context_requires
```
---
## 2. Изменения в `ClassMetadata`
```python
# ── Архитектурное решение: хелперы вместо прямого доступа ──
#
# get_compensator_for_aspect() — O(n) поиск по tuple.
# Это приемлемо, потому что количество компенсаторов в одном Action
# обычно 1-5 (по числу regular-аспектов с побочными эффектами).
# Паттерн аналогичен get_checkers_for_aspect(method_name).
compensators: tuple[CompensatorMeta, ...] = ()
def has_compensators(self) -> bool:
    return len(self.compensators) > 0
def get_compensator_for_aspect(self, aspect_name: str) -> CompensatorMeta | None:
    for comp in self.compensators:
        if comp.target_aspect_name == aspect_name:
            return comp
    return None
```
---
## 3. Декоратор `@compensate`
Файл `src/action_machine/compensate/compensate_decorator.py`.
```
# ── Архитектурное решение: привязка по строковому имени ──
#
# @compensate(target_aspect_name: str, description: str)
#
# Первый аргумент — СТРОКОВОЕ ИМЯ метода-аспекта, а не ссылка на объект.
# Это устраняет зависимость от порядка определения методов в классе.
# Паттерн аналогичен привязке чекеров к аспектам по method_name.
#
# Валидация привязки (существует ли такой аспект, является ли он regular)
# происходит в MetadataBuilder.build(), а не в декораторе — на этапе
# декорирования класс ещё не полностью определён.
```
### Валидации декоратора (выполняются при определении класса)
- `target_aspect_name` — непустая строка.
- `description` — непустая строка.
- Метод — `async def`.
- Имя метода заканчивается на `_compensate`.
- Количество параметров: 7 без `@context_requires`, 8 с `@context_requires`.
### Записываемый атрибут
```python
func._compensate_meta = {
    "target_aspect_name": target_aspect_name,
    "description": description,
}
```
---
## 4. Сигнатура компенсатора
```
# ── Архитектурное решение: сигнатура компенсатора ──
#
# Компенсатор получает ДВА состояния: state_before и state_after.
#
# state_before — состояние ДО выполнения аспекта.
# state_after  — состояние ПОСЛЕ аспекта (или None, если чекер отклонил).
#
# Почему два, а не одно:
# - state_after содержит данные, необходимые для отката (txn_id платежа,
#   id созданной записи). Без него компенсатор не знает, ЧТО откатывать.
# - state_before нужен для восстановления: если компенсатор должен
#   вернуть значение в прежнее состояние, ему нужно знать, каким оно было.
# - state_after=None сигнализирует: "аспект выполнился, но чекер отклонил
#   результат — побочный эффект МОГ произойти, но state не обновился".
#
# error — исключение, вызвавшее размотку. Позволяет компенсатору
# адаптировать стратегию отката в зависимости от типа ошибки.
#
# Возвращаемое значение ИГНОРИРУЕТСЯ — компенсатор выполняет побочные
# эффекты (откат платежа, удаление записи), а не обновляет state.
```
**Без `@context_requires`** (7 параметров):
```python
async def rollback_payment_compensate(
    self, params, state_before, state_after, box, connections, error
)
```
**С `@context_requires`** (8 параметров):
```python
async def rollback_payment_compensate(
    self, params, state_before, state_after, box, connections, error, ctx
)
```
| Параметр | Тип | Описание |
|---|---|---|
| `params` | `BaseParams` | Входные параметры действия (frozen) |
| `state_before` | `BaseState` | Состояние **до** выполнения аспекта (frozen) |
| `state_after` | `BaseState \| None` | Состояние **после** аспекта. `None` если чекер отклонил |
| `box` | `ToolsBox` | Тот же ToolsBox |
| `connections` | `dict` | Словарь ресурсных менеджеров |
| `error` | `Exception` | Исключение, вызвавшее размотку |
| `ctx` | `ContextView` | Только при `@context_requires` |
---
## 5. `SagaFrame` — фрейм стека компенсации
```python
@dataclass(frozen=True)
class SagaFrame:
    """
    Фрейм стека компенсации.
    Архитектурное решение: только 4 поля.
    params, connections, context, box — ОБЩИЕ для всего конвейера
    одного _run_internal. Они не меняются между аспектами. Хранить их
    в каждом фрейме — дублирование. Они передаются в _rollback_saga()
    как аргументы.
    Уникальное для каждого фрейма:
    - state_before — состояние до ЭТОГО КОНКРЕТНОГО аспекта
    - state_after  — состояние после ЭТОГО КОНКРЕТНОГО аспекта (или None)
    - compensator  — компенсатор ЭТОГО КОНКРЕТНОГО аспекта (или None)
    - aspect_name  — для диагностики и событий плагинов
    """
    compensator: CompensatorMeta | None
    aspect_name: str
    state_before: BaseState
    state_after: BaseState | None
```
---
## 6. Сборка в `MetadataBuilder`
### Коллектор
```
# ── Архитектурное решение: vars(cls), а не inspect.getmembers ──
#
# Компенсаторы НЕ НАСЛЕДУЮТСЯ. Обходим vars(cls), а не mro.
# Если родительский Action определил компенсатор, дочерний его не получит.
#
# Обоснование: компенсатор жёстко привязан к конкретному аспекту
# конкретного класса. При наследовании аспекты могут переопределяться,
# добавляться, удаляться — унаследованный компенсатор может ссылаться
# на несуществующий или изменённый аспект. Явное переопределение
# безопаснее неявного наследования.
```
В `metadata/collectors.py`:
```python
def collect_compensators(cls: type) -> list[CompensatorMeta]:
    """Собирает компенсаторы из vars(cls) — без наследования."""
```
### Валидатор
В `metadata/validators.py`:
```python
def validate_compensators(
    cls: type,
    compensators: list[CompensatorMeta],
    aspects: list[AspectMeta],
) -> None:
    """
    Проверки при сборке метаданных (до первого запроса):
    1. ПРИВЯЗКА К СУЩЕСТВУЮЩЕМУ АСПЕКТУ:
       target_aspect_name совпадает с method_name одного из аспектов.
       Аналог validate_checkers_belong_to_aspects.
    2. ТОЛЬКО REGULAR-АСПЕКТЫ:
       Целевой аспект имеет aspect_type == "regular".
       Компенсаторы для summary запрещены — summary формирует итоговый
       Result и не выполняет побочных эффектов, требующих отката.
    3. УНИКАЛЬНОСТЬ:
       Для одного аспекта — не более одного компенсатора.
       Дубли → ValueError при сборке.
    4. GateHost НЕ НУЖЕН ОТДЕЛЬНЫЙ:
       Компенсаторы работают в контексте Action, который уже наследует
       AspectGateHost. Отдельный CompensateGateHost избыточен.
    """
```
### Интеграция в `build()`
```
# ── Порядок валидации в build() после добавления ──
#
# 1. validate_meta_required
# 2. validate_gate_hosts
# 3. validate_aspects
# 4. validate_checkers_belong_to_aspects
# 5. validate_error_handlers
# 6. validate_compensators          ← НОВЫЙ ШАГ
# 7. validate_subscriptions
# 8. validate_described_fields
#
# Компенсаторы валидируются ПОСЛЕ аспектов и чекеров, но ПЕРЕД
# подписками — потому что зависят от уже собранных aspects.
```
---
## 7. Граф в `GateCoordinator`
```
# ── Архитектурное решение: компенсаторы как leaf-узлы графа ──
#
# Новый тип узла "compensator", новый тип ребра "has_compensator".
# Leaf-ребро — без проверки ацикличности.
#
# Компенсатор — терминальный узел: он не вызывает другие Action
# (хотя технически может через box.run, это антипаттерн).
# Поэтому ребро leaf — оно не участвует в проверке циклов графа.
```
В `_populate_graph()` после секции обработчиков ошибок:
```python
for comp_meta in metadata.compensators:
    comp_name = f"{class_name}.{comp_meta.method_name}"
    comp_idx = self._ensure_node(
        "compensator", comp_name,
        meta={
            "target_aspect": comp_meta.target_aspect_name,
            "description": comp_meta.description,
            "method_name": comp_meta.method_name,
        },
    )
    self._add_leaf_edge(class_idx, comp_idx, "has_compensator")
    for ctx_key in sorted(comp_meta.context_keys):
        field_idx = self._ensure_node(
            "context_field", ctx_key, meta={"path": ctx_key},
        )
        self._add_leaf_edge(comp_idx, field_idx, "requires_context")
```
---
## 8. Типизированные события плагинов
```
# ── Архитектурное решение: пять типов событий компенсации ──
#
# Уровень ВСЕЙ РАЗМОТКИ (saga-level):
# SagaRollbackStartedEvent   — начало размотки стека
# SagaRollbackCompletedEvent — конец размотки (с итогами)
#
# Уровень ОДНОГО КОМПЕНСАТОРА (compensator-level):
# BeforeCompensateAspectEvent — перед каждым компенсатором
# AfterCompensateAspectEvent  — после успешного компенсатора
# CompensateFailedEvent       — сбой компенсатора
#
# Почему ДВА УРОВНЯ:
# Плагину мониторинга нужны оба. Compensator-level даёт детали
# каждого отдельного отката. Saga-level даёт общую картину:
# "размотка началась с 4 фреймами, завершилась: 3 успешно, 1 сбой".
# Без saga-level плагин вынужден самостоятельно агрегировать
# compensator-level события и отслеживать границы размотки —
# это ненужная сложность в плагине.
#
# Почему CompensateFailedEvent — ОТДЕЛЬНЫЙ тип:
# Это аварийная ситуация, на которую плагин мониторинга реагирует
# ИНАЧЕ, чем на успешную компенсацию. Отдельный тип позволяет
# подписаться точечно: @on(CompensateFailedEvent) — только сбои,
# без потока успешных откатов.
#
# Иерархия подписки:
# @on(SagaRollbackStartedEvent)    — начало размотки
# @on(SagaRollbackCompletedEvent)  — конец размотки
# @on(CompensateFailedEvent)       — только сбои компенсаторов
# @on(BeforeCompensateAspectEvent) — перед каждым компенсатором
# @on(AfterCompensateAspectEvent)  — после успешного
# @on(SagaEvent)                   — все saga-события (группа)
# @on(CompensateAspectEvent)       — все события отдельных компенсаторов (группа)
# @on(AspectEvent)                 — все аспектные события включая компенсацию
```
### `SagaRollbackStartedEvent`
```python
@dataclass(frozen=True)
class SagaRollbackStartedEvent(SagaEvent):
    """
    Эмитируется ОДИН РАЗ перед началом размотки стека компенсации.
    Позволяет плагину мониторинга зафиксировать момент начала отката,
    количество фреймов, которые будут обработаны, и исключение-причину.
    """
    error: Exception                    # исключение, вызвавшее размотку
    stack_depth: int                    # количество фреймов в стеке
    compensator_count: int              # количество фреймов С компенсаторами
    aspect_names: tuple[str, ...]       # имена аспектов в стеке (в порядке размотки)
```
### `SagaRollbackCompletedEvent`
```python
@dataclass(frozen=True)
class SagaRollbackCompletedEvent(SagaEvent):
    """
    Эмитируется ОДИН РАЗ после завершения размотки стека компенсации.
    Содержит итоги: сколько компенсаторов выполнено успешно, сколько
    упало, сколько фреймов было без компенсатора (пропущено).
    Позволяет плагину мониторинга:
    - Замерить общую длительность размотки
    - Оценить успешность отката (succeeded vs failed)
    - Выявить аспекты без компенсаторов (skipped)
    """
    error: Exception                    # исключение, вызвавшее размотку
    total_frames: int                   # общее количество фреймов в стеке
    succeeded: int                      # компенсаторы, выполненные успешно
    failed: int                         # компенсаторы, завершившиеся ошибкой
    skipped: int                        # фреймы без компенсатора (пропущены)
    duration_ms: float                  # общая длительность размотки
    failed_aspects: tuple[str, ...]     # имена аспектов, чьи компенсаторы упали
```
### `BeforeCompensateAspectEvent`
```python
@dataclass(frozen=True)
class BeforeCompensateAspectEvent(CompensateAspectEvent):
    error: Exception
    compensator_name: str
    state_before: BaseState
    state_after: BaseState | None
```
### `AfterCompensateAspectEvent`
```python
@dataclass(frozen=True)
class AfterCompensateAspectEvent(CompensateAspectEvent):
    error: Exception
    compensator_name: str
    duration_ms: float
```
### `CompensateFailedEvent`
```python
@dataclass(frozen=True)
class CompensateFailedEvent(CompensateAspectEvent):
    original_error: Exception
    compensator_error: Exception
    compensator_name: str
    failed_for_aspect: str
```
---
## 9. Стек компенсации в `_execute_regular_aspects`
```
# ── Архитектурное решение: когда фрейм добавляется/не добавляется ──
#
# ДОБАВЛЯЕТСЯ (state_after=new_state):
#   Аспект вернул dict, чекеры пройдены, новый state создан.
#   Побочный эффект ТОЧНО выполнен — нужна компенсация.
#
# ДОБАВЛЯЕТСЯ (state_after=None):
#   Аспект вернул dict, но чекер ОТКЛОНИЛ результат.
#   Побочный эффект МОГ быть выполнен (HTTP-запрос к платёжному
#   шлюзу уже отправлен). state_after=None сигнализирует компенсатору:
#   "результат невалиден, но побочный эффект мог произойти".
#
# НЕ ДОБАВЛЯЕТСЯ:
#   Аспект бросил исключение до возврата dict.
#   Побочный эффект не гарантирован (исключение могло произойти
#   до вызова внешнего сервиса). Фрейм не добавляется.
#
# ── Архитектурное решение: взаимодействие с rollup=True ──
#
# Если box.rollup is True — стек НЕ СОЗДАЁТСЯ, компенсаторы
# НЕ ВЫЗЫВАЮТСЯ. В rollup-режиме транзакционный откат выполняется
# на уровне connections через WrapperConnectionManager.
# Компенсация предназначена для нетранзакционных побочных эффектов
# в production-режиме.
```
### Возврат стека
```
# ── Архитектурное решение: возврат кортежа ──
#
# _execute_regular_aspects возвращает (state, saga_stack) вместо
# одного state. Это позволяет _execute_aspects_with_error_handling
# использовать стек при перехвате исключения.
#
# Альтернатива (хранение стека в атрибуте self) отвергнута:
# при вложенных вызовах один экземпляр машины может обрабатывать
# несколько _run_internal параллельно — атрибут создаёт гонку.
```
---
## 10. Размотка стека `_rollback_saga()`
```python
async def _rollback_saga(
    self,
    saga_stack: list[SagaFrame],
    error: Exception,
    action: BaseAction,
    params: BaseParams,
    box: ToolsBox,
    connections: dict[str, BaseResourceManager],
    context: Context,
    plugin_ctx: PluginRunContext,
) -> None:
    """
    Размотка стека компенсации в обратном порядке.
    Архитектурное решение: метод НИКОГДА не бросает исключение.
    Ошибки компенсаторов подавляются и эмитируются как
    CompensateFailedEvent. Это гарантирует, что:
    1. Все компенсаторы в стеке получат шанс выполниться.
    2. После размотки управление вернётся к @on_error.
    3. @on_error получит ОРИГИНАЛЬНУЮ ошибку аспекта, а не ошибку
       компенсатора.
    """
```
### Алгоритм
```
# ── Эмитировать SagaRollbackStartedEvent ──
#     stack_depth = len(saga_stack)
#     compensator_count = количество фреймов с compensator is not None
#     aspect_names = tuple(frame.aspect_name for frame in reversed(saga_stack))
#
# ── Инициализировать счётчики ──
#     succeeded = 0
#     failed = 0
#     skipped = 0
#     failed_aspects = []
#     start_time = time.perf_counter()
#
# Для каждого фрейма в saga_stack (в ОБРАТНОМ порядке):
#     │
#     ├── Фрейм без компенсатора → skipped += 1, пропуск
#     │
#     ├── Эмитировать BeforeCompensateAspectEvent
#     │
#     ├── Создать ScopedLogger для компенсатора
#     │
#     ├── Если compensator.context_keys → создать ContextView
#     │
#     ├── try:
#     │       Вызвать компенсатор(action, params, frame.state_before,
#     │                           frame.state_after, box, connections,
#     │                           error[, ctx])
#     │       Замерить duration
#     │       Эмитировать AfterCompensateAspectEvent
#     │       succeeded += 1
#     │   except Exception as comp_error:
#     │       Эмитировать CompensateFailedEvent
#     │       failed += 1
#     │       failed_aspects.append(frame.aspect_name)
#     │       (размотка ПРОДОЛЖАЕТСЯ)
#     │
#     └── Следующий фрейм
#
# ── Эмитировать SagaRollbackCompletedEvent ──
#     duration_ms = (time.perf_counter() - start_time) * 1000
#     total_frames = stack_depth
#     succeeded, failed, skipped, failed_aspects
```
---
## 11. Порядок: компенсаторы → `@on_error`
```
# ── Архитектурное решение: порядок обработки ошибки ──
#
# 1. Аспект бросает исключение
# 2. Фрейм для упавшего аспекта НЕ добавляется в стек
# 3. _rollback_saga(saga_stack, error) — размотка в обратном порядке
# 4. После завершения размотки → _handle_aspect_error(error, ...)
#    4a. Если @on_error найден → вызов обработчика
#    4b. Если @on_error не найден → raise
#
# Обоснование порядка:
# Компенсаторы ОТКАТЫВАЮТ побочные эффекты — приводят систему в
# консистентное состояние. @on_error ОБРАБАТЫВАЕТ бизнес-логику —
# формирует ответ пользователю, логирует бизнес-событие.
# Сначала откат, потом обработка — иначе @on_error работает
# с неконсистентными данными.
```
---
## 12. Изменения в `_execute_aspects_with_error_handling`
```python
async def _execute_aspects_with_error_handling(self, ...):
    """
    Архитектурное решение: saga_stack объявляется ДО try-блока,
    чтобы быть доступным в except. Если _execute_regular_aspects
    бросит исключение на N-м аспекте, saga_stack будет содержать
    фреймы первых (N-1) успешных аспектов.
    """
    saga_stack: list[SagaFrame] = []
    try:
        state, saga_stack = await self._execute_regular_aspects(...)
        # ... summary ...
        return result
    except Exception as aspect_error:
        if not box.rollup and saga_stack:
            await self._rollback_saga(
                saga_stack, aspect_error, action, params,
                box, connections, context, plugin_ctx,
            )
        handled_result = await self._handle_aspect_error(...)
        return handled_result
```
---
## 13. Тестовая машина: метод `run_compensator`
```
# ── Архитектурное решение: изолированный запуск компенсаторов ──
#
# TestBench уже предоставляет run_aspect() для изолированного запуска
# отдельного regular-аспекта. Для компенсаторов нужен аналогичный
# механизм run_compensator().
#
# БЕЗ НЕГО тестирование компенсатора требует:
# 1. Собрать Action с несколькими аспектами.
# 2. Замокать один из них так, чтобы он упал.
# 3. Дождаться размотки стека.
# 4. Проверить побочный эффект компенсатора.
# Это интеграционный тест.
#
# С run_compensator() можно тестировать компенсатор КАК UNIT:
# передать params, state_before, state_after, error напрямую
# и проверить побочные эффекты.
#
# КЛЮЧЕВОЕ ОТЛИЧИЕ ОТ PRODUCTION:
# run_compensator() НЕ ПОДАВЛЯЕТ исключения.
# В production _rollback_saga() подавляет ошибки компенсаторов.
# В тестах ошибки ПРОБРАСЫВАЮТСЯ — это позволяет тестировать:
# - Что компенсатор НЕ падает при нормальных условиях.
# - Что компенсатор корректно обрабатывает ошибки внутренне.
# - Что компенсатор ПАДАЕТ при определённых условиях (граничные случаи).
```
### Сигнатура
```python
async def run_compensator(
    self,
    compensator_name: str,
    *,
    params: BaseParams,
    state_before: BaseState,
    state_after: BaseState | None,
    error: Exception,
    box: ToolsBox | None = None,
    connections: dict[str, BaseResourceManager] | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Изолированный запуск компенсатора для unit-тестирования.
    Аналог run_aspect() для аспектов.
    Параметры:
        compensator_name: Строковое имя метода-компенсатора
        params:           Входные параметры действия
        state_before:     Состояние до аспекта
        state_after:      Состояние после аспекта (None если чекер отклонил)
        error:            Исключение, вызвавшее размотку
        box:              ToolsBox (если None — создаётся дефолтный тестовый)
        connections:      Словарь ресурсных менеджеров (если None — пустой dict)
        context:          Dict для ContextView, если компенсатор использует
                          @context_requires
    Возвращает:
        None. Компенсатор не возвращает значение.
        Тестирование строится на проверке побочных эффектов.
    Raises:
        ValueError: если метод не найден, не является компенсатором,
                    или требует контекст, но context не передан.
        Любое исключение компенсатора: НЕ подавляется (в отличие
        от production-режима).
    """
```
### Валидации
```
# 1. Метод СУЩЕСТВУЕТ в классе Action.
# 2. Метод ЯВЛЯЕТСЯ компенсатором — имеет атрибут _compensate_meta.
# 3. Если компенсатор требует @context_requires, но context не передан → ValueError.
```
### Внутренняя реализация
```python
async def run_compensator(self, compensator_name, *, params, state_before,
                          state_after, error, box=None, connections=None,
                          context=None):
    # 1. Найти метод
    method = getattr(self._action_class, compensator_name, None)
    if method is None:
        raise ValueError(
            f"Метод '{compensator_name}' не найден в {self._action_class.__name__}"
        )
    # 2. Проверить, что это компенсатор
    if not hasattr(method, '_compensate_meta'):
        raise ValueError(
            f"Метод '{compensator_name}' не является компенсатором "
            f"(отсутствует декоратор @compensate)"
        )
    # 3. Подготовить окружение
    action_instance = self._create_action_instance()
    box = box or self._make_default_box()
    connections = connections or {}
    # 4. Обработка @context_requires
    context_keys = getattr(method, '_required_context_keys', None)
    if context_keys:
        if context is None:
            raise ValueError(
                f"Компенсатор '{compensator_name}' требует контекст "
                f"(ключи: {context_keys}), но context не передан"
            )
        ctx = ContextView(context, context_keys)
        await method(action_instance, params, state_before, state_after,
                     box, connections, error, ctx)
    else:
        await method(action_instance, params, state_before, state_after,
                     box, connections, error)
```
### Симметрия с `run_aspect()`
```
# ── Архитектурное решение: симметрия API тестовой машины ──
#
# | Свойство             | run_aspect()     | run_compensator()        |
# |----------------------|------------------|--------------------------|
# | Целевой метод        | @regular_aspect  | @compensate              |
# | Поиск метода         | По имени         | По имени                 |
# | Валидация атрибута   | _aspect_meta     | _compensate_meta         |
# | Возвращаемое значение| dict             | None (побочные эффекты)  |
# | Ошибки               | Пробрасываются   | Пробрасываются           |
# | @context_requires    | Поддерживается   | Поддерживается           |
#
# Единообразный API снижает когнитивную нагрузку: если разработчик
# умеет тестировать аспекты через run_aspect(), он сразу поймёт,
# как тестировать компенсаторы через run_compensator().
```
### Примеры использования в тестах
```python
async def test_payment_compensator_calls_refund():
    """Компенсатор вызывает refund с правильным txn_id."""
    bench = TestBench(CreateOrderAction)
    mock_payment = MockPaymentService()
    box = bench.make_box(services={PaymentService: mock_payment})
    await bench.run_compensator(
        "rollback_payment_compensate",
        params=CreateOrderParams(user_id=1, items=[...]),
        state_before=CreateOrderState(),
        state_after=CreateOrderState(txn_id="txn_123", amount=100),
        error=InsufficientStockError("Товар закончился"),
        box=box,
    )
    assert mock_payment.refund_called_with == "txn_123"

async def test_payment_compensator_handles_service_unavailable():
    """Компенсатор не падает, если платёжный сервис недоступен."""
    bench = TestBench(CreateOrderAction)
    mock_payment = MockPaymentService(raises=PaymentServiceUnavailable())
    box = bench.make_box(services={PaymentService: mock_payment})
    # Не должен бросить — обрабатывает ошибку внутренне
    await bench.run_compensator(
        "rollback_payment_compensate",
        params=CreateOrderParams(user_id=1, items=[...]),
        state_before=CreateOrderState(),
        state_after=CreateOrderState(txn_id="txn_456"),
        error=ValueError("some error"),
        box=box,
    )
    assert mock_payment.refund_attempted

async def test_payment_compensator_with_state_after_none():
    """Когда чекер отклонил — state_after=None, нечего откатывать."""
    bench = TestBench(CreateOrderAction)
    mock_payment = MockPaymentService()
    box = bench.make_box(services={PaymentService: mock_payment})
    await bench.run_compensator(
        "rollback_payment_compensate",
        params=CreateOrderParams(user_id=1, items=[...]),
        state_before=CreateOrderState(),
        state_after=None,
        error=CheckerRejectedError("Invalid amount"),
        box=box,
    )
    assert mock_payment.refund_called is False
```
---
## 14. Файлы и порядок реализации
### Этап 1: Фундамент
| Файл | Действие |
|---|---|
| `core/class_metadata.py` | Добавить `CompensatorMeta`, поле `compensators`, хелперы |
| `core/saga_frame.py` | Создать `SagaFrame` |
| `compensate/__init__.py` | Создать пакет |
| `compensate/compensate_decorator.py` | Создать `@compensate` |
### Этап 2: Сборка и валидация
| Файл | Действие |
|---|---|
| `metadata/collectors.py` | Добавить `collect_compensators()` |
| `metadata/validators.py` | Добавить `validate_compensators()` |
| `metadata/builder.py` | Интегрировать в `build()` |
### Этап 3: Граф
| Файл | Действие |
|---|---|
| `core/gate_coordinator.py` | Добавить узлы и рёбра компенсаторов в `_populate_graph()` |
### Этап 4: События
| Файл | Действие |
|---|---|
| `plugins/events.py` | Добавить `SagaRollbackStartedEvent`, `SagaRollbackCompletedEvent`, `BeforeCompensateAspectEvent`, `AfterCompensateAspectEvent`, `CompensateFailedEvent` |
| `plugins/__init__.py` | Обновить реэкспорт |
### Этап 5: Машина
| Файл | Действие |
|---|---|
| `core/action_product_machine.py` | Добавить `saga_stack` в `_execute_regular_aspects()`, реализовать `_rollback_saga()` с эмиссией `SagaRollbackStartedEvent`/`SagaRollbackCompletedEvent`, обновить `_execute_aspects_with_error_handling()` |
### Этап 6: Тестовая машина
| Файл | Действие |
|---|---|
| `testing/test_bench.py` | Добавить метод `run_compensator()` |
### Этап 7: Тесты
| Файл | Покрытие |
|---|---|
| `tests/compensate/test_compensate_decorator.py` | Валидации декоратора |
| `tests/compensate/test_compensate_metadata.py` | Сборка и валидация в MetadataBuilder |
| `tests/compensate/test_saga_rollback.py` | Размотка стека, обратный порядок |
| `tests/compensate/test_saga_nested.py` | Вложенные вызовы, изоляция стеков, try/catch |
| `tests/compensate/test_saga_errors.py` | Ошибки компенсаторов, CompensateFailedEvent |
| `tests/compensate/test_saga_events.py` | BeforeCompensate, AfterCompensate, SagaRollbackStarted, SagaRollbackCompleted |
| `tests/compensate/test_saga_rollup.py` | Поведение при rollup=True |
| `tests/compensate/test_saga_state_after.py` | state_after=None при ошибке чекера |
| `tests/compensate/test_saga_integration.py` | Полный конвейер через TestBench |
| `tests/compensate/test_bench_run_compensator.py` | Изолированный запуск компенсатора через TestBench |
| `tests/compensate/test_bench_run_compensator_validation.py` | Валидации run_compensator: несуществующий метод, не-компенсатор, отсутствие context |
| `tests/compensate/test_bench_run_compensator_context.py` | run_compensator с @context_requires |
---
## Результат
После реализации в ActionMachine появится полноценный механизм компенсации, соответствующий паттерну Saga, с:
- **Локальными стеками** на каждом уровне вложенности.
- **Отсутствием наследования** компенсаторов.
- **Молчаливыми ошибками** компенсаторов с типизированным событием `CompensateFailedEvent`.
- **Проверкой всех инвариантов** при инициализации через `MetadataBuilder`.
- **Полной интеграцией** с типизированной системой событий плагинов.
- **Событиями уровня всей размотки** (`SagaRollbackStartedEvent`, `SagaRollbackCompletedEvent`) для мониторинга и метрик.
- **Корректным поведением** при `try/catch` во вложенных вызовах.
- **Пропуском компенсации** при `rollup=True`.
- **Изолированным тестированием** компенсаторов через `TestBench.run_compensator()`.
Каждое архитектурное решение задокументировано в формате комментариев, готовых к переносу в docstring и inline-комментарии соответствующих модулей.
Контекст из исходного кода подтверждает использование стратегий выполнения (параллельной и последовательной), механизма наследования списков соединений с копированием при первом применении `@connection`, а также паттерна валидации `name` в промежуточных родительских классах.
````