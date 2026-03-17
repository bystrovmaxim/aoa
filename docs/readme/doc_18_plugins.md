18_plugins.md

# Плагины в ActionEngine

Плагины — это механизм наблюдения, встроенный в ActionEngine. Они позволяют видеть всё что происходит во время выполнения действий — логировать, собирать метрики, строить трассировки, вести аудит — не вмешиваясь в бизнес-логику. Плагин не может изменить поведение действия. Он только наблюдает [1].

Но плагины делают нечто большее чем просто пишут строки в консоль. Они являются механизмом построения семантического дерева выполнения — структурированного, машиночитаемого представления того что именно произошло в конкретном бизнес-процессе.

---

## Основной принцип

Плагин — это наблюдатель а не участник процесса. ActionMachine гарантирует что плагины не могут изменить params, state или result. Ошибки в плагине при ignore_exceptions=True не прерывают выполнение бизнес-логики. Плагины работают асинхронно но конвейер действий остаётся синхронным [1].

Это создаёт безопасный слой расширений. Можно добавлять и убирать плагины не боясь сломать логику.

---

## События жизненного цикла

ActionMachine генерирует фиксированный набор событий для каждого вызова run:

global_start — перед запуском первого аспекта. before — перед каждым regular-аспектом. after — после каждого regular-аспекта. global_finish — после выполнения summary-аспекта.

Каждое событие сопровождается набором данных:

params — входные данные действия. state_aspect — состояние на момент события. result — только при global_finish. duration — для after и global_finish. nest_level — уровень вложенности вызовов. context — полный объект Context.

---

## Структура плагина

Плагин — это класс наследующий Plugin. Он обязан реализовать метод get_initial_state и содержать обработчики событий помеченные декоратором @on.

```python
from ActionMachine.Plugins.Plugin import Plugin
from ActionMachine.Plugins.Decorators import on

class ConsoleLoggingPlugin(Plugin):

    def get_initial_state(self):
        return {}

    @on("global_start", ".*", ignore_exceptions=True)
    async def on_start(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}→ START {action_name} params={params}")
        return state_plugin

    @on("before:.*", ".*", ignore_exceptions=True)
    async def on_before(self, state_plugin, event_name, action_name,
                        params, state_aspect, is_summary,
                        deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}  BEFORE {event_name}: state={state_aspect}")
        return state_plugin

    @on("after:.*", ".*", ignore_exceptions=True)
    async def on_after(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}  AFTER {event_name}: duration={duration:.4f}s")
        return state_plugin

    @on("global_finish", ".*", ignore_exceptions=True)
    async def on_finish(self, state_plugin, event_name, action_name,
                        params, state_aspect, is_summary,
                        deps, context, result, duration, nest_level, **kwargs):
        indent = "  " * nest_level
        print(f"{indent}← FINISH {action_name} result={result} time={duration:.4f}s")
        return state_plugin
```

---

## Декоратор @on

Декоратор @on связывает метод плагина с событием через регулярные выражения:

```python
@on(event_regex="before:.*", class_regex=".*", ignore_exceptions=True)
```

event_regex — какие события ловить. Можно использовать регулярные выражения. class_regex — для каких действий. Точное имя класса или паттерн. ignore_exceptions — подавлять ли ошибки обработчика.

Примеры:

```python
# Ловить все события для всех действий
@on(".*", ".*", ignore_exceptions=True)

# Ловить только global_finish для конкретного действия
@on("global_finish", ".*CreateOrderAction.*", ignore_exceptions=False)

# Ловить только after-события
@on("after:.*", ".*", ignore_exceptions=True)
```

---

## Состояние плагина

Плагин не хранит состояние в self. ActionMachine вызывает get_initial_state для каждого вызова run и хранит состояние отдельно в _plugin_states. Это состояние передаётся обработчикам как state_plugin и возвращается из них [1].

Это исключает загрязнение состояния между разными запросами:

