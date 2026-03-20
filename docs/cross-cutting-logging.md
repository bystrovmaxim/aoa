## Cross-cutting Logging (English)

ActionMachine provides a built‑in cross‑cutting logging system that automatically enriches each logger call with execution context: machine name, mode, action, and aspect. The developer receives the `log` parameter of type `ActionBoundLogger` in aspects and can write `await log.info("Message")`, passing additional user data via `**kwargs`.

### Key Concepts

#### 1. Bound Logger (ActionBoundLogger)

**Problem:** Previously, logs lacked information about which action, aspect, and mode they were called from. This made log analysis and filtering difficult in complex scenarios with nested calls.

**Solution:** Introduced the `ActionBoundLogger` class, which is created for each aspect call and automatically adds the following fields to the `LogScope`:
- `machine` – machine class name (e.g., `"ActionProductMachine"`).
- `mode` – execution mode (passed to the machine constructor).
- `action` – full action class name (including module).
- `aspect` – aspect method name.

The logging level is passed via the `"level"` key in `var` (added automatically). User data is passed only via `**kwargs` and ends up in `var`; no system fields (except `level`) are automatically added to `var`, preserving the purity of the user context.

#### 2. Logging Coordinator (LogCoordinator)

**Problem:** Many places in the system needed to output logs (aspects, plugins, machine), and each of them had to know about specific loggers. This led to coupling and code duplication.

**Solution:** Created a single coordinator `LogCoordinator` through which all messages pass. The coordinator:
- Accepts a message with a template, variables, scope, context, and other parameters.
- Delegates variable substitution and `iif` expression evaluation to the `VariableSubstitutor` class.
- Broadcasts the final message to all registered loggers, which independently decide whether to process it (via filtering).

#### 3. Console Logger (ConsoleLogger)

**Problem:** During debugging, it is important to quickly distinguish logging levels (info, warning, error, debug) and see the execution context. Plain `print` does not provide such clarity.

**Solution:** Implemented `ConsoleLogger` – a basic logger implementation that outputs messages to `stdout` with support for:
- Indentation by nesting level (`indent`), visually reflecting call depth.
- **No automatic prefix** – the user must include scope variables explicitly in the template (e.g., `[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}]`).
- Colors are applied via template filters (see below), not built‑into the logger.

#### 4. Execution Mode (`mode`)

**Problem:** Previously, only the infrastructure environment (`environment` in `Context`) existed, describing the execution environment (host, service version, etc.). However, logging often requires a separate "mode of operation" indicator (production, staging, test, dev) that can influence output format or filtering.

**Solution:** Added a mandatory `mode` parameter to the machine constructor. It is passed to the logger scope and can be used for message filtering. Example values: `"production"`, `"staging"`, `"test"`, `"dev"`. This separates execution mode from the infrastructure environment and provides flexibility in logging configuration.

### Template Language

Log messages support a rich template language that includes variable substitution, conditional logic, colors, and sensitive data masking.

#### Variables

Variables are written as `{%namespace.path}` where `namespace` can be:
- `var` – developer‑supplied dictionary (via `**kwargs`).
- `state` – current aspect pipeline state (`BaseState`).
- `scope` – logging scope (machine, mode, action, aspect).
- `context` – execution context (`Context`).
- `params` – action input parameters (`BaseParams`).

Nested objects are traversed with dot notation, e.g., `{%context.user.user_id}`.

#### Conditional Logic (`iif`)

Use `{iif(condition; true_value; false_value)}` for inline conditions:
- `condition` is a Python‑like expression with access to variables (as literals).
- `true_value` and `false_value` can be string literals or variables.
- Example: `{iif({%var.amount} > 1000; 'HIGH'; 'LOW')}`.

#### Color Filters

You can add ANSI colors to any substituted value using filters:

- **Foreground only:** `{%var.amount|red}` – outside `iif`.
- **Background only:** `{%var.text|bg_red}`.
- **Foreground + background:** `{%var.text|red_on_blue}`.

Inside `iif`, use color functions (because `|` is not supported in expressions):
```
{iif({%var.amount} > 10000; red('⚠️ HIGH'); green('✅ LOW'))}
```

