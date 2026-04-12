# src/action_machine/context/__init__.py
"""
Пакет contextа выполнения ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Содержит все компоненты системы contextа выполнения действий:

- **Context** — context выполнения действия. Содержит информацию
  о пользователе (UserInfo), запросе (RequestInfo) и среде выполнения
  (RuntimeInfo). Передаётся в машину при вызове run() и используется
  для проверки ролей и логирования.

- **UserInfo** — информация о пользователе (user_id, roles).

- **RequestInfo** — метаданные входящего запроса (trace_id, client_ip,
  request_path, protocol и др.).

- **RuntimeInfo** — информация о среде выполнения (hostname, service_name,
  service_version и др.).

- **Ctx** — вложенная структура констант dot-path для декоратора
  @context_requires. Каждая константа строго соответствует реальному
  полю: Ctx.User.user_id == "user.user_id",
  Ctx.Request.trace_id == "request.trace_id" и т.д. IDE автодополняет,
  mypy проверяет статически.

- **ContextView** — frozen-объект с контролируемым доступом к полям
  contextа. Создаётся машиной для аспектов с @context_requires.
  Единственный публичный method get(key) проверяет, что ключ входит в
  подмножество, заданное @context_requires, и делегирует в context.resolve(key).
  Обращение к незапрошенному полю — ContextAccessError.

- **context_requires** — декоратор уровня methodа. Декларирует поля
  contextа, необходимые аспекту или обработчику ошибок. Записывает
  frozenset ключей в func._required_context_keys. Наличие декоратора
  меняет ожидаемую сигнатуру: аспект получает дополнительный параметр
  ctx: ContextView.

- **ContextRequiresIntent** — marker mixin, обозначающий поддержку
  @context_requires. Наследуется BaseAction.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Все компоненты contextа наследуют BaseSchema, что обеспечивает:
- Dict-подобный доступ к полям (obj["key"], obj.keys(), ...).
- Dot-path навигацию (context.resolve("user.user_id")).
- Иммутабельность (frozen=True на всех компонентах).
- Запрет произвольных полей (extra="forbid"). Расширение — только
  через наследование с явно объявленными полями.
- Сериализацию через model_dump() для логов и адаптеров.

    BaseSchema(BaseModel)
        ├── UserInfo       — frozen, forbid
        ├── RequestInfo    — frozen, forbid
        ├── RuntimeInfo    — frozen, forbid
        └── Context        — frozen, forbid
                ├── user: UserInfo
                ├── request: RequestInfo
                └── runtime: RuntimeInfo

═══════════════════════════════════════════════════════════════════════════════
УПРАВЛЯЕМЫЙ ДОСТУП К КОНТЕКСТУ
═══════════════════════════════════════════════════════════════════════════════

Экземпляр ToolsBox не содержит Context; аспект не может достать context через
box. Единственный легальный способ получить данные contextа в аспекте —
через ctx: ContextView, предоставляемый машиной при наличии @context_requires.

Без @context_requires аспект не имеет доступа к contextу вообще.
Большинство аспектов (валидация суммы, обработка платежа) не нуждаются
в contextе — они работают только с params, state, box и connections.

Поток данных:
    1. Аспект декларирует: @context_requires(Ctx.User.user_id)
    2. Инспектор аспектов собирает: aspect_snapshot.context_keys = frozenset({"user.user_id"})
    3. Машина при вызове: создаёт ContextView(context, context_keys)
    4. Аспект получает: ctx.get(Ctx.User.user_id) → значение
    5. Обращение к незапрошенному: ctx.get(Ctx.User.roles) → ContextAccessError

═══════════════════════════════════════════════════════════════════════════════
ПЕРЕМЕННАЯ СИГНАТУРА АСПЕКТОВ
═══════════════════════════════════════════════════════════════════════════════

Наличие @context_requires меняет ожидаемую сигнатуру methodа:

    Аспекты (@regular_aspect, @summary_aspect):
        Без @context_requires → (self, params, state, box, connections)     — 5 parameters
        С @context_requires   → (self, params, state, box, connections, ctx) — 6 parameters

    Обработчики ошибок (@on_error):
        Без @context_requires → (self, params, state, box, connections, error)      — 6 parameters
        С @context_requires   → (self, params, state, box, connections, error, ctx) — 7 parameters

═══════════════════════════════════════════════════════════════════════════════
РАСШИРЕНИЕ КОМПОНЕНТОВ КОНТЕКСТА
═══════════════════════════════════════════════════════════════════════════════

UserInfo, RequestInfo, RuntimeInfo расширяются через наследование
с явно объявленными полями. Константы Ctx покрывают стандартные поля.
Для кастомных полей — строки напрямую:

    @context_requires(Ctx.User.user_id, "user.billing_plan")

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context import Ctx, context_requires, ContextView

    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user = ctx.get(Ctx.User.user_id)
        ip = ctx.get(Ctx.Request.client_ip)
        return {"audited_by": user}

    # Аспект без contextа — стандартная signature:
    @regular_aspect("Расчёт")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}
"""

from .context import Context
from .context_requires_decorator import context_requires
from .context_requires_intent import ContextRequiresIntent
from .context_view import ContextView
from .ctx_constants import Ctx
from .request_info import RequestInfo
from .runtime_info import RuntimeInfo
from .user_info import UserInfo

__all__ = [
    "Context",
    "ContextRequiresIntent",
    "ContextView",
    "Ctx",
    "RequestInfo",
    "RuntimeInfo",
    "UserInfo",
    "context_requires",
]