```python
class MetricsPlugin(Plugin):

    def get_initial_state(self):
        return {
            "start_time": None,
            "aspect_count": 0,
            "errors": []
        }

    @on("global_start", ".*", ignore_exceptions=True)
    async def on_start(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        import time
        state_plugin["start_time"] = time.time()
        return state_plugin

    @on("after:.*", ".*", ignore_exceptions=True)
    async def on_after(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        state_plugin["aspect_count"] += 1
        return state_plugin

    @on("global_finish", ".*", ignore_exceptions=True)
    async def on_finish(self, state_plugin, event_name, action_name,
                        params, state_aspect, is_summary,
                        deps, context, result, duration, nest_level, **kwargs):
        total = duration
        count = state_plugin["aspect_count"]
        print(f"[METRICS] {action_name}: {count} аспектов за {total:.4f}s")
        return state_plugin
```

---

## Вложенность и семантическое дерево вызовов

Параметр nest_level указывает глубину вложенности. Корневое действие получает nest_level=0. Каждое вложенное действие увеличивает его на единицу [1].

Это позволяет строить не просто иерархические логи — а полноценное семантическое дерево выполнения. Плагин на 50 строк способен записывать в JSON структурированный граф с state на каждом узле, duration каждого аспекта и полной вложенностью вызовов.

```python
@on("global_start", ".*", ignore_exceptions=True)
async def on_start(self, state_plugin, event_name, action_name,
                   params, state_aspect, is_summary,
                   deps, context, result, duration, nest_level, **kwargs):
    indent = "  " * nest_level
    print(f"{indent}→ {action_name}")
    return state_plugin

@on("global_finish", ".*", ignore_exceptions=True)
async def on_finish(self, state_plugin, event_name, action_name,
                    params, state_aspect, is_summary,
                    deps, context, result, duration, nest_level, **kwargs):
    indent = "  " * nest_level
    print(f"{indent}← {action_name} ({duration:.4f}s)")
    return state_plugin
```

Вывод для вложенного вызова:

```
→ ParentAction
  → ChildAction
  ← ChildAction (0.0010s)
← ParentAction (0.1037s)
```

Такое дерево можно передать языковой модели и получить объяснение что именно произошло в этом конкретном вызове, где возникла проблема и почему. Это не документация — это живые данные о бизнес-процессе собранные в runtime.

---

## Плагин как инструмент анализа

Поскольку каждый Action является полностью машиночитаемой спецификацией самого себя — зависимости, роли, шаги, контракты — плагин получает доступ к богатому контексту на каждом событии. Из этого следует несколько нетривиальных возможностей.

Первое — плагин может записывать production-трассы в JSON. Каждый вызов machine.run превращается в структурированный документ с params, state на каждом шаге, result и duration. Такой документ можно использовать для автоматической генерации тестов.

Второе — плагин может собирать воронки бизнес-процессов. Сколько вызовов CreateOrderAction дошло до аспекта charge, сколько упало на validate. Это не метрики инфраструктуры — это метрики бизнес-логики.

Третье — плагин может строить аудит по ролям. Кто вызывал какие операции, с какими параметрами и когда. Context содержит user_id и роли — всё это доступно в каждом обработчике.

Четвёртое — плагин может обнаруживать аномалии. Аспект charge_card стал выполняться в 5 раз дольше обычного — это видно в duration события after.

Всё это работает без изменения единой строчки бизнес-логики. Плагины наблюдают но не участвуют.

---

## Обработка ошибок в плагинах

ActionMachine вызывает обработчики плагинов через _run_single_handler. Если обработчик бросил исключение и ignore_exceptions=True — ошибка пишется в лог и выполнение конвейера продолжается. Если ignore_exceptions=False — исключение поднимается наверх и прерывает выполнение [1].

Рекомендация: всегда используй ignore_exceptions=True в production-плагинах. Это гарантирует что сломанный плагин не остановит бизнес-процесс.

---

## Подключение плагинов к машине

Плагины передаются при создании ActionProductMachine:

```python
from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Context.Context import Context

machine = ActionProductMachine(
    context=Context(),
    plugins=[
        ConsoleLoggingPlugin(),
        MetricsPlugin(),
        AuditPlugin()
    ]
)

result = await machine.run(CreateOrderAction(), params)
```

---

