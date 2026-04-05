# src/action_machine/context/__init__.py
"""
Пакет контекста выполнения ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все компоненты системы контекста выполнения действий:

- **Context** — контекст выполнения действия. Содержит информацию
  о пользователе (UserInfo), запросе (RequestInfo) и среде выполнения
  (RuntimeInfo). Передаётся в машину при вызове run() и используется
  для проверки ролей и логирования.

- **UserInfo** — информация о пользователе (user_id, roles, extra).

- **RequestInfo** — метаданные входящего запроса (trace_id, client_ip,
  request_path, protocol и др.).

- **RuntimeInfo** — информация о среде выполнения (hostname, service_name,
  service_version и др.).

- **Ctx** — вложенная структура констант dot-path для декоратора
  @context_requires. Каждая константа строго соответствует реальному
  полю dataclass'а: Ctx.User.user_id == "user.user_id",
  Ctx.Request.trace_id == "request.trace_id" и т.д. IDE автодополняет,
  mypy проверяет статически.

- **ContextView** — frozen-объект с контролируемым доступом к полям
  контекста. Создаётся машиной для аспектов с @context_requires.
  Единственный публичный метод get(key) проверяет принадлежность ключа
  к множеству разрешённых и делегирует в context.resolve(key).
  Обращение к незапрошенному полю — ContextAccessError.

- **context_requires** — декоратор уровня метода. Декларирует поля
  контекста, необходимые аспекту или обработчику ошибок. Записывает
  frozenset ключей в func._required_context_keys. Наличие декоратора
  меняет ожидаемую сигнатуру: аспект получает дополнительный параметр
  ctx: ContextView.

- **ContextRequiresGateHost** — маркерный миксин, обозначающий поддержку
  @context_requires. Наследуется BaseAction. MetadataBuilder проверяет
  наличие миксина для каждого метода с _required_context_keys.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА УПРАВЛЯЕМОГО ДОСТУПА К КОНТЕКСТУ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к контексту через ToolsBox закрыт. Единственный легальный
способ получить данные контекста в аспекте — через ctx: ContextView,
предоставляемый машиной при наличии @context_requires.

Без @context_requires аспект не имеет доступа к контексту вообще.
Большинство аспектов (валидация суммы, обработка платежа) не нуждаются
в контексте — они работают только с params, state, box и connections.

Поток данных:
    1. Аспект декларирует: @context_requires(Ctx.User.user_id)
    2. MetadataBuilder собирает: AspectMeta.context_keys = frozenset({"user.user_id"})
    3. Машина при вызове: создаёт ContextView(context, context_keys)
    4. Аспект получает: ctx.get(Ctx.User.user_id) → значение
    5. Обращение к незапрошенному: ctx.get(Ctx.User.roles) → ContextAccessError

═══════════════════════════════════════════════════════════════════════════════
ПЕРЕМЕННАЯ СИГНАТУРА АСПЕКТОВ
═══════════════════════════════════════════════════════════════════════════════

Наличие @context_requires меняет ожидаемую сигнатуру метода:

    Аспекты (@regular_aspect, @summary_aspect):
        Без @context_requires → (self, params, state, box, connections)     — 5 параметров
        С @context_requires   → (self, params, state, box, connections, ctx) — 6 параметров

    Обработчики ошибок (@on_error):
        Без @context_requires → (self, params, state, box, connections, error)      — 6 параметров
        С @context_requires   → (self, params, state, box, connections, error, ctx) — 7 параметров

Гейтхост гарантирует консистентность: нельзя иметь лишний параметр
без декоратора и нельзя пропустить параметр с декоратором.

═══════════════════════════════════════════════════════════════════════════════
КАСТОМНЫЕ ПОЛЯ
═══════════════════════════════════════════════════════════════════════════════

UserInfo, RequestInfo, RuntimeInfo могут быть расширены наследниками.
Константы Ctx покрывают стандартные поля. Для кастомных — строки:

    @context_requires(Ctx.User.user_id, "user.extra.billing_plan")

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context import Ctx, context_requires, ContextView

    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user = ctx.get(Ctx.User.user_id)
        ip = ctx.get(Ctx.Request.client_ip)
        return {"audited_by": user}

    # Аспект без контекста — работает как раньше:
    @regular_aspect("Расчёт")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}
"""

from .context import Context
from .context_requires_decorator import context_requires
from .context_requires_gate_host import ContextRequiresGateHost
from .context_view import ContextView
from .ctx_constants import Ctx
from .request_info import RequestInfo
from .runtime_info import RuntimeInfo
from .user_info import UserInfo

__all__ = [
    "Context",
    "ContextRequiresGateHost",
    "ContextView",
    "Ctx",
    "RequestInfo",
    "RuntimeInfo",
    "UserInfo",
    "context_requires",
]