Available colors: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange` and their bright variants. Any combination of foreground and background is possible via the `foreground_on_background` syntax.

Color processing happens **after** all substitutions and `iif` evaluation, so ANSI codes never interfere with logic.

#### Sensitive Data Masking

Use the `@sensitive` decorator on a property getter to automatically mask its value in logs:

```python
@property
@sensitive(max_chars=3, char='*', max_percent=50)
def email(self):
    return self._email
```

Parameters:
- `max_chars`: maximum number of characters to show from the beginning (default 3).
- `char`: replacement character (default `'*'`).
- `max_percent`: maximum percentage of the string length to show (default 50). The actual shown length is `min(max_chars, ceil(len(s) * max_percent / 100))`. After the visible part, exactly 5 replacement characters are added.

If the value is numeric, boolean, or any other non‑string type, it is first converted to a string and then masked. This may cause errors if such a value is used in `iif` comparisons – this is a deliberate trade‑off for security.

#### Strict Underscore Rule

Any variable whose last segment starts with an underscore (`_` or `__`) will **raise `LogTemplateError`** when accessed. This prevents accidental logging of protected/private fields. To output such data, expose it through a public property.

### Usage in Code

#### 1. Creating a Machine with Logging

```python
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator

coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])

machine = ActionProductMachine(
    mode="production",
    log_coordinator=coordinator
)
```

If `log_coordinator` is not provided, a coordinator with a single `ConsoleLogger(use_colors=True)` is created automatically.

#### 2. Defining an Action with Aspects Using the Logger

All aspects **must** accept the `log` parameter (sixth). The parameter order is fixed:

```python
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.AspectMethod import aspect, summary_aspect

class MyAction(BaseAction[MyParams, MyResult]):

    @aspect("Data preparation")
    async def prepare(self, params, state, deps, connections, log):
        await log.info("Starting preparation", user=params.user_id)
        # ... logic
        return {"prepared": True}

    @summary_aspect("Result formation")
    async def summary(self, params, state, deps, connections, log):
        await log.debug("Result formed", total=state.get("total"))
        return MyResult(...)
```

#### 3. Logging with Different Levels

```python
await log.info("Informational message", extra="data")
await log.warning("Warning", code=403)
await log.error("Error", exc=repr(e))
await log.debug("Debug information", vars=some_dict)
```

All passed `**kwargs` end up in the `var` dictionary and can be used in message templates.

#### 4. Log Filtering

Each logger can have a list of regular expressions (`filters`). A message passes the filter if at least one expression matches the string composed of `scope.as_dotpath()`, the message text, and `key=value` pairs from `var`.

Example: logger that accepts only messages from the `ProcessOrderAction` action:

```python
logger = ConsoleLogger(filters=[r"ProcessOrderAction.*"])
```

### Extension: Creating a Custom Logger

**Problem:** The built‑in console logger may not suit all cases (e.g., file logging, sending to ELK, integration with external systems).

**Solution:** An abstract base class `BaseLogger` is provided. To create a custom logger, inherit from it and implement the asynchronous `write` method:

```python
from action_machine.Logging.base_logger import BaseLogger

class MyLogger(BaseLogger):
    async def write(self, scope, message, var, ctx, state, params, indent):
        # Your implementation (file writing, sending to ELK, etc.)
        ...
```

Then add an instance to the coordinator:

```python
coordinator.add_logger(MyLogger(filters=[...]))
```

If your logger supports ANSI colors, override the `supports_colors` property to return `True`. The coordinator will then preserve color markers.

### Testing

**Problem:** When testing actions, actual log output should not occur, and we need to verify that logs are called with the correct parameters.

**Solution:** Use `ActionTestMachine` for tests. By default, `mode="test"`. The logger can be replaced with a mock:

```python
from unittest.mock import AsyncMock

mock_coordinator = AsyncMock(spec=LogCoordinator)
machine = ActionTestMachine(mode="test", log_coordinator=mock_coordinator)
```

Now you can check `mock_coordinator.emit` calls and analyze the passed arguments.

### Complete Example

```python
import asyncio
from dataclasses import dataclass
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.sensitive_decorator import sensitive

@dataclass
class HelloParams(BaseParams):
    name: str

class HelloResult(BaseResult):
    greeting: str

