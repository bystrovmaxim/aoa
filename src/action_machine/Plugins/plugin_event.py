# src/action_machine/plugins/plugin_event.py
"""
PluginEvent — контейнер данных события, доставляемого обработчикам плагинов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

PluginEvent используется координатором плагинов (PluginRunContext) для
упаковки всех параметров, связанных с событием, которые затем передаются
в методы плагинов, помеченные декоратором @on.

Все поля предназначены только для чтения. Плагины — наблюдатели: они
читают данные события, но не могут изменить результат действия или
повлиять на ход выполнения конвейера.

═══════════════════════════════════════════════════════════════════════════════
ТИПЫ СОБЫТИЙ
═══════════════════════════════════════════════════════════════════════════════

    global_start      — начало выполнения действия.
    before:{aspect}   — перед выполнением аспекта.
    after:{aspect}    — после выполнения аспекта.
    on_error          — ошибка в аспекте (до вызова @on_error обработчика Action).
    global_finish     — завершение выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
FROZEN РЕЗУЛЬТАТ
═══════════════════════════════════════════════════════════════════════════════

Поле ``result`` аннотировано как ``BaseSchema | None``. BaseResult —
frozen pydantic-модель (наследник BaseSchema). Плагин может читать поля
результата через ``event.result["field"]`` или ``event.result.get("field")``,
но не может изменить его — любая попытка записи вызовет ошибку.

Это следствие общего принципа ActionMachine: все core-типы данных
(Params, Result, State) — frozen после создания.

═══════════════════════════════════════════════════════════════════════════════
FROZEN ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

Поле ``params`` аннотировано как ``BaseSchema``. BaseParams — frozen
pydantic-модель (наследник BaseSchema). Параметры неизменяемы на
протяжении всего конвейера.

═══════════════════════════════════════════════════════════════════════════════
СОБЫТИЕ on_error
═══════════════════════════════════════════════════════════════════════════════

Событие "on_error" эмитируется ПЕРЕД вызовом обработчика @on_error
на уровне Action. Плагин-наблюдатель не может изменить результат или
подавить ошибку — он только наблюдает. Поля PluginEvent при on_error:

    event_name          = "on_error"
    action_name         = полное имя действия
    params              = входные параметры
    state_aspect        = состояние конвейера на момент ошибки (dict)
    error               = экземпляр исключения, возникшего в аспекте
    has_action_handler  = True если Action имеет подходящий @on_error
    result              = None (ещё не определён)
    duration            = None

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ПЛАГИНА-НАБЛЮДАТЕЛЯ ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

    class ErrorObserverPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"errors": []}

        @on("on_error", ".*")
        async def on_observe_errors(self, state, event, log):
            state["errors"].append({
                "action": event.action_name,
                "error": str(event.error),
                "has_handler": event.has_action_handler,
            })
            await log.error(
                "[{%scope.plugin}] Ошибка в {%scope.action}: {%var.error}",
                error=str(event.error),
            )
            return state

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ПЛАГИНА МЕТРИК
═══════════════════════════════════════════════════════════════════════════════

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0}

        @on("global_finish", ".*")
        async def on_track(self, state, event, log):
            state["total"] += 1
            if event.result is not None:
                status = event.result.get("status", "unknown")
                await log.info("Статус: {%var.status}", status=status)
            return state
"""

from dataclasses import dataclass

from action_machine.context.context import Context
from action_machine.core.base_schema import BaseSchema
from action_machine.dependencies.dependency_factory import DependencyFactory


@dataclass
class PluginEvent:
    """
    Контейнер для всех данных, передаваемых в обработчик плагина.

    Создаётся на каждое событие и передаётся в методы плагинов,
    помеченные декоратором @on. Сигнатура обработчика:
    ``async def handler(self, state, event, log) → state``.

    Все поля предназначены только для чтения. Плагины — наблюдатели,
    они не могут модифицировать результат действия или состояние конвейера
    через объект события.

    Атрибуты:
        event_name: имя события ("global_start", "before:validate",
                    "after:save", "on_error", "global_finish").
        action_name: полное имя класса действия (включая модуль).
        params: входные параметры действия (frozen BaseParams, наследник BaseSchema).
        state_aspect: состояние конвейера на момент события как dict.
                      Для global_start и global_finish может быть None.
        is_summary: True если событие связано с summary-аспектом.
        deps: фабрика зависимостей для текущего выполнения действия.
        context: контекст выполнения (информация о пользователе, запросе, окружении).
        result: результат выполнения действия (frozen BaseResult, наследник BaseSchema).
                Для событий, отличных от global_finish, — None.
        duration: длительность выполнения в секундах. Для after-событий —
                  время аспекта. Для global_finish — общее время. Иначе — None.
        nest_level: уровень вложенности вызова действия (0 — корневое).
        error: исключение из аспекта (только для события "on_error").
        has_action_handler: наличие подходящего @on_error обработчика на Action
                            (только для "on_error").
    """

    event_name: str
    """Имя события."""

    action_name: str
    """Полное имя класса действия (включая модуль)."""

    params: BaseSchema
    """Входные параметры действия (frozen, наследник BaseSchema)."""

    state_aspect: dict[str, object] | None
    """Состояние конвейера на момент события как dict. Может быть None."""

    is_summary: bool
    """True если событие связано с summary-аспектом."""

    deps: DependencyFactory
    """Фабрика зависимостей для текущего выполнения действия."""

    context: Context
    """Контекст выполнения (пользователь, запрос, окружение)."""

    result: BaseSchema | None
    """Результат действия (frozen, наследник BaseSchema). None до global_finish."""

    duration: float | None
    """Длительность в секундах. None для событий без замера времени."""

    nest_level: int
    """Уровень вложенности вызова (0 — корневое, 1 — дочернее через box.run())."""

    error: Exception | None = None
    """Исключение из аспекта (только для события "on_error")."""

    has_action_handler: bool = False
    """Наличие подходящего @on_error обработчика на Action (только для "on_error")."""
