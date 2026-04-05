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
READ-ONLY РЕЗУЛЬТАТ
═══════════════════════════════════════════════════════════════════════════════

Поле ``result`` аннотировано как ``ReadableDataProtocol | None``.
BaseResult — frozen pydantic-модель. Плагин может читать поля результата
через ``event.result["field"]`` или ``event.result.get("field")``,
но не может изменить его — любая попытка записи вызовет ошибку.

Это следствие общего принципа ActionMachine: все core-типы данных
(Params, Result, State) — read-only после создания.

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
ПРИМЕР ПЛАГИНА-НАБЛЮДАТЕЛЯ
═══════════════════════════════════════════════════════════════════════════════

    class ErrorObserverPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"errors": []}

        @on("on_error", ".*")
        async def observe_errors_on(self, state, event, log):
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
            # Чтение результата — read-only:
            if event.result is not None:
                status = event.result.get("status", "unknown")
                await log.info("Статус: {%var.status}", status=status)
            return state
"""

from dataclasses import dataclass

from action_machine.context.context import Context
from action_machine.core.protocols import ReadableDataProtocol
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
    """

    event_name: str
    """Имя события ('global_start', 'before:validate', 'after:save', 'on_error', 'global_finish')."""

    action_name: str
    """Полное имя класса действия (включая модуль), для которого произошло событие."""

    params: ReadableDataProtocol
    """Входные параметры действия (frozen, read-only)."""

    state_aspect: dict[str, object] | None
    """
    Состояние (state) на момент события как dict.

    Для before-событий — состояние до выполнения аспекта.
    Для after-событий — состояние после выполнения аспекта.
    Для on_error — состояние на момент возникновения ошибки.
    Для global_start и global_finish может быть None.

    Передаётся как dict (через BaseState.to_dict()), а не как BaseState,
    потому что плагин получает снимок состояния, а не ссылку на объект
    конвейера.
    """

    is_summary: bool
    """Флаг, указывающий, относится ли событие к summary-аспекту."""

    deps: DependencyFactory
    """Фабрика зависимостей для текущего выполнения действия."""

    context: Context
    """Контекст выполнения (информация о пользователе, запросе, окружении)."""

    result: ReadableDataProtocol | None
    """
    Результат выполнения действия (для событий global_finish).

    BaseResult — frozen pydantic-модель. Плагин может читать поля
    через result["field"] или result.get("field"), но не может
    изменить результат — любая попытка записи вызовет ошибку.

    Для событий, отличных от global_finish, — None.
    """

    duration: float | None
    """
    Длительность выполнения в секундах.

    Для after-событий — время выполнения соответствующего аспекта.
    Для global_finish — общее время выполнения действия.
    Для других событий — None.
    """

    nest_level: int
    """Уровень вложенности вызова действия (0 — корневое, 1 — дочернее через box.run(), и т.д.)."""

    error: Exception | None = None
    """
    Исключение, возникшее в аспекте.

    Заполняется только для события "on_error". Для всех остальных — None.
    Позволяет плагину-наблюдателю получить тип исключения, сообщение
    и traceback через __traceback__.
    """

    has_action_handler: bool = False
    """
    Наличие подходящего обработчика @on_error на уровне Action.

    True если Action имеет @on_error обработчик, подходящий по типу
    исключения (isinstance). False если обработчик не найден и ошибка
    будет проброшена наружу.

    Заполняется только для события "on_error". Для остальных — False.
    """