class UserAccount:
    def __init__(self, name, email):
        self.name = name
        self._email = email

    @property
    @sensitive(max_chars=3)
    def email(self):
        return self._email

class HelloAction(BaseAction[HelloParams, HelloResult]):
    @summary_aspect("Say hello")
    async def summary(self, params, state, deps, connections, log):
        # Using scope variables, color filter, and iif
        await log.info(
            "[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}] "
            "Greeting user {%var.name|green}. Risk: {iif({%var.name} == 'admin'; red('ADMIN'); blue('user'))}",
            name=params.name
        )
        return HelloResult(greeting=f"Hello, {params.name}!")

async def main():
    coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
    machine = ActionProductMachine(mode="dev", log_coordinator=coordinator)

    user = UserAccount(name="World", email="world@example.com")
    context = Context(user=UserInfo(user_id="test"))
    context._extra["account"] = user  # to test sensitive masking

    params = HelloParams(name="World")
    result = await machine.run(context, HelloAction(), params)
    print(result.greeting)

asyncio.run(main())
```

Console output (with colors):
```
[ActionProductMachine.dev.HelloAction.summary] Greeting user World. Risk: user
Hello, World!
```

The email is not logged because it is not accessed; if we added `{%context.extra.account.email}`, it would be masked (e.g., `wor*****`).

---

## Сквозное логирование (Русский)

ActionMachine предоставляет встроенную систему сквозного логирования, которая автоматически обогащает каждый вызов логера контекстом выполнения: имя машины, режим, действие и аспект. Разработчик получает параметр `log` типа `ActionBoundLogger` в аспектах и может писать `await log.info("Сообщение")`, передавая дополнительные пользовательские данные через `**kwargs`.

### Ключевые концепции

#### 1. Привязанный логер (ActionBoundLogger)

**Проблема:** Раньше логам не хватало информации о том, из какого действия, аспекта и в каком режиме они были вызваны. Это затрудняло анализ и фильтрацию логов в сложных сценариях с вложенными вызовами.

**Решение:** Введён класс `ActionBoundLogger`, который создаётся для каждого вызова аспекта и автоматически добавляет в `LogScope` следующие поля:
- `machine` – имя класса машины (например, `"ActionProductMachine"`).
- `mode` – режим выполнения (передаётся в конструктор машины).
- `action` – полное имя класса действия (включая модуль).
- `aspect` – имя метода-аспекта.

Уровень логирования передаётся через ключ `"level"` в `var` (добавляется автоматически). Пользовательские данные передаются только через `**kwargs` и попадают в `var`; никакие системные поля (кроме `level`) не добавляются в `var`, сохраняя чистоту пользовательского контекста.

#### 2. Координатор логирования (LogCoordinator)

**Проблема:** В системе было много мест, где требовалось выводить логи (аспекты, плагины, машина), и каждое из них должно было знать о конкретных логерах. Это приводило к связанности и дублированию кода.

**Решение:** Создан единый координатор `LogCoordinator`, через который проходят все сообщения. Координатор:
- Принимает сообщение с шаблоном, переменными, скоупом, контекстом и другими параметрами.
- Делегирует подстановку переменных и вычисление выражений `iif` классу `VariableSubstitutor`.
- Рассылает итоговое сообщение всем зарегистрированным логерам, которые самостоятельно решают, обрабатывать ли его (через фильтрацию).

#### 3. Консольный логер (ConsoleLogger)

**Проблема:** При отладке важно быстро различать уровни логирования (info, warning, error, debug) и видеть контекст выполнения. Простой `print` не даёт такой наглядности.

**Решение:** Реализован `ConsoleLogger` – базовая реализация логера, выводящая сообщения в `stdout` с поддержкой:
- Отступов по уровню вложенности (`indent`), визуально отражающих глубину вызова.
- **Отсутствия автоматического префикса** – пользователь должен явно включать переменные скоупа в шаблон (например, `[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}]`).
- Цвета применяются через фильтры шаблонов (см. ниже), а не встроены в логер.

#### 4. Режим выполнения (`mode`)

**Проблема:** Раньше существовало только инфраструктурное окружение (`environment` в `Context`), описывающее среду выполнения (хост, версию сервиса и т.д.). Однако для логирования часто нужен отдельный индикатор «режима работы» (production, staging, test, dev), который может влиять на формат вывода или фильтрацию.

**Решение:** Добавлен обязательный параметр `mode` в конструктор машины. Он передаётся в скоуп логера и может использоваться для фильтрации сообщений. Примеры значений: `"production"`, `"staging"`, `"test"`, `"dev"`. Это отделяет режим выполнения от инфраструктурного окружения и даёт гибкость в настройке логирования.

### Язык шаблонов

Сообщения лога поддерживают богатый язык шаблонов, включающий подстановку переменных, условную логику, цвета и маскировку чувствительных данных.

#### Переменные

Переменные записываются как `{%namespace.path}`, где `namespace` может быть:
- `var` – словарь, переданный разработчиком (через `**kwargs`).
- `state` – текущее состояние конвейера аспектов (`BaseState`).
- `scope` – скоуп логирования (machine, mode, action, aspect).
- `context` – контекст выполнения (`Context`).
- `params` – входные параметры действия (`BaseParams`).

Вложенные объекты обходятся через точку, например, `{%context.user.user_id}`.

#### Условная логика (`iif`)

Используйте `{iif(условие; значение_истина; значение_ложь)}` для встроенных условий:
- `условие` – Python-подобное выражение с доступом к переменным (как литералам).
- `значение_истина` и `значение_ложь` могут быть строковыми литералами или переменными.
- Пример: `{iif({%var.amount} > 1000; 'HIGH'; 'LOW')}`.

#### Цветовые фильтры

Вы можете добавлять ANSI-цвета к любому подставленному значению с помощью фильтров:

- **Только текст:** `{%var.amount|red}` – вне `iif`.
- **Только фон:** `{%var.text|bg_red}`.
- **Текст + фон:** `{%var.text|red_on_blue}`.

Внутри `iif` используйте функции цвета (потому что `|` не поддерживается в выражениях):
```
{iif({%var.amount} > 10000; red('⚠️ ВЫСОКИЙ'); green('✅ низкий'))}
```

Доступные цвета: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange` и их яркие варианты. Любая комбинация текста и фона возможна через синтаксис `foreground_on_background`.

