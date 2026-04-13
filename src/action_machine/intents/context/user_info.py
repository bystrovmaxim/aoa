# src/action_machine/intents/context/user_info.py
"""
UserInfo — информация о пользователе, инициировавшем действие.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

UserInfo — компонент contextа выполнения (Context), содержащий данные
об аутентифицированном пользователе: идентификатор и кортеж ролей
(подклассы ``BaseRole``).

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
user_id=None, roles=(). Используется NoAuthCoordinator для открытых API.

Действия с @check_roles(NoneRole) пропускают анонимных пользователей.
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
        roles = ctx.get(Ctx.User.roles)        # → (AdminRole, UserRole)

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП (унаследован от BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    user = UserInfo(user_id="agent_123", roles=(AdminRole,))

    user["user_id"]         # → "agent_123"
    user["roles"]           # → (AdminRole,)
    "user_id" in user       # → True
    user.get("user_id")     # → "agent_123"
    list(user.keys())       # → ["user_id", "roles"]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Аутентифицированный пользователь (роли — классы BaseRole):
    user = UserInfo(user_id="john_doe", roles=(UserRole, ManagerRole))

    # Анонимный пользователь:
    anon = UserInfo()
    anon.user_id    # → None
    anon.roles      # → ()

    # Расширение через наследование:
    class TenantUserInfo(UserInfo):
        tenant_id: str = "default"
        department: str | None = None

    user = TenantUserInfo(
        user_id="john",
        roles=(UserRole,),
        tenant_id="acme",
        department="engineering",
    )
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, field_serializer, field_validator

from action_machine.intents.auth.base_role import BaseRole
from action_machine.model.base_schema import BaseSchema


class UserInfo(BaseSchema):
    """
    Информация о пользователе, инициировавшем действие.

    Frozen после создания. Произвольные поля запрещены.
    Расширение — только через наследование с явными полями.

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.

    Атрибуты:
        user_id: уникальный идентификатор пользователя.
                 None для анонимного пользователя.
        roles: кортеж подклассов ``BaseRole``, назначенных пользователю.
               Пустой кортеж для анонимного пользователя.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str | None = None
    roles: tuple[type[BaseRole], ...] = Field(default_factory=tuple)

    @field_validator("roles", mode="before")
    @classmethod
    def _coerce_roles(cls, v: Any) -> tuple[type[BaseRole], ...]:
        if v is None:
            return ()
        if isinstance(v, list | tuple):
            items = tuple(v)
        else:
            raise TypeError(
                "UserInfo.roles must be a list or tuple of BaseRole subclasses, "
                f"got {type(v).__name__}: {v!r}."
            )
        for i, x in enumerate(items):
            if not isinstance(x, type) or not issubclass(x, BaseRole):
                raise TypeError(
                    f"UserInfo.roles[{i}] must be a BaseRole subclass, got {x!r}."
                )
        return items

    @field_serializer("roles", when_used="json")
    def _serialize_roles(self, roles: tuple[type[BaseRole], ...]) -> list[str]:
        """
        Serialize role classes into stable wire-safe role names for JSON mode.

        Runtime auth keeps ``roles`` as classes for ``issubclass`` checks; only
        JSON projections convert them to strings.
        """
        return [role.name for role in roles]
