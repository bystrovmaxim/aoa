## idea_02_coordinator_loggers.md — Сквозной логер как окно в машину

### Проблема

В типичных проектах логирование разрозненно: в каждом модуле свой логер, уровни настраиваются глобально, и чтобы понять что происходит в конкретном действии, приходится собирать логи из разных мест и мысленно их склеивать. Разработчик вынужден дублировать вызовы `logger.info()` в каждом аспекте, вручную подставлять контекст (`user_id`, `trace_id`, `action_name`), и при этом менять формат логов можно только через изменение кода [6].

Но проблема глубже. Либо разработчик вызывает `logger.info()` в каждом методе, вручную подставляя контекст — имя сервиса, идентификатор пользователя, трассировку. Либо логирование отсутствует вовсе, потому что добавлять контекст вручную слишком утомительно. В обоих случаях бизнес-логика загрязняется инфраструктурными деталями: разработчик вынужден знать про `request.user.id`, про заголовки, про формат логов. При смене среды — с разработки на production — приходится либо удалять `print()`, либо переписывать вызовы на структурированный логер [1].

В контексте AOA эта проблема имеет дополнительное измерение. ActionMachine владеет полным контекстом выполнения — имя действия, имя аспекта, уровень вложенности, длительность, данные пользователя из Context, `trace_id`, hostname, окружение [1]. Но Action физически не имеет доступа к Context [2]. Значит, разработчик в аспекте не может и не должен вручную подставлять эти данные в лог. При этом именно эти данные делают лог полезным.

### Решение

Логер в AOA — не зависимость через `@depends` и не глобальный синглтон. Это **шестой параметр сигнатуры аспекта**, который ActionMachine создаёт автоматически перед каждым вызовом и наполняет полным контекстом выполнения [3]. Разработчик пишет только бизнес-сообщение. Всё остальное — `action_name`, `aspect_name`, `nest_level`, `duration`, `user_id`, `trace_id`, `hostname`, `environment` — добавляется машиной [3].

Сигнатура аспекта:

```python
# Было (без логера):
async def fetch(self, params, state, deps, connections):
    ...

# Стало (с логером):
async def fetch(self, params, state, deps, connections, log):
    log.info("Загружаю задачи", project=params.project_id)
```

Разработчик пишет одну строку. В тестах это `print`. В production — структурированный JSON в ELK, Telegram-алерт, файл с ротацией. Код Action не меняется никогда [3].

---

### Почему логер — параметр конвейера, а не зависимость

Если логер — зависимость через `@depends`, он загрязняет декларацию бизнес-зависимостей. Интроспектор [4] покажет `ILogger` в графе зависимостей наравне с `PaymentGateway` — но логер не является зависимостью бизнес-логики. Кроме того, логер через DI не знает контекст выполнения: ни `nest_level`, ни `aspect_name`, ни `duration`. Разработчику пришлось бы передавать всё это вручную — а это именно та работа, от которой AOA освобождает [3].

Логер как шестой параметр — это инструмент конвейера, наравне с `params`, `state`, `deps`, `connections`. Пять параметров — полная картина мира аспекта [1]:

- `params` — что приходит в Action
- `state` — что накапливается внутри
- `deps` — что нужно снаружи
- `connections` — какие транзакции открыты
- `log` — где я сейчас и что происходит

Причём `log` — единственный из пяти, кто знает контекст самой машины [1].

---

### Как это реализуется в ActionProductMachine

ActionMachine создаёт `ContextualLogger` перед каждым вызовом аспекта:

```python
async def _call_aspect(self, method, action, params, state, factory, connections):
    log = ContextualLogger(
        coordinator=self._log_coordinator,
        nest_level=self._nest_level,
        action_name=action.get_full_class_name(),
        aspect_name=method.__name__,
        context=self._context,
    )
    return await method(action, params, state, factory, connections, log)
```

`ContextualLogger` обогащает каждое сообщение данными, о которых бизнес-логика не знает и не должна знать [1,3]:

```python
class ContextualLogger:
    def __init__(self, coordinator, nest_level, action_name, aspect_name, context):
        self._coordinator = coordinator
        self._nest_level = nest_level
        self._action_name = action_name
        self._aspect_name = aspect_name
        self._context = context

    def info(self, message, **context):
        self._coordinator.info(
            message,
            nest_level=self._nest_level,
            action=self._action_name,
            aspect=self._aspect_name,
            user_id=self._context.user.user_id,
            trace_id=self._context.request.trace_id,
            **context
        )
```

Разработчик пишет:

```python
log.info("Загружено 150 задач")
```

В production-логе появляется:

```json
{
  "message": "Загружено 150 задач",
  "action": "SyncIssuesAction",
  "aspect": "fetch",
  "nest_level": 2,
  "duration": 0.450,
  "user_id": "agent_1",
  "trace_id": "abc-123",
  "hostname": "pod-xyz-42",
  "service_name": "kanban-assistant",
  "environment": "production"
}
```

Всё это добавлено машиной автоматически, потому что машина владеет полным контекстом [1,3].

---

### Координатор и множественные логеры

**LogCoordinator** — единая шина логирования. К нему подключается **любое количество независимых логеров**, каждый из которых самостоятельно решает:

- **Что** ему интересно — через фильтр на основе регулярных выражений
- **Как** форматировать — через шаблон с переменными, условной логикой и тегами
- **Куда** писать — консоль, файл, ELK, Telegram, XML, JSON, Syslog

Аспекты и плагины отправляют сообщения в координатор, не зная о конкретных получателях. Координатор рассылает по всем подключённым логерам. Каждый логер применяет свой фильтр и, если сообщение прошло, рендерит его по своему шаблону.

```python
class BaseLogger(ABC):
    @abstractmethod
    def info(self, message: str, **context: Any) -> None: ...
    @abstractmethod
    def warning(self, message: str, **context: Any) -> None: ...
    @abstractmethod
    def error(self, message: str, **context: Any) -> None: ...
    @abstractmethod
    def debug(self, message: str, **context: Any) -> None: ...
```

Адаптеры:

- `PrintLogger` — для тестов и разработки, вывод с отступами по `nest_level`. Подключается по умолчанию в `ActionTestMachine` — ничего не нужно конфигурировать [1].
- `StdLogger` — обёртка над стандартным `logging.getLogger()`.
- `StructuredLogger` — JSON в ELK, Datadog, CloudWatch.
- `TelegramLogger` — алерты критических ошибок.
- `FileLogger` — запись в файл с настраиваемым форматом.
- `SlackLogger`, `XmlLogger`, `SyslogLogger` и т.д.

---

### Множественность логеров

Один вызов `log.info("Списание средств", amount=150)` в аспекте порождает столько записей, сколько логеров подключено и сколько из них пропустили это сообщение через свой фильтр.

```python
coordinator = LogCoordinator()

coordinator.add_logger(ConsoleLogger(
    format="{indent}[{action}.{aspect}] {message}",
    level="DEBUG"
))

coordinator.add_logger(FileLogger(
    filename="logs/app.log",
    format="{date} {time} | {action} | {aspect} | {user_id} | {message}",
    level="INFO"
))

coordinator.add_logger(ElkLogger(
    format="json",
    level="WARNING"
))

coordinator.add_logger(TelegramLogger(
    chat_id=DIRECTOR_CHAT_ID,
    format="🚨 *{action}* провалился\nПользователь: {user_id}\nОшибка: {exception.message}",
    level="CRITICAL",
    filter_regex=r"exception\.type=(PaymentError|FraudDetected)"
))
```

Логеры работают независимо. Ошибка в одном не блокирует остальные. Добавление нового логера не требует изменения кода — только конфигурации [6].

---

### Шаблоны и переменные

Разработчик при конфигурации логера указывает строку формата с переменными в фигурных скобках. Координатор при рендеринге подставляет реальные значения из полного контекста выполнения.

**Доступные переменные:**