Обработка цветов происходит **после** всех подстановок и вычисления `iif`, поэтому ANSI-коды никогда не мешают логике.

#### Маскировка чувствительных данных

Используйте декоратор `@sensitive` на геттере свойства, чтобы автоматически маскировать его значение в логах:

```python
@property
@sensitive(max_chars=3, char='*', max_percent=50)
def email(self):
    return self._email
```

Параметры:
- `max_chars`: максимальное количество выводимых символов с начала (по умолчанию 3).
- `char`: символ замены (по умолчанию `'*'`).
- `max_percent`: максимальный процент длины строки для вывода (по умолчанию 50). Реальная длина вывода равна `min(max_chars, ceil(len(s) * max_percent / 100))`. После видимой части добавляется ровно 5 символов замены.

Если значение является числовым, булевым или другого нестрокового типа, оно сначала преобразуется в строку, а затем маскируется. Это может вызвать ошибки при использовании таких значений в сравнениях `iif` – это сознательный компромисс ради безопасности.

#### Строгое правило подчёркивания

Любая переменная, последний сегмент которой начинается с подчёркивания (`_` или `__`), вызовет `LogTemplateError` при обращении. Это предотвращает случайное логирование защищённых/приватных полей. Чтобы выводить такие данные, предоставьте их через публичное свойство.

### Использование в коде

#### 1. Создание машины с логированием

```python
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator

coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])

machine = ActionProductMachine(
    mode="production",
    log_coordinator=coordinator
)
```

Если `log_coordinator` не указан, автоматически создаётся координатор с одним `ConsoleLogger(use_colors=True)`.

#### 2. Определение действия с аспектами, использующими логер

Все аспекты **обязаны** принимать параметр `log` (шестой). Порядок параметров фиксирован:

```python
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.AspectMethod import aspect, summary_aspect

class MyAction(BaseAction[MyParams, MyResult]):

    @aspect("Подготовка данных")
    async def prepare(self, params, state, deps, connections, log):
        await log.info("Начинаем подготовку", user=params.user_id)
        # ... логика
        return {"prepared": True}

    @summary_aspect("Формирование результата")
    async def summary(self, params, state, deps, connections, log):
        await log.debug("Результат сформирован", total=state.get("total"))
        return MyResult(...)
```