## Плагин аудита

Типичный пример плагина для аудита бизнес-операций:

```python
class AuditPlugin(Plugin):

    def get_initial_state(self):
        return {"events": []}

    @on("global_start", ".*", ignore_exceptions=True)
    async def on_start(self, state_plugin, event_name, action_name,
                       params, state_aspect, is_summary,
                       deps, context, result, duration, nest_level, **kwargs):
        if context and context.user:
            state_plugin["events"].append({
                "type": "action_start",
                "action": action_name,
                "user_id": context.user.user_id,
                "roles": context.user.roles,
                "params": str(params)
            })
        return state_plugin

    @on("global_finish", ".*", ignore_exceptions=True)
    async def on_finish(self, state_plugin, event_name, action_name,
                        params, state_aspect, is_summary,
                        deps, context, result, duration, nest_level, **kwargs):
        state_plugin["events"].append({
            "type": "action_finish",
            "action": action_name,
            "duration": duration,
            "result": str(result)
        })
        for event in state_plugin["events"]:
            await self._save_to_audit_log(event)
        return state_plugin

    async def _save_to_audit_log(self, event):
        pass  # реальная запись в БД или файл
```

---

## Когда писать плагины

Плагины подходят для:

Логирования — вывод хода выполнения в консоль или файл. Метрик — сбор времени выполнения, количества вызовов. Трассировки — построение дерева вызовов для систем мониторинга. Аудита — запись кто что делал и когда. Профилирования — обнаружение медленных аспектов. Семантических деревьев выполнения — структурированный JSON для последующего анализа или передачи в LLM. Интеграции — отправка событий в Prometheus, Datadog, Sentry.

Плагины не подходят для:

Бизнес-логики — плагин не должен принимать решения. Изменения данных — плагин не может изменить params, state или result. Управления транзакциями — это ответственность Actions и ресурсов.

---

## Тестирование плагинов

Плагины тестируются через ActionTestMachine:

```python
import pytest

@pytest.mark.asyncio
async def test_logging_plugin():
    events = []

    class TestPlugin(Plugin):
        def get_initial_state(self):
            return []

        @on("global_start", ".*", ignore_exceptions=True)
        async def on_start(self, state_plugin, event_name, action_name,
                           params, state_aspect, is_summary,
                           deps, context, result, duration, nest_level, **kwargs):
            state_plugin.append(f"start:{action_name}")
            return state_plugin

        @on("global_finish", ".*", ignore_exceptions=True)
        async def on_finish(self, state_plugin, event_name, action_name,
                            params, state_aspect, is_summary,
                            deps, context, result, duration, nest_level, **kwargs):
            state_plugin.append(f"finish:{action_name}")
            events.extend(state_plugin)
            return state_plugin

    plugin = TestPlugin()
    machine = ActionTestMachine(plugins=[plugin])

    result = await machine.run(
        DoubleAction(),
        DoubleAction.Params(value=5)
    )

    assert result.doubled == 10
    assert any("start" in e for e in events)
    assert any("finish" in e for e in events)
```

---

## Итог

Плагины — это безопасный, изолированный и расширяемый слой наблюдения в AOA. Они вызываются автоматически, работают асинхронно, имеют собственное изолированное состояние и никогда не влияют на бизнес-логику. Ошибки в плагинах изолируются и не останавливают выполнение [1].

Но главное — плагины являются механизмом построения семантического дерева выполнения. Каждый вызов machine.run может быть записан как структурированный граф с state на каждом узле, duration каждого аспекта и полной вложенностью вызовов. Это дерево можно передать языковой модели, загрузить в систему мониторинга, использовать для автоматической генерации тестов или для аудита безопасности.

Observability в AOA встроена в архитектуру — не как дополнение, а как фундаментальный принцип.

---

## Что изучать дальше

19_testing.md — полное руководство по тестированию.

14_machine.md — жизненный цикл ActionMachine.

17_async.md — асинхронность и asyncio.

20_auth_architecture.md — аутентификация и Context.

24_architecture_overview.md — слои и поток данных в AOA.

28_specification.md — полная формальная модель AOA.