- Из машины и аспекта:
  - `{action_name}`, `{action}` — полное/короткое имя Action
  - `{action_module}` — модуль Action
  - `{aspect_name}`, `{aspect}` — имя аспекта
  - `{nest_level}` — уровень вложенности (0, 1, 2...)
  - `{indent}` — отступ по nest_level (автоматически `"  " * nest_level`)
  - `{duration}` — время выполнения аспекта в секундах
  - `{duration_ms}` — в миллисекундах
  - `{timestamp}`, `{date}`, `{time}` — временны́е метки

- Из Context (пользователь и запрос):
  - `{user_id}`, `{roles}`, `{client_ip}`, `{user_agent}`
  - `{trace_id}`, `{request_path}`, `{request_method}`
  - `{hostname}`, `{service_name}`, `{service_version}`, `{environment}`

- Из бизнес-данных:
  - `{params.field_name}` — любое поле Params через точечную нотацию
  - `{state.field_name}` — любое поле state после аспекта
  - `{result.field_name}` — любое поле Result (только в global_finish)

- Из исключения (если есть):
  - `{exception.message}`, `{exception.type}`, `{exception.traceback}`

---

### Условная логика — функция `iif`

Для условной подстановки используется встроенная функция `iif`:

```
{iif(условие; значение_если_истина; значение_если_ложь)}
```

Условие — простое выражение с операторами `==`, `!=`, `>`, `<`, `>=`, `<=`, `and`, `or`, `not`. Операнды — переменные или литералы (строки в одинарных кавычках, числа, `true`/`false`). Интерпретатор поддерживает также встроенные функции: `len`, `upper`, `lower`, `format_number`.

**Пример: уровень серьёзности в тексте**

```
{iif(exception.type=='PaymentError'; '💳 ПЛАТЁЖ'; iif(exception.type=='FraudDetected'; '🚨 ФРОД'; '⚠️ ОШИБКА'))}
```

**Пример: пометка крупных транзакций**

```
{iif(params.amount > 100000; '[КРУПНАЯ СДЕЛКА] '; '')}{message}
```

**Пример: статус операции в конце строки**

```
{date} {time} | {action} | {message} | {iif(result.success == true; 'OK'; 'FAILED')}
```

**Создание внутренних тегов через `iif`**

Особенно мощное применение — генерация тегов прямо внутри шаблона. Теги потом используются для поиска и фильтрации в ELK или Grafana:

```
{date} {time} level={iif(exception.type != ''; 'ERROR'; iif(duration > 5.0; 'SLOW'; 'INFO'))} action={action} trace={trace_id} {message}
```

Или для JSON-логера с динамическими полями:

```json
{
  "level": "{iif(exception.type != ''; 'error'; 'info')}",
  "risk": "{iif(params.amount > 1000000; 'high'; iif(params.amount > 100000; 'medium'; 'low'))}",
  "channel": "{iif(params.channel == 'sms'; 'mobile'; 'web')}",
  "message": "{message}"
}
```

Здесь `risk` и `channel` — теги которые разработчик **не пишет в коде**. Они генерируются координатором из данных запроса по правилам конфигурации [6].

---

### Фильтры через регулярные выражения

Каждый логер может иметь фильтр — регулярное выражение, которое применяется к **сериализованному контексту** сообщения перед рендерингом. Если регулярка не совпала — логер пропускает сообщение.

Фильтр работает по полному контексту в виде строки `"ключ=значение ключ=значение ..."`. Это позволяет фильтровать по любому сочетанию условий:

```python
# Только ошибки платёжной системы
TelegramLogger(filter_regex=r"exception\.type=PaymentError")

# Только для premium-пользователей
FileLogger(filter_regex=r"roles=.*premium.*")

# Только медленные операции (> 3 секунды)
AlertLogger(filter_regex=r"duration=[3-9]\.|duration=\d{2,}\.")

# Только конкретный action и только ошибки
SlackLogger(filter_regex=r"action=.*CheckoutAction.*exception\.type=\w+")

# Исключить технические действия из подробного лога
VerboseLogger(filter_regex=r"^(?!.*action=.*HealthCheck).*$")

# Реагировать на конкретные бизнес-события
DirectorTelegramLogger(filter_regex=r"params\.amount=\d{7,}")  # суммы от 10 млн
```

