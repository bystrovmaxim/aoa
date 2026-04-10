# src/action_machine/context/user_info.py
"""
UserInfo — информация о пользователе, инициировавшем действие.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

UserInfo — компонент contextа выполнения (Context), содержащий данные
об аутентифицированном пользователе: идентификатор и список ролей.

Используется машиной (ActionProductMachine) для проверки ролевых
ограничений (@check_roles), аспектами — для аудита и логирования
через @context_requires и ContextView.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── UserInfo (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
FROZEN И FORBID
═══════════════════════════════════════════════════════════════════════════════

UserInfo неизменяем после создания. Это гарантирует, что информация
о пользователе не может быть случайно модифицирована аспектами или
плагинами в ходе выполнения конвейера.

Произвольные поля запрещены (extra="forbid"). Если конкретному проекту
нужны дополнительные данные о пользователе (billing_plan, department,
tenant_id), создаётся наследник с явно объявленными полями:

    class BillingUserInfo(UserInfo):
        billing_plan: str = "free"
        tenant_id: str | None = None

═══════════════════════════════════════════════════════════════════════════════
АНОНИМНЫЙ ПОЛЬЗОВАТЕЛЬ
═══════════════════════════════════════════════════════════════════════════════

UserInfo() без аргументов создаёт анонимного пользователя:
user_id=None, roles=[]. Используется NoAuthCoordinator для открытых API.

Действия с @check_roles(ROLE_NONE) пропускают анонимных пользователей.
Действия с конкретными ролями отклоняют их с AuthorizationError.

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП В АСПЕКТАХ
═══════════════════════════════════════════════════════════════════════════════

Прямой доступ к UserInfo из аспекта невозможен. Единственный путь —
через @context_requires и ContextView:

    @regular_aspect("Аудит")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)    # → "agent_123"
        roles = ctx.get(Ctx.User.roles)          # → ["admin", "user"]
        return {}

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП (унаследован от BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    user = UserInfo(user_id="agent_123", roles=["admin"])

    user["user_id"]         # → "agent_123"
    user["roles"]           # → ["admin"]
    "user_id" in user       # → True
    user.get("user_id")     # → "agent_123"
    list(user.keys())       # → ["user_id", "roles"]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Аутентифицированный пользователь:
    user = UserInfo(user_id="john_doe", roles=["user", "manager"])

    # Анонимный пользователь:
    anon = UserInfo()
    anon.user_id    # → None
    anon.roles      # → []

    # Расширение через наследование:
    class TenantUserInfo(UserInfo):
        tenant_id: str = "default"
        department: str | None = None

    user = TenantUserInfo(
        user_id="john",
        roles=["user"],
        tenant_id="acme",
        department="engineering",
    )
"""

from pydantic import ConfigDict

from action_machine.core.base_schema import BaseSchema


class UserInfo(BaseSchema):
    """
    Информация о пользователе, инициировавшем действие.

    Frozen после создания. Произвольные поля запрещены.
    Расширение — только через наследование с явными полями.

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.

    Атрибуты:
        user_id: уникальный идентификатор пользователя.
                 None для анонимного пользователя.
        roles: список ролей пользователя (например, ["user", "admin"]).
               Пустой список для анонимного пользователя.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str | None = None
    roles: list[str] = []