#### 3. Логирование с разными уровнями

```python
await log.info("Информационное сообщение", extra="data")
await log.warning("Предупреждение", code=403)
await log.error("Ошибка", exc=repr(e))
await log.debug("Отладочная информация", vars=some_dict)
```

Все переданные `**kwargs` попадают в словарь `var` и могут использоваться в шаблонах сообщений.

#### 4. Фильтрация логов

Каждый логер может иметь список регулярных выражений (`filters`). Сообщение проходит фильтр, если хотя бы одно выражение совпадает со строкой, составленной из `scope.as_dotpath()`, текста сообщения и пар `key=value` из `var`.

Пример создания логера, принимающего только сообщения от действия `ProcessOrderAction`:

```python
logger = ConsoleLogger(filters=[r"ProcessOrderAction.*"])
```

### Расширение: создание собственного логера

**Проблема:** Встроенный консольный логер может не подходить для всех случаев (логирование в файл, отправка в ELK, интеграция с внешними системами).

**Решение:** Предоставлен абстрактный базовый класс `BaseLogger`. Чтобы создать собственный логер, унаследуйтесь от него и реализуйте асинхронный метод `write`:

```python
from action_machine.Logging.base_logger import BaseLogger

class MyLogger(BaseLogger):
    async def write(self, scope, message, var, ctx, state, params, indent):
        # Ваша реализация (запись в файл, отправка в ELK и т.д.)
        ...
```

Затем добавьте экземпляр в координатор:

```python
coordinator.add_logger(MyLogger(filters=[...]))
```

Если ваш логер поддерживает ANSI-цвета, переопределите свойство `supports_colors`, чтобы оно возвращало `True`. Координатор тогда будет сохранять цветовые маркеры.

### Тестирование

**Проблема:** При тестировании действий не должен происходить реальный вывод логов, и нужно проверять, что логеры вызываются с правильными параметрами.

**Решение:** Используйте `ActionTestMachine` для тестов. По умолчанию `mode="test"`. Логер можно заменить на мок:

```python
from unittest.mock import AsyncMock

mock_coordinator = AsyncMock(spec=LogCoordinator)
machine = ActionTestMachine(mode="test", log_coordinator=mock_coordinator)
```

Теперь можно проверять вызовы `mock_coordinator.emit` и анализировать переданные аргументы.

### Полный пример

```python
import asyncio
from dataclasses import dataclass
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.sensitive_decorator import sensitive

@dataclass
class HelloParams(BaseParams):
    name: str

class HelloResult(BaseResult):
    greeting: str

class UserAccount:
    def __init__(self, name, email):
        self.name = name
        self._email = email

    @property
    @sensitive(max_chars=3)
    def email(self):
        return self._email

class HelloAction(BaseAction[HelloParams, HelloResult]):
    @summary_aspect("Сказать привет")
    async def summary(self, params, state, deps, connections, log):
        # Использование переменных скоупа, цветного фильтра и iif
        await log.info(
            "[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}] "
            "Приветствуем пользователя {%var.name|green}. Риск: {iif({%var.name} == 'admin'; red('ADMIN'); blue('user'))}",
            name=params.name
        )
        return HelloResult(greeting=f"Привет, {params.name}!")

async def main():
    coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
    machine = ActionProductMachine(mode="dev", log_coordinator=coordinator)

    user = UserAccount(name="Мир", email="mir@example.com")
    context = Context(user=UserInfo(user_id="test"))
    context._extra["account"] = user  # для демонстрации маскировки

    params = HelloParams(name="Мир")
    result = await machine.run(context, HelloAction(), params)
    print(result.greeting)

asyncio.run(main())
```

Вывод в консоль (с цветами):
```
[ActionProductMachine.dev.HelloAction.summary] Приветствуем пользователя Мир. Риск: user
Привет, Мир!
```

Email не логируется, потому что к нему нет обращения; если добавить `{%context.extra.account.email}`, он будет замаскирован (например, `mir*****`).