Фильтр — это не уровень логирования. Логер с `level=INFO` и `filter_regex` пропустит INFO-сообщение только если оно ещё и совпадает с регулярным выражением. Оба условия должны выполняться одновременно.

---

### Форматы вывода

Логеры не ограничены текстом с отступами. Формат определяется конфигурацией и может быть любым.

**Консольный с отступами (для разработки):**

```
→ ProcessOrderAction
  → [validate_user] Проверка пользователя user_id=42
  ← [validate_user] OK 0.003s
  → [charge_card] Списание 1500.0
    → ChargeCardAction
      → [validate] Карта валидна
      ← [validate] OK 0.001s
    ← ChargeCardAction 0.450s
  ← [charge_card] OK 0.451s
← ProcessOrderAction result=order_id=1001 0.512s
```

**JSON (для ELK/Datadog):**

```json
{
  "timestamp": "2025-06-15T14:32:01Z",
  "level": "info",
  "action": "ProcessOrderAction",
  "aspect": "charge_card",
  "nest_level": 1,
  "duration_ms": 451,
  "user_id": "42",
  "trace_id": "abc-123",
  "risk": "low",
  "message": "Списание средств",
  "params.amount": 1500.0
}
```

**XML (для корпоративных систем):**

```xml
<log-entry timestamp="2025-06-15T14:32:01Z" level="INFO">
  <action>ProcessOrderAction</action>
  <aspect>charge_card</aspect>
  <user id="42" trace="abc-123"/>
  <message>Списание средств</message>
  <duration unit="ms">451</duration>
</log-entry>
```

**Syslog RFC 5424:**

```
<134>1 2025-06-15T14:32:01Z hostname service - abc-123 [action="ProcessOrderAction" user="42"] Списание средств
```

**Telegram Markdown:**

```
🔴 *ProcessOrderAction* провалился
👤 Пользователь: `42`
💰 Сумма: `1,500,000 ₽`
❌ Ошибка: `InsufficientFunds`
🔗 Trace: `abc-123`
```

Формат задаётся либо строкой шаблона (`format="..."`) либо именем предустановленного формата (`format="json"`, `format="xml"`, `format="syslog"`). Для нестандартных форматов разработчик создаёт собственный `FormatterAdapter` [6].

---

### Скоупы

Координатор поддерживает скоупы — возможность разделять логи разных потоков выполнения. Скоуп привязывается к текущему выполнению действия через `trace_id` и автоматически передаётся во все вложенные вызовы через `nest_level`.

Практическое применение: при расследовании инцидента можно включить `level=DEBUG` только для конкретного `trace_id` или `user_id`, не захламляя логи остальных пользователей [6].

---

### Вложенные вызовы и единый поток

Когда корневое действие вызывает дочернее через `deps.run_action()`, машина передаёт тот же координатор с увеличенным `nest_level` [2]. Все сообщения всего дерева выполнения идут в один поток с правильной вложенностью [3]:

```
→ ProcessOrderAction
  ℹ️ Начинаю обработку заказа
    → CalculateDiscountAction
      ℹ️ Скидка VIP: 10%
    ← CalculateDiscountAction
    → ChargeCardAction
      ℹ️ Списание 900₽
        → ValidateCardAction
          ℹ️ Карта валидна
        ← ValidateCardAction
    ← ChargeCardAction
  ℹ️ Заказ создан: #42
← ProcessOrderAction
```

Это не лог плагина. Это лог бизнес-логики, написанный разработчиком в аспектах, автоматически выстроенный в дерево машиной [3].

---

### Обратная совместимость

Машина проверяет сигнатуру аспекта через `inspect.signature()`. Если аспект принимает шесть параметров — передаёт `log`. Если пять — вызывает без логера. Старый код не ломается [1].

---

### Реальная конфигурация — полный пример

