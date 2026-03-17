02_getting_started.md

# Начало работы с ActionEngine

ActionEngine — это фреймворк, реализующий парадигму AOA. Он позволяет строить бизнес‑логику как последовательность предсказуемых, изолированных и тестируемых шагов. Этот документ проведёт тебя от установки до первого рабочего действия.

---

## Установка

ActionEngine устанавливается через pip:

```bash
pip install actionengine
```

Если ты разрабатываешь фреймворк локально или используешь собственный пакет:

```bash
pip install -e .
```

Никаких сложных зависимостей и конфигурационных файлов не требуется.

---

## Первое действие

Действие — это атомарная бизнес‑операция. Создадим простейшее действие, которое удваивает число.

```python
from dataclasses import dataclass
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.AspectMethod import summary_aspect

@dataclass(frozen=True)
class DoubleParams(BaseParams):
    value: int

@dataclass(frozen=True)
class DoubleResult(BaseResult):
    doubled: int

class DoubleNumber(BaseAction[DoubleParams, DoubleResult]):

    @summary_aspect("Удвоение числа")
    async def handle(self, params: DoubleParams, state, deps):
        return DoubleResult(doubled=params.value * 2)
```

Что здесь важно:

Params и Result — неизменяемые dataclass. Действие содержит ровно один summary‑аспект. Внутри нет состояния — все данные приходят через params. Все методы-аспекты объявляются как async def — это единый стиль для всего кода действий.

---

## Запуск через ActionMachine

ActionMachine — единственная точка входа для выполнения любого действия.

```python
from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Context.Context import Context

machine = ActionProductMachine(context=Context())

params = DoubleParams(value=21)
result = await machine.run(DoubleNumber(), params)

print(result.doubled)  # 42
```

Машина сама вызывает аспекты, управляет зависимостями и обрабатывает события плагинов.

---

## Добавление аспекта

Аспекты разбивают бизнес‑логику на этапы. Добавим проверку входных данных перед финальным расчётом.

```python
from ActionMachine.Core.AspectMethod import aspect

class DoubleNumber(BaseAction[DoubleParams, DoubleResult]):

    @aspect("Проверка входных данных")
    async def validate(self, params, state, deps):
        if params.value < 0:
            raise ValueError("Число должно быть неотрицательным")
        return state

    @summary_aspect("Удвоение числа")
    async def handle(self, params, state, deps):
        return DoubleResult(doubled=params.value * 2)
```

Теперь конвейер: validate — handle. Аспекты вызываются строго сверху вниз.

---

## Добавление зависимости

ActionEngine использует декларативное DI через декоратор depends. Добавим сервис логирования.

```python
from ActionMachine.Core.AspectMethod import depends

class Logger:
    def log(self, msg):
        print(msg)

@depends(Logger)
class LoggedDouble(BaseAction[DoubleParams, DoubleResult]):

    @aspect("Логирование")
    async def log(self, params, state, deps):
        deps.get(Logger).log(f"Удваиваем число {params.value}")
        return state

    @summary_aspect("Удвоение")
    async def handle(self, params, state, deps):
        return DoubleResult(doubled=params.value * 2)
```

Фабрика зависимостей создаётся автоматически. Никакой ручной конфигурации не нужно.

---

## Подключение плагинов

Плагины — наблюдатели за исполнением действий. Они не влияют на бизнес‑логику, но могут логировать события, собирать метрики и вести аудит.

```python
from ActionMachine.Plugins.Plugin import Plugin
from ActionMachine.Plugins.Decorators import on

class ConsolePlugin(Plugin):
    def get_initial_state(self):
        return {}

    @on("global_start", ".*", ignore_exceptions=True)
    async def on_start(self, state_plugin, event_name, action_name, params,
                       state_aspect, is_summary, deps, context, result, duration,
                       nest_level, **kwargs):
        print(f"[start] {action_name}")
        return state_plugin
```

Подключение плагина к машине:

```python
machine = ActionProductMachine(Context(), plugins=[ConsolePlugin()])
result = await machine.run(DoubleNumber(), DoubleParams(value=10))
```

---

## Тестирование

ActionEngine спроектирован так, чтобы тестирование было простым и быстрым. ActionTestMachine позволяет подменять зависимости без инфраструктуры.

```python
from ActionMachine.Core.ActionTestMachine import ActionTestMachine

async def test_double():
    machine = ActionTestMachine()
    result = await machine.run(DoubleNumber(), DoubleParams(5))
    assert result.doubled == 10
```

Для подмены зависимостей передай словарь моков:

```python
machine = ActionTestMachine({
    Logger: MockLogger()
})
```

---

## Что изучать дальше

03_glossary.md — все термины AOA в одном месте.

04_concepts.md — ключевые понятия архитектуры.

07_actions.md — как правильно писать действия.

08_aspects_vs_actions.md — когда аспект, когда отдельное действие.

14_machine.md — жизненный цикл и пайплайн ActionMachine.

15_di.md — декларативное внедрение зависимостей.

19_testing.md — полное руководство по тестированию.