```python
coordinator = LogCoordinator()

# 1. Разработка — всё в консоль с цветами и отступами
coordinator.add_logger(ConsoleLogger(
    format="{indent}[{aspect}] {message} {iif(duration_ms > 0; '(' + duration_ms + 'ms)'; '')}",
    level="DEBUG"
))

# 2. Продакшн — INFO и выше в файл в JSON
coordinator.add_logger(FileLogger(
    filename="/var/log/app/actions.jsonl",
    format="json",
    level="INFO"
))

# 3. ELK — WARNING и выше с расширенным контекстом
coordinator.add_logger(ElkLogger(
    index="app-warnings",
    format="""
    {
      "ts": "{timestamp}",
      "action": "{action}",
      "user": "{user_id}",
      "trace": "{trace_id}",
      "risk": "{iif(params.amount > 1000000; 'critical'; iif(params.amount > 100000; 'high'; 'normal'))}",
      "msg": "{message}",
      "exc": "{exception.type}"
    }
    """,
    level="WARNING"
))

# 4. Telegram директору — только критические платёжные ошибки
coordinator.add_logger(TelegramLogger(
    chat_id=DIRECTOR_CHAT_ID,
    format="🚨 *{iif(exception.type=='FraudDetected'; 'ФРОД'; 'КРИТИЧЕСКАЯ ОШИБКА')}*\n\n"
           "Действие: `{action}`\n"
           "Пользователь: `{user_id}`\n"
           "Сумма: `{params.amount}`\n"
           "Ошибка: `{exception.message}`\n"
           "Trace: `{trace_id}`",
    level="CRITICAL",
    filter_regex=r"exception\.type=(PaymentError|FraudDetected|InsufficientFunds)"
))

# 5. Slack команды — медленные операции (> 5 сек)
coordinator.add_logger(SlackLogger(
    channel="#performance-alerts",
    format="⏱ Медленная операция: *{action}.{aspect}* — {duration_ms}ms\n"
           "Пользователь: {user_id} | Trace: {trace_id}",
    level="WARNING",
    filter_regex=r"duration=[5-9]\.|duration=\d{2,}\."
))

configure_logger(coordinator)
```

---

### Как это выглядит в коде аспекта

Разработчик пишет одну строку. Куда она попадёт — определяет конфигурация:

```python
@aspect("Списание средств")
async def charge(self, params, state, deps, connections, log):
    log.info("Списание средств", amount=params.amount, card=params.card_last4)
    # ↑ Эта строка одновременно:
    # → попадает в консоль с отступом (если DEBUG)
    # → пишется в файл в JSON (если INFO)
    # → уходит в ELK с тегом risk=high (если amount > 100000)
    # → отправляется директору в Telegram (если PaymentError)
    # → сигнализирует в Slack (если выполняется > 5 сек)
```

Код аспекта не знает ни об одном из этих получателей [6].

---

### Почему это архитектурная теорема, а не фича

Логер со сквозным контекстом возможен только если выполнены три условия одновременно [3]:

1. **Единая точка исполнения** — `machine.run()`. Машина гарантированно присутствует при каждом вызове каждого аспекта. Некому создать контекстный логер в Django или FastAPI — нет единой точки.
2. **Формализованный конвейер с метаданными**. Машина знает `action_name`, `aspect_name`, `nest_level`, `duration`, `context` — и всё это гарантированные данные, потому что без них код не запустится [2].
3. **Context невидим для Actions**. Action не может получить контекст самостоятельно [2]. Но логер, созданный машиной, — видит всё.

Если в системе есть единая точка исполнения, формализованный конвейер с метаданными и изоляция контекста от бизнес-логики — то логер со сквозным контекстом следует из архитектуры как математическое следствие [3].

---

### Влияние

- **Бизнес-логика описывает *что* происходит. Машина знает *где, когда и в каком контексте*. Логер соединяет оба мира — без участия бизнес-логики** [3].
- **Принудительная формализация наблюдаемости** — так же как `@CheckRoles` принудительно формализует безопасность. Без `log` в сигнатуре разработчик либо не логирует вообще, либо логирует без контекста. С `log` — контекст бесплатный и всегда правильный [1].
- **Гибкость без изменения кода** — добавить новый канал, поменять формат, включить подробный лог для одного action — только конфигурация.
- **Богатый контекст автоматически** — `user_id`, `trace_id`, `nest_level`, `duration`, `params` подставляются машиной.
- **Условная логика прямо в шаблоне** — теги `risk=high`, `channel=mobile`, `status=FAILED` генерируются из данных без дополнительного кода.
- **Реакция на критические события** — Telegram-логер с `filter_regex` — это не просто лог. Это система раннего предупреждения, встроенная в инфраструктуру без отдельного кода мониторинга.
- **Любой формат** — консоль с отступами, JSON, XML, Syslog, Markdown — один и тот же вызов `log.info()` порождает нужный формат для каждого получателя.

---

### Что можно добавить (из roadmap)

- **Структурированные логи** — чтобы логгеры могли работать не только со строками, но и с JSON-объектами.
- **Автоматическое добавление контекста** — уже есть, но можно расширять.
- **Семплинг** — для высоконагруженных систем настроить вероятностную выборку сообщений.
- **Асинхронная отправка** — чтобы логирование не тормозило основное выполнение [6].

---

### Уникальность

Это не просто «логер с форматированием». Это **конфигурируемая шина логирования с языком шаблонов**, встроенная в инфраструктуру наблюдаемости AOA [6].

Ни один mainstream-фреймворк не предлагает:
- Множество независимых логеров с разными форматами, фильтрами и каналами из одной точки.
- Условную генерацию тегов через `iif` без изменения кода.
- Фильтрацию по произвольному контексту через регулярные выражения.
- Автоматический `nest_level` и `indent` из архитектуры машины.

Особая ценность при расследовании инцидентов: можно быстро добавить Telegram-логер с нужным `filter_regex`, получить мгновенные алерты, расследовать проблему — и убрать логер без единого изменения в коде приложения [6].

---

### Связь с другими идеями

- Координатор логеров усиливает плагинную систему [2]: плагины наблюдают за выполнением, а координатор обеспечивает доставку наблюдений в нужные каналы с нужным форматом.
- В сочетании с перехватчиками исключений (**idea_01**) координатор позволяет логировать обработанные и необработанные ошибки через разные шаблоны и каналы — Telegram для необработанных, файл для обработанных — не смешивая инфраструктуру с бизнес-логикой.
- В сочетании с телеметрией PostgreSQL (**idea_18**) шаблон может включать `{params.shared_blks_read}` и отправлять алерт в Slack если конкретный action начал читать больше обычного.
- **ExecutionTreePlugin (idea_17)** и логер синхронизированы автоматически — оба получают данные из одного источника: машины. Логи и дерево выполнения всегда согласованы.
- **PostgresUnitOfWork (idea_03)** — логер может писать "Буфер: 47 команд, flush перед SELECT" с привязкой к `trace_id` и `action_name`.
- **Генерация тестов из production-логов (idea_08)** — LLM анализирует логи вместе с деревом выполнения и телеметрией БД для генерации тестов.

---

### Что добавлено из других вариантов

**Из второго варианта:**
- Логер как шестой параметр аспекта и объяснение, почему это лучше DI.
- Механизм передачи логера от ActionMachine (`_call_aspect`).
- `ContextualLogger` и его реализация.
- Три условия архитектуры, делающие сквозной логер возможным.
- Обратная совместимость.
- Упоминание, что бизнес-логика не знает контекст, а логер — окно в машину.
- Связь с `ExecutionTreePlugin`, `idea_01`, `idea_03`, `idea_08`, `idea_18`.

**Из третьего варианта:**
- В раздел "Что можно добавить" добавлены пункты про семплинг и асинхронную отправку.
- Упоминание встроенных функций в `iif` (`len`, `upper`, `lower`, `format_number`).
- Лаконичные формулировки про уникальность и связь с плагинами.